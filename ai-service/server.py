"""GITEventHub AI Service — HTTP front door for the ADK Workspace agent.

A standalone FastAPI service, deployed and scaled separately from the
gieventhub backend. The backend (FastAPI, :8000) calls this service (:8080)
over HTTP whenever an endpoint needs real Google Workspace mutations; when this
service is unreachable the backend falls back to its own stubs.

Universal request contract — every endpoint accepts:

    POST /{endpoint}
    { "oauth_token": str, "prompt": str, "files"?: [...], ...extra }

`oauth_token` is the end user's Google OAuth access token. It is registered
with the ADK agent for the duration of the request and never echoed back.

Endpoints:
  GET  /health          — liveness + agent name
  POST /scan            — detect an event cluster in Drive  → structured JSON
  POST /adapt           — clone + customize a playbook      → { workspaceUrl }
  POST /clone-playbook  — clone a playbook's Workspace assets
  POST /invite-mentors  — send mentor invites + calendar holds
  POST /run             — escape hatch: forward a raw prompt to the agent
"""
from __future__ import annotations

import asyncio
import base64
import json
import logging
import random
import re
from typing import Any

from collections.abc import AsyncIterator

from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, ConfigDict

from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types as genai_types

from git_eventhub_agent import root_agent
from git_eventhub_agent.workspace_tools import (
    _WORKSPACE_FILE_STORE,
    normalize_oauth_token,
    require_oauth_token,
)

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("ai-service")

APP_NAME = "gieventhub-ai"

# The ADK runner is stateless across requests — we create a fresh session per
# call so concurrent users never share conversation context.
session_service = InMemorySessionService()
runner = Runner(agent=root_agent, app_name=APP_NAME, session_service=session_service)

app = FastAPI(title="GITEventHub AI Service")


# ── Wire models ──────────────────────────────────────────────────────────────

class AIRequest(BaseModel):
    """Universal request envelope. `extra="allow"` keeps caller-supplied fields
    such as `playbookId` / `playbookTitle` (sent by the backend's /api/adapt)."""

    model_config = ConfigDict(extra="allow")
    oauth_token: str
    prompt: str
    files: list[dict[str, Any]] | None = None


class ScanAsset(BaseModel):
    name: str
    type: str
    color: str = "zinc"


class ScanEventDetails(BaseModel):
    title: str
    category: str
    last_active: str
    assets: list[ScanAsset]


class ScanResponse(BaseModel):
    status: str = "success"
    event_detected: bool
    event_details: ScanEventDetails


class AdaptResponse(BaseModel):
    status: str = "success"
    message: str = ""
    workspaceUrl: str = ""
    workspace_drafts: list[dict[str, Any]] = []


# ── Agent runner ─────────────────────────────────────────────────────────────

def _stage_request(
    prompt: str,
    oauth_token: str,
    files: list[dict[str, Any]] | None,
) -> tuple[str, genai_types.Content]:
    """Register the OAuth token, stage attached files, build the agent message.

    Shared by the one-shot `_run_agent` and the streaming `_stream_agent` so
    both code paths use identical token / file handling.
    """
    token = normalize_oauth_token(oauth_token)
    if not token:
        raise HTTPException(status_code=400, detail="oauth_token is required")
    require_oauth_token(token)

    file_context = ""
    if files:
        store: dict[str, dict] = {}
        listed: list[str] = []
        for i, f in enumerate(files, start=1):
            key = f"file_{i}"
            raw = f.get("content_base64") or f.get("content") or ""
            try:
                content = base64.b64decode(raw) if raw else b""
            except (ValueError, TypeError):
                content = b""
            name = f.get("file_name") or f.get("name") or key
            mime = f.get("mime_type") or "application/octet-stream"
            store[key] = {"bytes": content, "mime_type": mime, "filename": name}
            listed.append(f"- {key}: {name} ({mime}, {len(content)} bytes)")
        _WORKSPACE_FILE_STORE.set(store)
        file_context = (
            "Attached files:\n" + "\n".join(listed) + "\n\n"
            "To upload a file to Drive, call upload_drive_file with "
            "content_base64='file_1' — the bytes are resolved automatically.\n\n"
        )

    instruction = (
        "oauth_token: <registered>\n\n"
        f"{file_context}"
        f"User instruction:\n{prompt}"
    )
    user_content = genai_types.Content(
        role="user",
        parts=[genai_types.Part.from_text(text=instruction)],
    )
    return token, user_content


