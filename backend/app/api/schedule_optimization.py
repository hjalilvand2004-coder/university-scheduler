# app/api/schedule_optimization.py
@router.post("/optimize/{schedule_id}")
async def optimize_schedule(schedule_id: int, background_tasks: BackgroundTasks):
    """اجرای بهینه‌سازی خودکار با OR-Tools"""
    result = await optimization_service.optimize(schedule_id)
    return {"status": "started", "task_id": result.task_id}

@router.get("/suggestions/{schedule_id}")
async def get_improvement_suggestions(schedule_id: int):
    """دریافت پیشنهادات جابه‌جایی هوشمند"""
    suggestions = optimization_service.suggest_improvements(schedule_id)
    return {"suggestions": suggestions}

@router.post("/feedback")
async def submit_feedback(feedback: FeedbackCreate):
    """ثبت بازخورد کاربر و تنظیم تدریجی وزن‌ها"""
    await feedback_service.collect_feedback(feedback)
    # در پس‌زمینه: تنظیم وزن‌ها
    return {"message": "Feedback received"}