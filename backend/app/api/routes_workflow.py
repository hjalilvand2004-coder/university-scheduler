# app/api/routes_workflow.py (نسخه اصلاح‌شده با لاگ‌های بیشتر)
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, desc, and_, or_
from typing import List, Dict, Any, Optional
from pydantic import BaseModel
import logging
import json

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
from app.models.unassigned_class import UnassignedClass
from app.models.term_course import TermCourse

# ===== وارد کردن از فایل مرجع اسلات‌ها =====
from app.services.schedule.slot_times import normalize_term, get_slots, time_to_minutes

# ===== اصلاح import مدل Instructor =====
try:
    from app.models.instructor import Instructor
except ImportError:
    try:
        from app.models import Instructor
    except ImportError:
        Instructor = None
        logging.warning("⚠️ مدل Instructor یافت نشد. نام استاد پر نخواهد شد.")

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/schedule/workflow", tags=["workflow"])


# ===== توابع کمکی =====
def extract_term_from_data(data: List[Dict]) -> str:
    """
    استخراج ترم از لیست دیکشنری‌ها (اولین آیتم دارای term_key یا term)
    در صورت عدم وجود، پیش‌فرض 'mehr' برگردانده می‌شود.
    """
    if not data:
        return "mehr"
    first = data[0]
    term_key = first.get("term_key")
    if term_key:
        try:
            return normalize_term(term_key)
        except ValueError:
            pass
    term_raw = first.get("term")
    if term_raw:
        try:
            return normalize_term(term_raw)
        except ValueError:
            pass
    return "mehr"


def has_time_conflict(start1: str, end1: str, start2: str, end2: str) -> bool:
    """بررسی تداخل زمانی دو بازه"""
    s1 = time_to_minutes(start1)
    e1 = time_to_minutes(end1)
    s2 = time_to_minutes(start2)
    e2 = time_to_minutes(end2)
    return s1 < e2 and s2 < e1


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


class BasketInitialRequest(BaseModel):
    semester: str
    levels: List[str]
    year: str = "1403"


class BasketStatisticsRequest(BaseModel):
    basket: List[Dict[str, Any]]


class SaveBasketRequest(BaseModel):
    basket: List[Dict[str, Any]]
    workflow_id: Optional[int] = None
    semester: str = ""


class UpdateBasketItemRequest(BaseModel):
    required_classes: Optional[int] = None
    from_manager: Optional[bool] = None


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
    basket_id: int
    workflow_id: int


class SaveScheduleRequest(BaseModel):
    classes: List[Dict[str, Any]]
    unassigned: List[Dict[str, Any]] = []
    basket_id: Optional[int] = None
    workflow_id: int
    semester: str
    year: str = "1403"
    overwrite: bool = False


# ============================================================
# ===== گام‌های ۱ تا ۵ (بدون تغییر) =====
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
    term = workflow.semester
    try:
        term = normalize_term(term)
    except ValueError:
        term = "mehr"
    try:
        step4_data = service.step4_day_scheduling(courses, term=term)
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
# ===== فرایندهای چهارگانه جدید =====
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


@router.post("/basket/save", status_code=status.HTTP_201_CREATED)
def save_basket(req: SaveBasketRequest, db: Session = Depends(get_db)):
    logger.info(f"📥 درخواست ذخیره سبد دریافت شد. تعداد آیتم‌ها: {len(req.basket)}")
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
# ===== زمان‌بندی و تخصیص دستی با بررسی تداخل =====
# ============================================================
@router.post("/schedule", status_code=status.HTTP_200_OK)
def process_schedule(
    req: ScheduleRequest,
    term: Optional[str] = Query(None, description="ترم (اختیاری) - در صورت عدم ارسال از داده‌ها استخراج می‌شود"),
    db: Session = Depends(get_db)
):
    if not req.basket:
        raise HTTPException(400, detail="سبد دروس خالی است")
    if term:
        try:
            term = normalize_term(term)
        except ValueError:
            raise HTTPException(400, detail="ترم ارسالی نامعتبر است")
    else:
        term = extract_term_from_data(req.basket)
    service = ScheduleService(db)
    try:
        result = service.process(req.basket, term=term)
        return result
    except Exception as e:
        logger.error(f"خطا در زمان‌بندی: {e}", exc_info=True)
        raise HTTPException(400, detail=f"خطا در زمان‌بندی استاد و درس: {str(e)}")


