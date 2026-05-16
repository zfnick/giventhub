"""Bulk seed — populates Firestore with ~80 diverse public playbooks.

Designed to make the Explore gallery look like a thriving community of event
organizers. Combinatorially generates playbooks from category x sector x host
x city building blocks. Stable seed → reproducible output.

Run:
    cd backend
    source venv/bin/activate
    python seed_bulk_playbooks.py
"""
from __future__ import annotations

import logging
import random
from datetime import datetime, timedelta, timezone

from deps import get_settings
from firestore_db import FirestoreDB, _slugify

log = logging.getLogger(__name__)


# ── Building blocks ─────────────────────────────────────────────────────────

CATEGORIES = [
    "Hackathon",
    "Demo Day",
    "Conference",
    "Workshop",
    "Meetup",
    "Bootcamp",
    "Summit",
    "Sprint",
    "Showcase",
    "Pitch Night",
]

SECTORS = [
    ("AI", "Generative AI", ["LLM", "Agents", "Gemini", "RAG"]),
    ("Climate", "Climate Tech", ["Carbon", "Renewables", "Grid", "Sustainability"]),
    ("Fintech", "Financial Services", ["Payments", "Banking", "Wealth", "Compliance"]),
    ("Web3", "Crypto & Web3", ["DeFi", "Wallets", "On-chain", "ZK"]),
    ("Healthtech", "Digital Health", ["Telehealth", "Diagnostics", "Wearables", "EHR"]),
    ("EdTech", "Education Tech", ["K-12", "Curriculum", "Tutoring", "Assessment"]),
    ("DevTools", "Developer Platforms", ["Open Source", "DX", "CI/CD", "Observability"]),
    ("Robotics", "Robotics & Automation", ["Mobility", "Industrial", "Drones"]),
    ("BioTech", "Biotech", ["SynBio", "Drug Discovery", "Genomics"]),
    ("Gaming", "Games & Interactive", ["Indie", "Esports", "GenAI Games"]),
    ("Design", "Design & UX", ["Product", "Brand", "Research"]),
    ("Security", "Cybersecurity", ["Offensive", "AppSec", "Threat Intel"]),
    ("Quantum", "Quantum Computing", ["Algorithms", "Hardware", "Cryptography"]),
    ("Hardware", "Hardware & IoT", ["Edge", "Wearables", "Sensors"]),
    ("SaaS", "B2B SaaS", ["Vertical SaaS", "Productivity", "RevOps"]),
    ("Mobile", "Consumer Mobile", ["iOS", "Android", "Cross-platform"]),
    ("Sustainability", "ESG & Sustainability", ["Circular", "Carbon Accounting"]),
]

