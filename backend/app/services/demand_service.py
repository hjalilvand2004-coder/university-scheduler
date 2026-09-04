# app/services/demand_service.py

import math
from typing import Optional

from app.schemas.course import Course


def predict_demand(course: Course) -> int:
    """
    پیش‌بینی ساده تقاضای درس بر اساس داده‌های تاریخی و درخواست‌های مستقیم.

    فرمول:
        predicted_demand = (historical_demand * 0.7) + (direct_requests * 1.5)

    در نسخه اولیه از یک مدل خطی ساده استفاده می‌شود.
    در نسخه‌های بعدی می‌توان این تابع را با مدل یادگیری ماشین جایگزین کرد.

    Args:
        course: شیء Course شامل historical_demand و direct_requests

    Returns:
        تعداد دانشجویان پیش‌بینی‌شده (حداقل ۱)
    """
    historical_part = course.historical_demand * 0.7
    direct_request_part = course.direct_requests * 1.5

    predicted_demand = historical_part + direct_request_part

    return max(1, round(predicted_demand))


def calculate_required_groups(
    predicted_students: int,
    room_capacity: int,
    max_groups: int = 3,
) -> int:
    """
    محاسبه تعداد گروه‌های لازم بر اساس تعداد دانشجویان پیش‌بینی‌شده و ظرفیت اتاق.

    فرمول:
        required_groups = ceil(predicted_students / room_capacity)

    Args:
        predicted_students: تعداد دانشجویان پیش‌بینی‌شده
        room_capacity: ظرفیت هر اتاق (تعداد صندلی)
        max_groups: حداکثر تعداد گروه مجاز (پیش‌فرض ۳)

    Returns:
        تعداد گروه‌های مورد نیاز (بین ۱ تا max_groups)

    مثال:
        >>> calculate_required_groups(60, 30)
        2
        >>> calculate_required_groups(100, 30, 4)
        4
    """
    if predicted_students <= 0:
        return 1

    if room_capacity <= 0:
        return max_groups

    required_groups = math.ceil(predicted_students / room_capacity)

    return min(max(1, required_groups), max_groups)