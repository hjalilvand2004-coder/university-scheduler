# backend/app/api/routes_feedback.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Dict, Any
from pydantic import BaseModel
from datetime import datetime

from app.core.database import get_db
from app.services.feedback_service import FeedbackService

router = APIRouter(prefix="/api/feedback", tags=["Feedback"])


# ---------- مدل‌های Pydantic برای ورودی/خروجی ----------
class FeedbackSubmitRequest(BaseModel):
    schedule_version_id: int
    ratings: Dict[str, int]  # {'instructor': 4, 'time': 5, ...}
    comment: str = ""
    submitted_at: datetime


class FeedbackStatsResponse(BaseModel):
    total_feedback: int
    avg_overall: float
    avg_instructor: float
    avg_time: float
    avg_room: float
    avg_comment_length: float


# ---------- مسیرهای API ----------
@router.post("/submit")
def submit_feedback(
    feedback_data: FeedbackSubmitRequest,
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    ثبت بازخورد کاربر
    """
    try:
        service = FeedbackService(db)
        result = service.collect_feedback(feedback_data.dict())
        return {
            "status": "success",
            "message": "بازخورد با موفقیت ثبت شد",
            "data": result
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"خطا در ثبت بازخورد: {str(e)}")


@router.get("/analysis")
def get_feedback_analysis(
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    دریافت تحلیل بازخوردها و وزن‌های تنظیم‌شده
    """
    try:
        service = FeedbackService(db)
        analysis = service.analyze_feedback()
        return {
            "status": "success",
            "data": analysis
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"خطا در تحلیل بازخورد: {str(e)}")


@router.get("/weight-history")
def get_weight_history(
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    دریافت تاریخچه تغییرات وزن‌ها
    """
    try:
        service = FeedbackService(db)
        history = service.get_weight_adjustment_history()
        return {
            "status": "success",
            "data": history
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"خطا در دریافت تاریخچه وزن‌ها: {str(e)}")


@router.get("/stats")
def get_feedback_stats(
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    دریافت آمار کلی بازخوردها
    """
    try:
        service = FeedbackService(db)
        stats = service.get_feedback_statistics()
        return {
            "status": "success",
            "data": stats
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"خطا در دریافت آمار بازخورد: {str(e)}")