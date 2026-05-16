"""Firestore wrapper — playbook persistence.

Auth: uses Application Default Credentials (the gcloud ADC at
~/.config/gcloud/application_default_credentials.json). No service-account JSON
needs to ship with the code.
"""
from __future__ import annotations

import logging
import re
from datetime import datetime, timezone
from typing import Any

from google.cloud import firestore

import schemas

log = logging.getLogger(__name__)


def _slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return slug or "playbook"


class FirestoreDB:
    """Thin async-friendly wrapper over the sync Firestore client.

    The sync client is fine for low-QPS demo traffic; we wrap blocking calls
    in `asyncio.to_thread` only if latency becomes an issue.
    """

    def __init__(self, project_id: str, database: str = "(default)") -> None:
        self.client = firestore.Client(project=project_id, database=database)
        self.playbooks = self.client.collection("playbooks")

    # ── reads ────────────────────────────────────────────────────────────

    def list_public_playbooks(self, limit: int = 200) -> list[schemas.Playbook]:
        query = (
            self.playbooks
            .where(filter=firestore.FieldFilter("visibility", "==", "public"))
            .limit(limit)
        )
        return [self._doc_to_playbook(d) for d in query.stream()]

    def list_user_playbooks(self, uid: str, limit: int = 200) -> list[schemas.Playbook]:
        query = (
            self.playbooks
            .where(filter=firestore.FieldFilter("author_uid", "==", uid))
            .limit(limit)
        )
        return [self._doc_to_playbook(d) for d in query.stream()]

    def get_playbook(self, playbook_id: str) -> schemas.Playbook | None:
        snap = self.playbooks.document(playbook_id).get()
        if not snap.exists:
            return None
        return self._doc_to_playbook(snap)

    # ── writes ───────────────────────────────────────────────────────────

    def create_playbook(
        self,
        *,
        author_uid: str,
        author_name: str,
        title: str,
        description: str,
        is_public: bool,
        tags: list[str],
        forked_from: str | None,
        timing: str,
        extra: dict[str, Any] | None = None,
    ) -> schemas.Playbook:
        playbook_id = self._unique_slug(title)
        now = datetime.now(timezone.utc)
        defaults: dict[str, Any] = {
            "id": playbook_id,
            "title": title,
            "author": author_name,
            "author_uid": author_uid,
            "description": description,
            "attendees": "",
            "duration": "",
            "category": "",
            "stats": "Just published",
            "visibility": "public" if is_public else "private",
            "tags": tags,
            "context": {
                "challenge": "",
                "targetAudience": "",
                "venue": "",
                "techStack": "",
            },
            "assets": [],
            "participants": [],
            "features": [],
            "forked_from": forked_from,
            "timing": timing,
            "created_at": now,
            "updated_at": now,
        }
        if extra:
            defaults.update(extra)
        self.playbooks.document(playbook_id).set(defaults)
        return self._dict_to_playbook(defaults)

    def upsert_playbook(self, payload: dict[str, Any]) -> None:
        """Used by the seed script."""
        playbook_id = payload["id"]
        payload.setdefault("created_at", datetime.now(timezone.utc))
        payload["updated_at"] = datetime.now(timezone.utc)
        self.playbooks.document(playbook_id).set(payload, merge=True)

    # ── helpers ──────────────────────────────────────────────────────────

    def _unique_slug(self, title: str) -> str:
        base = _slugify(title)
        candidate = base
        suffix = 2
        while self.playbooks.document(candidate).get().exists:
            candidate = f"{base}-{suffix}"
            suffix += 1
        return candidate

    @staticmethod
    def _doc_to_playbook(doc: firestore.DocumentSnapshot) -> schemas.Playbook:
        data = doc.to_dict() or {}
        data["id"] = doc.id
        return FirestoreDB._dict_to_playbook(data)

    @staticmethod
    def _dict_to_playbook(data: dict[str, Any]) -> schemas.Playbook:
        ctx_raw = data.get("context") or {}
        context = schemas.PlaybookContext(**{
            k: ctx_raw.get(k, "")
            for k in ("challenge", "targetAudience", "venue", "techStack")
        })
        assets = [schemas.PlaybookAsset(**a) for a in data.get("assets", [])]
        participants = [
            schemas.PlaybookParticipant(**p) for p in data.get("participants", [])
        ]
        return schemas.Playbook(
            id=data.get("id", ""),
            title=data.get("title", ""),
            author=data.get("author", ""),
            author_uid=data.get("author_uid"),
            description=data.get("description", ""),
            attendees=data.get("attendees", ""),
            duration=data.get("duration", ""),
            category=data.get("category", ""),
            stats=data.get("stats", ""),
            visibility=data.get("visibility", "public"),
            tags=data.get("tags", []),
            context=context,
            assets=assets,
            participants=participants,
            features=data.get("features", []),
            forked_from=data.get("forked_from"),
            created_at=data.get("created_at"),
            updated_at=data.get("updated_at"),
        )
