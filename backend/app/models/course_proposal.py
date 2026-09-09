from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Text
from sqlalchemy.orm import relationship
from datetime import datetime
from app.core.database import Base


class CourseProposal(Base):
    __tablename__ = "course_proposals"

    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("students.id"), nullable=False)
    term = Column(String(20), nullable=False)
    course_ids = Column(Text, nullable=False)  # ذخیره به‌صورت JSON
    description = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    status = Column(String(20), default="pending")  # pending, approved, rejected

    student = relationship("Student", back_populates="proposals")