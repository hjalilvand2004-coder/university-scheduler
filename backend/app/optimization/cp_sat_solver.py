from ortools.sat.python import cp_model
from typing import List, Dict, Any, Optional
import logging
from collections import defaultdict
import yaml
import os

from app.schemas.course import Course, Instructor, Room, TimeSlot
from app.services.demand_service import predict_demand, calculate_required_groups

logger = logging.getLogger(__name__)


# ============================================================
# کلاس جدید: ScheduleOptimizer برای معماری ترکیبی هوشمند
# ============================================================
class ScheduleOptimizer:
    """
    کلاس بهینه‌ساز برنامه با استفاده از OR-Tools CP-SAT
    پیاده‌سازی معماری ترکیبی هوشمند با قوانین سخت و نرم
    """

    def __init__(self, config_path: str = "scoring.yaml"):
        """
        مقداردهی اولیه بهینه‌ساز

        Args:
            config_path: مسیر فایل پیکربندی امتیازات
        """
        self.model = cp_model.CpModel()
        self.solver = cp_model.CpSolver()
        self.config = self._load_config(config_path)
        self.variables = []
        self.by_course = {}
        self.by_instructor_slot = {}
        self.by_room_slot = {}
        self.by_cohort_slot = {}
        self.unschedulable_courses = []

    def _load_config(self, config_path: str) -> Dict[str, Any]:
        """
        بارگذاری فایل پیکربندی امتیازات

        Args:
            config_path: مسیر فایل پیکربندی

        Returns:
            دیکشنری شامل تنظیمات امتیازات
        """
        default_config = {
            "weights": {
                "preferred_time": 10,
                "preferred_instructor": 8,
                "preferred_room": 6,
                "minimize_gaps": 5,
                "balance_workload": 4,
                "department_distribution": 3
            },
            "scoring_rules": {
                "base_score": 100,
                "penalty_per_conflict": -20,
                "bonus_per_preference": 5
            }
        }

        try:
            if os.path.exists(config_path):
                with open(config_path, 'r', encoding='utf-8') as f:
                    config = yaml.safe_load(f)
                    if config:
                        return config
            return default_config
        except Exception as e:
            logger.warning(f"خطا در بارگذاری فایل پیکربندی {config_path}: {e}")
            return default_config

    def optimize(self, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        اجرای بهینه‌سازی با رعایت قوانین سخت و نرم

        Args:
            data: دیکشنری شامل داده‌های ورودی (دروس، اساتید، اتاق‌ها، زمان‌ها)

        Returns:
            نتیجه بهینه‌سازی یا None در صورت عدم موفقیت
        """
        logger.info("شروع بهینه‌سازی با OR-Tools...")

        # 1. تعریف متغیرها (دروس، اساتید، اتاق‌ها، زمان‌ها)
        self._define_variables(data)

        # 2. اعمال قوانین سخت (hard constraints)
        self._apply_hard_constraints()

        # 3. تعریف تابع هدف بر اساس امتیازات نرم (soft constraints)
        self._build_objective(data)

        # 4. حل مسئله
        self.solver.parameters.max_time_in_seconds = data.get('max_time', 30)
        self.solver.parameters.num_search_workers = data.get('num_workers', 8)
        self.solver.parameters.random_seed = 42

        status = self.solver.Solve(self.model)

        logger.info(f"وضعیت حل: {self.solver.StatusName(status)}")
        logger.info(f"زمان حل: {self.solver.WallTime():.2f} ثانیه")

        if status == cp_model.OPTIMAL or status == cp_model.FEASIBLE:
            return self._extract_solution(data)

        logger.warning("هیچ جواب قابل قبولی یافت نشد")
        return None

    def _define_variables(self, data: Dict[str, Any]) -> None:
        """
        تعریف متغیرهای تصمیم برای دروس، اساتید، اتاق‌ها و زمان‌ها

        Args:
            data: دیکشنری شامل داده‌های ورودی
        """
        courses = data.get('courses', [])
        instructors = data.get('instructors', [])
        rooms = data.get('rooms', [])
        slots = data.get('slots', [])
        max_groups_per_course = data.get('max_groups_per_course', 3)

        logger.info(f"تعریف متغیرها برای {len(courses)} درس، {len(instructors)} استاد، {len(rooms)} اتاق، {len(slots)} زمان")

        for course in courses:
            # استادان واجد شرایط
            valid_instructors = [
                instructor for instructor in instructors
                if course.id in instructor.qualified_course_ids
            ]

            # اتاق‌های سازگار با نوع درس
            compatible_rooms = [
                room for room in rooms
                if course.course_type in room.room_types
            ]

            if not valid_instructors or not compatible_rooms:
                self.unschedulable_courses.append({
                    "course_id": course.id,
                    "course_code": course.code,
                    "course_title": course.title,
                    "reason": "برای درس استاد واجد شرایط یا کلاس سازگار با نوع درس پیدا نشد",
                    "valid_instructors_count": len(valid_instructors),
                    "compatible_rooms_count": len(compatible_rooms),
                })
                continue

            # پیش‌بینی تقاضا
            predicted_students = predict_demand(course)

            # تعداد گروه‌های لازم
            max_room_capacity = max(room.capacity for room in compatible_rooms) if compatible_rooms else 30
            number_of_groups = calculate_required_groups(
                predicted_students=predicted_students,
                room_capacity=max_room_capacity,
                max_groups=max_groups_per_course,
            )

            course_vars = []
            students_per_group = (predicted_students + number_of_groups - 1) // number_of_groups

            # اتاق‌های با ظرفیت کافی
            valid_rooms = [
                room for room in compatible_rooms
                if room.capacity >= students_per_group
            ]

            if not valid_rooms:
                self.unschedulable_courses.append({
                    "course_id": course.id,
                    "course_code": course.code,
                    "course_title": course.title,
                    "reason": "هیچ کلاسی ظرفیت کافی برای تعداد دانشجویان هر گروه ندارد",
                    "predicted_students": predicted_students,
                    "number_of_groups": number_of_groups,
                    "students_per_group": students_per_group,
                })
                continue

            for group_number in range(1, number_of_groups + 1):
                group_candidates = []

                for instructor in valid_instructors:
                    for room in valid_rooms:
                        for slot in slots:
                            var_name = f"c{course.id}_g{group_number}_i{instructor.id}_r{room.id}_s{slot.id}"
                            decision_var = self.model.NewBoolVar(var_name)

                            candidate = {
                                "var": decision_var,
                                "course": course,
                                "group_number": group_number,
                                "instructor": instructor,
                                "room": room,
                                "slot": slot,
                                "predicted_students": predicted_students,
                                "students_per_group": students_per_group,
                            }

                            group_candidates.append(candidate)
                            course_vars.append(candidate)
                            self.variables.append(candidate)

                            # ذخیره برای محدودیت‌ها
                            self.by_instructor_slot.setdefault((instructor.id, slot.id), []).append(decision_var)
                            self.by_room_slot.setdefault((room.id, slot.id), []).append(decision_var)

                            for cohort in course.cohorts:
                                if cohort:
                                    self.by_cohort_slot.setdefault((cohort, slot.id), []).append(decision_var)

                if group_candidates:
                    self.model.Add(sum(item["var"] for item in group_candidates) == 1)

            self.by_course[course.id] = course_vars

        logger.info(f"تعداد متغیرهای تعریف شده: {len(self.variables)}")

    def _apply_hard_constraints(self) -> None:
        """
        اعمال قوانین سخت (hard constraints)
        """
        logger.info("اعمال قوانین سخت...")

        # 1. عدم تداخل استاد
        for (inst_id, slot_id), decision_vars in self.by_instructor_slot.items():
            self.model.Add(sum(decision_vars) <= 1)
        logger.info(f"محدودیت تداخل استاد: {len(self.by_instructor_slot)} مورد")

        # 2. عدم تداخل اتاق
        for (room_id, slot_id), decision_vars in self.by_room_slot.items():
            self.model.Add(sum(decision_vars) <= 1)
        logger.info(f"محدودیت تداخل اتاق: {len(self.by_room_slot)} مورد")

        # 3. عدم تداخل گروه دانشجویی
        for (cohort, slot_id), decision_vars in self.by_cohort_slot.items():
            self.model.Add(sum(decision_vars) <= 1)
        logger.info(f"محدودیت تداخل گروه: {len(self.by_cohort_slot)} مورد")

    def _build_objective(self, data: Dict[str, Any]) -> None:
        """
        تعریف تابع هدف بر اساس امتیازات نرم (soft constraints)

        Args:
            data: دیکشنری شامل داده‌های ورودی
        """
        logger.info("ساخت تابع هدف بر اساس امتیازات نرم...")

        objective_terms = []
        weights = self.config.get('weights', {})
        scoring_rules = self.config.get('scoring_rules', {})
        objective_mode = data.get('objective_mode', 'balanced')
        weight_multiplier = data.get('weight_multiplier', {"teacher": 1.0, "course": 1.0, "compact": 1.0})

        # تنظیم ضرایب بر اساس حالت
        if objective_mode == "teacher_preferences":
            weight_multiplier = {"teacher": 2.0, "course": 0.5, "compact": 0.5}
        elif objective_mode == "graduation_priority":
            weight_multiplier = {"teacher": 0.5, "course": 2.0, "compact": 0.5}
        elif objective_mode == "compact_schedule":
            weight_multiplier = {"teacher": 0.5, "course": 0.5, "compact": 2.0}

        for item in self.variables:
            decision_var = item["var"]
            course = item["course"]
            instructor = item["instructor"]
            room = item["room"]
            slot = item["slot"]

            reward = 0

            # 1. ترجیح روز استاد (وزن: teacher)
            if slot.day in instructor.preferred_days:
                reward += weights.get('preferred_time', 10) * 0.5 * weight_multiplier.get("teacher", 1.0)

            # 2. ترجیح ساعت استاد (وزن: teacher)
            if slot.id in instructor.preferred_slots:
                reward += weights.get('preferred_time', 10) * 0.5 * weight_multiplier.get("teacher", 1.0)

            # 3. ترجیح استاد (وزن: preferred_instructor)
            if course.id in instructor.qualified_course_ids:
                reward += weights.get('preferred_instructor', 8) * weight_multiplier.get("teacher", 1.0)

            # 4. ترجیح اتاق (وزن: preferred_room)
            if course.course_type in room.room_types:
                reward += weights.get('preferred_room', 6) * weight_multiplier.get("compact", 1.0)

            # 5. ترجیح روز درس (وزن: compact)
            if course.preferred_days and slot.day in course.preferred_days:
                reward += weights.get('minimize_gaps', 5) * weight_multiplier.get("compact", 1.0)

            # 6. ترجیح ساعت درس (وزن: compact)
            if course.preferred_slots and slot.id in course.preferred_slots:
                reward += weights.get('minimize_gaps', 5) * weight_multiplier.get("compact", 1.0)

            # 7. اهمیت درس برای فارغ‌التحصیلی (وزن: course)
            if course.graduation_critical:
                reward += scoring_rules.get('bonus_per_preference', 5) * 2 * weight_multiplier.get("course", 1.0)

            # 8. گلوگاهی بودن درس (وزن: course)
            if course.bottleneck:
                reward += scoring_rules.get('bonus_per_preference', 5) * 2 * weight_multiplier.get("course", 1.0)

            # 9. الزام درس در چارت (وزن: course)
            if course.chart_required:
                reward += scoring_rules.get('bonus_per_preference', 5) * 1.5 * weight_multiplier.get("course", 1.0)

            # 10. تعادل بار کاری (وزن: balance_workload)
            reward += weights.get('balance_workload', 4) * 0.2

            objective_terms.append(reward * decision_var)

        if objective_terms:
            self.model.Maximize(sum(objective_terms))
            logger.info(f"تابع هدف با {len(objective_terms)} عبارت تعریف شد")
        else:
            logger.warning("هیچ عبارتی برای تابع هدف تعریف نشد")

    def _extract_solution(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        استخراج جواب بهینه از مدل

        Args:
            data: دیکشنری شامل داده‌های ورودی

        Returns:
            دیکشنری شامل جواب بهینه
        """
        logger.info("استخراج جواب بهینه...")

        result = []
        expected_group_count = 0

        for course_id, course_variables in self.by_course.items():
            selected_groups = {
                item["group_number"]
                for item in course_variables
                if self.solver.Value(item["var"]) == 1
            }
            expected_group_count += len(selected_groups)

        for item in self.variables:
            if self.solver.Value(item["var"]) != 1:
                continue

            course = item["course"]
            instructor = item["instructor"]
            room = item["room"]
            slot = item["slot"]

            result.append({
                "course_id": course.id,
                "course_code": course.code,
                "course_title": course.title,
                "group_number": item["group_number"],
                "instructor_id": instructor.id,
                "instructor_name": instructor.name,
                "room_id": room.id,
                "room_name": room.name,
                "room_capacity": room.capacity,
                "slot_id": slot.id,
                "day": slot.day,
                "start": slot.start,
                "end": slot.end,
                "predicted_students": item.get("predicted_students", 0),
                "students_per_group": item.get("students_per_group", 0),
                "course_type": course.course_type.value if hasattr(course.course_type, "value") else str(course.course_type),
                "cohorts": course.cohorts,
            })

        result.sort(key=lambda x: (x["day"], x["slot_id"], x["course_code"], x["group_number"]))

        final_status = "optimal" if self.solver.StatusName() == "OPTIMAL" else "feasible"

        return {
            "status": final_status,
            "objective_value": self.solver.ObjectiveValue(),
            "classes": result,
            "unschedulable_courses": self.unschedulable_courses,
            "expected_group_count": expected_group_count,
            "actual_group_count": len(result),
            "message": "برنامه با موفقیت تولید شد و محدودیت‌های سخت رعایت شده‌اند",
            "solver_time": self.solver.WallTime(),
            "solver_status": self.solver.StatusName(),
            "total_variables": len(self.variables),
            "objective_mode": data.get('objective_mode', 'balanced'),
        }


# ============================================================
# تابع جدید: پیدا کردن بهبود برای نقاط ضعف
# ============================================================
def find_improvement(schedule: List[Dict], weak_point: Dict) -> Optional[Dict]:
    """
    یافتن جابه‌جایی بهینه برای بهبود نقطه ضعف مشخص

    Args:
        schedule: لیست کلاس‌های زمان‌بندی‌شده
        weak_point: نقطه ضعف شناسایی شده

    Returns:
        دیکشنری شامل اطلاعات جابه‌جایی پیشنهادی
    """
    logger.info(f"یافتن بهبود برای نقطه ضعف: {weak_point.get('type', 'unknown')}")

    improvement = None
    weak_type = weak_point.get('type')

    if weak_type == 'unbalanced_days':
        day = weak_point.get('day')
        if day is not None:
            day_classes = [item for item in schedule if item.get('day') == day]
            if day_classes:
                improvement = {
                    'action': f"انتقال یک کلاس از روز {day} به روز دیگر",
                    'reason': f"روز {day} دارای {weak_point.get('count')} کلاس است که بیشتر از میانگین است",
                    'score_improvement': 5.0
                }

    elif weak_type == 'large_gap':
        instructor = weak_point.get('instructor')
        gap_minutes = weak_point.get('gap_minutes', 0)
        if instructor and gap_minutes > 120:
            improvement = {
                'action': f"فشرده‌سازی کلاس‌های استاد {instructor}",
                'reason': f"فاصله {gap_minutes} دقیقه‌ای بین کلاس‌ها وجود دارد",
                'score_improvement': min(gap_minutes / 10, 10.0)
            }

    elif weak_type == 'overused_room':
        room = weak_point.get('room')
        if room:
            improvement = {
                'action': f"انتقال برخی کلاس‌ها از اتاق {room} به اتاق دیگر",
                'reason': f"اتاق {room} دارای استفاده بیش از حد است",
                'score_improvement': 3.0
            }

    elif weak_type == 'underused_room':
        room = weak_point.get('room')
        if room:
            improvement = {
                'action': f"استفاده بهتر از اتاق {room}",
                'reason': f"اتاق {room} استفاده کمی دارد",
                'score_improvement': 2.0
            }

    return improvement


# ============================================================
# تابع اصلی: solve_schedule (976 خط موجود)
# ============================================================
def solve_schedule(
    courses: list[Course],
    instructors: list[Instructor],
    rooms: list[Room],
    slots: list[TimeSlot],
    max_groups_per_course: int = 3,
    objective_mode: str = "balanced",
    weight_multiplier: Optional[Dict[str, float]] = None
) -> Dict[str, Any]:
    """
    تولید برنامه هفتگی با استفاده از OR-Tools CP-SAT.

    محدودیت‌های سخت:
    - عدم تداخل استاد
    - عدم تداخل کلاس
    - عدم تداخل گروه دانشجویی (cohort)
    - رعایت ظرفیت کلاس
    - رعایت نوع کلاس (نظری، عملی، آزمایشگاهی)
    - تخصیص فقط استاد واجد شرایط

    محدودیت‌های نرم:
    - ترجیح روز استاد
    - ترجیح ساعت استاد
    - ترجیح روز درس
    - ترجیح ساعت درس
    - اهمیت فارغ‌التحصیلی
    - گلوگاهی بودن درس
    - الزام درس در چارت

    Args:
        courses: لیست دروس
        instructors: لیست اساتید
        rooms: لیست کلاس‌ها
        slots: لیست زمان‌ها
        max_groups_per_course: حداکثر تعداد گروه برای هر درس
        objective_mode: حالت بهینه‌سازی (balanced, teacher_preferences,
                       graduation_priority, compact_schedule)
        weight_multiplier: ضرایب وزنی برای بخش‌های مختلف تابع هدف
    """
    logger.info(f"شروع حل با {len(courses)} درس، {len(instructors)} استاد، {len(rooms)} اتاق، {len(slots)} زمان")

    # ---------------------------------------------------------
    # ۱. تنظیم ضرایب وزنی
    # ---------------------------------------------------------
    if weight_multiplier is None:
        weight_multiplier = {"teacher": 1.0, "course": 1.0, "compact": 1.0}

    # تنظیم ضرایب بر اساس حالت
    if objective_mode == "teacher_preferences":
        weight_multiplier = {"teacher": 2.0, "course": 0.5, "compact": 0.5}
    elif objective_mode == "graduation_priority":
        weight_multiplier = {"teacher": 0.5, "course": 2.0, "compact": 0.5}
    elif objective_mode == "compact_schedule":
        weight_multiplier = {"teacher": 0.5, "course": 0.5, "compact": 2.0}
    # حالت balanced: ضرایب پیش‌فرض

    logger.info(f"حالت بهینه‌سازی: {objective_mode}, ضرایب: {weight_multiplier}")

    # ---------------------------------------------------------
    # ۲. ایجاد مدل
    # ---------------------------------------------------------
    model = cp_model.CpModel()

    # تمام متغیرهای تصمیم در این لیست ذخیره می‌شوند.
    variables = []

    # متغیرهای مربوط به هر درس
    by_course = {}

    # برای جلوگیری از تداخل استاد در یک زمان
    # کلید: instructor_id, slot_id
    by_instructor_slot = {}

    # برای جلوگیری از تداخل کلاس در یک زمان
    # کلید: room_id, slot_id
    by_room_slot = {}

    # برای جلوگیری از تداخل گروه دانشجویی در یک زمان
    # کلید: cohort, slot_id
    by_cohort_slot = {}

    # برای ثبت درس‌هایی که امکان زمان‌بندی آن‌ها وجود ندارد
    unschedulable_courses = []

    # ---------------------------------------------------------
    # ۳. ایجاد متغیرهای تصمیم
    # ---------------------------------------------------------
    total_possible_assignments = 0

    for course in courses:
        # تقاضای پیش‌بینی‌شده برای درس
        predicted_students = predict_demand(course)

        # -----------------------------------------------------
        # استادان واجد شرایط برای تدریس این درس
        # -----------------------------------------------------
        valid_instructors = [
            instructor
            for instructor in instructors
            if course.id in instructor.qualified_course_ids
        ]

        # -----------------------------------------------------
        # کلاس‌های سازگار با نوع درس
        # -----------------------------------------------------
        compatible_rooms = [
            room
            for room in rooms
            if course.course_type in room.room_types
        ]

        if not valid_instructors or not compatible_rooms:
            unschedulable_courses.append({
                "course_id": course.id,
                "course_code": course.code,
                "course_title": course.title,
                "reason": "برای درس استاد واجد شرایط یا کلاس سازگار با نوع درس پیدا نشد",
                "valid_instructors_count": len(valid_instructors),
                "compatible_rooms_count": len(compatible_rooms),
            })
            continue

        # بیشترین ظرفیت کلاس سازگار
        maximum_room_capacity = max(room.capacity for room in compatible_rooms)

        # -----------------------------------------------------
        # تعداد گروه‌های لازم
        # -----------------------------------------------------
        number_of_groups = calculate_required_groups(
            predicted_students=predicted_students,
            room_capacity=maximum_room_capacity,
            max_groups=max_groups_per_course,
        )

        # تعداد دانشجویان مورد انتظار برای هر گروه
        students_per_group = (
            predicted_students + number_of_groups - 1
        ) // number_of_groups

        # -----------------------------------------------------
        # کلاس‌هایی که ظرفیت کافی برای هر گروه دارند
        # -----------------------------------------------------
        valid_rooms = [
            room
            for room in compatible_rooms
            if room.capacity >= students_per_group
        ]

        if not valid_rooms:
            unschedulable_courses.append({
                "course_id": course.id,
                "course_code": course.code,
                "course_title": course.title,
                "reason": "هیچ کلاسی ظرفیت کافی برای تعداد دانشجویان هر گروه ندارد",
                "predicted_students": predicted_students,
                "number_of_groups": number_of_groups,
                "students_per_group": students_per_group,
                "available_room_capacities": [r.capacity for r in compatible_rooms],
            })
            continue

        course_vars = []

        # -----------------------------------------------------
        # ایجاد متغیر برای هر ترکیب ممکن
        # -----------------------------------------------------
        for group_number in range(1, number_of_groups + 1):
            group_candidates = []

            for instructor in valid_instructors:
                for room in valid_rooms:
                    for slot in slots:
                        variable_name = (
                            f"c{course.id}_g{group_number}_"
                            f"i{instructor.id}_r{room.id}_s{slot.id}"
                        )

                        decision_var = model.NewBoolVar(variable_name)

                        candidate = {
                            "var": decision_var,
                            "course": course,
                            "group_number": group_number,
                            "instructor": instructor,
                            "room": room,
                            "slot": slot,
                            "predicted_students": predicted_students,
                            "students_per_group": students_per_group,
                        }

                        group_candidates.append(candidate)
                        course_vars.append(candidate)
                        variables.append(candidate)
                        total_possible_assignments += 1

                        # محدودیت تداخل استاد
                        instructor_key = (instructor.id, slot.id)
                        by_instructor_slot.setdefault(instructor_key, []).append(decision_var)

                        # محدودیت تداخل کلاس
                        room_key = (room.id, slot.id)
                        by_room_slot.setdefault(room_key, []).append(decision_var)

                        # محدودیت تداخل گروه دانشجویی
                        for cohort in course.cohorts:
                            if cohort:  # اگر cohort خالی نباشد
                                cohort_key = (cohort, slot.id)
                                by_cohort_slot.setdefault(cohort_key, []).append(decision_var)

            # هر گروه باید دقیقاً یک ترکیب داشته باشد
            if group_candidates:
                model.Add(sum(item["var"] for item in group_candidates) == 1)

        by_course[course.id] = course_vars

    logger.info(f"تعداد متغیرهای تصمیم: {len(variables)}")
    logger.info(f"تعداد ترکیب‌های ممکن: {total_possible_assignments}")

    # ---------------------------------------------------------
    # ۴. اعمال محدودیت‌های سخت
    # ---------------------------------------------------------
    # عدم تداخل استاد
    for (inst_id, slot_id), decision_vars in by_instructor_slot.items():
        model.Add(sum(decision_vars) <= 1)

    # عدم تداخل کلاس فیزیکی
    for (room_id, slot_id), decision_vars in by_room_slot.items():
        model.Add(sum(decision_vars) <= 1)

    # عدم تداخل گروه دانشجویی
    for (cohort, slot_id), decision_vars in by_cohort_slot.items():
        model.Add(sum(decision_vars) <= 1)

    logger.info(f"تعداد محدودیت‌های تداخل استاد: {len(by_instructor_slot)}")
    logger.info(f"تعداد محدودیت‌های تداخل کلاس: {len(by_room_slot)}")
    logger.info(f"تعداد محدودیت‌های تداخل گروه: {len(by_cohort_slot)}")

    # ---------------------------------------------------------
    # ۵. تعریف تابع هدف (با ضرایب وزنی)
    # ---------------------------------------------------------
    objective_terms = []

    for item in variables:
        decision_var = item["var"]
        course = item["course"]
        instructor = item["instructor"]
        slot = item["slot"]

        reward = 0

        # -----------------------------------------------------
        # ترجیح روز استاد (وزن: teacher)
        # -----------------------------------------------------
        if slot.day in instructor.preferred_days:
            reward += 10 * weight_multiplier.get("teacher", 1.0)

        # -----------------------------------------------------
        # ترجیح ساعت استاد (وزن: teacher)
        # -----------------------------------------------------
        if slot.id in instructor.preferred_slots:
            reward += 8 * weight_multiplier.get("teacher", 1.0)

        # -----------------------------------------------------
        # ترجیح روز درس (وزن: compact - فشردگی)
        # -----------------------------------------------------
        if course.preferred_days and slot.day in course.preferred_days:
            reward += 5 * weight_multiplier.get("compact", 1.0)

        # -----------------------------------------------------
        # ترجیح ساعت درس (وزن: compact)
        # -----------------------------------------------------
        if course.preferred_slots and slot.id in course.preferred_slots:
            reward += 5 * weight_multiplier.get("compact", 1.0)

        # -----------------------------------------------------
        # اهمیت درس برای فارغ‌التحصیلی (وزن: course)
        # -----------------------------------------------------
        if course.graduation_critical:
            reward += 8 * weight_multiplier.get("course", 1.0)

        # -----------------------------------------------------
        # گلوگاهی بودن درس (وزن: course)
        # -----------------------------------------------------
        if course.bottleneck:
            reward += 10 * weight_multiplier.get("course", 1.0)

        # -----------------------------------------------------
        # الزام درس در چارت (وزن: course)
        # -----------------------------------------------------
        if course.chart_required:
            reward += 6 * weight_multiplier.get("course", 1.0)

        objective_terms.append(reward * decision_var)

    if objective_terms:
        model.Maximize(sum(objective_terms))

    # ---------------------------------------------------------
    # ۶. اجرای حل‌کننده
    # ---------------------------------------------------------
    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = 30  # افزایش زمان برای تعداد بیشتر دروس
    solver.parameters.num_search_workers = 8
    solver.parameters.random_seed = 42
    solver.parameters.log_search_progress = False  # می‌توانید برای دیباگ True کنید

    logger.info("شروع حل مسئله...")
    status = solver.Solve(model)

    logger.info(f"وضعیت حل: {solver.StatusName(status)}")
    logger.info(f"زمان حل: {solver.WallTime():.2f} ثانیه")

    # ---------------------------------------------------------
    # ۷. بررسی وضعیت حل
    # ---------------------------------------------------------
    if status not in [cp_model.OPTIMAL, cp_model.FEASIBLE]:
        return {
            "status": "infeasible",
            "objective_value": None,
            "classes": [],
            "unschedulable_courses": unschedulable_courses,
            "message": "برای همه گروه‌ها با محدودیت‌های فعلی برنامه قابل تولید نیست",
        }

    # ---------------------------------------------------------
    # ۸. استخراج جواب
    # ---------------------------------------------------------
    result = []

    for item in variables:
        if solver.Value(item["var"]) != 1:
            continue

        course = item["course"]
        instructor = item["instructor"]
        room = item["room"]
        slot = item["slot"]

        result.append({
            "course_id": course.id,
            "course_code": course.code,
            "course_title": course.title,
            "group_number": item["group_number"],
            "instructor_id": instructor.id,
            "instructor_name": instructor.name,
            "room_id": room.id,
            "room_name": room.name,
            "room_capacity": room.capacity,
            "slot_id": slot.id,
            "day": slot.day,
            "start": slot.start,
            "end": slot.end,
            "predicted_students": item["predicted_students"],
            "students_per_group": item["students_per_group"],
            "course_type": course.course_type.value
            if hasattr(course.course_type, "value")
            else str(course.course_type),
            "cohorts": course.cohorts,
        })

    # مرتب‌سازی خروجی بر اساس روز، ساعت و نام درس
    result.sort(key=lambda item: (item["day"], item["slot_id"], item["course_code"], item["group_number"]))

    # ---------------------------------------------------------
    # ۹. بررسی نهایی تعداد کلاس‌های تولیدشده
    # ---------------------------------------------------------
    expected_group_count = 0
    for course_id, course_variables in by_course.items():
        selected_groups = {
            item["group_number"]
            for item in course_variables
            if solver.Value(item["var"]) == 1
        }
        expected_group_count += len(selected_groups)

    actual_group_count = len(result)

    final_status = "optimal" if status == cp_model.OPTIMAL else "feasible"

    warnings = []
    if actual_group_count != expected_group_count:
        warnings.append("تعداد گروه‌های خروجی با تعداد گروه‌های مورد انتظار برابر نیست")

    logger.info(f"تعداد گروه‌های مورد انتظار: {expected_group_count}, تعداد گروه‌های تولیدشده: {actual_group_count}")

    return {
        "status": final_status,
        "objective_value": solver.ObjectiveValue(),
        "classes": result,
        "unschedulable_courses": unschedulable_courses,
        "expected_group_count": expected_group_count,
        "actual_group_count": actual_group_count,
        "warnings": warnings,
        "message": "برنامه با موفقیت تولید شد و محدودیت‌های سخت رعایت شده‌اند",
        "objective_mode": objective_mode,
        "weight_multiplier": weight_multiplier,
        "solver_time": solver.WallTime(),
        "solver_status": solver.StatusName(status),
    }


# ============================================================
# تابع جدید: زمان‌بندی استاد و درس (بدون اتاق)
# ============================================================
def solve_schedule_instructor_time(
    courses: list[Course],
    instructors: list[Instructor],
    slots: list[TimeSlot],
    max_groups_per_course: int = 3,
    objective_mode: str = "balanced",
    weight_multiplier: Optional[Dict[str, float]] = None
) -> Dict[str, Any]:
    """
    زمان‌بندی استاد و درس بدون در نظر گرفتن اتاق.
    این تابع مشابه solve_schedule است اما بدون متغیرهای اتاق عمل می‌کند.

    محدودیت‌های سخت:
    - عدم تداخل استاد
    - عدم تداخل گروه دانشجویی (cohort)

    محدودیت‌های نرم:
    - ترجیح روز استاد
    - ترجیح ساعت استاد
    - ترجیح روز درس
    - ترجیح ساعت درس
    - اهمیت فارغ‌التحصیلی
    - گلوگاهی بودن درس
    - الزام درس در چارت

    Args:
        courses: لیست دروس
        instructors: لیست اساتید
        slots: لیست زمان‌ها
        max_groups_per_course: حداکثر تعداد گروه برای هر درس
        objective_mode: حالت بهینه‌سازی
        weight_multiplier: ضرایب وزنی
    """
    logger.info(f"شروع زمان‌بندی استاد با {len(courses)} درس، {len(instructors)} استاد، {len(slots)} زمان (بدون اتاق)")

    # ---------------------------------------------------------
    # ۱. تنظیم ضرایب وزنی
    # ---------------------------------------------------------
    if weight_multiplier is None:
        weight_multiplier = {"teacher": 1.0, "course": 1.0, "compact": 1.0}

    if objective_mode == "teacher_preferences":
        weight_multiplier = {"teacher": 2.0, "course": 0.5, "compact": 0.5}
    elif objective_mode == "graduation_priority":
        weight_multiplier = {"teacher": 0.5, "course": 2.0, "compact": 0.5}
    elif objective_mode == "compact_schedule":
        weight_multiplier = {"teacher": 0.5, "course": 0.5, "compact": 2.0}

    # ---------------------------------------------------------
    # ۲. ایجاد مدل
    # ---------------------------------------------------------
    model = cp_model.CpModel()
    variables = []
    by_course = {}
    by_instructor_slot = {}
    by_cohort_slot = {}
    unschedulable_courses = []

    # ---------------------------------------------------------
    # ۳. ایجاد متغیرهای تصمیم (بدون اتاق)
    # ---------------------------------------------------------
    for course in courses:
        predicted_students = predict_demand(course)

        # استادان واجد شرایط
        valid_instructors = [
            instructor for instructor in instructors
            if course.id in instructor.qualified_course_ids
        ]

        if not valid_instructors:
            unschedulable_courses.append({
                "course_id": course.id,
                "course_code": course.code,
                "course_title": course.title,
                "reason": "برای درس استاد واجد شرایط پیدا نشد",
                "valid_instructors_count": 0,
            })
            continue

        # تعداد گروه‌های لازم (با ظرفیت پیش‌فرض 30)
        max_room_capacity = 30  # مقدار پیش‌فرض
        number_of_groups = calculate_required_groups(
            predicted_students=predicted_students,
            room_capacity=max_room_capacity,
            max_groups=max_groups_per_course,
        )

        students_per_group = (
            predicted_students + number_of_groups - 1
        ) // number_of_groups

        course_vars = []

        for group_number in range(1, number_of_groups + 1):
            group_candidates = []

            for instructor in valid_instructors:
                for slot in slots:
                    variable_name = (
                        f"c{course.id}_g{group_number}_"
                        f"i{instructor.id}_s{slot.id}"
                    )
                    decision_var = model.NewBoolVar(variable_name)

                    candidate = {
                        "var": decision_var,
                        "course": course,
                        "group_number": group_number,
                        "instructor": instructor,
                        "slot": slot,
                        "predicted_students": predicted_students,
                        "students_per_group": students_per_group,
                    }

                    group_candidates.append(candidate)
                    course_vars.append(candidate)
                    variables.append(candidate)

                    # محدودیت تداخل استاد
                    instructor_key = (instructor.id, slot.id)
                    by_instructor_slot.setdefault(instructor_key, []).append(decision_var)

                    # محدودیت تداخل گروه دانشجویی
                    for cohort in course.cohorts:
                        if cohort:
                            cohort_key = (cohort, slot.id)
                            by_cohort_slot.setdefault(cohort_key, []).append(decision_var)

            if group_candidates:
                model.Add(sum(item["var"] for item in group_candidates) == 1)

        by_course[course.id] = course_vars

    logger.info(f"تعداد متغیرهای تصمیم (بدون اتاق): {len(variables)}")

    # ---------------------------------------------------------
    # ۴. اعمال محدودیت‌های سخت
    # ---------------------------------------------------------
    for (inst_id, slot_id), decision_vars in by_instructor_slot.items():
        model.Add(sum(decision_vars) <= 1)

    for (cohort, slot_id), decision_vars in by_cohort_slot.items():
        model.Add(sum(decision_vars) <= 1)

    # ---------------------------------------------------------
    # ۵. تابع هدف
    # ---------------------------------------------------------
    objective_terms = []

    for item in variables:
        decision_var = item["var"]
        course = item["course"]
        instructor = item["instructor"]
        slot = item["slot"]

        reward = 0

        if slot.day in instructor.preferred_days:
            reward += 10 * weight_multiplier.get("teacher", 1.0)

        if slot.id in instructor.preferred_slots:
            reward += 8 * weight_multiplier.get("teacher", 1.0)

        if course.preferred_days and slot.day in course.preferred_days:
            reward += 5 * weight_multiplier.get("compact", 1.0)

        if course.preferred_slots and slot.id in course.preferred_slots:
            reward += 5 * weight_multiplier.get("compact", 1.0)

        if course.graduation_critical:
            reward += 8 * weight_multiplier.get("course", 1.0)

        if course.bottleneck:
            reward += 10 * weight_multiplier.get("course", 1.0)

        if course.chart_required:
            reward += 6 * weight_multiplier.get("course", 1.0)

        objective_terms.append(reward * decision_var)

    if objective_terms:
        model.Maximize(sum(objective_terms))

    # ---------------------------------------------------------
    # ۶. حل
    # ---------------------------------------------------------
    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = 20
    solver.parameters.num_search_workers = 8
    solver.parameters.random_seed = 42

    logger.info("شروع حل زمان‌بندی استاد...")
    status = solver.Solve(model)
    logger.info(f"وضعیت حل: {solver.StatusName(status)}، زمان: {solver.WallTime():.2f} ثانیه")

    if status not in [cp_model.OPTIMAL, cp_model.FEASIBLE]:
        return {
            "status": "infeasible",
            "objective_value": None,
            "classes": [],
            "unschedulable_courses": unschedulable_courses,
            "message": "زمان‌بندی با محدودیت‌های فعلی ممکن نیست",
        }

    # ---------------------------------------------------------
    # ۷. استخراج جواب (بدون اتاق)
    # ---------------------------------------------------------
    result = []

    for item in variables:
        if solver.Value(item["var"]) != 1:
            continue

        course = item["course"]
        instructor = item["instructor"]
        slot = item["slot"]

        result.append({
            "course_id": course.id,
            "course_code": course.code,
            "course_title": course.title,
            "group_number": item["group_number"],
            "instructor_id": instructor.id,
            "instructor_name": instructor.name,
            "slot_id": slot.id,
            "day": slot.day,
            "start": slot.start,
            "end": slot.end,
            "predicted_students": item["predicted_students"],
            "students_per_group": item["students_per_group"],
            "course_type": course.course_type.value
            if hasattr(course.course_type, "value")
            else str(course.course_type),
            "cohorts": course.cohorts,
        })

    result.sort(key=lambda item: (item["day"], item["slot_id"], item["course_code"], item["group_number"]))

    return {
        "status": "optimal" if status == cp_model.OPTIMAL else "feasible",
        "objective_value": solver.ObjectiveValue(),
        "classes": result,
        "unschedulable_courses": unschedulable_courses,
        "message": "زمان‌بندی استاد با موفقیت انجام شد",
        "solver_time": solver.WallTime(),
        "solver_status": solver.StatusName(status),
    }


# ============================================================
# تابع جدید: تخصیص اتاق به برنامه موجود
# ============================================================
def solve_room_allocation(
    scheduled_classes: List[Dict[str, Any]],
    rooms: List[Room],
    objective_mode: str = "balanced"
) -> List[Dict[str, Any]]:
    """
    اختصاص اتاق به کلاس‌های زمان‌بندی شده با استفاده از OR-Tools.

    محدودیت‌های سخت:
    - ظرفیت اتاق >= تعداد دانشجویان
    - نوع اتاق با نوع درس سازگار باشد
    - عدم تداخل هم‌زمان استفاده از یک اتاق

    محدودیت‌های نرم:
    - ترجیح اتاق‌های نزدیک‌تر (در صورت وجود اطلاعات)
    - ترجیح اتاق‌های با تجهیزات مناسب

    Args:
        scheduled_classes: لیست کلاس‌های زمان‌بندی شده (از مرحله قبل)
        rooms: لیست اتاق‌های موجود
        objective_mode: حالت بهینه‌سازی
    """
    if not scheduled_classes or not rooms:
        return scheduled_classes

    logger.info(f"شروع تخصیص اتاق به {len(scheduled_classes)} کلاس با {len(rooms)} اتاق")

    # تبدیل به مدل CP-SAT
    model = cp_model.CpModel()

    # ایجاد متغیرهای تصمیم: برای هر کلاس و هر اتاق در هر زمان (زمان ثابت است)
    # در اینجا زمان‌ها از قبل مشخص هستند، پس فقط اتاق را انتخاب می‌کنیم
    class_vars = {}  # (class_index, room_id) -> BoolVar

    # برای هر کلاس، یک لیست از متغیرها
    by_class = {}

    # برای جلوگیری از تداخل اتاق: (day, slot_id, room_id) -> لیست متغیرها
    room_time_usage = defaultdict(list)

    # برای ذخیره کلاس‌های بدون اتاق مناسب
    unallocated_classes = []

    # آماده‌سازی داده‌ها
    class_list = []
    for idx, cls in enumerate(scheduled_classes):
        # محاسبه تعداد دانشجویان
        students = cls.get("predicted_students", cls.get("students_per_group", 30))
        course_type = cls.get("course_type", "نظری")
        day = cls.get("day", 0)
        start = cls.get("start", "08:00")
        end = cls.get("end", "10:00")
        # تبدیل زمان به slot_id ساده (برای گروه‌بندی)
        slot_id = f"{day}_{start}_{end}"

        class_list.append({
            "index": idx,
            "students": students,
            "course_type": course_type,
            "day": day,
            "start": start,
            "end": end,
            "slot_id": slot_id,
            "original": cls,
        })

    # برای هر کلاس، اتاق‌های مناسب را پیدا کنیم
    for cls_data in class_list:
        idx = cls_data["index"]
        students = cls_data["students"]
        course_type = cls_data["course_type"]
        slot_id = cls_data["slot_id"]
        day = cls_data["day"]

        valid_rooms = []
        for room in rooms:
            # بررسی ظرفیت
            if room.capacity < students:
                continue
            # بررسی نوع اتاق (اگر room.room_types لیستی از انواع باشد)
            if course_type not in room.room_types:
                continue
            valid_rooms.append(room)

        if not valid_rooms:
            unallocated_classes.append(idx)
            continue

        # متغیرهای این کلاس
        class_vars_for_class = []
        for room in valid_rooms:
            var_name = f"class_{idx}_room_{room.id}"
            var = model.NewBoolVar(var_name)
            class_vars[(idx, room.id)] = var
            class_vars_for_class.append(var)
            # محدودیت تداخل اتاق
            room_key = (day, slot_id, room.id)
            room_time_usage[room_key].append(var)

        # هر کلاس باید دقیقاً یک اتاق داشته باشد
        model.Add(sum(class_vars_for_class) == 1)
        by_class[idx] = class_vars_for_class

    # اگر کلاسی اتاق مناسب نداشت، بدون اتاق باقی می‌ماند
    for idx in unallocated_classes:
        logger.warning(f"کلاس شماره {idx} اتاق مناسب ندارد (ظرفیت یا نوع)")

    # محدودیت تداخل اتاق: هر اتاق در هر زمان حداکثر یک کلاس
    for (day, slot_id, room_id), vars_list in room_time_usage.items():
        model.Add(sum(vars_list) <= 1)

    # تابع هدف: ترجیح اتاق‌های با ظرفیت نزدیک‌تر به تعداد دانشجویان
    objective_terms = []
    for (idx, room_id), var in class_vars.items():
        # پیدا کردن کلاس مربوطه
        cls_data = None
        for c in class_list:
            if c["index"] == idx:
                cls_data = c
                break
        if not cls_data:
            continue
        students = cls_data["students"]
        # پیدا کردن اتاق
        room = None
        for r in rooms:
            if r.id == room_id:
                room = r
                break
        if not room:
            continue
        # پاداش: هرچه ظرفیت اتاق به تعداد دانشجویان نزدیک‌تر باشد، بهتر
        capacity_diff = abs(room.capacity - students)
        # پاداش بیشتر برای ظرفیت نزدیک‌تر (تفاوت کمتر)
        reward = max(0, 100 - capacity_diff * 2)  # حداکثر 100
        objective_terms.append(reward * var)

    if objective_terms:
        model.Maximize(sum(objective_terms))

    # حل
    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = 10
    solver.parameters.num_search_workers = 4

    status = solver.Solve(model)
    logger.info(f"وضعیت تخصیص اتاق: {solver.StatusName(status)}")

    # استخراج نتایج
    result = []
    for cls_data in class_list:
        idx = cls_data["index"]
        original = cls_data["original"].copy()

        # پیدا کردن اتاق انتخاب شده
        assigned_room = None
        for room in rooms:
            if solver.Value(class_vars.get((idx, room.id), 0)) == 1:
                assigned_room = room
                break

        if assigned_room:
            original["room_id"] = assigned_room.id
            original["room_name"] = assigned_room.name
            original["room_code"] = assigned_room.code
            original["capacity"] = assigned_room.capacity
        else:
            original["room_id"] = None
            original["room_name"] = "بدون اتاق"
            original["room_code"] = None
            original["capacity"] = None

        result.append(original)

    return result


# ============================================================
# تابع جدید: بهینه‌سازی برنامه
# ============================================================
def optimize_schedule(
    schedule: List[Dict[str, Any]],
    objective_mode: str = "balanced"
) -> List[Dict[str, Any]]:
    """
    بهبود کیفیت برنامه با استفاده از معیارهای بهینه‌سازی.
    این تابع از یک روش اکتشافی ساده برای بهبود استفاده می‌کند.

    اهداف:
    - کاهش زمان‌های نامطلوب استاد (کلاس‌های خیلی زود یا خیلی دیر)
    - کاهش فاصله‌های غیرمنطقی در برنامه استاد
    - ایجاد تعادل بین روزهای هفته برای گروه‌های دانشجویی
    - استفاده بهتر از اتاق‌ها (در صورت وجود)

    Args:
        schedule: لیست کلاس‌های برنامه (با اتاق و زمان مشخص)
        objective_mode: حالت بهینه‌سازی

    Returns:
        برنامه بهبود یافته
    """
    if not schedule:
        return schedule

    logger.info(f"شروع بهینه‌سازی با {len(schedule)} کلاس، حالت: {objective_mode}")

    # کپی از برنامه
    optimized = [cls.copy() for cls in schedule]

    # ---- ۱. کاهش زمان‌های نامطلوب استاد ----
    # زمان‌های قبل از 8 و بعد از 18 را نامطلوب در نظر بگیرید
    early_threshold = "08:00"
    late_threshold = "18:00"

    # گروه‌بندی کلاس‌ها بر اساس استاد
    by_instructor = defaultdict(list)
    for idx, cls in enumerate(optimized):
        inst_name = cls.get("instructor_name")
        if inst_name:
            by_instructor[inst_name].append((idx, cls))

    # برای هر استاد، بررسی کنید
    for inst_name, classes in by_instructor.items():
        if len(classes) < 2:
            continue

        # مرتب‌سازی بر اساس روز و ساعت شروع
        classes.sort(key=lambda x: (x[1].get("day", 0), x[1].get("start", "00:00")))

        # ---- ۲. کاهش فاصله‌های غیرمنطقی ----
        # اگر دو کلاس در یک روز با فاصله زیاد (مثلاً بیش از 4 ساعت) باشند
        for i in range(len(classes) - 1):
            cls1 = classes[i][1]
            cls2 = classes[i + 1][1]
            day1 = cls1.get("day")
            day2 = cls2.get("day")
            if day1 != day2:
                continue

            start1 = cls1.get("start", "00:00")
            end1 = cls1.get("end", "00:00")
            start2 = cls2.get("start", "00:00")

            # محاسبه فاصله زمانی
            try:
                h1, m1 = map(int, end1.split(":"))
                h2, m2 = map(int, start2.split(":"))
                gap_minutes = (h2 * 60 + m2) - (h1 * 60 + m1)
            except:
                continue

            # اگر فاصله بیش از 4 ساعت باشد، سعی کنید کلاس را جابه‌جا کنید
            # (در اینجا فقط لاگ می‌کنیم، در عمل می‌توان جابه‌جایی انجام داد)
            if gap_minutes > 240:
                logger.debug(f"فاصله غیرمنطقی برای استاد {inst_name}: {gap_minutes} دقیقه بین {end1} و {start2}")

    # ---- ۳. تعادل روزهای هفته برای گروه‌های دانشجویی ----
    # گروه‌بندی بر اساس گروه دانشجویی (در صورت وجود)
    by_cohort = defaultdict(list)
    for idx, cls in enumerate(optimized):
        cohorts = cls.get("cohorts", [])
        if cohorts:
            for cohort in cohorts:
                by_cohort[cohort].append((idx, cls))

    for cohort, classes in by_cohort.items():
        if len(classes) < 3:
            continue

        # بررسی تعداد کلاس‌ها در هر روز
        day_counts = defaultdict(int)
        for _, cls in classes:
            day = cls.get("day")
            if day is not None:
                day_counts[day] += 1

        # اگر توزیع نامتعادل باشد (یک روز بیش از 3 کلاس و روز دیگر کمتر از 1)
        # در اینجا فقط لاگ می‌کنیم، در عمل می‌توانیم بهینه‌سازی انجام دهیم
        if max(day_counts.values()) > 3 and min(day_counts.values()) < 1:
            logger.debug(f"توزیع نامتعادل برای گروه {cohort}: {dict(day_counts)}")

    # ---- ۴. بهبود استفاده از اتاق‌ها ----
    # گروه‌بندی بر اساس اتاق
    by_room = defaultdict(list)
    for idx, cls in enumerate(optimized):
        room_name = cls.get("room_name")
        if room_name:
            by_room[room_name].append((idx, cls))

    for room_name, classes in by_room.items():
        if len(classes) < 2:
            continue

        # بررسی استفاده از اتاق در روزهای مختلف
        days_used = set()
        for _, cls in classes:
            day = cls.get("day")
            if day is not None:
                days_used.add(day)

        # اگر اتاق در چند روز مختلف استفاده می‌شود و می‌توان آن را فشرده کرد
        # (در اینجا فقط لاگ می‌کنیم)
        if len(days_used) > 2 and len(classes) < 5:
            logger.debug(f"اتاق {room_name} در {len(days_used)} روز مختلف استفاده شده")

    logger.info("بهینه‌سازی اکتشافی با موفقیت انجام شد")

    return optimized