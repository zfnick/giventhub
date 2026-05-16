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

import logging
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware

import schemas
from ai_client import AIStackClient, AIStackUnavailable
from deps import (
    AuthedUser,
    get_current_user,
    get_current_user_optional,
    get_settings,
)
from firestore_db import FirestoreDB
from gemini_client import GeminiClient

log = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    app.state.settings = settings
    app.state.db = FirestoreDB(
        project_id=settings.gcp_project,
        database=settings.firestore_database,
    )
    app.state.ai = AIStackClient(base_url=settings.ai_service_url)
    app.state.gemini = GeminiClient(
        project=settings.gcp_project,
        location=settings.gcp_location,
        api_key=settings.gemini_api_key,
    )
    log.info("Backend ready. AI stack configured: %s", app.state.ai.configured)
    yield
    await app.state.ai.close()


app = FastAPI(title="gieventhub API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
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

@app.post("/api/adapt", response_model=schemas.AdaptResponse)
async def adapt_playbook(
    req: schemas.AdaptRequest,
    user: AuthedUser = Depends(get_current_user_optional),
) -> schemas.AdaptResponse:
    """The Smart Fork — clone a playbook into the user's Workspace, customized.

    This is the demo headline. The friend's AI stack does the heavy lifting
    (read source playbook → clone Drive folder → tailor Docs/Forms/Sheets to
    the user's prompt → return a workspace URL).
    """
    if app.state.ai.configured and req.google_access_token:
        try:
            stack_prompt = (
                f"Fork the '{req.playbookTitle}' playbook for this user. "
                f"Customization request: {req.prompt}. "
                "Clone the Drive folder, copy templates (Docs, Sheets, Forms), "
                "and tailor copy to the request. Return workspaceUrl pointing at "
                "the cloned root folder."
            )
            payload = await app.state.ai.invoke(
                endpoint="adapt",
                oauth_token=req.google_access_token,
                prompt=stack_prompt,
                extra={"playbookId": req.playbook_id, "playbookTitle": req.playbookTitle},
            )
            return schemas.AdaptResponse(
                status="success",
                message=f"Adapted {req.playbookTitle}",
                workspaceUrl=payload.get("workspaceUrl", payload.get("workspace_url", "")),
                workspace_drafts=payload.get("workspace_drafts", []),
            )
        except AIStackUnavailable as exc:
            log.warning("adapt: falling back to stub (%s)", exc)

    return schemas.AdaptResponse(
        status="success",
        message=f"(stub) Adapted {req.playbookTitle}",
        workspaceUrl="https://drive.google.com/drive/folders/mock-folder-id",
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
    return schemas.CommitResponse(
        status="success",
        playbook_id=playbook.id,
        message=f"Saved {playbook.title}",
    )


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
    reply = await app.state.gemini.architect_reply(req)
    if not reply:
        reply = "On it — refining the draft now."
    return schemas.ArchitectChatResponse(status="success", reply=reply)


# ── Chat: /onboarding/review — "Anything I missed?" ──────────────────────────

@app.post("/api/chat/review", response_model=schemas.ReviewChatResponse)
async def chat_review(
    req: schemas.ReviewChatRequest,
    user: AuthedUser = Depends(get_current_user_optional),
) -> schemas.ReviewChatResponse:
    reply = await app.state.gemini.review_reply(req)
    if not reply:
        reply = "Noted! I've added that to the playbook."
    return schemas.ReviewChatResponse(status="success", reply=reply)


# ── Chat: /chat ecosystem graph ──────────────────────────────────────────────

@app.post("/api/chat/ecosystem", response_model=schemas.EcosystemChatResponse)
async def chat_ecosystem(
    req: schemas.EcosystemChatRequest,
    user: AuthedUser = Depends(get_current_user),
) -> schemas.EcosystemChatResponse:
    # Ground the chat in the real Firestore catalogue so factual questions
    # (count by venue, list by host, etc.) get answered with actual data.
    playbooks = app.state.db.list_public_playbooks(limit=200)
    reply, nodes, edges = await app.state.gemini.ecosystem_reply_and_graph(
        req, playbooks=playbooks,
    )
    if not nodes:
        nodes, edges = _fallback_graph()
    if not reply:
        reply = "I sketched a basic relationship graph from your query."
    return schemas.EcosystemChatResponse(
        status="success",
        reply=reply,
        nodes=nodes,
        edges=edges,
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
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
