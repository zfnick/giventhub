from pathlib import Path

from dotenv import load_dotenv
from google.adk.agents import LlmAgent

from .tools import (
    classify_and_extract_request,
    draft_workspace_actions,
    rank_candidates,
    run_reconnection_workflow,
    search_relationships,
    verify_recommendations,
)


load_dotenv(Path(__file__).resolve().parents[1] / ".env")

intake_agent = LlmAgent(
    name="intake_agent",
    model="gemini-3.1-flash-lite",
    instruction="Parse user intent, entities, sector, and goal. Return concise structured JSON.",
)

relationship_agent = LlmAgent(
    name="relationship_agent",
    model="gemini-3-flash-preview",
    instruction="Trace grounded ecosystem relationships using only provided tool evidence.",
)

recommendation_agent = LlmAgent(
    name="recommendation_agent",
    model="gemini-3-flash-preview",
    instruction="Rank ecosystem candidates and propose next actions using evidence.",
)

verification_agent = LlmAgent(
    name="verification_agent",
    model="gemini-3.1-pro-preview",
    instruction="Reject unsupported claims. Assign confidence only from provided evidence.",
)

workspace_agent = LlmAgent(
    name="workspace_agent",
    model="gemini-2.5-flash",
    instruction="Plan Google Workspace drafts only. Never send, schedule, post, or share.",
)

root_agent = LlmAgent(
    name="git_eventhub_orchestrator",
    model="gemini-3-flash-preview",
    description="Central orchestrator for GITEventHub ecosystem intelligence workflows.",
    instruction=(
        "You are the GITEventHub central orchestrator. Agents are stateless; tools provide "
        "the temporary memory. For reconnection, relationship, recommendation, or workspace "
        "draft requests, call run_reconnection_workflow first. Present only grounded evidence, "
        "confidence, and approval-required Workspace drafts. Do not claim any real Gmail, "
        "Calendar, Drive, Docs, Sheets, Forms, or Chat action has been executed."
    ),
    tools=[
        run_reconnection_workflow,
        classify_and_extract_request,
        search_relationships,
        rank_candidates,
        verify_recommendations,
        draft_workspace_actions,
    ],
    sub_agents=[
        intake_agent,
        relationship_agent,
        recommendation_agent,
        verification_agent,
        workspace_agent,
    ],
)
