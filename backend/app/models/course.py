from sqlalchemy import Column, Integer, String, Boolean, Float
from app.core.database import Base

class UniqueCourse(Base):
    __tablename__ = "unique_courses"
    id = Column(Integer, primary_key=True, index=True)
    code = Column(String, unique=True, index=True)
    title = Column(String)
    status = Column(String, default="active")
    group = Column(String)
    estimated_capacity = Column(Integer, default=0)  # ← فیلد جدید

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