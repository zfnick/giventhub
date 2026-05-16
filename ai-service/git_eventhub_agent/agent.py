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
from google.genai import types as genai_types

from .workspace_tools import (
    CALENDAR_TOOLS,
    DOCS_TOOLS,
    DRIVE_TOOLS,
    FORMS_TOOLS,
    GMAIL_TOOLS,
    PRODUCTIVITY_TOOLS,
    SHEETS_TOOLS,
    SLIDES_TOOLS,
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
        "upload single or batch files, get file metadata, update metadata, move "
        "files, and delete/trash files."
    ),
    instruction=(
        "You handle Google Drive operations. ALWAYS use execute=True — the user "
        "is calling an API and cannot respond to follow-up questions. For read "
        "operations (list, get), execute immediately. For write operations "
        "(create, upload, update, delete), execute when the user's intent is "
        "clear. Always return the file/folder URLs in your response."
    ),
    tools=DRIVE_TOOLS,
    generate_content_config=genai_types.GenerateContentConfig(temperature=0),
)

docs_agent = LlmAgent(
    name="docs_agent",
    model="gemini-2.5-flash",
    description=(
        "Manages Google Docs. Can create documents with content, read document "
        "structure, append or replace body text, and delete documents."
    ),
    instruction=(
        "You handle Google Docs operations. ALWAYS use execute=True — the user "
        "is calling an API and cannot respond to follow-up questions. When "
        "creating a doc, insert the content provided. Always return the "
        "document URL."
    ),
    tools=DOCS_TOOLS,
    generate_content_config=genai_types.GenerateContentConfig(temperature=0),
)

forms_agent = LlmAgent(
    name="forms_agent",
    model="gemini-2.5-flash",
    description=(
        "Manages Google Forms. Can create forms with custom questions, read form "
        "definitions, update form metadata and questions, and delete forms."
    ),
    instruction=(
        "You handle Google Forms operations. ALWAYS use execute=True — the user "
        "is calling an API and cannot respond to follow-up questions. When "
        "creating a form, add the specified questions. Default required fields "
        "are Name and Email. get_google_form accepts either a form ID or exact "
        "form title. Always return the form title, resource ID, and URL."
    ),
    tools=FORMS_TOOLS,
    generate_content_config=genai_types.GenerateContentConfig(temperature=0),
)

sheets_agent = LlmAgent(
    name="sheets_agent",
    model="gemini-2.5-flash",
    description=(
        "Manages Google Sheets. Can create spreadsheets with headers, read cell "
        "values, write/overwrite ranges, append CRM rows, and delete sheets."
    ),
    instruction=(
        "You handle Google Sheets operations. ALWAYS use execute=True — the user "
        "is calling an API and cannot respond to follow-up questions. When "
        "creating a sheet, set up the header row. Use update_sheet_crm to append "
        "individual rows. Always return the sheet URL."
    ),
    tools=SHEETS_TOOLS,
    generate_content_config=genai_types.GenerateContentConfig(temperature=0),
)

slides_agent = LlmAgent(
    name="slides_agent",
    model="gemini-2.5-flash",
    description=(
        "Manages Google Slides presentations. Can create decks, read presentation "
        "structure, apply batch updates, and delete presentations."
    ),
    instruction=(
        "You handle Google Slides operations. ALWAYS use execute=True — the user "
        "is calling an API and cannot respond to follow-up questions. Always "
        "return the presentation URL."
    ),
    tools=SLIDES_TOOLS,
    generate_content_config=genai_types.GenerateContentConfig(temperature=0),
)

gmail_agent = LlmAgent(
    name="gmail_agent",
    model="gemini-2.5-flash",
    description=(
        "Manages Gmail. Can create drafts, send messages, list and read messages, "
        "update drafts, modify labels, trash messages, and delete drafts."
    ),
    instruction=(
        "You handle Gmail operations. ALWAYS use execute=True — the user is "
        "calling an API and cannot respond to follow-up questions. For reading "
        "and listing emails, execute immediately. For sending emails, prefer "
        "creating a draft unless the user explicitly says 'send'. When reading "
        "message content, use format_type='full' to get the body text. When "
        "listing or reading messages, treat the email title as the Subject "
        "header and summarize title, sender, date, and snippet instead of "
        "returning ID-only lists."
    ),
    tools=GMAIL_TOOLS,
    generate_content_config=genai_types.GenerateContentConfig(temperature=0),
)

