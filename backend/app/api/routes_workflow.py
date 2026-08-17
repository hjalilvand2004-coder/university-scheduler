# app/api/routes_workflow.py
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Dict, Any, Optional
from pydantic import BaseModel
import logging

from app.core.database import get_db
from app.services.workflow_service import WorkflowService
from app.services.basket_service import BasketService
from app.services.schedule_service import ScheduleService
from app.services.room_allocation_service import RoomAllocationService
from app.services.optimization_service import OptimizationService
from app.models.workflow import ScheduleWorkflow, WorkflowStatus
from app.models.basket_item import BasketItem
from app.models.schedule import ScheduledClass
from app.models.course import UniqueCourse, OfferedCourse

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/schedule/workflow", tags=["workflow"])


# ===== Pydantic Schemas =====
class WorkflowStep1Request(BaseModel):
    semester: str
    levels: List[str]
    year: str = "1403"


class WorkflowStep5Request(BaseModel):
    updated_data: List[Dict[str, Any]]


class WorkflowStepUpdateRequest(BaseModel):
    step_number: int
    data: List[Dict[str, Any]]


# ===== Schemas برای فرایندهای چهارگانه جدید =====
class BasketRequest(BaseModel):
    semester: str
    levels: List[str]
    year: str = "1403"


class ScheduleRequest(BaseModel):
    basket: List[Dict[str, Any]]


class RoomAllocationRequest(BaseModel):
    schedule: List[Dict[str, Any]]


class OptimizationRequest(BaseModel):
    schedule: List[Dict[str, Any]]


# ===== Schemas برای سبد دو مرحله‌ای =====
class BasketInitialRequest(BaseModel):
    semester: str
    levels: List[str]
    year: str = "1403"


class BasketStatisticsRequest(BaseModel):
    basket: List[Dict[str, Any]]


# ===== Schemas جدید برای ذخیره و بازیابی سبد =====
class SaveBasketRequest(BaseModel):
    basket: List[Dict[str, Any]]
    workflow_id: Optional[int] = None
    semester: str = ""


class UpdateBasketItemRequest(BaseModel):
    required_classes: Optional[int] = None
    from_manager: Optional[bool] = None


# ===== Schemas برای تخصیص دستی =====
class ManualAssignmentItem(BaseModel):
    id: Optional[int] = None
    course_name: str
    group_number: int
    level: str
    term: str
    instructor_code: str
    day: int
    start: str
    end: str


class ManualAssignRequest(BaseModel):
    assignments: List[ManualAssignmentItem]


# ===== Schema برای ذخیره‌سازی کلاس‌های زمان‌بندی شده =====
class SaveScheduleRequest(BaseModel):
    classes: List[Dict[str, Any]]
    workflow_id: int
    semester: str
    year: str = "1403"


# ============================================================
# ===== گام‌های ۱ تا ۵ =====
# ============================================================
@router.post("/step1", status_code=status.HTTP_201_CREATED)
def step1_integrate(req: WorkflowStep1Request, db: Session = Depends(get_db)):
    service = WorkflowService(db)
    try:
        data = service.step1_integrate_courses(req.semester, req.levels, req.year)
    except Exception as e:
        raise HTTPException(400, detail=f"خطا در یکپارچه‌سازی دروس: {str(e)}")
    workflow = ScheduleWorkflow(
        semester=req.semester,
        levels=req.levels,
        year=req.year,
        step1_data=data,
        step1_done=True,
        current_step=1,
        status=WorkflowStatus.IN_PROGRESS
    )
    db.add(workflow)
    db.commit()
    db.refresh(workflow)
    return {
        "workflow_id": workflow.id,
        "step1_data": data,
        "current_step": workflow.current_step,
        "status": workflow.status.value
    }


