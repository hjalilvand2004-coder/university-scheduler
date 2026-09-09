from sqlalchemy.orm import Session
from sqlalchemy import and_
from typing import List, Optional
from fastapi import HTTPException, status

from app.models.vote_poll import VotePoll
from app.models.course import UniqueCourse
from app.schemas.vote_poll import VotePollCreate, VotePollUpdate


class VotePollService:
    def __init__(self, db: Session):
        self.db = db

    def get_active_courses(self, term: str) -> List[UniqueCourse]:
        active_polls = self.db.query(VotePoll).filter(
            and_(VotePoll.term == term, VotePoll.is_active == True)
        ).all()

        course_ids = [poll.course_id for poll in active_polls]
        if not course_ids:
            return []

        courses = self.db.query(UniqueCourse).filter(
            UniqueCourse.id.in_(course_ids)
        ).all()
        return courses

    def update_vote_polls(self, term: str, course_ids: List[int]) -> dict:
        self.db.query(VotePoll).filter(VotePoll.term == term).update(
            {"is_active": False}
        )

        for course_id in course_ids:
            existing = self.db.query(VotePoll).filter(
                and_(VotePoll.course_id == course_id, VotePoll.term == term)
            ).first()

            if existing:
                existing.is_active = True
            else:
                new_poll = VotePoll(
                    course_id=course_id,
                    term=term,
                    is_active=True
                )
                self.db.add(new_poll)

        self.db.commit()
        return {
            "message": "نظرسنجی با موفقیت به‌روزرسانی شد",
            "term": term,
            "active_course_ids": course_ids,
            "count": len(course_ids)
        }