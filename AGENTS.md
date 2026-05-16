# gieventhub — Master Project Context

> **Read this whole file before touching code, designing UI, or wiring AI calls.**
> This is the single source of truth for product vision, terminology, repo layout, user flows, AI surfaces, data shapes, ports, env vars, and global rules. Sub-directories may have their own narrower AGENTS.md (e.g. `frontend/AGENTS.md`) — they extend this file, not replace it.

---

## 1. Product Vision & The "Moat"

We're building **gieventhub** — "GitHub for Events." A collaborative platform for event organizers (companies, accelerators, universities) that turns each event into a data-ingestion point for a **Global Knowledge Graph** of the startup/community ecosystem.

- **The trap to avoid:** "Luma + LLM wrapper." If we only auto-draft emails and landing pages, we lose.
- **The moat:** we track *relationships across events* (`Startup A` → `mentored by` → `Mentor B` → `at Event C`) and let organizers **fork/open-source** their event architectures so others can adapt them.
- **The wedge:** the AI doesn't just *write copy* — it provisions a real Google Workspace (Drive folder + Forms + Sheets + Docs + Calendar) tuned to the user's specific event, derived from past playbooks.

The 24-hour MVP is the **Smart Fork** loop:
1. Discover a Community Playbook → 2. Inspect its assets → 3. Adapt with a Gemini prompt → 4. Get handed a fully provisioned Google Workspace.

---

## 2. The Core Metaphor & UX Translation

We use developer concepts internally but **event planners are not developers**. Every piece of user-facing copy must use the consumer translation:

| Developer concept (code/architecture) | User-facing copy (UI) |
| :--- | :--- |
| Repository (Repo) | Playbook / Event Blueprint |
| Fork | Adapt Playbook / Clone & Customize |
| Commits / Pull Requests | Drafts / Suggested Updates |
| Open Source | Community Gallery |
| Branch | Variant |
| Issue | Note / Comment |

If you find yourself typing "repo" or "fork" in JSX, stop. Translate.

---

## 3. Repository Layout

```
google-hack/
├── AGENTS.md                  ← you are here (master context)
├── firebase.json              ← Firebase Auth config (Google sign-in)
├── .firebaserc
├── .agents/plans/             ← PR restructuring plans (>10 files / >300 LOC)
├── docs/
│   ├── hackathon_brainstorm.md     ← original ideation, deeper rationale
│   └── Problem Statement MyHack 2026.docx.pdf
│
├── frontend/                  ← Next.js 16 (App Router) + React 19 + Tailwind 4
│   ├── AGENTS.md              ← "this is NOT the Next.js you know" — read it
│   ├── CLAUDE.md              ← @AGENTS.md reference
│   ├── app/                   ← routes (see §4)
│   ├── components/            ← UI building blocks (see §5)
│   ├── lib/                   ← AuthContext, firebase client, utils
│   └── public/
│
├── backend/                   ← FastAPI mock API (the dumb backend)
│   ├── main.py                ← /api/scan, /api/adapt, /api/commit (all mocked)
│   └── venv/                  ← Python venv (gitignored)
│
└── ai-service/                ← Google ADK orchestrator (the real AI stack)
    ├── README.md
    ├── requirements.txt       ← google-adk==1.33.0
    ├── .env.example
    └── git_eventhub_agent/
        ├── agent.py           ← root_agent + 5 sub-agents
        ├── tools.py           ← 6 tool functions (intake, search, rank, verify, draft, run_workflow)
        ├── schemas.py         ← Pydantic models — the AI contract
        └── sample_data.py     ← mock STARTUPS + RELATIONSHIPS
```

The frontend talks to **backend** at `localhost:8000` (mocked endpoints).
The AI dev's job is to make `ai-service` real, then route `backend` calls into it.

---

## 4. Frontend Routes (Next.js App Router)

All routes live under `frontend/app/`. The user flow weaves between two distinct paths — **past event** (extract a playbook) and **upcoming event** (plan a new one) — that converge at `/onboarding/review` for the final commit.

