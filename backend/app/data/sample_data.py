from app.schemas.course import (
    Course,
    CourseType,
    Instructor,
    Room,
    TimeSlot,
)


def sample_courses():
    return [
        Course(
            id=1,
            code="CS101",
            title="مبانی کامپیوتر و برنامه‌سازی",
            chart_term=1,
            course_type=CourseType.THEORY,
            cohorts=["CS-1403-1"],
            credits=3,
            chart_required=True,
            graduation_critical=True,
            bottleneck=True,
            historical_demand=38,
            direct_requests=12,
        ),
        Course(
            id=2,
            code="MATH101",
            title="ریاضی عمومی ۱",
            chart_term=1,
            course_type=CourseType.THEORY,
            cohorts=["CS-1403-1"],
            credits=3,
            chart_required=True,
            graduation_critical=True,
            bottleneck=True,
            historical_demand=42,
            direct_requests=15,
        ),
        Course(
            id=3,
            code="CS201",
            title="ساختمان داده",
            chart_term=3,
            course_type=CourseType.THEORY,
            cohorts=["CS-1403-3"],
            prerequisites=[1],
            chart_required=True,
            graduation_critical=True,
            bottleneck=True,
            historical_demand=31,
            direct_requests=14,
        ),
        Course(
            id=4,
            code="CS301",
            title="سیستم‌عامل",
            chart_term=5,
            course_type=CourseType.THEORY,
            cohorts=["CS-1403-5"],
            prerequisites=[3],
            chart_required=True,
            bottleneck=True,
            historical_demand=27,
            direct_requests=9,
        ),
        Course(
            id=5,
            code="CS302L",
            title="آزمایشگاه سیستم‌عامل",
            chart_term=5,
            course_type=CourseType.LAB,
            cohorts=["CS-1403-5"],
            prerequisites=[4],
            corequisites=[4],
            chart_required=True,
            historical_demand=20,
            direct_requests=12,
        ),
    ]


def sample_instructors():
    return [
        Instructor(
            id=1,
            name="دکتر احمدی",
            qualified_course_ids=[1, 3],
            preferred_days=[0, 2],
            preferred_slots=[0, 1, 2],
        ),
        Instructor(
            id=2,
            name="دکتر رضایی",
            qualified_course_ids=[2, 4],
            preferred_days=[1, 3],
            preferred_slots=[1, 2, 3],
        ),
        Instructor(
            id=3,
            name="مهندس کریمی",
            qualified_course_ids=[5],
            preferred_days=[0, 2],
            preferred_slots=[2, 3],
        ),
    ]


def sample_rooms():
    return [
        Room(
            id=1,
            name="کلاس ۱۰۱",
            capacity=45,
            room_types=[CourseType.THEORY],
        ),
        Room(
            id=2,
            name="کلاس ۲۰۲",
            capacity=35,
            room_types=[CourseType.THEORY],
        ),
        Room(
            id=3,
            name="آزمایشگاه شبکه",
            capacity=25,
            room_types=[CourseType.LAB, CourseType.PRACTICAL],
        ),
    ]


def sample_slots():
    result = []
    slot_id = 1

    for day in range(5):
        for start, end in [
            ("08:00", "10:00"),
            ("10:00", "12:00"),
            ("13:00", "15:00"),
            ("15:00", "17:00"),
        ]:
            result.append({
                "id": slot_id,
                "day": day,
                "start": start,
                "end": end,
            })
            slot_id += 1

    return result