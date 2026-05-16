# GITEventHub AI Service

Python service workspace for the Google ADK-powered GITEventHub orchestrator.

## Architecture

The ADK service follows a central-orchestrator pattern:

```text
Request
|
git_eventhub_orchestrator
|
Intake -> Relationship -> Recommendation -> Verification -> Workspace Drafts
|
Grounded response with approval-required actions
```

Agents do not call each other randomly. The root orchestrator owns the flow and
uses tools as temporary memory for local demos.

Current agents:

- `intake_agent`: parses intent, entities, action, sector, goal, and urgency.
- `relationship_agent`: traces ecosystem relationship evidence.
- `recommendation_agent`: ranks candidate startups or ecosystem actions.
- `verification_agent`: rejects unsupported claims and assigns confidence.
- `workspace_agent`: plans approval-gated Google Workspace CRUD actions.

Current tool layer:

- `tools.py`: mocked relationship search, ranking, verification, and full workflow.
- `workspace_tools.py`: approval-gated tools for the broader Google Workspace suite.
- `sample_data.py`: local demo data standing in for Firestore.

Workspace planning and execution require the end user's Google OAuth token to
be registered first with `require_oauth_token`. After that, tool calls return
`status: planned` unless `execute=True` is supplied. When executed, the service
builds Google API clients from that OAuth token with per-API Workspace scopes.
Calendar event creation uses `sendUpdates=none` so execution does not email
attendees.

Production integrations still missing:

- Firestore relationship graph queries.
- Backend API route that calls this ADK service from `/api/adapt`.
- Optional vector search for semantic matching across event assets.

Workspace CRUD coverage:

| App | Create | Read | Update | Delete |
| --- | --- | --- | --- | --- |
| Drive | `create_drive_folder` | `list_drive_files`, `get_drive_file` | `update_drive_file_metadata` | `delete_drive_file` |
| Docs | `create_google_doc` | `get_google_doc` | `update_google_doc_content` | `delete_google_doc` |
| Forms | `create_google_form` | `get_google_form` | `update_google_form` | `delete_google_form` |
| Sheets | `create_google_sheet` | `get_google_sheet_values` | `update_google_sheet_values`, `update_sheet_crm` | `delete_google_sheet` |
| Gmail | `create_gmail_draft` | `get_gmail_draft` | `update_gmail_draft` | `delete_gmail_draft` |
| Calendar | `create_calendar_draft` | `get_calendar_event` | `update_calendar_event` | `delete_calendar_event` |
| Gmail Messages | `send_gmail_message` | `list_gmail_messages`, `get_gmail_message` | `modify_gmail_message_labels` | `trash_gmail_message` |
| Slides | `create_google_slide_deck` | `get_google_slide_deck` | `update_google_slide_deck` | `delete_google_slide_deck` |
| Tasks | `create_task_list`, `create_task` | `list_task_lists`, `get_task_list`, `list_tasks`, `get_task` | `update_task_list`, `update_task` | `delete_task_list`, `delete_task` |
| Chat | `create_chat_space`, `create_chat_message` | `list_chat_spaces`, `get_chat_space`, `get_chat_message` | `update_chat_space`, `update_chat_message` | `delete_chat_space`, `delete_chat_message` |
| Meet | `create_meet_space` | `get_meet_space` | `end_meet_active_conference` | Not supported by Meet API as normal CRUD |
| Keep | `create_keep_note` | `list_keep_notes`, `get_keep_note` | Limited by Keep API | `delete_keep_note` |
| NotebookLM Enterprise | `create_notebooklm_notebook` | `get_notebooklm_notebook` | `share_notebooklm_notebook` | `delete_notebooklm_notebooks` |
| AppSheet | `call_appsheet_table_action` with `Add` | `call_appsheet_table_action` with `Find` | `call_appsheet_table_action` with `Edit` | `call_appsheet_table_action` with `Delete` |
| Vids | Not available | Not available | `plan_google_vids_action` explains limitation | Not available |
| Sites | Limited legacy API only | Limited legacy API only | `plan_google_sites_action` explains limitation | Limited legacy API only |

## Setup

This venv was created with the Homebrew Python interpreter:

```sh
/opt/homebrew/opt/python@3.14/bin/python3.14 -m venv .venv
```

Activate it from this folder:

```sh
source .venv/bin/activate
```

Installed package:

```sh
python -m pip install -r requirements.txt
```

## Local Configuration

Copy the example environment file and fill in your Google Cloud project:

```sh
cp .env.example .env
```

For Google Cloud credits, use Vertex AI / Gemini Enterprise Agent Platform:

```sh
GOOGLE_GENAI_USE_VERTEXAI=TRUE
GOOGLE_CLOUD_PROJECT=your-project-id
GOOGLE_CLOUD_LOCATION=global
```

Provide an end-user Google OAuth access token in the ADK request payload or
interactive prompt. The agent registers it first and never includes it in tool
responses.

## Run

```sh
source .venv/bin/activate
adk run git_eventhub_agent
```

Try:

```text
oauth_token: ya29.example-token
instruction: Create a Drive folder called Climate Hackathon Workspace. Do not execute yet.
```
