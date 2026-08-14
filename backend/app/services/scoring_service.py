# app/services/scoring_service.py
from typing import Union, List, Tuple, Dict
from app.schemas.course import Course, Semester

BOTTLENECK_COURSES = {
    "ساختمان داده",
    "معماری کامپیوتر",
    "ریاضی عمومی ۱",
    "ریاضی عمومی ۲",
    "معادلات دیفرانسیل",
    "مدارهای منطقی",
    "برنامه‌سازی پیشرفته",
    "ریاضی گسسته",
}


def _extract_attribute(obj: Union[Course, dict], key: str, default=None):
    """
    دریافت مقدار یک ویژگی از شیء یا دیکشنری
    """
    if isinstance(obj, Course):
        return getattr(obj, key, default)
    else:
        return obj.get(key, default)


def calculate_course_score(
    course: Union[Course, dict],
    semester: Semester
) -> Tuple[float, List[str]]:
    """
    محاسبه امتیاز یک درس بر اساس عوامل مختلف.

    Args:
        course: شیء Course یا دیکشنری حاوی اطلاعات درس
        semester: نیمسال (مهر یا بهمن)

    Returns:
        (امتیاز, لیست دلایل)
    """
    score = 0
    reasons = []

    # استخراج مقادیر با تابع کمکی (هم برای شیء و هم دیکشنری)
    active = _extract_attribute(course, "active", False)
    chart_required = _extract_attribute(course, "chart_required", False)
    graduation_critical = _extract_attribute(course, "graduation_critical", False)
    bottleneck = _extract_attribute(course, "bottleneck", False)
    title = _extract_attribute(course, "title", "")
    historical_demand = _extract_attribute(course, "historical_demand", 0.0)
    direct_requests = _extract_attribute(course, "direct_requests", 0)
    chart_term = _extract_attribute(course, "chart_term", 1)

    # فعال بودن درس
    if active:
        score += 10
        reasons.append("درس فعال است")

    # الزام در چارت
    if chart_required:
        score += 20
        reasons.append("درس در چارت آموزشی الزامی است")

    # اهمیت فارغ‌التحصیلی
    if graduation_critical:
        score += 20
        reasons.append("درس برای فارغ‌التحصیلی اهمیت دارد")

    # درس گلوگاهی
    if bottleneck or title in BOTTLENECK_COURSES:
        score += 25
        reasons.append("درس گلوگاهی است و عدم ارائه آن مسیر تحصیلی را محدود می‌کند")

    # تقاضای تاریخی
    score += min(historical_demand * 0.5, 20)
    if historical_demand > 0:
        reasons.append(f"تقاضای تاریخی برابر با {historical_demand:.0f} نفر است")

    # درخواست مستقیم دانشجویان
    score += min(direct_requests * 0.8, 15)
    if direct_requests > 0:
        reasons.append(f"{direct_requests} درخواست مستقیم برای ارائه درس ثبت شده است")

    # سیاست زوج و فرد
    if semester == Semester.MEHR:
        if chart_term % 2 == 1:
            score += 15
            reasons.append("درس متعلق به ترم فرد و مناسب‌تر برای مهر است")
    else:
        if chart_term % 2 == 0:
            score += 15
            reasons.append("درس متعلق به ترم زوج و مناسب‌تر برای بهمن است")

    # درخواست عبور از حد نصاب (فقط در صورتی که درس چارتی نباشد)
    if direct_requests >= 10 and not chart_required:
        score += 10
        reasons.append("تعداد درخواست‌ها از حدنصاب عبور کرده است")

    return round(score, 2), reasons


def rank_courses(
    courses: List[Union[Course, dict]],
    semester: Semester
) -> List[Dict]:
    """
    رتبه‌بندی دروس بر اساس امتیاز

    Args:
        courses: لیست اشیاء Course یا دیکشنری
        semester: نیمسال

    Returns:
        لیست دیکشنری‌های مرتب‌شده شامل اطلاعات درس و امتیاز
    """
    result = []

    for course in courses:
        score, reasons = calculate_course_score(course, semester)

        # استخراج شناسه، کد و عنوان (هم برای شیء و هم دیکشنری)
        if isinstance(course, Course):
            course_id = course.id
            course_code = course.code
            course_title = course.title
        else:
            course_id = course.get("id")
            course_code = course.get("code", "")
            course_title = course.get("title", "")

        result.append({
            "course_id": course_id,
            "course_code": course_code,
            "course_title": course_title,
            "score": score,
            "reasons": reasons,
        })

    return sorted(result, key=lambda x: x["score"], reverse=True)