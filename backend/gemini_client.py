"""Direct Gemini calls — for non-Workspace AI (chat replies, ecosystem graph).

Uses google-genai SDK against Vertex AI. Auth via ADC.

Workspace mutations (sending email, creating Drive folders, etc.) live in the
friend's AI stack — see `ai_client.py`. This module handles things the friend's
stack is not responsible for: conversational replies in the Event Architect /
Review / Ecosystem chat surfaces.
"""
from __future__ import annotations

import json
import logging
from typing import Any

from google import genai
from google.genai import types as genai_types

import schemas

log = logging.getLogger(__name__)

_CHAT_MODEL = "gemini-3-flash-preview"
_GRAPH_MODEL = "gemini-3-flash-preview"

_PLAYBOOK_GRAPH_SCHEMA: dict[str, Any] = {
    "type": "object",
    "required": ["root_label", "categories"],
    "properties": {
        "root_label": {"type": "string"},
        "categories": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["id", "label", "kind", "items"],
                "properties": {
                    "id": {"type": "string"},
                    "label": {"type": "string"},
                    "kind": {
                        "type": "string",
                        "enum": ["people", "tool", "sponsor", "asset", "theme"],
                    },
                    "items": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "required": ["name"],
                            "properties": {
                                "name": {"type": "string"},
                                "role": {"type": "string"},
                                "detail": {"type": "string"},
                            },
                        },
                    },
                },
            },
        },
    },
}

_GRAPH_SCHEMA: dict[str, Any] = {
    "type": "object",
    "required": ["nodes", "edges"],
    "properties": {
        "nodes": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["id", "label", "type", "x", "y"],
                "properties": {
                    "id": {"type": "string"},
                    "label": {"type": "string"},
                    "type": {
                        "type": "string",
                        "enum": ["event", "shared", "people", "tool"],
                    },
                    "x": {"type": "number"},
                    "y": {"type": "number"},
                },
            },
        },
        "edges": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["id", "source", "target", "label"],
                "properties": {
                    "id": {"type": "string"},
                    "source": {"type": "string"},
                    "target": {"type": "string"},
                    "label": {"type": "string"},
                },
            },
        },
    },
}


