from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Dict, Any
import logging

from app.core.database import get_db
from app.services.room_allocation_service import RoomAllocationService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/room-allocation", tags=["Room Allocation"])


@router.post("/process")
async def process_room_allocation(
    payload: Dict[str, Any],
    db: Session = Depends(get_db)
):
    """
    پردازش تخصیص اتاق برای کلاس‌های زمان‌بندی شده
    """
    logger.info("=" * 60)
    logger.info("🚀 شروع تخصیص اتاق (مسیر /api/room-allocation/process)")

    # ---- لاگ payload ----
    logger.info(f"📦 Payload keys: {list(payload.keys())}")
    schedule = payload.get("schedule")
    scenario_id = payload.get("scenario_id")
    semester = payload.get("semester")
    year = payload.get("year", "1403")

    logger.info(f"📌 scenario_id: {scenario_id}, semester: {semester}, year: {year}")

    # اعتبارسنجی ورودی
    if not schedule:
        logger.error("❌ schedule خالی است یا وجود ندارد")
        raise HTTPException(400, "اطلاعات ناقص: schedule الزامی است")
    if not scenario_id:
        logger.error("❌ scenario_id خالی است یا وجود ندارد")
        raise HTTPException(400, "اطلاعات ناقص: scenario_id الزامی است")
    if not semester:
        logger.error("❌ semester خالی است یا وجود ندارد")
        raise HTTPException(400, "اطلاعات ناقص: semester الزامی است")

    logger.info(f"📊 تعداد کلاس‌های ورودی: {len(schedule)}")

    # لاگ نمونه‌های اول و آخر برای بررسی
    if schedule:
        logger.info(f"📌 نمونه کلاس اول: {schedule[0]}")
        cap = schedule[0].get("estimated_capacity")
        logger.info(f"📊 ظرفیت کلاس اول: {cap} (نوع: {type(cap)})")
        if cap is None or cap == 0:
            logger.warning("⚠️ ظرفیت کلاس اول صفر یا None است! ممکن است باعث عدم تخصیص شود.")

        if len(schedule) > 1:
            logger.info(f"📌 نمونه کلاس آخر: {schedule[-1]}")

    # بررسی وجود اتاق‌ها در دیتابیس (قبل از فراخوانی سرویس)
    from app.models.room import Room
    rooms_count = db.query(Room).count()
    logger.info(f"🏢 تعداد اتاق‌های موجود در دیتابیس: {rooms_count}")
    if rooms_count == 0:
        logger.warning("⚠️ هیچ اتاقی در دیتابیس ثبت نشده است. تخصیص امکان‌پذیر نیست.")

    try:
        service = RoomAllocationService(db)
        logger.info("🔄 در حال اجرای تخصیص اتاق...")

        # ارسال scenario_id به سرویس برای بارگذاری اشغال‌های قبلی
        allocated = service.process(schedule, scenario_id)

        logger.info(f"✅ تخصیص انجام شد. تعداد کلاس‌های تخصیص‌یافته: {len(allocated)}")

        # ذخیره در دیتابیس
        logger.info("💾 در حال ذخیره‌سازی در دیتابیس...")
        saved = service.save_allocated_classes(allocated, scenario_id, semester, year)
        logger.info(f"✅ {len(saved)} کلاس در دیتابیس ذخیره شد.")

        # ساختن خروجی
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

        # آمار تخصیص
        allocated_count = sum(1 for r in result if r.get("room_name") and r["room_name"] != "بدون اتاق")
        logger.info(f"📊 آمار نهایی: {allocated_count} از {len(result)} کلاس اتاق دریافت کردند.")
        if allocated_count == 0:
            logger.warning("⚠️ هیچ کلاسی اتاق دریافت نکرد! بررسی کنید که آیا اتاق‌ها با ظرفیت کلاس‌ها مطابقت دارند.")

        # لاگ چند نمونه از خروجی برای بررسی تداخل
        if result:
            logger.info("📌 نمونه خروجی (۵ کلاس اول):")
            for i, r in enumerate(result[:5]):
                logger.info(f"   {i+1}: {r['course_name']} - {r['room_name']} ({r['day']} {r['start']}-{r['end']})")

        logger.info("=" * 60)
        return {"data": result}

    except Exception as e:
        logger.error(f"❌ خطا در تخصیص اتاق: {str(e)}", exc_info=True)
        raise HTTPException(500, f"خطا در تخصیص اتاق: {str(e)}")


@router.get("/{scenario_id}")
async def get_allocated_classes(scenario_id: int, db: Session = Depends(get_db)):
    """
    دریافت کلاس‌های تخصیص‌یافته با اتاق برای یک scenario_id مشخص
    """
    logger.info(f"📥 دریافت کلاس‌های تخصیص‌یافته برای scenario_id: {scenario_id}")
    service = RoomAllocationService(db)
    result = service.get_allocated_classes(scenario_id)
    logger.info(f"✅ {len(result)} کلاس برای scenario_id {scenario_id} یافت شد.")
    return result


@router.put("/class/{class_id}/room")
async def update_class_room(
    class_id: int,
    payload: Dict[str, int],
    db: Session = Depends(get_db)
):
    """
    به‌روزرسانی اتاق یک کلاس خاص
    """
    room_id = payload.get("room_id")
    if not room_id:
        logger.error("❌ room_id در payload موجود نیست")
        raise HTTPException(400, "room_id الزامی است")

    logger.info(f"🔄 به‌روزرسانی کلاس {class_id} با اتاق {room_id}")
    service = RoomAllocationService(db)
    try:
        updated = service.update_room_for_class(class_id, room_id)
        logger.info(f"✅ کلاس {class_id} به اتاق {updated.room_name} (ظرفیت {updated.room_capacity}) تخصیص یافت.")
        return {
            "id": updated.id,
            "room_name": updated.room_name,
            "room_capacity": updated.room_capacity,
        }
    except ValueError as e:
        logger.warning(f"⚠️ خطا در به‌روزرسانی: {str(e)}")
        raise HTTPException(400, str(e))
    except Exception as e:
        logger.error(f"❌ خطای غیرمنتظره: {str(e)}", exc_info=True)
        raise HTTPException(500, f"خطای داخلی: {str(e)}")