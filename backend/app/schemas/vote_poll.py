from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

class VotePollBase(BaseModel):
    course_id: int
    term: str
    is_active: bool = True

class VotePollCreate(VotePollBase):
    pass

class VotePollUpdate(BaseModel):
    course_ids: List[int]
    term: str

class VotePollResponse(VotePollBase):
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True