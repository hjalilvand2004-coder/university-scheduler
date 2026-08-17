from typing import List, Optional

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

    class Config:
        from_attributes = True


class SaveScheduleRequest(BaseModel):
    classes: List[dict] = Field(
        ...,
        description="لیست کلاس‌های زمان‌بندی‌شده",
    )
    workflow_id: int = Field(
        ...,
        description="شناسه workflow",
    )
    semester: str = Field(
        ...,
        description="نیمسال",
    )
    year: str = Field(
        "1403",
        description="سال",
    )


class AllocatedClassesResponse(BaseModel):
    workflow_id: int
    total: int
    classes: List[ScheduledClassResponse]