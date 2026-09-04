# app/services/schedule/instructor_loader.py
# بارگذاری اطلاعات اساتید از دیتابیس (مرحله ۲).
import logging
from collections import defaultdict
from typing import Dict, Tuple
from sqlalchemy.orm import Session

from app.models.instructor import Instructor
from app.models.teaching_preference import TeachingPreference
from app.models.time_preference import TimePreference
from app.utils.helpers import normalize_instructor_code, normalize_code
# استفاده از normalize_day و DAY_MAP از slot_times (به جای constants)
from app.services.schedule.slot_times import normalize_day, DAY_MAP
# در صورت نیاز به COOPERATION_PRIORITY، آن را از جای دیگر وارد کنید
from app.utils.constants import COOPERATION_PRIORITY

logger = logging.getLogger(__name__)

class InstructorLoader:
    def __init__(self, db: Session):
        self.db = db

    def load(self) -> Tuple[Dict, Dict, Dict]:
        instructors = self.db.query(Instructor).all()
        instructor_data = {
            'codes': set(),
            'names': {},
            'coops': {},
            'max_units': {},
        }
        for inst in instructors:
            norm_code = normalize_instructor_code(inst.code)
            instructor_data['codes'].add(norm_code)
            instructor_data['names'][norm_code] = inst.name
            instructor_data['coops'][norm_code] = inst.cooperation_type or ""
            instructor_data['max_units'][norm_code] = inst.max_teaching_units or 999

        teaching_prefs = defaultdict(list)
        for pref in self.db.query(TeachingPreference).all():
            if not pref.unique_course_code or not pref.instructor_code:
                continue
            course_code = normalize_code(pref.unique_course_code)
            inst_code = normalize_instructor_code(pref.instructor_code)
            if inst_code not in instructor_data['codes']:
                continue
            priority = getattr(pref, 'priority', 999)
            teaching_prefs[course_code].append((inst_code, priority))

        for code, inst_list in teaching_prefs.items():
            inst_list.sort(
                key=lambda x: (x[1], -COOPERATION_PRIORITY.get(instructor_data['coops'].get(x[0], ""), 0))
            )
            teaching_prefs[code] = [inst[0] for inst in inst_list]

        time_prefs = defaultdict(list)
        for pref in self.db.query(TimePreference).all():
            if not pref.instructor_code:
                continue
            inst_code = normalize_instructor_code(pref.instructor_code)
            if inst_code not in instructor_data['codes']:
                continue
            day_norm = normalize_day(pref.day)
            day_num = DAY_MAP.get(day_norm)
            if day_num is None:
                logger.warning(f"روز '{pref.day}' (نرمال‌شده: '{day_norm}') برای استاد {inst_code} شناسایی نشد.")
                continue
            if pref.start_time and pref.end_time:
                priority = getattr(pref, 'priority', 999)
                time_prefs[inst_code].append((day_num, pref.start_time, pref.end_time, priority))

        for inst, time_list in time_prefs.items():
            time_list.sort(key=lambda x: x[3])

        logger.info(f"📚 مطلوبیت تدریس: {len(teaching_prefs)} درس")
        logger.info(f"⏰ مطلوبیت زمان: {len(time_prefs)} استاد")

        return instructor_data, dict(teaching_prefs), dict(time_prefs)