# gieventhub

> **"GitHub for Events."** A collaborative platform for event organizers — companies, accelerators, universities — that turns every event into a data-ingestion point for a **Global Knowledge Graph** of the startup ecosystem.

gieventhub is built around a single insight: most "event tools" are CRMs with a calendar bolted on. They forget the *relationships* an event produces — which mentor advised which founder, which sponsor funded which cohort, which playbook actually shipped. We model those relationships as a first-class graph and let organizers **fork** each other's event blueprints (Drive folders, Forms, Sheets, Docs, Calendars) so an *adapted* playbook arrives as a fully provisioned Google Workspace, not a generic template.

This is the hackathon repository for the **MyHack 2026** submission.

---

## Table of contents

1. [The 30-second pitch](#the-30-second-pitch)
2. [Live demo path](#live-demo-path)
3. [Repository layout](#repository-layout)
4. [Architecture](#architecture)
5. [The core metaphor](#the-core-metaphor-developer-vs-user-language)
6. [Tech stack](#tech-stack)
7. [Getting started](#getting-started)
8. [Environment variables](#environment-variables)
9. [Frontend routes](#frontend-routes)
10. [Backend API](#backend-api)
11. [AI service](#ai-service)
12. [Data contract (Pydantic schemas)](#data-contract-pydantic-schemas)
13. [Deployment](#deployment)
14. [Project conventions](#project-conventions)
15. [Further reading](#further-reading)

---

## The 30-second pitch

- **The trap to avoid:** "Luma + LLM wrapper." Auto-drafting emails and landing pages is not a moat.
- **The moat:** we track *relationships across events* (`Startup A` → `mentored by` → `Mentor B` → `at Event C`) and let organizers **fork** their event architectures so others can adapt them.
- **The wedge:** the AI doesn't just write copy — it *provisions a real Google Workspace* (Drive folder + Forms + Sheets + Docs + Calendar) tuned to the user's specific event, derived from past playbooks.

The 24-hour MVP centers on the **Smart Fork** loop: discover a Community Playbook → inspect its assets → adapt it with a Gemini prompt → receive a fully provisioned Google Workspace.

---

## Live demo path

What the judges should see, in order:

1. Land on [`/`](frontend/app/page.tsx) — the **Community Playbooks gallery** with category filters.
2. Open a playbook → see its assets and knowledge-graph view.
3. Click **"Adapt Playbook"** → prompt something like *"high school students, climate tech, SF"* → wait → land on a real Google Workspace URL with provisioned Drive/Docs/Forms/Calendar.
4. From home, choose **"Upcoming Event"** → land in [`/event/new`](frontend/app/event/new/page.tsx) → fork a playbook → walk through the 4-step intake → arrive at the **Command Center** with AI-drafted mentors, sponsors, venues, outreach, and timeline → hit **Launch**.
5. (Stretch) Visit [`/chat`](frontend/app/chat/page.tsx) and ask *"Find climate-tech startups Cradle should reconnect with"* → see a grounded ecosystem graph and approval-gated workspace drafts.

The judges should leave convinced this is **infrastructure for the ecosystem**, not yet another event tool with a chatbot bolted on.

---

## Repository layout

```
google-hack/
├── AGENTS.md                  ← master engineering context (read first if you'll touch code)
├── README.md                  ← you are here
├── firebase.json              ← Firebase Auth config (Google sign-in)
├── .firebaserc                ← targets GCP project ninth-library-496500-d8
├── pyrefly.toml               ← Python type checker config
│
├── docs/
│   ├── PITCH_DECK.md
│   ├── architecture.html
│   ├── hackathon_brainstorm.md
│   └── Problem Statement MyHack 2026.docx.pdf
│
├── frontend/                  ← Next.js 16 (App Router) + React 19 + Tailwind 4
│   ├── AGENTS.md / CLAUDE.md
│   ├── app/                   ← routes (see §Frontend routes)
│   ├── components/            ← shadcn-on-base-ui primitives + custom UI
│   ├── lib/                   ← AuthContext, Firebase client, utils
│   ├── public/
│   └── package.json
│
├── backend/                   ← FastAPI app — the API the frontend actually calls
│   ├── main.py                ← /api/scan, /api/adapt, /api/commit, /api/chat, /api/playbooks…
│   ├── ai_client.py           ← HTTP client for the ai-service
│   ├── gemini_client.py       ← direct Gemini calls (chat replies, relationship reasoning)
│   ├── firestore_db.py        ← Playbook persistence
│   ├── deps.py                ← Firebase ID token verification, settings
│   ├── schemas.py             ← Pydantic request/response models
│   ├── seed_playbooks.py      ← seed scripts for Firestore
│   ├── Procfile               ← Cloud Run entrypoint
│   └── requirements.txt
│
└── ai-service/                ← Google ADK orchestrator (Vertex AI + Gemini)
    ├── README.md
    ├── server.py              ← standalone FastAPI wrapper around the ADK agent
    ├── git_eventhub_agent/
    │   ├── agent.py           ← root_agent + 5 sub-agents
    │   ├── schemas.py         ← Pydantic models — the AI contract
    │   └── workspace_tools.py ← approval-gated Workspace CRUD across 15+ Google apps
    ├── tests/
    ├── Procfile
    └── requirements.txt
```

---

## Architecture

```
                       ┌────────────────────────────┐
                       │  Browser (Next.js, :3000)  │
                       │  • App Router pages        │
                       │  • Firebase Auth (Google)  │
                       └─────────────┬──────────────┘
                                     │  HTTPS + Bearer Firebase ID token
                                     ▼
                       ┌────────────────────────────┐
                       │  backend (FastAPI, :8000)  │
                       │  • Auth verification       │
                       │  • Playbook persistence    │
                       │  • Direct Gemini for chat  │
                       │  • Forwards Workspace ops  │
                       └──────┬──────────┬──────────┘
                              │          │
                              │          │ HTTP (OAuth token forwarded)
                              │          ▼
                              │   ┌────────────────────────────┐
                              │   │ ai-service (ADK, :8080)    │
                              │   │ root_agent  +  5 sub-agents│
                              │   │ + ~80 Workspace CRUD tools │
                              │   └──────────────┬─────────────┘
                              │                  │
                              ▼                  ▼
                       ┌────────────┐    ┌────────────────────┐
                       │ Firestore  │    │ Vertex AI / Gemini │
                       │ (playbooks)│    │ Google Workspace   │
                       └────────────┘    │ APIs (Drive, Docs, │
                                         │ Forms, Sheets,     │
                                         │ Calendar, Gmail,   │
                                         │ Slides, Tasks,     │
                                         │ Chat, Meet, …)     │
                                         └────────────────────┘
```

- The frontend **never** calls Vertex or Workspace APIs directly. Everything is mediated by the backend.
- The backend treats the ai-service as a separately deployable HTTP dependency — when it's unreachable or unconfigured, the backend falls back to deterministic stubs so the demo path still works.
- The ai-service is **stateless**. Its tools are the only "memory."
- Workspace mutations require a real **end-user Google OAuth token**, forwarded verbatim by the frontend on each mutating request. The ai-service registers it via `require_oauth_token` and never echoes it back.

---

## The core metaphor (developer vs user language)

We use developer concepts internally but **event planners are not developers.** All user-facing copy must use the consumer translation:

| Developer concept (code) | User-facing copy (UI) |
| :--- | :--- |
| Repository (Repo) | Playbook / Event Blueprint |
| Fork | Adapt Playbook / Clone & Customize |
| Commits / Pull Requests | Drafts / Suggested Updates |
| Open Source | Community Gallery |
| Branch | Variant |
| Issue | Note / Comment |

If you find yourself typing "repo" or "fork" in JSX, stop and translate.

---

## Tech stack

### Frontend
- **Next.js 16.2.6** — App Router, Turbopack dev. *Note:* this is **not the Next.js you know** — breaking changes from older versions. Read `frontend/node_modules/next/dist/docs/` before assuming an API.
- **React 19.2.4** — Server Components by default; client components opt-in via `"use client"`.
- **TypeScript 5**
- **Tailwind 4** (`@tailwindcss/postcss`, `tw-animate-css`)
- **shadcn 4.7** on **`@base-ui/react` 1.4** — primitives in [`frontend/components/ui/`](frontend/components/ui/)
- **lucide-react 1.16** — only icon set allowed
- **@xyflow/react 12.10** — React Flow for knowledge-map graphs
- **Firebase 12.13** — Google Sign-in only
- **OGL 1.0** — animated `PlasmaWave` hero background
- **react-markdown** + **remark-gfm** — chat message rendering

### Backend
- **FastAPI 0.136** + **Pydantic 2.13**
- **firebase-admin 7** — verifies Firebase ID tokens
- **google-cloud-firestore 2.21** — playbook persistence
- **google-genai 2.3** — direct Gemini calls (chat replies, relationship reasoning)
- **httpx 0.28** — async client to the ai-service
- Python 3.14 via Homebrew; venv at `backend/venv/`

### AI service
- **google-adk 1.33** — Google Agent Development Kit
- **google-api-python-client 2.187+** — Workspace APIs
- **FastAPI** — wraps the ADK agent at `:8080` for the backend to call
- Gemini family: `gemini-3-flash-preview`, `gemini-3.1-flash-lite`, `gemini-3.1-pro-preview`, `gemini-2.5-flash`
- **Vertex AI / Gemini Enterprise Agent Platform** for inference
- Python 3.14 via Homebrew; venv at `ai-service/.venv/`

### Infra
- **GCP project:** `ninth-library-496500-d8`
- **Firestore** — playbook JSONs, user profiles, version history
- **Firebase Auth** — Google OAuth (already wired)
- **Google Workspace APIs** — Drive, Docs, Sheets, Forms, Calendar, Gmail, Slides, Tasks, Chat, Meet, Keep, NotebookLM, AppSheet
- **Cloud Run** — `asia-southeast1` (frontend + backend deploy targets)

### Ports
- Frontend: `http://localhost:3000`
- Backend: `http://localhost:8000`
- AI service: `http://localhost:8080`

---

## Getting started

You need three terminals — one for each service.

### Prerequisites

- Python 3.14 (`brew install python@3.14`)
- Node.js 20+ and npm
- `gcloud` CLI authenticated to project `ninth-library-496500-d8`
- A Google OAuth access token for any Workspace mutations (the frontend obtains this via Firebase Sign-in with Google + extra scopes)

### 1. AI service (`ai-service/`)

```sh
cd ai-service
/opt/homebrew/opt/python@3.14/bin/python3.14 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt

cp .env.example .env
# Edit .env to point GOOGLE_CLOUD_PROJECT at your GCP project (default: ninth-library-496500-d8)

gcloud auth application-default login

# Run the HTTP wrapper (what the backend calls):
python server.py
# Or the interactive ADK CLI:
adk run git_eventhub_agent
```

Service is now at `http://localhost:8080`. See [`ai-service/README.md`](ai-service/README.md) for the full Workspace CRUD matrix.

### 2. Backend (`backend/`)

```sh
cd backend
/opt/homebrew/opt/python@3.14/bin/python3.14 -m venv venv
source venv/bin/activate
python -m pip install -r requirements.txt

cp .env.example .env
# Set AI_SERVICE_URL=http://localhost:8080
# Leave AUTH_DEV_BYPASS=0 unless you need to skip Firebase token verification locally

uvicorn main:app --reload --port 8000
```

Service is now at `http://localhost:8000`. Sanity check:

```sh
curl http://localhost:8000/health
# {"status":"ok","ai_stack_configured":true}
```

### 3. Frontend (`frontend/`)

```sh
cd frontend
npm install
npm run dev
```

App is now at `http://localhost:3000`. The frontend always calls `http://localhost:8000` — never Vertex or Workspace directly.

### Seeding playbooks

```sh
cd backend
source venv/bin/activate
python seed_playbooks.py       # seed the canonical playbooks
python seed_bulk_playbooks.py  # seed the bulk dataset
```

---

## Environment variables

### `backend/.env`

```env
GCP_PROJECT=ninth-library-496500-d8
GCP_LOCATION=global

# Where ai-service is reachable. Empty = backend uses stubs.
AI_SERVICE_URL=http://localhost:8080

# 1 = skip Firebase ID token verification (local dev only — never in prod).
AUTH_DEV_BYPASS=0

# Firestore database id. Use "(default)" unless you've created a named DB.
FIRESTORE_DATABASE=(default)

# AI Studio API key. When set, Gemini calls use the Developer API instead of
# Vertex AI (separate quota — useful when Vertex is rate-limited).
GEMINI_API_KEY=
```

### `ai-service/.env`

```env
GOOGLE_GENAI_USE_VERTEXAI=TRUE
GOOGLE_GENAI_USE_ENTERPRISE=TRUE
GOOGLE_CLOUD_PROJECT=ninth-library-496500-d8
GOOGLE_CLOUD_LOCATION=global
```

### Frontend
No `.env` required for local dev — it hardcodes `http://localhost:8000` and reads Firebase config from [`frontend/lib/firebase.ts`](frontend/lib/firebase.ts).

---

## Frontend routes

All routes live under [`frontend/app/`](frontend/app/). The user flow weaves between two distinct paths — **past event** (extract a playbook) and **upcoming event** (plan a new one) — that converge at `/onboarding/review` for the final commit.

| Route | File | Purpose |
| :--- | :--- | :--- |
| `/` | [app/page.tsx](frontend/app/page.tsx) | **Explore** — gallery of Community Playbooks. |
| `/playbooks/[id]` | [app/playbooks/[id]/page.tsx](frontend/app/playbooks/[id]/page.tsx) | **Inspect** — context, assets, features, knowledge graph. "Adapt Playbook" button opens `AdaptPlaybookModal`. |
| `/playbooks` | [app/playbooks/page.tsx](frontend/app/playbooks/page.tsx) | User's own playbooks list (post-login). |
| `/chat` | [app/chat/page.tsx](frontend/app/chat/page.tsx) | **Ecosystem chat** — relationship graph from a natural-language query. |
| `/onboarding/login` | [app/onboarding/login/page.tsx](frontend/app/onboarding/login/page.tsx) | Firebase Google sign-in. |
| `/onboarding/import` | [app/onboarding/import/page.tsx](frontend/app/onboarding/import/page.tsx) | "Past event" entry — connect Google Workspace. |
| `/onboarding/scan` | [app/onboarding/scan/page.tsx](frontend/app/onboarding/scan/page.tsx) | Animated scanning UI; POSTs `/api/scan`. |
| `/onboarding/review` | [app/onboarding/review/page.tsx](frontend/app/onboarding/review/page.tsx) | **Final commit screen.** Edits title/description/tags/visibility, shows the knowledge map. **No top NavBar.** |
| `/event/new` | [app/event/new/page.tsx](frontend/app/event/new/page.tsx) | **Upcoming-event Command Center.** 4-step onboarding (`mode → playbook/context → similar → plan`) ending in a board of AI-drafted picks + right-rail "Event Architect" chat. **No top NavBar.** |

### The two converging flows

```
Past event flow (extract → playbook):
  /  →  EventTypeModal ("Past")  →  /onboarding/import  →  /onboarding/scan
        →  /onboarding/review?timing=past  →  /playbooks/[id]

Upcoming event flow (plan → workspace):
  /  →  EventTypeModal ("Upcoming")  →  /event/new
        → step "mode" (fork vs scratch)
        → step "playbook" (if fork) — fork a past playbook
        → step "context" — 4-field intake (name, date, format, audience, goal)
        → step "similar" — top-3 similar past playbooks with similarity score
        → step "plan" — Command Center: Event Brief, AI-drafted cards,
                        Run-of-Show timeline, Launch CTA
        →  /onboarding/review?timing=upcoming  →  /playbooks/[id]
```

[`EventTypeModal`](frontend/components/EventTypeModal.tsx) is the fork point. The `?timing=` query param is the only thing that distinguishes the two flows on the review screen.

### Chat surfaces

There are **three chat inputs** in the UI:

1. **`/event/new` right rail — "Event Architect"** — step-aware AI guide.
2. **`/onboarding/review` right rail — "Anything I missed?"** — playbook refinement; accepts Drive links and triggers asset extraction.
3. **`/chat`** — ecosystem-level chat that produces a relationship graph from `RelationshipEvidence` records.

---

## Backend API

Lives in [`backend/main.py`](backend/main.py). Runs on `localhost:8000`. CORS allows `localhost:3000` and the Cloud Run frontend domains.

Auth: every authenticated request expects `Authorization: Bearer <Firebase ID token>`. Workspace-mutating endpoints additionally accept a Google OAuth access token in the body — it's forwarded verbatim to the ai-service.

Selected endpoints:

| Endpoint | Body | Behavior |
| :--- | :--- | :--- |
| `GET /health` | — | `{ status, ai_stack_configured }` |
| `POST /api/scan` | `{ userId, eventName?, oauth_token? }` | Detect an event cluster in Drive. If `AI_SERVICE_URL` is set + OAuth token present → forwards to ai-service. Else returns a stub `event_details`. |
| `POST /api/adapt` | `{ prompt, playbookTitle, oauth_token? }` | The Smart Fork. Provisions Drive folder + Docs + Forms + Sheets + Calendar; returns `{ workspaceUrl, workspace_drafts }`. |
| `POST /api/commit` | `{ title, description, is_public, commit_message, ... }` | Persists the playbook to Firestore; returns `{ playbook_id }`. |
| `POST /api/chat` | `{ messages, ... }` | SSE stream of `{ role, text }` from Gemini. |
| `GET  /api/playbooks` | — | List playbooks (mix of seed data + user-created). |
| `GET  /api/playbooks/{id}` | — | Single playbook detail. |

All non-streaming endpoints return `{ status: "success" \| "error", ...payload }`.

---

## AI service

See [`ai-service/README.md`](ai-service/README.md) for the full reference. Quick recap:

A central **`root_agent`** orchestrator (`gemini-3-flash-preview`) with **5 specialized sub-agents** and a suite of tools:

```
root_agent
├── tools
│   ├── classify_and_extract_request   → IntakeResult
│   ├── search_relationships            → list[RelationshipEvidence]
│   ├── rank_candidates                 → list[Recommendation]
│   ├── verify_recommendations          → list[VerifiedRecommendation]
│   ├── draft_workspace_actions         → list[WorkspaceDraft]
│   └── run_reconnection_workflow       → AgentResponse  (one-call demo path)
└── sub_agents
    ├── intake_agent          (gemini-3.1-flash-lite)   — parse intent
    ├── relationship_agent    (gemini-3-flash-preview)  — trace evidence
    ├── recommendation_agent  (gemini-3-flash-preview)  — rank
    ├── verification_agent    (gemini-3.1-pro-preview)  — reject unsupported claims
    └── workspace_agent       (gemini-2.5-flash)        — plan Workspace drafts
```

### HTTP endpoints (consumed by the backend)

Every endpoint accepts `{ oauth_token, prompt, files? }`.

| Endpoint | Purpose |
| :--- | :--- |
| `GET /health` | Liveness + agent name |
| `POST /scan` | Detect an event cluster in Drive |
| `POST /adapt` | Clone + customize a playbook |
| `POST /clone-playbook` | Clone a playbook's Workspace assets |
| `POST /invite-mentors` | Mentor invites + calendar holds |
| `POST /run` | Raw prompt escape hatch |

### Hard constraints (baked into the agent instructions)

- **Agents are stateless.** Tools provide the only memory.
- **Grounded evidence only.** `verification_agent` rejects any claim without supporting evidence (assigns confidence 0.25, status `"unsupported"`).
- **Workspace drafts only, never side effects by default.** Every `WorkspaceDraft.requires_approval` defaults to `True`. Mutations only execute when the caller explicitly passes `execute=True`.
- **Calendar uses `sendUpdates=none`** — execution never emails attendees.
- Final output must include intent + recommendations + workspace_drafts (`AgentResponse`).

### Workspace CRUD coverage

15+ Google apps with create/read/update/delete tools — including Drive, Docs, Forms, Sheets, Gmail (drafts and messages), Calendar, Slides, Tasks, Chat, Meet, Keep, NotebookLM Enterprise, AppSheet. Full matrix in [`ai-service/README.md`](ai-service/README.md).

---

## Data contract (Pydantic schemas)

Defined in [`ai-service/git_eventhub_agent/schemas.py`](ai-service/git_eventhub_agent/schemas.py). These are the AI ↔ frontend wire format — match them in TypeScript when adding new UI surfaces.

```python
IntakeResult           { intent, sector, goal }
RelationshipEvidence   { entity_id, entity_name, relationship_path: list[str], evidence }
Recommendation         { entity_id, name, score, reason, evidence: list[str] }
VerifiedRecommendation = Recommendation + { confidence: float, verification_status: str }
WorkspaceDraft         { type, title, summary, requires_approval: bool = True }
AgentResponse          { intent, recommendations: list[VerifiedRecommendation],
                         workspace_drafts: list[WorkspaceDraft] }
```

---

## Deployment

Both `backend/` and `ai-service/` ship to **Google Cloud Run** in `asia-southeast1`. Each directory has a `Procfile`:

```
# backend/Procfile
web: uvicorn main:app --host 0.0.0.0 --port $PORT

# ai-service/Procfile
web: uvicorn server:app --host 0.0.0.0 --port $PORT
```

The frontend deploys to Cloud Run as well. The CORS allowlist in [`backend/main.py`](backend/main.py) is the source of truth for which frontend origins are permitted:

```
http://localhost:3000
http://127.0.0.1:3000
https://frontend-1009420638811.asia-southeast1.run.app
https://frontend-mz2tiihnsa-as.a.run.app
```

When deploying a new frontend revision under a different URL, add it to the allowlist.

---

## Project conventions

These are binding across all three services. Full version in [`AGENTS.md`](AGENTS.md).

1. **Python: always use a venv.** `backend/venv/` and `ai-service/.venv/` both exist. Activate before installing or running anything.
2. **Frontend UI: no emojis. No generic SVG.** Premium, modern, professional. Lucide icons only.
3. **Translate developer terminology in UI copy.** Never expose "repo" / "fork" / "commit" / "PR" to end users — see [§The core metaphor](#the-core-metaphor-developer-vs-user-language).
4. **AI agents are stateless.** Use tools for memory. Never claim a real Workspace action was executed unless it actually was.
5. **Workspace actions are draft-only by default.** `requires_approval: true` on every `WorkspaceDraft`.
6. **No autonomous browser testing.** Type-check + dev-server `curl` is the default verification path.
7. **Layout containing a chat rail: bind to `h-screen`** (not `min-h-screen`) so each pane scrolls internally — otherwise the chat input falls off-screen when the left grows.
8. **Design palette:** Zinc base. Emerald = AI/grounded/success. Amber = warnings/tiers. Red = destructive only.
9. **Git / PR hygiene:**
   - Read `.github/pull_request_template.md` and `CONTRIBUTING.md` if present.
   - For changes > 10 files **or** > 300 LOC → write a PR plan in `.agents/plans/` first.
   - Each PR: max 10 files, max 350 LOC.
   - CI must pass before merge.

---

## Further reading

- [`AGENTS.md`](AGENTS.md) — the master engineering context. Read before touching code.
- [`frontend/AGENTS.md`](frontend/AGENTS.md) — a one-liner reminding you Next.js 16 is not the Next.js you knew.
- [`ai-service/README.md`](ai-service/README.md) — the agent architecture and the full Workspace CRUD matrix.
- [`docs/hackathon_brainstorm.md`](docs/hackathon_brainstorm.md) — the original product rationale and deeper ideation notes.
- [`docs/PITCH_DECK.md`](docs/PITCH_DECK.md) — the demo narrative.
- [`docs/architecture.html`](docs/architecture.html) — visual architecture diagram.
- [`docs/Problem Statement MyHack 2026.docx.pdf`](docs/Problem%20Statement%20MyHack%202026.docx.pdf) — the hackathon brief we're answering.