# Each host has: display name, fake author uid, kind (org|community|individual)
HOSTS: list[tuple[str, str, str]] = [
    # Universities
    ("Stanford ACM", "seed_user_stanford_acm", "org"),
    ("MIT 6.UAR", "seed_user_mit_uar", "org"),
    ("CMU Hackers", "seed_user_cmu_hackers", "org"),
    ("UC Berkeley XR", "seed_user_ucb_xr", "org"),
    ("Harvard Innovation Labs", "seed_user_harvard_iLabs", "org"),
    ("Cambridge AI Society", "seed_user_camai", "org"),
    ("Oxford Founders", "seed_user_oxfdr", "org"),
    ("ETH Zurich D-INFK", "seed_user_eth_infk", "org"),
    ("NUS Hackers", "seed_user_nus_hackers", "org"),
    ("Tsinghua x-lab", "seed_user_tsinghua_xlab", "org"),
    ("IIT Bombay e-Cell", "seed_user_iitb_ecell", "org"),
    # Companies
    ("Google Developers", "seed_user_google_devs", "org"),
    ("Stripe Dev Rel", "seed_user_stripe_dx", "org"),
    ("Vercel Community", "seed_user_vercel_comm", "org"),
    ("Anthropic Builders", "seed_user_anthro_builders", "org"),
    ("OpenAI Forum", "seed_user_openai_forum", "org"),
    ("Shopify Engineering", "seed_user_shopify_eng", "org"),
    ("GitHub Sponsors", "seed_user_gh_sponsors", "org"),
    ("Linear Lab", "seed_user_linear_lab", "org"),
    # Accelerators
    ("Y Combinator", "seed_user_yc", "org"),
    ("Techstars", "seed_user_techstars", "org"),
    ("a16z Crypto Startup School", "seed_user_a16z_css", "org"),
    ("Plug & Play Tech Center", "seed_user_pnp", "org"),
    ("Antler", "seed_user_antler", "org"),
    # Communities
    ("SF AI Builders", "seed_user_sfaib", "community"),
    ("NY Tech Alliance", "seed_user_nyta", "community"),
    ("Berlin AI Salon", "seed_user_berlin_ai", "community"),
    ("London Climate Devs", "seed_user_london_climate", "community"),
    ("Bangalore Hackers", "seed_user_blr_hack", "community"),
    # Individuals
    ("Priya Raman", "seed_user_priya_r", "individual"),
    ("Marcus Lee", "seed_user_marcus_l", "individual"),
    ("Jordan Kim", "seed_user_jordan_k", "individual"),
    ("Amelia Soto", "seed_user_amelia_s", "individual"),
]

CITIES = [
    ("San Francisco, CA", "SOMA Loft 22"),
    ("Palo Alto, CA", "Stanford CodeX"),
    ("Berkeley, CA", "Skydeck Pad 13"),
    ("New York, NY", "Industry City Building 6"),
    ("Boston, MA", "District Hall Seaport"),
    ("Seattle, WA", "South Lake Union Hub"),
    ("Austin, TX", "Capital Factory"),
    ("Toronto, ON", "MaRS Discovery District"),
    ("London, UK", "Plexal East"),
    ("Berlin, DE", "Factory Görlitzer Park"),
    ("Paris, FR", "Station F"),
    ("Amsterdam, NL", "B. Amsterdam"),
    ("Tokyo, JP", "WeWork Marunouchi"),
    ("Singapore", "BLOCK71"),
    ("Bangalore, IN", "Workbench Projects"),
    ("Mumbai, IN", "91springboard BKC"),
]

ATTENDEE_BANDS = ["<50", "50-100", "100-250", "200-500", "500-1000", "1000+"]

DURATION_BY_CATEGORY: dict[str, list[str]] = {
    "Hackathon": ["1 Day", "2 Days", "3 Days"],
    "Demo Day": ["Half Day", "1 Day"],
    "Conference": ["1 Day", "2 Days", "3 Days"],
    "Workshop": ["Half Day", "1 Day"],
    "Meetup": ["Evening"],
    "Bootcamp": ["1 Week", "2 Weeks", "1 Month"],
    "Summit": ["1 Day", "2 Days"],
    "Sprint": ["1 Day", "2 Days"],
    "Showcase": ["Half Day", "1 Day"],
    "Pitch Night": ["Evening"],
}

# Each tool entry = a structured asset {name, type, icon} plus a stack label.
# We pick from a single registry so the "Included Assets" list and the
# techStack string stay in lockstep.
Tool = dict  # {"name", "type", "icon" | None, "stack"}

