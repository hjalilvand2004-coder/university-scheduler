from sqlalchemy import Column, Integer, String, Boolean, Float, JSON, DateTime
from sqlalchemy.sql import func
from app.core.database import Base


class UniqueCourse(Base):
    __tablename__ = "unique_courses"
    id = Column(Integer, primary_key=True, index=True)
    code = Column(String, unique=True, index=True)
    title = Column(String)
    status = Column(String, default="active")
    group = Column(String)
    estimated_capacity = Column(Integer, default=0)  # ← فیلد جدید

    # فیلدهای جدید برای معماری ترکیبی هوشمند
    historical_demand = Column(JSON, default=list)  # ذخیره داده‌های تقاضای ترم‌های گذشته
    avg_rating = Column(Float, default=0.0)  # امتیاز متوسط از کاربران
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class OfferedCourse(Base):
    __tablename__ = "offered_courses"
    id = Column(Integer, primary_key=True, index=True)
    row_number = Column(Integer)
    offered_title = Column(String)
    unique_code = Column(String)
    unique_title = Column(String)
    theoretical_hours = Column(Integer, default=0)
    practical_hours = Column(Integer, default=0)
    prerequisite = Column(String, default="")
    corequisite = Column(String, default="")
    year = Column(String)
    course_type = Column(String)
    is_active = Column(Boolean, default=True)
    type_course = Column(String)

    # فیلدهای جدید برای معماری ترکیبی هوشمند
    preferred_instructors = Column(JSON, default=list)  # لیست اساتید ترجیحی
    preferred_time_slots = Column(JSON, default=list)  # زمان‌های ترجیحی
    enrollment_count = Column(Integer, default=0)  # تعداد دانشجویان ثبت‌نام شده
    demand_prediction = Column(Integer, default=0)  # پیش‌بینی تقاضا برای ترم جاری
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())