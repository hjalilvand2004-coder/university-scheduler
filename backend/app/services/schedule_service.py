# app/services/schedule_service.py

from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
import logging

from app.services.schedule.orchestrator import ScheduleOrchestrator
from app.utils.helpers import is_internship_or_project
from app.services.schedule.slot_times import get_slots, normalize_term, time_to_minutes

logger = logging.getLogger(__name__)


class ScheduleService:
    def __init__(self, db: Session):
        self.db = db
        self.orchestrator = ScheduleOrchestrator(db)

    def process(self, basket: List[Dict], term: Optional[str] = None) -> Dict[str, Any]:
        """
        اجرای فرایند کامل زمان‌بندی با استفاده از ارکستراتور.

        Args:
            basket: لیست دروس سبد
            term: شناسه ترم (مثلاً 'mehr', 'bahman', 'summer') - در صورت عدم ارسال، از داده‌ها استخراج می‌شود.

        Returns:
            خروجی ارکستراتور شامل برنامه زمان‌بندی‌شده و گزارش مراحل
        """
        return self.orchestrator.process(basket, term=term)

    def manual_assign(self, manual_assignments: List[Dict], term: Optional[str] = None) -> Dict[str, Any]:
        """
        تخصیص دستی کلاس‌ها با اعتبارسنجی اسلات‌ها بر اساس ترم.

        Args:
            manual_assignments: لیست تخصیص‌های دستی
            term: ترم جاری (اختیاری) - برای اعتبارسنجی اسلات‌ها

        Returns:
            نتیجه تخصیص‌ها با جزئیات موفقیت و خطاها
        """
        if not manual_assignments:
            return {"status": "error", "message": "لیست تخصیص دستی خالی است"}

        logger.info(f"🔄 مرحله دوم: تخصیص دستی {len(manual_assignments)} کلاس")

        # نرمال‌سازی ترم اگر ارسال شده باشد
        term_key = None
        if term:
            try:
                term_key = normalize_term(term)
            except ValueError:
                logger.warning(f"ترم نامعتبر '{term}' - اعتبارسنجی اسلات‌ها انجام نمی‌شود.")
                term_key = None

        results = []
        errors = []

        for idx, assign_data in enumerate(manual_assignments):
            instructor_code = assign_data.get("instructor_code")
            day = assign_data.get("day")
            start = assign_data.get("start")
            end = assign_data.get("end")
            course_name = assign_data.get("course_name")
            group_number = assign_data.get("group_number")
            level = assign_data.get("level")
            term = assign_data.get("term")
            units = assign_data.get("units", 2)  # پیش‌فرض ۲ واحد

            if not instructor_code:
                errors.append(f"ردیف {idx + 1}: کد استاد الزامی است")
                continue

            is_internship = is_internship_or_project(assign_data)

            if not is_internship:
                if day is None or not start or not end:
                    errors.append(f"ردیف {idx + 1}: روز، ساعت شروع و پایان برای دروس عادی الزامی است")
                    continue

                # ===== اعتبارسنجی اسلات با استفاده از slot_times =====
                if term_key:
                    try:
                        # دریافت اسلات‌های مجاز برای ترم و واحد
                        slots_data = get_slots(term=term_key, units=units)
                        valid_slots = [(item['start'], item['end']) for item in slots_data.get('slots', [])]

                        # بررسی اینکه (start, end) در لیست اسلات‌های مجاز باشد
                        if (start, end) not in valid_slots:
                            # تلاش برای یافتن نزدیک‌ترین اسلات مجاز (اختیاری)
                            logger.warning(
                                f"اسلات {start}-{end} برای ترم {term_key} و واحد {units} مجاز نیست. "
                                f"اسلات‌های مجاز: {valid_slots[:5]}..."
                            )
                            errors.append(
                                f"ردیف {idx + 1}: زمان {start}-{end} برای ترم جاری و واحد {units} معتبر نیست. "
                                f"لطفاً از اسلات‌های استاندارد استفاده کنید."
                            )
                            continue
                    except Exception as e:
                        logger.error(f"خطا در اعتبارسنجی اسلات برای ردیف {idx + 1}: {e}")
                        errors.append(f"ردیف {idx + 1}: خطا در اعتبارسنجی زمان: {str(e)}")
                        continue

            # بررسی وجود استاد در دیتابیس
            from app.models.instructor import Instructor
            instructor = self.db.query(Instructor).filter(Instructor.code == instructor_code).first()
            if not instructor:
                errors.append(f"ردیف {idx + 1}: استاد با کد {instructor_code} یافت نشد")
                continue

            # ثبت نتیجه موفق
            result = {
                "status": "success",
                "course_name": course_name,
                "group_number": group_number,
                "instructor_code": instructor.code,
                "instructor_name": instructor.name,
                "day": day,
                "start": start,
                "end": end,
                "message": f"استاد {instructor.name} با موفقیت تخصیص داده شد"
            }
            results.append(result)

        logger.info(f"✅ مرحله دوم: {len(results)} کلاس با موفقیت تخصیص یافت، {len(errors)} خطا")

        return {
            "status": "success" if not errors else "partial",
            "results": results,
            "errors": errors,
            "total": len(manual_assignments),
            "success_count": len(results),
            "error_count": len(errors)
        }