GOOGLE_ASSETS_BY_CATEGORY: dict[str, list[Tool]] = {
    "Hackathon": [
        {"name": "Registration Form", "type": "Google Forms", "icon": "/google-icons/google-forms.svg", "stack": "Google Forms (registration)"},
        {"name": "Team Roster", "type": "Google Sheets", "icon": "/google-icons/google-sheets.svg", "stack": "Google Sheets (roster)"},
        {"name": "Judging Rubric", "type": "Google Docs", "icon": "/google-icons/google-docs.svg", "stack": "Google Docs (rubric)"},
        {"name": "Mentor Match Tracker", "type": "Google Sheets", "icon": "/google-icons/google-sheets.svg", "stack": "Google Sheets (mentor matching)"},
    ],
    "Demo Day": [
        {"name": "Pitch Order Sheet", "type": "Google Sheets", "icon": "/google-icons/google-sheets.svg", "stack": "Google Sheets (pitch order)"},
        {"name": "Investor RSVP Form", "type": "Google Forms", "icon": "/google-icons/google-forms.svg", "stack": "Google Forms (investor RSVP)"},
        {"name": "Pitch Deck Template", "type": "Google Slides", "icon": "/google-icons/google-slides.svg", "stack": "Google Slides (decks)"},
        {"name": "Live Grading Sheet", "type": "Google Sheets", "icon": "/google-icons/google-sheets.svg", "stack": "Google Sheets (live grading)"},
    ],
    "Conference": [
        {"name": "CFP Form", "type": "Google Forms", "icon": "/google-icons/google-forms.svg", "stack": "Google Forms (CFP)"},
        {"name": "Master Schedule", "type": "Google Sheets", "icon": "/google-icons/google-sheets.svg", "stack": "Google Sheets (schedule)"},
        {"name": "Sponsor Prospectus", "type": "Google Docs", "icon": "/google-icons/google-docs.svg", "stack": "Google Docs (sponsor prospectus)"},
        {"name": "Speaker Deck Template", "type": "Google Slides", "icon": "/google-icons/google-slides.svg", "stack": "Google Slides (speaker decks)"},
    ],
    "Workshop": [
        {"name": "Sign-up Form", "type": "Google Forms", "icon": "/google-icons/google-forms.svg", "stack": "Google Forms (sign-up)"},
        {"name": "Worksheet", "type": "Google Docs", "icon": "/google-icons/google-docs.svg", "stack": "Google Docs (worksheet)"},
        {"name": "Slides", "type": "Google Slides", "icon": "/google-icons/google-slides.svg", "stack": "Google Slides (presentation)"},
    ],
    "Meetup": [
        {"name": "RSVP Form", "type": "Google Forms", "icon": "/google-icons/google-forms.svg", "stack": "Google Forms (RSVP)"},
        {"name": "Run-of-Show", "type": "Google Docs", "icon": "/google-icons/google-docs.svg", "stack": "Google Docs (run-of-show)"},
    ],
    "Bootcamp": [
        {"name": "Application Form", "type": "Google Forms", "icon": "/google-icons/google-forms.svg", "stack": "Google Forms (application)"},
        {"name": "Cohort Roster", "type": "Google Sheets", "icon": "/google-icons/google-sheets.svg", "stack": "Google Sheets (cohort roster)"},
        {"name": "Curriculum Outline", "type": "Google Docs", "icon": "/google-icons/google-docs.svg", "stack": "Google Docs (curriculum)"},
        {"name": "Module Slides", "type": "Google Slides", "icon": "/google-icons/google-slides.svg", "stack": "Google Slides (modules)"},
    ],
    "Summit": [
        {"name": "VIP RSVP Form", "type": "Google Forms", "icon": "/google-icons/google-forms.svg", "stack": "Google Forms (VIP RSVP)"},
        {"name": "Agenda", "type": "Google Docs", "icon": "/google-icons/google-docs.svg", "stack": "Google Docs (agenda)"},
        {"name": "Stakeholder Map", "type": "Google Sheets", "icon": "/google-icons/google-sheets.svg", "stack": "Google Sheets (stakeholder map)"},
    ],
    "Sprint": [
        {"name": "Sign-up Form", "type": "Google Forms", "icon": "/google-icons/google-forms.svg", "stack": "Google Forms (sign-up)"},
        {"name": "Team Formation Sheet", "type": "Google Sheets", "icon": "/google-icons/google-sheets.svg", "stack": "Google Sheets (team formation)"},
        {"name": "Design Brief", "type": "Google Docs", "icon": "/google-icons/google-docs.svg", "stack": "Google Docs (design brief)"},
    ],
    "Showcase": [
        {"name": "Submission Form", "type": "Google Forms", "icon": "/google-icons/google-forms.svg", "stack": "Google Forms (submissions)"},
        {"name": "Demo Lineup", "type": "Google Sheets", "icon": "/google-icons/google-sheets.svg", "stack": "Google Sheets (demo lineup)"},
        {"name": "Press Kit", "type": "Google Docs", "icon": "/google-icons/google-docs.svg", "stack": "Google Docs (press kit)"},
    ],
    "Pitch Night": [
        {"name": "Pitch Application", "type": "Google Forms", "icon": "/google-icons/google-forms.svg", "stack": "Google Forms (pitch application)"},
        {"name": "Run-of-Show", "type": "Google Docs", "icon": "/google-icons/google-docs.svg", "stack": "Google Docs (run-of-show)"},
        {"name": "Scoring Sheet", "type": "Google Sheets", "icon": "/google-icons/google-sheets.svg", "stack": "Google Sheets (scoring)"},
    ],
}

