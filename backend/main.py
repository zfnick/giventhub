"""gieventhub API — single-endpoint backend.

One POST /api/workspace endpoint that accepts:
  - Authorization: Bearer <token> header (required) — Google OAuth
    access token, or "dev" to auto-refresh from .env credentials
  - prompt      (required) — natural-language instruction
  - file_1..3   (optional) — file uploads from Swagger UI

The endpoint registers the OAuth token, then delegates to the ADK
root_agent (workspace_coordinator) which routes to the correct
domain sub-agent for all Google Workspace CRUD operations.
"""

from __future__ import annotations

import logging
import mimetypes
import os
import sys
import json
from pathlib import Path

import requests as http_requests
from dotenv import load_dotenv
from fastapi import Depends, FastAPI, File, Form, HTTPException, UploadFile
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.utils import get_openapi

# ---------------------------------------------------------------------------
# Make the ai-service package importable
# ---------------------------------------------------------------------------
AI_SERVICE_DIR = Path(__file__).resolve().parents[1] / "ai-service"
if str(AI_SERVICE_DIR) not in sys.path:
    sys.path.insert(0, str(AI_SERVICE_DIR))

# Load .env from ai-service (shared credentials)
load_dotenv(AI_SERVICE_DIR / ".env")

logger = logging.getLogger(__name__)

from google.adk.runners import Runner  # noqa: E402
from google.adk.sessions import InMemorySessionService  # noqa: E402
from google.genai import types as genai_types  # noqa: E402
from googleapiclient.errors import HttpError  # noqa: E402

from git_eventhub_agent.agent import root_agent  # noqa: E402
from git_eventhub_agent.workspace_tools import (
    normalize_oauth_token,
    require_oauth_token,
    _service_cache,
)  # noqa: E402


# ---------------------------------------------------------------------------
# FastAPI app
# ---------------------------------------------------------------------------
bearer_scheme = HTTPBearer(
    description=(
        'Google OAuth access token, or the literal word **dev** to '
        'auto-refresh from server-side .env credentials.'
    ),
)