class GeminiClient:
    def __init__(
        self,
        project: str,
        location: str = "global",
        api_key: str = "",
    ) -> None:
        # An AI Studio API key routes through the Gemini Developer API, which
        # has separate quota from Vertex AI — use it as a rate-limit fallback.
        # Otherwise fall back to Vertex AI with Application Default Credentials.
        if api_key:
            self.client = genai.Client(api_key=api_key)
            log.info("GeminiClient using Developer API (API key)")
        else:
            self.client = genai.Client(
                vertexai=True, project=project, location=location,
            )
            log.info("GeminiClient using Vertex AI (project=%s)", project)

    # ── Event Architect chat ─────────────────────────────────────────────

    async def architect_reply(self, req: schemas.ArchitectChatRequest) -> str:
        system = (
            "You are the Event Architect — an AI guide helping someone plan an event "
            "inside a tool called gieventhub. Reply in 1-3 short sentences, no markdown. "
            "Be concrete: name specific mentors, sponsors, or venues from the user's "
            "locked selections when relevant. Never mention Google Workspace actions "
            "as done — say 'I'll draft', not 'I sent'."
        )
        user_prompt = self._architect_prompt(req)
        return await self._generate_text(system, user_prompt, req.history)

    @staticmethod
    def _architect_prompt(req: schemas.ArchitectChatRequest) -> str:
        ctx = req.context
        lines = [f"User message: {req.message}", "", "Current event state:"]
        if ctx.event_name:
            lines.append(f"- Event: {ctx.event_name}")
        if ctx.event_format:
            lines.append(f"- Format: {ctx.event_format}")
        if ctx.audience:
            lines.append(f"- Audience: {ctx.audience}")
        if ctx.goal:
            lines.append(f"- Goal: {ctx.goal}")
        if ctx.locked_mentors:
            lines.append(f"- Locked mentors: {', '.join(ctx.locked_mentors)}")
        if ctx.locked_sponsors:
            lines.append(f"- Locked sponsors: {', '.join(ctx.locked_sponsors)}")
        if ctx.locked_venue:
            lines.append(f"- Venue: {ctx.locked_venue}")
        if ctx.forked_playbook_id:
            lines.append(f"- Forked from playbook: {ctx.forked_playbook_id}")
        lines.append(f"- Current step: {ctx.step}")
        return "\n".join(lines)

    # ── Review chat ──────────────────────────────────────────────────────

    async def review_reply(self, req: schemas.ReviewChatRequest) -> str:
        system = (
            "You help an event organizer finalize a playbook. Reply in 1-2 short "
            "sentences, no markdown. If the user pasted a Google Drive link, "
            "acknowledge that we'll pull data from it. If they uploaded a file, "
            "acknowledge the filename and what you'll extract."
        )
        prompt_lines = [f"User: {req.message}"]
        if req.file_name:
            prompt_lines.append(f"User uploaded file: {req.file_name}")
        return await self._generate_text(system, "\n".join(prompt_lines), req.history)

    # ── Playbook knowledge tree ──────────────────────────────────────────

    async def playbook_graph(
        self, playbook: schemas.Playbook | None, draft: schemas.PlaybookDraft | None,
    ) -> schemas.PlaybookGraph:
        """Generate a radial knowledge tree for a playbook.

        Returns 3-5 categories with 3-12 items each, derived from the playbook's
        title, description, category, context, assets, features, and tags.
        """
        title, context_block = _playbook_context_block(playbook, draft)
        system = (
            "You produce a structured knowledge tree for an event playbook. "
            "Return JSON only. Generate 3-5 categories that are most relevant "
            "to THIS event (e.g. Mentors, Sponsors, Tech Stack, Run-of-Show, "
            "Audience, Themes, Workspace Tools — whichever fits). Each category "
            "has 3-12 items. For each item: name (short label), role (one-line "
            "title/role/use), detail (short context — what it does or who it is). "
            "Pick the `kind` value that best fits each category:\n"
            "  - people: humans (mentors, judges, organizers, attendees)\n"
            "  - sponsor: companies funding the event\n"
            "  - tool: software / SaaS / Workspace surfaces\n"
            "  - asset: deliverables / artifacts (forms, rubrics, decks)\n"
            "  - theme: abstract concepts / themes / phases\n"
            "Be specific to this event — names, dates, real touchpoints. "
            "Avoid generic boilerplate."
        )
        prompt = (
            f"Event title: {title}\n\n{context_block}\n\n"
            "Return the JSON object with root_label and categories."
        )
        raw = await self._generate_text(
            system,
            prompt,
            [],
            response_mime_type="application/json",
            response_schema=_PLAYBOOK_GRAPH_SCHEMA,
            max_output_tokens=3072,
            thinking_level="high",
        )
        return _parse_playbook_graph(raw, fallback_root=title or "Event")

    # ── Ecosystem chat + graph ───────────────────────────────────────────

    async def ecosystem_reply_and_graph(
        self,
        req: schemas.EcosystemChatRequest,
        playbooks: list[schemas.Playbook] | None = None,
    ) -> tuple[str, list[schemas.GraphNode], list[schemas.GraphEdge]]:
        """Two separate calls — prose and graph — to avoid the model wrapping
        the entire structured payload inside a single string field.

        When `playbooks` is provided, a compact catalogue is injected into the
        system instruction so Gemini can answer factual questions (count by
        venue, list by host, etc.) over the real Firestore data.
        """
        catalogue = _format_playbook_catalogue(playbooks or [])

        reply_system = (
            "You are the gieventhub ecosystem assistant. You can:\n"
            "  1. Answer factual questions about the playbook catalogue below "
            "(counts, filters by venue / host / category / tag / city).\n"
            "  2. Explain relationships between events.\n"
            "Reply in 1-3 short paragraphs of markdown. When the user asks a "
            "factual question, cite playbook titles you found. If no playbooks "
            "match, say so plainly. Don't invent venues, hosts, or counts.\n\n"
            f"{catalogue}"
        )
        graph_system = (
            "You produce a small knowledge graph that visually represents the "
            "assistant's answer to the user's query, grounded in the playbook "
            "catalogue below. Output JSON only.\n"
            "Node types:\n"
            "  - event: one specific playbook / event\n"
            "  - people: a person, organizer, host, or author\n"
            "  - tool: a piece of software, platform, or Workspace surface\n"
            "  - shared: a shared theme, topic, venue, or category\n"
            "Rules:\n"
            "  - If the answer lists several events tied to ONE entity (a "
            "person, host, sponsor, tool, or theme), make a central node for "
            "that entity and ONE event node per listed event, each connected "
            "to the central node with a descriptive edge label (e.g. "
            "'organized', 'involved in').\n"
            "  - If the answer covers MULTIPLE events and what connects them "
            "(shared participants, tools, themes, venues, or hosts), render "
            "every event as its own event node and every connector as its own "
            "node, linking each connector to each event it belongs to. Those "
            "shared connectors are the whole point of the graph.\n"
            "  - If the answer compares two events, show both events plus the "
            "themes / tools / people they share.\n"
            "  - Use the EXACT playbook titles and people names from the "
            "answer and catalogue as labels. NEVER output placeholders like "
            "'Event A', 'Event B', or a generic 'Shared Theme'.\n"
            "  - 4-50 nodes; every node must be reachable by at least one "
            "edge. When the answer covers many events, include ALL of them "
            "as event nodes plus every shared connector (participant, tool, "
            "theme, venue, host) — a connector that links multiple events "
            "must have an edge to each event it belongs to, so the graph "
            "shows the full web of relationships, not isolated pairs.\n"
            "  - Edge labels are short and descriptive (e.g. 'mentored at', "
            "'shares theme', 'same venue').\n"
            "  - Layout: spread nodes out, x in 0..900, y in -300..500.\n"
            "  - Use short ids (e1, p1, t1, s1).\n\n"
            f"{catalogue}"
        )
        reply_prompt = f"User query: {req.query}"

        reply = await self._generate_text(
            reply_system, reply_prompt, req.history, max_output_tokens=4096,
        )
        # The graph call is grounded in the reply so the visualization matches
        # the answer the user actually sees.
        graph_prompt = (
            f"User query: {req.query}\n\n"
            f'Assistant answer to visualize:\n"""\n{reply}\n"""\n\n'
            "Return a JSON object with two top-level arrays: nodes and edges "
            "that visually represent the answer above. Nothing else — no reply "
            "field."
        )
        graph_raw = await self._generate_text(
            graph_system,
            graph_prompt,
            req.history,
            response_mime_type="application/json",
            response_schema=_GRAPH_SCHEMA,
            # JSON mode pretty-prints with indentation, which burns tokens
            # fast — a multi-node graph needs generous headroom or it
            # truncates into invalid JSON and silently falls back.
            max_output_tokens=12288,
            thinking_level="high",
        )
        nodes, edges = _parse_graph_only(graph_raw)
        return reply, nodes, edges

    # ── Internal ─────────────────────────────────────────────────────────

    async def _generate_text(
        self,
        system: str,
        user_prompt: str,
        history: list[schemas.ChatMessage],
        response_mime_type: str | None = None,
        response_schema: Any | None = None,
        max_output_tokens: int = 1024,
        thinking_level: str = "low",
    ) -> str:
        contents: list[genai_types.Content] = []
        for msg in history[-6:]:
            role = "user" if msg.role == "user" else "model"
            contents.append(
                genai_types.Content(role=role, parts=[genai_types.Part(text=msg.text)])
            )
        contents.append(
            genai_types.Content(role="user", parts=[genai_types.Part(text=user_prompt)])
        )

        config = genai_types.GenerateContentConfig(
            system_instruction=system,
            temperature=0.6,
            max_output_tokens=max_output_tokens,
        )
        # Gemini 3 controls reasoning via thinking_level ("low" | "high").
        # "high" buys deeper reasoning for structured work (the knowledge
        # graph); "low" keeps prose chat fast. Keep max_output_tokens generous
        # either way so reasoning never truncates the visible answer.
        config.thinking_config = genai_types.ThinkingConfig(
            thinking_level=thinking_level,
        )
        if response_mime_type:
            config.response_mime_type = response_mime_type
        if response_schema is not None:
            config.response_schema = response_schema

        resp = await self.client.aio.models.generate_content(
            model=_CHAT_MODEL,
            contents=contents,
            config=config,
        )
        text = (resp.text or "").strip()
        if not text:
            log.warning("Empty Gemini response")
            return ""
        return text


