from sqlalchemy import Column, Integer, String, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime
from app.core.database import Base


class CourseVote(Base):
    __tablename__ = "course_votes"

    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("students.id"), nullable=False)
    course_id = Column(Integer, ForeignKey("unique_courses.id"), nullable=False)  # تغییر به unique_courses
    vote_type = Column(String(20), nullable=False)  # "like" یا "request"
    term = Column(String(20), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    student = relationship("Student", back_populates="votes")
    # در صورت نیاز به رابطه با UniqueCourse، آن را فعال کنید (اگر در UniqueCourse تعریف شده باشد)
    # course = relationship("UniqueCourse", back_populates="votes")