"""Neo4j wrapper — relationship index over the playbook catalogue.

Firestore is the source of truth for playbook documents. Neo4j mirrors the
*relationships* across playbooks so the ecosystem chat can answer questions
like "which mentors have appeared in multiple climate-tech events?" with a
Cypher query in tens of milliseconds, instead of asking Gemini to invent a
graph from scratch on every request.

Schema:

    (:Playbook {id, title, category, host, attendees, duration, forked_from})
    (:Person   {name, organization})
    (:Theme    {name})
    (:Venue    {name})
    (:Tool     {name})

    (Person)   -[:PARTICIPATED_IN {role}]-> (Playbook)
    (Playbook) -[:HAS_THEME]            -> (Theme)
    (Playbook) -[:AT_VENUE]             -> (Venue)
    (Playbook) -[:USES_TOOL]            -> (Tool)
    (Playbook) -[:FORKED_FROM]          -> (Playbook)

Entity names are normalized (trimmed + collapsed whitespace + title case) so
"Alice Chen" and "alice  chen" merge to the same node. This is good enough
for demo-scale data; production would need proper entity resolution.

The driver is the synchronous Neo4j 5.x driver. Endpoints wrap blocking
calls in `asyncio.to_thread`, matching the FirestoreDB pattern.
"""
from __future__ import annotations

import logging
import os
import re
from contextlib import contextmanager
from typing import Any, Iterable

from neo4j import GraphDatabase, Driver

import schemas

log = logging.getLogger(__name__)


# ── Normalization helpers ────────────────────────────────────────────────────

_WS = re.compile(r"\s+")
_TOOL_SPLIT = re.compile(r"[,;/|]+|\s+(?:and|\+|&)\s+", re.IGNORECASE)


def _norm(value: str) -> str:
    """Collapse whitespace, strip, title-case — for entity name uniqueness."""
    if not value:
        return ""
    return _WS.sub(" ", value.strip()).title()


def _split_tools(tech_stack: str) -> list[str]:
    """Tech stack is a free-text string. Split on common delimiters."""
    if not tech_stack:
        return []
    parts = _TOOL_SPLIT.split(tech_stack)
    return [t for t in (_norm(p) for p in parts) if t]


_STOPWORDS = {
    "a", "an", "and", "are", "as", "at", "be", "by", "for", "from",
    "has", "have", "i", "in", "is", "it", "its", "me", "my", "of",
    "on", "or", "that", "the", "this", "to", "was", "we", "what", "when",
    "where", "which", "who", "why", "with", "you", "your", "show", "find",
    "list", "all", "any", "give", "get", "tell", "about", "do", "does",
    "did", "can", "could", "would", "should", "want", "need", "events",
    "event", "playbook", "playbooks",
}


def extract_keywords(query: str) -> list[str]:
    """Tokenize the user's natural-language query into matchable keywords.

    Demo-grade: lowercase, split on non-alphanumeric, drop stopwords + tokens
    shorter than 3 chars. Two-word phrases are preserved by also returning
    adjacent bigrams (so "climate tech" matches a Theme named "Climate Tech").
    """
    tokens = [t for t in re.split(r"[^A-Za-z0-9]+", query.lower()) if len(t) >= 3]
    unigrams = [t for t in tokens if t not in _STOPWORDS]
    bigrams: list[str] = []
    for i in range(len(tokens) - 1):
        if tokens[i] in _STOPWORDS or tokens[i + 1] in _STOPWORDS:
            continue
        bigrams.append(f"{tokens[i]} {tokens[i + 1]}")
    # Bigrams first — more specific matches outrank single-word matches.
    return bigrams + unigrams


# ── Driver wrapper ───────────────────────────────────────────────────────────

