from pydantic import BaseModel
from datetime import datetime
from typing import List, Optional

class BasketItemBase(BaseModel):
    level: str
    term: str
    course_name: str
    unique_code: str
    units: Optional[int] = 0
    course_type: Optional[str] = ""
    estimated_capacity: Optional[int] = 0
    required_classes: Optional[int] = 1
    group_number: Optional[int] = 1
    avg_in_mehr: Optional[int] = 0
    avg_in_bahman: Optional[int] = 0
    avg_capacity_in_mehr: Optional[int] = 0
    avg_capacity_in_bahman: Optional[int] = 0
    from_termic: Optional[bool] = False
    from_prerequisite: Optional[bool] = False
    from_student_demand: Optional[bool] = False
    from_manager: Optional[bool] = False
    workflow_id: Optional[int] = None
    semester: Optional[str] = None

class BasketItemOut(BasketItemBase):
    id: int
    basket_id: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class BasketBase(BaseModel):
    title: str
    semester: str
    year: str

class BasketCreate(BasketBase):
    pass

class BasketUpdate(BasketBase):
    pass

class BasketOut(BasketBase):
    id: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    items: List[BasketItemOut] = []

    class Config:
        from_attributes = True