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

_ARCHITECT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "required": ["reply"],
    "properties": {
        "reply": {"type": "string"},
        "updates": {
            "type": "object",
            "properties": {
                "event_name": {"type": "string"},
                "event_date": {"type": "string"},
                "event_format": {"type": "string"},
                "audience": {"type": "string"},
                "goal": {"type": "string"},
                "locked_mentors": {"type": "array", "items": {"type": "string"}},
                "locked_sponsors": {"type": "array", "items": {"type": "string"}},
                "locked_venue": {"type": "string"},
                "locked_outreach": {"type": "array", "items": {"type": "string"}},
                "enabled_tools": {"type": "array", "items": {"type": "string"}},
            },
        },
    },
}

_REVIEW_SCHEMA: dict[str, Any] = {
    "type": "object",
    "required": ["reply"],
    "properties": {
        "reply": {"type": "string"},
        "updates": {
            "type": "object",
            "properties": {
                "title": {"type": "string"},
                "description": {"type": "string"},
                "tags": {"type": "array", "items": {"type": "string"}},
                "visibility": {"type": "string", "enum": ["public", "private"]},
            },
        },
    },
}

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


_MATCH_SCHEMA: dict[str, Any] = {
    "type": "object",
    "required": ["reply", "candidates"],
    "properties": {
        "reply": {"type": "string"},
        "candidates": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["name", "fit_score", "engagement_score", "reason"],
                "properties": {
                    "name": {"type": "string"},
                    "organization": {"type": "string"},
                    "role": {"type": "string"},
                    "fit_score": {"type": "integer"},
                    "engagement_score": {"type": "integer"},
                    "track_record": {"type": "string"},
                    "evidence": {"type": "array", "items": {"type": "string"}},
                    "reason": {"type": "string"},
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

    async def architect_reply(
        self, req: schemas.ArchitectChatRequest,
    ) -> tuple[str, dict[str, Any]]:
        """Returns (reply_text, field_updates).

        The Event Architect can BOTH chat AND directly edit the form fields the
        user sees on `/event/new`. We use structured output so a single call
        returns both the prose reply and a patch the frontend applies to its
        local state (event_name, format, locked mentors, etc.).
        """
        ctx = req.context
        system = (
            "You are the Event Architect — an AI co-planner inside a tool called "
            "gieventhub. You help an organizer fill out their event plan on the "
            "/event/new screen. You can do TWO things in one reply:\n\n"
            "  1. Chat back: 1-3 short sentences, no markdown.\n"
            "  2. Directly edit form fields by returning them in `updates`.\n\n"
            "Editable fields:\n"
            "  - event_name (free text)\n"
            "  - event_date (ISO date YYYY-MM-DD)\n"
            "  - event_format (MUST be one of AVAILABLE_FORMATS below)\n"
            "  - audience (free text — e.g. '250 students')\n"
            "  - goal (free text, 1-2 sentences)\n"
            "  - locked_mentors (subset of AVAILABLE_MENTORS — full list to set)\n"
            "  - locked_sponsors (subset of AVAILABLE_SPONSORS — full list to set)\n"
            "  - locked_venue (one of AVAILABLE_VENUES, or '' to clear)\n"
            "  - locked_outreach (subset of AVAILABLE_OUTREACH — full list to set)\n"
            "  - enabled_tools (subset of AVAILABLE_TOOLS — full list to set)\n\n"
            "Return JSON with two keys: `reply` and `updates`.\n\n"
            "HARD RULES:\n"
            "  - When the user asks you to fill, prefill, randomize, draft, or "
            "give an example — populate EVERY currently-empty field with "
            "reasonable values drawn from the AVAILABLE_* lists. Do NOT "
            "overwrite fields the user already filled in unless they explicitly "
            "ask you to change them.\n"
            "  - For locked_mentors / locked_sponsors / locked_outreach / "
            "enabled_tools, ALWAYS return the COMPLETE new list (keep + add - "
            "remove), never a partial diff.\n"
            "  - Never invent a mentor, sponsor, venue, outreach list, or tool "
            "that is not in the corresponding AVAILABLE_* list. Pick subsets.\n"
            "  - Format MUST come from AVAILABLE_FORMATS verbatim (case "
            "matters: 'Hackathon', 'Demo Day', etc.).\n"
            "  - If the user only asks a question or asks for advice, answer "
            "in `reply` and OMIT `updates` (or send updates as {}).\n"
            "  - In `reply`, plainly tell the user what you changed (e.g. "
            "'Filled the brief with a Stanford workshop and locked 3 mentors.') "
            "or answer their question. Never say a Google Workspace action was "
            "performed — say 'I'll draft', not 'I sent'."
        )
        user_prompt = self._architect_prompt(req)
        raw = await self._generate_text(
            system,
            user_prompt,
            req.history,
            response_mime_type="application/json",
            response_schema=_ARCHITECT_SCHEMA,
            max_output_tokens=2048,
        )
        return _parse_architect_reply(raw, ctx)

    @staticmethod
    def _architect_prompt(req: schemas.ArchitectChatRequest) -> str:
        ctx = req.context
        lines = [
            f"User message: {req.message}",
            "",
            f"Current step: {ctx.step}",
            "Current form state (only mention fields you change):",
            f"  - event_name: {ctx.event_name or '(empty)'}",
            f"  - event_date: {ctx.event_date or '(empty)'}",
            f"  - event_format: {ctx.event_format or '(empty)'}",
            f"  - audience: {ctx.audience or '(empty)'}",
            f"  - goal: {ctx.goal or '(empty)'}",
            f"  - locked_mentors: {', '.join(ctx.locked_mentors) or '(none)'}",
            f"  - locked_sponsors: {', '.join(ctx.locked_sponsors) or '(none)'}",
            f"  - locked_venue: {ctx.locked_venue or '(none)'}",
            f"  - locked_outreach: {', '.join(ctx.locked_outreach) or '(none)'}",
            f"  - enabled_tools: {', '.join(ctx.enabled_tools) or '(none)'}",
        ]
        if ctx.forked_playbook_id:
            lines.append(f"  - forked_from: {ctx.forked_playbook_id}")
        lines.append("")
        lines.append("Available catalogues — pick ONLY from these:")
        lines.append(
            f"  AVAILABLE_FORMATS: {', '.join(ctx.available_formats) or '(none)'}"
        )
        lines.append(
            f"  AVAILABLE_MENTORS: {', '.join(ctx.available_mentors) or '(none)'}"
        )
        lines.append(
            f"  AVAILABLE_SPONSORS: {', '.join(ctx.available_sponsors) or '(none)'}"
        )
        lines.append(
            f"  AVAILABLE_VENUES: {', '.join(ctx.available_venues) or '(none)'}"
        )
        lines.append(
            f"  AVAILABLE_OUTREACH: {', '.join(ctx.available_outreach) or '(none)'}"
        )
        lines.append(
            f"  AVAILABLE_TOOLS: {', '.join(ctx.available_tools) or '(none)'}"
        )
        return "\n".join(lines)

    # ── Review chat ──────────────────────────────────────────────────────

    async def review_reply(
        self, req: schemas.ReviewChatRequest,
    ) -> tuple[str, dict[str, Any]]:
        """Returns (reply_text, field_updates).

        The review screen lets the AI directly edit the playbook's editable
        fields, so this is a structured-output call: the model returns both a
        chat reply and a patch of the fields the user asked to change.
        """
        cur = req.current
        system = (
            "You help an event organizer finalize a playbook on the review "
            "screen. You can DIRECTLY EDIT the playbook's editable fields: "
            "title, description, tags, and visibility (public/private).\n\n"
            "Return JSON with two keys:\n"
            "  - reply: 1-2 short sentences, no markdown, confirming what you "
            "changed or answering the user.\n"
            "  - updates: an object holding ONLY the fields the user asked to "
            "change. Omit a field (or omit updates entirely) when it does not "
            "change.\n\n"
            "Rules:\n"
            "- To rename the playbook, set updates.title.\n"
            "- When editing the description, return the FULL new description "
            "(max 350 characters), never a diff or fragment.\n"
            "- For tags, return the COMPLETE new tag list — existing tags the "
            "user keeps, PLUS additions, MINUS anything they removed.\n"
            "- Only set updates.visibility ('public' or 'private') when the "
            "user explicitly asks to change visibility.\n"
            "- Never invent values the user did not ask for. If the user only "
            "asks a question, answer in reply and send no updates.\n"
            "- If the user pasted a Google Drive link or uploaded a file, "
            "acknowledge it in reply — you cannot read its contents yet, so "
            "do not invent them.\n"
            "- Never claim a Google Workspace action was performed."
        )
        prompt_lines = [
            f"User message: {req.message}",
            "",
            "Current playbook fields:",
            f"- title: {cur.title or '(empty)'}",
            f"- description: {cur.description or '(empty)'}",
            f"- tags: {', '.join(cur.tags) if cur.tags else '(none)'}",
            f"- visibility: {cur.visibility}",
        ]
        if req.file_name:
            prompt_lines.append(f"- the user just uploaded a file: {req.file_name}")
        raw = await self._generate_text(
            system,
            "\n".join(prompt_lines),
            req.history,
            response_mime_type="application/json",
            response_schema=_REVIEW_SCHEMA,
            max_output_tokens=2048,
        )
        return _parse_review_reply(raw)

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

    # ── Smart Match — outcome-scoring learning loop ──────────────────────

    async def recommend_matches(
        self,
        req: schemas.MatchRequest,
        playbooks: list[schemas.Playbook] | None = None,
    ) -> tuple[str, list[schemas.MatchCandidate]]:
        """Score people from past engagements against a new need.

        This is the platform's learning loop: every playbook is a past
        engagement record, and the more engagements accumulate, the more
        signal the scorer has. Scores are grounded only in observed
        participation and the events' reported outcome stats — never invented.
        """
        history_block = _format_engagement_history(playbooks or [])
        role_hint = (
            "" if req.role == "any" else f"\nRole the organizer needs: {req.role}"
        )
        system = (
            "You are the gieventhub Smart Match engine — the platform's "
            "outcome-scoring learning loop. gieventhub treats every ecosystem "
            "relationship (mentor, sponsor, judge, speaker, partner) as a "
            "reusable entity. Given a new need, mine the ENGAGEMENT HISTORY "
            "below and recommend the people whose past engagements best "
            "predict success here.\n\n"
            "For every candidate produce TWO scores, each an integer 0-100:\n"
            "  - fit_score: how well the person's domain, role, and the kinds "
            "of events they've joined match THIS specific need.\n"
            "  - engagement_score: the strength of their track record — how "
            "many events they recur in, how senior their roles, and the "
            "measurable OUTCOMES (attendee numbers, startups funded, etc.) "
            "reported by those events.\n\n"
            "HARD RULES:\n"
            "  - Recommend ONLY people who appear in the ENGAGEMENT HISTORY. "
            "Never invent a person.\n"
            "  - Derive engagement_score ONLY from observed participation and "
            "the events' reported outcome stats. Never invent ratings or "
            "outcomes that are not in the data.\n"
            "  - evidence: the exact event titles that back this candidate.\n"
            "  - reason: 1-2 sentences that cite the events by name.\n"
            "  - track_record: one short line summarizing their past "
            "engagement outcomes.\n"
            "  - Return 3-6 candidates, ranked best-first by combined score.\n"
            "  - If the history has too few people to match well, say so "
            "honestly in reply and return whatever partial matches exist.\n\n"
            "reply: 1-2 short paragraphs of markdown summarizing who you "
            "picked and why the past engagement data supports them.\n\n"
            f"{history_block}"
        )
        prompt = (
            f"Organizer's need: {req.query}{role_hint}\n\n"
            "Return a JSON object with `reply` and `candidates`."
        )
        raw = await self._generate_text(
            system,
            prompt,
            req.history,
            response_mime_type="application/json",
            response_schema=_MATCH_SCHEMA,
            max_output_tokens=6144,
            thinking_level="high",
        )
        return _parse_match(raw)

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


def _format_engagement_history(playbooks: list[schemas.Playbook]) -> str:
    """Dump every playbook as a past engagement record for the Smart Match scorer.

    Unlike the ecosystem catalogue, this emphasises the two signals the scorer
    needs: each event's reported OUTCOMES (`stats`) and the full roster of
    people who took part — so a person who recurs across high-outcome events
    earns a high engagement_score, grounded in real data.
    """
    if not playbooks:
        return "ENGAGEMENT HISTORY: (empty — no past engagements on the platform yet)"
    lines = [
        f"ENGAGEMENT HISTORY ({len(playbooks)} past engagements). Each event "
        "lists its reported outcomes and the people who took part. A person "
        "who recurs across events — especially high-outcome events — has a "
        "strong, reusable track record:"
    ]
    for p in playbooks:
        cat = p.category or "uncategorised"
        stats = p.stats or "no reported outcomes"
        tags = ",".join(p.tags[:6])
        lines.append(
            f"  • {p.title} | category: {cat} | outcomes: {stats} | tags: {tags}"
        )
        if p.participants:
            roster = "; ".join(
                f"{pp.name} ({pp.role or 'participant'}"
                + (f", {pp.organization}" if pp.organization else "")
                + ")"
                for pp in p.participants[:14]
            )
            lines.append(f"     people: {roster}")
    return "\n".join(lines)


def _clamp_score(value: Any) -> int:
    """Coerce a model-supplied score into a 0-100 integer."""
    try:
        return max(0, min(100, round(float(value))))
    except (TypeError, ValueError):
        return 0


def _parse_match(raw: str) -> tuple[str, list[schemas.MatchCandidate]]:
    """Pull (reply, candidates) out of the Smart Match JSON response."""
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        log.warning("Smart Match response was not JSON")
        return "", []

    reply = str(data.get("reply", "")).strip()
    candidates: list[schemas.MatchCandidate] = []
    for c in data.get("candidates", []):
        if not isinstance(c, dict) or not c.get("name"):
            continue
        evidence = [
            str(e).strip() for e in c.get("evidence", []) if str(e).strip()
        ]
        candidates.append(
            schemas.MatchCandidate(
                name=str(c["name"]).strip(),
                organization=str(c.get("organization", "")).strip(),
                role=str(c.get("role", "")).strip(),
                fit_score=_clamp_score(c.get("fit_score")),
                engagement_score=_clamp_score(c.get("engagement_score")),
                track_record=str(c.get("track_record", "")).strip(),
                evidence=evidence[:6],
                reason=str(c.get("reason", "")).strip(),
            )
        )
    return reply, candidates


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


_VALID_FORMATS_FALLBACK = {
    "Hackathon", "Demo Day", "Conference", "Sprint", "Workshop", "Meetup",
}


def _parse_architect_reply(
    raw: str, ctx: schemas.ArchitectContext,
) -> tuple[str, dict[str, Any]]:
    """Pull (reply, updates) out of the Architect chat's JSON response.

    Updates are aggressively validated against the catalogues `ctx` advertises
    so the AI can never feed the frontend a value its dropdown / pill list
    doesn't render. Anything invalid is silently dropped — better to under-
    apply than to write bogus state.
    """
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        log.warning("Architect reply was not JSON")
        return "", {}

    reply = str(data.get("reply", "")).strip()
    updates: dict[str, Any] = {}
    raw_updates = data.get("updates")
    if not isinstance(raw_updates, dict):
        return reply, updates

    # Free-text fields — trim, drop empty.
    for key in ("event_name", "event_date", "audience", "goal"):
        value = raw_updates.get(key)
        if isinstance(value, str) and value.strip():
            updates[key] = value.strip()

    # event_format — must match the catalogue exactly (UI renders pills).
    fmt = raw_updates.get("event_format")
    if isinstance(fmt, str) and fmt.strip():
        allowed = set(ctx.available_formats) or _VALID_FORMATS_FALLBACK
        if fmt.strip() in allowed:
            updates["event_format"] = fmt.strip()

    # locked_venue — must be in catalogue, or "" to clear.
    venue = raw_updates.get("locked_venue")
    if isinstance(venue, str):
        venue = venue.strip()
        if venue == "" or venue in ctx.available_venues:
            updates["locked_venue"] = venue

    # List-typed fields — keep only catalogue members, dedupe, preserve order.
    list_catalogues = {
        "locked_mentors": ctx.available_mentors,
        "locked_sponsors": ctx.available_sponsors,
        "locked_outreach": ctx.available_outreach,
        "enabled_tools": ctx.available_tools,
    }
    for key, catalogue in list_catalogues.items():
        value = raw_updates.get(key)
        if not isinstance(value, list):
            continue
        allowed = set(catalogue)
        cleaned: list[str] = []
        seen: set[str] = set()
        for item in value:
            if not isinstance(item, str):
                continue
            name = item.strip()
            if not name or name in seen:
                continue
            # Empty catalogue (frontend didn't pass one) → accept as-is.
            if allowed and name not in allowed:
                continue
            cleaned.append(name)
            seen.add(name)
        updates[key] = cleaned

    return reply, updates


def _parse_review_reply(raw: str) -> tuple[str, dict[str, Any]]:
    """Pull (reply, updates) out of the review chat's JSON response.

    `updates` only ever contains keys with valid, non-empty values, so the
    caller can splat it straight into ReviewFieldUpdates.
    """
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        log.warning("Review reply was not JSON")
        return "", {}

    reply = str(data.get("reply", "")).strip()
    updates: dict[str, Any] = {}
    raw_updates = data.get("updates")
    if isinstance(raw_updates, dict):
        title = raw_updates.get("title")
        if isinstance(title, str) and title.strip():
            updates["title"] = title.strip()
        description = raw_updates.get("description")
        if isinstance(description, str) and description.strip():
            updates["description"] = description.strip()[:350]
        tags = raw_updates.get("tags")
        if isinstance(tags, list):
            cleaned = [str(t).strip() for t in tags if str(t).strip()]
            # An explicit empty list is a valid edit (the user cleared tags).
            updates["tags"] = cleaned
        if raw_updates.get("visibility") in ("public", "private"):
            updates["visibility"] = raw_updates["visibility"]
    return reply, updates


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
