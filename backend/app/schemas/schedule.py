from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class ScheduledClass(BaseModel):
    course_id: int
    course_code: str
    course_title: str
    group_number: int
    instructor_id: int
    instructor_name: str
    room_id: int
    room_name: str
    room_capacity: int
    slot_id: int
    day: int
    start: str
    end: str
    predicted_students: int
    students_per_group: int
    course_type: str
    cohorts: List[str] = Field(default_factory=list)
    explanation: List[str] = Field(default_factory=list)
    basket_id: Optional[int] = None


class Conflict(BaseModel):
    type: str
    message: str
    related_items: List[int] = Field(default_factory=list)


class ScheduleResponse(BaseModel):
    status: str
    objective_value: Optional[float] = None
    classes: List[ScheduledClass] = Field(default_factory=list)
    hard_constraints_satisfied: bool
    conflicts: List[Conflict] = Field(default_factory=list)
    explanations: List[str] = Field(default_factory=list)
    unschedulable_courses: List[dict] = Field(default_factory=list)
    expected_group_count: int = 0
    actual_group_count: int = 0
    warnings: List[str] = Field(default_factory=list)
    alternative_scenarios: List[dict] = Field(default_factory=list)


class RoomAssignmentRequest(BaseModel):
    class_id: int = Field(..., description="شناسه کلاس برنامه")
    room_id: int = Field(..., description="شناسه اتاق جدید")
    reason: Optional[str] = Field(None, description="دلیل تغییر")


class ScheduledClassResponse(BaseModel):
    id: int
    course_code: str
    course_title: str
    group_number: int
    instructor_name: Optional[str] = None
    room_name: Optional[str] = None
    room_id: Optional[int] = None
    capacity: Optional[int] = None
    day: int
    start_time: str
    end_time: str
    predicted_students: int
    scenario_id: int
    basket_id: Optional[int] = None

    class Config:
        from_attributes = True


class SaveScheduleRequest(BaseModel):
    classes: List[dict] = Field(..., description="لیست کلاس‌های زمان‌بندی‌شده")
    workflow_id: int = Field(..., description="شناسه workflow")
    semester: str = Field(..., description="نیمسال")
    year: str = Field("1403", description="سال")


class AllocatedClassesResponse(BaseModel):
    workflow_id: int
    total: int
    classes: List[ScheduledClassResponse]


# ============================================================
#  اسکیماهای مربوط به بهینه‌سازی (Optimization)
# ============================================================

class OptimizationRequest(BaseModel):
    """
    درخواست بهینه‌سازی برنامه
    """
    schedule: List[Dict[str, Any]] = Field(
        ...,
        description="لیست کلاس‌های برنامه (هر کلاس یک دیکشنری با فیلدهای مشخص)"
    )
    workflow_id: Optional[int] = Field(
        None,
        description="شناسه workflow (اختیاری)"
    )
    basket_id: Optional[int] = Field(
        None,
        description="شناسه سبد (اختیاری)"
    )

    class Config:
        schema_extra = {
            "example": {
                "schedule": [
                    {
                        "id": 1,
                        "course_name": "ریاضی عمومی",
                        "instructor_code": "P001",
                        "day": 0,
                        "start": "08:00",
                        "end": "09:30",
                        "room_id": 5,
                        "room_name": "A101",
                        "group_number": 1,
                        "units": 3,
                        "level": "کارشناسی",
                        "estimated_capacity": 40
                    }
                ],
                "workflow_id": 1,
                "basket_id": 1
            }
        }


class OptimizationResponse(BaseModel):
    """
    پاسخ بهینه‌سازی برنامه
    """
    success: bool = Field(..., description="وضعیت موفقیت")
    message: str = Field(..., description="پیام")
    optimized_schedule: List[Dict[str, Any]] = Field(
        ...,
        description="برنامه بهینه‌سازی‌شده (با همان ساختار ورودی)"
    )
    total_classes: int = Field(..., description="تعداد کل کلاس‌ها")

    class Config:
        schema_extra = {
            "example": {
                "success": True,
                "message": "بهینه‌سازی با موفقیت انجام شد.",
                "optimized_schedule": [
                    {
                        "id": 1,
                        "course_name": "ریاضی عمومی",
                        "instructor_code": "P001",
                        "day": 1,
                        "start": "10:00",
                        "end": "11:30",
                        "room_id": 3,
                        "room_name": "A102",
                        "group_number": 1,
                        "units": 3,
                        "level": "کارشناسی",
                        "estimated_capacity": 40
                    }
                ],
                "total_classes": 1
            }
        }