from __future__ import annotations

import base64
from contextvars import ContextVar
import json
import os
from email.message import EmailMessage
from typing import Any

import requests
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

from .schemas import WorkspaceDraft


DRIVE_FOLDER_MIME_TYPE = "application/vnd.google-apps.folder"
GOOGLE_DOC_MIME_TYPE = "application/vnd.google-apps.document"
GOOGLE_SLIDES_MIME_TYPE = "application/vnd.google-apps.presentation"
GOOGLE_SHEET_MIME_TYPE = "application/vnd.google-apps.spreadsheet"
OAUTH_TOKEN_REQUIRED_MESSAGE = "oauth_token is required before planning or executing Google Workspace actions."
_WORKSPACE_OAUTH_TOKEN: ContextVar[str] = ContextVar("workspace_oauth_token", default="")

API_SCOPES = {
    "calendar": ["https://www.googleapis.com/auth/calendar"],
    "chat": [
        "https://www.googleapis.com/auth/chat.messages",
        "https://www.googleapis.com/auth/chat.spaces",
    ],
    "cloud-platform": ["https://www.googleapis.com/auth/cloud-platform"],
    "docs": ["https://www.googleapis.com/auth/documents"],
    "drive": ["https://www.googleapis.com/auth/drive"],
    "forms": ["https://www.googleapis.com/auth/forms.body"],
    "gmail": [
        "https://www.googleapis.com/auth/gmail.compose",
        "https://www.googleapis.com/auth/gmail.modify",
    ],
    "keep": ["https://www.googleapis.com/auth/keep"],
    "meet": ["https://www.googleapis.com/auth/meetings.space.created"],
    "sheets": ["https://www.googleapis.com/auth/spreadsheets"],
    "slides": ["https://www.googleapis.com/auth/presentations"],
    "tasks": ["https://www.googleapis.com/auth/tasks"],
}


def _workspace_url(kind: str, resource_id: str) -> str:
    urls = {
        "calendar": "https://calendar.google.com/calendar/event?eid={resource_id}",
        "doc": "https://docs.google.com/document/d/{resource_id}/edit",
        "drive_folder": "https://drive.google.com/drive/folders/{resource_id}",
        "form": "https://docs.google.com/forms/d/{resource_id}/edit",
        "slide": "https://docs.google.com/presentation/d/{resource_id}/edit",
        "sheet": "https://docs.google.com/spreadsheets/d/{resource_id}/edit",
    }
    return urls[kind].format(resource_id=resource_id)


def require_oauth_token(oauth_token: str) -> dict:
    """Register the end user's OAuth token before any Workspace action."""
    token = oauth_token.strip()
    if not token:
        raise ValueError(OAUTH_TOKEN_REQUIRED_MESSAGE)
    _WORKSPACE_OAUTH_TOKEN.set(token)
    return {
        "status": "ready",
        "operation": "require_oauth_token",
        "requires_approval": False,
        "executed": False,
        "oauth_token_registered": True,
    }


def _require_oauth_token() -> str:
    token = _WORKSPACE_OAUTH_TOKEN.get().strip()
    if not token:
        raise ValueError(OAUTH_TOKEN_REQUIRED_MESSAGE)
    return token


def _planned_result(operation: str, title: str, payload: dict[str, Any]) -> dict:
    _require_oauth_token()
    return {
        "status": "planned",
        "operation": operation,
        "title": title,
        "requires_approval": True,
        "executed": False,
        "payload": payload,
    }


def _executed_result(operation: str, title: str, resource_id: str, url: str, extra: dict | None = None) -> dict:
    result = {
        "status": "success",
        "operation": operation,
        "title": title,
        "requires_approval": False,
        "executed": True,
        "resource_id": resource_id,
        "url": url,
    }
    if extra:
        result.update(extra)
    return result


def _deleted_result(operation: str, title: str, resource_id: str, permanent: bool) -> dict:
    return {
        "status": "success",
        "operation": operation,
        "title": title,
        "requires_approval": False,
        "executed": True,
        "resource_id": resource_id,
        "deleted": permanent,
        "trashed": not permanent,
    }


def _google_service(api_name: str, version: str) -> Any:
    """Build a dynamic Google API client resource from the user's token.

    googleapiclient resources expose API methods dynamically from discovery
    documents, so static analyzers cannot know about members like files() or
    documents(). Returning Any keeps that dynamic boundary contained here.
    """
    creds = Credentials(token=_require_oauth_token(), scopes=API_SCOPES[api_name])
    if api_name in {"forms", "keep", "meet"}:
        return build(api_name, version, credentials=creds, static_discovery=False)
    return build(api_name, version, credentials=creds)


def _access_token(scope_key: str = "cloud-platform") -> str:
    if scope_key not in API_SCOPES:
        raise KeyError(f"Unknown Google API scope key: {scope_key}")
    return _require_oauth_token()


def _authed_json_request(method: str, url: str, body: dict | None = None, scope_key: str = "cloud-platform") -> dict:
    response = requests.request(
        method,
        url,
        headers={"Authorization": f"Bearer {_access_token(scope_key)}", "Content-Type": "application/json"},
        json=body,
        timeout=30,
    )
    response.raise_for_status()
    if not response.content:
        return {}
    return response.json()


def _move_drive_file(file_id: str, folder_id: str) -> None:
    drive_service = _google_service("drive", "v3")
    file = drive_service.files().get(fileId=file_id, fields="parents").execute()
    previous_parents = ",".join(file.get("parents", []))
    drive_service.files().update(
        fileId=file_id,
        addParents=folder_id,
        removeParents=previous_parents,
        fields="id, parents",
    ).execute()


def _parse_json_list(raw_json: str, default: list) -> list:
    if not raw_json:
        return default
    parsed = json.loads(raw_json)
    if not isinstance(parsed, list):
        raise ValueError("Expected a JSON list.")
    return parsed


def _build_email_message(to: str, subject: str, body: str, cc: str = "") -> str:
    message = EmailMessage()
    message["To"] = to
    if cc:
        message["Cc"] = cc
    message["Subject"] = subject
    message.set_content(body)
    return base64.urlsafe_b64encode(message.as_bytes()).decode()