@router.post("/schedule/manual", status_code=status.HTTP_200_OK)
def manual_assign_instructors(req: ManualAssignRequest, db: Session = Depends(get_db)):
    if not req.assignments:
        raise HTTPException(400, detail="لیست تخصیص دستی خالی است")

    workflow = db.query(ScheduleWorkflow).filter(ScheduleWorkflow.id == req.workflow_id).first()
    if not workflow:
        raise HTTPException(404, detail="Workflow یافت نشد")

    from app.models.basket import Basket
    basket_obj = db.query(Basket).filter(Basket.id == req.basket_id).first()
    if not basket_obj:
        raise HTTPException(404, detail="سبد اصلی یافت نشد")

    semester = basket_obj.semester or "mehr"
    year = basket_obj.year or "1403"

    success_count = 0
    errors = []
    updated_ids = []
    conflict_errors = []

    def get_instructor_name(instructor_code: str) -> Optional[str]:
        if not instructor_code:
            return None
        if Instructor is None:
            return None
        try:
            instructor = db.query(Instructor).filter(Instructor.code == instructor_code).first()
            if instructor:
                return instructor.name
        except Exception as e:
            logger.warning(f"⚠️ خطا در دریافت نام استاد {instructor_code}: {e}")
        return None

    def check_conflict(instructor_code: str, day: int, start: str, end: str, exclude_id: Optional[int] = None) -> bool:
        if not instructor_code:
            return False
        query = db.query(ScheduledClass).filter(
            ScheduledClass.instructor_code == instructor_code,
            ScheduledClass.day == day,
            ScheduledClass.basket_id == req.basket_id,
            ScheduledClass.scenario_id == req.workflow_id
        )
        if exclude_id is not None:
            query = query.filter(ScheduledClass.id != exclude_id)
        existing_classes = query.all()
        for cls in existing_classes:
            if has_time_conflict(start, end, cls.start_time, cls.end_time):
                return True
        return False

    for assign in req.assignments:
        try:
            unique_course = db.query(UniqueCourse).filter(
                UniqueCourse.title == assign.course_name
            ).first()
            if not unique_course:
                unique_course = db.query(UniqueCourse).filter(
                    UniqueCourse.title.ilike(f"%{assign.course_name}%")
                ).first()
            if not unique_course:
                errors.append(f"درس '{assign.course_name}' یافت نشد")
                continue

            if assign.instructor_code:
                conflict_exists = check_conflict(
                    instructor_code=assign.instructor_code,
                    day=assign.day,
                    start=assign.start,
                    end=assign.end,
                    exclude_id=assign.id
                )
                if conflict_exists:
                    conflict_errors.append(
                        f"تداخل زمانی برای استاد {assign.instructor_code} در روز {assign.day} و بازه {assign.start}-{assign.end} "
                        f"برای درس '{assign.course_name}' (گروه {assign.group_number})"
                    )
                    continue

            instructor_name = get_instructor_name(assign.instructor_code)

            if assign.id is not None:
                existing_class = db.query(ScheduledClass).filter(
                    ScheduledClass.id == assign.id,
                    ScheduledClass.basket_id == req.basket_id,
                    ScheduledClass.scenario_id == req.workflow_id
                ).first()
                if not existing_class:
                    errors.append(f"رکورد با id={assign.id} برای درس '{assign.course_name}' یافت نشد")
                    continue

                existing_class.instructor_code = assign.instructor_code
                existing_class.instructor_name = instructor_name
                existing_class.day = assign.day
                existing_class.start_time = assign.start
                existing_class.end_time = assign.end

                db.flush()
                success_count += 1
                updated_ids.append(assign.id)
                logger.info(f"✅ ویرایش کلاس (id={assign.id}): {assign.course_name} (گروه {assign.group_number}) → استاد {assign.instructor_code}")

            else:
                offered = db.query(OfferedCourse).filter(
                    OfferedCourse.unique_code == unique_course.code,
                    OfferedCourse.year == year
                ).first()
                if not offered:
                    offered = OfferedCourse(
                        unique_code=unique_course.code,
                        offered_title=unique_course.title,
                        unique_title=unique_course.title,
                        year=year,
                    )
                    db.add(offered)
                    db.flush()

                new_class = ScheduledClass(
                    course_id=offered.id,
                    course_code=unique_course.code,
                    course_title=assign.course_name,
                    group_number=assign.group_number,
                    instructor_code=assign.instructor_code,
                    instructor_name=instructor_name,
                    day=assign.day,
                    start_time=assign.start,
                    end_time=assign.end,
                    semester=semester,
                    year=year,
                    scenario_id=req.workflow_id,
                    basket_id=req.basket_id,
                    predicted_students=0,
                )
                db.add(new_class)

                unassigned = db.query(UnassignedClass).filter(
                    UnassignedClass.basket_id == req.basket_id,
                    UnassignedClass.course_code == unique_course.code,
                    UnassignedClass.group_number == assign.group_number,
                    UnassignedClass.scenario_id == req.workflow_id
                ).first()
                if unassigned:
                    db.delete(unassigned)

                success_count += 1
                logger.info(f"✅ تخصیص دستی جدید: {assign.course_name} (گروه {assign.group_number}) → استاد {assign.instructor_code}")

        except Exception as e:
            errors.append(f"خطا در پردازش {assign.course_name}: {str(e)}")
            logger.error(f"❌ خطا در پردازش {assign.course_name}: {e}")

    if conflict_errors:
        errors.extend(conflict_errors)

    if errors:
        db.rollback()
        error_message = ";\n".join(errors)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"خطا در تخصیص دستی:\n{error_message}"
        )

    try:
        db.commit()
    except Exception as e:
        db.rollback()
        logger.error(f"❌ خطا در commit دیتابیس: {e}")
        raise HTTPException(400, detail=f"خطا در ذخیره‌سازی دیتابیس: {str(e)}")

    return {
        "success_count": success_count,
        "errors": errors,
        "updated_ids": updated_ids,
        "message": f"{success_count} کلاس با موفقیت تخصیص/ویرایش یافت." + (f" {len(errors)} خطا رخ داد." if errors else "")
    }


# ============================================================
# ===== تخصیص اتاق =====
# ============================================================
@router.post("/rooms", status_code=status.HTTP_200_OK)
def process_rooms(
    req: RoomAllocationRequest,
    workflow_id: int = Query(..., description="شناسه workflow جاری"),
    semester: str = Query(..., description="نیمسال (mehr/bahman)"),
    year: str = Query("1403", description="سال تحصیلی"),
    db: Session = Depends(get_db)
):
    logger.info("=" * 60)
    logger.info("🏢 درخواست تخصیص اتاق دریافت شد.")
    logger.info(f"📦 workflow_id: {workflow_id}, semester: {semester}, year: {year}")
    logger.info(f"📊 تعداد کلاس‌های ورودی: {len(req.schedule)}")

    if not req.schedule:
        raise HTTPException(400, detail="برنامه زمان‌بندی خالی است")

    if req.schedule:
        sample = req.schedule[0]
        logger.info(f"📌 نمونه کلاس اول: {sample}")

    try:
        term = normalize_term(semester)
    except ValueError:
        term = "mehr"

    service = RoomAllocationService(db)
    try:
        allocated = service.process(req.schedule)
        logger.info(f"✅ تخصیص اتاق انجام شد. تعداد کلاس‌های پردازش‌شده: {len(allocated)}")

        saved = service.save_allocated_classes(
            classes_with_rooms=allocated,
            workflow_id=workflow_id,
            semester=semester,
            year=year
        )
        logger.info(f"💾 {len(saved)} کلاس در دیتابیس ذخیره شد.")

        result = [
            {
                "course_name": c.course_title,
                "instructor_name": c.instructor_name,
                "day": c.day,
                "start": c.start_time,
                "end": c.end_time,
                "room_name": c.room_name,
                "capacity": c.room_capacity,
                "group_number": c.group_number,
                "room_id": c.room_id,
                "id": c.id,
            }
            for c in saved
        ]

        allocated_count = sum(1 for r in result if r.get("room_name") and r["room_name"] != "بدون اتاق")
        logger.info(f"📊 آمار نهایی: {allocated_count} از {len(result)} کلاس اتاق دریافت کردند.")
        if allocated_count == 0:
            logger.warning("⚠️ هیچ کلاسی اتاق دریافت نکرد!")
        logger.info("=" * 60)

        return {"data": result}

    except Exception as e:
        logger.error(f"❌ خطا در تخصیص اتاق: {str(e)}", exc_info=True)
        raise HTTPException(500, detail=f"خطا در تخصیص اتاق: {str(e)}")


@router.post("/optimize", status_code=status.HTTP_200_OK)
def process_optimize(
    req: OptimizationRequest,
    term: Optional[str] = Query(None, description="ترم (اختیاری) - در صورت عدم ارسال از داده‌ها استخراج می‌شود"),
    db: Session = Depends(get_db)
):
    if not req.schedule:
        raise HTTPException(400, detail="برنامه ورودی خالی است")
    if term:
        try:
            term = normalize_term(term)
        except ValueError:
            raise HTTPException(400, detail="ترم ارسالی نامعتبر است")
    else:
        term = extract_term_from_data(req.schedule)
    service = OptimizationService(db)
    try:
        optimized = service.process(req.schedule, term=term)
    except Exception as e:
        raise HTTPException(400, detail=f"خطا در بهینه‌سازی برنامه: {str(e)}")
    return {"optimized": optimized}


# ============================================================
# ===== ذخیره و بازیابی کلاس‌های زمان‌بندی شده =====
# ============================================================
@router.post("/save-schedule", status_code=status.HTTP_201_CREATED)
def save_schedule(req: SaveScheduleRequest, db: Session = Depends(get_db)):
    if not req.classes and not req.unassigned:
        raise HTTPException(400, detail="هر دو لیست کلاس‌ها و بدون استاد خالی است")

    workflow = db.query(ScheduleWorkflow).filter(ScheduleWorkflow.id == req.workflow_id).first()
    if not workflow:
        raise HTTPException(404, detail="Workflow یافت نشد")

    basket_id = req.basket_id

    if basket_id is not None and req.overwrite:
        deleted_assigned = db.query(ScheduledClass).filter(
            ScheduledClass.basket_id == basket_id,
            ScheduledClass.scenario_id == req.workflow_id
        ).delete()
        deleted_unassigned = db.query(UnassignedClass).filter(
            UnassignedClass.basket_id == basket_id,
            UnassignedClass.scenario_id == req.workflow_id
        ).delete()
        db.commit()
        logger.info(f"🗑️ {deleted_assigned} کلاس تخصیص‌یافته و {deleted_unassigned} کلاس بدون استاد قبلی حذف شدند.")
    elif basket_id is not None:
        existing_count = db.query(ScheduledClass).filter(
            ScheduledClass.basket_id == basket_id
        ).count()
        if existing_count > 0:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"برای سبد {basket_id} قبلاً برنامه زمان‌بندی ثبت شده است. لطفاً با overwrite=true درخواست دهید."
            )

    def get_or_create_offered_course(unique_course, year, db):
        offered = db.query(OfferedCourse).filter(
            OfferedCourse.unique_code == unique_course.code,
            OfferedCourse.year == year
        ).first()
        if offered:
            return offered
        new_offered = OfferedCourse(
            unique_code=unique_course.code,
            offered_title=unique_course.title,
            unique_title=unique_course.title,
            year=year,
        )
        db.add(new_offered)
        db.flush()
        return new_offered

    saved_count = 0
    for idx, cls_data in enumerate(req.classes):
        course_code = cls_data.get("course_code") or cls_data.get("unique_code")
        if not course_code:
            logger.warning(f"⚠️ کلاس #{idx} فاقد course_code، رد شد")
            continue
        unique_course = db.query(UniqueCourse).filter(UniqueCourse.code == course_code).first()
        if not unique_course:
            logger.error(f"❌ UniqueCourse با کد {course_code} یافت نشد")
            continue
        try:
            offered_course = get_or_create_offered_course(unique_course, req.year, db)
        except Exception as e:
            logger.error(f"❌ خطا در ساخت OfferedCourse برای {course_code}: {e}")
            continue
        course_id = offered_course.id
        item_basket_id = cls_data.get("basket_id") or basket_id

        new_class = ScheduledClass(
            course_id=course_id,
            course_code=course_code,
            course_title=cls_data.get("course_name"),
            group_number=cls_data.get("group_number", 1),
            instructor_name=cls_data.get("instructor_name"),
            instructor_code=cls_data.get("instructor_code"),
            room_name=cls_data.get("room_name"),
            day=cls_data.get("day"),
            start_time=cls_data.get("start"),
            end_time=cls_data.get("end"),
            predicted_students=cls_data.get("predicted_students", 0),
            semester=req.semester,
            year=req.year,
            scenario_id=req.workflow_id,
            basket_id=item_basket_id,
        )
        db.add(new_class)
        saved_count += 1
        logger.debug(f"➕ کلاس تخصیص‌یافته اضافه شد: {course_code}")

    unassigned_saved = 0
    for un_item in req.unassigned:
        course_code = un_item.get("course_code") or un_item.get("unique_code")
        if not course_code:
            logger.warning(f"⚠️ آیتم بدون استاد فاقد course_code، رد شد")
            continue
        unassigned = UnassignedClass(
            basket_id=un_item.get("basket_id") or basket_id,
            scenario_id=req.workflow_id,
            course_code=course_code,
            course_title=un_item.get("course_name"),
            group_number=un_item.get("group_number", 1),
            level=un_item.get("level"),
            term=un_item.get("term"),
            units=un_item.get("units"),
            estimated_capacity=un_item.get("estimated_capacity", 0),
        )
        db.add(unassigned)
        unassigned_saved += 1
        logger.debug(f"➕ کلاس بدون استاد اضافه شد: {course_code}")

    db.commit()
    logger.info(f"✅ {saved_count} کلاس تخصیص‌یافته و {unassigned_saved} کلاس بدون استاد ذخیره شد.")
    return {
        "status": "success",
        "message": f"{saved_count} کلاس تخصیص‌یافته و {unassigned_saved} کلاس بدون استاد ذخیره شد.",
        "saved_count": saved_count,
        "unassigned_saved": unassigned_saved
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
            "instructor_code": cls.instructor_code,
            "room_name": cls.room_name,
            "room_id": cls.room_id,
            "capacity": cls.room_capacity,
            "day": cls.day,
            "start_time": cls.start_time,
            "end_time": cls.end_time,
            "predicted_students": cls.predicted_students,
            "basket_id": cls.basket_id,
        })
    return {
        "workflow_id": workflow_id,
        "total": len(result),
        "classes": result
    }