| Route | File | Purpose |
| :--- | :--- | :--- |
| `/` | `app/page.tsx` | **Explore** — gallery of Community Playbooks with category filters. Entry point. |
| `/playbooks/[id]` | `app/playbooks/[id]/page.tsx` | **Inspect** — drill into one playbook: context, assets, features, knowledge graph. "Adapt Playbook" button opens `AdaptPlaybookModal`. |
| `/playbooks` | `app/playbooks/page.tsx` | User's own playbooks list (post-login). |
| `/chat` | `app/chat/page.tsx` | **Ecosystem chat** — chat surface that visualizes a relationship graph (React Flow) from the user's query. Currently all simulated. |
| `/onboarding/login` | `app/onboarding/login/page.tsx` | Firebase Google sign-in. |
| `/onboarding/import` | `app/onboarding/import/page.tsx` | "Past event" entry — connect Google Workspace. |
| `/onboarding/scan` | `app/onboarding/scan/page.tsx` | Animated scanning UI; POSTs `/api/scan` to extract an event from Drive. |
| `/onboarding/review` | `app/onboarding/review/page.tsx` | **Final commit screen** for both flows. Edits title/description/tags/visibility, shows the knowledge map. POSTs `/api/commit` → routes to the new playbook. Back-button is dynamic (history-aware, falls back to `/event/new` for upcoming or `/onboarding/scan` for past). **No top NavBar.** |
| `/event/new` | `app/event/new/page.tsx` | **Upcoming-event Command Center.** 4-step onboarding (`mode → playbook/context → similar → plan`) ending in a "board" of AI-drafted picks (Mentors, Sponsors, Venue, Workspace stack, Outreach, Timeline) + right-rail "Event Architect" chat. **No top NavBar.** |

### The two converging flows

```
Past event flow (extract → playbook):
  /  →  EventTypeModal ("Past")  →  /onboarding/import  →  /onboarding/scan
        →  /onboarding/review?timing=past  →  /playbooks/[id]

Upcoming event flow (plan → workspace):
  /  →  EventTypeModal ("Upcoming")  →  /event/new
        → step "mode" (fork vs scratch)
        → step "playbook" (if fork) — fork a past playbook
        → step "context" — 4-field intake (name, date, format chips, audience, goal)
        → step "similar" — top-3 similar past playbooks with similarity score
        → step "plan" — Command Center: hero w/ "Discard plan" + readiness bar,
                        Event Brief, AI-drafted cards stacked single-column,
                        Run-of-Show timeline, Launch CTA
        →  /onboarding/review?timing=upcoming  →  /playbooks/[id]
```

The `EventTypeModal` (`components/EventTypeModal.tsx`) is the fork point. The `?timing=` query param is the only thing that distinguishes the two flows on the review screen.

---

## 5. Frontend Components & UI Surfaces

### Top-level components (`frontend/components/`)
- `NavBar.tsx` — sticky logo + search + auth dropdown. **Not rendered inside `/event/new` or `/onboarding/review`** (those are full-screen workspaces).
- `EventTypeModal.tsx` — Past vs Upcoming chooser. Routes accordingly.
- `AdaptPlaybookModal.tsx` — the "Smart Fork" prompt modal. POSTs `/api/adapt`.
- `PlasmaWave.tsx` — animated hero background (OGL).
- `graph/PlaybookFlow.tsx` + `PlaybookFlowClient.tsx` — React Flow knowledge-map visualization.
- `ui/` — shadcn primitives (Button, Card, Dialog, Input, Label, Textarea, Avatar, Badge, Tabs, Sheet, Separator, Breadcrumb, Table). All built on `@base-ui/react`.

### AI-facing surfaces (where chat input meets the backend)
There are **three chat surfaces** in the UI today:

1. **`/event/new` right rail — "Event Architect"** — step-aware AI guide. Currently echoes canned replies (`setTimeout` + keyword match). Replace with streaming Gemini calls keyed off `step` state.
2. **`/onboarding/review` right rail — "Anything I missed?"** — playbook refinement. Currently echoes canned replies. Should accept Drive links (regex `drive.google.com`) and trigger asset extraction.
3. **`/chat`** — ecosystem-level chat that generates a relationship graph. Currently fully simulated graph generation (`generateGraphForQuery`). Replace with `ai-service`'s `run_reconnection_workflow` output → render nodes/edges from `RelationshipEvidence`.

