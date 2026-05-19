"""gieventhub backend — FastAPI app.

Architecture:
  Frontend (Next.js, :3000)
    ↓
  This backend (FastAPI, :8000)
    ├──> Firestore (playbook persistence)
    ├──> Gemini direct (relationship reasoning, chat replies)
    └──> Friend's AI stack (Google Workspace mutations — clone, invite, etc.)

Auth: Firebase ID token in `Authorization: Bearer <token>` (verified via
firebase-admin). For Workspace mutations the frontend additionally passes the
user's Google OAuth access token in the request body — this token is forwarded
verbatim to the friend's AI stack.
"""
from __future__ import annotations

import asyncio
import json
import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

import schemas
from ai_client import AIStackClient, AIStackUnavailable
from deps import (
    AuthedUser,
    get_current_user,
    get_current_user_optional,
    get_settings,
)
from cache import TTLCache, normalize_query
from firestore_db import FirestoreDB
from gemini_client import GeminiClient
from neo4j_client import Neo4jClient

log = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    app.state.settings = settings
    app.state.db = FirestoreDB(
        project_id=settings.gcp_project,
        database=settings.firestore_database,
    )
    # Adapt runs ~5 sequential Workspace creates with content — easily blows
    # past the 60s default. Give the ADK agent room to finish.
    app.state.ai = AIStackClient(base_url=settings.ai_service_url, timeout_seconds=240.0)
    app.state.gemini = GeminiClient(
        project=settings.gcp_project,
        location=settings.gcp_location,
        api_key=settings.gemini_api_key,
    )
    # Neo4j is optional — empty NEO4J_URI puts the client into a no-op mode
    # and the ecosystem chat falls back to the older Gemini-only path.
    app.state.graph = Neo4jClient(
        uri=settings.neo4j_uri,
        username=settings.neo4j_username,
        password=settings.neo4j_password,
    )
    # Process-local response cache for /api/chat/ecosystem. Version bumps on
    # every playbook write so cached entries are never served past a change
    # to the catalogue. 10-min TTL is a safety net.
    app.state.cache = TTLCache(max_size=256, ttl_seconds=600.0)
    log.info(
        "Backend ready. AI stack configured: %s. Neo4j enabled: %s",
        app.state.ai.configured, not app.state.graph.disabled,
    )
    yield
    await app.state.ai.close()
    app.state.graph.close()


