# backend/check_schedule_data.py
from app.core.database import SessionLocal
from app.models import (
    UniqueCourse, OfferedCourse, Instructor, Room,
    TermCourse, TeachingPreference, TimePreference,
    ScheduleHistory
)
from sqlalchemy import func


def check_schedule_data():
    db = SessionLocal()

    print("=" * 60)
    print("📊 بررسی داده‌های مورد نیاز برای تولید برنامه")
    print("=" * 60)

    # 1. بررسی دروس ترمیک (چارت)
    term_courses = db.query(TermCourse).all()
    print(f"\n📅 دروس ترمیک (چارت): {len(term_courses)}")
    if term_courses:
        # نمایش توزیع بر اساس مقطع و ترم
        levels = db.query(TermCourse.level, func.count(TermCourse.id)).group_by(TermCourse.level).all()
        print("  توزیع بر اساس مقطع:")
        for level, count in levels:
            print(f"    - {level}: {count}")

        terms = db.query(TermCourse.term, func.count(TermCourse.id)).group_by(TermCourse.term).all()
        print("  توزیع بر اساس ترم:")
        for term, count in terms:
            print(f"    - {term}: {count}")
    else:
        print("  ⚠️ هیچ داده‌ای در جدول دروس ترمیک وجود ندارد!")

    # 2. بررسی دروس ارائه
    offered = db.query(OfferedCourse).all()
    print(f"\n📖 دروس ارائه: {len(offered)}")
    if not offered:
        print("  ⚠️ هیچ داده‌ای در جدول دروس ارائه وجود ندارد!")

    # 3. بررسی اساتید
    instructors = db.query(Instructor).all()
    print(f"\n👨‍🏫 اساتید: {len(instructors)}")
    if not instructors:
        print("  ⚠️ هیچ داده‌ای در جدول اساتید وجود ندارد!")

    # 4. بررسی اتاق‌ها
    rooms = db.query(Room).all()
    print(f"\n🏫 اتاق‌ها: {len(rooms)}")
    if not rooms:
        print("  ⚠️ هیچ داده‌ای در جدول اتاق‌ها وجود ندارد!")

    # 5. بررسی مطلوبیت‌های تدریس
    teaching_prefs = db.query(TeachingPreference).all()
    print(f"\n📋 مطلوبیت‌های تدریس: {len(teaching_prefs)}")
    if teaching_prefs:
        # نمایش اساتیدی که مطلوبیت دارند
        instructors_with_prefs = db.query(TeachingPreference.instructor_name).distinct().all()
        print(f"  اساتید دارای مطلوبیت: {len(instructors_with_prefs)}")

    # 6. بررسی مطلوبیت‌های زمان‌بندی
    time_prefs = db.query(TimePreference).all()
    print(f"\n⏰ مطلوبیت‌های زمان‌بندی: {len(time_prefs)}")
    if time_prefs:
        instructors_with_time = db.query(TimePreference.instructor_name).distinct().all()
        print(f"  اساتید دارای مطلوبیت زمان‌بندی: {len(instructors_with_time)}")

    # 7. بررسی سوابق برنامه‌ریزی (برای پیش‌بینی)
    history = db.query(ScheduleHistory).all()
    print(f"\n📜 سوابق برنامه‌ریزی: {len(history)}")
    if not history:
        print("  ⚠️ هیچ داده‌ای در جدول سوابق برنامه‌ریزی وجود ندارد!")

    print("\n" + "=" * 60)
    print("💡 جمع‌بندی:")
    print("=" * 60)

    issues = []
    if not term_courses:
        issues.append("❌ جدول دروس ترمیک خالی است - برای تولید برنامه نیاز است")
    if not offered:
        issues.append("❌ جدول دروس ارائه خالی است - برای تولید برنامه نیاز است")
    if not instructors:
        issues.append("❌ جدول اساتید خالی است - برای تولید برنامه نیاز است")
    if not rooms:
        issues.append("❌ جدول اتاق‌ها خالی است - برای تولید برنامه نیاز است")

    if issues:
        print("\n".join(issues))
        print("\n📌 لطفاً ابتدا داده‌های مورد نیاز را بارگذاری کنید.")
    else:
        print("✅ همه داده‌های مورد نیاز برای تولید برنامه وجود دارند!")

    db.close()


if __name__ == "__main__":
    check_schedule_data()