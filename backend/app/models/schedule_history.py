from sqlalchemy import Column, Integer, String, DateTime, Float
from app.core.database import Base
from datetime import datetime

class ScheduleHistory(Base):
    __tablename__ = "schedule_history"

    id = Column(Integer, primary_key=True, index=True)
    semester = Column(String(50))                     # نیمسال ارائه
    course_name = Column(String(200))                 # نام درس
    faculty_code = Column(String(50))                 # کد دانشکده استخراج‌شده
    faculty_name_clean = Column(String(200))          # نام دانشکده تمیز
    department_code = Column(String(50))              # کد گروه آموزشی
    department_name_clean = Column(String(200))       # نام گروه آموزشی تمیز
    instructor_code = Column(String(50))              # کد استاد مرجع
    instructor_name_clean = Column(String(200))       # نام استاد تمیز
    max_capacity = Column(Integer)                    # حداکثر ظرفیت
    level = Column(String(50))                        # مقطع ارائه درس
    course_type = Column(String(50))                  # نوع درس
    day = Column(String(20))                          # روز کلاس
    start_time = Column(String(20))                   # ساعت شروع کلاس
    end_time = Column(String(20))                     # ساعت پایان کلاس
    exam_date = Column(String(20))                    # تاریخ امتحان
    exam_start_time = Column(String(20))              # ساعت شروع امتحان
    exam_end_time = Column(String(20))                # ساعت پایان امتحان
    ref_course_title = Column(String(200))            # عنوان درس مرجع
    ref_unique_course_code = Column(String(50))       # کد درس یکتا مرجع
    ref_unique_course_title = Column(String(200))     # عنوان درس یکتا مرجع
    class_code = Column(String(50))                   # کد کلاس استخراج‌شده
    class_name = Column(String(200))                  # نام کلاس
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)