def _format_playbook_catalogue(playbooks: list[schemas.Playbook]) -> str:
    """Compact catalogue dump for the ecosystem chat system prompt.

    Each row is one line of pipe-separated fields so the model can scan it
    quickly. We omit description/features (too verbose) and emit only the
    facets useful for filtering: title, author, category, venue, attendees,
    duration, tags.
    """
    if not playbooks:
        return "PLAYBOOK CATALOGUE: (empty)"
    lines = [
        f"PLAYBOOK CATALOGUE ({len(playbooks)} entries). Each entry is one "
        "line `id | title | author | category | venue | attendees | duration "
        "| tags`, optionally followed by a `participants:` line listing the "
        "people involved as `Name (role)`:"
    ]
    for p in playbooks:
        venue = (p.context.venue or "").split(".")[0].strip()  # first sentence
        tags = ",".join(p.tags[:5])
        lines.append(
            f"  - {p.id} | {p.title} | {p.author} | {p.category} | "
            f"{venue} | {p.attendees} | {p.duration} | {tags}"
        )
        if p.participants:
            roster = ", ".join(
                f"{pp.name} ({pp.role})" if pp.role else pp.name
                for pp in p.participants[:10]
            )
            lines.append(f"      participants: {roster}")
    return "\n".join(lines)


