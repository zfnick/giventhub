# AI Service ADK V1 PR Plan

## Remote Branch Name

Intermediate branch: `feature/ai-service-adk-v1`

Feature branches:

- `feature/ai-service-adk-core`
- `feature/ai-service-workspace-tools`

## PR Restructuring

This change is larger than 300 LOC, so split it into two PRs that both merge
into `feature/ai-service-adk-v1`. After both feature PRs land, open one final
small merge PR from `feature/ai-service-adk-v1` into `main`.

## PR 1: ADK Core

Commit Message:

`feat(ai-service): add ADK orchestrator core`

PR Title:

`Add ADK orchestrator core`

PR Description:

Adds the central GITEventHub ADK orchestrator, stateless role agents, local
relationship demo data, intake parsing, relationship search, ranking,
verification, and safe Workspace draft planning.

Files To Upload:

- `ai-service/README.md`
- `ai-service/requirements.txt`
- `ai-service/git_eventhub_agent/__init__.py`
- `ai-service/git_eventhub_agent/agent.py`
- `ai-service/git_eventhub_agent/sample_data.py`
- `ai-service/git_eventhub_agent/schemas.py`
- `ai-service/git_eventhub_agent/tools.py`

## PR 2: Workspace Tools

Commit Message:

`feat(ai-service): add approval-gated workspace tools`

PR Title:

`Add approval-gated Google Workspace tools`

PR Description:

Adds approval-gated Google Workspace tools for Drive, Gmail, Meet, Calendar,
Chat, Gemini-adjacent orchestration, Docs, Sheets, Slides, Keep, Sites
limitations, Forms, Tasks, NotebookLM Enterprise, and AppSheet. Tools return
planned actions by default and execute only when `execute=True` is passed with
Google Application Default Credentials or the relevant AppSheet access key
configured.

Files To Upload:

- `ai-service/git_eventhub_agent/agent.py`
- `ai-service/git_eventhub_agent/workspace_tools.py`
- `ai-service/tests/test_workflow.py`
- `.agents/plans/ai-service-adk-v1.md`
