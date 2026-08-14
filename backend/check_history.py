# backend/check_history.py
from app.core.database import SessionLocal
from app.models.schedule_history import ScheduleHistory
from sqlalchemy import func


def check_history():
    db = SessionLocal()

    print("=" * 60)
    print("📊 بررسی سوابق برنامه‌ریزی (ScheduleHistory)")
    print("=" * 60)

    # 1. تعداد کل رکوردها
    total_records = db.query(ScheduleHistory).count()
    print(f"\n📌 تعداد کل رکوردها: {total_records}")

    # 2. تعداد دروس منحصر‌به‌فرد
    unique_courses = db.query(ScheduleHistory.course_name).distinct().count()
    print(f"📌 تعداد دروس منحصر‌به‌فرد: {unique_courses}")

    # 3. توزیع بر اساس ترم (نیمسال)
    semester_counts = db.query(
        ScheduleHistory.semester,
        func.count(ScheduleHistory.id).label('count')
    ).group_by(ScheduleHistory.semester).all()

    print("\n📌 توزیع بر اساس ترم:")
    for item in semester_counts:
        print(f"  - {item.semester}: {item.count} رکورد")

    # 4. ۲۰ درس با بیشترین تکرار
    top_courses = db.query(
        ScheduleHistory.course_name,
        ScheduleHistory.ref_unique_course_code,
        func.count(ScheduleHistory.id).label('count'),
        func.avg(ScheduleHistory.max_capacity).label('avg_capacity')
    ).group_by(
        ScheduleHistory.course_name,
        ScheduleHistory.ref_unique_course_code
    ).order_by(
        func.count(ScheduleHistory.id).desc()
    ).limit(20).all()

    print("\n📌 ۲۰ درس با بیشترین تکرار در سوابق:")
    print("-" * 60)
    print(f"{'ردیف':<4} {'نام درس':<25} {'تعداد':<6} {'میانگین ظرفیت':<10}")
    print("-" * 60)
    for idx, item in enumerate(top_courses, 1):
        avg_cap = int(item.avg_capacity) if item.avg_capacity else 0
        print(f"{idx:<4} {item.course_name[:24]:<25} {item.count:<6} {avg_cap:<10}")

    # 5. بررسی توزیع بر اساس روز
    day_counts = db.query(
        ScheduleHistory.day,
        func.count(ScheduleHistory.id).label('count')
    ).group_by(ScheduleHistory.day).all()

    print("\n📌 توزیع بر اساس روز:")
    day_map = {"شنبه": 0, "یکشنبه": 1, "دوشنبه": 2, "سه‌شنبه": 3, "چهارشنبه": 4, "پنجشنبه": 5}
    reverse_day = {v: k for k, v in day_map.items()}
    for item in day_counts:
        day_name = reverse_day.get(item.day, str(item.day))
        print(f"  - {day_name}: {item.count} رکورد")

    # 6. بررسی توزیع استادان
    top_instructors = db.query(
        ScheduleHistory.instructor_name_clean,
        func.count(ScheduleHistory.id).label('count')
    ).group_by(
        ScheduleHistory.instructor_name_clean
    ).order_by(
        func.count(ScheduleHistory.id).desc()
    ).limit(10).all()

    print("\n📌 ۱۰ استاد با بیشترین سابقه تدریس:")
    for idx, item in enumerate(top_instructors, 1):
        print(f"  {idx}. {item.instructor_name_clean}: {item.count} کلاس")

    # 7. بررسی وجود `ref_unique_course_code` خالی
    empty_code = db.query(ScheduleHistory).filter(
        ScheduleHistory.ref_unique_course_code == "یافت نشد"
    ).count()
    print(f"\n📌 دروس با کد یکتا 'یافت نشد': {empty_code}")

    db.close()


if __name__ == "__main__":
    check_history()