class Neo4jClient:
    """Thin wrapper around the Neo4j sync driver.

    When `uri` is empty the client is `disabled` — all write methods become
    no-ops and `ecosystem_subgraph` returns empty results. This lets the
    backend run without Neo4j configured (mirrors the AI service fallback).
    """

    def __init__(self, uri: str, username: str, password: str) -> None:
        self.uri = uri
        self.disabled = not uri
        self._driver: Driver | None = None
        if self.disabled:
            log.info("Neo4j disabled — NEO4J_URI not set, ecosystem chat will fall back to Gemini-only graph")
            return
        try:
            self._driver = GraphDatabase.driver(uri, auth=(username, password))
            self._driver.verify_connectivity()
            self._ensure_constraints()
            log.info("Neo4j ready at %s", uri)
        except Exception:
            log.exception("Neo4j init failed — disabling client")
            self._driver = None
            self.disabled = True

    def close(self) -> None:
        if self._driver is not None:
            self._driver.close()
            self._driver = None

    @contextmanager
    def _session(self):
        assert self._driver is not None  # caller must check `disabled`
        with self._driver.session() as sess:
            yield sess

    # ── Schema ───────────────────────────────────────────────────────────

    def _ensure_constraints(self) -> None:
        statements = [
            "CREATE CONSTRAINT playbook_id IF NOT EXISTS FOR (p:Playbook) REQUIRE p.id IS UNIQUE",
            "CREATE CONSTRAINT person_name IF NOT EXISTS FOR (n:Person) REQUIRE n.name IS UNIQUE",
            "CREATE CONSTRAINT theme_name  IF NOT EXISTS FOR (n:Theme)  REQUIRE n.name IS UNIQUE",
            "CREATE CONSTRAINT venue_name  IF NOT EXISTS FOR (n:Venue)  REQUIRE n.name IS UNIQUE",
            "CREATE CONSTRAINT tool_name   IF NOT EXISTS FOR (n:Tool)   REQUIRE n.name IS UNIQUE",
        ]
        with self._session() as sess:
            for stmt in statements:
                sess.run(stmt)

    # ── Writes ───────────────────────────────────────────────────────────

    def upsert_playbook(self, playbook: schemas.Playbook) -> None:
        """Mirror a playbook + its relationships into Neo4j.

        Idempotent: re-running on the same playbook is a no-op. Deletes and
        re-creates *outgoing* relationships from the playbook so edits are
        reflected (e.g. a removed tag drops its HAS_THEME edge).
        """
        if self.disabled:
            return

        themes = sorted({_norm(t) for t in playbook.tags if t})
        if playbook.category:
            themes.append(_norm(playbook.category))
        themes = [t for t in dict.fromkeys(themes) if t]  # dedupe, preserve order

        venue = _norm(playbook.context.venue) if playbook.context else ""
        tools = _split_tools(playbook.context.techStack if playbook.context else "")
        people = [
            {
                "name": _norm(p.name),
                "organization": _norm(p.organization),
                "role": p.role or "Participant",
            }
            for p in playbook.participants
            if p.name and _norm(p.name)
        ]

        params = {
            "id": playbook.id,
            "title": playbook.title,
            "category": playbook.category or "",
            "host": playbook.author or "",
            "attendees": playbook.attendees or "",
            "duration": playbook.duration or "",
            "forked_from": playbook.forked_from,
            "themes": themes,
            "venue": venue,
            "tools": tools,
            "people": people,
        }

        cypher = """
        MERGE (p:Playbook {id: $id})
        SET p.title = $title,
            p.category = $category,
            p.host = $host,
            p.attendees = $attendees,
            p.duration = $duration

        // Reset this playbook's outgoing connector edges so edits propagate.
        WITH p
        OPTIONAL MATCH (p)-[r:HAS_THEME|AT_VENUE|USES_TOOL|FORKED_FROM]->()
        DELETE r
        WITH p
        OPTIONAL MATCH (:Person)-[r:PARTICIPATED_IN]->(p)
        DELETE r

        // Themes
        WITH p
        UNWIND $themes AS theme
        MERGE (t:Theme {name: theme})
        MERGE (p)-[:HAS_THEME]->(t)

        // Venue (single)
        WITH DISTINCT p
        FOREACH (_ IN CASE WHEN $venue <> '' THEN [1] ELSE [] END |
            MERGE (v:Venue {name: $venue})
            MERGE (p)-[:AT_VENUE]->(v)
        )

        // Tools
        WITH p
        UNWIND $tools AS tool
        MERGE (tl:Tool {name: tool})
        MERGE (p)-[:USES_TOOL]->(tl)

        // People (role on the edge — same person can participate in many events with different roles)
        WITH DISTINCT p
        UNWIND $people AS person
        MERGE (pr:Person {name: person.name})
        SET pr.organization = coalesce(person.organization, pr.organization)
        MERGE (pr)-[r:PARTICIPATED_IN]->(p)
        SET r.role = person.role

        // Forked-from lineage
        WITH DISTINCT p
        FOREACH (_ IN CASE WHEN $forked_from IS NOT NULL THEN [1] ELSE [] END |
            MERGE (parent:Playbook {id: $forked_from})
            MERGE (p)-[:FORKED_FROM]->(parent)
        )
        """
        with self._session() as sess:
            sess.run(cypher, **params)

    # ── Reads ────────────────────────────────────────────────────────────

    def ecosystem_subgraph(
        self,
        query: str,
        *,
        max_connectors: int = 6,
        max_playbooks: int = 12,
    ) -> tuple[list[schemas.GraphNode], list[schemas.GraphEdge]]:
        """Return a subgraph relevant to the user's query.

        Strategy:
          1. Extract keywords from the query.
          2. Find connector nodes (Theme/Person/Venue/Tool) whose names match
             any keyword (case-insensitive substring).
          3. Pull every Playbook attached to those connectors.
          4. Pull every other connector those playbooks share, so the result
             shows the *web* of relationships, not isolated pairs.

        When no keywords match, return a small "popular" subgraph: the
        most-connected playbooks plus their top shared themes. This gives the
        UI something to render for vague queries like "show me the ecosystem".
        """
        if self.disabled:
            return [], []

        keywords = extract_keywords(query)

        if keywords:
            nodes, edges = self._keyword_subgraph(keywords, max_connectors, max_playbooks)
            if nodes:
                return nodes, edges

        # Empty match → fall back to "popular" view.
        return self._popular_subgraph(max_playbooks)

    def _keyword_subgraph(
        self,
        keywords: list[str],
        max_connectors: int,
        max_playbooks: int,
    ) -> tuple[list[schemas.GraphNode], list[schemas.GraphEdge]]:
        cypher = """
        WITH $keywords AS keywords
        UNWIND keywords AS kw
        MATCH (c)
        WHERE (c:Theme OR c:Person OR c:Venue OR c:Tool)
          AND toLower(c.name) CONTAINS toLower(kw)
        WITH DISTINCT c
        LIMIT $max_connectors
        MATCH (c)-[r]-(p:Playbook)
        WITH collect(DISTINCT c) AS connectors,
             collect(DISTINCT p) AS playbooks
        WITH connectors, playbooks[..$max_playbooks] AS playbooks
        UNWIND playbooks AS p
        OPTIONAL MATCH (p)-[r2]-(c2)
        WHERE c2 IN connectors OR (c2:Theme OR c2:Person OR c2:Venue OR c2:Tool)
        RETURN connectors, playbooks,
               collect(DISTINCT {playbook_id: p.id, connector: c2, rel: type(r2), role: r2.role}) AS triples
        """
        with self._session() as sess:
            record = sess.run(
                cypher,
                keywords=keywords,
                max_connectors=max_connectors,
                max_playbooks=max_playbooks,
            ).single()

        if record is None:
            return [], []
        return _record_to_subgraph(record, max_playbooks)

    def _popular_subgraph(
        self,
        max_playbooks: int,
    ) -> tuple[list[schemas.GraphNode], list[schemas.GraphEdge]]:
        cypher = """
        MATCH (p:Playbook)-[r]-(c)
        WHERE c:Theme OR c:Person OR c:Venue OR c:Tool
        WITH p, count(DISTINCT c) AS degree
        ORDER BY degree DESC
        LIMIT $max_playbooks
        WITH collect(p) AS playbooks
        UNWIND playbooks AS p
        OPTIONAL MATCH (p)-[r2]-(c2)
        WHERE c2:Theme OR c2:Person OR c2:Venue OR c2:Tool
        WITH playbooks,
             collect(DISTINCT c2) AS connectors,
             collect(DISTINCT {playbook_id: p.id, connector: c2, rel: type(r2), role: r2.role}) AS triples
        RETURN connectors, playbooks, triples
        """
        with self._session() as sess:
            record = sess.run(cypher, max_playbooks=max_playbooks).single()
        if record is None:
            return [], []
        return _record_to_subgraph(record, max_playbooks)

    # ── CLI: one-shot backfill from Firestore ────────────────────────────

    def backfill_from(self, playbooks: Iterable[schemas.Playbook]) -> int:
        count = 0
        for pb in playbooks:
            try:
                self.upsert_playbook(pb)
                count += 1
            except Exception:
                log.exception("backfill: failed for %s", pb.id)
        return count


