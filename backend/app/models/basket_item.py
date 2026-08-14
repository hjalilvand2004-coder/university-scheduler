from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from app.core.database import Base

class BasketItem(Base):
    __tablename__ = "basket_items"

    id = Column(Integer, primary_key=True, index=True)
    basket_id = Column(Integer, ForeignKey("baskets.id"), nullable=False)

    level = Column(String(50), nullable=False)
    term = Column(String(50), nullable=False)
    course_name = Column(String(200), nullable=False)
    unique_code = Column(String(50), nullable=False)
    units = Column(Integer, default=0)
    course_type = Column(String(50), default="")
    estimated_capacity = Column(Integer, default=0)
    required_classes = Column(Integer, default=1)
    group_number = Column(Integer, default=1)
    avg_in_mehr = Column(Integer, default=0)
    avg_in_bahman = Column(Integer, default=0)
    avg_capacity_in_mehr = Column(Integer, default=0)
    avg_capacity_in_bahman = Column(Integer, default=0)
    from_termic = Column(Boolean, default=False)
    from_prerequisite = Column(Boolean, default=False)
    from_student_demand = Column(Boolean, default=False)
    from_manager = Column(Boolean, default=False)
    workflow_id = Column(Integer, ForeignKey("schedule_workflows.id"), nullable=True)
    semester = Column(String(20), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # روابط
    basket = relationship("Basket", back_populates="items")
    workflow = relationship("ScheduleWorkflow", backref="basket_items")

    def to_dict(self):
        return {
            "id": self.id,
            "basket_id": self.basket_id,
            "level": self.level,
            "term": self.term,
            "course_name": self.course_name,
            "unique_code": self.unique_code,
            "units": self.units,
            "course_type": self.course_type,
            "estimated_capacity": self.estimated_capacity,
            "required_classes": self.required_classes,
            "group_number": self.group_number,
            "avg_in_mehr": self.avg_in_mehr,
            "avg_in_bahman": self.avg_in_bahman,
            "avg_capacity_in_mehr": self.avg_capacity_in_mehr,
            "avg_capacity_in_bahman": self.avg_capacity_in_bahman,
            "from_termic": self.from_termic,
            "from_prerequisite": self.from_prerequisite,
            "from_student_demand": self.from_student_demand,
            "from_manager": self.from_manager,
            "workflow_id": self.workflow_id,
            "semester": self.semester,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }