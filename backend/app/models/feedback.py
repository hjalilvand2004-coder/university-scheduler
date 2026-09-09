from sqlalchemy import Column, Integer, JSON, String, DateTime, ForeignKey
from app.core.database import Base
from datetime import datetime


class UserFeedback(Base):
    __tablename__ = "user_feedback"

    id = Column(Integer, primary_key=True, index=True)
    schedule_version_id = Column(Integer, ForeignKey("schedule_versions.id"), nullable=True)
    ratings = Column(JSON, nullable=False)  # {'instructor': 4, 'time': 5, ...}
    comment = Column(String, nullable=True)
    submitted_at = Column(DateTime, default=datetime.utcnow)