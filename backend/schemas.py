"""Pydantic wire schemas — the frontend ↔ backend contract.

Keep these in sync with the TypeScript shapes the frontend expects.
Field names use snake_case except where the frontend already sends camelCase
(those are aliased to remain backwards-compatible with the existing client).
"""
from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


# ── Common ───────────────────────────────────────────────────────────────────

class StatusEnvelope(BaseModel):
    """Every endpoint wraps responses with `status: "success" | "error"`."""

    status: Literal["success", "error"] = "success"
    message: str | None = None


# ── /api/scan ────────────────────────────────────────────────────────────────

class ScanRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    userId: str | None = None
    eventName: str | None = None
    google_access_token: str | None = Field(default=None, alias="googleAccessToken")


class ScanAsset(BaseModel):
    name: str
    type: str
    color: str = "zinc"


class ScanEventDetails(BaseModel):
    title: str
    category: str
    last_active: str
    assets: list[ScanAsset]


class ScanResponse(StatusEnvelope):
    event_detected: bool
    event_details: ScanEventDetails


# ── /api/adapt ───────────────────────────────────────────────────────────────

class AdaptRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    prompt: str
    playbookTitle: str
    playbook_id: str | None = Field(default=None, alias="playbookId")
    google_access_token: str | None = Field(default=None, alias="googleAccessToken")


class AdaptResponse(StatusEnvelope):
    workspaceUrl: str
    workspace_drafts: list[dict[str, Any]] = []


# ── /api/commit ──────────────────────────────────────────────────────────────

class CommitRequest(BaseModel):
    title: str
    description: str
    is_public: bool = True
    commit_message: str = "Initial save"
    tags: list[str] = []
    timing: Literal["past", "upcoming"] = "past"
    forked_from: str | None = None


class CommitResponse(StatusEnvelope):
    playbook_id: str


# ── Playbooks ────────────────────────────────────────────────────────────────

class PlaybookContext(BaseModel):
    challenge: str = ""
    targetAudience: str = ""
    venue: str = ""
    techStack: str = ""


class PlaybookAsset(BaseModel):
    name: str
    type: str
    icon: str | None = None


class PlaybookParticipant(BaseModel):
    """Anyone involved in running or attending the event.

    `role` is free-text (e.g. Organizer, Mentor, Judge, Speaker, Sponsor,
    Attendee) so the knowledge tree can group everyone under one roster.
    """

    name: str
    role: str = ""
    organization: str = ""
    email: str = ""


class Playbook(BaseModel):
    id: str
    title: str
    author: str = ""
    author_uid: str | None = None
    description: str = ""
    attendees: str = ""
    duration: str = ""
    category: str = ""
    stats: str = ""
    visibility: Literal["public", "private"] = "public"
    tags: list[str] = []
    context: PlaybookContext = PlaybookContext()
    assets: list[PlaybookAsset] = []
    participants: list[PlaybookParticipant] = []
    features: list[str] = []
    forked_from: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


class PlaybookList(BaseModel):
    playbooks: list[Playbook]


# ── Chat surfaces ────────────────────────────────────────────────────────────

class ChatMessage(BaseModel):
    role: Literal["user", "ai"]
    text: str


class ArchitectContext(BaseModel):
    """Minimal slice of `/event/new` state the AI needs to reason."""

    step: Literal["mode", "playbook", "context", "similar", "plan"] = "mode"
    mode: Literal["playbook", "scratch"] | None = None
    forked_playbook_id: str | None = None
    event_name: str = ""
    event_date: str = ""
    event_format: str = ""
    audience: str = ""
    goal: str = ""
    locked_mentors: list[str] = []
    locked_sponsors: list[str] = []
    locked_venue: str = ""
    locked_outreach: list[str] = []
    enabled_tools: list[str] = []


class ArchitectChatRequest(BaseModel):
    message: str
    history: list[ChatMessage] = []
    context: ArchitectContext = ArchitectContext()


class ArchitectChatResponse(StatusEnvelope):
    reply: str
    suggestions: dict[str, Any] = {}


class ReviewChatRequest(BaseModel):
    message: str
    history: list[ChatMessage] = []
    playbook_id: str | None = None
    file_name: str | None = None


class ReviewChatResponse(StatusEnvelope):
    reply: str
    extracted_assets: list[PlaybookAsset] = []


class GraphNode(BaseModel):
    id: str
    label: str
    type: Literal["event", "shared", "people", "tool"] = "shared"
    x: float = 0
    y: float = 0


class GraphEdge(BaseModel):
    id: str
    source: str
    target: str
    label: str = ""


class EcosystemChatRequest(BaseModel):
    query: str
    history: list[ChatMessage] = []


class EcosystemChatResponse(StatusEnvelope):
    reply: str
    nodes: list[GraphNode]
    edges: list[GraphEdge]


# ── Knowledge tree (PlaybookFlow graph) ──────────────────────────────────────

class GraphItem(BaseModel):
    name: str
    role: str = ""
    detail: str = ""


class GraphCategory(BaseModel):
    id: str
    label: str
    kind: Literal["people", "tool", "sponsor", "asset", "theme"] = "theme"
    items: list[GraphItem]


class PlaybookGraph(BaseModel):
    root_label: str
    categories: list[GraphCategory]


class PlaybookDraft(BaseModel):
    """In-flight playbook data used to generate a graph before commit."""

    title: str = ""
    description: str = ""
    category: str = ""
    tags: list[str] = []
    context: PlaybookContext | None = None
    assets: list[PlaybookAsset] = []
    features: list[str] = []


class GraphRequest(BaseModel):
    playbook_id: str | None = None
    draft: PlaybookDraft | None = None


# ── Workspace actions (proxy → friend's AI stack) ────────────────────────────

class WorkspaceCloneRequest(BaseModel):
    playbook_id: str
    google_access_token: str
    customization_prompt: str | None = None


class WorkspaceInviteRequest(BaseModel):
    google_access_token: str
    mentor_names: list[str]
    event_name: str
    event_date: str = ""
    custom_note: str | None = None


class WorkspaceRunRequest(BaseModel):
    """Escape hatch: forward an arbitrary prompt to the AI stack."""

    google_access_token: str
    prompt: str
    files: list[dict[str, Any]] | None = None


class WorkspaceActionResponse(StatusEnvelope):
    result: dict[str, Any] = {}


# ── Auth helper ──────────────────────────────────────────────────────────────

class AuthedUser(BaseModel):
    """Re-exported for route handlers that don't want to import from deps."""

    uid: str
    email: str | None = None
    name: str | None = None
