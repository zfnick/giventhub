"""GITEventHub ADK agent hierarchy.

Architecture: workspace_agent as root with 9 domain sub-agents.
Backend POST → ADK → workspace_agent → domain_agent → Google API.

Follows Google ADK best practices:
- Specialization: each agent owns its domain tools (max ~10 per agent)
- Descriptions: precise descriptions so the LLM routes correctly
- execute=True/False safety pattern on all tools
"""

from pathlib import Path

from dotenv import load_dotenv
from google.adk.agents import LlmAgent

from .workspace_tools import (
    CALENDAR_TOOLS,
    CHAT_MEET_TOOLS,
    DOCS_TOOLS,
    DRIVE_TOOLS,
    FORMS_TOOLS,
    GMAIL_TOOLS,
    PRODUCTIVITY_TOOLS,
    SHEETS_TOOLS,
    SLIDES_TOOLS,
    draft_workspace_actions,
    require_oauth_token,
)


load_dotenv(Path(__file__).resolve().parents[1] / ".env")


# ═══════════════════════════════════════════════════════════════════════════
# Domain Agents — each owns one Google service's CRUD tools
# ═══════════════════════════════════════════════════════════════════════════

drive_agent = LlmAgent(
    name="drive_agent",
    model="gemini-2.5-flash",
    description=(
        "Manages Google Drive files and folders. Can create folders, list files, "
        "get file metadata, update metadata, move files, and delete/trash files."
    ),
    instruction=(
        "You handle Google Drive operations. Use execute=True only when the user "
        "explicitly approves execution. For all other requests, return the planned "
        "action with execute=False. Always return the file/folder URLs."
    ),
    tools=DRIVE_TOOLS,
)

docs_agent = LlmAgent(
    name="docs_agent",
    model="gemini-2.5-flash",
    description=(
        "Manages Google Docs. Can create documents with content, read document "
        "structure, append or replace body text, and delete documents."
    ),
    instruction=(
        "You handle Google Docs operations. When creating a doc, insert the "
        "content provided. Use execute=True only after user approval. "
        "Always return the document URL."
    ),
    tools=DOCS_TOOLS,
)

forms_agent = LlmAgent(
    name="forms_agent",
    model="gemini-2.5-flash",
    description=(
        "Manages Google Forms. Can create forms with custom questions, read form "
        "definitions, update form metadata and questions, and delete forms."
    ),
    instruction=(
        "You handle Google Forms operations. When creating a form, add the "
        "specified questions. Default required fields are Name and Email. "
        "Use execute=True only after user approval. Always return the form URL."
    ),
    tools=FORMS_TOOLS,
)

sheets_agent = LlmAgent(
    name="sheets_agent",
    model="gemini-2.5-flash",
    description=(
        "Manages Google Sheets. Can create spreadsheets with headers, read cell "
        "values, write/overwrite ranges, append CRM rows, and delete sheets."
    ),
    instruction=(
        "You handle Google Sheets operations. When creating a sheet, set up the "
        "header row. Use update_sheet_crm to append individual rows. "
        "Use execute=True only after user approval. Always return the sheet URL."
    ),
    tools=SHEETS_TOOLS,
)

slides_agent = LlmAgent(
    name="slides_agent",
    model="gemini-2.5-flash",
    description=(
        "Manages Google Slides presentations. Can create decks, read presentation "
        "structure, apply batch updates, and delete presentations."
    ),
    instruction=(
        "You handle Google Slides operations. Use execute=True only after user "
        "approval. Always return the presentation URL."
    ),
    tools=SLIDES_TOOLS,
)

gmail_agent = LlmAgent(
    name="gmail_agent",
    model="gemini-2.5-flash",
    description=(
        "Manages Gmail. Can create drafts, send messages, list and read messages, "
        "update drafts, modify labels, trash messages, and delete drafts."
    ),
    instruction=(
        "You handle Gmail operations. NEVER send an email without explicit user "
        "approval — default to creating a draft instead. Use execute=True only "
        "after user approval. For send_gmail_message, always confirm first."
    ),
    tools=GMAIL_TOOLS,
)

