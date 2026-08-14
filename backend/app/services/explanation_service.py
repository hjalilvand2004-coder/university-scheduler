from app.schemas.course import Course


def explain_scheduled_class(item: dict, courses: list[Course]) -> list[str]:
    course = next(
        (course for course in courses if course.id == item["course_id"]),
        None,
    )

    if not course:
        return []

    explanations = []

    if course.chart_required:
        explanations.append("این درس در چارت آموزشی الزامی است")

    if course.graduation_critical:
        explanations.append("این درس برای فارغ‌التحصیلی اهمیت بالایی دارد")

    if course.bottleneck:
        explanations.append(
            "این درس گلوگاهی است و عدم ارائه آن می‌تواند مسیر تحصیلی دانشجویان را مسدود کند"
        )

    if course.direct_requests:
        explanations.append(
            f"{course.direct_requests} درخواست مستقیم برای ارائه درس ثبت شده است"
        )

    explanations.append(
        f"تقاضای پیش‌بینی‌شده برای این درس {item['predicted_students']} نفر است"
    )

    explanations.append(
        f"استاد {item['instructor_name']} بر اساس صلاحیت تدریس به این درس تخصیص داده شد"
    )

    explanations.append(
        f"کلاس {item['room_name']} با توجه به ظرفیت و نوع درس انتخاب شد"
    )

    return explanations