app = FastAPI(title="gieventhub API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:3001",
        "http://127.0.0.1:3001",
        "https://frontend-1009420638811.asia-southeast1.run.app",
        "https://frontend-mz2tiihnsa-as.a.run.app",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Health ───────────────────────────────────────────────────────────────────

@app.get("/health")
async def health() -> dict:
    return {
        "status": "ok",
        "ai_stack_configured": app.state.ai.configured,
    }


# ── /api/scan ────────────────────────────────────────────────────────────────

@app.post("/api/scan", response_model=schemas.ScanResponse)
async def scan_workspace(
    req: schemas.ScanRequest,
    user: AuthedUser = Depends(get_current_user_optional),
) -> schemas.ScanResponse:
    """Detect an event cluster in the user's Drive.

    If the AI stack is configured AND we have the user's Google OAuth token,
    forward there. Otherwise return a fully-formed stub so the demo path works.
    """
    event_name = req.eventName or "Stanford AI Demo Day 2026"

    if app.state.ai.configured and req.google_access_token:
        try:
            payload = await app.state.ai.invoke(
                endpoint="scan",
                oauth_token=req.google_access_token,
                prompt=(
                    f"Identify the most recent event-related cluster of files in "
                    f"this user's Drive. Working title hint: '{event_name}'. "
                    "Return event_details with title, category, last_active, and "
                    "an assets list (name, type, color)."
                ),
            )
            return schemas.ScanResponse(**payload)
        except AIStackUnavailable as exc:
            log.warning("scan: falling back to stub (%s)", exc)

    return _scan_stub(event_name)


def _scan_stub(event_name: str) -> schemas.ScanResponse:
    return schemas.ScanResponse(
        status="success",
        event_detected=True,
        event_details=schemas.ScanEventDetails(
            title=event_name,
            category="Hackathon",
            last_active="2 days ago",
            assets=[
                schemas.ScanAsset(name="Demo Day Registration", type="Form", color="blue"),
                schemas.ScanAsset(name="Master Roster & Check-in", type="Sheet", color="green"),
                schemas.ScanAsset(name="Judge Scoring Rubric", type="Doc", color="indigo"),
                schemas.ScanAsset(name="Opening Ceremony Deck", type="Slide", color="yellow"),
            ],
        ),
    )


# ── /api/adapt ───────────────────────────────────────────────────────────────

def _build_adapt_prompt(source: schemas.Playbook, customization: str) -> str:
    """Compose the ADK agent prompt for a Smart Fork.

    The agent has create-with-content tools (create_google_doc(content=…),
    create_google_form(questions_json=…), create_google_sheet(headers_json=…)),
    so we feed it the source's full structure + the customization and tell it
    to author each asset's content end-to-end. The previous prompt just said
    "clone the Drive folder", which the agent interpreted as making an empty
    folder + empty files (there is no source Drive folder to copy from — the
    template lives in Firestore).
    """
    ctx = source.context

    asset_lines = "\n".join(
        f"  - {a.name} ({a.type})" for a in source.assets
    ) or (
        "  (none listed in the source — infer the standard "
        f"set for a '{source.category or 'event'}')"
    )

    feature_lines = "\n".join(f"  - {f}" for f in source.features) or "  (none listed)"

    # Roles roster — dedup while keeping source order so the agent can pre-build
    # appropriate sheet columns / form questions for the people involved.
    seen: set[str] = set()
    unique_roles: list[str] = []
    for p in source.participants:
        if p.role and p.role not in seen:
            seen.add(p.role)
            unique_roles.append(p.role)
    role_lines = "\n".join(f"  - {r}" for r in unique_roles) or "  (none listed)"

    customization_block = (customization or "").strip() or (
        "(no specific customization — adapt the playbook for a clean fork "
        "but still personalize names/titles to feel new)"
    )

    return (
        "You are forking a Google Workspace event playbook into the organizer's "
        "own Drive. The source playbook lives in our database — it is a "
        "*template description*, NOT a set of existing Drive files. You must "
        "CREATE every asset fresh, with real content authored to match the "
        "customization request.\n\n"
        "SOURCE PLAYBOOK\n"
        f"  - Title: {source.title}\n"
        f"  - Category: {source.category or 'event'}\n"
        f"  - Typical attendees: {source.attendees or 'unspecified'}\n"
        f"  - Duration: {source.duration or 'unspecified'}\n"
        f"  - Description: {source.description or '(none)'}\n"
        f"  - Challenge / theme: {ctx.challenge or '(none)'}\n"
        f"  - Target audience: {ctx.targetAudience or '(none)'}\n"
        f"  - Venue notes: {ctx.venue or '(none)'}\n"
        f"  - Tech stack notes: {ctx.techStack or '(none)'}\n\n"
        "  Assets to recreate, each as a fresh Workspace file:\n"
        f"{asset_lines}\n\n"
        "  Features the assets must support:\n"
        f"{feature_lines}\n\n"
        "  Roles to plan for (use for sheet columns / form options / doc sections):\n"
        f"{role_lines}\n\n"
        "CUSTOMIZATION REQUEST from the organizer:\n"
        f'"""\n{customization_block}\n"""\n\n'
        "TASK — execute every step, do not just plan. Pass execute=True on every tool call.\n\n"
        "1. Create ONE Google Drive folder for this customized event via drive_agent. "
        "Name it so the customization is visible (incorporate the new audience, "
        "theme, or location). Capture the folder's resource_id.\n\n"
        "2. For EACH asset listed above, create a fresh file inside that folder "
        "by passing folder_id to the create call:\n"
        "   - 'Google Forms' → create_google_form with questions_json tailored to "
        "the request (e.g. high-school registration asks grade/school, not "
        "generic 'What are you building?').\n"
        "   - 'Google Sheets' → create_google_sheet with headers_json that "
        "matches the asset's purpose (roster columns, judging criteria, etc.).\n"
        "   - 'Google Docs' → create_google_doc with a non-empty `content` "
        "argument holding the full body text (run-of-show, rulebook, rubric — "
        "real sentences, not placeholders).\n"
        "   - 'Google Slides' → create_google_slide_deck, then update_google_slide_deck "
        "to populate slides with titled content.\n\n"
        "3. Every file MUST contain real, customization-aware content. The user "
        "will open each file and read it — empty files or generic placeholder "
        "text (\"TBD\", \"Sample question\", \"Lorem ipsum\") count as a failure. "
        "Tailor names, questions, columns, and prose to the customization request "
        "and the source's category/audience.\n\n"
        "4. Return the Drive folder URL as workspaceUrl in your final summary.\n"
    )


@app.post("/api/adapt", response_model=schemas.AdaptResponse)
async def adapt_playbook(
    req: schemas.AdaptRequest,
    user: AuthedUser = Depends(get_current_user),
) -> schemas.AdaptResponse:
    """The Smart Fork — clone a playbook into the user's Workspace, customized.

    Two-phase so the user always sees a result:
      1. Persist a fork in Firestore against this user (always — Firestore is
         our source of truth, so My Playbooks reflects reality regardless of
         whether the AI service is reachable).
      2. If we have a Google OAuth token AND the AI service is wired up,
         attempt to provision the real Workspace assets and store the live
         Drive URL on the fork.

    The frontend gets the fork's id back so it can navigate the user there.
    """
    # ── 1. Resolve the source playbook ─────────────────────────────────────
    source: schemas.Playbook | None = None
    if req.playbook_id:
        source = app.state.db.get_playbook(req.playbook_id)
    if source is None:
        # Backwards-compat — older clients only sent the title.
        for p in app.state.db.list_public_playbooks(limit=200):
            if p.title == req.playbookTitle:
                source = p
                break
    if source is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Source playbook not found",
        )

    # ── 2. Persist the fork in Firestore ───────────────────────────────────
    # Private by default — it's the user's working copy. They can publish
    # later from the playbook detail page.
    fork = app.state.db.create_playbook(
        author_uid=user.uid,
        author_name=user.name or user.email or "Anonymous",
        title=source.title,
        description=req.prompt.strip() or source.description,
        is_public=False,
        tags=source.tags,
        forked_from=source.id,
        timing="upcoming",
        extra={
            "attendees": source.attendees,
            "duration": source.duration,
            "category": source.category,
            "stats": "Forked",
            "context": source.context.model_dump(),
            "assets": [a.model_dump() for a in source.assets],
            "participants": [p.model_dump() for p in source.participants],
            "features": source.features,
        },
    )
    _mirror_to_neo4j(fork)

    # ── 3. Best-effort: provision the real Workspace assets ────────────────
    workspace_url = ""
    workspace_drafts: list[dict] = []
    message = f"Forked '{source.title}' into your playbooks."

    if not req.google_access_token:
        message += " Sign in with Google again to provision the Workspace assets."
    elif not app.state.ai.configured:
        message += " AI service not configured — workspace assets were not provisioned."
    else:
        stack_prompt = _build_adapt_prompt(source, req.prompt)
        try:
            payload = await app.state.ai.invoke(
                endpoint="adapt",
                oauth_token=req.google_access_token,
                prompt=stack_prompt,
                extra={"playbookId": source.id, "playbookTitle": source.title},
            )
            workspace_url = payload.get("workspaceUrl") or payload.get("workspace_url", "")
            workspace_drafts = payload.get("workspace_drafts", []) or []
            if workspace_url:
                # Stamp the live Drive URL onto the fork so the playbook
                # detail page can deep-link the user back to their workspace.
                app.state.db.playbooks.document(fork.id).update({
                    "workspace_url": workspace_url,
                    "workspace_drafts": workspace_drafts,
                })
                message = f"Forked '{source.title}' and provisioned your Google Workspace."
            else:
                message += " AI ran but did not return a workspace URL."
        except AIStackUnavailable as exc:
            log.warning("adapt: AI service unavailable (%s)", exc)
            message += " Workspace provisioning failed — you can retry from the playbook page."

    return schemas.AdaptResponse(
        status="success",
        message=message,
        playbook_id=fork.id,
        workspaceUrl=workspace_url,
        workspace_drafts=workspace_drafts,
    )


