# backend/app/services/validation_service.py
import logging
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from datetime import datetime
import yaml
import os

from app.models.schedule import ScheduledClass
from app.models.course import OfferedCourse, Course
from app.models.instructor import Instructor
from app.models.room import Room
from app.models.term import Term

logger = logging.getLogger(__name__)

class ValidationResult:
    """نتیجه اعتبارسنجی"""
    def __init__(self, is_valid: bool, errors: List[str] = None,
                 warnings: List[str] = None, score: float = 0.0,
                 details: Dict = None):
        self.is_valid = is_valid
        self.errors = errors or []
        self.warnings = warnings or []
        self.score = score
        self.details = details or {}

    def to_dict(self):
        return {
            "is_valid": self.is_valid,
            "errors": self.errors,
            "warnings": self.warnings,
            "score": self.score,
            "details": self.details
        }


class ConstraintResult:
    """نتیجه بررسی یک محدودیت"""
    def __init__(self, is_met: bool, message: str = "", details: Dict = None):
        self.is_met = is_met
        self.message = message
        self.details = details or {}


class ValidationService:
    """
    سرویس اعتبارسنجی جامع برنامه درسی
    """

    def __init__(self, db: Session):
        self.db = db
        self.constraints = self._load_constraints()
        self.scoring = self._load_scoring()

    def _load_constraints(self) -> Dict:
        """بارگذاری فایل constraints.yaml از ریشه پروژه"""
        config_path = os.path.join(
            os.path.dirname(__file__), '..', '..', 'constraints.yaml'
        )
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                return yaml.safe_load(f) or {}
        except FileNotFoundError:
            logger.warning("فایل constraints.yaml یافت نشد، از مقادیر پیش‌فرض استفاده می‌شود.")
            return self._default_constraints()
        except Exception as e:
            logger.error(f"خطا در بارگذاری constraints.yaml: {e}")
            return self._default_constraints()

    def _load_scoring(self) -> Dict:
        """بارگذاری فایل scoring.yaml"""
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
        """مقادیر پیش‌فرض در صورت عدم وجود فایل"""
        return {
            "hard_constraints": [
                "no_instructor_conflict",
                "no_room_conflict",
                "room_capacity_enough",
                "no_student_conflict",
                "instructor_availability"
            ],
            "soft_constraints": [
                "preferred_time_slots",
                "minimize_gaps",
                "balance_workload",
                "department_distribution"
            ]
        }

    def validate_all(self, schedule_data: Dict) -> ValidationResult:
        """
        اجرای تمام اعتبارسنجی‌ها بر اساس constraints.yaml
        :param schedule_data: دیکشنری شامل schedule_id یا list کلاس‌ها
        """
        errors = []
        warnings = []
        details = {}

        # استخراج کلاس‌های برنامه از schedule_data
        classes = self._extract_classes(schedule_data)

        # ۱. بررسی محدودیت‌های سخت
        for constraint_name in self.constraints.get('hard_constraints', []):
            method_name = f"_validate_{constraint_name}"
            if hasattr(self, method_name):
                result = getattr(self, method_name)(classes)
                if not result.is_met:
                    errors.append(f"[{constraint_name}] {result.message}")
                    details[constraint_name] = result.details

        # ۲. بررسی محدودیت‌های نرم (اخطار)
        for constraint_name in self.constraints.get('soft_constraints', []):
            method_name = f"_check_{constraint_name}"
            if hasattr(self, method_name):
                result = getattr(self, method_name)(classes)
                if not result.is_met:
                    warnings.append(f"[{constraint_name}] {result.message}")
                    details[constraint_name] = result.details

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

    def _extract_classes(self, schedule_data: Dict) -> List[ScheduledClass]:
        """استخراج لیست کلاس‌ها از دیتای ورودی"""
        if 'schedule_id' in schedule_data:
            schedule_id = schedule_data['schedule_id']
            classes = self.db.query(ScheduledClass).filter(
                ScheduledClass.schedule_version_id == schedule_id
            ).all()
            return classes
        elif 'classes' in schedule_data:
            # اگر لیست کلاس‌ها به صورت مستقیم داده شده باشد (مثلاً برای تست)
            class_ids = schedule_data['classes']
            return self.db.query(ScheduledClass).filter(
                ScheduledClass.id.in_(class_ids)
            ).all()
        else:
            return []

    def detect_conflicts(self, classes: List[ScheduledClass]) -> Dict:
        """
        تشخیص تعارضات استاد، اتاق و دانشجو
        """
        conflicts = {
            'instructor': [],
            'room': [],
            'student': []
        }

        # گروه‌بندی کلاس‌ها بر اساس زمان (روز، ساعت شروع)
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
                    'classes': [c.id for c in group]
                })

            # تعارض اتاق
            room_ids = [c.room_id for c in group]
            if len(set(room_ids)) < len(room_ids):
                conflicts['room'].append({
                    'time': key,
                    'rooms': list(set(room_ids)),
                    'classes': [c.id for c in group]
                })

            # تعارض دانشجو (در صورت وجود فیلد student_group یا مشابه)
            # در صورت نیاز پیاده‌سازی شود

        total = len(conflicts['instructor']) + len(conflicts['room']) + len(conflicts['student'])
        return {
            'total': total,
            'details': conflicts
        }

    # ---------- متدهای اعتبارسنجی محدودیت‌های سخت ----------

    def _validate_no_instructor_conflict(self, classes: List[ScheduledClass]) -> ConstraintResult:
        """بررسی عدم تداخل زمانی استاد"""
        conflicts = self._find_conflicts(classes, 'instructor_id')
        if conflicts:
            return ConstraintResult(
                is_met=False,
                message=f"تداخل استاد در {len(conflicts)} مورد",
                details={'conflicts': conflicts}
            )
        return ConstraintResult(is_met=True, message="هیچ تداخلی برای استاد وجود ندارد")

    def _validate_no_room_conflict(self, classes: List[ScheduledClass]) -> ConstraintResult:
        """بررسی عدم تداخل زمانی اتاق"""
        conflicts = self._find_conflicts(classes, 'room_id')
        if conflicts:
            return ConstraintResult(
                is_met=False,
                message=f"تداخل اتاق در {len(conflicts)} مورد",
                details={'conflicts': conflicts}
            )
        return ConstraintResult(is_met=True, message="هیچ تداخلی برای اتاق وجود ندارد")

    def _validate_room_capacity_enough(self, classes: List[ScheduledClass]) -> ConstraintResult:
        """بررسی کافی بودن ظرفیت اتاق برای هر کلاس"""
        insufficient = []
        for cls in classes:
            room = self.db.query(Room).filter(Room.id == cls.room_id).first()
            if room:
                enrollment = cls.expected_enrollment or 30
                if room.capacity < enrollment:
                    insufficient.append({
                        'class_id': cls.id,
                        'room': room.name,
                        'capacity': room.capacity,
                        'needed': enrollment
                    })
        if insufficient:
            return ConstraintResult(
                is_met=False,
                message=f"{len(insufficient)} کلاس ظرفیت کافی ندارند",
                details={'insufficient': insufficient}
            )
        return ConstraintResult(is_met=True)

    def _validate_no_student_conflict(self, classes: List[ScheduledClass]) -> ConstraintResult:
        """بررسی عدم تداخل دانشجو (در صورت وجود اطلاعات دانشجو)"""
        # در صورت وجود مدل Student و Enrollment پیاده‌سازی می‌شود
        return ConstraintResult(is_met=True, message="دانشجویی تعریف نشده است")

    def _validate_instructor_availability(self, classes: List[ScheduledClass]) -> ConstraintResult:
        """بررسی در دسترس بودن استاد در زمان کلاس"""
        unavailable = []
        for cls in classes:
            instructor = self.db.query(Instructor).filter(
                Instructor.id == cls.instructor_id
            ).first()
            if instructor:
                # بررسی زمان‌های نامناسب (مثلاً جمعه‌ها یا بعد از ساعت مشخص)
                if cls.day == 'Friday' or cls.start_time > 18:
                    unavailable.append({
                        'class_id': cls.id,
                        'instructor': instructor.name,
                        'day': cls.day,
                        'time': cls.start_time
                    })
        if unavailable:
            return ConstraintResult(
                is_met=False,
                message=f"{len(unavailable)} کلاس در زمان نامناسب استاد تشکیل شده",
                details={'unavailable': unavailable}
            )
        return ConstraintResult(is_met=True)

    # ---------- متدهای بررسی محدودیت‌های نرم ----------

    def _check_preferred_time_slots(self, classes: List[ScheduledClass]) -> ConstraintResult:
        """بررسی ترجیحات زمانی اساتید"""
        not_preferred = []
        for cls in classes:
            instructor = self.db.query(Instructor).filter(
                Instructor.id == cls.instructor_id
            ).first()
            if instructor and hasattr(instructor, 'preferred_time_slots'):
                preferred = instructor.preferred_time_slots or {}
                day = cls.day
                time = cls.start_time
                if day in preferred and time not in preferred[day]:
                    not_preferred.append({
                        'class_id': cls.id,
                        'instructor': instructor.name,
                        'preferred_times': preferred
                    })
        if not_preferred:
            return ConstraintResult(
                is_met=False,
                message=f"{len(not_preferred)} کلاس در زمان ترجیحی استاد نیست",
                details={'not_preferred': not_preferred}
            )
        return ConstraintResult(is_met=True, message="همه کلاس‌ها در زمان ترجیحی تشکیل شده‌اند")

    def _check_minimize_gaps(self, classes: List[ScheduledClass]) -> ConstraintResult:
        """بررسی وجود شکاف‌های زمانی زیاد"""
        gaps = []
        # گروه‌بندی بر اساس استاد و روز
        for instructor_id in set(c.id for c in classes):
            for day in set(c.day for c in classes):
                times = sorted([c.start_time for c in classes if c.instructor_id == instructor_id and c.day == day])
                if len(times) > 1:
                    for i in range(len(times)-1):
                        gap = times[i+1] - times[i]
                        if gap > 2:  # شکاف بیشتر از ۲ ساعت
                            gaps.append({
                                'instructor': instructor_id,
                                'day': day,
                                'gap_hours': gap,
                                'between': (times[i], times[i+1])
                            })
        if gaps:
            return ConstraintResult(
                is_met=False,
                message=f"{len(gaps)} شکاف زمانی بزرگتر از ۲ ساعت شناسایی شد",
                details={'gaps': gaps}
            )
        return ConstraintResult(is_met=True, message="شکاف‌های زمانی مناسب")

    def _check_balance_workload(self, classes: List[ScheduledClass]) -> ConstraintResult:
        """بررسی توزیع متوازن بار کاری اساتید"""
        workload = {}
        for cls in classes:
            workload[cls.instructor_id] = workload.get(cls.instructor_id, 0) + (cls.hours or 3)
        max_load = max(workload.values()) if workload else 0
        min_load = min(workload.values()) if workload else 0
        if max_load - min_load > 6:  # تفاوت بیشتر از ۶ ساعت
            return ConstraintResult(
                is_met=False,
                message=f"بار کاری اساتید نامتوازن (بیشترین {max_load}، کمترین {min_load})",
                details={'workload': workload}
            )
        return ConstraintResult(is_met=True, message="بار کاری متوازن است")

    def _check_department_distribution(self, classes: List[ScheduledClass]) -> ConstraintResult:
        """بررسی توزیع مناسب بین دپارتمان‌ها"""
        dept_counts = {}
        for cls in classes:
            offered_course = self.db.query(OfferedCourse).filter(
                OfferedCourse.id == cls.offered_course_id
            ).first()
            if offered_course and hasattr(offered_course, 'department'):
                dept_counts[offered_course.department] = dept_counts.get(offered_course.department, 0) + 1
        if len(dept_counts) < 2:
            return ConstraintResult(is_met=True, message="تنها یک دپارتمان وجود دارد")
        # چک می‌کنیم که هیچ دپارتمانی بیش از ۶۰٪ کلاس‌ها را نداشته باشد
        total = len(classes)
        for dept, count in dept_counts.items():
            if count / total > 0.6:
                return ConstraintResult(
                    is_met=False,
                    message=f"دپارتمان {dept} بیش از ۶۰٪ کلاس‌ها را به خود اختصاص داده",
                    details={'departments': dept_counts}
                )
        return ConstraintResult(is_met=True, message="توزیع دپارتمان‌ها متعادل است")

    # ---------- متدهای کمکی ----------

    def _find_conflicts(self, classes: List[ScheduledClass], field: str) -> List[Dict]:
        """یافتن تداخل‌ها بر اساس یک فیلد (instructor_id یا room_id)"""
        conflicts = []
        time_groups = {}
        for cls in classes:
            key = f"{cls.day}_{cls.start_time}"
            if key not in time_groups:
                time_groups[key] = []
            time_groups[key].append(cls)

        for key, group in time_groups.items():
            ids = [getattr(c, field) for c in group]
            if len(set(ids)) < len(ids):
                conflicts.append({
                    'time': key,
                    'ids': list(set(ids)),
                    'classes': [c.id for c in group]
                })
        return conflicts

    def _calculate_score(self, classes: List[ScheduledClass], details: Dict) -> float:
        """محاسبه امتیاز نهایی بر اساس scoring.yaml"""
        weights = self.scoring.get('weights', {})
        base_score = self.scoring.get('scoring', {}).get('base_score', 1000)
        penalty = self.scoring.get('scoring', {}).get('penalty_per_violation', 50)

        score = base_score

        # کسر امتیاز به ازای هر خطا (محدودیت سخت نقض شده)
        errors_count = len(details.get('hard_violations', {}))
        score -= errors_count * penalty

        # کسر امتیاز به ازای هر هشدار (محدودیت نرم نقض شده)
        warnings_count = len(details.get('soft_violations', {}))
        score -= warnings_count * (penalty // 2)

        return max(0, score)  # امتیاز نمی‌تواند منفی باشد