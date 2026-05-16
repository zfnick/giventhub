"""HTTP client for the friend's AI stack.

Universal contract per friend's spec — every endpoint expects:

    POST {AI_SERVICE_URL}/{endpoint}
    {
      "oauth_token": str,        # user's Google Workspace OAuth access token
      "prompt": str,             # natural-language instruction
      "files": [ ... ] | None,   # optional uploads (base64 + name + mime)
    }

Returns arbitrary JSON which we forward straight to the frontend.

When AI_SERVICE_URL is empty, `invoke()` raises `AIStackUnavailable` and the
caller decides whether to fall back to a stub.
"""
from __future__ import annotations

import logging
from typing import Any

import httpx

log = logging.getLogger(__name__)


class AIStackUnavailable(RuntimeError):
    """Raised when the AI stack is not configured or unreachable."""


class AIStackClient:
    def __init__(self, base_url: str, timeout_seconds: float = 60.0) -> None:
        self.base_url = base_url.rstrip("/")
        self._client = httpx.AsyncClient(timeout=timeout_seconds)

    @property
    def configured(self) -> bool:
        return bool(self.base_url)

    async def invoke(
        self,
        endpoint: str,
        oauth_token: str,
        prompt: str,
        files: list[dict[str, Any]] | None = None,
        extra: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        if not self.configured:
            raise AIStackUnavailable("AI_SERVICE_URL not set")

        payload: dict[str, Any] = {
            "oauth_token": oauth_token,
            "prompt": prompt,
        }
        if files:
            payload["files"] = files
        if extra:
            payload.update(extra)

        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        try:
            resp = await self._client.post(url, json=payload)
        except httpx.HTTPError as exc:
            log.warning("AI stack network error at %s: %s", url, exc)
            raise AIStackUnavailable(str(exc)) from exc

        if resp.status_code >= 400:
            log.warning(
                "AI stack returned %s at %s: %s",
                resp.status_code, url, resp.text[:300],
            )
            raise AIStackUnavailable(f"{resp.status_code} from AI stack")

        try:
            return resp.json()
        except ValueError as exc:
            raise AIStackUnavailable("AI stack returned non-JSON") from exc

    async def close(self) -> None:
        await self._client.aclose()