# ── /api/adapt/stream — real-time progress for the Smart Fork ────────────────

@app.post("/api/adapt/stream")
async def adapt_playbook_stream(
    req: schemas.AdaptRequest,
    user: AuthedUser = Depends(get_current_user),
) -> StreamingResponse:
    """Streaming variant of /api/adapt.

    Emits NDJSON to the frontend so it can render a live progress feed:
      - `{type: "fork_created", playbook_id}` first, so the UI knows where to
        navigate even if Workspace provisioning later fails.
      - then every tool_call / tool_result the ADK agent produces (e.g.
        `create_drive_folder`, `create_google_doc`) as it happens.
      - finally `{type: "final", workspaceUrl}` after the agent settles.

    All the same persistence rules as /api/adapt apply — the fork is always
    saved in Firestore, Workspace provisioning is best-effort.
    """
    # ── 1. Resolve the source playbook ─────────────────────────────────────
    source: schemas.Playbook | None = None
    if req.playbook_id:
        source = app.state.db.get_playbook(req.playbook_id)
    if source is None:
        for p in app.state.db.list_public_playbooks(limit=200):
            if p.title == req.playbookTitle:
                source = p
                break
    if source is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Source playbook not found",
        )

    # ── 2. Persist the fork in Firestore (always) ──────────────────────────
    fork = app.state.db.create_playbook(
        author_uid=user.uid,
        author_name=user.name or user.email or "Anonymous",
        title=source.title,
        description=req.prompt.strip() or source.description,
        is_public=False,
        tags=source.tags,
        forked_from=source.id,
        timing="upcoming",
        extra={
            "attendees": source.attendees,
            "duration": source.duration,
            "category": source.category,
            "stats": "Forked",
            "context": source.context.model_dump(),
            "assets": [a.model_dump() for a in source.assets],
            "participants": [p.model_dump() for p in source.participants],
            "features": source.features,
        },
    )
    _mirror_to_neo4j(fork)

    # Snapshot the values needed inside the generator — `req` and `source`
    # are still in scope, but capturing keeps the closure tight.
    source_id = source.id
    source_title = source.title
    fork_id = fork.id
    google_token = req.google_access_token
    stack_prompt = _build_adapt_prompt(source, req.prompt)
    ai_configured = app.state.ai.configured
    ai = app.state.ai
    db = app.state.db

    async def gen() -> AsyncIterator[bytes]:
        def emit(obj: dict) -> bytes:
            return (json.dumps(obj) + "\n").encode("utf-8")

        # First chunk — the fork id, so the UI can navigate even on failure.
        yield emit({"type": "fork_created", "playbook_id": fork_id, "title": source_title})

        if not google_token:
            yield emit({
                "type": "skipped",
                "reason": "Sign in with Google again to provision the Workspace assets.",
            })
            yield emit({"type": "final", "workspaceUrl": "", "playbook_id": fork_id})
            return
        if not ai_configured:
            yield emit({
                "type": "skipped",
                "reason": "AI service not configured — workspace assets were not provisioned.",
            })
            yield emit({"type": "final", "workspaceUrl": "", "playbook_id": fork_id})
            return

        workspace_url = ""
        drafts: list[dict] = []
        try:
            async for evt in ai.stream(
                endpoint="adapt-stream",
                oauth_token=google_token,
                prompt=stack_prompt,
                extra={"playbookId": source_id, "playbookTitle": source_title},
            ):
                if evt.get("type") == "final":
                    workspace_url = evt.get("workspaceUrl") or ""
                if evt.get("type") == "tool_result":
                    drafts.append({
                        "name": evt.get("name"),
                        "title": evt.get("title"),
                        "url": evt.get("url"),
                    })
                yield emit(evt)
        except AIStackUnavailable as exc:
            log.warning("adapt-stream: AI service unavailable (%s)", exc)
            yield emit({
                "type": "error",
                "detail": "Workspace provisioning failed — you can retry from the playbook page.",
            })
            yield emit({"type": "final", "workspaceUrl": "", "playbook_id": fork_id})
            return

        # Stamp the live Drive URL onto the fork so the playbook detail page
        # can deep-link the user back to their workspace.
        if workspace_url:
            try:
                db.playbooks.document(fork_id).update({
                    "workspace_url": workspace_url,
                    "workspace_drafts": drafts,
                })
            except Exception:  # noqa: BLE001 — best-effort persistence
                log.exception("adapt-stream: failed to stamp workspace_url on fork")

        # Re-emit final with the fork id so the UI has both in one place.
        yield emit({
            "type": "final",
            "workspaceUrl": workspace_url,
            "playbook_id": fork_id,
        })

    return StreamingResponse(
        gen(),
        media_type="application/x-ndjson",
        headers={"X-Accel-Buffering": "no", "Cache-Control": "no-cache"},
    )


