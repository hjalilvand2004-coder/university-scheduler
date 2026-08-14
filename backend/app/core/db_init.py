# app/core/db_init.py
from app.core.database import engine, Base
from app.models import (
    UniqueCourse,
    OfferedCourse,
    Instructor,
    Room,
    ScheduledClass,          # ← اصلاح: تغییر نام به ScheduledClass
    ScheduleHistory,
    TermCourse,
    TeachingPreference,
    TimePreference
)

def init_db():
    try:
        Base.metadata.create_all(bind=engine)
        print("✅ جداول دیتابیس با موفقیت ایجاد شدند.")
        print("📋 جداول ایجاد شده:")
        for table in Base.metadata.tables.keys():
            print(f"   - {table}")
    except Exception as e:
        print(f"❌ خطا در ایجاد جداول: {e}")
        raise