from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional

from app.core.database import get_db
from app.models.course_rating import CourseRating
from app.schemas.course_rating import CourseRatingCreate, CourseRatingResponse
from app.services.rating_service import RatingService

router = APIRouter(prefix="/ratings", tags=["Course Ratings"])

@router.post("/", response_model=CourseRatingResponse)
def create_rating(
    rating: CourseRatingCreate,
    student_id: int,
    db: Session = Depends(get_db)
):
    """دانشجو به برنامه زمانی ارائه شده امتیاز می‌دهد"""
    service = RatingService(db)
    return service.create_rating(student_id, rating)

@router.get("/", response_model=List[CourseRatingResponse])
def get_ratings(
    student_id: Optional[int] = None,
    schedule_id: Optional[int] = None,
    db: Session = Depends(get_db)
):
    service = RatingService(db)
    return service.get_ratings(student_id, schedule_id)

@router.get("/stats/{schedule_id}")
def get_rating_stats(schedule_id: int, db: Session = Depends(get_db)):
    """آمار امتیازهای یک برنامه زمانی"""
    service = RatingService(db)
    return service.get_rating_stats(schedule_id)