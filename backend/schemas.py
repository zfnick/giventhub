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
    # ID of the newly-created fork in Firestore — frontend navigates here so
    # the user lands on their adapted copy in My Playbooks.
    playbook_id: str = ""
    # Live Drive folder URL when the AI service provisioned assets; "" when
    # the AI service was unreachable / no Workspace token was supplied.
    workspaceUrl: str = ""
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
    """Minimal slice of `/event/new` state the AI needs to reason.

    `available_*` lists are the canonical catalogues the form lets the user
    pick from. The AI is required to pick subsets of these — never invent —
    so we forward whatever the frontend currently shows.
    """

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
    # Catalogues the AI is allowed to draw from — populated by the frontend
    # from its mock data so backend stays decoupled from the UI lists.
    available_formats: list[str] = []
    available_mentors: list[str] = []
    available_sponsors: list[str] = []
    available_venues: list[str] = []
    available_outreach: list[str] = []
    available_tools: list[str] = []


class ArchitectChatRequest(BaseModel):
    message: str
    history: list[ChatMessage] = []
    context: ArchitectContext = ArchitectContext()


class ArchitectFieldUpdates(BaseModel):
    """Field-level edits the AI wants applied to the /event/new form.

    Mirrors the `ReviewFieldUpdates` pattern — every field is optional and
    only the ones the AI is actually changing are populated. The frontend
    patches its local state with whatever is set.
    """

    event_name: str | None = None
    event_date: str | None = None       # ISO YYYY-MM-DD
    event_format: str | None = None
    audience: str | None = None
    goal: str | None = None
    locked_mentors: list[str] | None = None
    locked_sponsors: list[str] | None = None
    locked_venue: str | None = None
    locked_outreach: list[str] | None = None
    enabled_tools: list[str] | None = None


class ArchitectChatResponse(StatusEnvelope):
    reply: str
    updates: ArchitectFieldUpdates = ArchitectFieldUpdates()
    suggestions: dict[str, Any] = {}


class ReviewDraftState(BaseModel):
    """Current `/onboarding/review` form state the AI is allowed to edit."""

    title: str = ""
    description: str = ""
    tags: list[str] = []
    visibility: Literal["public", "private"] = "public"


class ReviewChatRequest(BaseModel):
    message: str
    history: list[ChatMessage] = []
    playbook_id: str | None = None
    file_name: str | None = None
    current: ReviewDraftState = ReviewDraftState()


class ReviewFieldUpdates(BaseModel):
    """Field-level edits the AI wants applied to the review form.

    Every field is optional — only the ones the user asked to change are
    populated. The frontend patches its form state with whatever is set.
    """

    title: str | None = None
    description: str | None = None
    tags: list[str] | None = None
    visibility: Literal["public", "private"] | None = None


class ReviewChatResponse(StatusEnvelope):
    reply: str
    updates: ReviewFieldUpdates = ReviewFieldUpdates()
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


# ── Smart Match (outcome-scoring learning loop) ──────────────────────────────

class MatchRequest(BaseModel):
    """A request for people recommendations, scored against past engagements."""

    query: str
    role: Literal["mentor", "sponsor", "judge", "speaker", "partner", "any"] = "any"
    history: list[ChatMessage] = []


class MatchCandidate(BaseModel):
    """One scored recommendation.

    Scores are derived from observed participation across the playbook
    catalogue — never invented. `evidence` lists the playbooks backing them.
    """

    name: str
    organization: str = ""
    role: str = ""
    fit_score: int = 0          # 0-100 — domain/role fit for this specific need
    engagement_score: int = 0   # 0-100 — track record across past engagements
    track_record: str = ""      # one-line summary of past engagement outcomes
    evidence: list[str] = []    # playbook titles that back the scores
    reason: str = ""            # why this candidate, grounded in evidence


class MatchResponse(StatusEnvelope):
    reply: str = ""
    learned_from: int = 0       # number of past playbooks (engagements) scored
    candidates: list[MatchCandidate] = []


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
