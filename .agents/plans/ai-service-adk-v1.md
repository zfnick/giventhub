# AI Service ADK V1 PR Plan

## Remote Branch Name

`feature/ai-service-adk-v1`

## Commit Message

`feat(ai-service): add ADK orchestrator prototype`

## PR Title

`Add ADK AI service prototype`

## PR Description

Adds the first Google ADK prototype for GITEventHub. The service uses a central orchestrator, stateless role agents, local sample ecosystem data, and mocked tools for relationship search, ranking, verification, and Workspace draft planning.

The implementation is intentionally mock-data driven so the AI workflow can be validated before wiring Firestore, Google OAuth, or Google Workspace APIs.

## Files To Upload

- `ai-service/.env.example`
- `ai-service/.gitignore`
- `ai-service/README.md`
- `ai-service/requirements.txt`
- `ai-service/git_eventhub_agent/__init__.py`
- `ai-service/git_eventhub_agent/agent.py`
- `ai-service/git_eventhub_agent/sample_data.py`
- `ai-service/git_eventhub_agent/schemas.py`
- `ai-service/git_eventhub_agent/tools.py`
- `.agents/plans/ai-service-adk-v1.md`
