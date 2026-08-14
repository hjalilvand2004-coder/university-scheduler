# app/services/schedule/data_preparer.py
# آماده‌سازی داده‌های ورودی (مرحله ۱).
import re
from typing import List, Dict

from app.utils.helpers import normalize_code

class DataPreparer:
    @staticmethod
    def prepare(basket: List[Dict]) -> List[Dict]:
        prepared = []
        for course in basket:
            new_course = course.copy()
            if "unique_code" in new_course:
                new_course["unique_code"] = normalize_code(new_course["unique_code"])
            if "term_number" not in new_course:
                term_str = new_course.get("term", "")
                match = re.search(r'\d+', term_str)
                new_course["term_number"] = int(match.group()) if match else 1
            if "group_number" not in new_course:
                new_course["group_number"] = 1
            if "is_prerequisite" not in new_course:
                new_course["is_prerequisite"] = False
            if "student_demand" not in new_course:
                new_course["student_demand"] = 0
            new_course["unassigned_reason"] = None
            prepared.append(new_course)
        return prepared