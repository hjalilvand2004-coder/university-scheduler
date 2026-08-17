# app/services/room_allocation_service.py

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
    با استفاده از روش اکتشافی (در صورت عدم دسترسی به OR-Tools، می‌توان از هیوریستیک استفاده کرد)
    """

    def __init__(self, db: Session):
        self.db = db

    # ============================================================
    # متد اصلی پردازش (همانند قبل)
    # ============================================================
    def process(self, schedule: List[Dict]) -> List[Dict]:
        """
        ورودی: لیست کلاس‌های زمان‌بندی شده (بدون اتاق)
        خروجی: لیست کلاس‌ها با اتاق اختصاص‌یافته
        """
        if not schedule:
            return []

        rooms = self.db.query(Room).all()
        if not rooms:
            logger.warning("هیچ اتاقی در دیتابیس موجود نیست.")
            return schedule

        try:
            from app.optimization.cp_sat_solver import solve_room_allocation
            return solve_room_allocation(schedule, rooms)
        except (ImportError, AttributeError):
            logger.warning("تابع solve_room_allocation در دسترس نیست، از روش اکتشافی استفاده می‌شود.")
            return self._heuristic_allocate(schedule, rooms)

    def _heuristic_allocate(self, schedule: List[Dict], rooms: List[Room]) -> List[Dict]:
        """
        روش اکتشافی ساده برای تخصیص اتاق:
        - مرتب‌سازی اتاق‌ها بر اساس ظرفیت
        - برای هر کلاس، اولین اتاق با ظرفیت کافی و بدون تداخل زمانی را انتخاب می‌کند
        """
        sorted_rooms = sorted(rooms, key=lambda r: r.capacity)
        room_occupancy = defaultdict(dict)  # day -> {(start, end): room_id}

        result = []
        for item in schedule:
            day = item.get("day")
            start = item.get("start")
            end = item.get("end")
            required_capacity = item.get("estimated_capacity", 30)

            assigned_room = None
            for room in sorted_rooms:
                if room.capacity < required_capacity:
                    continue
                day_occ = room_occupancy.get(day, {})
                conflict = any(s < end and e > start and r_id == room.id for (s, e), r_id in day_occ.items())
                if not conflict:
                    assigned_room = room
                    day_occ[(start, end)] = room.id
                    room_occupancy[day] = day_occ
                    break

            new_item = item.copy()
            if assigned_room:
                new_item["room_name"] = assigned_room.name
                new_item["room_code"] = assigned_room.code
                new_item["capacity"] = assigned_room.capacity
                new_item["room_id"] = assigned_room.id
            else:
                new_item["room_name"] = "بدون اتاق"
                new_item["room_code"] = None
                new_item["capacity"] = None
                new_item["room_id"] = None
                logger.warning(f"کلاس {item.get('course_name')} گروه {item.get('group_number')} اتاق مناسب نیافت.")

            result.append(new_item)
        return result

    # ============================================================
    # متدهای جدید برای ذخیره‌سازی و بازیابی از دیتابیس
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

        Args:
            classes_with_rooms: لیست کلاس‌های دارای اتاق (خروجی متد process)
            workflow_id: شناسه workflow
            semester: نیمسال
            year: سال

        Returns:
            لیست مدل‌های ScheduledClass ذخیره‌شده
        """
        saved_classes = []
        for cls_data in classes_with_rooms:
            # جلوگیری از ذخیره تکراری با بررسی scenario_id و course_code و group_number
            existing = self.db.query(ScheduledClass).filter(
                ScheduledClass.scenario_id == workflow_id,
                ScheduledClass.course_code == cls_data.get("course_code"),
                ScheduledClass.group_number == cls_data.get("group_number")
            ).first()

            if existing:
                # به‌روزرسانی اتاق و سایر اطلاعات
                existing.room_id = cls_data.get("room_id")
                existing.room_name = cls_data.get("room_name")
                existing.room_capacity = cls_data.get("capacity")
                existing.day = cls_data.get("day")
                existing.start_time = cls_data.get("start")
                existing.end_time = cls_data.get("end")
                existing.predicted_students = cls_data.get("estimated_capacity", 0)
                saved_classes.append(existing)
            else:
                new_class = ScheduledClass(
                    course_code=cls_data.get("course_code"),
                    course_title=cls_data.get("course_name"),
                    group_number=cls_data.get("group_number"),
                    instructor_name=cls_data.get("instructor_name"),
                    room_id=cls_data.get("room_id"),
                    room_name=cls_data.get("room_name"),
                    room_capacity=cls_data.get("capacity"),
                    day=cls_data.get("day"),
                    start_time=cls_data.get("start"),
                    end_time=cls_data.get("end"),
                    predicted_students=cls_data.get("estimated_capacity", 0),
                    semester=semester,
                    year=year,
                    scenario_id=workflow_id,
                )
                self.db.add(new_class)
                saved_classes.append(new_class)

        self.db.commit()
        logger.info(f"✅ {len(saved_classes)} کلاس با اتاق در دیتابیس ذخیره شد.")
        return saved_classes

    def get_allocated_classes(self, workflow_id: int) -> List[Dict]:
        """
        دریافت کلاس‌های تخصیص‌یافته با اتاق برای یک workflow

        Args:
            workflow_id: شناسه workflow

        Returns:
            لیست دیکشنری‌های کلاس‌ها با اطلاعات کامل
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
        به‌روزرسانی اتاق یک کلاس خاص

        Args:
            class_id: شناسه کلاس
            room_id: شناسه اتاق جدید

        Returns:
            مدل به‌روز شده
        """
        scheduled_class = self.db.query(ScheduledClass).filter(
            ScheduledClass.id == class_id
        ).first()
        if not scheduled_class:
            raise ValueError(f"کلاس با شناسه {class_id} یافت نشد")

        room = self.db.query(Room).filter(Room.id == room_id).first()
        if not room:
            raise ValueError(f"اتاق با شناسه {room_id} یافت نشد")

        # بررسی تداخل زمانی
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