def _summarize_part(part: Any) -> dict[str, Any] | None:
    """Translate one ADK content part into a UI-friendly event, or None to skip.

    The frontend renders a progress chip per tool call (e.g. "Created Drive
    folder: <name>") so we surface enough metadata to label it without dumping
    raw API responses.
    """
    if not part:
        return None

    fc = getattr(part, "function_call", None)
    if fc and getattr(fc, "name", None):
        args: dict[str, Any] = {}
        try:
            raw_args = getattr(fc, "args", None) or {}
            # google.genai args is a Struct/dict-like — coerce to plain dict.
            args = dict(raw_args)
        except (TypeError, ValueError):
            args = {}
        # Only forward small scalar args so the wire stays tight (no base64).
        compact = {
            k: v for k, v in args.items()
            if isinstance(v, (str, int, float, bool)) and len(str(v)) < 200
        }
        return {"type": "tool_call", "name": fc.name, "args": compact}

    fr = getattr(part, "function_response", None)
    if fr and getattr(fr, "name", None):
        resp = getattr(fr, "response", None) or {}
        try:
            resp_dict = dict(resp) if not isinstance(resp, dict) else resp
        except (TypeError, ValueError):
            resp_dict = {}
        # Pull out the human-readable bits a chip can show.
        title = resp_dict.get("title") or resp_dict.get("folder_name") or ""
        url = (
            resp_dict.get("url")
            or resp_dict.get("workspaceUrl")
            or resp_dict.get("folder_url")
            or ""
        )
        executed = bool(resp_dict.get("executed", True))
        return {
            "type": "tool_result",
            "name": fr.name,
            "title": title,
            "url": url,
            "executed": executed,
        }

    text = getattr(part, "text", "") or ""
    text = text.strip()
    if text:
        # Cap so a chatty model can't flood the stream.
        return {"type": "thought", "text": text[:400]}
    return None


async def _stream_agent(
    prompt: str, oauth_token: str, files: list[dict[str, Any]] | None,
) -> AsyncIterator[dict[str, Any]]:
    """Run the ADK agent and yield one structured event per content part."""
    _, user_content = _stage_request(prompt, oauth_token, files)
    session = await session_service.create_session(app_name=APP_NAME, user_id="backend")

    collected: list[dict[str, Any]] = []  # mirrors _run_agent's events list
    last_text = ""

    async for event in runner.run_async(
        session_id=session.id, user_id="backend", new_message=user_content,
    ):
        if not event.content or not event.content.parts:
            continue
        for part in event.content.parts:
            evt = _summarize_part(part)
            if evt is None:
                continue
            yield evt
            if evt["type"] == "thought":
                last_text = evt["text"]
                collected.append({"author": event.author, "text": last_text})
            elif evt["type"] == "tool_result":
                collected.append({
                    "author": event.author,
                    "function_response": {
                        "name": evt["name"],
                        "response": {"title": evt.get("title"), "url": evt.get("url")},
                    },
                })

    workspace_url = _first_folder_url(collected, last_text)
    yield {
        "type": "final",
        "summary": last_text,
        "workspaceUrl": workspace_url,
    }


async def _run_agent(
    prompt: str, oauth_token: str, files: list[dict[str, Any]] | None,
) -> tuple[str, list[dict]]:
    """Register the OAuth token, run the ADK agent once, return (final_text, events).

    Token and file-store state live in ContextVars; each request handler runs
    in its own asyncio Task with an isolated context copy, so concurrent
    requests never see each other's credentials.
    """
    _, user_content = _stage_request(prompt, oauth_token, files)
    session = await session_service.create_session(app_name=APP_NAME, user_id="backend")

    events: list[dict] = []
    async for event in runner.run_async(
        session_id=session.id, user_id="backend", new_message=user_content,
    ):
        part = event.content and event.content.parts and event.content.parts[0]
        if part and part.text:
            events.append({"author": event.author, "text": part.text})
        if part and part.function_response:
            events.append({
                "author": event.author,
                "function_response": {
                    "name": part.function_response.name,
                    "response": part.function_response.response,
                },
            })

    final_text = next((e["text"] for e in reversed(events) if e.get("text")), "")
    return final_text, events


