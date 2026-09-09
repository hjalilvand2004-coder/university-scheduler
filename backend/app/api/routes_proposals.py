from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
from app.core.database import get_db
from app.schemas.course_proposal import CourseProposalCreate, CourseProposalResponse
from app.services.proposal_service import ProposalService

router = APIRouter(prefix="/proposals", tags=["Course Proposals"])

@router.post("/", response_model=CourseProposalResponse)
def create_proposal(
    proposal: CourseProposalCreate,
    student_id: int,
    db: Session = Depends(get_db)
):
    service = ProposalService(db)
    return service.create_proposal(student_id, proposal)

@router.get("/", response_model=List[CourseProposalResponse])
def get_proposals(
    student_id: Optional[int] = None,
    term: Optional[str] = None,
    db: Session = Depends(get_db)
):
    service = ProposalService(db)
    return service.get_proposals(student_id, term)

@router.get("/{proposal_id}", response_model=CourseProposalResponse)
def get_proposal(proposal_id: int, db: Session = Depends(get_db)):
    service = ProposalService(db)
    return service.get_proposal(proposal_id)