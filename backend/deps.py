"""Settings + auth dependencies for the FastAPI app."""
from __future__ import annotations

import logging
import os
from functools import lru_cache

import firebase_admin
from dotenv import load_dotenv
from fastapi import Depends, Header, HTTPException, status
from firebase_admin import auth as fb_auth
from pydantic import BaseModel

load_dotenv()
log = logging.getLogger(__name__)


class Settings(BaseModel):
    gcp_project: str
    gcp_location: str
    ai_service_url: str
    auth_dev_bypass: bool
    firestore_database: str
    gemini_api_key: str
    neo4j_uri: str
    neo4j_username: str
    neo4j_password: str


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings(
        gcp_project=os.getenv("GCP_PROJECT", "ninth-library-496500-d8"),
        gcp_location=os.getenv("GCP_LOCATION", "global"),
        ai_service_url=os.getenv("AI_SERVICE_URL", "").rstrip("/"),
        auth_dev_bypass=os.getenv("AUTH_DEV_BYPASS", "0") == "1",
        firestore_database=os.getenv("FIRESTORE_DATABASE", "(default)"),
        # When set, Gemini calls use the Developer API (AI Studio key) instead
        # of Vertex AI + ADC. Handy as a fallback when Vertex is rate-limited.
        gemini_api_key=os.getenv("GEMINI_API_KEY", ""),
        # Empty NEO4J_URI disables the Neo4j client — backend still runs, but
        # the ecosystem chat falls back to the older Gemini-only graph path.
        neo4j_uri=os.getenv("NEO4J_URI", ""),
        neo4j_username=os.getenv("NEO4J_USERNAME", "neo4j"),
        neo4j_password=os.getenv("NEO4J_PASSWORD", ""),
    )


@lru_cache(maxsize=1)
def _init_firebase() -> firebase_admin.App:
    settings = get_settings()
    return firebase_admin.initialize_app(options={"projectId": settings.gcp_project})


class AuthedUser(BaseModel):
    uid: str
    email: str | None = None
    name: str | None = None


def _bypass_user() -> AuthedUser:
    return AuthedUser(uid="dev-bypass-uid", email="dev@local", name="Dev User")


async def get_current_user(
    authorization: str | None = Header(default=None),
    settings: Settings = Depends(get_settings),
) -> AuthedUser:
    """Verify Firebase ID token from `Authorization: Bearer <token>`."""
    if settings.auth_dev_bypass:
        return _bypass_user()

    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing bearer token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    token = authorization.split(" ", 1)[1].strip()
    _init_firebase()
    try:
        decoded = fb_auth.verify_id_token(token)
    except Exception as exc:
        log.warning("ID token verification failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid ID token",
        ) from exc
    return AuthedUser(
        uid=decoded["uid"],
        email=decoded.get("email"),
        name=decoded.get("name") or decoded.get("email"),
    )


async def get_current_user_optional(
    authorization: str | None = Header(default=None),
    settings: Settings = Depends(get_settings),
) -> AuthedUser | None:
    """Same as `get_current_user` but returns None for unauthenticated requests."""
    if settings.auth_dev_bypass:
        return _bypass_user()
    if not authorization or not authorization.lower().startswith("bearer "):
        return None
    try:
        return await get_current_user(authorization=authorization, settings=settings)
    except HTTPException:
        return None