def _extract_json(text: str) -> dict | None:
    """Pull the last JSON object out of an agent reply (fenced or bare)."""
    if not text:
        return None
    candidates = re.findall(r"```(?:json)?\s*(.*?)```", text, re.DOTALL)
    if not candidates:
        start, end = text.find("{"), text.rfind("}")
        if start != -1 and end > start:
            candidates = [text[start:end + 1]]
    for raw in reversed(candidates):
        try:
            parsed = json.loads(raw.strip())
        except json.JSONDecodeError:
            continue
        if isinstance(parsed, dict):
            return parsed
    return None


_FOLDER_URL_RE = re.compile(r"https://drive\.google\.com/drive/folders/[\w-]+")


def _first_folder_url(events: list[dict], final_text: str) -> str:
    """Best-effort extraction of the cloned Drive root folder URL."""
    for e in events:
        fr = e.get("function_response")
        if fr:
            match = _FOLDER_URL_RE.search(json.dumps(fr.get("response", {}), default=str))
            if match:
                return match.group(0)
    match = _FOLDER_URL_RE.search(final_text or "")
    return match.group(0) if match else ""


# ── Quota / 429 handling ─────────────────────────────────────────────────────
#
# A single /adapt fans out across the coordinator + 4-6 sub-agents, each of
# which makes its own gemini-2.5-flash call (often several turns). That bursts
# right through Vertex's per-minute quota, surfacing as
# google.adk.models.google_llm._ResourceExhaustedError. Google's mitigation
# guidance is exponential backoff with retry, so we retry the whole request
# (sessions are fresh per call) and only fail open with HTTP 429 once we've
# given the bucket time to refill.

_QUOTA_RETRY_DELAYS = (2.0, 6.0, 18.0)  # seconds — ~26s worst case before 429


def _is_quota_error(exc: BaseException) -> bool:
    name = type(exc).__name__
    if name in ("_ResourceExhaustedError", "ResourceExhausted"):
        return True
    msg = str(exc)
    return "RESOURCE_EXHAUSTED" in msg or "429" in msg


async def _with_quota_retry(coro_factory):
    """Run `coro_factory()` with exponential backoff on Gemini 429s."""
    last_exc: BaseException | None = None
    for attempt, base_delay in enumerate(_QUOTA_RETRY_DELAYS, start=1):
        try:
            return await coro_factory()
        except HTTPException:
            raise
        except Exception as exc:  # noqa: BLE001 — retry decision below
            if not _is_quota_error(exc):
                raise
            last_exc = exc
            # Full jitter keeps concurrent /adapt calls from re-colliding.
            delay = random.uniform(0, base_delay)
            log.warning(
                "Gemini quota exhausted (attempt %d/%d) — retrying in %.1fs",
                attempt, len(_QUOTA_RETRY_DELAYS) + 1, delay,
            )
            await asyncio.sleep(delay)
    # One last try after the final sleep.
    try:
        return await coro_factory()
    except HTTPException:
        raise
    except Exception as exc:  # noqa: BLE001
        if _is_quota_error(exc):
            raise HTTPException(
                status_code=429,
                detail=(
                    "Gemini quota exhausted after retries. "
                    "Please wait a minute and try again, or request a "
                    "quota increase for gemini-2.5-flash in your "
                    "Vertex AI region."
                ),
            ) from exc
        raise
    finally:
        if last_exc is not None:
            log.debug("recovered or surfaced after quota error: %s", last_exc)


async def _run_or_502(req: AIRequest, prompt: str | None = None) -> tuple[str, list[dict]]:
    """Run the agent, retrying on 429 and converting other failures into 502."""
    effective_prompt = prompt or req.prompt
    try:
        return await _with_quota_retry(
            lambda: _run_agent(effective_prompt, req.oauth_token, req.files)
        )
    except HTTPException:
        raise
    except Exception as exc:  # noqa: BLE001 — surface any agent failure as 502
        log.exception("agent run failed")
        raise HTTPException(status_code=502, detail=f"agent run failed: {exc}") from exc