# Non-Google tools — surface in BOTH the assets list and the techStack string
# so the knowledge tree and the Included Assets stay aligned.
EXTRA_TOOLS: list[Tool] = [
    {"name": "Master Run-of-Show", "type": "Notion", "icon": None, "stack": "Notion (run-of-show)"},
    {"name": "Community Hub", "type": "Slack", "icon": None, "stack": "Slack (community)"},
    {"name": "Community Chat", "type": "Discord", "icon": None, "stack": "Discord (community)"},
    {"name": "RSVP Landing Page", "type": "Luma", "icon": None, "stack": "Luma (RSVP)"},
    {"name": "Ticketing Portal", "type": "Eventbrite", "icon": None, "stack": "Eventbrite (ticketing)"},
    {"name": "Livestream", "type": "Streamyard", "icon": None, "stack": "Streamyard (livestream)"},
    {"name": "Brand & Asset Library", "type": "Figma", "icon": None, "stack": "Figma (design)"},
    {"name": "Ops Tracker", "type": "Linear", "icon": None, "stack": "Linear (project tracking)"},
    {"name": "Code & Submissions", "type": "GitHub", "icon": None, "stack": "GitHub (code & submissions)"},
    {"name": "Knowledge Wiki", "type": "Confluence", "icon": None, "stack": "Confluence (wiki)"},
    {"name": "Feedback Survey", "type": "Typeform", "icon": None, "stack": "Typeform (feedback)"},
    {"name": "Email Campaigns", "type": "Mailchimp", "icon": None, "stack": "Mailchimp (email blasts)"},
    {"name": "Investor / Sponsor CRM", "type": "Airtable", "icon": None, "stack": "Airtable (CRM)"},
    {"name": "Mentor Sessions", "type": "Calendly", "icon": None, "stack": "Calendly (mentor scheduling)"},
    {"name": "Onboarding Bot", "type": "Zapier", "icon": None, "stack": "Zapier (automation)"},
    {"name": "Live Captions", "type": "Otter", "icon": None, "stack": "Otter (live captions)"},
]

