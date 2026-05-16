from pydantic import BaseModel


class WorkspaceDraft(BaseModel):
    type: str
    title: str
    summary: str
    requires_approval: bool = True