# ── Subgraph → GraphNode/GraphEdge ───────────────────────────────────────────

# Map Neo4j label → frontend node type. Frontend supports event/people/tool/shared.
_LABEL_TO_TYPE: dict[str, str] = {
    "Playbook": "event",
    "Person": "people",
    "Tool": "tool",
    "Theme": "shared",
    "Venue": "shared",
}


def _node_label(n: Any) -> tuple[str, str]:
    """Return (id, display label) for a Neo4j node."""
    labels = list(n.labels)
    if "Playbook" in labels:
        return (f"e:{n['id']}", n.get("title") or n.get("id"))
    primary = labels[0] if labels else "Shared"
    code = primary.lower()[0]  # p/t/v/o(person/theme/venue/tool→o)
    name = n.get("name") or "Unknown"
    return (f"{code}:{name}", name)


def _node_type(n: Any) -> str:
    for label in n.labels:
        if label in _LABEL_TO_TYPE:
            return _LABEL_TO_TYPE[label]
    return "shared"


def _layout(
    playbook_nodes: list[schemas.GraphNode],
    connector_nodes: list[schemas.GraphNode],
) -> None:
    """Deterministic 2D layout, mutates nodes in place.

    Connectors on a horizontal band (y=-150). Playbooks on a wider lower band
    (y=200). Spread x evenly across 0..900 — the same range Gemini was using,
    so the React Flow viewport stays consistent.
    """
    if connector_nodes:
        step = 900 / max(len(connector_nodes), 1)
        for i, n in enumerate(connector_nodes):
            n.x = 50 + step * (i + 0.5)
            n.y = -150
    if playbook_nodes:
        step = 900 / max(len(playbook_nodes), 1)
        for i, n in enumerate(playbook_nodes):
            n.x = 50 + step * (i + 0.5)
            n.y = 200