### Design rules (from `frontend/AGENTS.md`)
- **NO emojis.** Anywhere. Lucide icons only.
- **NO generic/cheap SVG.** Premium, modern, professional.
- Zinc-based palette. Emerald = AI/grounded/success. Amber = warnings/tiers. Red = destructive only.
- Tailwind 4 + `cn()` helper (`lib/utils.ts`). Prefer `Button`, `Card`, etc. from `components/ui/`.
- Layouts that contain a chat rail must be **`h-screen` bounded with internal scrolling**, not `min-h-screen` (otherwise the chat input falls off-screen as the left grows).
- Card grids in `/event/new` plan step are intentionally single-column for visual rhythm.

---

## 6. Backend (FastAPI — currently all mock)

Lives in `backend/main.py`. Runs on **`localhost:8000`**. CORS allows only `localhost:3000`.

| Endpoint | Body | Response (mocked) | Where it's called |
| :--- | :--- | :--- | :--- |
| `POST /api/scan` | `{ userId: string }` | `{ status, event_detected, event_details: { title, category, last_active, assets[] } }` after a 4.5s sleep | `app/onboarding/scan/page.tsx` |
| `POST /api/adapt` | `{ prompt: string, playbookTitle: string }` | `{ status, message, workspaceUrl }` after a 2.5s sleep | `components/AdaptPlaybookModal.tsx` |
| `POST /api/commit` | `{ title, description, is_public, commit_message }` | `{ status, playbook_id, message }` after a 2.0s sleep | `app/onboarding/review/page.tsx` |

**All three sleep + return canned shapes.** The AI dev's task: wire each one to the `ai-service` orchestrator and return real, schema-conformant data.

Run locally:
```sh
cd backend
source venv/bin/activate
uvicorn main:app --reload --port 8000
```

---

## 7. AI Service (Google ADK orchestrator)

Lives in `ai-service/git_eventhub_agent/`. Uses `google-adk==1.33.0` (Vertex AI / Gemini Enterprise Agent Platform).

### Architecture
A central `root_agent` (orchestrator) with **5 specialized sub-agents** and **6 tools**:

```
root_agent  (gemini-3-flash-preview)
├── tools:
│   ├── classify_and_extract_request   → IntakeResult
│   ├── search_relationships            → list[RelationshipEvidence]
│   ├── rank_candidates                 → list[Recommendation]
│   ├── verify_recommendations          → list[VerifiedRecommendation]
│   ├── draft_workspace_actions         → list[WorkspaceDraft]
│   └── run_reconnection_workflow       → AgentResponse  (one-call demo path)
└── sub_agents:
    ├── intake_agent          (gemini-3.1-flash-lite) — parse intent
    ├── relationship_agent    (gemini-3-flash-preview) — trace evidence
    ├── recommendation_agent  (gemini-3-flash-preview) — rank
    ├── verification_agent    (gemini-3.1-pro-preview) — reject unsupported claims
    └── workspace_agent       (gemini-2.5-flash) — plan-only Workspace drafts
```

### Hard constraints (already baked into the agent instructions — keep them!)
- **Agents are stateless.** Tools provide the only memory.
- **Grounded evidence only.** `verification_agent` rejects any claim without supporting evidence (assigns confidence 0.25, status `"unsupported"`).
- **Workspace drafts only, never side effects.** `workspace_agent` plans Gmail/Calendar/Drive/Docs/Sheets/Forms drafts — it must **never** send/schedule/post/share. `WorkspaceDraft.requires_approval` defaults to `True`.
- Output must include intent + recommendations + workspace_drafts (`AgentResponse`).

### Pydantic schemas (the contract — `schemas.py`)
These are the AI ↔ frontend wire format. Match these in TypeScript when wiring up:

