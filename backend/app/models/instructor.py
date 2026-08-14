from sqlalchemy import Column, Integer, String
from app.core.database import Base

class Instructor(Base):
    __tablename__ = "instructors"
    id = Column(Integer, primary_key=True, index=True)
    row_number = Column(Integer)
    code = Column(String(50), unique=True, index=True)
    name = Column(String(100), nullable=False)
    username = Column(String(50), unique=True)
    group = Column(String(50))
    cooperation_type = Column(String(50))
    max_teaching_units = Column(Integer, default=0)   # ← فیلد جدید