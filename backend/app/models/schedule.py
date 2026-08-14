from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Float, Text
from sqlalchemy.sql import func
from app.core.database import Base


class ScheduledClass(Base):
    __tablename__ = "scheduled_classes"

    id = Column(Integer, primary_key=True, index=True)

    # اطلاعات درس
    course_id = Column(Integer, ForeignKey("offered_courses.id"), nullable=False)
    course_code = Column(String(50))
    course_title = Column(String(200))
    group_number = Column(Integer)

    # اطلاعات استاد
    instructor_id = Column(Integer, ForeignKey("instructors.id"))
    instructor_name = Column(String(100))

    # اطلاعات کلاس
    room_id = Column(Integer, ForeignKey("rooms.id"))
    room_name = Column(String(100))
    room_capacity = Column(Integer)

    # اطلاعات زمان
    slot_id = Column(Integer)
    day = Column(Integer)  # 0=شنبه تا 4=چهارشنبه
    start_time = Column(String(10))
    end_time = Column(String(10))

    # اطلاعات آماری
    predicted_students = Column(Integer)
    students_per_group = Column(Integer)
    course_type = Column(String(50))
    cohorts = Column(Text)  # به صورت JSON یا CSV ذخیره شود

    # اطلاعات برنامه
    semester = Column(String(20))  # mehr / bahman
    year = Column(String(20))
    term_code = Column(String(20))

    # امتیاز و توضیحات
    score = Column(Float, default=0)
    explanation = Column(Text)  # JSON یا متن

    # زمان ایجاد
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, onupdate=func.now())

    # شناسه سناریو (برای تشخیص سناریوهای مختلف)
    scenario_id = Column(Integer, default=1)