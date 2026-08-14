import math

from app.schemas.course import Course


def predict_demand(course: Course) -> int:
    """
    پیش‌بینی ساده تقاضای درس.

    در نسخه اولیه:
    - ۷۰ درصد تقاضای تاریخی
    - ۱۵۰ درصد درخواست مستقیم دانشجویان

    در نسخه‌های بعدی می‌توان این تابع را با
    مدل یادگیری ماشین جایگزین کرد.
    """

    historical_part = (
        course.historical_demand * 0.7
    )

    direct_request_part = (
        course.direct_requests * 1.5
    )

    predicted_demand = (
        historical_part +
        direct_request_part
    )

    return max(
        1,
        round(predicted_demand),
    )


def calculate_required_groups(
    predicted_students: int,
    room_capacity: int,
    max_groups: int = 3,
) -> int:
    """
    محاسبه تعداد گروه لازم.

    مثال:

    predicted_students = ۶۰
    room_capacity = ۳۰

    نتیجه:
    required_groups = ۲
    """

    if predicted_students <= 0:
        return 1

    if room_capacity <= 0:
        return max_groups

    required_groups = math.ceil(
        predicted_students / room_capacity
    )

    return min(
        max(1, required_groups),
        max_groups,
    )