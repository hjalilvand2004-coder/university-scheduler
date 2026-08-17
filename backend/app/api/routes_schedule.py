from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func
from pydantic import BaseModel, Field
from typing import List, Optional, Any, Dict, Union

from app.core.database import get_db
from app.services.scheduler_service import generate_schedule_from_db
from app.optimization.cp_sat_solver import solve_schedule
from app.data.sample_data import sample_courses, sample_instructors, sample_rooms, sample_slots
from app.schemas.course import Course, Instructor, Room, TimeSlot, CourseType, Semester
from app.models.instructor import Instructor as InstructorModel

# ===== تعریف router =====
router = APIRouter(prefix="/api/schedules", tags=["Schedules"])


# ============================================================
# مدل‌های درخواست و پاسخ
# ============================================================

class GenerateScheduleRequest(BaseModel):
    semester: str = Field(..., description="نیمسال تحصیلی: 'mehr' یا 'bahman'")
    levels: Optional[List[str]] = Field(None, description="لیست مقاطع (اختیاری) - اگر null باشد همه مقاطع")
    year: str = Field("1403", description="سال تحصیلی")
    max_groups_per_course: int = Field(3, ge=1, le=5, description="حداکثر تعداد گروه برای هر درس")
    demand_threshold: int = Field(10, ge=1, description="آستانه تقاضا برای اضافه شدن درس (در صورت عدم وجود در چارت)")
    number_of_scenarios: int = Field(3, ge=1, le=5, description="تعداد سناریوهای جایگزین")
    max_courses: int = Field(80, ge=1, le=150, description="حداکثر تعداد دروس قابل انتخاب (پیش‌فرض ۸۰)")


class ScheduledClassResponse(BaseModel):
    id: int
    course_code: str
    course_title: str
    group_number: int
    instructor_name: str
    room_name: str
    day: int
    start_time: str
    end_time: str
    predicted_students: int
    explanation: Optional[List[str]] = []


class RankedCourseResponse(BaseModel):
    course_code: str
    course_name: str
    score: float
    reasons: List[str]
    course_id: int


class ScheduleResponse(BaseModel):
    status: str
    objective_value: Optional[float]
    classes: List[ScheduledClassResponse]
    hard_constraints_satisfied: bool
    conflicts: List[Any]
    explanations: List[str]
    rejected_courses: List[Any]
    selected_courses: List[Any]
    ranked_courses: List[RankedCourseResponse]  # اضافه شد
    alternative_scenarios: List[Any]
    quality_metrics: Dict[str, Any]
    unschedulable_courses: List[Any]  # اضافه شد


class SavedScheduleResponse(BaseModel):
    total_classes: int
    scenarios: Dict[int, List[Any]]
    classes: List[Any]


class ManualChangeRequest(BaseModel):
    scheduled_class_id: int
    new_instructor_id: Optional[int] = None
    new_room_id: Optional[int] = None
    new_slot_id: Optional[int] = None
    reason: str


class ManualChangeResponse(BaseModel):
    status: str
    message: str
    conflicts: Optional[List[Dict[str, str]]] = None
    class_data: Optional[Dict[str, Any]] = None


# ============================================================
# توابع کمکی برای تبدیل داده‌های نمونه به Pydantic
# ============================================================

def convert_sample_course(data: Union[dict, Course]) -> Course:
    if isinstance(data, Course):
        return data
    course_type_str = data.get("course_type", "theory")
    try:
        course_type_enum = CourseType(course_type_str.lower())
    except ValueError:
        course_type_enum = CourseType.THEORY
    return Course(
        id=data["id"],
        code=data.get("code", ""),
        title=data["title"],
        chart_term=data.get("chart_term", 1),
        course_type=course_type_enum,
        cohorts=data.get("cohorts", []),
        prerequisites=data.get("prerequisites", []),
        corequisites=data.get("corequisites", []),
        active=data.get("active", True),
        graduation_critical=data.get("graduation_critical", False),
        bottleneck=data.get("bottleneck", False),
        historical_demand=data.get("historical_demand", 0),
        direct_requests=data.get("direct_requests", 0),
        chart_required=data.get("chart_required", False),
        preferred_days=data.get("preferred_days", []),
        preferred_slots=data.get("preferred_slots", []),
    )


