# app/services/schedule/course_scorer.py
# امتیازدهی و اولویت‌بندی دروس (مرحله ۳)
# با استفاده از normalize_term از slot_times برای تشخیص دقیق‌تر ترم

from collections import defaultdict
from typing import List, Dict

# وارد کردن تابع normalize_term از slot_times
from app.services.schedule.slot_times import normalize_term

class CourseScorer:
    @staticmethod
    def score_and_sort(courses: List[Dict]) -> List[Dict]:
        """
        امتیازدهی به دروس و مرتب‌سازی بر اساس اولویت.

        معیارهای امتیاز:
        - پیش‌نیاز بودن: +۱۰
        - ترم جاری: +۵ (با استفاده از normalize_term)
        - وجود تقاضای دانشجو: +۳
        - تعداد واحد: +۳ (برای ۳ واحد)، +۲ (برای ۲ واحد)، +۱ (برای ۱ واحد)
        - جریمه برای تکرار (گروه‌های تکراری): -۲ به ازای هر تکرار

        Args:
            courses: لیست درس‌ها

        Returns:
            لیست درس‌های امتیازدهی‌شده و مرتب شده
        """
        if not courses:
            return []

        # شمارش تعداد تکرار هر درس بر اساس unique_code
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

            # ۱. پیش‌نیاز بودن
            if course.get("is_prerequisite", False):
                score += 10
                components["prerequisite"] = 10

            # ۲. تشخیص ترم جاری با استفاده از normalize_term
            term_raw = course.get("term", "").strip()
            term_number = course.get("term_number", 1)  # شماره ترم (۱ یا ۲ یا ...)
            is_current = False

            if term_raw:
                try:
                    # نرمال‌سازی نام ترم
                    canonical_term = normalize_term(term_raw)
                    # بر اساس کلید استاندارد، تشخیص ترم جاری:
                    # فرض می‌کنیم ترم‌های فرد (۱، ۳، ...) معادل semester_1 (مهر) هستند
                    # و ترم‌های زوج (۲، ۴، ...) معادل semester_2 (بهمن) هستند
                    if canonical_term == "semester_1" and term_number % 2 == 1:
                        is_current = True
                    elif canonical_term == "semester_2" and term_number % 2 == 0:
                        is_current = True
                    # در صورت عدم تطابق، از منطق قبلی استفاده می‌کنیم (به عنوان fallback)
                    else:
                        # اگر ترم استاندارد با شماره ترم همخوانی نداشت،
                        # از روش قبلی (جستجوی کلمات) استفاده می‌کنیم
                        term_lower = term_raw.lower()
                        if ("مهر" in term_lower or "mehr" in term_lower) and term_number % 2 == 1:
                            is_current = True
                        elif ("بهمن" in term_lower or "bahman" in term_lower) and term_number % 2 == 0:
                            is_current = True
                        elif "تابستان" in term_lower or "summer" in term_lower:
                            # برای تابستان، می‌توانیم آن را به عنوان ترم جاری در نظر بگیریم یا نه
                            # در اینجا به صورت پیش‌فرض در نظر نمی‌گیریم
                            pass
                except ValueError:
                    # اگر normalize_term خطا داد (ترم نامعتبر)، از منطق قبلی استفاده می‌کنیم
                    term_lower = term_raw.lower()
                    if ("مهر" in term_lower or "mehr" in term_lower) and term_number % 2 == 1:
                        is_current = True
                    elif ("بهمن" in term_lower or "bahman" in term_lower) and term_number % 2 == 0:
                        is_current = True
            else:
                # اگر فیلد term خالی بود، بر اساس term_number تشخیص می‌دهیم
                if term_number % 2 == 1:
                    is_current = True

            if is_current:
                score += 5
                components["current_term"] = 5

            # ۳. وجود تقاضای دانشجو
            if course.get("student_demand", 0) > 0:
                score += 3
                components["demand"] = 3

            # ۴. تعداد واحد
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

            # ۵. جریمه برای تکرار (گروه‌های تکراری)
            total_count = course_count.get(code, 1)
            repeat_penalty = (total_count - 1) * 2
            if repeat_penalty > 0:
                score -= repeat_penalty
                components["repeat_penalty"] = -repeat_penalty

            # ذخیره امتیاز و اجزای آن در درس
            course["priority_score"] = score
            course["score_components"] = components
            scored.append(course)

        # مرتب‌سازی نزولی بر اساس امتیاز اولویت
        scored.sort(key=lambda x: x.get("priority_score", 0), reverse=True)
        return scored