from sqlalchemy.orm import Session
from typing import List, Optional, Dict
from sqlalchemy import func
from fastapi import HTTPException

from app.models.course_vote import CourseVote
from app.models.student import Student
from app.models.course import UniqueCourse  # تغییر از Course به UniqueCourse
from app.schemas.course_vote import CourseVoteCreate


class VoteService:
    def __init__(self, db: Session):
        self.db = db

    def create_vote(self, student_id: int, vote_data: CourseVoteCreate):
        student = self.db.query(Student).filter(Student.id == student_id).first()
        if not student:
            raise HTTPException(status_code=404, detail="Student not found")

        # استفاده از UniqueCourse
        course = self.db.query(UniqueCourse).filter(UniqueCourse.id == vote_data.course_id).first()
        if not course:
            raise HTTPException(status_code=404, detail="Course not found")

        # جلوگیری از رأی تکراری
        existing = self.db.query(CourseVote).filter(
            CourseVote.student_id == student_id,
            CourseVote.course_id == vote_data.course_id,
            CourseVote.term == vote_data.term
        ).first()
        if existing:
            raise HTTPException(status_code=400, detail="You have already voted for this course this term")

        new_vote = CourseVote(
            student_id=student_id,
            course_id=vote_data.course_id,
            vote_type=vote_data.vote_type,
            term=vote_data.term
        )
        self.db.add(new_vote)
        self.db.commit()
        self.db.refresh(new_vote)
        return new_vote

    def get_votes(self, student_id: Optional[int], course_id: Optional[int], term: Optional[str]):
        query = self.db.query(CourseVote)
        if student_id:
            query = query.filter(CourseVote.student_id == student_id)
        if course_id:
            query = query.filter(CourseVote.course_id == course_id)
        if term:
            query = query.filter(CourseVote.term == term)
        return query.all()

    def get_vote_stats(self, course_id: int, term: str) -> Dict:
        likes = self.db.query(func.count(CourseVote.id)).filter(
            CourseVote.course_id == course_id,
            CourseVote.term == term,
            CourseVote.vote_type == "like"
        ).scalar() or 0

        requests = self.db.query(func.count(CourseVote.id)).filter(
            CourseVote.course_id == course_id,
            CourseVote.term == term,
            CourseVote.vote_type == "request"
        ).scalar() or 0

        return {
            "course_id": course_id,
            "term": term,
            "likes": likes,
            "requests": requests,
            "total": likes + requests
        }