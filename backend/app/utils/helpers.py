# app/utils/helpers.py

from typing import Dict
from .constants import DAY_NAMES
from .normalization import normalize_code, normalize_instructor_code, normalize_day
from .time_utils import time_to_minutes, slot_overlap, calculate_time_match_score

def get_day_name(day_num: int) -> str:
    return DAY_NAMES[day_num] if 0 <= day_num < 6 else str(day_num)

def is_internship_or_project(course: Dict) -> bool:
    # ایمن‌سازی برای مقادیر None
    course_type = course.get("course_type") or ""
    if course_type.lower() in ["internship", "project", "کارآموزی", "پروژه"]:
        return True
    name = course.get("course_name") or ""
    if "کارآموزی" in name or "پروژه" in name:
        return True
    return False