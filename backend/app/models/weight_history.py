from sqlalchemy import Column, Integer, JSON, DateTime, String, Float
from app.core.database import Base
from datetime import datetime


class WeightHistory(Base):
    __tablename__ = "weight_history"

    id = Column(Integer, primary_key=True, index=True)
    new_weights = Column(JSON, nullable=False)
    correlations = Column(JSON, nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow)
    reason = Column(String, nullable=True)
    impact = Column(Float, default=0.0)