@router.post("/step2/{workflow_id}")
def step2_add_bottleneck(workflow_id: int, db: Session = Depends(get_db)):
    workflow = db.query(ScheduleWorkflow).filter(ScheduleWorkflow.id == workflow_id).first()
    if not workflow:
        raise HTTPException(404, detail="Workflow not found")
    if not workflow.step1_data or "integrated_courses" not in workflow.step1_data:
        raise HTTPException(400, detail="داده‌های گام اول موجود نیست")
    integrated = workflow.step1_data["integrated_courses"]
    if not isinstance(integrated, list):
        raise HTTPException(400, detail="داده‌های گام اول باید از نوع لیست باشد")
    service = WorkflowService(db)
    try:
        step2_data = service.step2_add_bottleneck_courses(integrated)
    except Exception as e:
        raise HTTPException(400, detail=f"خطا در اضافه کردن دروس گلوگاهی: {str(e)}")
    workflow.step2_data = step2_data
    workflow.step2_done = True
    workflow.current_step = 2
    db.commit()
    db.refresh(workflow)
    return {
        "step2_data": step2_data,
        "current_step": workflow.current_step,
        "status": workflow.status.value
    }


@router.post("/step3/{workflow_id}")
def step3_estimate_demand(workflow_id: int, db: Session = Depends(get_db)):
    workflow = db.query(ScheduleWorkflow).filter(ScheduleWorkflow.id == workflow_id).first()
    if not workflow:
        raise HTTPException(404, detail="Workflow not found")
    if not workflow.step2_data:
        raise HTTPException(400, detail="داده‌های گام دوم موجود نیست")
    service = WorkflowService(db)
    courses = workflow.step2_data
    try:
        step3_data = service.step3_estimate_demand(courses)
    except Exception as e:
        raise HTTPException(400, detail=f"خطا در تخمین میانگین فراوانی: {str(e)}")
    workflow.step3_data = step3_data
    workflow.step3_done = True
    workflow.current_step = 3
    db.commit()
    db.refresh(workflow)
    return {
        "step3_data": step3_data,
        "current_step": workflow.current_step,
        "status": workflow.status.value
    }


@router.post("/step4/{workflow_id}")
def step4_day_scheduling(workflow_id: int, db: Session = Depends(get_db)):
    workflow = db.query(ScheduleWorkflow).filter(ScheduleWorkflow.id == workflow_id).first()
    if not workflow:
        raise HTTPException(404, detail="Workflow not found")
    if not workflow.step3_data:
        raise HTTPException(400, detail="داده‌های گام سوم موجود نیست")
    service = WorkflowService(db)
    courses = workflow.step3_data
    try:
        step4_data = service.step4_day_scheduling(courses)
    except Exception as e:
        raise HTTPException(400, detail=f"خطا در چیدمان روزانه: {str(e)}")
    workflow.step4_data = step4_data
    workflow.step4_done = True
    workflow.current_step = 4
    db.commit()
    db.refresh(workflow)
    return {
        "step4_data": step4_data,
        "current_step": workflow.current_step,
        "status": workflow.status.value
    }


@router.post("/step5/{workflow_id}")
def step5_assign_instructors(workflow_id: int, db: Session = Depends(get_db)):
    workflow = db.query(ScheduleWorkflow).filter(ScheduleWorkflow.id == workflow_id).first()
    if not workflow:
        raise HTTPException(404, detail="Workflow not found")
    if not workflow.step4_data:
        raise HTTPException(400, detail="داده‌های گام چهارم موجود نیست")
    service = WorkflowService(db)
    courses = workflow.step4_data
    try:
        step5_data = service.step5_assign_instructors(courses)
    except Exception as e:
        raise HTTPException(400, detail=f"خطا در تخصیص استاد: {str(e)}")
    workflow.step5_data = step5_data
    workflow.step5_done = True
    workflow.current_step = 5
    workflow.status = WorkflowStatus.COMPLETED
    db.commit()
    db.refresh(workflow)
    return {
        "step5_data": step5_data,
        "current_step": workflow.current_step,
        "status": workflow.status.value,
        "message": "فرایند تولید برنامه با موفقیت کامل شد."
    }


