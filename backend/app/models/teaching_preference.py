from sqlalchemy import Column, Integer, String
from app.core.database import Base

class TeachingPreference(Base):
    __tablename__ = "teaching_preferences"

    id = Column(Integer, primary_key=True, index=True)
    unique_course_code = Column(String(50))      # کد یکتا درس
    course_name = Column(String(200))            # نام درس
    cooperation_type = Column(String(50))        # نوع همکاری
    expert_group = Column(String(100))           # گروه تخصصی
    row_number = Column(Integer)                 # ردیف
    instructor_code = Column(String(50))         # کد استاد
    instructor_name = Column(String(100))        # نام استاد
    instructor_username = Column(String(50))     # یوزرنیم استاد
    status = Column(String(50))                  # وضعیت (pending, approved, rejected)
    term_code = Column(String(20))               # کد ترم تحصیلی