# ============================================================
# ===== دریافت برنامه بر اساس basket_id (جدیدترین نسخه) =====
# ============================================================
@router.get("/scheduled-classes/by-basket/{basket_id}")
def get_scheduled_classes_by_basket(basket_id: int, db: Session = Depends(get_db)):
    max_scenario = db.query(func.max(ScheduledClass.scenario_id)).filter(
        ScheduledClass.basket_id == basket_id
    ).scalar()
    if max_scenario is None:
        max_scenario_un = db.query(func.max(UnassignedClass.scenario_id)).filter(
            UnassignedClass.basket_id == basket_id
        ).scalar()
        if max_scenario_un is not None:
            max_scenario = max_scenario_un
        else:
            logger.warning(f"⚠️ هیچ داده‌ای برای basket_id={basket_id} یافت نشد")
            return {
                "basket_id": basket_id,
                "total": 0,
                "scenario_id": None,
                "classes": [],
                "unassigned": []
            }

    logger.info(f"📋 جدیدترین scenario_id برای basket_id={basket_id}: {max_scenario}")

    assigned_classes = db.query(ScheduledClass).filter(
        ScheduledClass.basket_id == basket_id,
        ScheduledClass.scenario_id == max_scenario
    ).all()

    unassigned_classes = db.query(UnassignedClass).filter(
        UnassignedClass.basket_id == basket_id,
        UnassignedClass.scenario_id == max_scenario
    ).all()

    # ===== دریافت نگاشت course_code -> course_name =====
    course_name_map = {}
    if assigned_classes:
        course_codes = list(set([cls.course_code for cls in assigned_classes if cls.course_code]))
        if course_codes:
            unique_courses = db.query(UniqueCourse).filter(UniqueCourse.code.in_(course_codes)).all()
            for uc in unique_courses:
                course_name_map[uc.code] = uc.title
            logger.info(f"📚 نگاشت نام دروس از unique_courses برای {len(course_name_map)} درس دریافت شد.")

    result_assigned = []
    for cls in assigned_classes:
        # ===== دریافت نام درس =====
        course_name = course_name_map.get(cls.course_code, cls.course_title)
        if not course_name:
            try:
                term_course = db.query(TermCourse).filter(TermCourse.unique_course_code == cls.course_code).first()
                if term_course:
                    course_name = term_course.course_name or term_course.unique_course_name
                    logger.info(f"   📘 نام درس از term_courses: {course_name} برای {cls.course_code}")
            except Exception as e:
                logger.warning(f"⚠️ خطا در جستجوی term_courses برای {cls.course_code}: {e}")
        if not course_name:
            course_name = cls.course_code or f"کلاس {cls.id}"
            logger.warning(f"⚠️ نام درس برای course_code={cls.course_code} پیدا نشد، از course_code استفاده شد: {course_name}")

        result_assigned.append({
            "id": cls.id,
            "course_code": cls.course_code,
            "course_title": course_name,
            "course_name": course_name,  # ← اضافه کردن course_name برای فرانت
            "group_number": cls.group_number,
            "instructor_name": cls.instructor_name,
            "instructor_code": cls.instructor_code,
            "room_name": cls.room_name,
            "room_id": cls.room_id,
            "capacity": cls.room_capacity,
            "day": cls.day,
            "start_time": cls.start_time,
            "end_time": cls.end_time,
            "predicted_students": cls.predicted_students,
            "basket_id": cls.basket_id,
            "scenario_id": cls.scenario_id,
        })

    result_unassigned = [u.to_dict() for u in unassigned_classes]

    logger.info(f"✅ {len(result_assigned)} کلاس تخصیص‌یافته و {len(result_unassigned)} کلاس بدون استاد برای basket_id={basket_id} برگردانده شد.")
    if result_assigned:
        logger.info(f"📌 نمونه کلاس اول: {result_assigned[0]}")
        # ===== لاگ کامل اولین کلاس برای بررسی =====
        logger.info(f"📌 کلاس اول (JSON): {json.dumps(result_assigned[0], ensure_ascii=False)}")
    return {
        "basket_id": basket_id,
        "total": len(result_assigned),
        "scenario_id": max_scenario,
        "classes": result_assigned,
        "unassigned": result_unassigned
    }