@router.put("/step5/manual/{workflow_id}")
def step5_manual_edit(workflow_id: int, req: WorkflowStep5Request, db: Session = Depends(get_db)):
    workflow = db.query(ScheduleWorkflow).filter(ScheduleWorkflow.id == workflow_id).first()
    if not workflow:
        raise HTTPException(404, detail="Workflow not found")
    if not req.updated_data or len(req.updated_data) == 0:
        raise HTTPException(400, detail="داده‌های ویرایش‌شده خالی است")
    workflow.step5_data = req.updated_data
    workflow.step5_done = True
    workflow.status = WorkflowStatus.COMPLETED
    db.commit()
    db.refresh(workflow)
    return {
        "status": "finalized",
        "message": "برنامه نهایی با موفقیت ذخیره شد.",
        "data": req.updated_data,
        "workflow_id": workflow.id
    }


@router.put("/{workflow_id}/step")
def update_workflow_step(workflow_id: int, req: WorkflowStepUpdateRequest, db: Session = Depends(get_db)):
    workflow = db.query(ScheduleWorkflow).filter(ScheduleWorkflow.id == workflow_id).first()
    if not workflow:
        raise HTTPException(404, detail="Workflow not found")
    step_num = req.step_number
    if not (1 <= step_num <= 5):
        raise HTTPException(400, detail="شماره گام باید بین ۱ تا ۵ باشد")
    step_field = f"step{step_num}_data"
    if not hasattr(workflow, step_field):
        raise HTTPException(400, detail="فیلد گام نامعتبر است")
    if not isinstance(req.data, list):
        raise HTTPException(400, detail="داده‌ها باید به صورت لیست ارسال شوند")
    setattr(workflow, step_field, req.data)
    db.commit()
    db.refresh(workflow)
    return {
        "message": f"گام {step_num} با موفقیت به‌روز شد",
        "workflow_id": workflow.id,
        "step_number": step_num,
        "data": req.data
    }


@router.get("/{workflow_id}")
def get_workflow(workflow_id: int, db: Session = Depends(get_db)):
    workflow = db.query(ScheduleWorkflow).filter(ScheduleWorkflow.id == workflow_id).first()
    if not workflow:
        raise HTTPException(404, detail="Workflow not found")
    return workflow.to_dict()


@router.get("/list/all")
def get_all_workflows(db: Session = Depends(get_db)):
    workflows = db.query(ScheduleWorkflow).order_by(ScheduleWorkflow.created_at.desc()).all()
    return {"workflows": [w.to_dict() for w in workflows]}


@router.delete("/{workflow_id}")
def delete_workflow(workflow_id: int, db: Session = Depends(get_db)):
    workflow = db.query(ScheduleWorkflow).filter(ScheduleWorkflow.id == workflow_id).first()
    if not workflow:
        raise HTTPException(404, detail="Workflow not found")
    if workflow.status == WorkflowStatus.IN_PROGRESS:
        workflow.status = WorkflowStatus.CANCELLED
        db.commit()
    db.delete(workflow)
    db.commit()
    return {"status": "deleted", "workflow_id": workflow_id}


# ============================================================
# ===== فرایندهای چهارگانه جدید (با سرویس‌های مستقل) =====
# ============================================================

@router.post("/basket", status_code=status.HTTP_200_OK)
def process_basket(req: BasketRequest, db: Session = Depends(get_db)):
    service = BasketService(db)
    try:
        basket = service.process(req.semester, req.levels, req.year)
    except Exception as e:
        raise HTTPException(400, detail=f"خطا در شناسایی سبد دروس: {str(e)}")
    return {"basket": basket}


@router.post("/basket/initial", status_code=status.HTTP_200_OK)
def get_initial_basket(req: BasketInitialRequest, db: Session = Depends(get_db)):
    service = BasketService(db)
    try:
        basket = service.get_initial_basket(req.semester, req.levels, req.year)
    except Exception as e:
        raise HTTPException(400, detail=f"خطا در دریافت لیست اولیه: {str(e)}")
    return {"basket": basket}


@router.post("/basket/statistics", status_code=status.HTTP_200_OK)
def add_statistics_to_basket(req: BasketStatisticsRequest, db: Session = Depends(get_db)):
    if not req.basket:
        raise HTTPException(400, detail="سبد دروس خالی است")
    service = BasketService(db)
    try:
        basket = service.add_statistics_to_basket(req.basket)
    except Exception as e:
        raise HTTPException(400, detail=f"خطا در افزودن آمار به سبد: {str(e)}")
    return {"basket": basket}


# ============================================================
# ===== APIهای ذخیره و بازیابی سبد (با ترتیب صحیح) =====
# ============================================================
@router.post("/basket/save", status_code=status.HTTP_201_CREATED)
def save_basket(req: SaveBasketRequest, db: Session = Depends(get_db)):
    logger.info(f"📥 درخواست ذخیره سبد دریافت شد. تعداد آیتم‌ها: {len(req.basket)}")
    logger.debug(f"workflow_id: {req.workflow_id}, semester: {req.semester}")

    if not req.basket:
        raise HTTPException(400, detail="سبد دروس خالی است")

    service = BasketService(db)
    try:
        saved_items = service.save_basket(
            basket_items=req.basket,
            workflow_id=req.workflow_id,
            semester=req.semester
        )
        logger.info(f"✅ {len(saved_items)} رکورد با موفقیت ذخیره شد.")
        return {
            "status": "success",
            "message": f"{len(saved_items)} رکورد با موفقیت ذخیره شد.",
            "count": len(saved_items),
            "items": [item.to_dict() for item in saved_items]
        }
    except Exception as e:
        logger.error(f"❌ خطا در ذخیره‌سازی سبد: {e}", exc_info=True)
        raise HTTPException(400, detail=f"خطا در ذخیره‌سازی سبد: {str(e)}")


@router.get("/basket/test")
def test_basket_route():
    return {"status": "ok", "message": "Basket routes are working"}


@router.get("/basket/{workflow_id}")
def get_basket_by_workflow(workflow_id: int, db: Session = Depends(get_db)):
    service = BasketService(db)
    try:
        items = service.get_basket_by_workflow(workflow_id)
        return {"basket": items, "count": len(items)}
    except Exception as e:
        raise HTTPException(400, detail=f"خطا در دریافت سبد: {str(e)}")


@router.get("/basket")
def get_basket_by_semester(
    semester: str,
    level: Optional[str] = None,
    db: Session = Depends(get_db)
):
    service = BasketService(db)
    try:
        items = service.get_basket_by_semester(semester, level)
        return {"basket": items, "count": len(items)}
    except Exception as e:
        raise HTTPException(400, detail=f"خطا در دریافت سبد: {str(e)}")


@router.put("/basket/item/{item_id}")
def update_basket_item(item_id: int, req: UpdateBasketItemRequest, db: Session = Depends(get_db)):
    item = db.query(BasketItem).filter(BasketItem.id == item_id).first()
    if not item:
        raise HTTPException(404, detail="آیتم سبد یافت نشد")
    if req.required_classes is not None:
        item.required_classes = req.required_classes
    if req.from_manager is not None:
        item.from_manager = req.from_manager
    db.commit()
    db.refresh(item)
    return {"status": "success", "item": item.to_dict()}


@router.delete("/basket/{workflow_id}")
def delete_basket_by_workflow(workflow_id: int, db: Session = Depends(get_db)):
    service = BasketService(db)
    try:
        deleted_count = service.delete_basket_by_workflow(workflow_id)
        return {
            "status": "success",
            "message": f"{deleted_count} رکورد با موفقیت حذف شد.",
            "deleted_count": deleted_count
        }
    except Exception as e:
        raise HTTPException(400, detail=f"خطا در حذف سبد: {str(e)}")


# ============================================================
# ===== فرایندهای ۲، ۳ و ۴ (با ساختار دو مرحله‌ای) =====
# ============================================================

