# Google Hackathon Brainstorm: "GitHub for Events" (Ecosystem OS)

## 1. The Core Concept
Event management platforms like Luma or Eventbrite are built for ticketing and single events. This project builds an **Ecosystem OS**—a collaborative platform that acts like "GitHub for Event Planners," utilizing the Google Ecosystem to turn messy, isolated event data into a structured global network.

### The "GitHub" Metaphor Translation
To ensure event planners (who are non-technical) understand the product, we translate developer concepts into consumer-friendly UX:
* **Repository (Repo)** ➡️ **"Playbook"** or **"Event Blueprint"**
* **Fork** ➡️ **"Adapt Playbook"** or **"Clone & Customize"**
* **Commits / Pull Requests** ➡️ **"Drafts"** or **"Suggested Updates"**
* **Open Source** ➡️ **"Community Gallery"**

---

## 2. The Moat: Why this isn't just a "Luma + LLM Wrapper"
To win the hackathon, the pitch must emphasize infrastructure and ecosystem mapping, rather than just simple event automation.

1. **Knowledge Graph vs. Vector Database:**
   Instead of just doing semantic search for ticketing, the platform uses a **Graph Layer** to track relationships (`Startup A` -> `Mentored By` -> `Mentor B` -> `At Event C`). This allows for deep ecosystem intelligence and matchmaking across multiple events.
2. **Ecosystem Management vs. Event Management:**
   Luma's value ends when the event ends. This platform lives in the "space between events," building persistent, verified profiles for startups and mentors based on their historical event participation.
3. **Open-Source Playbooks (Forking):**
   Unlike Luma where you can only duplicate your own events, this platform allows organizations (e.g., Google) to publish "Public Playbooks" that anyone in the community can fork and adapt.

---

## 3. The 24-Hour MVP Plan: The "Smart Fork"
Given the 24-hour time constraint, the MVP will focus entirely on proving the "Forking" concept while deeply integrating with the mandatory **Google Ecosystem**.

### Tech Stack
* **Frontend:** Next.js / Vue.js (Simple Canva-like dashboard)
* **Backend/AI:** LangChain (Node/Python) + Vertex AI / Gemini API
* **Database:** Firebase/Firestore (for storing the Playbook JSON templates)
* **Integrations:** Google Workspace APIs (Google Drive, Google Docs, Google Forms)

### The 4-Step Planner-Friendly User Flow (The Live Demo)
1. **Discovery (The "Explore" Page):**
   The organizer logs in and sees a beautiful gallery of Community Playbooks (e.g., "Google AI Hackathon Playbook - 500 Attendees").
2. **Inspection:**
   They click a playbook and see what assets are included (Registration Form, Judging Rubric, Schedule).
3. **Action (The "Fork"):**
   They click **"✨ Adapt this Playbook ✨"**. A Gemini-powered chat modal asks how they want to customize it. 
   *Example Prompt:* "I am running this for high school students in London focusing on Climate Tech instead of AI."
4. **Execution & Handoff (The "Wow" Moment):**
   The AI modifies the playbook's base JSON. Using **Google Workspace APIs**, the app automatically:
   * Creates a new Google Drive folder ("Climate Tech Hackathon").
   * Generates a customized judging rubric via Google Docs API.
   * Generates a customized registration form via Google Forms API (or Doc if Forms API is too complex for the timeframe).
   * Hands the user a link to their ready-to-use Google Workspace.

---

## 4. Next Steps for Development
* [ ] Setup Google Cloud Project and enable Vertex AI, Drive API, Docs API, and Forms API.
* [ ] Scaffold the frontend (Next.js/Nuxt) with a mocked login and "Explore" gallery.
* [ ] Create 1 or 2 hardcoded JSON templates in Firestore to represent the "Playbooks".
* [ ] Write the LangChain/Gemini prompt to modify the JSON template based on user input.
* [ ] Build the API integration layer that takes the AI's output and executes the Google Workspace API calls.
