from sqlalchemy import Column, Integer, String, ForeignKey, Boolean, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime
from app.core.database import Base

class VotePoll(Base):
    __tablename__ = "vote_polls"

    id = Column(Integer, primary_key=True, index=True)
    course_id = Column(Integer, ForeignKey("unique_courses.id"), nullable=False)
    term = Column(String(20), nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # ===== این رابطه را دقیقاً به همین شکل نگه دارید =====
    course = relationship("UniqueCourse", back_populates="vote_polls")