# ── /api/commit ──────────────────────────────────────────────────────────────

@app.post("/api/commit", response_model=schemas.CommitResponse)
async def commit_playbook(
    req: schemas.CommitRequest,
    user: AuthedUser = Depends(get_current_user),
) -> schemas.CommitResponse:
    """Persist a new playbook to Firestore."""
    playbook = app.state.db.create_playbook(
        author_uid=user.uid,
        author_name=user.name or user.email or "Anonymous",
        title=req.title,
        description=req.description,
        is_public=req.is_public,
        tags=req.tags,
        forked_from=req.forked_from,
        timing=req.timing,
    )
    _mirror_to_neo4j(playbook)
    return schemas.CommitResponse(
        status="success",
        playbook_id=playbook.id,
        message=f"Saved {playbook.title}",
    )


def _mirror_to_neo4j(playbook: schemas.Playbook) -> None:
    """Best-effort write-through of a fresh playbook into the Neo4j index.

    Never raises — Firestore is the source of truth, the graph is a derived
    index. A Neo4j outage must not break the user-facing write path.

    Also bumps the response cache version: the catalogue just changed, so
    every cached `/api/chat/ecosystem` answer needs to be re-derived.
    """
    try:
        app.state.graph.upsert_playbook(playbook)
    except Exception:  # noqa: BLE001
        log.exception("neo4j: write-through failed for %s", playbook.id)
    app.state.cache.invalidate()


