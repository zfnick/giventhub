from pydantic import BaseModel


class IntakeResult(BaseModel):
    intent: str
    sector: str
    goal: str


class RelationshipEvidence(BaseModel):
    entity_id: str
    entity_name: str
    relationship_path: list[str]
    evidence: str


class Recommendation(BaseModel):
    entity_id: str
    name: str
    score: int
    reason: str
    evidence: list[str]


class VerifiedRecommendation(Recommendation):
    confidence: float
    verification_status: str


class WorkspaceDraft(BaseModel):
    type: str
    title: str
    summary: str
    requires_approval: bool = True


class AgentResponse(BaseModel):
    intent: IntakeResult
    recommendations: list[VerifiedRecommendation]
    workspace_drafts: list[WorkspaceDraft]
