# gieventhub — Pitch Deck

> **Build With AI 2026 KL · MyHack** — Problem: *Automating Ecosystem Linkages Instead of Manual Coordination* (Cradle)
>
> Tagline: **Ecosystem linkages — programmed, not coordinated.**
>
> Use this file as the source copy for the submission slides (PDF). Each slide
> below = one PDF page. "On slide" is what the audience sees; "Speaker notes"
> is what you say. Keep slide text terse — the notes carry the detail.

---

## Slide 1 — Title

**On slide**
- **gieventhub**
- Ecosystem linkages — programmed, not coordinated.
- An AI platform that turns mentor, company, and partner relationships into reusable, programmable entities.
- Build With AI 2026 KL · MyHack · [Team name]

**Speaker notes**
> "We're gieventhub. Innovation ecosystems run on relationships — but those relationships are managed by hand. We make them programmable."

---

## Slide 2 — The Problem

**On slide**
- Innovation ecosystems still run on **manual coordination**.
- Admins verify participants, match mentors to companies, assign companies to programmes — **by hand, one-off, every cohort.**
- Critical linkages (mentor→company, company→programme, partner→initiative) are **one-off assignments, not reusable system entities.**
- It doesn't scale across cohorts, programmes, or countries.

**Speaker notes**
> "Today, when an ecosystem operator like Cradle runs a programme, every linkage is handcrafted in spreadsheets and emails. Nothing is reused. The next programme starts from zero. As participation grows, coordination becomes the bottleneck."

---

## Slide 3 — Why It Matters

**On slide**
- **Affected:** programme owners, ecosystem admins, mentors, companies, partners, service providers.
- Manual coordination → operational bottlenecks, inconsistent quality, no institutional memory.
- Platforms **can't learn** from past engagements or apply insight to future programmes.
- The cost compounds with every new country and initiative.

**Speaker notes**
> "This isn't a cosmetic problem. It caps how fast an ecosystem can grow, and it means every programme is as hard as the first one."

---

## Slide 4 — The Insight

**On slide**
- A relationship should be a **first-class, programmable entity** — not a row in a spreadsheet.
- Define a linkage structure **once** → fork it, adapt it, automate it **anywhere**.
- We borrow the most reusable model in software: **version control.**
- "GitHub for ecosystem programmes."

**Speaker notes**
> "The fix is a shift in primitive. In software, code became reusable when we made repositories first-class — fork, branch, reuse. We do the same for ecosystem relationships."

---

## Slide 5 — The Solution: the Playbook

**On slide**
- **gieventhub** packages every programme's relationships into a **Playbook** — the programmable entity.
- A Playbook carries: mentors, sponsors, companies, programme structure, and the live Workspace assets behind it.
- Four moves: **Discover** a Playbook → **Adapt** it to a new context → **Smart-Match** people from past engagements → get a **fully provisioned Google Workspace.**
- Every Playbook feeds one shared **ecosystem linkage graph** — and one shared **engagement history** the matcher learns from.

**Speaker notes**
> "A Playbook is the relationship made programmable. You don't rebuild a programme — you fork a Playbook and our AI adapts it to your country, sector, and audience. And every Playbook you commit makes the next programme's matching smarter, because past engagements feed the scorer."

---

## Slide 6 — How It Works: Smart Fork + Smart Match

**On slide**
1. **Discover** — browse a community library of Playbooks.
2. **Inspect** — see the linkage map: mentors, sponsors, assets, programme structure.
3. **Adapt** — describe the new context in plain language.
4. **Smart Match** — Gemini scores past participants on **Fit** and **Track record**, grounded in every past engagement on the platform — the **outcome-scoring learning loop**.
5. **Provision** — a Google ADK agent builds a live Workspace: Drive, Docs, Forms, Sheets, Calendar.
- Coordination that took days → done in seconds.
- Matching that was guesswork → grounded in real participation history.

**Speaker notes**
> "Two AI moves stacked. First, Smart Fork: take an existing Playbook, describe the new context, and the agent provisions the real Google Workspace. Second, Smart Match: every past Playbook is a past engagement record, so when you need mentors or sponsors, Gemini mines that history and scores candidates — fit, and track record — with every score cited back to the specific events that prove it. That's the learning loop Cradle asked for."

---

## Slide 7 — Live Demo

