# app/api/routes_optimization.py
from fastapi import APIRouter, Depends, HTTPException, status
from typing import List, Dict, Any, Optional
import logging

from sqlalchemy.orm import Session

from app.services.optimization_service import OptimizationService
from app.schemas.schedule import OptimizationRequest, OptimizationResponse
from app.services.schedule.slot_times import normalize_term
from app.models.course import UniqueCourse
from app.models.term_course import TermCourse

# ===== وارد کردن صحیح get_db =====
from app.core.database import get_db  # <-- اصلاح: import صحیح

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/optimization",
    tags=["Optimization"],
    responses={
        404: {"description": "Not found"},
        500: {"description": "Internal server error"},
    },
)


def enrich_course_names(schedule: List[Dict[str, Any]], db: Session) -> List[Dict[str, Any]]:
    """
    اطمینان از وجود course_name در هر کلاس.
    اگر course_name خالی باشد، از دیتابیس (unique_courses یا term_courses) دریافت می‌کند.
    """
    if not schedule or db is None:
        return schedule

    # جمع‌آوری course_codeهای موجود
    course_codes = list(set([item.get("course_code") for item in schedule if item.get("course_code")]))
    course_name_map = {}

    if course_codes:
        try:
            # دریافت از unique_courses
            unique_courses = db.query(UniqueCourse).filter(UniqueCourse.code.in_(course_codes)).all()
            for uc in unique_courses:
                course_name_map[uc.code] = uc.title
            logger.info(f"📚 از unique_courses {len(course_name_map)} نام درس دریافت شد.")
        except Exception as e:
            logger.warning(f"⚠️ خطا در دریافت نام درس از unique_courses: {e}")

        # اگر برخی از course_codeها هنوز نام ندارند، از term_courses دریافت کن
        missing_codes = [code for code in course_codes if code not in course_name_map]
        if missing_codes:
            try:
                term_courses = db.query(TermCourse).filter(TermCourse.unique_course_code.in_(missing_codes)).all()
                for tc in term_courses:
                    if tc.unique_course_code not in course_name_map:
                        course_name_map[tc.unique_course_code] = tc.course_name or tc.unique_course_name or tc.unique_course_code
                logger.info(f"📚 از term_courses {len(term_courses)} نام درس تکمیلی دریافت شد.")
            except Exception as e:
                logger.warning(f"⚠️ خطا در دریافت نام درس از term_courses: {e}")

    # به‌روزرسانی آیتم‌ها
    enriched = []
    for item in schedule:
        course_code = item.get("course_code")
        if course_code and course_code in course_name_map:
            if not item.get("course_name"):
                item["course_name"] = course_name_map[course_code]
            if not item.get("course_title"):
                item["course_title"] = course_name_map[course_code]
        enriched.append(item)

    return enriched


@router.post("/optimize", response_model=OptimizationResponse)
def optimize_schedule(
        request: OptimizationRequest,
        db: Session = Depends(get_db),  # <-- اصلاح: استفاده از get_db واقعی
):
    """
    بهینه‌سازی برنامه زمان‌بندی با استفاده از الگوریتم‌های پیشرفته.
    """
    try:
        if not request.schedule:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="برنامه ورودی خالی است. لطفاً کلاس‌ها را ارسال کنید."
            )

        # استخراج ترم از درخواست
        term: Optional[str] = None

        if hasattr(request, 'term') and request.term:
            try:
                term = normalize_term(request.term)
                logger.info(f"ترم از درخواست: {term}")
            except ValueError as e:
                logger.warning(f"ترم ارسالی نامعتبر است: {request.term} - {e}")
                term = None

        if not term:
            first_course = request.schedule[0] if request.schedule else {}
            term_key = first_course.get("term_key")
            if term_key:
                term = term_key
                logger.info(f"ترم از term_key داده‌ها: {term}")
            else:
                term_raw = first_course.get("term", "")
                if term_raw:
                    try:
                        term = normalize_term(term_raw)
                        logger.info(f"ترم از فیلد term داده‌ها: {term}")
                    except ValueError:
                        logger.warning(f"ترم نامعتبر در داده‌ها: {term_raw} - از پیش‌فرض استفاده می‌شود")
                        term = "mehr"
                else:
                    term = "mehr"
                    logger.info("ترم مشخص نشد، استفاده از پیش‌فرض: mehr")

        logger.info(f"دریافت درخواست بهینه‌سازی با {len(request.schedule)} کلاس، ترم: {term}")
        if request.workflow_id:
            logger.info(f"workflow_id: {request.workflow_id}")
        if request.basket_id:
            logger.info(f"basket_id: {request.basket_id}")

        # ===== تکمیل نام درس‌ها =====
        enriched_schedule = enrich_course_names(request.schedule, db)
        logger.info(f"📝 نام درس‌ها تکمیل شد. تعداد کلاس‌ها: {len(enriched_schedule)}")

        # ایجاد نمونه از سرویس بهینه‌سازی و پردازش
        service = OptimizationService(db)
        optimized = service.process(enriched_schedule, term=term)

        # ===== اطمینان از وجود course_name در خروجی =====
        optimized = enrich_course_names(optimized, db)

        logger.info(f"بهینه‌سازی با موفقیت انجام شد. تعداد کلاس‌های خروجی: {len(optimized)}")

        return OptimizationResponse(
            success=True,
            message="بهینه‌سازی با موفقیت انجام شد.",
            optimized_schedule=optimized,
            total_classes=len(optimized)
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"خطا در بهینه‌سازی: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"خطا در بهینه‌سازی: {str(e)}"
        )


@router.get("/status/{workflow_id}")
def get_optimization_status(
        workflow_id: int,
        db: Session = Depends(get_db),  # <-- اصلاح
):
    """
    دریافت وضعیت بهینه‌سازی برای یک workflow مشخص.
    """
    return {
        "workflow_id": workflow_id,
        "status": "ready",
        "message": "برنامه آماده بهینه‌سازی است.",
        "last_optimization": None,
    }