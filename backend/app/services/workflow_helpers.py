import re
from typing import List, Dict, Any

# لیست دروس گلوگاهی
BOTTLENECK_COURSES = {
    "ساختمان داده", "معماری کامپیوتر", "ریاضی عمومی ۱", "ریاضی عمومی ۲",
    "معادلات دیفرانسیل", "مدارهای منطقی", "برنامه‌سازی پیشرفته", "ریاضی گسسته",
    "سیستم‌عامل", "هوش مصنوعی", "مهندسی نرم‌افزار", "طراحی سیستم‌های دیجیتال"
}


def parse_row_codes(row_codes_str: str) -> List[int]:
    """
    تبدیل رشته‌ی کدهای ردیف (مثل '1,2' یا '21، 24') به لیست اعداد
    """
    if not row_codes_str:
        return []
    cleaned = re.sub(r'[^\d]', ' ', row_codes_str)
    return [int(x) for x in cleaned.split() if x.strip()]


def calculate_final_score(course: Dict[str, Any]) -> int:
    """
    محاسبه امتیاز نهایی بر اساس قوانین:
    - از ترمیک: ۱۰ امتیاز
    - از پیش‌نیاز: ۵ امتیاز
    - از تقاضای دانشجو: ۵ امتیاز
    - میانگین مهر: به اندازه خود عدد صحیح
    - میانگین بهمن: نصف عدد صحیح (تقسیم صحیح بر ۲)
    - انتخاب مدیر: ۱۰ امتیاز
    """
    score = 0
    if course.get("from_termic"):
        score += 10
    if course.get("from_prerequisite"):
        score += 5
    if course.get("from_student_demand"):
        score += 5
    score += course.get("avg_in_mehr", 0)
    score += course.get("avg_in_bahman", 0) // 2
    if course.get("from_manager"):
        score += 10
    return score


def is_bottleneck(course: Dict[str, Any]) -> bool:
    """بررسی گلوگاهی بودن درس"""
    name = course.get("course_name", "")
    code = course.get("unique_code", "")
    return name in BOTTLENECK_COURSES or code in BOTTLENECK_COURSES