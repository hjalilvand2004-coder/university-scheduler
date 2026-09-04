from sqlalchemy.orm import Session
from typing import List, Dict, Any, Optional
import logging
from collections import defaultdict

from app.models.schedule import ScheduledClass
from app.models.room import Room

logger = logging.getLogger(__name__)


class RoomAllocationService:
    """
    سرویس تخصیص اتاق به کلاس‌های زمان‌بندی شده
    با استفاده از روش اکتشافی (بدون ایجاد تداخل)
    """

    def __init__(self, db: Session):
        self.db = db

    # ============================================================
    # متد اصلی پردازش
    # ============================================================
    def process(self, schedule: List[Dict], scenario_id: Optional[int] = None) -> List[Dict]:
        """
        ورودی: لیست کلاس‌های زمان‌بندی شده (بدون اتاق)
        خروجی: لیست کلاس‌ها با اتاق اختصاص‌یافته (بدون تداخل)
        """
        if not schedule:
            logger.warning("برنامه زمان‌بندی خالی است.")
            return []

        logger.info(f"📥 دریافت {len(schedule)} کلاس برای تخصیص اتاق.")
        if schedule:
            sample = schedule[0]
            logger.info(f"📌 نمونه کلاس اول: {sample}")
            cap = sample.get('estimated_capacity')
            logger.info(f"📊 ظرفیت کلاس اول: {cap} (نوع: {type(cap)})")
            class_type = sample.get('type')
            logger.info(f"📌 نوع کلاس اول: {class_type}")

        rooms = self.db.query(Room).all()
        if not rooms:
            logger.warning("⚠️ هیچ اتاقی در دیتابیس موجود نیست.")
            return self._mark_no_room(schedule)

        logger.info(f"🏢 تعداد اتاق‌های موجود: {len(rooms)}")
        if rooms:
            sample_room = rooms[0]
            room_type_val = getattr(sample_room, 'room_type', 'نامشخص')
            logger.info(f"📌 نمونه اتاق اول: {sample_room.name} (ظرفیت: {sample_room.capacity}, نوع: {room_type_val})")

        logger.info("🔄 استفاده از روش اکتشافی (هیوریستیک) برای تخصیص بدون تداخل...")
        return self._heuristic_allocate(schedule, rooms, scenario_id)

    def _mark_no_room(self, schedule: List[Dict]) -> List[Dict]:
        """تمام کلاس‌ها را بدون اتاق علامت‌گذاری می‌کند."""
        result = []
        for item in schedule:
            new_item = item.copy()
            new_item["room_name"] = "بدون اتاق"
            new_item["room_code"] = None
            new_item["capacity"] = None
            new_item["room_id"] = None
            result.append(new_item)
        return result

    def _heuristic_allocate(self, schedule: List[Dict], rooms: List[Room], scenario_id: Optional[int] = None) -> List[Dict]:
        """
        روش اکتشافی برای تخصیص اتاق بدون تداخل:
        - ابتدا اشغال‌های موجود در دیتابیس (برای سناریوی داده‌شده) بارگذاری می‌شوند.
        - مرتب‌سازی اتاق‌ها بر اساس ظرفیت (صعودی)
        - برای هر کلاس، اولین اتاق با ظرفیت کافی، نوع مناسب (در صورت وجود) و بدون تداخل زمانی انتخاب می‌شود
        - اگر چنین اتاقی یافت نشد، کلاس بدون اتاق می‌ماند
        """
        # ساختار جدید: day -> room_id -> list of (start, end)
        room_occupancy = defaultdict(lambda: defaultdict(list))

        # ---- بارگذاری اشغال‌های موجود از دیتابیس (برای جلوگیری از تداخل با کلاس‌های قبلی) ----
        if scenario_id is not None:
            schedule_ids = {item.get("id") for item in schedule if item.get("id")}
            existing_classes = self.db.query(ScheduledClass).filter(
                ScheduledClass.scenario_id == scenario_id,
                ScheduledClass.room_id.isnot(None)
            ).all()
            loaded_count = 0
            for cls in existing_classes:
                # کلاس‌هایی که در لیست ورودی هستند را از اشغال اولیه حذف می‌کنیم تا تداخل با خودشان ایجاد نشود
                if cls.id in schedule_ids:
                    continue
                day = cls.day
                start = cls.start_time
                end = cls.end_time
                room_id = cls.room_id
                if day is not None and start is not None and end is not None and room_id is not None:
                    room_occupancy[day][room_id].append((start, end))
                    loaded_count += 1
            logger.info(f"📂 {loaded_count} اشغال قبلی از دیتابیس بارگذاری شد (به جز کلاس‌های موجود در ورودی).")

        # مرتب‌سازی اتاق‌ها بر اساس ظرفیت (صعودی)
        sorted_rooms = sorted(rooms, key=lambda r: r.capacity)

        result = []
        total_allocated = 0

        for idx, item in enumerate(schedule):
            day = item.get("day")
            start = item.get("start")
            end = item.get("end")
            required_capacity = item.get("estimated_capacity", 30)
            class_type = item.get("type")  # ممکن است None باشد
            course_name = item.get("course_name", "نامشخص")
            group = item.get("group_number", "?")

            # تبدیل زمان به عدد دقایق برای مقایسه دقیق‌تر
            def time_to_minutes(t):
                if not t:
                    return 0
                try:
                    parts = t.split(":")
                    return int(parts[0]) * 60 + int(parts[1])
                except:
                    return 0

            start_min = time_to_minutes(start)
            end_min = time_to_minutes(end)

            assigned_room = None
            log_details = []

            # جستجوی اتاق مناسب (با ظرفیت، نوع و بدون تداخل)
            for room in sorted_rooms:
                # بررسی ظرفیت
                if room.capacity < required_capacity:
                    log_details.append(f"❌ ظرفیت ناکافی: {room.name} ({room.capacity} < {required_capacity})")
                    continue

                # بررسی نوع (در صورت وجود)
                if class_type is not None:
                    room_type = getattr(room, 'room_type', None)
                    if room_type != class_type:
                        log_details.append(f"❌ نوع نامناسب: {room.name} (نوع {room_type} != {class_type})")
                        continue

                # بررسی تداخل در همان روز و برای همین اتاق
                occupancies = room_occupancy[day].get(room.id, [])
                conflict = False
                for (s, e) in occupancies:
                    s_min = time_to_minutes(s)
                    e_min = time_to_minutes(e)
                    # بررسی همپوشانی: تداخل اگر پایان یکی <= شروع دیگری نباشد
                    if not (end_min <= s_min or start_min >= e_min):
                        conflict = True
                        log_details.append(f"❌ تداخل زمانی: {room.name} با کلاس دیگری در بازه {s}-{e} تداخل دارد.")
                        break

                if not conflict:
                    assigned_room = room
                    # ثبت اشغال جدید
                    room_occupancy[day][room.id].append((start, end))
                    log_details.append(f"✅ انتخاب شد: {room.name} (ظرفیت {room.capacity})")
                    break
                # اگر تداخل داشت، ادامه می‌دهیم تا اتاق بعدی بررسی شود

            # ساخت آیتم نهایی
            new_item = item.copy()
            if assigned_room:
                new_item["room_name"] = assigned_room.name
                new_item["room_code"] = assigned_room.code
                new_item["capacity"] = assigned_room.capacity
                new_item["room_id"] = assigned_room.id
                total_allocated += 1
                logger.info(f"✅ کلاس {idx} - {course_name} گروه {group} -> اتاق {assigned_room.name} (ظرفیت {assigned_room.capacity})")
            else:
                new_item["room_name"] = "بدون اتاق"
                new_item["room_code"] = None
                new_item["capacity"] = None
                new_item["room_id"] = None
                reason = f"نیاز: {required_capacity} دانشجو"
                if class_type is not None:
                    reason += f", نوع: {class_type}"
                logger.warning(f"❌ کلاس {idx} - {course_name} گروه {group} اتاق مناسب نیافت ({reason})")
                # لاگ جزئیات رد شدن اتاق‌ها
                if log_details:
                    logger.warning(f"   جزئیات بررسی اتاق‌ها: {' | '.join(log_details)}")
                else:
                    logger.warning("   هیچ اتاقی برای بررسی وجود نداشت (ظرفیت یا نوع همه نامناسب بود)")

            result.append(new_item)

        logger.info(f"✅ تخصیص اکتشافی: {total_allocated} از {len(result)} کلاس اتاق گرفتند (بدون تداخل).")
        return result

    # ============================================================
    # متدهای ذخیره‌سازی و بازیابی از دیتابیس
    # ============================================================

    def save_allocated_classes(
        self,
        classes_with_rooms: List[Dict],
        workflow_id: int,
        semester: str,
        year: str = "1403"
    ) -> List[ScheduledClass]:
        """
        ذخیره‌سازی کلاس‌های تخصیص‌یافته با اتاق در دیتابیس
        به‌روزرسانی رکوردهای موجود بر اساس id و scenario_id
        """
        saved_classes = []
        for cls_data in classes_with_rooms:
            class_id = cls_data.get("id")
            if class_id is None:
                logger.warning(f"کلاس بدون id: {cls_data.get('course_name')} - از آن صرف‌نظر شد.")
                continue

            existing = self.db.query(ScheduledClass).filter(
                ScheduledClass.id == class_id,
                ScheduledClass.scenario_id == workflow_id
            ).first()

            if existing:
                existing.room_id = cls_data.get("room_id")
                existing.room_name = cls_data.get("room_name")
                existing.room_capacity = cls_data.get("capacity")
                saved_classes.append(existing)
            else:
                logger.warning(f"کلاس با id {class_id} در scenario {workflow_id} یافت نشد. ایجاد نشد.")
                continue

        self.db.commit()
        logger.info(f"✅ {len(saved_classes)} کلاس با اتاق در دیتابیس به‌روزرسانی شد.")
        return saved_classes

    def get_allocated_classes(self, workflow_id: int) -> List[Dict]:
        """
        دریافت کلاس‌های تخصیص‌یافته با اتاق برای یک workflow
        """
        classes = self.db.query(ScheduledClass).filter(
            ScheduledClass.scenario_id == workflow_id
        ).all()

        result = []
        for cls in classes:
            result.append({
                "id": cls.id,
                "course_code": cls.course_code,
                "course_name": cls.course_title,
                "group_number": cls.group_number,
                "instructor_name": cls.instructor_name,
                "room_name": cls.room_name,
                "room_id": cls.room_id,
                "capacity": cls.room_capacity,
                "day": cls.day,
                "start": cls.start_time,
                "end": cls.end_time,
                "predicted_students": cls.predicted_students,
                "scenario_id": cls.scenario_id,
            })
        return result

    def update_room_for_class(self, class_id: int, room_id: int) -> ScheduledClass:
        """
        به‌روزرسانی اتاق یک کلاس خاص (با بررسی تداخل)
        """
        scheduled_class = self.db.query(ScheduledClass).filter(
            ScheduledClass.id == class_id
        ).first()
        if not scheduled_class:
            raise ValueError(f"کلاس با شناسه {class_id} یافت نشد")

        room = self.db.query(Room).filter(Room.id == room_id).first()
        if not room:
            raise ValueError(f"اتاق با شناسه {room_id} یافت نشد")

        # بررسی تداخل زمانی با سایر کلاس‌ها
        conflicting = self.db.query(ScheduledClass).filter(
            ScheduledClass.room_id == room_id,
            ScheduledClass.day == scheduled_class.day,
            ScheduledClass.start_time < scheduled_class.end_time,
            ScheduledClass.end_time > scheduled_class.start_time,
            ScheduledClass.id != class_id
        ).first()

        if conflicting:
            raise ValueError(
                f"اتاق {room.name} در این زمان توسط کلاس '{conflicting.course_title}' اشغال است."
            )

        scheduled_class.room_id = room_id
        scheduled_class.room_name = room.name
        scheduled_class.room_capacity = room.capacity
        self.db.commit()
        self.db.refresh(scheduled_class)

        return scheduled_class