```python
IntakeResult           {intent, sector, goal}
RelationshipEvidence   {entity_id, entity_name, relationship_path: list[str], evidence}
Recommendation         {entity_id, name, score, reason, evidence: list[str]}
VerifiedRecommendation = Recommendation + {confidence: float, verification_status: str}
WorkspaceDraft         {type, title, summary, requires_approval: bool = True}
AgentResponse          {intent, recommendations: list[VerifiedRecommendation], workspace_drafts: list[WorkspaceDraft]}
```

### Local setup
```sh
cd ai-service
source .venv/bin/activate
python -m pip install -r requirements.txt
cp .env.example .env   # then fill in GOOGLE_CLOUD_PROJECT
gcloud auth application-default login
adk run git_eventhub_agent
```

Env vars (`.env.example`):
```
GOOGLE_GENAI_USE_VERTEXAI=TRUE
GOOGLE_GENAI_USE_ENTERPRISE=TRUE
GOOGLE_CLOUD_PROJECT=ninth-library-496500-d8
GOOGLE_CLOUD_LOCATION=global
```

---

## 8. Where the AI Dev Plugs In

### Priority order
1. **`/api/adapt`** (the "Smart Fork" — the demo headline). Take `{ prompt, playbookTitle }`, call the orchestrator with intent `"adapt_playbook"`, return real `workspaceUrl` + a `workspace_drafts[]` payload the frontend can render.
2. **`/event/new` Event Architect chat** — step-aware. Pipe each step's state (`mode`, `forkedPlaybookId`, context fields, locked selections) as conversational context. The "draft cards" (mentors / sponsors / venues / outreach / timeline) should be populated from agent output, not the current static mocks in `app/event/new/page.tsx`.
3. **`/api/scan`** — wire to a real Drive-reading agent that returns `event_details.assets[]`.
4. **`/chat`** — replace `generateGraphForQuery` simulation with `run_reconnection_workflow` output. `RelationshipEvidence.relationship_path` maps cleanly to React Flow nodes+edges.
5. **`/api/commit`** — persist the playbook (Firestore) and return a real `playbook_id`.

### Mock data the AI must eventually generate
In `app/event/new/page.tsx`, search for these arrays — they're frontend hardcodes that the Event Architect should produce dynamically:
- `PAST_PLAYBOOKS` — 4 fork-able templates
- `MENTORS`, `SPONSORS`, `VENUES`, `OUTREACH`, `WORKSPACE_TOOLS`, `TIMELINE`
- The "similarity score" is currently `60 + format match bonus + random(0..6)` — replace with real semantic similarity from past-event embeddings.

### Frontend ↔ AI handshake conventions
- Frontend always calls **`localhost:8000`** (backend). Backend fans out to `ai-service`. The frontend should **never** call Vertex directly.
- All endpoints return `{ status: "success" | "error", ...payload }`.
- Streaming chat responses should be SSE from `/api/chat` (not yet implemented) — when you add it, mirror the message format `{ role: "ai" | "user", text: string }` used in the existing UIs.

---

## 9. Tech Stack (full)

### Frontend
- **Next.js 16.2.6** (App Router, Turbopack dev) — **note: breaking changes from older Next; read `node_modules/next/dist/docs/` before assuming an API.**
- **React 19.2.4** (Server Components default; client components opt-in with `"use client"`)
- **TypeScript 5**
- **Tailwind 4** (`@tailwindcss/postcss`, `tw-animate-css`)
- **shadcn 4.7** built on **`@base-ui/react` 1.4** — primitives in `components/ui/`
- **lucide-react 1.16** — icon library (no other icon sets)
- **@xyflow/react 12.10** — React Flow for knowledge-map / ecosystem graphs
- **Firebase 12.13** — auth only (Google sign-in)
- **OGL 1.0** — animated `PlasmaWave` hero background

### Backend (mock)
- **FastAPI** + **Pydantic v2**
- Python venv at `backend/venv/` (Python 3.14 via Homebrew)

### AI service
- **google-adk 1.33** (Google Agent Development Kit)
- Gemini family models: `gemini-3-flash-preview`, `gemini-3.1-flash-lite`, `gemini-3.1-pro-preview`, `gemini-2.5-flash`
- **Vertex AI / Gemini Enterprise Agent Platform** for inference
- Python venv at `ai-service/.venv/` (Python 3.14 via Homebrew)