**On slide** (screenshots)
- Explore gallery + Playbook inspect (linkage graph).
- Smart Fork → adapt prompt → real Workspace URL provisioned.
- Command Center — AI-matched mentors / sponsors / venues.
- **Smart Match** — ranked candidate cards with Fit + Track-record scores, evidence chips citing past playbooks, *"scored against N past engagements."*
- Ecosystem Connections graph — relationships across programmes.

**Speaker notes**
> Walk the 3-minute video path live or via screenshots. End on Smart Match: "every programme run on gieventhub adds to the engagement history — so the very next match is grounded in more data than the last."

---

## Slide 8 — Architecture & Google Technology

**On slide** (insert `architecture.html` screenshot)
- **Frontend:** Next.js 16, React 19, Tailwind 4 — on Cloud Run.
- **Auth:** Firebase Authentication (Google Sign-in).
- **Backend:** FastAPI on Cloud Run — orchestration + REST API.
- **Data:** Firestore — Playbooks + the ecosystem linkage graph.
- **AI reasoning:** Gemini on Vertex AI — matching, chat, graph generation.
- **AI execution:** Google Agent Development Kit — an 8-domain agent hierarchy.
- **Action surface:** full Google Workspace APIs — Drive, Docs, Sheets, Forms, Slides, Gmail, Calendar, Tasks.

**Speaker notes**
> "Why Google? Ecosystem operators already live in Google Workspace. Instead of adding another tool, we automate the tools they already use. Gemini reasons; the ADK agents act; Workspace is the canvas."

---

## Slide 9 — AI Components & Responsible AI

**On slide**
- **Reasoning:** Gemini on Vertex AI — powers Smart Match scoring, ecosystem graph, and chat replies.
- **Execution:** Google ADK `workspace_coordinator` routes to 8 specialist Workspace agents (Gemini 2.5 Flash).
- **Grounded scores, not opinions:** Smart Match `fit_score` and `engagement_score` are derived only from observed participation + each event's reported outcomes — every score cites the playbooks behind it. **Never invent a person or an outcome.**
- **Grounded chat:** ecosystem-graph and chat answers are grounded in real Firestore data.
- **Human-in-the-loop:** Workspace mutations are **draft-by-default** (`requires_approval = true`); a human approves before anything sends or shares.
- **Honest:** the agent never reports an action it did not actually execute.
- **Data minimisation:** the user's OAuth token is request-scoped, never persisted or echoed.

**Speaker notes**
> "Smart Match has the most safety-sensitive job here — recommending real people. So every score is grounded in observed history with the evidence shown alongside; the model is explicitly forbidden to invent people or outcomes. On the Workspace side, every mutation is a draft a human signs off on. Safety isn't bolted on — it's how the system is shaped."

---

## Slide 10 — Business Model & Scalability

**On slide**
- **Customers:** ecosystem operators — accelerators, government agencies (e.g. Cradle), universities, VC platforms.
- **Model:** SaaS, tiered by active programmes + seats. Community Playbook marketplace as a second surface.
- **Technical scalability:** stateless agents, Firestore, Cloud Run — horizontal by default; AI service scales independently of the API.
- **Operational scalability:** every new programme adds reusable Playbooks → the linkage graph compounds → matching keeps improving.
- **Cross-geography:** a Playbook is country-agnostic; adapt, don't rebuild.

**Speaker notes**
> "The business scales the same way the product does — the marginal programme gets cheaper to run, because it inherits the structure of every programme before it."

---

## Slide 11 — Impact & Close

**On slide**
- **Measurable improvement:** programme setup that took hours-to-days of manual coordination → minutes; relationship structures become reusable institutional memory; mentor/sponsor matching moves from guesswork to evidence-scored recommendations.
- **The loop is closed:** every Playbook committed adds to the engagement history — so the *next* match is grounded in more data than the last. The platform gets smarter with every programme.
- **UN SDGs:** **SDG 9** (Industry, Innovation & Infrastructure) and **SDG 8** (Decent Work & Economic Growth) — scalable, inclusive innovation infrastructure.
- **Roadmap:** explicit outcome capture (mentor ratings, funding events, programme KPIs) layered onto the existing scorer → cross-border Playbook exchange → marketplace of community-contributed Playbooks.
- **gieventhub — ecosystem linkages, programmed not coordinated.**