FEATURE_LIBRARY_BY_CATEGORY: dict[str, list[str]] = {
    "Hackathon": [
        "Automated team formation",
        "Mentor matching algorithm",
        "Live judging rubric aggregation",
        "Slack onboarding bot",
        "Certificate generation workflow",
        "Late-night meal logistics tracker",
    ],
    "Demo Day": [
        "Investor outreach pipeline",
        "Real-time pitch grading",
        "Auto follow-up email sequence",
        "Founder bio handout generator",
    ],
    "Conference": [
        "CFP voting workflow",
        "Multi-track schedule auto-balance",
        "Sponsor tier management",
        "Attendee badge printing",
        "Captions / a11y workflow",
    ],
    "Workshop": [
        "Pre-reads autosend",
        "Live exercise checkpoints",
        "Post-workshop feedback collection",
    ],
    "Meetup": [
        "Auto-RSVP with waitlist",
        "Door check-in via QR",
        "Sponsor shout-out kit",
    ],
    "Bootcamp": [
        "Weekly module gating",
        "1:1 coach matching",
        "Project review pipeline",
        "Alumni Slack onboarding",
    ],
    "Summit": [
        "VIP visa support tracker",
        "Speaker brief packets",
        "Off-record session protocol",
    ],
    "Sprint": [
        "Pre-sprint research brief",
        "Daily standup template",
        "Final deck handoff packet",
    ],
    "Showcase": [
        "Demo station map",
        "Public livestream package",
        "Press follow-up sequence",
    ],
    "Pitch Night": [
        "5-minute pitch timer",
        "Live audience voting",
        "Investor scorecards",
    ],
}

TAG_BANK_BY_CATEGORY: dict[str, list[str]] = {
    "Hackathon": ["Hackathon", "Builders", "Students"],
    "Demo Day": ["Demo Day", "Startups", "Investors"],
    "Conference": ["Conference", "Speakers", "Talks"],
    "Workshop": ["Workshop", "Hands-on", "Education"],
    "Meetup": ["Meetup", "Community"],
    "Bootcamp": ["Bootcamp", "Training", "Cohort"],
    "Summit": ["Summit", "Leadership", "Industry"],
    "Sprint": ["Sprint", "Design", "Prototype"],
    "Showcase": ["Showcase", "Public", "Press"],
    "Pitch Night": ["Pitch", "Investors", "Demo"],
}


# ── Generator ───────────────────────────────────────────────────────────────

def generate_playbook(rng: random.Random, idx: int) -> dict:
    cat = rng.choice(CATEGORIES)
    sector_key, sector_name, sector_focus = rng.choice(SECTORS)
    host, host_uid, host_kind = rng.choice(HOSTS)
    city, venue = rng.choice(CITIES)
    year = rng.choice([2024, 2025, 2026])
    attendees = rng.choice(ATTENDEE_BANDS)
    duration = rng.choice(DURATION_BY_CATEGORY[cat])

    sector_short = sector_key
    title = _generate_title(rng, cat, sector_short, host, year)

    visibility = "public" if rng.random() < 0.92 else "private"
    organizers_used = rng.randint(3, 240)
    stats = f"Used by {organizers_used} organizer{'s' if organizers_used != 1 else ''}"

    challenge = _generate_challenge(rng, cat, sector_name, sector_focus)
    audience = _generate_audience(rng, cat, sector_short, host_kind)
    venue_text = f"{venue}, {city}. POC: {_generate_poc_name(rng)}"

    google_pool = GOOGLE_ASSETS_BY_CATEGORY[cat]
    google_count = min(len(google_pool), rng.randint(2, 3))
    picked_google = rng.sample(google_pool, google_count)

    extra_count = rng.randint(1, 3)
    picked_extra = rng.sample(EXTRA_TOOLS, min(extra_count, len(EXTRA_TOOLS)))

    picked = picked_google + picked_extra
    assets = [
        {"name": t["name"], "type": t["type"], "icon": t["icon"]}
        for t in picked
    ]

    feature_pool = FEATURE_LIBRARY_BY_CATEGORY[cat]
    feat_count = min(len(feature_pool), rng.randint(2, 4))
    features = rng.sample(feature_pool, feat_count)

    base_tags = TAG_BANK_BY_CATEGORY[cat]
    tags = list(dict.fromkeys(base_tags + [sector_short] + rng.sample(sector_focus, min(2, len(sector_focus)))))

    # techStack string is derived from the same tool picks so the knowledge
    # tree and the Included Assets list always reflect the same surfaces.
    tech_stack = ", ".join(t["stack"] for t in picked)

    description = _generate_description(rng, cat, sector_name, host, city, year)

    # Spread timestamps over the past 180 days; bias older events to higher
    # "used by" counts so popular ones feel battle-tested.
    days_ago = rng.randint(1, 180)
    created = datetime.now(timezone.utc) - timedelta(days=days_ago, hours=rng.randint(0, 23))
    updated = created + timedelta(hours=rng.randint(0, 72))

    base_slug = _slugify(f"{title}-{idx}")
    return {
        "id": base_slug,
        "title": title,
        "author": host,
        "author_uid": host_uid,
        "description": description,
        "attendees": attendees,
        "duration": duration,
        "category": cat,
        "stats": stats,
        "visibility": visibility,
        "tags": tags,
        "context": {
            "challenge": challenge,
            "targetAudience": audience,
            "venue": venue_text,
            "techStack": tech_stack,
        },
        "assets": assets,
        "participants": _generate_participants(rng, host),
        "features": features,
        "forked_from": None,
        "timing": "past" if days_ago > 30 else rng.choice(["past", "upcoming"]),
        "created_at": created,
        "updated_at": updated,
    }


