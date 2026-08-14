# app/services/schedule/course_scorer.py
# امتیازدهی و اولویت‌بندی دروس (مرحله ۳)
# برای تیت گیت اپ
from collections import defaultdict
from typing import List, Dict

class CourseScorer:
    @staticmethod
    def score_and_sort(courses: List[Dict]) -> List[Dict]:
        if not courses:
            return []

        course_count = defaultdict(int)
        for c in courses:
            code = c.get("unique_code")
            if code:
                course_count[code] += 1

        scored = []
        for course in courses:
            code = course.get("unique_code")
            score = 0
            components = {}

            if course.get("is_prerequisite", False):
                score += 10
                components["prerequisite"] = 10

            term_number = course.get("term_number", 1)
            term = course.get("term", "").lower()
            is_current = False
            if "مهر" in term and term_number % 2 == 1:
                is_current = True
            elif "بهمن" in term and term_number % 2 == 0:
                is_current = True
            elif not term:
                if term_number % 2 == 1:
                    is_current = True

            if is_current:
                score += 5
                components["current_term"] = 5

            if course.get("student_demand", 0) > 0:
                score += 3
                components["demand"] = 3

            units = course.get("units", 2)
            if units == 3:
                score += 3
                components["units"] = 3
            elif units == 2:
                score += 2
                components["units"] = 2
            elif units == 1:
                score += 1
                components["units"] = 1
            else:
                components["units"] = 0

            total_count = course_count.get(code, 1)
            repeat_penalty = (total_count - 1) * 2
            if repeat_penalty > 0:
                score -= repeat_penalty
                components["repeat_penalty"] = -repeat_penalty

            course["priority_score"] = score
            course["score_components"] = components
            scored.append(course)

        scored.sort(key=lambda x: x.get("priority_score", 0), reverse=True)
        return scored