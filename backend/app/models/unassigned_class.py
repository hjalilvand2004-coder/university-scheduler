from sqlalchemy import Column, Integer, String, ForeignKey, Float, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime
from app.core.database import Base

class UnassignedClass(Base):
    __tablename__ = "unassigned_classes"

    id = Column(Integer, primary_key=True, index=True)
    basket_id = Column(Integer, ForeignKey("baskets.id", ondelete="CASCADE"), nullable=True)
    scenario_id = Column(Integer, ForeignKey("schedule_workflows.id", ondelete="CASCADE"), nullable=True)

    course_code = Column(String(50), nullable=False)
    course_title = Column(String(200), nullable=False)
    group_number = Column(Integer, nullable=False, default=1)
    level = Column(String(50), nullable=True)
    term = Column(String(50), nullable=True)
    units = Column(Integer, nullable=True)
    estimated_capacity = Column(Integer, nullable=True, default=0)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # روابط (اختیاری)
    basket = relationship("Basket", backref="unassigned_classes")
    workflow = relationship("ScheduleWorkflow", backref="unassigned_classes")

    def to_dict(self):
        return {
            "id": self.id,
            "basket_id": self.basket_id,
            "scenario_id": self.scenario_id,
            "course_code": self.course_code,
            "course_title": self.course_title,
            "group_number": self.group_number,
            "level": self.level,
            "term": self.term,
            "units": self.units,
            "estimated_capacity": self.estimated_capacity,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }