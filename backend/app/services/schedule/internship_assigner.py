# app/services/schedule/internship_assigner.py
# تخصیص استاد به دروس کارآموزی/پروژه (مرحله ۶).
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
        assigned = []
        unassigned = []

        for course in internship_courses:
            course_code = normalize_code(course.get("unique_code", ""))
            preferred_instructors = teaching_prefs.get(course_code, [])

            if not preferred_instructors:
                logger.warning(f"⚠️ کارآموزی/پروژه '{course.get('course_name')}' - هیچ استاد واجدشرایطی یافت نشد")
                course["instructor_code"] = None
                course["instructor_name"] = None
                course["final_score"] = 0
                course["manual_required"] = True
                course["unassigned_reason"] = "هیچ استاد واجد شرطی برای درس کارآموزی/پروژه ثبت نشده است"
                unassigned.append(course)
                continue

            inst_code = preferred_instructors[0]
            inst_name = instructor_data['names'].get(inst_code, inst_code)

            course["instructor_code"] = inst_code
            course["instructor_name"] = inst_name
            course["day"] = None
            course["start"] = None
            course["end"] = None
            course["final_score"] = calculate_final_score(course)
            course["manual_required"] = False
            assigned.append(course)
            logger.info(f"✅ کارآموزی/پروژه '{course.get('course_name')}' گروه {course.get('group_number')} → استاد {inst_name}")

        return assigned, unassigned