@router.post("/schedule", status_code=status.HTTP_200_OK)
def process_schedule(req: ScheduleRequest, db: Session = Depends(get_db)):
    if not req.basket:
        raise HTTPException(400, detail="سبد دروس خالی است")
    service = ScheduleService(db)
    try:
        result = service.process(req.basket)
        return result
    except Exception as e:
        logger.error(f"خطا در زمان‌بندی: {e}", exc_info=True)
        raise HTTPException(400, detail=f"خطا در زمان‌بندی استاد و درس: {str(e)}")


@router.post("/schedule/manual", status_code=status.HTTP_200_OK)
def manual_assign_instructors(req: ManualAssignRequest, db: Session = Depends(get_db)):
    if not req.assignments:
        raise HTTPException(400, detail="لیست تخصیص دستی خالی است")
    service = ScheduleService(db)
    try:
        assignments_data = [item.dict() for item in req.assignments]
        result = service.manual_assign(assignments_data)
        return result
    except Exception as e:
        logger.error(f"خطا در تخصیص دستی: {e}", exc_info=True)
        raise HTTPException(400, detail=f"خطا در تخصیص دستی: {str(e)}")


@router.post("/rooms", status_code=status.HTTP_200_OK)
def process_rooms(req: RoomAllocationRequest, db: Session = Depends(get_db)):
    if not req.schedule:
        raise HTTPException(400, detail="برنامه زمان‌بندی خالی است")
    service = RoomAllocationService(db)
    try:
        allocated = service.process(req.schedule)
    except Exception as e:
        raise HTTPException(400, detail=f"خطا در تخصیص اتاق: {str(e)}")
    return {"allocated": allocated}


@router.post("/optimize", status_code=status.HTTP_200_OK)
def process_optimize(req: OptimizationRequest, db: Session = Depends(get_db)):
    if not req.schedule:
        raise HTTPException(400, detail="برنامه ورودی خالی است")
    service = OptimizationService(db)
    try:
        optimized = service.process(req.schedule)
    except Exception as e:
        raise HTTPException(400, detail=f"خطا در بهینه‌سازی برنامه: {str(e)}")
    return {"optimized": optimized}


# ============================================================
# ===== اندپوینت‌های جدید برای ذخیره و بازیابی کلاس‌های زمان‌بندی شده =====
# ============================================================

