from sqlalchemy.orm import Session
from typing import List, Optional
from fastapi import HTTPException  # ← این خط را اضافه کنید
import json  # ← در صورت استفاده از json.dumps/loads

from app.models.course_proposal import CourseProposal
from app.models.student import Student
from app.schemas.course_proposal import CourseProposalCreate, CourseProposalResponse


class ProposalService:
    def __init__(self, db: Session):
        self.db = db

    def create_proposal(self, student_id: int, proposal_data: CourseProposalCreate):
        # بررسی وجود دانشجو
        student = self.db.query(Student).filter(Student.id == student_id).first()
        if not student:
            raise HTTPException(status_code=404, detail="Student not found")

        new_proposal = CourseProposal(
            student_id=student_id,
            term=proposal_data.term,
            course_ids=json.dumps(proposal_data.course_ids),  # اگر از json استفاده می‌کنید
            description=proposal_data.description
        )
        self.db.add(new_proposal)
        self.db.commit()
        self.db.refresh(new_proposal)
        return new_proposal

    def get_proposals(self, student_id: Optional[int], term: Optional[str]):
        query = self.db.query(CourseProposal)
        if student_id:
            query = query.filter(CourseProposal.student_id == student_id)
        if term:
            query = query.filter(CourseProposal.term == term)
        proposals = query.all()
        # تبدیل course_ids از JSON به لیست
        for p in proposals:
            p.course_ids = json.loads(p.course_ids)
        return proposals

    def get_proposal(self, proposal_id: int):
        proposal = self.db.query(CourseProposal).filter(CourseProposal.id == proposal_id).first()
        if not proposal:
            raise HTTPException(status_code=404, detail="Proposal not found")
        proposal.course_ids = json.loads(proposal.course_ids)
        return proposal