# ── Playbooks (read) ─────────────────────────────────────────────────────────

@app.get("/api/playbooks", response_model=schemas.PlaybookList)
async def list_playbooks() -> schemas.PlaybookList:
    return schemas.PlaybookList(playbooks=app.state.db.list_public_playbooks())


@app.get("/api/playbooks/me", response_model=schemas.PlaybookList)
async def list_my_playbooks(
    user: AuthedUser = Depends(get_current_user),
) -> schemas.PlaybookList:
    return schemas.PlaybookList(playbooks=app.state.db.list_user_playbooks(user.uid))


@app.get("/api/playbooks/{playbook_id}", response_model=schemas.Playbook)
async def get_playbook(playbook_id: str) -> schemas.Playbook:
    playbook = app.state.db.get_playbook(playbook_id)
    if not playbook:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Playbook not found")
    return playbook


@app.post("/api/playbooks/graph", response_model=schemas.PlaybookGraph)
async def generate_playbook_graph(
    req: schemas.GraphRequest,
) -> schemas.PlaybookGraph:
    """Generate a dynamic knowledge tree for a playbook.

    Accepts either a `playbook_id` (loaded from Firestore) or an in-flight
    `draft` (used directly — for the review screen before commit).
    """
    playbook: schemas.Playbook | None = None
    if req.playbook_id:
        playbook = app.state.db.get_playbook(req.playbook_id)
        if not playbook:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Playbook not found",
            )
    if playbook is None and req.draft is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Provide playbook_id or draft",
        )
    return await app.state.gemini.playbook_graph(playbook=playbook, draft=req.draft)


# ── Chat: /event/new Event Architect ─────────────────────────────────────────

