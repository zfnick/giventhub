# Project Overview: "GitHub for Events" (Ecosystem OS)

**Context for AI Agents**: This document contains the master context, product vision, technical architecture, and UI/UX guidelines for the hackathon project. Read this thoroughly before making any architectural decisions, generating UI, or writing backend logic.

## 1. Product Vision & The "Moat"
The goal is to build an **Ecosystem OS** that connects companies, startups, and mentors. Traditional platforms (like Luma or Eventbrite) are B2C tools optimized for single-event ticketing. Our product uses events as data-ingestion points to build a **Global Knowledge Graph** of the ecosystem.

* **The Trap to Avoid:** Do not build a "Luma + LLM Wrapper". If the product only automates sending emails and creating landing pages, it fails.
* **The Moat:** We track *relationships* across multiple events (e.g., `Startup A` was mentored by `Mentor B` at `Event C`). We allow event planners to "Open Source" their event architectures.

## 2. The Core Metaphor & UX Translation
The project uses the "GitHub" architecture (open-source collaboration, version control, forking), but **Event Planners are not developers**. Agents generating UI copy MUST use the translated consumer-friendly terminology below.

| Developer Concept (Architecture) | User-Facing Concept (UI/UX Copy) |
| :--- | :--- |
| Repository (Repo) | Playbook / Event Blueprint |
| Fork | Adapt Playbook / Clone & Customize |
| Commits / Pull Requests | Drafts / Suggested Updates |
| Open Source | Community Gallery |

## 3. The 24-Hour MVP: The "Smart Fork"
The hackathon MVP focuses entirely on the "Forking" capability to prove the concept while heavily utilizing the Google Ecosystem.

**The User Flow:**
1. **Discovery:** The planner views a Canva-like gallery of Community Playbooks (e.g., "Google AI Hackathon Playbook").
2. **Inspection:** They view the assets included in the Playbook (Registration Form, Judging Rubric, Schedule).
3. **Action (The Fork):** They click **"Adapt this Playbook"**. A Gemini-powered chat modal asks for their specific context (e.g., "Make this for high school students focusing on Climate Tech").
4. **Execution (The Wow Moment):** The backend AI modifies the Playbook's base JSON. Using **Google Workspace APIs**, the app automatically creates a Google Drive folder, generates a customized Google Doc (rubric/schedule), and generates a Google Form. The user is handed a link to the complete workspace.

## 4. Technical Architecture & Stack
The tech stack is specifically chosen for speed and strict adherence to the Google Ecosystem requirement.

### Frontend
* **Framework:** Next.js (App Router), React, TypeScript.
* **Styling & UI:** Tailwind CSS, `shadcn/ui`.
* **Graph/Visualization:** React Flow (`@xyflow/react`) for visualizing the knowledge tree and ecosystem graphs.
* **Location:** `/frontend` directory.

### Backend
* **Framework:** FastAPI (Python).
* **Environment:** **ALWAYS** use a `venv` when working with the Python project.
* **AI Orchestration:** Gemini 1.5 Pro (Google Vertex AI / Google AI Studio).
* **Location:** `/backend` directory (To be created).

### Infrastructure & Integrations
* **Database:** Firebase / Firestore (NoSQL, for storing Playbook JSONs and user profiles).
* **Integrations:** Google Drive API, Google Docs API, Google Forms API.
* **Infra:** Google Cloud Platform (GCP).

## 5. Strict User Rules & Directives for AI Agents
Agents MUST adhere to the following global rules:
1. **Python Environments:** ALWAYS USE VENV WHENEVER YOU NEED TO DO ANYTHING WITH THE PYTHON PROJECT.
2. **UI/UX Design:** WHEN YOU DESIGN ANYTHING FRONTEND RELATED, DO NOT USE EMOJIS AND GENERIC SVG DESIGN. Ensure a premium, modern aesthetic (e.g., sleek, professional, avoid cheap graphics).
3. **Testing:** DO NOT PERFORM WEB BROWSER TESTING ON YOUR OWN UNLESS EXPLICITLY TOLD TO DO SO.
4. **Git & PR Management:**
   * Read `.github/pull_request_template.md` (if available) for PR templates.
   * Read `CONTRIBUTING.md` (if available) for commit message conventions.
   * **For changes >10 files or >300 LOC**, you MUST make a plan for PR restructuring and place it inside `.agents/plans/`. The plan must include: Remote Branch Name, Commit Message, PR Title, PR Description, Files to upload.
   * Each PR should be max 10 files and max 350 LOC.
   * Branch Strategy: One remote branch that merges into `main`, with other feature remote branches merging into that intermediate remote branch for cleaner merges.
   * CI Tests: Ensure PRs do not fail CI tests. Check with caution.
