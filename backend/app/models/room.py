from sqlalchemy import Column, Integer, String, JSON
from app.core.database import Base

class Room(Base):
    __tablename__ = "rooms"
    id = Column(Integer, primary_key=True, index=True)
    row_number = Column(Integer, nullable=True)          # ردیف
    code = Column(String(50), unique=True, index=True)   # کد کلاس
    name = Column(String(100), nullable=False)           # نام کلاس
    capacity = Column(Integer, nullable=False)           # ظرفیت
    group = Column(String(100))                          # گروه
    place_type = Column(String(50))                      # نوع مکان (نظری، عملی، ...)
    # اگر نیاز به room_types دارید، می‌توانید نگه دارید
    room_types = Column(JSON, default=list)              # برای سازگاری با کدهای دیگر