@app.post("/api/chat/event-architect", response_model=schemas.ArchitectChatResponse)
async def chat_event_architect(
    req: schemas.ArchitectChatRequest,
    user: AuthedUser = Depends(get_current_user_optional),
) -> schemas.ArchitectChatResponse:
    reply, updates = await app.state.gemini.architect_reply(req)
    if not reply:
        reply = "On it — refining the draft now."
    return schemas.ArchitectChatResponse(
        status="success",
        reply=reply,
        updates=schemas.ArchitectFieldUpdates(**updates),
    )


# ── Chat: /onboarding/review — "Anything I missed?" ──────────────────────────

@app.post("/api/chat/review", response_model=schemas.ReviewChatResponse)
async def chat_review(
    req: schemas.ReviewChatRequest,
    user: AuthedUser = Depends(get_current_user_optional),
) -> schemas.ReviewChatResponse:
    reply, updates = await app.state.gemini.review_reply(req)
    if not reply:
        reply = "Noted! I've added that to the playbook."
    return schemas.ReviewChatResponse(
        status="success",
        reply=reply,
        updates=schemas.ReviewFieldUpdates(**updates),
    )


# ── Chat: /chat ecosystem graph ──────────────────────────────────────────────

@app.post("/api/chat/ecosystem", response_model=schemas.EcosystemChatResponse)
async def chat_ecosystem(
    req: schemas.EcosystemChatRequest,
    user: AuthedUser = Depends(get_current_user),
) -> schemas.EcosystemChatResponse:
    """Neo4j-backed when configured: one Cypher query for the subgraph + one
    Gemini call for the prose reply. Falls back to the older Gemini-only path
    (two sequential LLM calls, model invents the graph) when Neo4j is disabled
    or returns no matches.

    Responses are cached on a normalized query key — repeated identical
    queries return instantly. The cache is version-tagged: any playbook write
    bumps the version (see `_mirror_to_neo4j`), so cached entries can never
    outlive a change to the catalogue.
    """
    cache_key = normalize_query(req.query)
    cached = app.state.cache.get(cache_key)
    if cached is not None:
        return cached

    if not app.state.graph.disabled:
        # Cypher in tens of ms, then a single grounded Gemini call. Compared
        # to the legacy path (model generates a graph with thinking=high on
        # a 12k-token JSON response) this is 3-5x faster end-to-end.
        nodes, edges = await asyncio.to_thread(
            app.state.graph.ecosystem_subgraph, req.query,
        )
        if nodes:
            reply = await app.state.gemini.ecosystem_reply_from_subgraph(
                req, nodes, edges,
            )
            if not reply:
                reply = "I found these connected playbooks in our relationship index."
            response = schemas.EcosystemChatResponse(
                status="success", reply=reply, nodes=nodes, edges=edges,
            )
            app.state.cache.set(cache_key, response)
            return response

    # Fallback: Neo4j disabled or empty. Use the older Gemini-only path so
    # the demo still works against a fresh DB.
    playbooks = app.state.db.list_public_playbooks(limit=200)
    reply, nodes, edges = await app.state.gemini.ecosystem_reply_and_graph(
        req, playbooks=playbooks,
    )
    if not nodes:
        nodes, edges = _fallback_graph()
    if not reply:
        reply = "I sketched a basic relationship graph from your query."
    response = schemas.EcosystemChatResponse(
        status="success",
        reply=reply,
        nodes=nodes,
        edges=edges,
    )
    app.state.cache.set(cache_key, response)
    return response


# ── Smart Match: outcome-scoring learning loop ───────────────────────────────

@app.post("/api/match/recommend", response_model=schemas.MatchResponse)
async def match_recommend(
    req: schemas.MatchRequest,
    user: AuthedUser = Depends(get_current_user),
) -> schemas.MatchResponse:
    """Recommend people for a new need, scored against past engagements.

    Every public playbook is treated as a past engagement record. The scorer
    mines that history so recommendations improve as more engagements
    accumulate — the platform's learning loop.
    """
    playbooks = app.state.db.list_public_playbooks(limit=200)
    reply, candidates = await app.state.gemini.recommend_matches(req, playbooks)
    if not reply:
        reply = (
            "Here are the strongest matches from past engagement history."
            if candidates
            else "I couldn't find enough past engagement data to score a match yet."
        )
    return schemas.MatchResponse(
        status="success",
        reply=reply,
        learned_from=len(playbooks),
        candidates=candidates,
    )


