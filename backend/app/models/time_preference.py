from sqlalchemy import Column, Integer, String, Boolean
from app.core.database import Base

class TimePreference(Base):
    __tablename__ = "time_preferences"

    id = Column(Integer, primary_key=True, index=True)
    day = Column(String(20))                     # روز (شنبه، یکشنبه، ...)
    cooperation_type = Column(String(50))        # نوع همکاری
    end_time = Column(String(20))                # زمان پایان
    expert_group = Column(String(100))           # گروه تخصصی
    row_number = Column(Integer)                 # ردیف
    status = Column(Boolean, default=True)      # وضعیت (True/False)
    instructor_code = Column(String(50))         # کد استاد
    instructor_name = Column(String(100))        # نام استاد
    instructor_username = Column(String(50))     # یوزرنیم استاد
    start_time = Column(String(20))              # زمان شروع
    time_group = Column(String(20))              # گروه زمانی (morning, afternoon, evening)
    priority = Column(Integer, default=0)        # ← فیلد جدید