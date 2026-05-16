from __future__ import annotations

import json

from .sample_data import RELATIONSHIPS, STARTUPS
from .schemas import (
    AgentResponse,
    IntakeResult,
    Recommendation,
    RelationshipEvidence,
    VerifiedRecommendation,
    WorkspaceDraft,
)


def classify_and_extract_request(message: str) -> dict:
    """Parse a GITEventHub request into intent, sector, and goal."""
    lowered = message.lower()
    sector = "climate-tech" if "climate" in lowered else "fintech" if "fintech" in lowered else "general"
    goal = "re-engagement" if any(word in lowered for word in ["reconnect", "follow-up", "outreach"]) else "discovery"
    intent = "reconnection_query" if goal == "re-engagement" else "relationship_query"
    return IntakeResult(intent=intent, sector=sector, goal=goal).model_dump()


def search_relationships(sector: str, goal: str) -> list[dict]:
    """Find relationship evidence for entities that match the requested sector."""
    startup_by_id = {startup["id"]: startup for startup in STARTUPS}
    results: list[RelationshipEvidence] = []
    for rel in RELATIONSHIPS:
        startup = startup_by_id[rel["entity_id"]]
        if sector != "general" and startup["sector"] != sector:
            continue
        path = [startup["name"], rel["event"], *rel["people"]]
        results.append(
            RelationshipEvidence(
                entity_id=startup["id"],
                entity_name=startup["name"],
                relationship_path=path,
                evidence=rel["evidence"],
            )
        )
    return [result.model_dump() for result in results]


def rank_candidates(evidence_json: str) -> list[dict]:
    """Rank candidates from relationship evidence JSON."""
    evidence = json.loads(evidence_json)
    ranked: list[Recommendation] = []
    for item in evidence:
        score = 86 if "follow-up" in item["evidence"].lower() else 78
        ranked.append(
            Recommendation(
                entity_id=item["entity_id"],
                name=item["entity_name"],
                score=score,
                reason=f"Strong ecosystem signal through {' -> '.join(item['relationship_path'])}.",
                evidence=[item["evidence"]],
            )
        )
    ranked.sort(key=lambda candidate: candidate.score, reverse=True)
    return [candidate.model_dump() for candidate in ranked]


def verify_recommendations(recommendations_json: str) -> list[dict]:
    """Verify recommendations only when they include supporting evidence."""
    recommendations = json.loads(recommendations_json)
    verified: list[VerifiedRecommendation] = []
    for rec in recommendations:
        has_evidence = bool(rec.get("evidence"))
        confidence = min(0.95, rec["score"] / 100) if has_evidence else 0.25
        verified.append(
            VerifiedRecommendation(
                **rec,
                confidence=confidence,
                verification_status="grounded" if has_evidence else "unsupported",
            )
        )
    return [rec.model_dump() for rec in verified]


def draft_workspace_actions(recommendations_json: str) -> list[dict]:
    """Create approval-required Google Workspace draft actions."""
    recommendations = json.loads(recommendations_json)
    drafts: list[WorkspaceDraft] = []
    for rec in recommendations[:3]:
        drafts.append(
            WorkspaceDraft(
                type="gmail_draft",
                title=f"Reconnect with {rec['name']}",
                summary=f"Draft a warm follow-up citing: {rec['evidence'][0]}",
            )
        )
        drafts.append(
            WorkspaceDraft(
                type="calendar_draft",
                title=f"Follow-up meeting with {rec['name']}",
                summary="Prepare a 30-minute reconnection invite for the ecosystem team.",
            )
        )
    return [draft.model_dump() for draft in drafts]


def run_reconnection_workflow(message: str) -> dict:
    """Run the full mocked GITEventHub workflow for local demos."""
    intent = classify_and_extract_request(message)
    evidence = search_relationships(intent["sector"], intent["goal"])
    recommendations = rank_candidates(json.dumps(evidence))
    verified = verify_recommendations(json.dumps(recommendations))
    drafts = draft_workspace_actions(json.dumps(verified))
    return AgentResponse(
        intent=IntakeResult(**intent),
        recommendations=[VerifiedRecommendation(**rec) for rec in verified],
        workspace_drafts=[WorkspaceDraft(**draft) for draft in drafts],
    ).model_dump()
