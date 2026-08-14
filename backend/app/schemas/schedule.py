from typing import List, Optional

from pydantic import BaseModel


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
    cohorts: List[str] = []
    explanation: List[str] = []


class Conflict(BaseModel):
    type: str
    message: str
    related_items: List[int] = []


class ScheduleResponse(BaseModel):
    status: str
    objective_value: Optional[float] = None

    classes: List[ScheduledClass] = []

    hard_constraints_satisfied: bool

    conflicts: List[Conflict] = []

    explanations: List[str] = []

    unschedulable_courses: List[dict] = []

    expected_group_count: int = 0
    actual_group_count: int = 0

    warnings: List[str] = []

    alternative_scenarios: List[dict] = []