def convert_sample_instructor(data: Union[dict, Instructor]) -> Instructor:
    if isinstance(data, Instructor):
        return data
    return Instructor(
        id=data["id"],
        name=data["name"],
        qualified_course_ids=data.get("qualified_course_ids", []),
        preferred_days=data.get("preferred_days", []),
        preferred_slots=data.get("preferred_slots", []),
    )


def convert_sample_room(data: Union[dict, Room]) -> Room:
    if isinstance(data, Room):
        return data
    room_types = []
    for rt in data.get("room_types", []):
        try:
            room_types.append(CourseType(rt.lower()))
        except ValueError:
            pass
    if not room_types:
        room_types = [CourseType.THEORY, CourseType.PRACTICAL, CourseType.LAB]
    return Room(
        id=data["id"],
        name=data["name"],
        capacity=data["capacity"],
        room_types=room_types,
    )


def convert_sample_time_slot(data: Union[dict, TimeSlot]) -> TimeSlot:
    if isinstance(data, TimeSlot):
        return data
    return TimeSlot(
        id=data["id"],
        day=data["day"],
        start=data["start"],
        end=data["end"],
    )


# ============================================================
# APIها
# ============================================================

@router.post(
    "/generate",
    response_model=ScheduleResponse,
    summary="تولید برنامه هفتگی",
    description="تولید برنامه بر اساس نیمسال و مقاطع انتخابی با استفاده از داده‌های دیتابیس"
)
def generate_schedule(
    request: GenerateScheduleRequest,
    db: Session = Depends(get_db)
):
    if request.semester not in ["mehr", "bahman"]:
        raise HTTPException(status_code=400, detail="نیمسال باید 'mehr' یا 'bahman' باشد")
    try:
        result = generate_schedule_from_db(
            db=db,
            semester=request.semester,
            levels=request.levels,
            year=request.year,
            max_groups_per_course=request.max_groups_per_course,
            demand_threshold=request.demand_threshold,
            number_of_scenarios=request.number_of_scenarios,
            max_courses=request.max_courses  # اضافه شد
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"خطا در تولید برنامه: {str(e)}")


@router.post(
    "/generate-sample",
    summary="تولید برنامه نمونه (برای تست)",
    description="تولید برنامه با داده‌های نمونه - بدون نیاز به دیتابیس"
)
def generate_sample_schedule(
    semester: str = "mehr",
    db: Session = Depends(get_db)  # اختیاری
):
    raw_courses = sample_courses()
    raw_instructors = sample_instructors()
    raw_rooms = sample_rooms()
    raw_slots = sample_slots()

    courses = [convert_sample_course(c) for c in raw_courses]
    instructors = [convert_sample_instructor(i) for i in raw_instructors]
    rooms = [convert_sample_room(r) for r in raw_rooms]
    slots = [convert_sample_time_slot(s) for s in raw_slots]

    solution = solve_schedule(
        courses=courses,
        instructors=instructors,
        rooms=rooms,
        slots=slots,
        max_groups_per_course=3,
    )

    return {
        "status": solution["status"],
        "objective_value": solution["objective_value"],
        "classes": solution["classes"],
        "hard_constraints_satisfied": solution["status"] != "infeasible",
        "conflicts": [],
        "explanations": ["برنامه نمونه با داده‌های نمونه تولید شده است"],
        "rejected_courses": [],
        "selected_courses": [],
        "alternative_scenarios": [],
        "quality_metrics": {
            "total_classes": len(solution["classes"]),
            "total_groups": len(solution["classes"]),
        },
        "ranked_courses": [],  # نمونه رتبه‌بندی ندارد
        "unschedulable_courses": solution.get("unschedulable_courses", [])
    }


