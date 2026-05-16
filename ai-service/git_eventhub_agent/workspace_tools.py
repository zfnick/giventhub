from __future__ import annotations

import base64
from contextvars import ContextVar
import io
import json
import mimetypes
import os
from email.message import EmailMessage
from typing import Any

import requests
import google.auth.credentials
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload

from .schemas import WorkspaceDraft


DRIVE_FOLDER_MIME_TYPE = "application/vnd.google-apps.folder"
GOOGLE_DOC_MIME_TYPE = "application/vnd.google-apps.document"
GOOGLE_FORM_MIME_TYPE = "application/vnd.google-apps.form"
GOOGLE_SLIDES_MIME_TYPE = "application/vnd.google-apps.presentation"
GOOGLE_SHEET_MIME_TYPE = "application/vnd.google-apps.spreadsheet"
OAUTH_TOKEN_REQUIRED_MESSAGE = "oauth_token is required before planning or executing Google Workspace actions."
REGISTERED_OAUTH_TOKEN_PLACEHOLDER = "<registered>"
_WORKSPACE_OAUTH_TOKEN: ContextVar[str] = ContextVar("workspace_oauth_token", default="")
_WORKSPACE_FILE_STORE: ContextVar[dict] = ContextVar("workspace_file_store", default={})

API_SCOPES = {
    "calendar": ["https://www.googleapis.com/auth/calendar"],
    "docs": ["https://www.googleapis.com/auth/documents"],
    "drive": ["https://www.googleapis.com/auth/drive"],
    "forms": ["https://www.googleapis.com/auth/forms.body"],
    "gmail": ["https://www.googleapis.com/auth/gmail.modify"],
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


def _drive_query_string(value: str) -> str:
    return value.replace("\\", "\\\\").replace("'", "\\'")


def normalize_oauth_token(oauth_token: str) -> str:
    """Normalize token values from headers, Swagger UI, and agent prompts."""
    token = oauth_token.strip().strip('"').strip("'").strip()
    while token.lower().startswith("bearer "):
        token = token[7:].strip()
    return token


def require_oauth_token(oauth_token: str) -> dict:
    """Register the end user's OAuth token before any Workspace action."""
    token = normalize_oauth_token(oauth_token)
    if not token:
        raise ValueError(OAUTH_TOKEN_REQUIRED_MESSAGE)
    if token == REGISTERED_OAUTH_TOKEN_PLACEHOLDER:
        token = _WORKSPACE_OAUTH_TOKEN.get().strip()
        if not token:
            raise ValueError(OAUTH_TOKEN_REQUIRED_MESSAGE)
    else:
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


class _StaticCredentials(google.auth.credentials.Credentials):
    """Minimal credentials that hold a pre-fetched access token and never refresh."""

    def __init__(self, token: str):
        super().__init__()
        self.token = token

    def refresh(self, request):
        # Token is already set; nothing to do.
        pass

    @property
    def valid(self):
        return bool(self.token)

    @property
    def expired(self):
        return False


_service_cache: dict[tuple[str, str, str], Any] = {}


def _google_service(api_name: str, version: str) -> Any:
    """Build a dynamic Google API client resource from the user's token.

    googleapiclient resources expose API methods dynamically from discovery
    documents, so static analyzers cannot know about members like files() or
    documents(). Returning Any keeps that dynamic boundary contained here.

    Results are cached per (api_name, version, token) to avoid repeated
    discovery-document fetches (~300-800ms each).
    """
    token = _require_oauth_token()
    cache_key = (api_name, version, token)
    cached = _service_cache.get(cache_key)
    if cached is not None:
        return cached
    creds = _StaticCredentials(token=token)
    if api_name in {"forms"}:
        svc = build(api_name, version, credentials=creds, static_discovery=False)
    else:
        svc = build(api_name, version, credentials=creds)
    _service_cache[cache_key] = svc
    return svc


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


def _resolve_drive_file_id(identifier: str, mime_type: str = "") -> str:
    """Resolve a Drive-backed Google app title to an ID when possible."""
    candidate = identifier.strip()
    if not candidate:
        raise ValueError("A file ID or title is required.")

    query_parts = [f"name = '{_drive_query_string(candidate)}'", "trashed = false"]
    if mime_type:
        query_parts.append(f"mimeType = '{mime_type}'")

    drive_service = _google_service("drive", "v3")
    response = (
        drive_service.files()
        .list(q=" and ".join(query_parts), pageSize=2, fields="files(id, name, mimeType, webViewLink)")
        .execute()
    )
    files = response.get("files", [])
    if len(files) == 1:
        return files[0]["id"]
    return candidate


def _parse_json_list(raw_json: str, default: list) -> list:
    if not raw_json:
        return default
    parsed = json.loads(raw_json)
    if not isinstance(parsed, list):
        raise ValueError("Expected a JSON list.")
    return parsed


def _decode_base64_file(content_base64: str) -> bytes:
    if not content_base64:
        raise ValueError("content_base64 is required for file upload.")
    _, _, encoded = content_base64.partition(",")
    raw_content = encoded if content_base64.strip().startswith("data:") else content_base64
    compact_content = "".join(raw_content.split())
    try:
        return base64.b64decode(compact_content, validate=True)
    except ValueError as exc:
        raise ValueError("content_base64 must be valid base64 data.") from exc


def _mime_type_for(file_name: str, mime_type: str = "") -> str:
    if mime_type:
        return mime_type
    guessed_type, _ = mimetypes.guess_type(file_name)
    return guessed_type or "application/octet-stream"


def _upload_payload(
    file_name: str,
    content_base64: str,
    mime_type: str = "",
    folder_id: str = "",
    description: str = "",
) -> dict[str, Any]:
    return {
        "file_name": file_name,
        "mime_type": _mime_type_for(file_name, mime_type),
        "folder_id": folder_id,
        "description": description,
        "content_base64_chars": len(content_base64),
        "has_content": bool(content_base64),
    }


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
        if not isinstance(rec, dict):
            continue
        if rec.get("verification_status") == "unsupported":
            continue
        name = rec.get("name") or rec.get("title") or rec.get("summary")
        if not name:
            continue
        evidence = rec.get("evidence") or ["No supporting evidence provided."]
        drafts.append(
            WorkspaceDraft(
                type="gmail_draft",
                title=f"Reconnect with {name}",
                summary=f"Draft a warm follow-up citing: {evidence[0]}",
            )
        )
        drafts.append(
            WorkspaceDraft(
                type="calendar_draft",
                title=f"Follow-up meeting with {name}",
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


def upload_drive_file(
    file_name: str,
    content_base64: str,
    mime_type: str = "",
    folder_id: str = "",
    description: str = "",
    execute: bool = False,
) -> dict:
    """Upload one file to Google Drive from base64 content, or return a plan."""
    file_name = file_name.strip()
    if not file_name:
        raise ValueError("file_name is required for file upload.")
    payload = _upload_payload(file_name, content_base64, mime_type, folder_id, description)
    if not execute:
        return _planned_result("upload_drive_file", file_name, payload)

    # Check if content_base64 is a file store reference (e.g. "file_1")
    resolved_mime_type = payload["mime_type"]
    store = _WORKSPACE_FILE_STORE.get()
    if content_base64 in store:
        file_entry = store[content_base64]
        file_bytes = file_entry["bytes"]
        if not resolved_mime_type or resolved_mime_type == "application/octet-stream":
            resolved_mime_type = file_entry.get("mime_type", resolved_mime_type)
    else:
        file_bytes = _decode_base64_file(content_base64)
    metadata: dict[str, Any] = {"name": file_name}
    if folder_id:
        metadata["parents"] = [folder_id]
    if description:
        metadata["description"] = description

    media = MediaIoBaseUpload(io.BytesIO(file_bytes), mimetype=resolved_mime_type, resumable=False)
    drive_service = _google_service("drive", "v3")
    uploaded_file = (
        drive_service.files()
        .create(
            body=metadata,
            media_body=media,
            fields="id, name, mimeType, webViewLink, parents",
        )
        .execute()
    )
    return _executed_result(
        "upload_drive_file",
        uploaded_file.get("name", file_name),
        uploaded_file["id"],
        uploaded_file.get("webViewLink", ""),
        {"file": uploaded_file},
    )


def upload_drive_files(files_json: str, folder_id: str = "", execute: bool = False) -> dict:
    """Upload multiple files to Google Drive from a JSON list, or return a plan."""
    files = _parse_json_list(files_json, [])
    if not files:
        raise ValueError("At least one file is required for batch upload.")
    payload_files = []
    for file_entry in files:
        if not isinstance(file_entry, dict):
            raise ValueError("Each batch upload item must be a JSON object.")
        file_name = str(file_entry.get("file_name", "")).strip()
        if not file_name:
            raise ValueError("Each batch upload item requires file_name.")
        item_folder_id = str(file_entry.get("folder_id") or folder_id)
        payload_files.append(
            _upload_payload(
                file_name,
                str(file_entry.get("content_base64", "")),
                str(file_entry.get("mime_type", "")),
                item_folder_id,
                str(file_entry.get("description", "")),
            )
        )

    payload = {"files": payload_files, "folder_id": folder_id, "file_count": len(payload_files)}
    if not execute:
        return _planned_result("upload_drive_files", "Drive file batch upload", payload)

    uploaded_files = []
    for file_entry in files:
        uploaded_files.append(
            upload_drive_file(
                str(file_entry["file_name"]),
                str(file_entry.get("content_base64", "")),
                mime_type=str(file_entry.get("mime_type", "")),
                folder_id=str(file_entry.get("folder_id") or folder_id),
                description=str(file_entry.get("description", "")),
                execute=True,
            )
        )

    return {
        "status": "success",
        "operation": "upload_drive_files",
        "requires_approval": False,
        "executed": True,
        "file_count": len(uploaded_files),
        "files": uploaded_files,
    }


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

    # Forms API create() leaves the Drive file name as "Untitled form".
    # Rename it via Drive so the title is visible in Drive/folder views.
    drive_service = _google_service("drive", "v3")
    drive_service.files().update(fileId=form_id, body={"name": title}).execute()

    if folder_id:
        _move_drive_file(form_id, folder_id)

    return _executed_result(
        "create_google_form",
        title,
        form_id,
        _workspace_url("form", form_id),
        {"form_title": title},
    )


def get_google_form(form_id: str, execute: bool = False) -> dict:
    """Read a Google Form by ID or exact Drive title, or return an approval-required plan."""
    payload = {"form_id": form_id}
    if not execute:
        return _planned_result("get_google_form", form_id, payload)

    form_id = _resolve_drive_file_id(form_id, GOOGLE_FORM_MIME_TYPE)
    forms_service = _google_service("forms", "v1")
    form = forms_service.forms().get(formId=form_id).execute()
    return {
        "status": "success",
        "operation": "get_google_form",
        "requires_approval": False,
        "executed": True,
        "resource_id": form_id,
        "url": _workspace_url("form", form_id),
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


def _gmail_headers(message: dict) -> dict[str, str]:
    headers = message.get("payload", {}).get("headers", [])
    return {header.get("name", "").lower(): header.get("value", "") for header in headers}


def list_gmail_messages(query: str = "", max_results: int = 20, execute: bool = False) -> dict:
    """List Gmail messages matching a query, or return an approval-required plan.

    Uses batch API to fetch message metadata in one round-trip instead of N+1.
    """
    payload = {"query": query, "max_results": max_results}
    if not execute:
        return _planned_result("list_gmail_messages", "Gmail messages", payload)

    gmail_service = _google_service("gmail", "v1")
    response = gmail_service.users().messages().list(userId="me", q=query or None, maxResults=max_results).execute()
    message_ids = response.get("messages", [])
    if not message_ids:
        return {
            "status": "success",
            "operation": "list_gmail_messages",
            "requires_approval": False,
            "executed": True,
            "messages": [],
        }

    # Batch fetch all message metadata in one round-trip
    fetched: list[dict] = []

    def _on_message(request_id, resp, exception):
        if exception is not None:
            return
        fetched.append(resp)

    batch = gmail_service.new_batch_http_request(callback=_on_message)
    for item in message_ids:
        batch.add(
            gmail_service.users().messages().get(
                userId="me",
                id=item["id"],
                format="metadata",
                metadataHeaders=["From", "Subject", "Date"],
            )
        )
    batch.execute()

    messages = []
    for message in fetched:
        headers = _gmail_headers(message)
        messages.append(
            {
                "id": message.get("id", ""),
                "thread_id": message.get("threadId", ""),
                "title": headers.get("subject", ""),
                "from": headers.get("from", ""),
                "subject": headers.get("subject", ""),
                "date": headers.get("date", ""),
                "snippet": message.get("snippet", ""),
            }
        )
    return {
        "status": "success",
        "operation": "list_gmail_messages",
        "requires_approval": False,
        "executed": True,
        "messages": messages,
    }


def get_gmail_message(message_id: str, format_type: str = "metadata", execute: bool = False) -> dict:
    """Read a Gmail message, or return an approval-required plan."""
    payload = {"message_id": message_id, "format_type": format_type}
    if not execute:
        return _planned_result("get_gmail_message", message_id, payload)

    gmail_service = _google_service("gmail", "v1")
    kwargs: dict[str, Any] = {"userId": "me", "id": message_id, "format": format_type}
    if format_type == "metadata":
        kwargs["metadataHeaders"] = ["From", "Subject", "Date"]
    message = gmail_service.users().messages().get(**kwargs).execute()
    headers = _gmail_headers(message)
    return {
        "status": "success",
        "operation": "get_gmail_message",
        "requires_approval": False,
        "executed": True,
        "resource_id": message.get("id", message_id),
        "title": headers.get("subject", ""),
        "from": headers.get("from", ""),
        "subject": headers.get("subject", ""),
        "date": headers.get("date", ""),
        "snippet": message.get("snippet", ""),
        "message": message,
    }


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




# ---------------------------------------------------------------------------
# Domain-grouped tool lists for the restructured agent hierarchy
# ---------------------------------------------------------------------------

DRIVE_TOOLS = [
    create_drive_folder,
    upload_drive_file,
    upload_drive_files,
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
    *PRODUCTIVITY_TOOLS,
]
