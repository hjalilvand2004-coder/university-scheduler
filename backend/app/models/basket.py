from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime
from app.core.database import Base

class Basket(Base):
    __tablename__ = "baskets"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(200), nullable=False)
    semester = Column(String(20), nullable=False)
    year = Column(String(10), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # رابطه با آیتم‌ها (یک سبد شامل چندین آیتم)
    items = relationship("BasketItem", back_populates="basket", cascade="all, delete-orphan")

    def to_dict(self):
        return {
            "id": self.id,
            "title": self.title,
            "semester": self.semester,
            "year": self.year,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "items_count": len(self.items) if self.items else 0,
        }

    @property
    def items_count(self):
        return len(self.items) if self.items else 0