def _playbook_context_block(
    playbook: schemas.Playbook | None,
    draft: schemas.PlaybookDraft | None,
) -> tuple[str, str]:
    """Returns (title, context_block_text) sourced from playbook or draft."""
    if playbook is not None:
        lines: list[str] = []
        if playbook.description:
            lines.append(f"Description: {playbook.description}")
        if playbook.category:
            lines.append(f"Category: {playbook.category}")
        if playbook.attendees:
            lines.append(f"Attendees: {playbook.attendees}")
        if playbook.duration:
            lines.append(f"Duration: {playbook.duration}")
        if playbook.tags:
            lines.append(f"Tags: {', '.join(playbook.tags)}")
        ctx = playbook.context
        if ctx.challenge:
            lines.append(f"Challenge: {ctx.challenge}")
        if ctx.targetAudience:
            lines.append(f"Audience: {ctx.targetAudience}")
        if ctx.venue:
            lines.append(f"Venue: {ctx.venue}")
        if ctx.techStack:
            lines.append(f"Tech stack: {ctx.techStack}")
        if playbook.assets:
            lines.append(
                "Existing assets: "
                + "; ".join(f"{a.name} ({a.type})" for a in playbook.assets)
            )
        if playbook.features:
            lines.append("Features: " + "; ".join(playbook.features))
        return playbook.title, "\n".join(lines)

    if draft is not None:
        lines = []
        if draft.description:
            lines.append(f"Description: {draft.description}")
        if draft.category:
            lines.append(f"Category: {draft.category}")
        if draft.tags:
            lines.append(f"Tags: {', '.join(draft.tags)}")
        if draft.context:
            ctx = draft.context
            if ctx.challenge:
                lines.append(f"Challenge: {ctx.challenge}")
            if ctx.targetAudience:
                lines.append(f"Audience: {ctx.targetAudience}")
            if ctx.venue:
                lines.append(f"Venue: {ctx.venue}")
            if ctx.techStack:
                lines.append(f"Tech stack: {ctx.techStack}")
        if draft.assets:
            lines.append(
                "Existing assets: "
                + "; ".join(f"{a.name} ({a.type})" for a in draft.assets)
            )
        if draft.features:
            lines.append("Features: " + "; ".join(draft.features))
        return draft.title, "\n".join(lines)

    return "", ""


def _parse_playbook_graph(raw: str, fallback_root: str) -> schemas.PlaybookGraph:
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        log.warning("Playbook graph response was not JSON")
        return schemas.PlaybookGraph(root_label=fallback_root or "Event", categories=[])

    categories: list[schemas.GraphCategory] = []
    for cat in data.get("categories", []):
        if not isinstance(cat, dict):
            continue
        items = []
        for it in cat.get("items", []):
            if not isinstance(it, dict) or not it.get("name"):
                continue
            items.append(
                schemas.GraphItem(
                    name=str(it["name"]),
                    role=str(it.get("role", "")),
                    detail=str(it.get("detail", "")),
                )
            )
        if not items:
            continue
        categories.append(
            schemas.GraphCategory(
                id=str(cat.get("id") or f"cat-{len(categories)}"),
                label=str(cat.get("label") or "Category"),
                kind=cat.get("kind", "theme"),
                items=items,
            )
        )
    return schemas.PlaybookGraph(
        root_label=str(data.get("root_label") or fallback_root or "Event"),
        categories=categories,
    )


def _parse_graph_only(
    raw: str,
) -> tuple[list[schemas.GraphNode], list[schemas.GraphEdge]]:
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        log.warning("Gemini graph response was not JSON")
        return ([], [])
    nodes = [_safe_node(n) for n in data.get("nodes", []) if isinstance(n, dict)]
    edges = [_safe_edge(e) for e in data.get("edges", []) if isinstance(e, dict)]
    return [n for n in nodes if n], [e for e in edges if e]


def _safe_node(n: dict[str, Any]) -> schemas.GraphNode | None:
    try:
        return schemas.GraphNode(
            id=str(n["id"]),
            label=str(n["label"]),
            type=n.get("type", "shared"),
            x=float(n.get("x", 0)),
            y=float(n.get("y", 0)),
        )
    except (KeyError, ValueError, TypeError):
        return None


def _safe_edge(e: dict[str, Any]) -> schemas.GraphEdge | None:
    try:
        return schemas.GraphEdge(
            id=str(e["id"]),
            source=str(e["source"]),
            target=str(e["target"]),
            label=str(e.get("label", "")),
        )
    except (KeyError, ValueError, TypeError):
        return None
