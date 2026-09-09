from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class CourseRatingCreate(BaseModel):
    schedule_id: int
    rating: str  # excellent, good, average, weak, very_weak
    comment: Optional[str] = None

class CourseRatingResponse(BaseModel):
    id: int
    student_id: int
    schedule_id: int
    rating: str
    comment: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True