# ── Endpoints ────────────────────────────────────────────────────────────────

@app.get("/health")
async def health() -> dict:
    return {"status": "ok", "agent": root_agent.name}


_SCAN_FORMAT = (
    "\n\nWhen done, end your reply with a fenced ```json code block in EXACTLY "
    'this shape: {"event_detected": true, "event_details": {"title": "...", '
    '"category": "...", "last_active": "...", "assets": [{"name": "...", '
    '"type": "Doc", "color": "blue"}]}}'
)


@app.post("/scan", response_model=ScanResponse)
async def scan(req: AIRequest) -> ScanResponse:
    """Detect the most recent event-related file cluster in the user's Drive."""
    final_text, _ = await _run_or_502(req, prompt=req.prompt + _SCAN_FORMAT)
    payload = _extract_json(final_text)
    if not payload or "event_details" not in payload:
        # No structured result — let the backend fall back to its scan stub.
        raise HTTPException(status_code=502, detail="agent returned no scan result")
    try:
        return ScanResponse(**payload)
    except Exception as exc:  # noqa: BLE001 — malformed agent JSON
        raise HTTPException(status_code=502, detail=f"bad scan shape: {exc}") from exc


@app.post("/adapt", response_model=AdaptResponse)
async def adapt(req: AIRequest) -> AdaptResponse:
    """The Smart Fork — clone a playbook into the user's Workspace, customized."""
    title = getattr(req, "playbookTitle", None) or "playbook"
    final_text, events = await _run_or_502(req)
    drafts = [e["function_response"] for e in events if "function_response" in e]
    return AdaptResponse(
        status="success",
        message=final_text or f"Adapted {title}",
        workspaceUrl=_first_folder_url(events, final_text),
        workspace_drafts=drafts,
    )


@app.post("/adapt-stream")
async def adapt_stream(req: AIRequest) -> StreamingResponse:
    """Streaming variant of /adapt.

    Returns NDJSON: one JSON object per line, terminated by `\\n`. The frontend
    renders each tool_call / tool_result as a progress chip in real time, so
    the user watches "Created Drive folder → Created Google Form → ..." happen
    instead of staring at a spinner for a minute.
    """
    async def _drain_once() -> list[dict[str, Any]]:
        """Consume the agent stream fully so a mid-stream 429 can be retried.
        Buffering is fine here — events are tiny (one chip per tool call)."""
        return [
            evt async for evt in _stream_agent(req.prompt, req.oauth_token, req.files)
        ]

    async def gen() -> AsyncIterator[bytes]:
        try:
            events = await _with_quota_retry(_drain_once)
            for evt in events:
                yield (json.dumps(evt) + "\n").encode("utf-8")
        except HTTPException as exc:
            yield (json.dumps({
                "type": "error", "status": exc.status_code, "detail": str(exc.detail),
            }) + "\n").encode("utf-8")
        except Exception as exc:  # noqa: BLE001 — surface any agent failure on-stream
            log.exception("adapt-stream failed")
            yield (json.dumps({
                "type": "error", "status": 502, "detail": f"agent run failed: {exc}",
            }) + "\n").encode("utf-8")

    # `x-no-buffer` is a hint for any reverse proxy (nginx etc.) not to buffer.
    return StreamingResponse(
        gen(),
        media_type="application/x-ndjson",
        headers={"X-Accel-Buffering": "no", "Cache-Control": "no-cache"},
    )


@app.post("/clone-playbook")
async def clone_playbook(req: AIRequest) -> dict:
    """Clone a playbook's Workspace assets (Drive folder + Docs/Sheets/Forms)."""
    final_text, events = await _run_or_502(req)
    return {"status": "success", "summary": final_text, "events": events}


@app.post("/invite-mentors")
async def invite_mentors(req: AIRequest) -> dict:
    """Send mentor invitation emails and create Calendar holds."""
    final_text, events = await _run_or_502(req)
    return {"status": "success", "summary": final_text, "events": events}


@app.post("/run")
async def run(req: AIRequest) -> dict:
    """Escape hatch — forward a raw prompt (and optional files) to the agent."""
    final_text, events = await _run_or_502(req)
    return {"status": "success", "summary": final_text, "events": events}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("server:app", host="0.0.0.0", port=8080, reload=True)