### Infra (target)
- **Firestore** — Playbook JSONs, user profiles, version history (not yet wired)
- **Firebase Auth** — Google OAuth ✅ already wired (`lib/firebase.ts`, `lib/AuthContext.tsx`)
- **Google Workspace APIs** — Drive, Docs, Sheets, Forms, Calendar (target for `workspace_agent`)
- **GCP project:** `ninth-library-496500-d8`

### Ports
- Frontend: `http://localhost:3000`
- Backend: `http://localhost:8000`
- AI service: invoked via `adk run` (no fixed HTTP port — usually wrapped by the backend)

---

## 10. Global Rules (binding for all agents/devs)

1. **Python: always use a venv.** `backend/venv/` and `ai-service/.venv/` both exist. Activate before installing or running anything.
2. **Frontend UI: no emojis. No generic/cheap SVG.** Premium, modern, professional aesthetic. Lucide icons only.
3. **No autonomous browser testing.** Don't open a browser to "verify" without being explicitly asked. Type-check + dev-server `curl` is the default.
4. **Translate developer terminology in UI copy.** See §2 — never expose "repo" / "fork" / "commit" / "PR" to users.
5. **AI agents are stateless.** Use tools for memory. Never claim a real Workspace action was executed unless it actually was.
6. **Workspace actions are draft-only by default.** `requires_approval: true` on every `WorkspaceDraft`.
7. **Layout containing a chat rail: bind to `h-screen`** (not `min-h-screen`) so each pane scrolls internally.
8. **Git / PR management:**
   - Read `.github/pull_request_template.md` if present.
   - Read `CONTRIBUTING.md` if present.
   - **For changes >10 files OR >300 LOC** → write a PR plan in `.agents/plans/` first (branch name, commit message, PR title/description, file list).
   - Each PR: max 10 files, max 350 LOC.
   - Branch strategy: feature branches → intermediate branch → `main` (cleaner merges).
   - **CI must pass.**

---

## 11. Quick Reference — Where Things Live

| If you need to … | Look at |
| :--- | :--- |
| Add a new AI endpoint | `backend/main.py` (route) → `ai-service/git_eventhub_agent/tools.py` (logic) |
| Change Pydantic AI contract | `ai-service/git_eventhub_agent/schemas.py` (also update TS types in frontend) |
| Modify the orchestrator's behavior | `ai-service/git_eventhub_agent/agent.py` (instructions on root_agent + sub-agents) |
| Add a playbook | `frontend/app/page.tsx` (`playbooks` array) + `frontend/app/playbooks/[id]/page.tsx` (`playbooksData`) — these will move to Firestore |
| Edit the planning Command Center | `frontend/app/event/new/page.tsx` (single file, ~1100 LOC, step machine + all draft cards) |
| Edit the final commit screen | `frontend/app/onboarding/review/page.tsx` |
| Touch auth | `frontend/lib/AuthContext.tsx`, `frontend/lib/firebase.ts`, `firebase.json` |
| Change global nav | `frontend/components/NavBar.tsx` (note: `/event/new` and `/onboarding/review` deliberately don't render it) |
| Read product rationale | `docs/hackathon_brainstorm.md`, `docs/Problem Statement MyHack 2026.docx.pdf` |
| Plan a large PR | drop a file in `.agents/plans/` |

---

## 12. Demo Path (what the judges should see)

1. Land on `/` → see Community Playbooks gallery.
2. Open a playbook → see assets + knowledge graph.
3. Click "Adapt Playbook" → prompt "high school students, climate tech, SF" → wait → get a real Google Workspace URL with provisioned Drive/Docs/Forms.
4. Click "Upcoming Event" from home → land in `/event/new` → fork a playbook → 4-step flow → arrive at Command Center with AI-drafted mentors/sponsors/venue/outreach → hit Launch.
5. (Stretch) Visit `/chat` and ask "Find climate-tech startups Cradle should reconnect with" → see grounded ecosystem graph + workspace drafts.

The judges should walk away convinced this is **infrastructure for the ecosystem** — not yet another event tool with a chatbot bolted on.