def draft_workspace_actions(recommendations_json: str) -> list[dict]:
    """Create approval-required Google Workspace draft actions."""
    _require_oauth_token()
    recommendations = json.loads(recommendations_json)
    drafts: list[WorkspaceDraft] = []
    for rec in recommendations[:3]:
        if rec.get("verification_status") == "unsupported":
            continue
        evidence = rec.get("evidence") or ["No supporting evidence provided."]
        drafts.append(
            WorkspaceDraft(
                type="gmail_draft",
                title=f"Reconnect with {rec['name']}",
                summary=f"Draft a warm follow-up citing: {evidence[0]}",
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


def create_drive_folder(folder_name: str, parent_folder_id: str = "", execute: bool = False) -> dict:
    """Create a Google Drive folder, or return an approval-required plan."""
    payload = {"folder_name": folder_name, "parent_folder_id": parent_folder_id}
    if not execute:
        return _planned_result("create_drive_folder", folder_name, payload)

    metadata: dict[str, Any] = {"name": folder_name, "mimeType": DRIVE_FOLDER_MIME_TYPE}
    if parent_folder_id:
        metadata["parents"] = [parent_folder_id]

    drive_service = _google_service("drive", "v3")
    folder = drive_service.files().create(body=metadata, fields="id, name").execute()
    folder_id = folder["id"]
    return _executed_result(
        "create_drive_folder",
        folder.get("name", folder_name),
        folder_id,
        _workspace_url("drive_folder", folder_id),
    )


def list_drive_files(query: str = "", page_size: int = 20, execute: bool = False) -> dict:
    """List Google Drive files, or return an approval-required plan."""
    payload = {"query": query, "page_size": page_size}
    if not execute:
        return _planned_result("list_drive_files", "Drive file list", payload)

    drive_service = _google_service("drive", "v3")
    response = (
        drive_service.files()
        .list(
            q=query or "trashed = false",
            pageSize=page_size,
            fields="files(id, name, mimeType, webViewLink, parents, trashed)",
        )
        .execute()
    )
    return {
        "status": "success",
        "operation": "list_drive_files",
        "requires_approval": False,
        "executed": True,
        "files": response.get("files", []),
    }


def get_drive_file(file_id: str, execute: bool = False) -> dict:
    """Read Google Drive file metadata, or return an approval-required plan."""
    payload = {"file_id": file_id}
    if not execute:
        return _planned_result("get_drive_file", file_id, payload)

    drive_service = _google_service("drive", "v3")
    file = (
        drive_service.files()
        .get(fileId=file_id, fields="id, name, mimeType, webViewLink, parents, trashed")
        .execute()
    )
    return {
        "status": "success",
        "operation": "get_drive_file",
        "requires_approval": False,
        "executed": True,
        "file": file,
    }


def update_drive_file_metadata(
    file_id: str,
    name: str = "",
    description: str = "",
    add_parent_folder_id: str = "",
    remove_parent_folder_id: str = "",
    execute: bool = False,
) -> dict:
    """Update Drive file metadata or parents, or return an approval-required plan."""
    payload = {
        "file_id": file_id,
        "name": name,
        "description": description,
        "add_parent_folder_id": add_parent_folder_id,
        "remove_parent_folder_id": remove_parent_folder_id,
    }
    if not execute:
        return _planned_result("update_drive_file_metadata", file_id, payload)

    metadata = {}
    if name:
        metadata["name"] = name
    if description:
        metadata["description"] = description

    drive_service = _google_service("drive", "v3")
    file = (
        drive_service.files()
        .update(
            fileId=file_id,
            body=metadata,
            addParents=add_parent_folder_id or None,
            removeParents=remove_parent_folder_id or None,
            fields="id, name, mimeType, webViewLink, parents",
        )
        .execute()
    )
    return _executed_result(
        "update_drive_file_metadata",
        file.get("name", file_id),
        file["id"],
        file.get("webViewLink", ""),
        {"file": file},
    )


def delete_drive_file(file_id: str, permanent: bool = False, execute: bool = False) -> dict:
    """Trash or permanently delete a Drive file, or return an approval-required plan."""
    payload = {"file_id": file_id, "permanent": permanent}
    if not execute:
        return _planned_result("delete_drive_file", file_id, payload)

    drive_service = _google_service("drive", "v3")
    if permanent:
        drive_service.files().delete(fileId=file_id).execute()
    else:
        drive_service.files().update(fileId=file_id, body={"trashed": True}).execute()
    return _deleted_result("delete_drive_file", file_id, file_id, permanent)


def create_google_doc(title: str, content: str = "", folder_id: str = "", execute: bool = False) -> dict:
    """Create a Google Doc, optionally insert content, or return an approval-required plan."""
    payload = {"title": title, "content": content, "folder_id": folder_id}
    if not execute:
        return _planned_result("create_google_doc", title, payload)

    if folder_id:
        drive_service = _google_service("drive", "v3")
        doc = (
            drive_service.files()
            .create(
                body={"name": title, "mimeType": GOOGLE_DOC_MIME_TYPE, "parents": [folder_id]},
                fields="id, name",
            )
            .execute()
        )
        document_id = doc["id"]
    else:
        docs_service = _google_service("docs", "v1")
        doc = docs_service.documents().create(body={"title": title}).execute()
        document_id = doc["documentId"]

    if content:
        docs_service = _google_service("docs", "v1")
        docs_service.documents().batchUpdate(
            documentId=document_id,
            body={"requests": [{"insertText": {"location": {"index": 1}, "text": content}}]},
        ).execute()

    return _executed_result("create_google_doc", title, document_id, _workspace_url("doc", document_id))


def get_google_doc(document_id: str, execute: bool = False) -> dict:
    """Read a Google Doc structure, or return an approval-required plan."""
    payload = {"document_id": document_id}
    if not execute:
        return _planned_result("get_google_doc", document_id, payload)

    docs_service = _google_service("docs", "v1")
    document = docs_service.documents().get(documentId=document_id).execute()
    return {
        "status": "success",
        "operation": "get_google_doc",
        "requires_approval": False,
        "executed": True,
        "document": document,
    }


def update_google_doc_content(
    document_id: str,
    content: str,
    mode: str = "append",
    execute: bool = False,
) -> dict:
    """Append or replace Google Doc body text, or return an approval-required plan."""
    payload = {"document_id": document_id, "content": content, "mode": mode}
    if not execute:
        return _planned_result("update_google_doc_content", document_id, payload)
    if mode not in {"append", "replace"}:
        raise ValueError("mode must be 'append' or 'replace'.")

    docs_service = _google_service("docs", "v1")
    document = docs_service.documents().get(documentId=document_id).execute()
    body_content = document.get("body", {}).get("content", [])
    end_index = body_content[-1].get("endIndex", 1) if body_content else 1

    requests: list[dict[str, Any]] = []
    if mode == "replace" and end_index > 2:
        requests.append({"deleteContentRange": {"range": {"startIndex": 1, "endIndex": end_index - 1}}})
        insert_index = 1
    else:
        insert_index = max(1, end_index - 1)
    requests.append({"insertText": {"location": {"index": insert_index}, "text": content}})

    response = (
        docs_service.documents()
        .batchUpdate(documentId=document_id, body={"requests": requests})
        .execute()
    )
    return _executed_result(
        "update_google_doc_content",
        document.get("title", document_id),
        document_id,
        _workspace_url("doc", document_id),
        {"replies": response.get("replies", [])},
    )


def delete_google_doc(document_id: str, permanent: bool = False, execute: bool = False) -> dict:
    """Trash or permanently delete a Google Doc through Drive."""
    payload = {"document_id": document_id, "permanent": permanent}
    if not execute:
        return _planned_result("delete_google_doc", document_id, payload)

    delete_drive_file(document_id, permanent=permanent, execute=True)
    return _deleted_result("delete_google_doc", document_id, document_id, permanent)


def create_google_form(
    title: str,
    description: str = "",
    questions_json: str = "",
    folder_id: str = "",
    execute: bool = False,
) -> dict:
    """Create a Google Form with text questions, or return an approval-required plan."""
    questions = _parse_json_list(questions_json, ["Name", "Email", "What are you building?"])
    payload = {"title": title, "description": description, "questions": questions, "folder_id": folder_id}
    if not execute:
        return _planned_result("create_google_form", title, payload)

    forms_service = _google_service("forms", "v1")
    form = forms_service.forms().create(body={"info": {"title": title}}).execute()
    form_id = form["formId"]

    requests: list[dict[str, Any]] = []
    if description:
        requests.append(
            {
                "updateFormInfo": {
                    "info": {"description": description},
                    "updateMask": "description",
                }
            }
        )
    for index, question in enumerate(questions):
        requests.append(
            {
                "createItem": {
                    "item": {
                        "title": str(question),
                        "questionItem": {
                            "question": {
                                "required": index < 2,
                                "textQuestion": {"paragraph": index > 1},
                            }
                        },
                    },
                    "location": {"index": index},
                }
            }
        )

    if requests:
        forms_service.forms().batchUpdate(formId=form_id, body={"requests": requests}).execute()
    if folder_id:
        _move_drive_file(form_id, folder_id)

    return _executed_result("create_google_form", title, form_id, _workspace_url("form", form_id))


def get_google_form(form_id: str, execute: bool = False) -> dict:
    """Read a Google Form definition, or return an approval-required plan."""
    payload = {"form_id": form_id}
    if not execute:
        return _planned_result("get_google_form", form_id, payload)

    forms_service = _google_service("forms", "v1")
    form = forms_service.forms().get(formId=form_id).execute()
    return {
        "status": "success",
        "operation": "get_google_form",
        "requires_approval": False,
        "executed": True,
        "form": form,
    }


def update_google_form(
    form_id: str,
    title: str = "",
    description: str = "",
    questions_json: str = "",
    execute: bool = False,
) -> dict:
    """Update Google Form metadata and append text questions, or return a plan."""
    questions = _parse_json_list(questions_json, [])
    payload = {"form_id": form_id, "title": title, "description": description, "questions": questions}
    if not execute:
        return _planned_result("update_google_form", form_id, payload)

    requests: list[dict[str, Any]] = []
    info: dict[str, str] = {}
    update_mask = []
    if title:
        info["title"] = title
        update_mask.append("title")
    if description:
        info["description"] = description
        update_mask.append("description")
    if info:
        requests.append(
            {
                "updateFormInfo": {
                    "info": info,
                    "updateMask": ",".join(update_mask),
                }
            }
        )
    for index, question in enumerate(questions):
        requests.append(
            {
                "createItem": {
                    "item": {
                        "title": str(question),
                        "questionItem": {
                            "question": {
                                "required": False,
                                "textQuestion": {"paragraph": True},
                            }
                        },
                    },
                    "location": {"index": index},
                }
            }
        )

    forms_service = _google_service("forms", "v1")
    response = {}
    if requests:
        response = forms_service.forms().batchUpdate(formId=form_id, body={"requests": requests}).execute()
    return _executed_result(
        "update_google_form",
        title or form_id,
        form_id,
        _workspace_url("form", form_id),
        {"replies": response.get("replies", [])},
    )


def delete_google_form(form_id: str, permanent: bool = False, execute: bool = False) -> dict:
    """Trash or permanently delete a Google Form through Drive."""
    payload = {"form_id": form_id, "permanent": permanent}
    if not execute:
        return _planned_result("delete_google_form", form_id, payload)

    delete_drive_file(form_id, permanent=permanent, execute=True)
    return _deleted_result("delete_google_form", form_id, form_id, permanent)


def create_google_sheet(
    title: str,
    headers_json: str = "",
    folder_id: str = "",
    execute: bool = False,
) -> dict:
    """Create a Google Sheet and optional header row, or return an approval-required plan."""
    headers = _parse_json_list(headers_json, ["Name", "Email", "Organization", "Status"])
    payload = {"title": title, "headers": headers, "folder_id": folder_id}
    if not execute:
        return _planned_result("create_google_sheet", title, payload)

    drive_service = _google_service("drive", "v3")
    metadata: dict[str, Any] = {"name": title, "mimeType": GOOGLE_SHEET_MIME_TYPE}
    if folder_id:
        metadata["parents"] = [folder_id]
    sheet = drive_service.files().create(body=metadata, fields="id, name").execute()
    spreadsheet_id = sheet["id"]

    if headers:
        sheets_service = _google_service("sheets", "v4")
        sheets_service.spreadsheets().values().append(
            spreadsheetId=spreadsheet_id,
            range="A1",
            valueInputOption="RAW",
            body={"values": [headers]},
        ).execute()

    return _executed_result(
        "create_google_sheet",
        title,
        spreadsheet_id,
        _workspace_url("sheet", spreadsheet_id),
    )


def get_google_sheet_values(
    spreadsheet_id: str,
    range_name: str = "A1:Z1000",
    execute: bool = False,
) -> dict:
    """Read values from a Google Sheet, or return an approval-required plan."""
    payload = {"spreadsheet_id": spreadsheet_id, "range_name": range_name}
    if not execute:
        return _planned_result("get_google_sheet_values", spreadsheet_id, payload)

    sheets_service = _google_service("sheets", "v4")
    response = (
        sheets_service.spreadsheets()
        .values()
        .get(spreadsheetId=spreadsheet_id, range=range_name)
        .execute()
    )
    return {
        "status": "success",
        "operation": "get_google_sheet_values",
        "requires_approval": False,
        "executed": True,
        "spreadsheet_id": spreadsheet_id,
        "range": response.get("range"),
        "values": response.get("values", []),
    }


def update_google_sheet_values(
    spreadsheet_id: str,
    values_json: str,
    range_name: str = "A1",
    execute: bool = False,
) -> dict:
    """Overwrite a Google Sheet range, or return an approval-required plan."""
    values = _parse_json_list(values_json, [])
    payload = {"spreadsheet_id": spreadsheet_id, "range_name": range_name, "values": values}
    if not execute:
        return _planned_result("update_google_sheet_values", spreadsheet_id, payload)

    sheets_service = _google_service("sheets", "v4")
    response = (
        sheets_service.spreadsheets()
        .values()
        .update(
            spreadsheetId=spreadsheet_id,
            range=range_name,
            valueInputOption="USER_ENTERED",
            body={"values": values},
        )
        .execute()
    )
    return _executed_result(
        "update_google_sheet_values",
        spreadsheet_id,
        spreadsheet_id,
        _workspace_url("sheet", spreadsheet_id),
        {"updated_range": response.get("updatedRange"), "updated_cells": response.get("updatedCells")},
    )


def delete_google_sheet(spreadsheet_id: str, permanent: bool = False, execute: bool = False) -> dict:
    """Trash or permanently delete a Google Sheet through Drive."""
    payload = {"spreadsheet_id": spreadsheet_id, "permanent": permanent}
    if not execute:
        return _planned_result("delete_google_sheet", spreadsheet_id, payload)

    delete_drive_file(spreadsheet_id, permanent=permanent, execute=True)
    return _deleted_result("delete_google_sheet", spreadsheet_id, spreadsheet_id, permanent)


def create_google_slide_deck(title: str, folder_id: str = "", execute: bool = False) -> dict:
    """Create a Google Slides presentation, or return an approval-required plan."""
    payload = {"title": title, "folder_id": folder_id}
    if not execute:
        return _planned_result("create_google_slide_deck", title, payload)

    if folder_id:
        drive_service = _google_service("drive", "v3")
        deck = (
            drive_service.files()
            .create(
                body={"name": title, "mimeType": GOOGLE_SLIDES_MIME_TYPE, "parents": [folder_id]},
                fields="id, name",
            )
            .execute()
        )
        presentation_id = deck["id"]
    else:
        slides_service = _google_service("slides", "v1")
        deck = slides_service.presentations().create(body={"title": title}).execute()
        presentation_id = deck["presentationId"]

    return _executed_result(
        "create_google_slide_deck",
        title,
        presentation_id,
        _workspace_url("slide", presentation_id),
    )


def get_google_slide_deck(presentation_id: str, execute: bool = False) -> dict:
    """Read a Google Slides presentation, or return an approval-required plan."""
    payload = {"presentation_id": presentation_id}
    if not execute:
        return _planned_result("get_google_slide_deck", presentation_id, payload)

    slides_service = _google_service("slides", "v1")
    presentation = slides_service.presentations().get(presentationId=presentation_id).execute()
    return {
        "status": "success",
        "operation": "get_google_slide_deck",
        "requires_approval": False,
        "executed": True,
        "presentation": presentation,
    }


def update_google_slide_deck(presentation_id: str, requests_json: str, execute: bool = False) -> dict:
    """Apply a Slides batchUpdate request list, or return an approval-required plan."""
    requests_list = _parse_json_list(requests_json, [])
    payload = {"presentation_id": presentation_id, "requests": requests_list}
    if not execute:
        return _planned_result("update_google_slide_deck", presentation_id, payload)

    slides_service = _google_service("slides", "v1")
    response = (
        slides_service.presentations()
        .batchUpdate(presentationId=presentation_id, body={"requests": requests_list})
        .execute()
    )
    return _executed_result(
        "update_google_slide_deck",
        presentation_id,
        presentation_id,
        _workspace_url("slide", presentation_id),
        {"replies": response.get("replies", [])},
    )


def delete_google_slide_deck(presentation_id: str, permanent: bool = False, execute: bool = False) -> dict:
    """Trash or permanently delete a Google Slides deck through Drive."""
    payload = {"presentation_id": presentation_id, "permanent": permanent}
    if not execute:
        return _planned_result("delete_google_slide_deck", presentation_id, payload)

    delete_drive_file(presentation_id, permanent=permanent, execute=True)
    return _deleted_result("delete_google_slide_deck", presentation_id, presentation_id, permanent)


def update_sheet_crm(
    spreadsheet_id: str,
    row_json: str,
    range_name: str = "A1",
    execute: bool = False,
) -> dict:
    """Append one CRM row to a Google Sheet, or return an approval-required plan."""
    row = _parse_json_list(row_json, [])
    payload = {"spreadsheet_id": spreadsheet_id, "range_name": range_name, "row": row}
    if not execute:
        return _planned_result("update_sheet_crm", spreadsheet_id, payload)

    sheets_service = _google_service("sheets", "v4")
    response = (
        sheets_service.spreadsheets()
        .values()
        .append(
            spreadsheetId=spreadsheet_id,
            range=range_name,
            valueInputOption="USER_ENTERED",
            insertDataOption="INSERT_ROWS",
            body={"values": [row]},
        )
        .execute()
    )
    return _executed_result(
        "update_sheet_crm",
        spreadsheet_id,
        spreadsheet_id,
        _workspace_url("sheet", spreadsheet_id),
        {"updated_range": response.get("updates", {}).get("updatedRange")},
    )


def create_gmail_draft(
    to: str,
    subject: str,
    body: str,
    cc: str = "",
    execute: bool = False,
) -> dict:
    """Create a Gmail draft, or return an approval-required plan."""
    payload = {"to": to, "cc": cc, "subject": subject, "body": body}
    if not execute:
        return _planned_result("create_gmail_draft", subject, payload)

    encoded_message = _build_email_message(to, subject, body, cc)
    gmail_service = _google_service("gmail", "v1")
    draft = (
        gmail_service.users()
        .drafts()
        .create(userId="me", body={"message": {"raw": encoded_message}})
        .execute()
    )
    return _executed_result(
        "create_gmail_draft",
        subject,
        draft["id"],
        "https://mail.google.com/mail/u/0/#drafts",
        {"message_id": draft.get("message", {}).get("id")},
    )


def get_gmail_draft(draft_id: str, execute: bool = False) -> dict:
    """Read a Gmail draft, or return an approval-required plan."""
    payload = {"draft_id": draft_id}
    if not execute:
        return _planned_result("get_gmail_draft", draft_id, payload)

    gmail_service = _google_service("gmail", "v1")
    draft = gmail_service.users().drafts().get(userId="me", id=draft_id).execute()
    return {
        "status": "success",
        "operation": "get_gmail_draft",
        "requires_approval": False,
        "executed": True,
        "draft": draft,
    }


def update_gmail_draft(
    draft_id: str,
    to: str,
    subject: str,
    body: str,
    cc: str = "",
    execute: bool = False,
) -> dict:
    """Update a Gmail draft, or return an approval-required plan."""
    payload = {"draft_id": draft_id, "to": to, "cc": cc, "subject": subject, "body": body}
    if not execute:
        return _planned_result("update_gmail_draft", draft_id, payload)

    encoded_message = _build_email_message(to, subject, body, cc)
    gmail_service = _google_service("gmail", "v1")
    draft = (
        gmail_service.users()
        .drafts()
        .update(userId="me", id=draft_id, body={"id": draft_id, "message": {"raw": encoded_message}})
        .execute()
    )
    return _executed_result(
        "update_gmail_draft",
        subject,
        draft["id"],
        "https://mail.google.com/mail/u/0/#drafts",
        {"message_id": draft.get("message", {}).get("id")},
    )


def delete_gmail_draft(draft_id: str, execute: bool = False) -> dict:
    """Delete a Gmail draft, or return an approval-required plan."""
    payload = {"draft_id": draft_id}
    if not execute:
        return _planned_result("delete_gmail_draft", draft_id, payload)

    gmail_service = _google_service("gmail", "v1")
    gmail_service.users().drafts().delete(userId="me", id=draft_id).execute()
    return _deleted_result("delete_gmail_draft", draft_id, draft_id, permanent=True)


def create_calendar_draft(
    summary: str,
    start_datetime: str,
    end_datetime: str,
    attendee_emails_json: str = "",
    description: str = "",
    timezone: str = "UTC",
    calendar_id: str = "primary",
    execute: bool = False,
) -> dict:
    """Create a Calendar event draft, or return an approval-required plan."""
    attendee_emails = _parse_json_list(attendee_emails_json, [])
    event = {
        "summary": summary,
        "description": description,
        "start": {"dateTime": start_datetime, "timeZone": timezone},
        "end": {"dateTime": end_datetime, "timeZone": timezone},
        "attendees": [{"email": email} for email in attendee_emails],
    }
    payload = {"calendar_id": calendar_id, "event": event}
    if not execute:
        return _planned_result("create_calendar_draft", summary, payload)

    calendar_service = _google_service("calendar", "v3")
    created_event = (
        calendar_service.events()
        .insert(calendarId=calendar_id, body=event, sendUpdates="none")
        .execute()
    )
    return _executed_result(
        "create_calendar_draft",
        summary,
        created_event["id"],
        created_event.get("htmlLink", _workspace_url("calendar", created_event["id"])),
    )


def list_calendar_events(
    calendar_id: str = "primary",
    time_min: str = "",
    time_max: str = "",
    query: str = "",
    max_results: int = 50,
    execute: bool = False,
) -> dict:
    """List Google Calendar events, optionally filtered by time range or text query.

    Args:
        calendar_id: Calendar ID (default "primary").
        time_min: RFC3339 lower bound (e.g. "2026-05-01T00:00:00Z").
        time_max: RFC3339 upper bound.
        query: Free-text search within event fields.
        max_results: Maximum events to return.
        execute: If False, return a plan; if True, call the API.

    Returns:
        dict with list of calendar events.
    """
    payload = {
        "calendar_id": calendar_id,
        "time_min": time_min,
        "time_max": time_max,
        "query": query,
        "max_results": max_results,
    }
    if not execute:
        return _planned_result("list_calendar_events", "Calendar events", payload)

    calendar_service = _google_service("calendar", "v3")
    kwargs: dict[str, Any] = {
        "calendarId": calendar_id,
        "maxResults": max_results,
        "singleEvents": True,
        "orderBy": "startTime",
    }
    if time_min:
        kwargs["timeMin"] = time_min
    if time_max:
        kwargs["timeMax"] = time_max
    if query:
        kwargs["q"] = query

    response = calendar_service.events().list(**kwargs).execute()
    return {
        "status": "success",
        "operation": "list_calendar_events",
        "requires_approval": False,
        "executed": True,
        "events": response.get("items", []),
    }


def get_calendar_event(calendar_id: str, event_id: str, execute: bool = False) -> dict:
    """Read a Calendar event, or return an approval-required plan."""
    payload = {"calendar_id": calendar_id, "event_id": event_id}
    if not execute:
        return _planned_result("get_calendar_event", event_id, payload)

    calendar_service = _google_service("calendar", "v3")
    event = calendar_service.events().get(calendarId=calendar_id, eventId=event_id).execute()
    return {
        "status": "success",
        "operation": "get_calendar_event",
        "requires_approval": False,
        "executed": True,
        "event": event,
    }


def update_calendar_event(
    calendar_id: str,
    event_id: str,
    summary: str = "",
    start_datetime: str = "",
    end_datetime: str = "",
    attendee_emails_json: str = "",
    description: str = "",
    timezone: str = "UTC",
    execute: bool = False,
) -> dict:
    """Patch a Calendar event, or return an approval-required plan."""
    attendee_emails = _parse_json_list(attendee_emails_json, [])
    event_patch: dict[str, Any] = {}
    if summary:
        event_patch["summary"] = summary
    if description:
        event_patch["description"] = description
    if start_datetime:
        event_patch["start"] = {"dateTime": start_datetime, "timeZone": timezone}
    if end_datetime:
        event_patch["end"] = {"dateTime": end_datetime, "timeZone": timezone}
    if attendee_emails:
        event_patch["attendees"] = [{"email": email} for email in attendee_emails]

    payload = {"calendar_id": calendar_id, "event_id": event_id, "event_patch": event_patch}
    if not execute:
        return _planned_result("update_calendar_event", event_id, payload)

    calendar_service = _google_service("calendar", "v3")
    event = (
        calendar_service.events()
        .patch(calendarId=calendar_id, eventId=event_id, body=event_patch, sendUpdates="none")
        .execute()
    )
    return _executed_result(
        "update_calendar_event",
        event.get("summary", event_id),
        event["id"],
        event.get("htmlLink", _workspace_url("calendar", event["id"])),
    )


def delete_calendar_event(calendar_id: str, event_id: str, execute: bool = False) -> dict:
    """Delete a Calendar event without notifying attendees, or return a plan."""
    payload = {"calendar_id": calendar_id, "event_id": event_id}
    if not execute:
        return _planned_result("delete_calendar_event", event_id, payload)

    calendar_service = _google_service("calendar", "v3")
    calendar_service.events().delete(calendarId=calendar_id, eventId=event_id, sendUpdates="none").execute()
    return _deleted_result("delete_calendar_event", event_id, event_id, permanent=True)


def create_task_list(title: str, execute: bool = False) -> dict:
    """Create a Google Tasks task list, or return an approval-required plan."""
    payload = {"title": title}
    if not execute:
        return _planned_result("create_task_list", title, payload)

    tasks_service = _google_service("tasks", "v1")
    task_list = tasks_service.tasklists().insert(body={"title": title}).execute()
    return _executed_result("create_task_list", title, task_list["id"], task_list.get("selfLink", ""))


def list_task_lists(max_results: int = 100, execute: bool = False) -> dict:
    """List Google Tasks task lists, or return an approval-required plan."""
    payload = {"max_results": max_results}
    if not execute:
        return _planned_result("list_task_lists", "Google Tasks lists", payload)

    tasks_service = _google_service("tasks", "v1")
    response = tasks_service.tasklists().list(maxResults=max_results).execute()
    return {
        "status": "success",
        "operation": "list_task_lists",
        "requires_approval": False,
        "executed": True,
        "task_lists": response.get("items", []),
    }


def get_task_list(tasklist_id: str, execute: bool = False) -> dict:
    """Read a Google Tasks task list, or return an approval-required plan."""
    payload = {"tasklist_id": tasklist_id}
    if not execute:
        return _planned_result("get_task_list", tasklist_id, payload)

    tasks_service = _google_service("tasks", "v1")
    task_list = tasks_service.tasklists().get(tasklist=tasklist_id).execute()
    return {"status": "success", "operation": "get_task_list", "requires_approval": False, "executed": True, "task_list": task_list}


def update_task_list(tasklist_id: str, title: str, execute: bool = False) -> dict:
    """Update a Google Tasks task list, or return an approval-required plan."""
    payload = {"tasklist_id": tasklist_id, "title": title}
    if not execute:
        return _planned_result("update_task_list", tasklist_id, payload)

    tasks_service = _google_service("tasks", "v1")
    task_list = tasks_service.tasklists().patch(tasklist=tasklist_id, body={"title": title}).execute()
    return _executed_result("update_task_list", title, task_list["id"], task_list.get("selfLink", ""))


def delete_task_list(tasklist_id: str, execute: bool = False) -> dict:
    """Delete a Google Tasks task list, or return an approval-required plan."""
    payload = {"tasklist_id": tasklist_id}
    if not execute:
        return _planned_result("delete_task_list", tasklist_id, payload)

    tasks_service = _google_service("tasks", "v1")
    tasks_service.tasklists().delete(tasklist=tasklist_id).execute()
    return _deleted_result("delete_task_list", tasklist_id, tasklist_id, permanent=True)


def create_task(tasklist_id: str, title: str, notes: str = "", due: str = "", execute: bool = False) -> dict:
    """Create a Google Tasks task, or return an approval-required plan."""
    body = {"title": title}
    if notes:
        body["notes"] = notes
    if due:
        body["due"] = due
    payload = {"tasklist_id": tasklist_id, "task": body}
    if not execute:
        return _planned_result("create_task", title, payload)

    tasks_service = _google_service("tasks", "v1")
    task = tasks_service.tasks().insert(tasklist=tasklist_id, body=body).execute()
    return _executed_result("create_task", title, task["id"], task.get("selfLink", ""))


def list_tasks(tasklist_id: str, max_results: int = 100, execute: bool = False) -> dict:
    """List tasks in a Google Tasks task list, or return an approval-required plan."""
    payload = {"tasklist_id": tasklist_id, "max_results": max_results}
    if not execute:
        return _planned_result("list_tasks", tasklist_id, payload)

    tasks_service = _google_service("tasks", "v1")
    response = tasks_service.tasks().list(tasklist=tasklist_id, maxResults=max_results).execute()
    return {"status": "success", "operation": "list_tasks", "requires_approval": False, "executed": True, "tasks": response.get("items", [])}


def get_task(tasklist_id: str, task_id: str, execute: bool = False) -> dict:
    """Read a Google Tasks task, or return an approval-required plan."""
    payload = {"tasklist_id": tasklist_id, "task_id": task_id}
    if not execute:
        return _planned_result("get_task", task_id, payload)

    tasks_service = _google_service("tasks", "v1")
    task = tasks_service.tasks().get(tasklist=tasklist_id, task=task_id).execute()
    return {"status": "success", "operation": "get_task", "requires_approval": False, "executed": True, "task": task}


def update_task(
    tasklist_id: str,
    task_id: str,
    title: str = "",
    notes: str = "",
    status: str = "",
    due: str = "",
    execute: bool = False,
) -> dict:
    """Patch a Google Tasks task, or return an approval-required plan."""
    body = {}
    if title:
        body["title"] = title
    if notes:
        body["notes"] = notes
    if status:
        body["status"] = status
    if due:
        body["due"] = due
    payload = {"tasklist_id": tasklist_id, "task_id": task_id, "task_patch": body}
    if not execute:
        return _planned_result("update_task", task_id, payload)

    tasks_service = _google_service("tasks", "v1")
    task = tasks_service.tasks().patch(tasklist=tasklist_id, task=task_id, body=body).execute()
    return _executed_result("update_task", task.get("title", task_id), task["id"], task.get("selfLink", ""))


def delete_task(tasklist_id: str, task_id: str, execute: bool = False) -> dict:
    """Delete a Google Tasks task, or return an approval-required plan."""
    payload = {"tasklist_id": tasklist_id, "task_id": task_id}
    if not execute:
        return _planned_result("delete_task", task_id, payload)

    tasks_service = _google_service("tasks", "v1")
    tasks_service.tasks().delete(tasklist=tasklist_id, task=task_id).execute()
    return _deleted_result("delete_task", task_id, task_id, permanent=True)


def create_chat_space(display_name: str, space_type: str = "SPACE", execute: bool = False) -> dict:
    """Create a Google Chat space, or return an approval-required plan."""
    body = {"displayName": display_name, "spaceType": space_type}
    payload = {"space": body}
    if not execute:
        return _planned_result("create_chat_space", display_name, payload)

    chat_service = _google_service("chat", "v1")
    space = chat_service.spaces().create(body=body).execute()
    return _executed_result("create_chat_space", display_name, space["name"], space.get("spaceUri", ""), {"space": space})


def list_chat_spaces(page_size: int = 100, execute: bool = False) -> dict:
    """List Google Chat spaces, or return an approval-required plan."""
    payload = {"page_size": page_size}
    if not execute:
        return _planned_result("list_chat_spaces", "Google Chat spaces", payload)

    chat_service = _google_service("chat", "v1")
    response = chat_service.spaces().list(pageSize=page_size).execute()
    return {"status": "success", "operation": "list_chat_spaces", "requires_approval": False, "executed": True, "spaces": response.get("spaces", [])}


def get_chat_space(space_name: str, execute: bool = False) -> dict:
    """Read a Google Chat space, or return an approval-required plan."""
    payload = {"space_name": space_name}
    if not execute:
        return _planned_result("get_chat_space", space_name, payload)

    chat_service = _google_service("chat", "v1")
    space = chat_service.spaces().get(name=space_name).execute()
    return {"status": "success", "operation": "get_chat_space", "requires_approval": False, "executed": True, "space": space}


def update_chat_space(space_name: str, display_name: str, execute: bool = False) -> dict:
    """Update a Google Chat space display name, or return an approval-required plan."""
    payload = {"space_name": space_name, "display_name": display_name}
    if not execute:
        return _planned_result("update_chat_space", space_name, payload)

    chat_service = _google_service("chat", "v1")
    space = chat_service.spaces().patch(name=space_name, updateMask="displayName", body={"displayName": display_name}).execute()
    return _executed_result("update_chat_space", display_name, space["name"], space.get("spaceUri", ""), {"space": space})


def delete_chat_space(space_name: str, execute: bool = False) -> dict:
    """Delete a Google Chat space, or return an approval-required plan."""
    payload = {"space_name": space_name}
    if not execute:
        return _planned_result("delete_chat_space", space_name, payload)

    chat_service = _google_service("chat", "v1")
    chat_service.spaces().delete(name=space_name).execute()
    return _deleted_result("delete_chat_space", space_name, space_name, permanent=True)


def create_chat_message(space_name: str, text: str, execute: bool = False) -> dict:
    """Create a Google Chat message, or return an approval-required plan."""
    payload = {"space_name": space_name, "text": text}
    if not execute:
        return _planned_result("create_chat_message", space_name, payload)

    chat_service = _google_service("chat", "v1")
    message = chat_service.spaces().messages().create(parent=space_name, body={"text": text}).execute()
    return _executed_result("create_chat_message", space_name, message["name"], "", {"message": message})


def get_chat_message(message_name: str, execute: bool = False) -> dict:
    """Read a Google Chat message, or return an approval-required plan."""
    payload = {"message_name": message_name}
    if not execute:
        return _planned_result("get_chat_message", message_name, payload)

    chat_service = _google_service("chat", "v1")
    message = chat_service.spaces().messages().get(name=message_name).execute()
    return {"status": "success", "operation": "get_chat_message", "requires_approval": False, "executed": True, "message": message}


def update_chat_message(message_name: str, text: str, execute: bool = False) -> dict:
    """Update a Google Chat message, or return an approval-required plan."""
    payload = {"message_name": message_name, "text": text}
    if not execute:
        return _planned_result("update_chat_message", message_name, payload)

    chat_service = _google_service("chat", "v1")
    message = chat_service.spaces().messages().patch(name=message_name, updateMask="text", body={"text": text}).execute()
    return _executed_result("update_chat_message", message_name, message["name"], "", {"message": message})


def delete_chat_message(message_name: str, execute: bool = False) -> dict:
    """Delete a Google Chat message, or return an approval-required plan."""
    payload = {"message_name": message_name}
    if not execute:
        return _planned_result("delete_chat_message", message_name, payload)

    chat_service = _google_service("chat", "v1")
    chat_service.spaces().messages().delete(name=message_name).execute()
    return _deleted_result("delete_chat_message", message_name, message_name, permanent=True)


def create_meet_space(display_name: str = "", execute: bool = False) -> dict:
    """Create a Google Meet meeting space, or return an approval-required plan."""
    payload = {"display_name": display_name}
    if not execute:
        return _planned_result("create_meet_space", display_name or "Meet space", payload)

    meet_service = _google_service("meet", "v2")
    space = meet_service.spaces().create(body={}).execute()
    return _executed_result("create_meet_space", display_name or space["name"], space["name"], space.get("meetingUri", ""), {"space": space})


def get_meet_space(space_name: str, execute: bool = False) -> dict:
    """Read a Google Meet space, or return an approval-required plan."""
    payload = {"space_name": space_name}
    if not execute:
        return _planned_result("get_meet_space", space_name, payload)

    meet_service = _google_service("meet", "v2")
    space = meet_service.spaces().get(name=space_name).execute()
    return {"status": "success", "operation": "get_meet_space", "requires_approval": False, "executed": True, "space": space}


def end_meet_active_conference(space_name: str, execute: bool = False) -> dict:
    """End the active Google Meet conference for a space, or return an approval-required plan."""
    payload = {"space_name": space_name}
    if not execute:
        return _planned_result("end_meet_active_conference", space_name, payload)

    meet_service = _google_service("meet", "v2")
    meet_service.spaces().endActiveConference(name=space_name).execute()
    return _executed_result("end_meet_active_conference", space_name, space_name, "")


def create_keep_note(title: str, text: str, execute: bool = False) -> dict:
    """Create a Google Keep note, or return an approval-required plan."""
    body = {"title": title, "body": {"text": {"text": text}}}
    payload = {"note": body}
    if not execute:
        return _planned_result("create_keep_note", title, payload)

    keep_service = _google_service("keep", "v1")
    note = keep_service.notes().create(body=body).execute()
    return _executed_result("create_keep_note", title, note["name"], "", {"note": note})


def list_keep_notes(page_size: int = 100, filter_query: str = "", execute: bool = False) -> dict:
    """List Google Keep notes, or return an approval-required plan."""
    payload = {"page_size": page_size, "filter_query": filter_query}
    if not execute:
        return _planned_result("list_keep_notes", "Google Keep notes", payload)

    keep_service = _google_service("keep", "v1")
    response = keep_service.notes().list(pageSize=page_size, filter=filter_query or None).execute()
    return {"status": "success", "operation": "list_keep_notes", "requires_approval": False, "executed": True, "notes": response.get("notes", [])}


def get_keep_note(note_name: str, execute: bool = False) -> dict:
    """Read a Google Keep note, or return an approval-required plan."""
    payload = {"note_name": note_name}
    if not execute:
        return _planned_result("get_keep_note", note_name, payload)

    keep_service = _google_service("keep", "v1")
    note = keep_service.notes().get(name=note_name).execute()
    return {"status": "success", "operation": "get_keep_note", "requires_approval": False, "executed": True, "note": note}


def delete_keep_note(note_name: str, execute: bool = False) -> dict:
    """Delete a Google Keep note, or return an approval-required plan."""
    payload = {"note_name": note_name}
    if not execute:
        return _planned_result("delete_keep_note", note_name, payload)

    keep_service = _google_service("keep", "v1")
    keep_service.notes().delete(name=note_name).execute()
    return _deleted_result("delete_keep_note", note_name, note_name, permanent=True)


def list_gmail_messages(query: str = "", max_results: int = 20, execute: bool = False) -> dict:
    """List Gmail messages matching a query, or return an approval-required plan."""
    payload = {"query": query, "max_results": max_results}
    if not execute:
        return _planned_result("list_gmail_messages", "Gmail messages", payload)

    gmail_service = _google_service("gmail", "v1")
    response = gmail_service.users().messages().list(userId="me", q=query or None, maxResults=max_results).execute()
    return {"status": "success", "operation": "list_gmail_messages", "requires_approval": False, "executed": True, "messages": response.get("messages", [])}


def get_gmail_message(message_id: str, format_type: str = "metadata", execute: bool = False) -> dict:
    """Read a Gmail message, or return an approval-required plan."""
    payload = {"message_id": message_id, "format_type": format_type}
    if not execute:
        return _planned_result("get_gmail_message", message_id, payload)

    gmail_service = _google_service("gmail", "v1")
    message = gmail_service.users().messages().get(userId="me", id=message_id, format=format_type).execute()
    return {"status": "success", "operation": "get_gmail_message", "requires_approval": False, "executed": True, "message": message}


def send_gmail_message(to: str, subject: str, body: str, cc: str = "", execute: bool = False) -> dict:
    """Send a Gmail message, or return an approval-required plan."""
    payload = {"to": to, "cc": cc, "subject": subject, "body": body}
    if not execute:
        return _planned_result("send_gmail_message", subject, payload)

    encoded_message = _build_email_message(to, subject, body, cc)
    gmail_service = _google_service("gmail", "v1")
    message = gmail_service.users().messages().send(userId="me", body={"raw": encoded_message}).execute()
    return _executed_result("send_gmail_message", subject, message["id"], "https://mail.google.com/mail/u/0/#sent", {"message": message})


def modify_gmail_message_labels(
    message_id: str,
    add_label_ids_json: str = "",
    remove_label_ids_json: str = "",
    execute: bool = False,
) -> dict:
    """Modify Gmail message labels, or return an approval-required plan."""
    add_label_ids = _parse_json_list(add_label_ids_json, [])
    remove_label_ids = _parse_json_list(remove_label_ids_json, [])
    payload = {"message_id": message_id, "add_label_ids": add_label_ids, "remove_label_ids": remove_label_ids}
    if not execute:
        return _planned_result("modify_gmail_message_labels", message_id, payload)

    gmail_service = _google_service("gmail", "v1")
    message = (
        gmail_service.users()
        .messages()
        .modify(
            userId="me",
            id=message_id,
            body={"addLabelIds": add_label_ids, "removeLabelIds": remove_label_ids},
        )
        .execute()
    )
    return _executed_result("modify_gmail_message_labels", message_id, message["id"], "", {"message": message})


def trash_gmail_message(message_id: str, execute: bool = False) -> dict:
    """Move a Gmail message to trash, or return an approval-required plan."""
    payload = {"message_id": message_id}
    if not execute:
        return _planned_result("trash_gmail_message", message_id, payload)

    gmail_service = _google_service("gmail", "v1")
    message = gmail_service.users().messages().trash(userId="me", id=message_id).execute()
    return _executed_result("trash_gmail_message", message_id, message["id"], "", {"message": message})


def create_notebooklm_notebook(
    project_number: str,
    title: str,
    location: str = "global",
    endpoint_location: str = "global",
    execute: bool = False,
) -> dict:
    """Create a NotebookLM Enterprise notebook, or return an approval-required plan."""
    payload = {"project_number": project_number, "title": title, "location": location, "endpoint_location": endpoint_location}
    if not execute:
        return _planned_result("create_notebooklm_notebook", title, payload)

    url = f"https://{endpoint_location}-discoveryengine.googleapis.com/v1alpha/projects/{project_number}/locations/{location}/notebooks"
    notebook = _authed_json_request("POST", url, {"title": title})
    return _executed_result("create_notebooklm_notebook", title, notebook.get("name", ""), "", {"notebook": notebook})


def get_notebooklm_notebook(
    project_number: str,
    notebook_id: str,
    location: str = "global",
    endpoint_location: str = "global",
    execute: bool = False,
) -> dict:
    """Read a NotebookLM Enterprise notebook, or return an approval-required plan."""
    payload = {"project_number": project_number, "notebook_id": notebook_id, "location": location, "endpoint_location": endpoint_location}
    if not execute:
        return _planned_result("get_notebooklm_notebook", notebook_id, payload)

    url = f"https://{endpoint_location}-discoveryengine.googleapis.com/v1alpha/projects/{project_number}/locations/{location}/notebooks/{notebook_id}"
    notebook = _authed_json_request("GET", url)
    return {"status": "success", "operation": "get_notebooklm_notebook", "requires_approval": False, "executed": True, "notebook": notebook}


def share_notebooklm_notebook(
    project_number: str,
    notebook_id: str,
    account_roles_json: str,
    location: str = "global",
    endpoint_location: str = "global",
    execute: bool = False,
) -> dict:
    """Share a NotebookLM Enterprise notebook, or return an approval-required plan."""
    account_roles = _parse_json_list(account_roles_json, [])
    payload = {"project_number": project_number, "notebook_id": notebook_id, "account_roles": account_roles}
    if not execute:
        return _planned_result("share_notebooklm_notebook", notebook_id, payload)

    url = f"https://{endpoint_location}-discoveryengine.googleapis.com/v1alpha/projects/{project_number}/locations/{location}/notebooks/{notebook_id}:share"
    response = _authed_json_request("POST", url, {"accountAndRoles": account_roles})
    return _executed_result("share_notebooklm_notebook", notebook_id, notebook_id, "", {"response": response})


def delete_notebooklm_notebooks(
    project_number: str,
    notebook_names_json: str,
    location: str = "global",
    endpoint_location: str = "global",
    execute: bool = False,
) -> dict:
    """Delete NotebookLM Enterprise notebooks in batch, or return an approval-required plan."""
    notebook_names = _parse_json_list(notebook_names_json, [])
    payload = {"project_number": project_number, "location": location, "notebook_names": notebook_names}
    if not execute:
        return _planned_result("delete_notebooklm_notebooks", project_number, payload)

    url = f"https://{endpoint_location}-discoveryengine.googleapis.com/v1alpha/projects/{project_number}/locations/{location}/notebooks:batchDelete"
    response = _authed_json_request("POST", url, {"names": notebook_names})
    return _executed_result("delete_notebooklm_notebooks", project_number, project_number, "", {"response": response})


def call_appsheet_table_action(
    app_id: str,
    table_name: str,
    action: str,
    rows_json: str = "",
    properties_json: str = "",
    region: str = "api.appsheet.com",
    app_access_key: str = "",
    execute: bool = False,
) -> dict:
    """Call AppSheet Find/Add/Edit/Delete/Action for a table, or return an approval-required plan."""
    rows = _parse_json_list(rows_json, [])
    properties = json.loads(properties_json) if properties_json else {}
    payload = {"app_id": app_id, "table_name": table_name, "action": action, "properties": properties, "rows": rows}
    if not execute:
        return _planned_result("call_appsheet_table_action", f"{table_name}:{action}", payload)

    access_key = app_access_key or os.getenv("APPSHEET_APP_ACCESS_KEY", "")
    if not access_key:
        raise ValueError("AppSheet app access key is required.")
    response = requests.post(
        f"https://{region}/api/v2/apps/{app_id}/tables/{table_name}/Action",
        headers={"ApplicationAccessKey": access_key, "Content-Type": "application/json"},
        json={"Action": action, "Properties": properties, "Rows": rows},
        timeout=30,
    )
    response.raise_for_status()
    return {
        "status": "success",
        "operation": "call_appsheet_table_action",
        "requires_approval": False,
        "executed": True,
        "response": response.json() if response.content else {},
    }


def plan_google_vids_action(action: str, details: str = "") -> dict:
    """Record that Google Vids has no public CRUD API tool implementation."""
    return _planned_result(
        "plan_google_vids_action",
        action,
        {"details": details, "limitation": "No stable public Google Vids CRUD API is currently wired."},
    )


def plan_google_sites_action(action: str, details: str = "") -> dict:
    """Record that Google Sites API support is limited to legacy/classic APIs."""
    return _planned_result(
        "plan_google_sites_action",
        action,
        {"details": details, "limitation": "New Google Sites does not have a full modern CRUD API tool wired."},
    )


# ---------------------------------------------------------------------------
# Domain-grouped tool lists for the restructured agent hierarchy
# ---------------------------------------------------------------------------

DRIVE_TOOLS = [
    create_drive_folder,
    list_drive_files,
    get_drive_file,
    update_drive_file_metadata,
    delete_drive_file,
]

DOCS_TOOLS = [
    create_google_doc,
    get_google_doc,
    update_google_doc_content,
    delete_google_doc,
]

FORMS_TOOLS = [
    create_google_form,
    get_google_form,
    update_google_form,
    delete_google_form,
]

SHEETS_TOOLS = [
    create_google_sheet,
    get_google_sheet_values,
    update_google_sheet_values,
    update_sheet_crm,
    delete_google_sheet,
]

SLIDES_TOOLS = [
    create_google_slide_deck,
    get_google_slide_deck,
    update_google_slide_deck,
    delete_google_slide_deck,
]

GMAIL_TOOLS = [
    create_gmail_draft,
    get_gmail_draft,
    update_gmail_draft,
    delete_gmail_draft,
    list_gmail_messages,
    get_gmail_message,
    send_gmail_message,
    modify_gmail_message_labels,
    trash_gmail_message,
]

CALENDAR_TOOLS = [
    create_calendar_draft,
    list_calendar_events,
    get_calendar_event,
    update_calendar_event,
    delete_calendar_event,
]

CHAT_MEET_TOOLS = [
    create_chat_space,
    list_chat_spaces,
    get_chat_space,
    update_chat_space,
    delete_chat_space,
    create_chat_message,
    get_chat_message,
    update_chat_message,
    delete_chat_message,
    create_meet_space,
    get_meet_space,
    end_meet_active_conference,
]

PRODUCTIVITY_TOOLS = [
    create_task_list,
    list_task_lists,
    get_task_list,
    update_task_list,
    delete_task_list,
    create_task,
    list_tasks,
    get_task,
    update_task,
    delete_task,
    create_keep_note,
    list_keep_notes,
    get_keep_note,
    delete_keep_note,
    create_notebooklm_notebook,
    get_notebooklm_notebook,
    share_notebooklm_notebook,
    delete_notebooklm_notebooks,
    call_appsheet_table_action,
    plan_google_vids_action,
    plan_google_sites_action,
]

# Flat list kept for backward compatibility
WORKSPACE_TOOLS = [
    require_oauth_token,
    draft_workspace_actions,
    *DRIVE_TOOLS,
    *DOCS_TOOLS,
    *FORMS_TOOLS,
    *SHEETS_TOOLS,
    *SLIDES_TOOLS,
    *GMAIL_TOOLS,
    *CALENDAR_TOOLS,
    *CHAT_MEET_TOOLS,
    *PRODUCTIVITY_TOOLS,
]
