"""One-shot script — seeds the 4 community playbooks into Firestore.

Mirrors the data currently hard-coded in:
  frontend/app/page.tsx  (`playbooks` array)
  frontend/app/playbooks/[id]/page.tsx  (`playbooksData` map)

Run:
    cd backend
    source venv/bin/activate
    python seed_playbooks.py

Idempotent — uses `set(merge=True)`.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone

from deps import get_settings
from firestore_db import FirestoreDB

log = logging.getLogger(__name__)


PLAYBOOKS = [
    {
        "id": "google-genai-hackathon",
        "title": "Google GenAI Hackathon",
        "author": "Google Developers",
        "author_uid": None,
        "description": (
            "A comprehensive 48-hour hackathon playbook focused on generative AI. "
            "Includes registration forms, judging rubrics, and mentor matching logic."
        ),
        "attendees": "200-500",
        "duration": "2 Days",
        "category": "Hackathon",
        "stats": "Used by 124 organizers",
        "visibility": "public",
        "tags": ["Hackathon", "Generative AI", "Google"],
        "context": {
            "challenge": (
                "Build a functioning generative AI prototype using Google Gemini APIs "
                "that solves a real-world problem in education, climate, or health."
            ),
            "targetAudience": (
                "Full-stack developers, AI researchers, and UX designers from "
                "university to mid-senior level."
            ),
            "venue": "Google Campus (or Hybrid), POC: Sarah Jane (Events Lead, sarah@example.com)",
            "techStack": (
                "Google Forms (Registration), Google Sheets (Roster & Mentor Matches), "
                "Google Docs (Rulebook), Google Meet (Virtual Mentorship)"
            ),
        },
        "assets": [
            {"name": "Registration Form", "type": "Google Forms", "icon": "/google-icons/google-forms.svg"},
            {"name": "Participant Roster", "type": "Google Sheets", "icon": "/google-icons/google-sheets.svg"},
            {"name": "Judging Rubric", "type": "Google Docs", "icon": "/google-icons/google-docs.svg"},
        ],
        "features": [
            "Automated Slack invites upon registration",
            "Dynamic mentor-team matching algorithm",
            "Pre-configured judging criteria for AI projects",
            "Certificate generation workflow",
        ],
        "participants": [
            {"name": "Sarah Jane", "role": "Events Lead", "organization": "Google Developers", "email": "sarah@example.com"},
            {"name": "Daniel Okafor", "role": "Organizer / Logistics", "organization": "Google Developers", "email": "daniel@example.com"},
            {"name": "Priya Nair", "role": "Lead Mentor (AI)", "organization": "DeepMind", "email": "priya@example.com"},
            {"name": "Marcus Lee", "role": "Mentor (Full-stack)", "organization": "Vercel", "email": "marcus@example.com"},
            {"name": "Lin Chen", "role": "Judge", "organization": "Google Research", "email": "lin@example.com"},
            {"name": "Aisha Rahman", "role": "Judge", "organization": "Kaggle", "email": "aisha@example.com"},
            {"name": "Tom Bradley", "role": "Sponsor Rep", "organization": "Google Cloud", "email": "tom@example.com"},
            {"name": "Elena Vega", "role": "Participant / Team Lead", "organization": "Stanford AI Club", "email": "elena@example.com"},
            {"name": "Raj Patel", "role": "Participant / Team Lead", "organization": "UC Berkeley", "email": "raj@example.com"},
        ],
    },
    {
        "id": "ycombinator-demo-day",
        "title": "Accelerator Demo Day",
        "author": "Startup Community",
        "author_uid": None,
        "description": (
            "The gold-standard demo day architecture. Pitch schedule, investor "
            "grading sheets, and automated follow-up email templates."
        ),
        "attendees": "50-100",
        "duration": "1 Day",
        "category": "Showcase",
        "stats": "Used by 89 organizers",
        "visibility": "public",
        "tags": ["Demo Day", "Startups", "Investors"],
        "context": {
            "challenge": (
                "Startups pitch their latest progress to an exclusive audience of "
                "top-tier angel investors and venture capitalists to raise seed funding."
            ),
            "targetAudience": (
                "Pre-seed and seed stage founders, Angel Investors, and Venture "
                "Capital Partners."
            ),
            "venue": "Downtown Convention Center, POC: Mike Smith (mike@example.com)",
            "techStack": (
                "Google Forms (Startup Intake), Google Sheets (Investor CRM & "
                "Live Grading), Mailchimp (Follow-ups)"
            ),
        },
        "assets": [
            {"name": "Startup Intake Form", "type": "Google Forms", "icon": "/google-icons/google-forms.svg"},
            {"name": "Investor CRM", "type": "Google Sheets", "icon": "/google-icons/google-sheets.svg"},
            {"name": "Pitch Grading Sheet", "type": "Google Sheets", "icon": "/google-icons/google-sheets.svg"},
        ],
        "features": [
            "Automated investor outreach tracking",
            "Real-time pitch grading aggregation",
            "Post-event follow-up automation",
        ],
        "participants": [
            {"name": "Mike Smith", "role": "Program Director", "organization": "Startup Community", "email": "mike@example.com"},
            {"name": "Hannah Cole", "role": "Operations Lead", "organization": "Startup Community", "email": "hannah@example.com"},
            {"name": "Jessica Lin", "role": "Pitch Coach / Mentor", "organization": "Startup Community", "email": "jessica@example.com"},
            {"name": "Angela Wu", "role": "Angel Investor", "organization": "Sequoia Capital", "email": "angela@example.com"},
            {"name": "David Brooks", "role": "VC Partner", "organization": "a16z", "email": "david@example.com"},
            {"name": "Carlos Mendez", "role": "VC Partner", "organization": "Accel", "email": "carlos@example.com"},
            {"name": "Nina Park", "role": "Founder (Pitching)", "organization": "Aurora Labs", "email": "nina@example.com"},
            {"name": "Sam Iyer", "role": "Founder (Pitching)", "organization": "Nimbus", "email": "sam@example.com"},
        ],
    },
    {
        "id": "tech-conference-pro",
        "title": "Standard Tech Conference",
        "author": "DevRel Masters",
        "author_uid": None,
        "description": (
            "A 3-track tech conference blueprint. Speaker submission forms, "
            "sponsor tier structures, and multi-room scheduling."
        ),
        "attendees": "1000+",
        "duration": "3 Days",
        "category": "Conference",
        "stats": "Used by 45 organizers",
        "visibility": "public",
        "tags": ["Conference", "DevRel"],
        "context": {
            "challenge": (
                "A multi-day, multi-track conference focusing on cutting-edge software "
                "engineering, DevOps, and cloud architecture."
            ),
            "targetAudience": "Software Engineers, CTOs, and DevOps practitioners.",
            "venue": "Grand Hotel Expo, POC: Alice Wong (alice@example.com)",
            "techStack": (
                "Google Forms (CFP), Google Sheets (Master Schedule), Google Docs "
                "(Sponsor Prospectus)"
            ),
        },
        "assets": [
            {"name": "Speaker CFP", "type": "Google Forms", "icon": "/google-icons/google-forms.svg"},
            {"name": "Master Schedule", "type": "Google Sheets", "icon": "/google-icons/google-sheets.svg"},
            {"name": "Sponsor Prospectus", "type": "Google Docs", "icon": "/google-icons/google-docs.svg"},
        ],
        "features": [
            "Speaker CFP management and voting",
            "Sponsor onboarding workflow",
            "Attendee ticketing sync",
        ],
        "participants": [
            {"name": "Alice Wong", "role": "Conference Chair", "organization": "DevRel Masters", "email": "alice@example.com"},
            {"name": "Greg Thompson", "role": "Track Lead (DevOps)", "organization": "DevRel Masters", "email": "greg@example.com"},
            {"name": "Sophie Adams", "role": "Volunteer Coordinator", "organization": "DevRel Masters", "email": "sophie@example.com"},
            {"name": "Maria Santos", "role": "Speaker", "organization": "Stripe", "email": "maria@example.com"},
            {"name": "Kenji Tanaka", "role": "Speaker", "organization": "GitHub", "email": "kenji@example.com"},
            {"name": "Omar Haddad", "role": "Speaker", "organization": "Datadog", "email": "omar@example.com"},
            {"name": "Tom Bradley", "role": "Sponsor Rep", "organization": "Google Cloud", "email": "tom@example.com"},
            {"name": "Ravi Kumar", "role": "Attendee Liaison", "organization": "DevRel Masters", "email": "ravi@example.com"},
        ],
    },
    {
        "id": "university-climate-sprint",
        "title": "University Climate Sprint",
        "author": "EcoTech Labs",
        "author_uid": None,
        "description": (
            "A beginner-friendly design sprint focusing on climate tech. Great "
            "for high schools and universities."
        ),
        "attendees": "50-200",
        "duration": "1 Day",
        "category": "Sprint",
        "stats": "Used by 210 organizers",
        "visibility": "public",
        "tags": ["Sprint", "Climate Tech", "Education"],
        "context": {
            "challenge": (
                "Design an innovative conceptual solution or app mockup aimed at "
                "reducing carbon footprints in urban environments."
            ),
            "targetAudience": (
                "University students, high school coders, and design enthusiasts."
            ),
            "venue": "University Main Library, POC: Prof. Davis (davis@example.edu)",
            "techStack": (
                "Google Forms (Sign-up), Google Sheets (Team Formation), Google "
                "Docs (Sprint Guide)"
            ),
        },
        "assets": [
            {"name": "Sign-up Form", "type": "Google Forms", "icon": "/google-icons/google-forms.svg"},
            {"name": "Team Formation", "type": "Google Sheets", "icon": "/google-icons/google-sheets.svg"},
            {"name": "Design Sprint Guide", "type": "Google Docs", "icon": "/google-icons/google-docs.svg"},
        ],
        "features": [
            "Beginner-friendly step-by-step instructions",
            "Pre-filled templates for ideation",
            "Simple judging rubrics",
        ],
        "participants": [
            {"name": "Prof. Davis", "role": "Faculty Lead", "organization": "University", "email": "davis@example.edu"},
            {"name": "Emma Lawson", "role": "Student Organizer", "organization": "EcoTech Labs", "email": "emma@example.com"},
            {"name": "Noah Kim", "role": "Mentor (Design)", "organization": "EcoTech Labs", "email": "noah@example.com"},
            {"name": "Grace Park", "role": "Mentor (Climate Tech)", "organization": "EcoTech Labs", "email": "grace@example.com"},
            {"name": "Dr. Helen Cho", "role": "Judge", "organization": "Climate Research Institute", "email": "helen@example.com"},
            {"name": "Jordan Blake", "role": "Sponsor Rep", "organization": "EcoTech Labs", "email": "jordan@example.com"},
            {"name": "Liam Foster", "role": "Participant", "organization": "University", "email": "liam@example.com"},
            {"name": "Mia Torres", "role": "Participant", "organization": "University", "email": "mia@example.com"},
        ],
    },
]


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    settings = get_settings()
    db = FirestoreDB(project_id=settings.gcp_project, database=settings.firestore_database)
    now = datetime.now(timezone.utc)
    for pb in PLAYBOOKS:
        payload = {**pb, "created_at": now, "updated_at": now}
        db.upsert_playbook(payload)
        log.info("seeded: %s", pb["id"])
    log.info("Done. %d playbooks in Firestore.", len(PLAYBOOKS))


if __name__ == "__main__":
    main()
