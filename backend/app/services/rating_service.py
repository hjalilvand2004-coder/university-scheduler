from sqlalchemy.orm import Session
from typing import List, Optional, Dict
from sqlalchemy import func
from fastapi import HTTPException

from app.models.course_rating import CourseRating
from app.models.student import Student
from app.models.schedule import ScheduledClass  # تغییر از Schedule به ScheduledClass
from app.schemas.course_rating import CourseRatingCreate


class RatingService:
    def __init__(self, db: Session):
        self.db = db

    def create_rating(self, student_id: int, rating_data: CourseRatingCreate):
        student = self.db.query(Student).filter(Student.id == student_id).first()
        if not student:
            raise HTTPException(status_code=404, detail="Student not found")

        # استفاده از ScheduledClass
        schedule = self.db.query(ScheduledClass).filter(ScheduledClass.id == rating_data.schedule_id).first()
        if not schedule:
            raise HTTPException(status_code=404, detail="Schedule not found")

        existing = self.db.query(CourseRating).filter(
            CourseRating.student_id == student_id,
            CourseRating.schedule_id == rating_data.schedule_id
        ).first()
        if existing:
            raise HTTPException(status_code=400, detail="You have already rated this schedule")

        new_rating = CourseRating(
            student_id=student_id,
            schedule_id=rating_data.schedule_id,
            rating=rating_data.rating,
            comment=rating_data.comment
        )
        self.db.add(new_rating)
        self.db.commit()
        self.db.refresh(new_rating)
        return new_rating

    def get_ratings(self, student_id: Optional[int], schedule_id: Optional[int]):
        query = self.db.query(CourseRating)
        if student_id:
            query = query.filter(CourseRating.student_id == student_id)
        if schedule_id:
            query = query.filter(CourseRating.schedule_id == schedule_id)
        return query.all()

    def get_rating_stats(self, schedule_id: int) -> Dict:
        ratings = ["excellent", "good", "average", "weak", "very_weak"]
        stats = {}
        total = 0

        for r in ratings:
            count = self.db.query(func.count(CourseRating.id)).filter(
                CourseRating.schedule_id == schedule_id,
                CourseRating.rating == r
            ).scalar() or 0
            stats[r] = count
            total += count

        stats["total"] = total
        stats["schedule_id"] = schedule_id
        return stats