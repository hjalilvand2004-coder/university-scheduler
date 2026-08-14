# app/utils/time_utils.py
# توابع مرتبط با زمان، اسلات‌ها و محاسبه امتیاز تطابق.
from typing import List, Tuple
from .constants import TWO_UNIT_SLOTS, THREE_UNIT_SLOTS

def time_to_minutes(t: str) -> int:
    """
    تبدیل زمان رشته‌ای به دقیقه از نیمه‌شب
    """
    try:
        h, m = map(int, t.split(':'))
        return h * 60 + m
    except:
        return 0

def slot_overlap(s1_start: str, s1_end: str, s2_start: str, s2_end: str) -> bool:
    """
    بررسی تداخل دو بازه زمانی
    """
    return time_to_minutes(s1_start) < time_to_minutes(s2_end) and time_to_minutes(s2_start) < time_to_minutes(s1_end)

def get_slots_for_units(units: int) -> List[Tuple[str, str]]:
    """
    برگرداندن لیست اسلات‌های ممکن بر اساس تعداد واحد
    """
    return THREE_UNIT_SLOTS if units == 3 else TWO_UNIT_SLOTS

def calculate_time_match_score(
        slot_start: str,
        slot_end: str,
        pref_start: str,
        pref_end: str,
        priority: int,
        max_tolerance_minutes: int = 90
) -> float:
    """
    محاسبه امتیاز تطابق یک اسلات با بازه مطلوب استاد
    """
    slot_mid = (time_to_minutes(slot_start) + time_to_minutes(slot_end)) / 2
    pref_mid = (time_to_minutes(pref_start) + time_to_minutes(pref_end)) / 2
    distance = abs(slot_mid - pref_mid)
    if distance > max_tolerance_minutes:
        return 0.0
    score = 100.0 * (1 - (distance / max_tolerance_minutes))
    priority_factor = max(0.5, 1.5 - (priority / 100.0))
    return score * priority_factor