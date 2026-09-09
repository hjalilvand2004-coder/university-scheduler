from pydantic import BaseModel
from datetime import datetime

class CourseVoteCreate(BaseModel):
    course_id: int
    vote_type: str  # "like" یا "request"
    term: str

class CourseVoteResponse(BaseModel):
    id: int
    student_id: int
    course_id: int
    vote_type: str
    term: str
    created_at: datetime

    class Config:
        from_attributes = True