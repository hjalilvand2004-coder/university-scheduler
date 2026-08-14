# app/core/database.py
# تنظیمات اتصال به دیتابیس با استفاده از SQLAlchemy

import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base  # ← تغییر import برای سازگاری با SQLAlchemy 2.0

# خواندن آدرس دیتابیس از متغیر محیطی (با fallback به پیش‌فرض)
SQLALCHEMY_DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "sqlite:///./university_scheduler.db"
)

# تنظیمات موتور دیتابیس
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False} if SQLALCHEMY_DATABASE_URL.startswith("sqlite") else {},
    echo=False,                # خاموش کردن لاگ‌های SQL (برای محیط تولید)
    pool_pre_ping=True,        # بررسی سلامت اتصال قبل از استفاده
    pool_recycle=3600,         # بازیابی اتصال پس از یک ساعت
)

# کارخانهٔ جلسات (Session) برای تعامل با دیتابیس
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# کلاس پایه برای مدل‌ها (با استفاده از declarative_base جدید)
Base = declarative_base()

def get_db():
    """
    توابع وابسته (dependency) برای دریافت session دیتابیس.
    در FastAPI به‌عنوان dependency استفاده می‌شود.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()