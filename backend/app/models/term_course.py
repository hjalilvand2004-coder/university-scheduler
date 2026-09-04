from sqlalchemy import Column, Integer, String, Text
from app.core.database import Base

class TermCourse(Base):
    __tablename__ = "term_courses"

    id = Column(Integer, primary_key=True, index=True)
    level = Column(String(100))
    term = Column(String(50))
    row_number = Column(Integer)
    course_name = Column(String(200))
    units = Column(Integer)
    course_type = Column(String(50))
    approximate_term = Column(Integer)
    description = Column(Text)
    prerequisite_row_codes = Column(String(200))
    corequisite_row_codes = Column(String(200))
    unique_course_code = Column(String(50))
    unique_course_name = Column(String(200))
    year_identified = Column(String(20))
    # ===== فیلد جدید =====
    capacity = Column(Integer, default=0)  # ظرفیت درس