**Speaker notes**
> "Cradle asked: how might we treat ecosystem relationships as first-class, programmable entities that can be reused *and improved* across programmes and countries. The Playbook is the entity. Smart Match is the improvement loop — grounded in every past engagement, getting better with every new one. That's gieventhub. Thank you."

---

## Appendix — Questionnaire answers (paste-ready)

**Elevator pitch**
> Innovation ecosystems still coordinate mentors, companies, and partners by hand — ad hoc and unrepeatable. gieventhub turns every ecosystem relationship into a programmable, forkable entity — a Playbook — so linkages can be defined once and then reused, adapted, and automated across any programme or country. An AI agent provisions the real Google Workspace behind each programme, and a Smart Match engine scores past participants on Fit and Track record, grounded in every prior engagement on the platform — so the matching gets sharper with every Playbook committed.

**Google technologies used & why**
> Gemini on Vertex AI (relationship reasoning, mentor/sponsor matching, knowledge-graph generation); Google Agent Development Kit (multi-agent orchestrator that executes Workspace actions); the full Workspace API suite — Drive, Docs, Sheets, Forms, Slides, Gmail, Calendar, Tasks; Firebase Authentication and Cloud Firestore; Cloud Run for deployment. We chose Google because ecosystem operators already run their programmes inside Google Workspace — automating *within* their existing tools removes the coordination tax instead of adding another silo.

**AI components / models & ethical considerations**
> Gemini-family models via Vertex AI handle reasoning surfaces: the Smart Match scorer (`/api/match/recommend`), the ecosystem relationship graph, and conversational replies. An ADK `workspace_coordinator` orchestrates 8 domain-specialist agents (Gemini 2.5 Flash) for Workspace execution. Responsible-AI measures: Smart Match recommends only people who appear in the engagement history and derives every score from observed participation + each event's reported outcomes — the model is explicitly forbidden to invent people or outcomes, and each candidate shows the playbook evidence behind its score; Workspace mutations are draft-by-default and require explicit human approval (`requires_approval = true`); the agent never claims an action it did not execute; ecosystem-graph and chat answers are grounded in real Firestore data; the user's OAuth token is request-scoped, never persisted, never echoed.

**Tech stack, deployment & AI performance**
> Next.js 16 / React 19 / Tailwind 4 frontend; FastAPI backend; a separately deployed FastAPI AI service wrapping the ADK agent; Firestore for persistence; Firebase Auth. Deployed on Google Cloud Run — frontend, backend, and AI service scale independently. Agents are stateless, so the service scales horizontally; the AI service is isolated from the API so a slow agent run never blocks reads. Gemini 2.5 Flash keeps agent routing fast; reasoning calls use higher-capability Gemini where quality matters.

**Targeted issue & measurable improvement**
> Targeted issue: manual ecosystem coordination — linkages handled as one-off assignments, with no mechanism to learn from past programmes. Our solution makes relationships reusable, programmable Playbooks and closes the learning loop with Smart Match. Measurable improvements: (1) a multi-asset programme workspace that took an admin hours-to-days of manual setup is provisioned in seconds; (2) mentor/sponsor/partner matching moves from gut feel to evidence-scored recommendations, with every score citing the past engagements that back it; (3) the marginal programme gets cheaper *and* sharper, because every new Playbook contributes signal the scorer reads on the next match.

**Core features, stakeholders, beneficiaries**
> Core features: Playbook library (discover), Playbook inspect with linkage graph, Smart Fork (adapt + provision a real Google Workspace), AI Command Center (mentor/sponsor/venue drafting), **Smart Match** (outcome-scoring learning loop — scores past participants on Fit and Track record against every engagement on the platform, with cited evidence), and the Ecosystem Connections chat (relationship graph across programmes). Primary stakeholders: ecosystem operators and programme administrators. Beneficiaries: mentors, companies, partners, and service providers who get timely, relevant, well-managed connections — and whose track records become reusable institutional memory rather than locked inside one programme.

**Business & revenue model, scalability**
> SaaS for ecosystem operators (accelerators, government agencies, universities, VC platforms), tiered by active programmes and seats; a community Playbook marketplace as a second revenue surface. Technical scalability: stateless agents, Firestore, and Cloud Run scale horizontally; the AI service scales independently of the API. Operational scalability: each new programme contributes reusable Playbooks to a shared linkage graph, so matching quality compounds and the marginal programme gets cheaper to run.
