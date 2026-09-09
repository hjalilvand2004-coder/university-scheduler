from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional

from app.core.database import get_db
from app.schemas.course_vote import CourseVoteCreate, CourseVoteResponse
from app.services.vote_service import VoteService

router = APIRouter(prefix="/votes", tags=["Course Votes"])

@router.post("/", response_model=CourseVoteResponse)
def create_vote(
    vote: CourseVoteCreate,
    student_id: int,
    db: Session = Depends(get_db)
):
    """دانشجو به یک درس رأی می‌دهد (لایک یا درخواست ارائه)"""
    service = VoteService(db)
    return service.create_vote(student_id, vote)

@router.get("/", response_model=List[CourseVoteResponse])
def get_votes(
    student_id: Optional[int] = None,
    course_id: Optional[int] = None,
    term: Optional[str] = None,
    db: Session = Depends(get_db)
):
    service = VoteService(db)
    return service.get_votes(student_id, course_id, term)

@router.get("/stats/{course_id}")
def get_vote_stats(course_id: int, term: str, db: Session = Depends(get_db)):
    """آمار رأی‌های یک درس در یک ترم مشخص"""
    service = VoteService(db)
    return service.get_vote_stats(course_id, term)