TITLE_TEMPLATES = {
    "Hackathon": [
        "{host} {sector} Hackathon {year}",
        "{sector} Hack {year} — Hosted by {host}",
        "{host} Build Weekend: {sector} Edition",
    ],
    "Demo Day": [
        "{host} {sector} Demo Day {year}",
        "{sector} Founders Demo Day {year}",
    ],
    "Conference": [
        "{sector}Conf {year} — by {host}",
        "{host} {sector} Summit Conference {year}",
    ],
    "Workshop": [
        "{host} {sector} Workshop Series",
        "Intro to {sector} — Workshop by {host}",
    ],
    "Meetup": [
        "{host} {sector} Meetup",
        "{sector} Builders Night — {host}",
    ],
    "Bootcamp": [
        "{host} {sector} Bootcamp {year}",
        "{sector} Fundamentals — {host} Bootcamp",
    ],
    "Summit": [
        "{host} {sector} Leadership Summit {year}",
        "{sector} Industry Summit {year}",
    ],
    "Sprint": [
        "{host} {sector} Design Sprint",
        "{sector} Build Sprint {year}",
    ],
    "Showcase": [
        "{host} {sector} Showcase {year}",
        "{sector} Student Showcase — {host}",
    ],
    "Pitch Night": [
        "{host} {sector} Pitch Night",
        "{sector} Founders Pitch — {host}",
    ],
}


def _generate_title(
    rng: random.Random, cat: str, sector: str, host: str, year: int,
) -> str:
    template = rng.choice(TITLE_TEMPLATES[cat])
    return template.format(host=host, sector=sector, year=year)


