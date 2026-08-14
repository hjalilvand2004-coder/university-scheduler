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
    """آیتم تخصیص دستی استاد"""
    id: Optional[int] = None  # شناسه کلاس در دیتابیس (اختیاری)
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
# 🔴 مهم: مسیرهای ثابت باید قبل از مسیرهای با پارامتر تعریف شوند
# مسیرهای ثابت:
# - /basket/save
# - /basket/test
# - /basket/initial
# - /basket/statistics
# سپس مسیرهای با پارامتر: /basket/{workflow_id}

@router.post("/basket/save", status_code=status.HTTP_201_CREATED)
def save_basket(req: SaveBasketRequest, db: Session = Depends(get_db)):
    """
    ذخیره‌سازی سبد دروس (کلاس‌های تولید شده) در دیتابیس
    """
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
    """
    مسیر تست برای بررسی اینکه روتر به درستی کار می‌کند
    """
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
    """
    زمان‌بندی استاد و درس در دو مرحله:
    1. تخصیص خودکار با اولویت‌بندی (هیات علمی، مطلوبیت‌ها)
    2. بازگرداندن کلاس‌های بدون استاد برای تخصیص دستی

    خروجی شامل:
        - assigned: لیست کلاس‌های تخصیص‌یافته
        - unassigned: لیست کلاس‌های بدون استاد (نیازمند مداخله دستی)
        - all: همه کلاس‌ها با وضعیت
    """
    if not req.basket:
        raise HTTPException(400, detail="سبد دروس خالی است")

    service = ScheduleService(db)
    try:
        result = service.process(req.basket)
        # result شامل: assigned, unassigned, all
        return result
    except Exception as e:
        logger.error(f"خطا در زمان‌بندی: {e}", exc_info=True)
        raise HTTPException(400, detail=f"خطا در زمان‌بندی استاد و درس: {str(e)}")


@router.post("/schedule/manual", status_code=status.HTTP_200_OK)
def manual_assign_instructors(req: ManualAssignRequest, db: Session = Depends(get_db)):
    """
    تخصیص دستی استاد برای کلاس‌های بدون استاد (مرحله دوم)

    ورودی: لیستی از آیتم‌های تخصیص دستی با فیلدهای:
        - course_name, group_number, level, term: شناسه کلاس
        - instructor_code: کد استاد جدید
        - day, start, end: زمان جدید
    """
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