# app/services/schedule_service.py

from typing import List, Dict, Any
from sqlalchemy.orm import Session

from app.services.schedule.orchestrator import ScheduleOrchestrator
from app.utils.helpers import is_internship_or_project

class ScheduleService:
    def __init__(self, db: Session):
        self.db = db
        self.orchestrator = ScheduleOrchestrator(db)

    def process(self, basket: List[Dict]) -> Dict[str, Any]:
        return self.orchestrator.process(basket)

    def manual_assign(self, manual_assignments: List[Dict]) -> Dict[str, Any]:
        # منطق manual_assign را می‌توان در همین فایل نگه داشت یا به یک کلاس مجزا منتقل کرد.
        # برای سادگی، همان کد قبلی را اینجا می‌گذاریم (با تغییرات جزئی import)
        import logging
        logger = logging.getLogger(__name__)
        if not manual_assignments:
            return {"status": "error", "message": "لیست تخصیص دستی خالی است"}

        logger.info(f"🔄 مرحله دوم: تخصیص دستی {len(manual_assignments)} کلاس")

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

            if not instructor_code:
                errors.append(f"ردیف {idx + 1}: کد استاد الزامی است")
                continue

            is_internship = is_internship_or_project(assign_data)

            if not is_internship:
                if day is None or not start or not end:
                    errors.append(f"ردیف {idx + 1}: روز، ساعت شروع و پایان برای دروس عادی الزامی است")
                    continue

            from app.models.instructor import Instructor
            instructor = self.db.query(Instructor).filter(Instructor.code == instructor_code).first()
            if not instructor:
                errors.append(f"ردیف {idx + 1}: استاد با کد {instructor_code} یافت نشد")
                continue

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