calendar_agent = LlmAgent(
    name="calendar_agent",
    model="gemini-2.5-flash",
    description=(
        "Manages Google Calendar. Can create events (without notifying attendees), "
        "list upcoming events, read event details, update events, and delete events."
    ),
    instruction=(
        "You handle Google Calendar operations. When creating events, use "
        "sendUpdates='none' to avoid notifying attendees unless explicitly asked. "
        "Use execute=True only after user approval. Always return the event link."
    ),
    tools=CALENDAR_TOOLS,
)

chat_meet_agent = LlmAgent(
    name="chat_meet_agent",
    model="gemini-2.5-flash",
    description=(
        "Manages Google Chat spaces and messages, and Google Meet meetings. "
        "Can create/list/update/delete spaces and messages, and create/end Meet calls."
    ),
    instruction=(
        "You handle Google Chat and Meet operations. Use execute=True only after "
        "user approval. For chat messages, never send without confirmation."
    ),
    tools=CHAT_MEET_TOOLS,
)

productivity_agent = LlmAgent(
    name="productivity_agent",
    model="gemini-2.5-flash",
    description=(
        "Manages Google Tasks, Keep notes, NotebookLM notebooks, and AppSheet. "
        "Can create/list/read/update/delete task lists, tasks, notes, and notebooks."
    ),
    instruction=(
        "You handle Tasks, Keep, NotebookLM, and AppSheet operations. "
        "Use execute=True only after user approval."
    ),
    tools=PRODUCTIVITY_TOOLS,
)


# ═══════════════════════════════════════════════════════════════════════════
# Root Agent — Workspace Coordinator (entry point for all requests)
# ═══════════════════════════════════════════════════════════════════════════

root_agent = LlmAgent(
    name="workspace_coordinator",
    model="gemini-2.5-flash",
    description="Coordinates all Google Workspace CRUD operations for GITEventHub.",
    instruction=(
        "You are the GITEventHub Workspace Coordinator.\n\n"
        "INPUT CONTRACT:\n"
        "Every request from the backend includes:\n"
        "1. oauth_token (REQUIRED) — The end user's Google OAuth token. All "
        "Google Workspace API calls MUST be performed on behalf of this user.\n"
        "2. instruction (REQUIRED) — The user's request describing what to "
        "create, read, update, or delete.\n"
        "3. file (OPTIONAL) — An uploaded file (e.g. a playbook JSON, CSV, or "
        "template) to use as context for the operation.\n\n"
        "AUTH FIRST:\n"
        "Before routing, planning, or executing any Workspace operation, call "
        "require_oauth_token with the provided oauth_token. If oauth_token is "
        "missing or empty, stop and ask for it. Never echo the token back to "
        "the user.\n\n"
        "ROUTING RULES:\n"
        "Based on the instruction, route to the correct domain agent:\n"
        "- Files/folders → drive_agent\n"
        "- Documents → docs_agent\n"
        "- Forms/surveys/registration → forms_agent\n"
        "- Spreadsheets/CRM/tracking → sheets_agent\n"
        "- Presentations/decks → slides_agent\n"
        "- Email/drafts → gmail_agent\n"
        "- Calendar events/scheduling → calendar_agent\n"
        "- Chat spaces/meetings → chat_meet_agent\n"
        "- Task lists/notes/notebooks → productivity_agent\n\n"
        "MULTI-ASSET REQUESTS:\n"
        "For requests like 'set up a hackathon workspace', delegate to each "
        "domain agent in sequence: first create the Drive folder, then create "
        "docs/forms/sheets inside it. Pass the folder_id from drive_agent to "
        "subsequent agents so all assets live in the same folder.\n\n"
        "FILE HANDLING:\n"
        "When a file is attached, parse its contents and use it to inform the "
        "operation. For example, a playbook JSON defines which assets to create "
        "and what content to populate them with.\n\n"
        "SAFETY:\n"
        "- Use draft_workspace_actions to generate approval-required plans.\n"
        "- Never claim an action was executed unless a tool returned executed=true.\n"
        "- For destructive operations (delete, send email), always confirm first."
    ),
    tools=[require_oauth_token, draft_workspace_actions],
    sub_agents=[
        drive_agent,
        docs_agent,
        forms_agent,
        sheets_agent,
        slides_agent,
        gmail_agent,
        calendar_agent,
        chat_meet_agent,
        productivity_agent,
    ],
)