def _record_to_subgraph(
    record: Any,
    max_playbooks: int,
) -> tuple[list[schemas.GraphNode], list[schemas.GraphEdge]]:
    """Convert a Cypher record (connectors, playbooks, triples) into our wire format."""
    raw_connectors = record["connectors"] or []
    raw_playbooks = (record["playbooks"] or [])[:max_playbooks]
    triples = record["triples"] or []

    nodes: dict[str, schemas.GraphNode] = {}
    edges: dict[str, schemas.GraphEdge] = {}

    playbook_ids = {p["id"] for p in raw_playbooks}

    playbook_node_list: list[schemas.GraphNode] = []
    connector_node_list: list[schemas.GraphNode] = []

    for p in raw_playbooks:
        node_id, label = _node_label(p)
        if node_id in nodes:
            continue
        node = schemas.GraphNode(id=node_id, label=label, type="event")
        nodes[node_id] = node
        playbook_node_list.append(node)

    for c in raw_connectors:
        if c is None:
            continue
        node_id, label = _node_label(c)
        if node_id in nodes:
            continue
        node = schemas.GraphNode(id=node_id, label=label, type=_node_type(c))
        nodes[node_id] = node
        connector_node_list.append(node)

    for t in triples:
        connector = t.get("connector")
        if connector is None:
            continue
        playbook_id = t["playbook_id"]
        if playbook_id not in playbook_ids:
            continue

        c_id, c_label = _node_label(connector)
        if c_id not in nodes:
            node = schemas.GraphNode(id=c_id, label=c_label, type=_node_type(connector))
            nodes[c_id] = node
            connector_node_list.append(node)

        p_id = f"e:{playbook_id}"
        edge_label = _rel_label(t["rel"], t.get("role"))
        edge_id = f"{c_id}->{p_id}"
        if edge_id in edges:
            continue
        edges[edge_id] = schemas.GraphEdge(
            id=edge_id, source=c_id, target=p_id, label=edge_label,
        )

    _layout(playbook_node_list, connector_node_list)
    return list(nodes.values()), list(edges.values())


_REL_LABELS = {
    "HAS_THEME": "themed",
    "AT_VENUE": "venue",
    "USES_TOOL": "uses",
    "FORKED_FROM": "forked from",
}


def _rel_label(rel: str, role: str | None) -> str:
    if rel == "PARTICIPATED_IN":
        return (role or "participated").lower()
    return _REL_LABELS.get(rel, rel.lower().replace("_", " "))


# ── CLI: backfill ────────────────────────────────────────────────────────────

def _cli_backfill() -> None:
    """One-shot: read every public playbook from Firestore, upsert to Neo4j.

    Run after seeding to populate the graph from existing data:

        cd backend && source venv/bin/activate
        python neo4j_client.py backfill
    """
    from dotenv import load_dotenv
    load_dotenv()

    from firestore_db import FirestoreDB

    project = os.getenv("GCP_PROJECT", "ninth-library-496500-d8")
    database = os.getenv("FIRESTORE_DATABASE", "(default)")
    uri = os.getenv("NEO4J_URI", "")
    user = os.getenv("NEO4J_USERNAME", "neo4j")
    password = os.getenv("NEO4J_PASSWORD", "")

    if not uri:
        raise SystemExit("NEO4J_URI is not set — populate backend/.env first")

    db = FirestoreDB(project_id=project, database=database)
    client = Neo4jClient(uri=uri, username=user, password=password)
    if client.disabled:
        raise SystemExit("Neo4j client failed to initialize — check logs")

    playbooks = db.list_public_playbooks(limit=1000)
    n = client.backfill_from(playbooks)
    client.close()
    print(f"backfill: upserted {n} playbooks")


if __name__ == "__main__":
    import sys
    logging.basicConfig(level=logging.INFO)
    if len(sys.argv) >= 2 and sys.argv[1] == "backfill":
        _cli_backfill()
    else:
        print("usage: python neo4j_client.py backfill")
        raise SystemExit(2)