app = FastAPI(
    title="gieventhub API",
    version="0.3.0",
    description="Single-endpoint backend that delegates to the ADK workspace coordinator.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def custom_openapi():
    """Patch file upload schemas so Swagger UI shows file pickers.

    FastAPI with OpenAPI 3.1 currently emits `contentMediaType` for UploadFile,
    which this Swagger UI renders as string inputs. `format: binary` is the
    interoperable shape Swagger expects for multipart file fields.
    """
    if app.openapi_schema:
        return app.openapi_schema

    schema = get_openapi(
        title=app.title,
        version=app.version,
        description=app.description,
        routes=app.routes,
    )
    body_schema = schema["components"]["schemas"].get("Body_workspace_api_workspace_post", {})
    properties = body_schema.get("properties", {})
    for field_name in ("file",):
        if field_name in properties:
            properties[field_name] = {
                "type": "string",
                "format": "binary",
                "title": "File",
                "description": "Optional file upload",
            }

    app.openapi_schema = schema
    return app.openapi_schema


app.openapi = custom_openapi


# ---------------------------------------------------------------------------
# Dev OAuth auto-refresh helper
# ---------------------------------------------------------------------------
_GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"


def _uploaded_file_or_none(file: UploadFile | str | None) -> UploadFile | None:
    """Treat Swagger's placeholder file string as no uploaded file."""
    if isinstance(file, str):
        return None
    if file and file.filename:
        return file
    return None


def _env_value(*names: str) -> str:
    """Return the first non-empty environment value from a list of aliases."""
    for name in names:
        value = os.getenv(name, "").strip()
        if value:
            return value
    return ""


def _refresh_dev_oauth_token() -> str:
    """Exchange the .env refresh token for a fresh Google access token."""
    access_token = _env_value("GOOGLE_ACCESS_TOKEN", "GOOGLE_OAUTH_ACCESS_TOKEN")
    if access_token:
        return normalize_oauth_token(access_token)

    client_id = _env_value("GOOGLE_CLIENT_ID", "GOOGLE_OAUTH_CLIENT_ID")
    client_secret = _env_value("GOOGLE_CLIENT_SECRET", "GOOGLE_OAUTH_CLIENT_SECRET")
    refresh_token = _env_value("GOOGLE_REFRESH_TOKEN", "GOOGLE_OAUTH_REFRESH_TOKEN")

    if not all([client_id, client_secret, refresh_token]):
        missing = []
        if not client_id:
            missing.append("GOOGLE_CLIENT_ID")
        if not client_secret:
            missing.append("GOOGLE_CLIENT_SECRET")
        if not refresh_token:
            missing.append("GOOGLE_REFRESH_TOKEN")
        raise ValueError(
            "oauth_token='dev' requires either GOOGLE_ACCESS_TOKEN or "
            "GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET, and GOOGLE_REFRESH_TOKEN "
            f"in ai-service/.env. Missing: {', '.join(missing)}"
        )

    resp = http_requests.post(
        _GOOGLE_TOKEN_URL,
        data={
            "client_id": client_id,
            "client_secret": client_secret,
            "refresh_token": refresh_token,
            "grant_type": "refresh_token",
        },
        timeout=10,
    )
    if resp.status_code != 200:
        logger.error("Token refresh failed: %s", resp.text)
        raise ValueError(f"Token refresh failed ({resp.status_code}): {resp.text}")

    access_token = resp.json().get("access_token", "")
    if not access_token:
        raise ValueError("Token refresh returned no access_token.")

    logger.info("Dev token refreshed successfully.")
    return access_token


def _resolve_oauth_token(oauth_token: str) -> str:
    """Return a usable access token.

    If oauth_token is literally ``"dev"``, exchange the refresh token stored
    in environment variables for a fresh access token.  Otherwise return the
    token as-is (assumes the caller passed a real access token).
    """
    token = normalize_oauth_token(oauth_token)
    if token.lower() != "dev":
        return token
    return _refresh_dev_oauth_token()


def _google_api_error_detail(exc: HttpError) -> dict:
    """Return a Swagger-friendly Google API error without leaking credentials."""
    raw_content = exc.content.decode("utf-8", errors="replace") if exc.content else ""
    parsed_content: dict = {}
    if raw_content:
        try:
            parsed_content = json.loads(raw_content)
        except json.JSONDecodeError:
            parsed_content = {"raw": raw_content}

    error = parsed_content.get("error", parsed_content)
    message = error.get("message") or str(exc)
    status_code = int(getattr(exc.resp, "status", 502) or 502)
    detail = {
        "status": "google_api_error",
        "google_status_code": status_code,
        "message": message,
        "errors": error.get("errors", []),
    }
    if status_code == 401:
        detail["hint"] = (
            "The Google access token is invalid or expired. In Swagger Authorize, "
            "enter dev to refresh from ai-service/.env, or paste a fresh OAuth "
            "access token with Calendar scope."
        )
    return detail


# ---------------------------------------------------------------------------
# ADK runner (reused across requests)
# ---------------------------------------------------------------------------
session_service = InMemorySessionService()
runner = Runner(
    agent=root_agent,
    app_name="gieventhub",
    session_service=session_service,
)


# Track active sessions per user for conversation reuse
_user_sessions: dict[str, str] = {}  # user_id -> session_id


async def _run_workspace_agent(user_content: genai_types.Content, user_id: str = "api-caller") -> list[dict]:
    """Run the ADK agent and collect text/tool response events.

    Reuses existing sessions per user_id so chained requests share context
    (e.g. folder_id from step 1 carries into step 2).
    """
    existing_session_id = _user_sessions.get(user_id)
    session = None

    if existing_session_id:
        try:
            session = await session_service.get_session(
                app_name="gieventhub",
                user_id=user_id,
                session_id=existing_session_id,
            )
        except Exception:
            session = None

    if session is None:
        session = await session_service.create_session(
            app_name="gieventhub",
            user_id=user_id,
        )
        _user_sessions[user_id] = session.id

    agent_events: list[dict] = []
    async for event in runner.run_async(
        session_id=session.id,
        user_id=user_id,
        new_message=user_content,
    ):
        part = event.content and event.content.parts and event.content.parts[0]
        if part and part.text:
            agent_events.append(
                {
                    "author": event.author,
                    "text": part.text,
                }
            )
        if part and part.function_response:
            agent_events.append(
                {
                    "author": event.author,
                    "function_response": {
                        "name": part.function_response.name,
                        "response": part.function_response.response,
                    },
                }
            )
    return agent_events


# ---------------------------------------------------------------------------
# POST /api/workspace — the only endpoint
# ---------------------------------------------------------------------------
@app.post("/api/workspace")
async def workspace(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    prompt: str = Form(..., description="Natural-language instruction for the agent"),
    file: UploadFile | str | None = File(default=None, description="Optional file upload"),
):
    """Single entry-point for all Google Workspace CRUD operations.

    The agent decides what to create/read/update/delete based on the prompt.
    An uploaded file can be passed for Drive upload or agent context.

    **Auth:** Pass a Google OAuth access token (or ``dev``) in the
    ``Authorization: Bearer <token>`` header.  Use the Authorize button
    in Swagger UI to set it once for all requests.
    """
    # 1. Resolve OAuth token (auto-refresh when "dev")
    try:
        resolved_token = _resolve_oauth_token(credentials.credentials)
        _service_cache.clear()  # Invalidate cached API clients for new token
        require_oauth_token(resolved_token)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    # 2. Build the user message with optional file context
    parts: list[genai_types.Part] = []

    upload = _uploaded_file_or_none(file)

    if upload:
        from git_eventhub_agent.workspace_tools import _WORKSPACE_FILE_STORE

        content = await upload.read()
        mime = upload.content_type
        if not mime or mime == "application/octet-stream":
            guessed, _ = mimetypes.guess_type(upload.filename or "")
            mime = guessed or "application/octet-stream"

        # Store bytes under a reference key the agent can use
        _WORKSPACE_FILE_STORE.set({
            "file_1": {
                "bytes": content,
                "mime_type": mime,
                "filename": upload.filename,
            }
        })

        file_context = (
            f"Attached file:\n"
            f"- file_1: {upload.filename} ({mime}, {len(content)} bytes)\n\n"
            f"To upload this file to Drive, use upload_drive_file with "
            f"content_base64='file_1'. The actual bytes are resolved automatically.\n\n"
        )
    else:
        file_context = ""

    # Compose the full instruction sent to the agent
    instruction = (
        f"oauth_token: <registered>\n\n"
        f"{file_context}"
        f"User instruction:\n{prompt}"
    )
    parts.insert(0, genai_types.Part.from_text(text=instruction))

    user_content = genai_types.Content(
        role="user",
        parts=parts,
    )

    # 3. Run the agent
    try:
        agent_events = await _run_workspace_agent(user_content)
    except HttpError as exc:
        status_code = int(getattr(exc.resp, "status", 502) or 502)
        if status_code == 401 and normalize_oauth_token(credentials.credentials).lower() != "dev":
            try:
                require_oauth_token(_refresh_dev_oauth_token())
                agent_events = await _run_workspace_agent(user_content)
            except ValueError as retry_exc:
                raise HTTPException(status_code=400, detail=str(retry_exc)) from retry_exc
            except HttpError as retry_exc:
                retry_status_code = int(getattr(retry_exc.resp, "status", 502) or 502)
                raise HTTPException(
                    status_code=retry_status_code if 400 <= retry_status_code < 600 else 502,
                    detail=_google_api_error_detail(retry_exc),
                ) from retry_exc
        else:
            raise HTTPException(
                status_code=status_code if 400 <= status_code < 600 else 502,
                detail=_google_api_error_detail(exc),
            ) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    # 4. Extract the final agent response
    final_text = ""
    for ev in reversed(agent_events):
        if ev.get("text"):
            final_text = ev["text"]
            break

    return {
        "status": "success",
        "response": final_text,
        "events": agent_events,
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
