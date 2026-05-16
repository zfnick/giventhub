# ADK End-to-End Test Plan

Replace `YOUR_TOKEN` with a fresh Google OAuth access token before running.

Run these **in order** — each step builds on the previous one.

---

## Journey 1: Smart Fork (The Hackathon MVP)

**Frontend:** User clicks "Adapt Playbook" on `/playbooks/google-genai-hackathon`
**What it proves:** The core product works — one prompt creates an entire event workspace.

```bash
# STEP 1 — Create full hackathon workspace (drive → docs → forms → sheets)
curl -s -X POST http://localhost:8000/api/workspace \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -F 'prompt=Create a Drive folder called "Google GenAI Hackathon 2026". Inside it create: 1) A Google Form "Participant Registration" with questions Full Name, Email, University, Role, Experience Level, What AI problem are you solving, Team Name. 2) A Google Doc "Judging Rubric" with content about scoring criteria: Innovation 25%, Technical Complexity 25%, Impact 25%, Presentation 15%, Google API Usage 10%, scored 1-5 per criterion. 3) A Google Sheet "Participant Roster" with headers Name, Email, University, Role, Team, Check-in, Score. 4) A Google Doc "Event Schedule" with a two-day hackathon schedule including registration, hacking, mentor hours, demos, and awards.' | python3 -m json.tool
```

**✅ Expected:** 5 assets created, all inside one folder. Each has a URL.

---

## Journey 2: Read Back Assets

**Frontend:** `/playbooks/[id]` detail page loading real asset data
**What it proves:** The workspace assets are real and readable.

```bash
# STEP 2 — List folder contents + read form questions
curl -s -X POST http://localhost:8000/api/workspace \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -F 'prompt=List all files in the "Google GenAI Hackathon 2026" folder, then read the Participant Registration form to show me its questions' | python3 -m json.tool
```

**✅ Expected:** Lists 4 files in the folder + shows 7 form questions.

---

## Journey 3: Search Workspace (Import Flow)

**Frontend:** `/onboarding/import` → user types event name, clicks "Search Workspace"
**What it proves:** Users can discover existing event assets by name.

```bash
# STEP 3 — Search Drive for event-related files
curl -s -X POST http://localhost:8000/api/workspace \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -F 'prompt=Search my Drive for files related to "GenAI Hackathon". List all matching files with their name, type, and URL.' | python3 -m json.tool
```

**✅ Expected:** Finds the folder + all assets created in Step 1.

---

## Journey 4: Import Past Event (Reverse-Engineer Playbook)

**Frontend:** `/onboarding/review` → after scanning, AI generates a playbook summary
**What it proves:** The system can read existing assets and synthesize a playbook.

```bash
# STEP 4 — Read existing assets, create a summary doc
curl -s -X POST http://localhost:8000/api/workspace \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -F 'prompt=Read the Google Form "Participant Registration" to get its questions, and read the Google Doc "Judging Rubric" to get the scoring criteria. Then create a new Google Doc called "GenAI Hackathon Playbook Summary" in the "Google GenAI Hackathon 2026" folder that summarizes the event structure including registration questions and judging criteria.' | python3 -m json.tool
```

**✅ Expected:** Reads the form + doc, creates a new summary doc in the same folder.

---

## Journey 5: Post-Event Ops (CRM + Email Follow-up)

**Frontend:** Future feature — post-event lifecycle management
**What it proves:** Cross-domain chaining: update a sheet row, then draft an email.

```bash
# STEP 5 — Add a participant to the roster, then draft a follow-up email
curl -s -X POST http://localhost:8000/api/workspace \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -F 'prompt=Add a row to the "Participant Roster" sheet with values: Jane Doe, jane@stanford.edu, Stanford, Developer, Team Alpha, Yes, 22. Then create a Gmail draft to jane@stanford.edu with subject "Congratulations from GenAI Hackathon" and body "Hi Jane, congratulations on your performance at the GenAI Hackathon! Your team scored 22/25."' | python3 -m json.tool
```

**✅ Expected:** 1 row appended to the sheet + 1 Gmail draft created.

---

## Journey 6: Ecosystem Intelligence (The Moat)

**Frontend:** `/chat` → "Explore Connections" knowledge graph
**What it proves:** Cross-service reads that power the knowledge graph — what Luma can't do.

```bash
# STEP 6 — Read event data + schedule a follow-up from it
curl -s -X POST http://localhost:8000/api/workspace \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -F 'prompt=Read the "Participant Roster" sheet to see the teams, then create a calendar event called "GenAI Hackathon Winners Mentorship" for next Monday 2pm to 3pm with description "Follow-up mentorship for top-scoring teams"' | python3 -m json.tool
```

**✅ Expected:** Reads the sheet, creates a calendar event.

---

## Journey 7: Cross-Domain Dashboard Read

**Frontend:** `/chat` — user asks about their ecosystem
**What it proves:** Gmail batch API + Calendar reads work together.

```bash
# STEP 7 — Fetch emails + calendar events in one request
curl -s -X POST http://localhost:8000/api/workspace \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -F 'prompt=Show my 3 latest emails and list my upcoming calendar events' | python3 -m json.tool
```

**✅ Expected:** 3 emails with metadata (batch API) + calendar events list.

---

## Summary: Agent Coverage

| Journey | Agents Chained | Frontend Screen |
|---------|---------------|-----------------|
| 1. Smart Fork | drive → docs → forms → sheets | `/playbooks/[id]` modal |
| 2. Read Back | drive → forms | `/playbooks/[id]` assets |
| 3. Search | drive | `/onboarding/import` |
| 4. Import | forms → docs → docs | `/onboarding/review` |
| 5. Post-Event | sheets → gmail | Future |
| 6. Ecosystem | sheets → calendar | `/chat` |
| 7. Dashboard | gmail → calendar | `/chat` |
