from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import List

from app.core.database import get_db
from app.schemas.vote_poll import VotePollUpdate
from app.services.vote_poll_service import VotePollService

router = APIRouter(prefix="/vote-polls", tags=["Vote Polls"])

@router.get("/active")
def get_active_vote_polls(
    term: str = Query(..., description="ترم مورد نظر (مثال: 1405-mehr)"),
    db: Session = Depends(get_db)
):
    service = VotePollService(db)
    courses = service.get_active_courses(term)
    return courses

@router.post("/update")
def update_vote_polls(
    payload: VotePollUpdate,
    db: Session = Depends(get_db)
):
    service = VotePollService(db)
    result = service.update_vote_polls(payload.term, payload.course_ids)
    return result