@router.get("/saved", response_model=SavedScheduleResponse)
def get_saved_schedules(
    semester: Optional[str] = None,
    year: Optional[str] = None,
    db: Session = Depends(get_db)
):
    from app.models.schedule import ScheduledClass
    query = db.query(ScheduledClass)
    if semester:
        query = query.filter(ScheduledClass.semester == semester)
    if year:
        query = query.filter(ScheduledClass.year == year)
    classes = query.all()
    scenarios = {}
    for cls in classes:
        if cls.scenario_id not in scenarios:
            scenarios[cls.scenario_id] = []
        scenarios[cls.scenario_id].append(cls)
    return {"total_classes": len(classes), "scenarios": scenarios, "classes": classes}


@router.get("/{schedule_id}", response_model=ScheduledClassResponse)
def get_schedule(schedule_id: int, db: Session = Depends(get_db)):
    from app.models.schedule import ScheduledClass
    schedule = db.query(ScheduledClass).filter(ScheduledClass.id == schedule_id).first()
    if not schedule:
        raise HTTPException(status_code=404, detail="برنامه پیدا نشد")
    return {
        "id": schedule.id,
        "course_code": schedule.course_code,
        "course_title": schedule.course_title,
        "group_number": schedule.group_number,
        "instructor_name": schedule.instructor_name,
        "room_name": schedule.room_name,
        "day": schedule.day,
        "start_time": schedule.start_time,
        "end_time": schedule.end_time,
        "predicted_students": schedule.predicted_students,
        "explanation": schedule.explanation
    }


# ============================================================
# API اصلاح دستی برنامه
# ============================================================

@router.put(
    "/manual-change",
    response_model=ManualChangeResponse,
    summary="اصلاح دستی یک کلاس برنامه",
    description="تغییر استاد، کلاس یا زمان یک کلاس برنامه‌ریزی‌شده با اعتبارسنجی محدودیت‌ها"
)
def manual_change(
    request: ManualChangeRequest,
    db: Session = Depends(get_db)
):
    from app.models.schedule import ScheduledClass

    # 1. پیدا کردن کلاس مورد نظر
    scheduled_class = db.query(ScheduledClass).filter(
        ScheduledClass.id == request.scheduled_class_id
    ).first()
    if not scheduled_class:
        raise HTTPException(status_code=404, detail="کلاس برنامه پیدا نشد")

    # 2. اعتبارسنجی تغییرات
    conflicts = validate_manual_change(
        scheduled_class=scheduled_class,
        new_instructor_id=request.new_instructor_id,
        new_room_id=request.new_room_id,
        new_slot_id=request.new_slot_id,
        db=db
    )

    if conflicts:
        return ManualChangeResponse(
            status="conflict",
            message="تغییرات با محدودیت‌های سخت در تضاد است",
            conflicts=conflicts,
            class_data=None
        )

    # 3. اعمال تغییرات
    if request.new_instructor_id is not None:
        new_instructor = db.query(InstructorModel).filter(
            InstructorModel.id == request.new_instructor_id
        ).first()
        if not new_instructor:
            raise HTTPException(status_code=404, detail="استاد جدید پیدا نشد")
        scheduled_class.instructor_id = request.new_instructor_id
        scheduled_class.instructor_name = new_instructor.name

    if request.new_room_id is not None:
        scheduled_class.room_id = request.new_room_id

    if request.new_slot_id is not None:
        scheduled_class.slot_id = request.new_slot_id

    db.commit()
    db.refresh(scheduled_class)

    class_dict = {
        "id": scheduled_class.id,
        "course_code": scheduled_class.course_code,
        "course_title": scheduled_class.course_title,
        "group_number": scheduled_class.group_number,
        "instructor_name": scheduled_class.instructor_name,
        "room_name": scheduled_class.room_name,
        "day": scheduled_class.day,
        "start_time": scheduled_class.start_time,
        "end_time": scheduled_class.end_time,
        "predicted_students": scheduled_class.predicted_students,
    }

    return ManualChangeResponse(
        status="success",
        message="تغییرات با موفقیت اعمال شد",
        conflicts=None,
        class_data=class_dict
    )