@router.post("/save-schedule", status_code=status.HTTP_201_CREATED)
def save_schedule(req: SaveScheduleRequest, db: Session = Depends(get_db)):
    """
    ذخیره‌سازی کلاس‌های زمان‌بندی‌شده در جدول scheduled_classes
    با تطبیق با ساختار واقعی جدول offered_courses
    """
    if not req.classes:
        raise HTTPException(400, detail="لیست کلاس‌ها خالی است")

    workflow = db.query(ScheduleWorkflow).filter(ScheduleWorkflow.id == req.workflow_id).first()
    if not workflow:
        raise HTTPException(404, detail="Workflow یافت نشد")

    # ---- تابع کمکی اصلاح‌شده بر اساس ساختار واقعی ----
    def get_or_create_offered_course(unique_course, year, db):
        """
        جستجو یا ایجاد رکورد در offered_courses بر اساس unique_code و year
        (چون ستون semester در این جدول وجود ندارد، آن را نادیده می‌گیریم)
        """
        # 1. جستجوی رکورد موجود
        offered = db.query(OfferedCourse).filter(
            OfferedCourse.unique_code == unique_course.code,
            OfferedCourse.year == year
        ).first()

        if offered:
            logger.debug(f"✅ OfferedCourse موجود با id={offered.id} برای کد {unique_course.code}")
            return offered

        # 2. ایجاد رکورد جدید در offered_courses
        new_offered = OfferedCourse(
            unique_code=unique_course.code,
            offered_title=unique_course.title,  # ✅ صحیح
            unique_title=unique_course.title,  # ✅ صحیح
            year=year,
        )
        db.add(new_offered)
        db.flush()  # برای گرفتن id جدید
        logger.info(f"✅ رکورد جدید در offered_courses با id={new_offered.id} ساخته شد")
        return new_offered

    saved_count = 0
    for idx, cls_data in enumerate(req.classes):
        course_code = cls_data.get("course_code") or cls_data.get("unique_code")
        if not course_code:
            logger.warning(f"⚠️ کلاس #{idx} فاقد course_code، رد شد")
            continue

        # پیدا کردن UniqueCourse (جدول دروس اصلی)
        unique_course = db.query(UniqueCourse).filter(UniqueCourse.code == course_code).first()
        if not unique_course:
            logger.error(f"❌ UniqueCourse با کد {course_code} یافت نشد")
            continue

        # ساخت/یافتن OfferedCourse (با ارسال year به جای semester)
        try:
            offered_course = get_or_create_offered_course(unique_course, req.year, db)
        except Exception as e:
            logger.error(f"❌ خطا در ساخت OfferedCourse برای {course_code}: {e}")
            continue

        course_id = offered_course.id  # این id در جدول scheduled_classes به عنوان کلید خارجی ذخیره می‌شود

        # بررسی تکراری نبودن در scheduled_classes
        existing = db.query(ScheduledClass).filter(
            ScheduledClass.course_code == course_code,
            ScheduledClass.group_number == cls_data.get("group_number", 1),
            ScheduledClass.scenario_id == req.workflow_id
        ).first()

        if existing:
            # به‌روزرسانی رکورد موجود
            existing.instructor_name = cls_data.get("instructor_name")
            existing.day = cls_data.get("day")
            existing.start_time = cls_data.get("start")
            existing.end_time = cls_data.get("end")
            existing.predicted_students = cls_data.get("predicted_students", 0)
            saved_count += 1
            logger.debug(f"🔄 کلاس موجود به‌روز شد: {course_code}")
            continue

        # ایجاد رکورد جدید در scheduled_classes
        new_class = ScheduledClass(
            course_id=course_id,
            course_code=course_code,
            course_title=cls_data.get("course_name"),
            group_number=cls_data.get("group_number", 1),
            instructor_name=cls_data.get("instructor_name"),
            room_name=cls_data.get("room_name"),
            day=cls_data.get("day"),
            start_time=cls_data.get("start"),
            end_time=cls_data.get("end"),
            predicted_students=cls_data.get("predicted_students", 0),
            semester=req.semester,  # اینجا semester ذخیره می‌شود (چون در scheduled_classes وجود دارد)
            year=req.year,
            scenario_id=req.workflow_id,
        )
        db.add(new_class)
        saved_count += 1
        logger.debug(f"➕ کلاس جدید اضافه شد: {course_code}")

    db.commit()
    logger.info(f"✅ تعداد {saved_count} کلاس با موفقیت در scheduled_classes ذخیره شد.")
    return {
        "status": "success",
        "message": f"{saved_count} کلاس با موفقیت ذخیره شد.",
        "saved_count": saved_count
    }


@router.get("/{workflow_id}/scheduled-classes")
def get_scheduled_classes(workflow_id: int, db: Session = Depends(get_db)):
    workflow = db.query(ScheduleWorkflow).filter(ScheduleWorkflow.id == workflow_id).first()
    if not workflow:
        raise HTTPException(404, detail="Workflow یافت نشد")

    classes = db.query(ScheduledClass).filter(
        ScheduledClass.scenario_id == workflow_id
    ).all()

    result = []
    for cls in classes:
        result.append({
            "id": cls.id,
            "course_code": cls.course_code,
            "course_title": cls.course_title,
            "group_number": cls.group_number,
            "instructor_name": cls.instructor_name,
            "room_name": cls.room_name,
            "room_id": cls.room_id,
            "capacity": cls.room_capacity,
            "day": cls.day,
            "start_time": cls.start_time,
            "end_time": cls.end_time,
            "predicted_students": cls.predicted_students,
        })

    return {
        "workflow_id": workflow_id,
        "total": len(result),
        "classes": result
    }