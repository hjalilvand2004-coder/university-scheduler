# app/services/schedule/internship_assigner.py
# تخصیص استاد به دروس کارآموزی/پروژه (مرحله ۶).
# این مرحله وابسته به زمان‌بندی (اسلات‌ها) نیست و صرفاً استاد مناسب را به درس متصل می‌کند.

import logging
from typing import List, Dict, Tuple

from app.utils.helpers import normalize_code
from app.services.workflow_helpers import calculate_final_score

logger = logging.getLogger(__name__)

class InternshipAssigner:
    @staticmethod
    def assign_internships(
            internship_courses: List[Dict],
            teaching_prefs: Dict,
            instructor_data: Dict
    ) -> Tuple[List[Dict], List[Dict]]:
        """
        تخصیص استاد به دروس کارآموزی/پروژه.

        Args:
            internship_courses: لیست دروس کارآموزی/پروژه (هر کدام شامل unique_code, group_number, ...)
            teaching_prefs: ترجیحات تدریس { course_code: [instructor_code1, ...] }
            instructor_data: اطلاعات اساتید شامل names, max_units, ...

        Returns:
            (assigned, unassigned): لیست دروس تخصیص‌یافته و تخصیص‌نیافته
        """
        assigned = []
        unassigned = []

        for course in internship_courses:
            course_code = normalize_code(course.get("unique_code", ""))
            preferred_instructors = teaching_prefs.get(course_code, [])

            if not preferred_instructors:
                logger.warning(
                    f"⚠️ کارآموزی/پروژه '{course.get('course_name')}' گروه {course.get('group_number')} - "
                    f"هیچ استاد واجدشرایطی یافت نشد"
                )
                course["instructor_code"] = None
                course["instructor_name"] = None
                course["final_score"] = 0
                course["manual_required"] = True
                course["unassigned_reason"] = "هیچ استاد واجد شرطی برای درس کارآموزی/پروژه ثبت نشده است"
                unassigned.append(course)
                continue

            # انتخاب اولین استاد اولویت‌دار (بر اساس ترتیب در teaching_prefs)
            inst_code = preferred_instructors[0]
            inst_name = instructor_data.get('names', {}).get(inst_code, inst_code)

            # تخصیص استاد به درس (بدون زمان‌بندی)
            course["instructor_code"] = inst_code
            course["instructor_name"] = inst_name
            course["day"] = None
            course["start"] = None
            course["end"] = None
            course["final_score"] = calculate_final_score(course)
            course["manual_required"] = False
            assigned.append(course)

            logger.info(
                f"✅ کارآموزی/پروژه '{course.get('course_name')}' گروه {course.get('group_number')} "
                f"→ استاد {inst_name} (کد {inst_code})"
            )

        logger.info(
            f"📊 تخصیص کارآموزی/پروژه: {len(assigned)} تخصیص‌یافته، {len(unassigned)} تخصیص‌نیافته"
        )
        return assigned, unassigned