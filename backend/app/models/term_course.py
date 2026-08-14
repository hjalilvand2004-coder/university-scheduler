from sqlalchemy import Column, Integer, String, Text
from app.core.database import Base

class TermCourse(Base):
    __tablename__ = "term_courses"

    id = Column(Integer, primary_key=True, index=True)
    level = Column(String(100))               # مقطع ارائه (مثلاً "پیوسته 1394")
    term = Column(String(50))                 # ترم (مثلاً "ترم یک")
    row_number = Column(Integer)              # ردیف
    course_name = Column(String(200))         # نام درس
    units = Column(Integer)                   # واحد
    course_type = Column(String(50))          # نوع درس (اصلی، پایه، عمومی)
    approximate_term = Column(Integer)        # ترم تقریبی (عدد)
    description = Column(Text)                # توضیح (پیش‌نیازها و ...)
    prerequisite_row_codes = Column(String(200))  # کد ردیف پیش‌نیازها (مثل "1,2")
    corequisite_row_codes = Column(String(200))   # کد ردیف هم‌نیازها
    unique_course_code = Column(String(50))   # کد درس یکتا
    unique_course_name = Column(String(200))  # نام درس یکتا
    year_identified = Column(String(20))      # سال شناسایی