# ============================================================
# توابع کمکی برای اعتبارسنجی اصلاح دستی
# ============================================================

def validate_manual_change(
    scheduled_class,
    new_instructor_id: Optional[int],
    new_room_id: Optional[int],
    new_slot_id: Optional[int],
    db: Session
) -> List[Dict[str, str]]:
    from app.models.schedule import ScheduledClass

    conflicts = []

    final_slot_id = new_slot_id if new_slot_id is not None else scheduled_class.slot_id
    final_instructor_id = new_instructor_id if new_instructor_id is not None else scheduled_class.instructor_id
    final_room_id = new_room_id if new_room_id is not None else scheduled_class.room_id

    if final_instructor_id:
        existing = db.query(ScheduledClass).filter(
            ScheduledClass.instructor_id == final_instructor_id,
            ScheduledClass.slot_id == final_slot_id,
            ScheduledClass.id != scheduled_class.id
        ).first()
        if existing:
            conflicts.append({
                "type": "instructor_conflict",
                "message": f"استاد '{existing.instructor_name}' در این زمان کلاس دیگری دارد: '{existing.course_title}'"
            })

    if final_room_id:
        existing = db.query(ScheduledClass).filter(
            ScheduledClass.room_id == final_room_id,
            ScheduledClass.slot_id == final_slot_id,
            ScheduledClass.id != scheduled_class.id
        ).first()
        if existing:
            conflicts.append({
                "type": "room_conflict",
                "message": f"کلاس '{existing.room_name}' در این زمان اشغال است: '{existing.course_title}'"
            })

    return conflicts



# -------------------------------------
#افزودن اندپوینت اختصاصی برای تخصیص اتاق درroutes_schedule.py
# --------------------------------------
# در app/api/routes_workflow.py یا app/api/routes_schedule.py

class RoomAssignmentRequest(BaseModel):
    class_id: int
    room_id: int
    reason: Optional[str] = None

@router.put("/scheduled-classes/{class_id}/room")
def assign_room_to_class(
    class_id: int,
    req: RoomAssignmentRequest,
    db: Session = Depends(get_db)
):
    from app.models.schedule import ScheduledClass
    from app.models.room import Room

    scheduled_class = db.query(ScheduledClass).filter(ScheduledClass.id == class_id).first()
    if not scheduled_class:
        raise HTTPException(404, detail="کلاس برنامه پیدا نشد")

    room = db.query(Room).filter(Room.id == req.room_id).first()
    if not room:
        raise HTTPException(404, detail="اتاق پیدا نشد")

    # اعتبارسنجی ساده (تداخل زمانی با سایر کلاس‌ها در همان اتاق)
    conflicting = db.query(ScheduledClass).filter(
        ScheduledClass.room_id == req.room_id,
        ScheduledClass.day == scheduled_class.day,
        ScheduledClass.start_time < scheduled_class.end_time,
        ScheduledClass.end_time > scheduled_class.start_time,
        ScheduledClass.id != class_id
    ).first()
    if conflicting:
        raise HTTPException(
            status_code=409,
            detail=f"اتاق {room.name} در این زمان توسط کلاس '{conflicting.course_title}' اشغال است."
        )

    scheduled_class.room_id = req.room_id
    scheduled_class.room_name = room.name
    if req.reason:
        scheduled_class.explanation = req.reason

    db.commit()
    db.refresh(scheduled_class)

    return {
        "status": "success",
        "message": f"اتاق {room.name} با موفقیت به کلاس {scheduled_class.course_title} تخصیص یافت.",
        "class": {
            "id": scheduled_class.id,
            "course_title": scheduled_class.course_title,
            "group_number": scheduled_class.group_number,
            "room_name": scheduled_class.room_name,
            "day": scheduled_class.day,
            "start_time": scheduled_class.start_time,
            "end_time": scheduled_class.end_time,
        }
    }