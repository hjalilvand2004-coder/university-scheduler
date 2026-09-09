# app/models/student.py
from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime
from app.core.database import Base


class Student(Base):
    __tablename__ = "students"

    id = Column(Integer, primary_key=True, index=True)
    first_name = Column(String(50), nullable=False)
    last_name = Column(String(50), nullable=False)
    student_code = Column(String(20), unique=True, index=True, nullable=False)
    email = Column(String(100), unique=True, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # روابط با مدل‌های جدید
    proposals = relationship("CourseProposal", back_populates="student")
    votes = relationship("CourseVote", back_populates="student")
    ratings = relationship("CourseRating", back_populates="student")