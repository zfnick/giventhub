from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import asyncio

app = FastAPI(title="gieventhub API")

# Add CORS middleware to allow requests from the frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class AdaptRequest(BaseModel):
    prompt: str
    playbookTitle: str

@app.post("/api/adapt")
async def adapt_playbook(req: AdaptRequest):
    # Here we would normally call Gemini 1.5 Pro via google-genai
    # and then interact with Google Workspace APIs.
    # For now, simulate the delay and return success.
    
    # Simulate processing time
    await asyncio.sleep(2.5)
    
    return {
        "status": "success",
        "message": f"Successfully adapted {req.playbookTitle}",
        "workspaceUrl": "https://drive.google.com/drive/folders/mock-folder-id"
    }

class ScanRequest(BaseModel):
    userId: str = "mock-user-id"

@app.post("/api/scan")
async def scan_workspace(req: ScanRequest):
    # Simulate the AI reading through Google Workspace and clustering files
    await asyncio.sleep(4.5)
    return {
        "status": "success",
        "event_detected": True,
        "event_details": {
            "title": "Stanford AI Demo Day 2026",
            "category": "Hackathon",
            "last_active": "2 days ago",
            "assets": [
                {"name": "Demo Day Registration", "type": "Form", "color": "blue"},
                {"name": "Master Roster & Check-in", "type": "Sheet", "color": "green"},
                {"name": "Judge Scoring Rubric", "type": "Doc", "color": "indigo"},
                {"name": "Opening Ceremony Deck", "type": "Slide", "color": "yellow"}
            ]
        }
    }

class CommitRequest(BaseModel):
    title: str
    description: str
    is_public: bool
    commit_message: str

@app.post("/api/commit")
async def commit_playbook(req: CommitRequest):
    # Simulate pushing the AI-generated playbook to the database
    await asyncio.sleep(2.0)
    playbook_id = req.title.lower().replace(" ", "-")
    return {
        "status": "success",
        "playbook_id": playbook_id,
        "message": f"Successfully committed {req.title}"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