def _fallback_graph() -> tuple[list[schemas.GraphNode], list[schemas.GraphEdge]]:
    nodes = [
        schemas.GraphNode(id="e1", label="Event A", type="event", x=0, y=0),
        schemas.GraphNode(id="e2", label="Event B", type="event", x=400, y=0),
        schemas.GraphNode(id="s1", label="Shared Theme", type="shared", x=200, y=-120),
    ]
    edges = [
        schemas.GraphEdge(id="e1-s1", source="e1", target="s1", label="relates to"),
        schemas.GraphEdge(id="e2-s1", source="e2", target="s1", label="relates to"),
    ]
    return nodes, edges


# ── Workspace mutations (proxy → friend's AI stack) ──────────────────────────

@app.post("/api/workspace/clone-playbook", response_model=schemas.WorkspaceActionResponse)
async def workspace_clone_playbook(
    req: schemas.WorkspaceCloneRequest,
    user: AuthedUser = Depends(get_current_user),
) -> schemas.WorkspaceActionResponse:
    """Clone a playbook's Workspace assets (Drive folder + Docs + Sheets + Forms)
    into the user's own Workspace."""
    playbook = app.state.db.get_playbook(req.playbook_id)
    if not playbook:
        raise HTTPException(status_code=404, detail="Playbook not found")

    asset_summary = ", ".join(f"{a.name} ({a.type})" for a in playbook.assets) or "(no assets)"
    prompt = (
        f"Clone the '{playbook.title}' playbook into this user's Google Drive. "
        f"Source assets to recreate: {asset_summary}. "
        f"Tech stack reference: {playbook.context.techStack}. "
    )
    if req.customization_prompt:
        prompt += f"Customization request: {req.customization_prompt}. "
    prompt += "Return the cloned Drive root folder URL."

    return await _proxy_workspace("clone-playbook", req.google_access_token, prompt)


@app.post("/api/workspace/invite-mentors", response_model=schemas.WorkspaceActionResponse)
async def workspace_invite_mentors(
    req: schemas.WorkspaceInviteRequest,
    user: AuthedUser = Depends(get_current_user),
) -> schemas.WorkspaceActionResponse:
    """Send mentor invitation emails via Gmail + create Calendar holds."""
    names = ", ".join(req.mentor_names)
    prompt = (
        f"Send invite emails to these mentors for '{req.event_name}': {names}. "
        f"Event date: {req.event_date or 'TBD'}. "
        "Use a warm, concise template. Include event date and ask for confirmation. "
    )
    if req.custom_note:
        prompt += f"Custom note from organizer: {req.custom_note}. "
    prompt += "Return per-mentor send status."

    return await _proxy_workspace("invite-mentors", req.google_access_token, prompt)


@app.post("/api/workspace/run", response_model=schemas.WorkspaceActionResponse)
async def workspace_run(
    req: schemas.WorkspaceRunRequest,
    user: AuthedUser = Depends(get_current_user),
) -> schemas.WorkspaceActionResponse:
    """Escape hatch — forward a raw prompt + optional files to the AI stack."""
    return await _proxy_workspace(
        "run", req.google_access_token, req.prompt, files=req.files,
    )


async def _proxy_workspace(
    endpoint: str,
    oauth_token: str,
    prompt: str,
    files: list[dict] | None = None,
) -> schemas.WorkspaceActionResponse:
    if not app.state.ai.configured:
        return schemas.WorkspaceActionResponse(
            status="error",
            message="AI_SERVICE_URL not configured — friend's AI stack is not yet wired up.",
        )
    try:
        result = await app.state.ai.invoke(
            endpoint=endpoint,
            oauth_token=oauth_token,
            prompt=prompt,
            files=files,
        )
    except AIStackUnavailable as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"AI stack unavailable: {exc}",
        ) from exc
    return schemas.WorkspaceActionResponse(status="success", result=result)


# ── Local entrypoint ─────────────────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8001, reload=True)
