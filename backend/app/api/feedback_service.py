# backend/app/api/routes_feedback.py
from fastapi import APIRouter, Depends
from app.services.feedback_service import FeedbackService

router = APIRouter(prefix="/api/feedback", tags=["Feedback"])

@router.post("/submit")
def submit_feedback(feedback_data: dict, service: FeedbackService = Depends()):
    """ثبت بازخورد کاربر"""
    return service.collect_feedback(feedback_data)

@router.get("/analysis")
def get_feedback_analysis(service: FeedbackService = Depends()):
    """دریافت گزارش تحلیل رضایت و وزن‌های تنظیم‌شده"""
    return service.analyze_feedback()

@router.get("/weight-history")
def get_weight_history(service: FeedbackService = Depends()):
    """دریافت تاریخچه‌ی تغییرات وزن‌ها"""
    return service.get_weight_adjustment_history()