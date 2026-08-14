from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, Field


class Semester(str, Enum):
    MEHR = "mehr"
    BAHMAN = "bahman"


class CourseType(str, Enum):
    THEORY = "theory"
    PRACTICAL = "practical"
    LAB = "lab"


class Course(BaseModel):
    id: int
    code: str
    title: str

    # شماره ترم در چارت، مانند 1، 2، 3 و ...
    chart_term: int

    credits: int = 3
    course_type: CourseType = CourseType.THEORY

    # گروه دانشجویی یا ترم هدف
    cohorts: List[str] = []

    prerequisites: List[int] = []
    corequisites: List[int] = []

    active: bool = True
    graduation_critical: bool = False
    bottleneck: bool = False

    historical_demand: float = 0
    direct_requests: int = 0
    chart_required: bool = False

    preferred_days: List[int] = []
    preferred_slots: List[int] = []


class Instructor(BaseModel):
    id: int
    name: str
    qualified_course_ids: List[int]

    preferred_days: List[int] = []
    preferred_slots: List[int] = []


class Room(BaseModel):
    id: int
    name: str
    capacity: int
    room_types: List[CourseType]


class TimeSlot(BaseModel):
    id: int
    day: int
    start: str
    end: str


class ScheduleRequest(BaseModel):
    semester: Semester
    courses: List[Course]
    instructors: List[Instructor]
    rooms: List[Room]
    slots: List[TimeSlot]

    max_groups_per_course: int = 3
    demand_threshold: int = 10
    number_of_scenarios: int = 3

    # شناسه چارت انتخاب‌شده
    chart_id: int = 1

    # ترم فعلی دانشجویان
    current_terms: List[int] = []