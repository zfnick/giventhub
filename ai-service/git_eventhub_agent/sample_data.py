STARTUPS = [
    {
        "id": "startup_clima_loop",
        "name": "ClimaLoop",
        "sector": "climate-tech",
        "stage": "seed",
        "location": "Kuala Lumpur",
    },
    {
        "id": "startup_gridwise",
        "name": "GridWise",
        "sector": "climate-tech",
        "stage": "pre-seed",
        "location": "Singapore",
    },
    {
        "id": "startup_paypilot",
        "name": "PayPilot",
        "sector": "fintech",
        "stage": "seed",
        "location": "Jakarta",
    },
]

RELATIONSHIPS = [
    {
        "entity_id": "startup_clima_loop",
        "event": "Google AI Hackathon 2025",
        "edges": ["attended", "met_mentor", "submitted_demo"],
        "people": ["Dr. Aisha Tan", "Cradle Ventures"],
        "evidence": "Won mentor commendation and requested follow-up support.",
    },
    {
        "entity_id": "startup_gridwise",
        "event": "Climate Builders Sprint",
        "edges": ["attended", "met_investor", "joined_office_hours"],
        "people": ["Cradle Ventures", "Northstar Climate Fund"],
        "evidence": "Investor noted strong grid analytics fit during office hours.",
    },
    {
        "entity_id": "startup_paypilot",
        "event": "Fintech Founder Day",
        "edges": ["attended", "met_investor"],
        "people": ["Fintech Angels MY"],
        "evidence": "Relevant fintech relationship, but not climate-tech.",
    },
]
