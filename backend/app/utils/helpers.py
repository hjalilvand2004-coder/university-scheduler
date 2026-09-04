# app/utils/helpers.py

from typing import Dict

from .constants import DAY_NAMES
from .normalization import normalize_code, normalize_instructor_code
from .time_utils import time_to_minutes, slot_overlap, calculate_time_match_score

# ===== یکپارچه‌سازی با فایل مرجع slot_times =====
# برای رفع خطاهای ImportError، normalize_day و DAY_MAP را از slot_times وارد می‌کنیم
# و مجدداً صادر می‌کنیم تا سایر ماژول‌ها بتوانند از helpers import کنند.
from app.services.schedule.slot_times import normalize_day, DAY_MAP

# ============================================================
# توابع اصلی کمکی
# ============================================================

def get_day_name(day_num: int) -> str:
    """
    دریافت نام فارسی روز بر اساس شماره (۰ تا ۵ برای شنبه تا پنجشنبه).
    """
    return DAY_NAMES[day_num] if 0 <= day_num < 6 else str(day_num)


def is_internship_or_project(course: Dict) -> bool:
    """
    تشخیص اینکه آیا درس از نوع کارآموزی یا پروژه است.
    """
    course_type = course.get("course_type") or ""
    if course_type.lower() in ["internship", "project", "کارآموزی", "پروژه"]:
        return True
    name = course.get("course_name") or ""
    if "کارآموزی" in name or "پروژه" in name:
        return True
    return False