# backend/check_term_courses.py
from app.core.database import SessionLocal
from app.models.term_course import TermCourse
from sqlalchemy import func


def check_term_courses():
    db = SessionLocal()

    print("=" * 60)
    print("📊 بررسی دروس ترمیک (TermCourse)")
    print("=" * 60)

    total = db.query(TermCourse).count()
    print(f"\n📌 تعداد کل دروس ترمیک: {total}")

    # توزیع بر اساس مقطع
    levels = db.query(TermCourse.level, func.count(TermCourse.id)).group_by(TermCourse.level).all()
    print("\n📌 توزیع بر اساس مقطع:")
    for level, count in levels:
        print(f"  - {level}: {count} درس")

    # توزیع بر اساس ترم
    terms = db.query(TermCourse.term, func.count(TermCourse.id)).group_by(TermCourse.term).all()
    print("\n📌 توزیع بر اساس ترم:")
    # مرتب‌سازی بر اساس شماره ترم
    term_order = {
        "ترم یک": 1, "ترم دو": 2, "ترم سه": 3, "ترم چهار": 4,
        "ترم پنج": 5, "ترم شش": 6, "ترم هفت": 7, "ترم هشت": 8,
        "ترم اول": 1, "ترم دوم": 2, "ترم سوم": 3, "ترم چهارم": 4,
        "ترم پنجم": 5, "ترم ششم": 6, "ترم هفتم": 7, "ترم هشتم": 8
    }
    sorted_terms = sorted(terms, key=lambda x: term_order.get(x[0], 99))
    for term, count in sorted_terms:
        print(f"  - {term}: {count} درس")

    # بررسی دروس با unique_course_code معتبر
    valid_code = db.query(TermCourse).filter(TermCourse.unique_course_code != "یافت نشد").count()
    print(f"\n📌 دروس با کد یکتا معتبر: {valid_code}")
    invalid_code = total - valid_code
    print(f"📌 دروس با کد یکتا نامعتبر ('یافت نشد'): {invalid_code}")

    # بررسی دروس با پیش‌نیاز
    with_prereq = db.query(TermCourse).filter(TermCourse.prerequisite_row_codes.isnot(None)).count()
    print(f"\n📌 دروس دارای پیش‌نیاز: {with_prereq}")

    # بررسی دروس با هم‌نیاز
    with_coreq = db.query(TermCourse).filter(TermCourse.corequisite_row_codes.isnot(None)).count()
    print(f"📌 دروس دارای هم‌نیاز: {with_coreq}")

    # برای هر مقطع، لیست ترم‌های موجود
    print("\n📌 جزئیات هر مقطع:")
    for level, _ in levels:
        print(f"\n  مقطع: {level}")
        terms_for_level = db.query(TermCourse.term, func.count(TermCourse.id)).filter(
            TermCourse.level == level
        ).group_by(TermCourse.term).all()
        sorted_level_terms = sorted(terms_for_level, key=lambda x: term_order.get(x[0], 99))
        for term, count in sorted_level_terms:
            print(f"    - {term}: {count} درس")

    # ۲۰ درس اول از هر مقطع برای نمونه
    print("\n📌 نمونه دروس ترمیک (۱۰ درس اول هر مقطع):")
    for level, _ in levels:
        print(f"\n  مقطع: {level}")
        sample = db.query(TermCourse).filter(TermCourse.level == level).limit(10).all()
        for s in sample:
            print(f"    - {s.course_name} ({s.term}) - کد: {s.unique_course_code}")

    db.close()


if __name__ == "__main__":
    check_term_courses()