def _generate_description(
    rng: random.Random, cat: str, sector_name: str, host: str, city: str, year: int,
) -> str:
    intros = {
        "Hackathon": [
            "A high-energy build event where teams ship working {sector} prototypes against a shared theme.",
            "An intensive build sprint focused on {sector}. Includes mentor sessions, judging tracks, and post-event publication.",
        ],
        "Demo Day": [
            "The capstone showcase for {host}'s latest cohort. Founders pitch progress to a curated investor audience.",
            "A polished demo day for {sector} startups. Investor outreach, live grading, and follow-up automation included.",
        ],
        "Conference": [
            "A multi-track conference for the {sector} community. CFP voting, sponsor onboarding, and attendee logistics covered.",
            "{host}'s annual gathering for {sector} practitioners. Speakers, sponsors, and side events fully scoped.",
        ],
        "Workshop": [
            "A hands-on workshop introducing {sector} fundamentals. Pre-reads, exercises, and post-workshop materials included.",
        ],
        "Meetup": [
            "A relaxed evening meetup for the {sector} community in {city}. Lightning talks + casual networking.",
        ],
        "Bootcamp": [
            "{host}'s structured cohort program covering {sector}. Weekly modules, coach matching, and capstone reviews.",
        ],
        "Summit": [
            "A by-invitation summit gathering {sector} leaders. Off-record sessions, speaker briefs, and VIP logistics.",
        ],
        "Sprint": [
            "A focused design sprint applying methodology to {sector} problems. Daily standups and handoff packet provided.",
        ],
        "Showcase": [
            "A public showcase highlighting recent {sector} work from {host}. Press kits, demo stations, and follow-up sequences.",
        ],
        "Pitch Night": [
            "An evening pitch competition for {sector} founders in {city}. Audience voting + investor scorecards.",
        ],
    }
    intro = rng.choice(intros.get(cat, ["A community-led event in {sector}."]))
    closer = rng.choice([
        "Fork it to run your own variant.",
        "Used by organizers across multiple cohorts.",
        "Tuned over multiple cycles — ready to clone.",
        "Includes everything from registration to follow-up.",
    ])
    body = intro.format(sector=sector_name, host=host, city=city.split(",")[0])
    return f"{body} {closer}"


def _generate_challenge(rng: random.Random, cat: str, sector_name: str, focus_options: list[str]) -> str:
    focus = rng.choice(focus_options) if focus_options else sector_name
    options = {
        "Hackathon": (
            f"Build a working prototype in {sector_name} centered on {focus.lower()}. "
            "Teams have 48h, two mentor sessions, and a final 4-minute demo."
        ),
        "Demo Day": (
            f"Present material progress on a {sector_name} startup leveraging {focus.lower()}. "
            "Targeting seed/Series A investors."
        ),
        "Conference": (
            f"Convene leaders in {sector_name} for a multi-track program on {focus.lower()}. "
            "Mix of plenaries, lightning talks, and workshops."
        ),
        "Workshop": (
            f"Hands-on introduction to {sector_name} with a focus on {focus.lower()}. "
            "Participants leave with a runnable artifact."
        ),
        "Meetup": (
            f"Casual meetup for {sector_name} builders — 2 lightning talks then open networking."
        ),
        "Bootcamp": (
            f"Multi-week structured curriculum on {sector_name} with weekly capstones. "
            f"Module focus: {focus.lower()}."
        ),
        "Summit": (
            f"Leadership-level summit on {sector_name}. Off-record discussions on {focus.lower()}."
        ),
        "Sprint": (
            f"5-day design sprint applying methodology to {sector_name} problems around {focus.lower()}."
        ),
        "Showcase": (
            f"Public showcase of student-led {sector_name} work, themed around {focus.lower()}."
        ),
        "Pitch Night": (
            f"5-minute pitches from {sector_name} founders. Theme: {focus.lower()}."
        ),
    }
    return options.get(cat, f"Event around {sector_name} and {focus.lower()}.")


def _generate_audience(rng: random.Random, cat: str, sector: str, host_kind: str) -> str:
    base = {
        "org": "Industry professionals",
        "community": "Builders and operators",
        "individual": "Friends-of-friends and curated invites",
    }[host_kind]
    student_clause = ", students from local programs" if host_kind == "org" and rng.random() < 0.5 else ""
    sector_clause = f", with strong interest in {sector.lower()}"
    return f"{base}{student_clause}{sector_clause}."


PARTICIPANT_FIRST_NAMES = [
    "Alex", "Priya", "Marcus", "Sarah", "Jordan", "Lin", "Wei", "Amelia",
    "David", "Sophie", "Yusuf", "Carmen", "Ravi", "Mei", "Noah", "Zara",
    "Diego", "Hannah", "Omar", "Grace", "Kenji", "Elena", "Tom", "Aisha",
    "Daniel", "Nina", "Sam", "Maya", "Leo", "Fatima",
]