calendar_agent = LlmAgent(
    name="calendar_agent",
    model="gemini-2.5-flash",
    description=(
        "Manages Google Calendar. Can create events (without notifying attendees), "
        "list upcoming events, read event details, update events, and delete events."
    ),
    instruction=(
        "You handle Google Calendar operations. ALWAYS use execute=True — the user "
        "is calling an API and cannot respond to follow-up questions. When "
        "creating events, use sendUpdates='none' to avoid notifying attendees "
        "unless explicitly asked. Always return the event link."
    ),
    tools=CALENDAR_TOOLS,
    generate_content_config=genai_types.GenerateContentConfig(temperature=0),
)

productivity_agent = LlmAgent(
    name="productivity_agent",
    model="gemini-2.5-flash",
    description=(
        "Manages Google Tasks. "
        "Can create/list/read/update/delete task lists and tasks."
    ),
    instruction=(
        "You handle Google Tasks operations. ALWAYS "
        "use execute=True — the user is calling an API and cannot respond to "
        "follow-up questions."
    ),
    tools=PRODUCTIVITY_TOOLS,
    generate_content_config=genai_types.GenerateContentConfig(temperature=0),
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
        "EXECUTION MODE:\n"
        "This is an API — there is NO interactive back-and-forth with the user. "
        "You MUST execute operations immediately. NEVER ask 'would you like me "
        "to execute?', 'shall I proceed?', or 'do you want me to...'. "
        "The user's prompt IS the approval. "
        "Always pass execute=True to every tool call.\n\n"
        "INPUT CONTRACT:\n"
        "Every request from the backend includes:\n"
        "1. oauth_token (REQUIRED) — already registered by the backend.\n"
        "2. instruction (REQUIRED) — The user's request describing what to "
        "create, read, update, or delete.\n"
        "3. file or files (OPTIONAL) — Uploaded file metadata plus base64 content "
        "(e.g. a playbook JSON, CSV, or template) to use as context or upload to "
        "Drive.\n\n"
        "AUTH FIRST:\n"
        "The backend registers the OAuth token before you run. If oauth_token "
        "is '<registered>', do not call require_oauth_token again. Only call "
        "require_oauth_token when the request includes a real token value. If "
        "oauth_token is missing or empty, stop and ask for it. Never echo the "
        "token back to the user.\n\n"
        "ROUTING RULES:\n"
        "Based on the instruction, route to the correct domain agent:\n"
        "- Files/folders/uploads → drive_agent\n"
        "- Documents → docs_agent\n"
        "- Forms/surveys/registration → forms_agent\n"
        "- Spreadsheets/CRM/tracking → sheets_agent\n"
        "- Presentations/decks → slides_agent\n"
        "- Email/drafts → gmail_agent\n"
        "- Calendar events/scheduling → calendar_agent\n"
        "- Task lists/tasks → productivity_agent\n\n"
        "MULTI-ASSET REQUESTS (CRITICAL):\n"
        "For requests that create multiple assets (e.g. 'set up a hackathon "
        "workspace'):\n"
        "1. ALWAYS create the Drive folder FIRST via drive_agent.\n"
        "2. Extract the folder resource_id from the drive_agent response.\n"
        "3. Pass that resource_id as folder_id to EVERY subsequent create call "
        "(docs, forms, sheets, slides). NEVER create an asset without folder_id "
        "when a folder was created in the same request.\n"
        "4. Delegate to each domain agent in sequence — do NOT try to call "
        "multiple agents in parallel.\n"
        "5. When passing context to a sub-agent, include the exact folder_id "
        "value, not a reference like 'the folder I just created'.\n\n"
        "FILE HANDLING:\n"
        "When a file is attached for context, parse its contents and use it to "
        "inform the operation. For example, a playbook JSON defines which assets "
        "to create and what content to populate them with. When the user asks to "
        "store attached files, route to drive_agent for single or batch upload.\n\n"
        "RESPONSE FORMAT:\n"
        "After completing all operations, provide a concise summary listing:\n"
        "- Each asset created/read/updated with its title and URL\n"
        "- Any errors encountered\n"
        "Do NOT repeat the full API response JSON. Keep the summary human-readable.\n\n"
        "SAFETY:\n"
        "- Never claim an action was executed unless a tool returned executed=true.\n"
        "- For destructive operations (permanent delete), add a warning in the response.\n"
        "- After creating a resource, include its title, resource_id, and URL. "
        "If the user gives a resource title instead of an ID, resolve it first "
        "when the relevant tool supports title lookup."
    ),
    tools=[require_oauth_token],
    sub_agents=[
        drive_agent,
        docs_agent,
        forms_agent,
        sheets_agent,
        slides_agent,
        gmail_agent,
        calendar_agent,
        productivity_agent,
    ],
    generate_content_config=genai_types.GenerateContentConfig(temperature=0),
)
