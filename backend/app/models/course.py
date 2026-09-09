from sqlalchemy import Column, Integer, String, Boolean, Float, JSON, DateTime
from sqlalchemy.orm import relationship  # ← ایمپورت ضروری برای رابطه
from sqlalchemy.sql import func
from app.core.database import Base


class UniqueCourse(Base):
    __tablename__ = "unique_courses"
    id = Column(Integer, primary_key=True, index=True)
    code = Column(String, unique=True, index=True)
    title = Column(String)
    status = Column(String, default="active")
    group = Column(String)
    estimated_capacity = Column(Integer, default=0)

    # فیلدهای جدید برای معماری ترکیبی هوشمند
    historical_demand = Column(JSON, default=list)
    avg_rating = Column(Float, default=0.0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # ===== رابطه با VotePoll (برای رفع خطای Mapper) =====
    vote_polls = relationship("VotePoll", back_populates="course")


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
    preferred_instructors = Column(JSON, default=list)
    preferred_time_slots = Column(JSON, default=list)
    enrollment_count = Column(Integer, default=0)
    demand_prediction = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())