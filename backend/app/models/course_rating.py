from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Text
from sqlalchemy.orm import relationship
from datetime import datetime
from app.core.database import Base


class CourseRating(Base):
    __tablename__ = "course_ratings"

    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("students.id"), nullable=False)
    schedule_id = Column(Integer, ForeignKey("scheduled_classes.id"), nullable=False)  # تغییر به scheduled_classes
    rating = Column(String(20), nullable=False)  # excellent, good, average, weak, very_weak
    comment = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    student = relationship("Student", back_populates="ratings")
    # در صورت نیاز به رابطه با ScheduledClass، آن را فعال کنید
    # schedule = relationship("ScheduledClass", back_populates="ratings")