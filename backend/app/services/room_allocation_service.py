from sqlalchemy.orm import Session
from typing import List, Dict, Any
import logging
from collections import defaultdict

from app.models.room import Room

logger = logging.getLogger(__name__)


class RoomAllocationService:
    """
    سرویس تخصیص اتاق به کلاس‌های زمان‌بندی شده
    با استفاده از روش اکتشافی (در صورت عدم دسترسی به OR-Tools، می‌توان از هیوریستیک استفاده کرد)
    """

    def __init__(self, db: Session):
        self.db = db

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

        # سعی در استفاده از OR-Tools (در صورت وجود)
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