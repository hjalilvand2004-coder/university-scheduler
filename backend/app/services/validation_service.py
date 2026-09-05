# backend/app/services/validation_service.py
import logging
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
import yaml
import os

from app.models.schedule import ScheduledClass
from app.models.course import OfferedCourse
from app.models.instructor import Instructor
from app.models.room import Room

logger = logging.getLogger(__name__)

# ---------- کلاس‌های کمکی ----------
class ValidationResult:
    """نتیجه نهایی اعتبارسنجی"""
    def __init__(self, is_valid: bool, errors: List[str] = None,
                 warnings: List[str] = None, score: float = 0.0,
                 details: Dict = None):
        self.is_valid = is_valid
        self.errors = errors or []
        self.warnings = warnings or []
        self.score = score
        self.details = details or {}

    def to_dict(self) -> Dict:
        return {
            "is_valid": self.is_valid,
            "errors": self.errors,
            "warnings": self.warnings,
            "score": self.score,
            "details": self.details
        }


class ConstraintResult:
    """نتیجه بررسی یک محدودیت خاص"""
    def __init__(self, is_met: bool, message: str = "", details: Dict = None):
        self.is_met = is_met
        self.message = message
        self.details = details or {}


# ---------- سرویس اصلی ----------
class ValidationService:
    def __init__(self, db: Session):
        self.db = db
        self.constraints = self._load_constraints()
        self.scoring = self._load_scoring()

    # ----- بارگذاری فایل‌های پیکربندی -----
    def _load_constraints(self) -> Dict:
        """بارگذاری constraints.yaml از ریشه پروژه"""
        config_path = os.path.join(
            os.path.dirname(__file__), '..', '..', 'constraints.yaml'
        )
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f) or {}
                # اطمینان از وجود کلیدهای اصلی
                if 'hard_constraints' not in data:
                    data['hard_constraints'] = []
                if 'soft_constraints' not in data:
                    data['soft_constraints'] = []
                return data
        except FileNotFoundError:
            logger.warning("constraints.yaml یافت نشد، از مقادیر پیش‌فرض استفاده می‌شود.")
            return self._default_constraints()
        except Exception as e:
            logger.error(f"خطا در بارگذاری constraints.yaml: {e}")
            return self._default_constraints()

    def _load_scoring(self) -> Dict:
        """بارگذاری scoring.yaml"""
        config_path = os.path.join(
            os.path.dirname(__file__), '..', '..', 'scoring.yaml'
        )
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                return yaml.safe_load(f) or {}
        except Exception as e:
            logger.error(f"خطا در بارگذاری scoring.yaml: {e}")
            return {}

    def _default_constraints(self) -> Dict:
        """مقادیر پیش‌فرض برای محدودیت‌ها"""
        return {
            "hard_constraints": [
                "no_instructor_conflict",
                "no_room_conflict",
                "room_capacity_enough",
                "instructor_availability"
            ],
            "soft_constraints": [
                "preferred_time_slots",
                "minimize_gaps",
                "balance_workload"
            ]
        }

    # ----- متد اصلی اعتبارسنجی -----
    def validate_all(self, schedule_data: Dict) -> ValidationResult:
        """
        اجرای تمام اعتبارسنجی‌ها بر اساس constraints.yaml

        :param schedule_data: دیکشنری شامل schedule_id یا class_ids
        """
        errors = []
        warnings = []
        details = {}

        # استخراج لیست کلاس‌ها از ورودی
        classes = self._extract_classes(schedule_data)
        if not classes:
            return ValidationResult(
                is_valid=False,
                errors=["هیچ کلاسی برای اعتبارسنجی یافت نشد"],
                score=0
            )

        # ۱. بررسی محدودیت‌های سخت
        hard_list = self.constraints.get('hard_constraints', [])
        for constraint_name in hard_list:
            method_name = f"_validate_{constraint_name}"
            if hasattr(self, method_name):
                result = getattr(self, method_name)(classes)
                if not result.is_met:
                    errors.append(f"[{constraint_name}] {result.message}")
                    details[f"hard_{constraint_name}"] = result.details

        # ۲. بررسی محدودیت‌های نرم (اخطار)
        soft_list = self.constraints.get('soft_constraints', [])
        for constraint_name in soft_list:
            method_name = f"_check_{constraint_name}"
            if hasattr(self, method_name):
                result = getattr(self, method_name)(classes)
                if not result.is_met:
                    warnings.append(f"[{constraint_name}] {result.message}")
                    details[f"soft_{constraint_name}"] = result.details

        # ۳. تشخیص تعارضات اضافی (استاد، اتاق، دانشجو)
        conflict_result = self.detect_conflicts(classes)
        details['conflicts'] = conflict_result
        if conflict_result['total'] > 0:
            errors.append(f"تعداد {conflict_result['total']} تعارض در برنامه وجود دارد.")

        # ۴. محاسبه امتیاز نهایی
        score = self._calculate_score(classes, details)

        is_valid = (len(errors) == 0)

        return ValidationResult(
            is_valid=is_valid,
            errors=errors,
            warnings=warnings,
            score=score,
            details=details
        )

    # ----- استخراج داده از ورودی -----
    def _extract_classes(self, schedule_data: Dict) -> List[ScheduledClass]:
        """تبدیل ورودی به لیست کلاس‌های دیتابیس"""
        if 'schedule_id' in schedule_data:
            schedule_id = schedule_data['schedule_id']
            return self.db.query(ScheduledClass).filter(
                ScheduledClass.schedule_version_id == schedule_id
            ).all()
        elif 'class_ids' in schedule_data:
            class_ids = schedule_data['class_ids']
            return self.db.query(ScheduledClass).filter(
                ScheduledClass.id.in_(class_ids)
            ).all()
        else:
            return []

    # ----- تشخیص تعارضات -----
    def detect_conflicts(self, classes: List[ScheduledClass]) -> Dict:
        """
        تشخیص تعارضات استاد، اتاق و دانشجو
        بازگشت دیکشنری شامل تعداد و جزئیات
        """
        conflicts = {
            'instructor': [],
            'room': [],
            'student': []
        }

        # گروه‌بندی بر اساس (day, start_time)
        time_groups = {}
        for cls in classes:
            key = f"{cls.day}_{cls.start_time}"
            if key not in time_groups:
                time_groups[key] = []
            time_groups[key].append(cls)

        for key, group in time_groups.items():
            # تعارض استاد
            instructor_ids = [c.instructor_id for c in group]
            if len(set(instructor_ids)) < len(instructor_ids):
                conflicts['instructor'].append({
                    'time': key,
                    'instructors': list(set(instructor_ids)),
                    'class_ids': [c.id for c in group]
                })

            # تعارض اتاق
            room_ids = [c.room_id for c in group]
            if len(set(room_ids)) < len(room_ids):
                conflicts['room'].append({
                    'time': key,
                    'rooms': list(set(room_ids)),
                    'class_ids': [c.id for c in group]
                })

            # تعارض دانشجو (در صورت وجود اطلاعات دانشجو – فعلاً غیرفعال)
            # ...

        total = len(conflicts['instructor']) + len(conflicts['room']) + len(conflicts['student'])
        return {
            'total': total,
            'details': conflicts
        }

    # ----- متدهای اعتبارسنجی محدودیت‌های سخت -----

    def _validate_no_instructor_conflict(self, classes: List[ScheduledClass]) -> ConstraintResult:
        """بررسی عدم تداخل استاد"""
        conflicts = self._find_conflicts(classes, 'instructor_id')
        if conflicts:
            return ConstraintResult(
                is_met=False,
                message=f"تداخل استاد در {len(conflicts)} بازه زمانی",
                details={'conflicts': conflicts}
            )
        return ConstraintResult(is_met=True, message="هیچ تداخل استادی وجود ندارد")

    def _validate_no_room_conflict(self, classes: List[ScheduledClass]) -> ConstraintResult:
        """بررسی عدم تداخل اتاق"""
        conflicts = self._find_conflicts(classes, 'room_id')
        if conflicts:
            return ConstraintResult(
                is_met=False,
                message=f"تداخل اتاق در {len(conflicts)} بازه زمانی",
                details={'conflicts': conflicts}
            )
        return ConstraintResult(is_met=True, message="هیچ تداخل اتاقی وجود ندارد")

    def _validate_room_capacity_enough(self, classes: List[ScheduledClass]) -> ConstraintResult:
        """بررسی ظرفیت اتاق برای هر کلاس"""
        insufficient = []
        for cls in classes:
            room = self.db.query(Room).filter(Room.id == cls.room_id).first()
            if room:
                # تعداد دانشجویان مورد انتظار (از OfferedCourse یا پیش‌فرض)
                offered = self.db.query(OfferedCourse).filter(
                    OfferedCourse.id == cls.offered_course_id
                ).first()
                expected = getattr(offered, 'expected_enrollment', 30) if offered else 30
                if room.capacity < expected:
                    insufficient.append({
                        'class_id': cls.id,
                        'room': room.name,
                        'capacity': room.capacity,
                        'expected': expected
                    })
        if insufficient:
            return ConstraintResult(
                is_met=False,
                message=f"{len(insufficient)} کلاس ظرفیت کافی ندارند",
                details={'insufficient': insufficient}
            )
        return ConstraintResult(is_met=True, message="همه کلاس‌ها ظرفیت کافی دارند")

    def _validate_instructor_availability(self, classes: List[ScheduledClass]) -> ConstraintResult:
        """بررسی در دسترس بودن استاد (زمان‌های غیرمجاز)"""
        unavailable = []
        for cls in classes:
            instructor = self.db.query(Instructor).filter(
                Instructor.id == cls.instructor_id
            ).first()
            if instructor:
                # فرض: استاد نمی‌تواند جمعه‌ها یا بعد از ۱۸ تدریس کند
                if cls.day == 'Friday' or cls.start_time > 18:
                    unavailable.append({
                        'class_id': cls.id,
                        'instructor': instructor.name,
                        'day': cls.day,
                        'start_time': cls.start_time
                    })
        if unavailable:
            return ConstraintResult(
                is_met=False,
                message=f"{len(unavailable)} کلاس در زمان غیرمجاز استاد",
                details={'unavailable': unavailable}
            )
        return ConstraintResult(is_met=True, message="همه استادان در زمان مجاز تدریس می‌کنند")

    # ----- متدهای بررسی محدودیت‌های نرم -----

    def _check_preferred_time_slots(self, classes: List[ScheduledClass]) -> ConstraintResult:
        """بررسی تطابق زمان با ترجیحات استاد"""
        not_preferred = []
        for cls in classes:
            instructor = self.db.query(Instructor).filter(
                Instructor.id == cls.instructor_id
            ).first()
            if instructor and hasattr(instructor, 'preferred_time_slots'):
                preferred = instructor.preferred_time_slots or {}
                day = cls.day
                time = cls.start_time
                # اگر ترجیح برای این روز تعریف شده و زمان در لیست نیست
                if day in preferred and time not in preferred[day]:
                    not_preferred.append({
                        'class_id': cls.id,
                        'instructor': instructor.name,
                        'day': day,
                        'time': time,
                        'preferred': preferred.get(day, [])
                    })
        if not_preferred:
            return ConstraintResult(
                is_met=False,
                message=f"{len(not_preferred)} کلاس در زمان غیرترجیحی استاد",
                details={'not_preferred': not_preferred}
            )
        return ConstraintResult(is_met=True, message="همه کلاس‌ها در زمان ترجیحی تشکیل شده‌اند")

    def _check_minimize_gaps(self, classes: List[ScheduledClass]) -> ConstraintResult:
        """بررسی شکاف‌های زمانی بزرگ (بیشتر از ۲ ساعت) برای هر استاد"""
        gaps = []
        # گروه‌بندی بر اساس استاد و روز
        for instructor_id in set(c.instructor_id for c in classes):
            for day in set(c.day for c in classes):
                times = sorted([
                    c.start_time for c in classes
                    if c.instructor_id == instructor_id and c.day == day
                ])
                if len(times) > 1:
                    for i in range(len(times) - 1):
                        gap = times[i+1] - times[i]
                        if gap > 2:
                            gaps.append({
                                'instructor': instructor_id,
                                'day': day,
                                'gap_hours': gap,
                                'between': (times[i], times[i+1])
                            })
        if gaps:
            return ConstraintResult(
                is_met=False,
                message=f"{len(gaps)} شکاف بزرگتر از ۲ ساعت شناسایی شد",
                details={'gaps': gaps}
            )
        return ConstraintResult(is_met=True, message="شکاف‌های زمانی مناسب هستند")

    def _check_balance_workload(self, classes: List[ScheduledClass]) -> ConstraintResult:
        """بررسی توزیع متوازن بار کاری اساتید (تفاوت کمتر از ۶ ساعت)"""
        workload = {}
        for cls in classes:
            hours = getattr(cls, 'hours', 3) or 3
            workload[cls.instructor_id] = workload.get(cls.instructor_id, 0) + hours

        if not workload:
            return ConstraintResult(is_met=True, message="هیچ استادی وجود ندارد")

        max_load = max(workload.values())
        min_load = min(workload.values())
        if max_load - min_load > 6:
            return ConstraintResult(
                is_met=False,
                message=f"بار کاری اساتید نامتوازن (بیشترین {max_load}، کمترین {min_load})",
                details={'workload': workload}
            )
        return ConstraintResult(is_met=True, message="بار کاری اساتید متوازن است")

    # ----- متدهای کمکی -----

    def _find_conflicts(self, classes: List[ScheduledClass], field: str) -> List[Dict]:
        """یافتن تداخل‌ها بر اساس فیلد (instructor_id یا room_id) در زمان‌های مشترک"""
        conflicts = []
        time_groups = {}
        for cls in classes:
            key = f"{cls.day}_{cls.start_time}"
            time_groups.setdefault(key, []).append(cls)

        for key, group in time_groups.items():
            ids = [getattr(c, field) for c in group]
            if len(set(ids)) < len(ids):
                conflicts.append({
                    'time': key,
                    'ids': list(set(ids)),
                    'class_ids': [c.id for c in group]
                })
        return conflicts

    def _calculate_score(self, classes: List[ScheduledClass], details: Dict) -> float:
        """محاسبه امتیاز بر اساس scoring.yaml"""
        weights = self.scoring.get('weights', {})
        base_score = self.scoring.get('scoring', {}).get('base_score', 1000)
        penalty = self.scoring.get('scoring', {}).get('penalty_per_violation', 50)

        score = base_score

        # کسر به ازای هر خطا (سخت)
        errors_count = sum(1 for k in details if k.startswith('hard_'))
        score -= errors_count * penalty

        # کسر به ازای هر هشدار (نرم)
        warnings_count = sum(1 for k in details if k.startswith('soft_'))
        score -= warnings_count * (penalty // 2)

        # کسر به ازای تعارضات
        conflicts = details.get('conflicts', {}).get('total', 0)
        score -= conflicts * (penalty // 3)

        return max(0, int(score))