PARTICIPANT_LAST_NAMES = [
    "Chen", "Patel", "Okafor", "Nguyen", "Santos", "Kim", "Haddad", "Lee",
    "Rahman", "Brooks", "Mendez", "Adams", "Kumar", "Tanaka", "Vega",
    "Foster", "Cole", "Park", "Wong", "Bradley", "Lawson", "Torres",
]

# Roles that make up "everyone involved in the event". Weighted so a roster
# skews toward mentors and attendees, with a couple of organizers up top.
PARTICIPANT_ROLE_WEIGHTS: list[tuple[str, int]] = [
    ("Mentor", 3),
    ("Judge", 2),
    ("Speaker", 2),
    ("Sponsor Rep", 1),
    ("Participant", 5),
]

# Orgs that external roles (mentors, judges, speakers, sponsors) belong to.
PARTICIPANT_ORG_POOL = [
    "Google", "DeepMind", "Stripe", "Vercel", "GitHub", "Datadog",
    "Sequoia Capital", "a16z", "Accel", "Anthropic", "OpenAI", "Figma",
    "Independent", "Local University",
]


def _generate_poc_name(rng: random.Random) -> str:
    first = rng.choice([
        "Alex", "Priya", "Marcus", "Sarah", "Jordan", "Lin", "Wei",
        "Amelia", "David", "Sophie", "Yusuf", "Carmen", "Ravi", "Mei",
        "Noah", "Zara", "Diego", "Hannah",
    ])
    last_initial = rng.choice("ABCDEFGHIJKLMNOPQRSTUVWXYZ")
    return f"{first} {last_initial}."


def _generate_participants(rng: random.Random, host: str) -> list[dict]:
    """Build a roster of everyone involved — organizers, mentors, judges,
    speakers, sponsors, and attendees — for the knowledge tree."""
    count = rng.randint(7, 12)
    roles = ["Organizer", "Operations Lead"]
    pool = [r for r, _ in PARTICIPANT_ROLE_WEIGHTS]
    weights = [w for _, w in PARTICIPANT_ROLE_WEIGHTS]
    roles += rng.choices(pool, weights=weights, k=count - 2)

    used_names: set[str] = set()
    roster: list[dict] = []
    for role in roles:
        name = f"{rng.choice(PARTICIPANT_FIRST_NAMES)} {rng.choice(PARTICIPANT_LAST_NAMES)}"
        guard = 0
        while name in used_names and guard < 25:
            name = f"{rng.choice(PARTICIPANT_FIRST_NAMES)} {rng.choice(PARTICIPANT_LAST_NAMES)}"
            guard += 1
        used_names.add(name)

        org = host if role in ("Organizer", "Operations Lead") else rng.choice(PARTICIPANT_ORG_POOL)
        first, last = name.split(" ", 1)
        email = f"{first.lower()}.{last[0].lower()}@example.com"
        roster.append({"name": name, "role": role, "organization": org, "email": email})
    return roster


# ── Main ────────────────────────────────────────────────────────────────────

def main(count: int = 80) -> None:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    settings = get_settings()
    db = FirestoreDB(project_id=settings.gcp_project, database=settings.firestore_database)

    rng = random.Random(42)
    seen_ids: set[str] = set()
    written = 0

    for i in range(count):
        playbook = generate_playbook(rng, idx=i)
        # Ensure unique slugs even if title duplicates (handled by idx suffix
        # in _slugify input, but double-check here).
        if playbook["id"] in seen_ids:
            playbook["id"] = f"{playbook['id']}-{i}"
        seen_ids.add(playbook["id"])
        db.upsert_playbook(playbook)
        written += 1
        if written % 10 == 0:
            log.info("seeded %d…", written)

    log.info("Done. %d bulk playbooks in Firestore.", written)


if __name__ == "__main__":
    main()
