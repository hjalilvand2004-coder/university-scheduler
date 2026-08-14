from sqlalchemy.orm import Session
from typing import List, Dict, Any, Optional, Tuple
import logging
import re
from collections import defaultdict
from datetime import datetime

from app.models.instructor import Instructor
from app.models.teaching_preference import TeachingPreference
from app.models.time_preference import TimePreference
from app.models.schedule_history import ScheduleHistory
from app.services.workflow_helpers import calculate_final_score

logger = logging.getLogger(__name__)

DAY_MAP = {
    "شنبه": 0, "یکشنبه": 1, "دوشنبه": 2,
    "سه‌شنبه": 3, "سهشنبه": 3,
    "چهارشنبه": 4, "پنجشنبه": 5,
}
DAY_NAMES = ["شنبه", "یکشنبه", "دوشنبه", "سه‌شنبه", "چهارشنبه", "پنجشنبه"]

COOPERATION_PRIORITY = {
    "هیات علمی": 30,
    "استاد مدعو": 20,
    "دستیار آموزشی": 10,
    "کارشناس": 5,
}

TWO_UNIT_SLOTS = [
    ("07:30", "09:15"), ("09:16", "11:00"), ("11:01", "12:45"),
    ("13:00", "14:45"), ("14:46", "16:30"), ("16:31", "18:15"), ("18:16", "20:00")
]
THREE_UNIT_SLOTS = [
    ("07:30", "10:10"), ("10:11", "12:50"), ("13:00", "15:30"),
    ("15:31", "18:00"), ("18:01", "20:30")
]

# ============================================================
# StepLogger (بدون تغییر)
# ============================================================
class StepLogger:
    def __init__(self):
        self.steps = []
        self.current_step = 0

    def start_step(self, name: str, description: str = ""):
        self.current_step += 1
        step = {
            "step": self.current_step,
            "name": name,
            "description": description,
            "status": "running",
            "details": {},
            "timestamp": datetime.now().isoformat()
        }
        self.steps.append(step)
        return step

    def complete_step(self, details: dict, status: str = "success"):
        if self.steps:
            self.steps[-1]["status"] = status
            self.steps[-1]["details"] = details
            self.steps[-1]["timestamp_end"] = datetime.now().isoformat()

    def fail_step(self, error_message: str):
        if self.steps:
            self.steps[-1]["status"] = "failed"
            self.steps[-1]["details"]["error"] = error_message

    def get_result(self):
        return self.steps

# ============================================================
# توابع کمکی (Normalize, helpers)
# ============================================================
def normalize_code(code: str) -> str:
    if not code:
        return code
    normalized = re.sub(r'[^A-Za-z0-9_]', '', code)
    return normalized.upper()

def normalize_instructor_code(code: str) -> str:
    if not code:
        return code
    cleaned = re.sub(r'\s+', '', code)
    if cleaned.isdigit():
        return str(int(cleaned))
    return cleaned

def normalize_day(day: str) -> str:
    if not day:
        return day
    day = day.replace("\u200c", " ")
    day = " ".join(day.split())
    return day.replace(" ", "")

def time_to_minutes(t: str) -> int:
    try:
        h, m = map(int, t.split(':'))
        return h * 60 + m
    except:
        return 0

def get_slots_for_units(units: int) -> List[Tuple[str, str]]:
    return THREE_UNIT_SLOTS if units == 3 else TWO_UNIT_SLOTS

def get_day_name(day_num: int) -> str:
    return DAY_NAMES[day_num] if 0 <= day_num < 6 else str(day_num)

def calculate_time_match_score(
        slot_start: str,
        slot_end: str,
        pref_start: str,
        pref_end: str,
        priority: int,
        max_tolerance_minutes: int = 90
) -> float:
    slot_mid = (time_to_minutes(slot_start) + time_to_minutes(slot_end)) / 2
    pref_mid = (time_to_minutes(pref_start) + time_to_minutes(pref_end)) / 2
    distance = abs(slot_mid - pref_mid)
    if distance > max_tolerance_minutes:
        return 0.0
    score = 100.0 * (1 - (distance / max_tolerance_minutes))
    priority_factor = max(0.5, 1.5 - (priority / 100.0))
    return score * priority_factor

def is_internship_or_project(course: Dict) -> bool:
    course_type = course.get("course_type", "").lower()
    if course_type in ["internship", "project", "کارآموزی", "پروژه"]:
        return True
    name = course.get("course_name", "").lower()
    if "کارآموزی" in name or "پروژه" in name:
        return True
    return False

def slot_overlap(s1_start, s1_end, s2_start, s2_end) -> bool:
    return time_to_minutes(s1_start) < time_to_minutes(s2_end) and time_to_minutes(s2_start) < time_to_minutes(s1_end)

# ============================================================
# کلاس اصلی ScheduleService
# ============================================================
class ScheduleService:
    def __init__(self, db: Session):
        self.db = db

    def process(self, basket: List[Dict]) -> Dict[str, Any]:
        step_logger = StepLogger()
        if not basket:
            logger.warning("سبد دروس خالی است")
            return {"assigned": [], "unassigned": [], "all": [], "steps": step_logger.get_result()}

        logger.info("=" * 80)
        logger.info("🚀 شروع فرایند زمان‌بندی استاد و درس")
        logger.info(f"📊 تعداد کلاس‌های سبد: {len(basket)}")
        logger.info("=" * 80)

        # ---------- مرحله ۱: آماده‌سازی ----------
        step_logger.start_step("آماده‌سازی داده‌ها", "نرمال‌سازی کدها و استخراج شماره ترم")
        try:
            prepared_courses = self._prepare_data(basket)
            step_logger.complete_step({
                "total_courses": len(prepared_courses),
                "sample_codes": [c.get("unique_code") for c in prepared_courses[:3]]
            })
            logger.info(f"📝 مرحله ۱: آماده‌سازی داده‌ها - {len(prepared_courses)} درس آماده شد")
        except Exception as e:
            step_logger.fail_step(str(e))
            raise

        # ---------- مرحله ۲: بارگذاری اطلاعات ----------
        step_logger.start_step("بارگذاری اطلاعات اساتید", "دریافت از دیتابیس")
        try:
            instructor_data, teaching_prefs, time_prefs = self._load_instructor_data()
            sample_teaching = []
            teaching_items = list(teaching_prefs.items())
            for course_code, inst_list in teaching_items[:5]:
                instructors_info = []
                for inst_code in inst_list[:3]:
                    instructors_info.append({
                        "code": inst_code,
                        "name": instructor_data['names'].get(inst_code, inst_code)
                    })
                sample_teaching.append({
                    "course_code": course_code,
                    "instructors": instructors_info
                })

            sample_time = []
            time_items = list(time_prefs.items())
            for inst_code, time_list in time_items[:5]:
                prefs = []
                for day_num, start, end, priority in time_list[:3]:
                    prefs.append({
                        "day": get_day_name(day_num),
                        "start": start,
                        "end": end,
                        "priority": priority
                    })
                sample_time.append({
                    "instructor_code": inst_code,
                    "instructor_name": instructor_data['names'].get(inst_code, inst_code),
                    "preferences": prefs
                })

            step_logger.complete_step({
                "instructors_count": len(instructor_data['codes']),
                "teaching_prefs_count": len(teaching_prefs),
                "time_prefs_count": len(time_prefs),
                "sample_teaching_prefs": sample_teaching,
                "sample_time_prefs": sample_time
            })
            logger.info(f"👨‍🏫 مرحله ۲: اطلاعات اساتید بارگذاری شد - {len(instructor_data['codes'])} استاد")
        except Exception as e:
            step_logger.fail_step(str(e))
            raise

        regular_courses = [c for c in prepared_courses if not is_internship_or_project(c)]
        internship_courses = [c for c in prepared_courses if is_internship_or_project(c)]
        logger.info(f"🔍 تفکیک دروس: {len(regular_courses)} درس عادی، {len(internship_courses)} درس کارآموزی/پروژه")

        # ---------- مرحله ۳: اولویت‌بندی دروس ----------
        step_logger.start_step("اولویت‌بندی دروس عادی", "محاسبه امتیاز بر اساس پیش‌نیاز، ترم جاری، تقاضا و واحد")
        try:
            scored_courses = self._score_and_sort_courses(regular_courses)
            step_logger.complete_step({
                "total_courses": len(scored_courses),
                "sample_scores": [
                    {
                        "course_name": c.get("course_name"),
                        "group_number": c.get("group_number"),
                        "priority_score": c.get("priority_score"),
                        "score_components": c.get("score_components", {})
                    }
                    for c in scored_courses[:10]
                ]
            })
            logger.info(f"📊 مرحله ۳: اولویت‌بندی دروس عادی - {len(scored_courses)} درس امتیازدهی شد")
        except Exception as e:
            step_logger.fail_step(str(e))
            raise

        # ---------- مرحله ۴: تخصیص استاد ----------
        step_logger.start_step("تخصیص استاد به دروس عادی", "بر اساس اولویت‌های تدریس و نوع همکاری (چرخشی)")
        try:
            assigned_regular_with_instructor, unassigned_regular_no_instructor = self._assign_instructor_to_regular_courses(
                scored_courses, teaching_prefs, instructor_data
            )
            step_logger.complete_step({
                "assigned": len(assigned_regular_with_instructor),
                "unassigned": len(unassigned_regular_no_instructor),
                "assigned_instructor": assigned_regular_with_instructor[:50],
                "unassigned_instructor": unassigned_regular_no_instructor[:50]
            })
            logger.info(
                f"✅ مرحله ۴: تخصیص استاد به دروس عادی - {len(assigned_regular_with_instructor)} تخصیص یافت، {len(unassigned_regular_no_instructor)} بدون استاد")
        except Exception as e:
            step_logger.fail_step(str(e))
            raise

        # ============================================================
        # مرحله ۵: زمان‌بندی کامل هر استاد (با رویکرد تساهل تدریجی و توزیع متوازن)
        # ============================================================
        step_logger.start_step("زمان‌بندی کامل به ازای هر استاد",
                               "برای هر استاد، با افزایش تدریجی تساهل، دروس را به طور متوازن در روزهای ترجیحی تخصیص می‌دهد")
        try:
            assigned_regular_complete, unassigned_regular_no_time = self._assign_full_schedule_per_instructor(
                assigned_regular_with_instructor, time_prefs, instructor_data
            )
            step_logger.complete_step({
                "assigned": len(assigned_regular_complete),
                "unassigned": len(unassigned_regular_no_time),
                "assigned_time": assigned_regular_complete[:50],
                "unassigned_time": unassigned_regular_no_time[:50]
            })
            logger.info(
                f"✅ مرحله ۵: زمان‌بندی کامل به ازای هر استاد - {len(assigned_regular_complete)} تخصیص یافت، {len(unassigned_regular_no_time)} بدون زمان")
        except Exception as e:
            step_logger.fail_step(str(e))
            raise

        # ---------- مرحله ۶: کارآموزی/پروژه ----------
        step_logger.start_step("تخصیص استاد به کارآموزی/پروژه", "بدون محدودیت زمان و واحد")
        try:
            assigned_internship, unassigned_internship = self._assign_internship_instructors(
                internship_courses, teaching_prefs, instructor_data
            )
            step_logger.complete_step({
                "assigned": len(assigned_internship),
                "unassigned": len(unassigned_internship),
                "assigned_internship": assigned_internship[:50],
                "unassigned_internship": unassigned_internship[:50]
            })
            logger.info(
                f"✅ مرحله ۶: تخصیص استاد به کارآموزی/پروژه - {len(assigned_internship)} تخصیص یافت، {len(unassigned_internship)} بدون استاد")
        except Exception as e:
            step_logger.fail_step(str(e))
            raise

        assigned = assigned_regular_complete + assigned_internship
        unassigned = unassigned_regular_no_instructor + unassigned_regular_no_time + unassigned_internship

        # ---------- مرحله ۷: گزارش نهایی ----------
        step_logger.start_step("گزارش نهایی", "جمع‌بندی و پاک‌سازی")
        try:
            instructor_used_units = defaultdict(int)
            for item in assigned_regular_complete:
                if item.get("instructor_code"):
                    instructor_used_units[item["instructor_code"]] += item.get("units", 0)

            self._generate_final_report(assigned, unassigned, instructor_data, dict(instructor_used_units))

            for item in assigned:
                item.pop("room", None)
                item.pop("room_id", None)
                item.pop("room_name", None)
                item.pop("capacity", None)

            mismatch_details = []
            occupancy = defaultdict(lambda: defaultdict(list))
            for item in assigned:
                if item.get("instructor_code") and item.get("day") is not None and item.get("start") and item.get("end"):
                    occupancy[item["instructor_code"]][item["day"]].append({
                        "start": item["start"],
                        "end": item["end"],
                        "course_name": item.get("course_name", "نامشخص"),
                        "group": item.get("group_number", 0)
                    })

            def find_conflict_for_preferred_time(instructor_code, day, start, end, exclude_course=None):
                if instructor_code not in occupancy or day not in occupancy[instructor_code]:
                    return None
                for occ in occupancy[instructor_code][day]:
                    if exclude_course and occ["course_name"] == exclude_course and occ["group"] == 0:
                        continue
                    if slot_overlap(start, end, occ["start"], occ["end"]):
                        return occ
                return None

            def check_match_status(course, teaching_prefs, time_prefs, instructor_data):
                if not course.get("instructor_code") or course.get("day") is None or not course.get("start"):
                    return {
                        "status": "no_assignment",
                        "reason": "درس تخصیص کامل ندارد (استاد، روز یا زمان مشخص نشده)"
                    }

                instructor_code = course["instructor_code"]
                course_code = course.get("unique_code")
                day = course["day"]
                start = course["start"]
                end = course["end"]

                teach_match = False
                if course_code and instructor_code:
                    pref_list = teaching_prefs.get(course_code, [])
                    if instructor_code in pref_list:
                        teach_match = True

                day_match = False
                time_match = False
                time_pref_list = time_prefs.get(instructor_code, [])
                for d, s, e, p in time_pref_list:
                    if d == day:
                        day_match = True
                        score = calculate_time_match_score(start, end, s, e, p, max_tolerance_minutes=90)
                        if score > 0:
                            time_match = True
                            break

                if teach_match and day_match and time_match:
                    return {"status": "full", "reason": None}

                reasons = []
                if not teach_match:
                    reasons.append("استاد در لیست مطلوبیت تدریس این درس نیست")

                if not day_match or not time_match:
                    best_pref = None
                    best_priority = 999
                    for d, s, e, p in time_pref_list:
                        if p < best_priority:
                            best_priority = p
                            best_pref = (d, s, e)

                    if best_pref:
                        pref_day, pref_start, pref_end = best_pref
                        conflict = find_conflict_for_preferred_time(
                            instructor_code, pref_day, pref_start, pref_end,
                            exclude_course=course.get("course_name")
                        )
                        if conflict:
                            reasons.append(
                                f"زمان مطلوب استاد ({get_day_name(pref_day)} {pref_start}-{pref_end}) با درس '{conflict['course_name']}' (گروه {conflict['group']}) تداخل دارد"
                            )
                        else:
                            if not day_match:
                                reasons.append(
                                    f"روز مطلوب استاد ({get_day_name(pref_day)}) با روز تخصیص‌یافته ({get_day_name(day)}) متفاوت است")
                            if not time_match:
                                reasons.append(
                                    f"زمان تخصیص‌یافته ({start}-{end}) با مطلوبیت‌های زمان استاد تطابق ندارد (با تساهل ۹۰ دقیقه)")
                    else:
                        if not day_match:
                            reasons.append("روز تخصیص‌یافته در مطلوبیت‌های روز استاد نیست")
                        if not time_match:
                            reasons.append("زمان تخصیص‌یافته با مطلوبیت‌های زمان استاد تطابق ندارد (با تساهل ۹۰ دقیقه)")

                if not reasons:
                    if not teach_match and not day_match and not time_match:
                        reasons.append("هیچ یک از مطلوبیت‌های تدریس، روز و زمان با تخصیص تطابق ندارند")
                    elif not teach_match and not day_match:
                        reasons.append("مطلوبیت تدریس و روز با تخصیص تطابق ندارند")
                    elif not teach_match and not time_match:
                        reasons.append("مطلوبیت تدریس و زمان با تخصیص تطابق ندارند")
                    elif not day_match and not time_match:
                        reasons.append("مطلوبیت روز و زمان با تخصیص تطابق ندارند")
                    elif not teach_match:
                        reasons.append("مطلوبیت تدریس با تخصیص تطابق ندارد")
                    elif not day_match:
                        reasons.append("مطلوبیت روز با تخصیص تطابق ندارد")
                    elif not time_match:
                        reasons.append("مطلوبیت زمان با تخصیص تطابق ندارد")

                return {
                    "status": "partial" if (teach_match or day_match or time_match) else "none",
                    "reason": "؛ ".join(reasons) if reasons else "دلیل نامشخص"
                }

            for item in assigned:
                match_info = check_match_status(item, teaching_prefs, time_prefs, instructor_data)
                if match_info["status"] != "full":
                    mismatch_details.append({
                        "course_name": item.get("course_name"),
                        "group_number": item.get("group_number"),
                        "instructor_code": item.get("instructor_code"),
                        "instructor_name": item.get("instructor_name"),
                        "day": item.get("day"),
                        "start": item.get("start"),
                        "end": item.get("end"),
                        "status": match_info["status"],
                        "reason": match_info["reason"],
                        "level": item.get("level"),
                        "term": item.get("term"),
                        "unique_code": item.get("unique_code"),
                        "is_assigned": True
                    })

            for item in unassigned:
                reason = item.get("unassigned_reason", "دلیل نامشخص")
                mismatch_details.append({
                    "course_name": item.get("course_name"),
                    "group_number": item.get("group_number"),
                    "instructor_code": item.get("instructor_code"),
                    "instructor_name": item.get("instructor_name"),
                    "day": item.get("day"),
                    "start": item.get("start"),
                    "end": item.get("end"),
                    "status": "unassigned",
                    "reason": reason,
                    "level": item.get("level"),
                    "term": item.get("term"),
                    "unique_code": item.get("unique_code"),
                    "is_assigned": False
                })

            logger.info("📋 زمان‌های نهایی تخصیص‌یافته (نمونه):")
            for item in assigned[:5]:
                logger.info(
                    f"   {item.get('course_name')} گروه {item.get('group_number')} → {item.get('day')} {item.get('start')}-{item.get('end')} (واحد: {item.get('units')})")

            step_logger.complete_step({
                "total_assigned": len(assigned),
                "total_unassigned": len(unassigned),
                "success_rate": f"{len(assigned) / (len(assigned) + len(unassigned)) * 100:.2f}%" if (len(assigned) + len(unassigned)) > 0 else "0%",
                "mismatch_details": mismatch_details
            })
        except Exception as e:
            step_logger.fail_step(str(e))
            raise

        all_classes = assigned + unassigned
        return {
            "assigned": assigned,
            "unassigned": unassigned,
            "all": all_classes,
            "steps": step_logger.get_result()
        }

    # ============================================================
    # مرحله ۱: آماده‌سازی داده‌ها
    # ============================================================
    def _prepare_data(self, basket: List[Dict]) -> List[Dict]:
        prepared = []
        for course in basket:
            new_course = course.copy()
            if "unique_code" in new_course:
                new_course["unique_code"] = normalize_code(new_course["unique_code"])
            if "term_number" not in new_course:
                term_str = new_course.get("term", "")
                match = re.search(r'\d+', term_str)
                new_course["term_number"] = int(match.group()) if match else 1
            if "group_number" not in new_course:
                new_course["group_number"] = 1
            if "is_prerequisite" not in new_course:
                new_course["is_prerequisite"] = False
            if "student_demand" not in new_course:
                new_course["student_demand"] = 0
            new_course["unassigned_reason"] = None
            prepared.append(new_course)
        return prepared

    # ============================================================
    # مرحله ۳: اولویت‌بندی دروس
    # ============================================================
    def _score_and_sort_courses(self, courses: List[Dict]) -> List[Dict]:
        if not courses:
            return []

        course_count = defaultdict(int)
        for c in courses:
            code = c.get("unique_code")
            if code:
                course_count[code] += 1

        scored = []
        for course in courses:
            code = course.get("unique_code")
            score = 0
            components = {}

            if course.get("is_prerequisite", False):
                score += 10
                components["prerequisite"] = 10

            term_number = course.get("term_number", 1)
            term = course.get("term", "").lower()
            is_current = False
            if "مهر" in term and term_number % 2 == 1:
                is_current = True
            elif "بهمن" in term and term_number % 2 == 0:
                is_current = True
            elif not term:
                if term_number % 2 == 1:
                    is_current = True

            if is_current:
                score += 5
                components["current_term"] = 5

            if course.get("student_demand", 0) > 0:
                score += 3
                components["demand"] = 3

            units = course.get("units", 2)
            if units == 3:
                score += 3
                components["units"] = 3
            elif units == 2:
                score += 2
                components["units"] = 2
            elif units == 1:
                score += 1
                components["units"] = 1
            else:
                components["units"] = 0

            total_count = course_count.get(code, 1)
            repeat_penalty = (total_count - 1) * 2
            if repeat_penalty > 0:
                score -= repeat_penalty
                components["repeat_penalty"] = -repeat_penalty

            course["priority_score"] = score
            course["score_components"] = components
            scored.append(course)

        scored.sort(key=lambda x: x.get("priority_score", 0), reverse=True)
        return scored

    # ============================================================
    # مرحله ۲: بارگذاری اطلاعات
    # ============================================================
    def _load_instructor_data(self) -> Tuple[Dict, Dict, Dict]:
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

    # ============================================================
    # مرحله ۴: تخصیص استاد
    # ============================================================
    def _assign_instructor_to_regular_courses(
            self,
            regular_courses: List[Dict],
            teaching_prefs: Dict,
            instructor_data: Dict
    ) -> Tuple[List[Dict], List[Dict]]:
        if not regular_courses:
            return [], []

        groups_by_course = defaultdict(list)
        for course in regular_courses:
            code_norm = normalize_code(course.get("unique_code", ""))
            if code_norm:
                group_key = (code_norm, course.get("group_number", 1))
                groups_by_course[code_norm].append((group_key, course))

        course_max_score = {}
        for code, groups in groups_by_course.items():
            max_score = max((g[1].get("priority_score", 0) for g in groups), default=0)
            course_max_score[code] = max_score

        sorted_course_codes = sorted(course_max_score.keys(), key=lambda c: course_max_score.get(c, 0), reverse=True)

        instructor_used_units = defaultdict(int)
        assigned_groups = set()
        assigned = []
        unassigned = []

        for course_code in sorted_course_codes:
            groups = groups_by_course[course_code]
            preferred_instructors = teaching_prefs.get(course_code, [])

            if not preferred_instructors:
                for group_key, group in groups:
                    group["instructor_code"] = None
                    group["instructor_name"] = None
                    group["final_score"] = 0
                    group["manual_required"] = True
                    group["unassigned_reason"] = "هیچ استاد واجد شرطی برای این درس ثبت نشده است"
                    unassigned.append(group)
                continue

            num_instructors = len(preferred_instructors)
            instructor_index = 0
            groups.sort(key=lambda x: x[0][1])

            for group_key, group in groups:
                if group_key in assigned_groups:
                    continue

                units = group.get("units", 2)
                assigned_instructor = None
                for _ in range(num_instructors):
                    inst_code = preferred_instructors[instructor_index % num_instructors]
                    if instructor_used_units.get(inst_code, 0) + units <= instructor_data['max_units'].get(inst_code, 999):
                        assigned_instructor = inst_code
                        instructor_index = (instructor_index + 1) % num_instructors
                        break
                    else:
                        instructor_index = (instructor_index + 1) % num_instructors

                if assigned_instructor:
                    inst_name = instructor_data['names'].get(assigned_instructor, assigned_instructor)
                    group["instructor_code"] = assigned_instructor
                    group["instructor_name"] = inst_name
                    priority_index = preferred_instructors.index(assigned_instructor)
                    group["instructor_priority"] = priority_index + 1
                    group["final_score"] = calculate_final_score(group)
                    group["manual_required"] = False
                    instructor_used_units[assigned_instructor] += units
                    assigned_groups.add(group_key)
                    assigned.append(group)
                    logger.info(
                        f"✅ درس '{group.get('course_name')}' گروه {group.get('group_number')} → استاد {inst_name} (اولویت {priority_index + 1})")
                else:
                    group["instructor_code"] = None
                    group["instructor_name"] = None
                    group["final_score"] = 0
                    group["manual_required"] = True
                    group["unassigned_reason"] = "تمامی اساتید اولویت‌دار ظرفیت تدریس خود را تکمیل کرده‌اند"
                    unassigned.append(group)
                    logger.warning(
                        f"⚠️ درس '{group.get('course_name')}' گروه {group.get('group_number')} - هیچ استاد با ظرفیت کافی یافت نشد")

        return assigned, unassigned

    # ============================================================
    # مرحله ۵: زمان‌بندی کامل هر استاد
    # ============================================================

    def _assign_full_schedule_per_instructor(
            self,
            courses_with_instructor: List[Dict],
            time_prefs: Dict,
            instructor_data: Dict
    ) -> Tuple[List[Dict], List[Dict]]:

        if not courses_with_instructor:
            return [], []

        assigned: List[Dict] = []
        unassigned: List[Dict] = []

        courses_by_instructor = defaultdict(list)

        # ------------------------------------------------------------
        # گروه‌بندی دروس بر اساس استاد
        # ------------------------------------------------------------

        for course in courses_with_instructor:

            instructor_code = course.get("instructor_code")

            if instructor_code:
                courses_by_instructor[instructor_code].append(course)
            else:
                course["day"] = None
                course["start"] = None
                course["end"] = None
                course["schedule_match_level"] = "no_instructor"
                course["schedule_tolerance"] = None
                course["unassigned_reason"] = (
                    "درس در مرحله چهارم استاد ندارد"
                )
                unassigned.append(course)

        # ------------------------------------------------------------
        # توابع کمکی
        # ------------------------------------------------------------

        def sort_slots(
                slots: List[Tuple[str, str]]
        ) -> List[Tuple[str, str]]:

            return sorted(
                list(slots),
                key=lambda slot: (
                    time_to_minutes(slot[0]),
                    time_to_minutes(slot[1])
                )
            )

        def is_conflict(
                occupied_slots: List[Tuple[str, str]],
                start: str,
                end: str
        ) -> bool:

            return any(
                slot_overlap(
                    start,
                    end,
                    occupied_start,
                    occupied_end
                )
                for occupied_start, occupied_end in occupied_slots
            )

        def get_course_slots(
                course: Dict
        ) -> List[Tuple[str, str]]:

            units = int(course.get("units", 2) or 2)

            if units == 3:
                return sort_slots(THREE_UNIT_SLOTS)

            return sort_slots(TWO_UNIT_SLOTS)

        def get_interval_metrics(
                slot_start: str,
                slot_end: str,
                pref_start: str,
                pref_end: str
        ) -> Dict[str, Any]:

            slot_start_min = time_to_minutes(slot_start)
            slot_end_min = time_to_minutes(slot_end)

            pref_start_min = time_to_minutes(pref_start)
            pref_end_min = time_to_minutes(pref_end)

            fully_inside = (
                    slot_start_min >= pref_start_min
                    and slot_end_min <= pref_end_min
            )

            # مهم‌ترین شرط مرحله اصلی
            start_inside = (
                    pref_start_min <= slot_start_min < pref_end_min
            )

            end_inside = (
                    pref_start_min < slot_end_min <= pref_end_min
            )

            overlap_start = max(
                slot_start_min,
                pref_start_min
            )

            overlap_end = min(
                slot_end_min,
                pref_end_min
            )

            overlap_minutes = max(
                0,
                overlap_end - overlap_start
            )

            slot_duration = max(
                1,
                slot_end_min - slot_start_min
            )

            overlap_ratio = (
                    overlap_minutes / slot_duration
            )

            if slot_end_min < pref_start_min:
                distance = pref_start_min - slot_end_min
            elif slot_start_min > pref_end_min:
                distance = slot_start_min - pref_end_min
            else:
                distance = 0

            return {
                "fully_inside": fully_inside,
                "start_inside": start_inside,
                "end_inside": end_inside,
                "overlap_minutes": overlap_minutes,
                "overlap_ratio": overlap_ratio,
                "distance": distance,
                "slot_start_minutes": slot_start_min,
                "slot_end_minutes": slot_end_min
            }

        def candidate_sort_key(
                candidate: Dict[str, Any]
        ) -> Tuple:

            return (
                # اول اسلات کاملاً داخل بازه
                -int(candidate["fully_inside"]),

                # سپس اسلاتی که شروعش داخل بازه است
                -int(candidate["start_inside"]),

                # سپس میزان هم‌پوشانی بیشتر
                -candidate["overlap_minutes"],

                # سپس فاصله واقعی کمتر
                candidate["distance"],

                # سپس اولویت زمانی استاد
                candidate["priority"],

                # سپس شروع زودتر
                candidate["slot_start_minutes"]
            )

        def get_best_candidate(
                course: Dict,
                day_preferences: List[Tuple[str, str, int]],
                occupied_slots: List[Tuple[str, str]],
                mode: str
        ) -> Optional[Dict[str, Any]]:
            """
            mode ها:

            strict:
                فقط اسلات‌هایی که شروعشان داخل بازه مطلوب است.

            tolerance:
                اسلات‌های دارای شروع داخل بازه یا حداکثر یک ساعت
                فاصله واقعی از بازه مطلوب.

            fallback:
                هر اسلات قابل استفاده، با اولویت نزدیک‌ترین اسلات.
            """

            candidates = []

            for pref_start, pref_end, pref_priority in day_preferences:

                for slot_start, slot_end in get_course_slots(course):

                    if is_conflict(
                            occupied_slots,
                            slot_start,
                            slot_end
                    ):
                        continue

                    metrics = get_interval_metrics(
                        slot_start=slot_start,
                        slot_end=slot_end,
                        pref_start=pref_start,
                        pref_end=pref_end
                    )

                    # ------------------------------------------------
                    # مرحله اول:
                    # شروع اسلات باید داخل بازه مطلوب باشد.
                    # ------------------------------------------------

                    if mode == "strict":

                        if not metrics["start_inside"]:
                            continue

                        score = 1000.0

                        if metrics["fully_inside"]:
                            score += 500.0

                        score += metrics["overlap_minutes"]

                    # ------------------------------------------------
                    # مرحله دوم:
                    # شروع داخل بازه یا فاصله حداکثر ۶۰ دقیقه
                    # ------------------------------------------------

                    elif mode == "tolerance":

                        if (
                                not metrics["start_inside"]
                                and metrics["distance"] > 60
                        ):
                            continue

                        score = 500.0

                        if metrics["fully_inside"]:
                            score += 500.0

                        if metrics["start_inside"]:
                            score += 250.0

                        score += metrics["overlap_minutes"]

                        score -= metrics["distance"]

                    # ------------------------------------------------
                    # مرحله سوم:
                    # fallback نزدیک‌ترین اسلات
                    # ------------------------------------------------

                    else:

                        score = 0.0

                        if metrics["fully_inside"]:
                            score += 1000.0

                        elif metrics["start_inside"]:
                            score += 800.0

                        elif metrics["overlap_minutes"] > 0:
                            score += (
                                    400.0
                                    + metrics["overlap_ratio"] * 100.0
                            )

                        score -= metrics["distance"]

                    candidates.append({
                        "slot_start": slot_start,
                        "slot_end": slot_end,
                        "priority": pref_priority,
                        "score": score,
                        **metrics
                    })

            if not candidates:
                return None

            # در strict و tolerance، کیفیت زمانی از شروع زودتر مهم‌تر است.
            candidates.sort(
                key=lambda candidate: (
                    -int(candidate["fully_inside"]),
                    -int(candidate["start_inside"]),
                    -candidate["overlap_minutes"],
                    candidate["distance"],
                    candidate["priority"],
                    -candidate["score"],
                    candidate["slot_start_minutes"]
                )
            )

            return candidates[0]

        def choose_next_course(
                remaining_courses: List[Dict],
                day_preferences: List[Tuple[str, str, int]],
                occupied_slots: List[Tuple[str, str]],
                mode: str
        ) -> Optional[Dict[str, Any]]:
            """
            انتخاب درس بعدی.

            اول کیفیت زمانی بررسی می‌شود و سپس اولویت آموزشی درس.
            """

            candidates = []

            for queue_index, course in enumerate(
                    remaining_courses
            ):

                candidate = get_best_candidate(
                    course=course,
                    day_preferences=day_preferences,
                    occupied_slots=occupied_slots,
                    mode=mode
                )

                if candidate is None:
                    continue

                candidates.append({
                    "queue_index": queue_index,
                    "course": course,
                    "candidate": candidate
                })

            if not candidates:
                return None

            def choose_key(item: Dict[str, Any]) -> Tuple:

                candidate = item["candidate"]
                course = item["course"]

                if mode == "strict":
                    return (
                        # ابتدا کیفیت جایگاه زمانی
                        -int(candidate["fully_inside"]),
                        -int(candidate["start_inside"]),
                        -candidate["overlap_minutes"],
                        candidate["distance"],

                        # سپس اولویت آموزشی
                        -course.get("priority_score", 0),

                        candidate["priority"],
                        item["queue_index"]
                    )

                return (
                    -course.get("priority_score", 0),
                    -int(candidate["fully_inside"]),
                    -int(candidate["start_inside"]),
                    -candidate["overlap_minutes"],
                    candidate["distance"],
                    candidate["priority"],
                    item["queue_index"]
                )

            candidates.sort(key=choose_key)

            return candidates[0]

        def assign_course(
                course: Dict,
                instructor_code: str,
                day: int,
                candidate: Dict[str, Any],
                match_level: str,
                tolerance: Optional[int]
        ) -> None:

            course["day"] = day
            course["start"] = candidate["slot_start"]
            course["end"] = candidate["slot_end"]

            course["schedule_match_level"] = match_level
            course["schedule_tolerance"] = tolerance
            course["schedule_match_score"] = round(
                candidate.get("score", 0),
                2
            )

            course["schedule_distance_minutes"] = candidate.get(
                "distance"
            )

            course["schedule_fully_inside_preference"] = (
                candidate.get("fully_inside", False)
            )

            course["schedule_start_inside_preference"] = (
                candidate.get("start_inside", False)
            )

            course["schedule_overlap_minutes"] = candidate.get(
                "overlap_minutes",
                0
            )

            assigned.append(course)

            logger.info(
                f"⏰ درس '{course.get('course_name')}' "
                f"گروه {course.get('group_number')} → "
                f"استاد {instructor_code}، "
                f"{get_day_name(day)} "
                f"{course['start']}-{course['end']} "
                f"(سطح: {match_level}، "
                f"داخل کامل: "
                f"{candidate.get('fully_inside', False)}، "
                f"شروع داخل بازه: "
                f"{candidate.get('start_inside', False)}، "
                f"تساهل: {tolerance})"
            )

        # ============================================================
        # زمان‌بندی مستقل هر استاد
        # ============================================================

        for instructor_code, instructor_courses in (
                courses_by_instructor.items()
        ):

            remaining_courses = sorted(
                list(instructor_courses),
                key=lambda course: (
                    -course.get("priority_score", 0),
                    course.get("course_name", "")
                )
            )

            prefs = list(
                time_prefs.get(instructor_code, [])
            )

            # --------------------------------------------------------
            # بدون مطلوبیت زمانی
            # --------------------------------------------------------

            if not prefs:

                occupied = defaultdict(list)

                for course in list(remaining_courses):

                    selected_day = None
                    selected_slot = None

                    for day in range(6):

                        for slot in get_course_slots(course):

                            if not is_conflict(
                                    occupied[day],
                                    slot[0],
                                    slot[1]
                            ):
                                selected_day = day
                                selected_slot = slot
                                break

                        if selected_slot is not None:
                            break

                    remaining_courses.remove(course)

                    if selected_slot is None:
                        course["day"] = None
                        course["start"] = None
                        course["end"] = None
                        course["schedule_match_level"] = "unassigned"
                        course["schedule_tolerance"] = None
                        course["unassigned_reason"] = (
                            f"برای استاد {instructor_code} "
                            f"اسلات آزاد پیدا نشد"
                        )

                        unassigned.append(course)
                        continue

                    candidate = {
                        "slot_start": selected_slot[0],
                        "slot_end": selected_slot[1],
                        "score": 0,
                        "distance": None,
                        "fully_inside": False,
                        "start_inside": False,
                        "overlap_minutes": 0
                    }

                    assign_course(
                        course=course,
                        instructor_code=instructor_code,
                        day=selected_day,
                        candidate=candidate,
                        match_level="no_preference_default",
                        tolerance=None
                    )

                    occupied[selected_day].append(
                        selected_slot
                    )

                continue

            # --------------------------------------------------------
            # گروه‌بندی مطلوبیت‌ها
            # --------------------------------------------------------

            day_preferences = defaultdict(list)

            for day_num, start, end, priority in prefs:
                day_preferences[day_num].append(
                    (start, end, priority)
                )

            for day in day_preferences:
                day_preferences[day].sort(
                    key=lambda item: (
                        item[2],
                        time_to_minutes(item[0])
                    )
                )

            sorted_days = sorted(
                day_preferences.keys(),
                key=lambda day: (
                    min(
                        pref[2]
                        for pref in day_preferences[day]
                    ),
                    day
                )
            )

            occupied = defaultdict(list)

            logger.info(
                f"📅 ترتیب روزهای استاد {instructor_code}: "
                f"{[(get_day_name(day), min(p[2] for p in day_preferences[day])) for day in sorted_days]}"
            )

            # ========================================================
            # مرحله اول: فقط شروع داخل بازه مطلوب
            # ========================================================
            #
            # نکته مهم:
            # این مرحله باید برای تمام روزهای مطلوب اجرا شود.
            # بنابراین اگر سه‌شنبه اسلات مناسب دیگری نداشته باشد،
            # الگوریتم به چهارشنبه می‌رود؛ نه اینکه اسلات 10:11
            # سه‌شنبه را انتخاب کند.
            # ========================================================

            for day in sorted_days:

                if not remaining_courses:
                    break

                day_prefs = day_preferences[day]

                while remaining_courses:

                    selected = choose_next_course(
                        remaining_courses=remaining_courses,
                        day_preferences=day_prefs,
                        occupied_slots=occupied[day],
                        mode="strict"
                    )

                    if selected is None:
                        break

                    queue_index = selected["queue_index"]
                    course = selected["course"]
                    candidate = selected["candidate"]

                    match_level = (
                        "full"
                        if candidate["fully_inside"]
                        else "start_inside_preference"
                    )

                    assign_course(
                        course=course,
                        instructor_code=instructor_code,
                        day=day,
                        candidate=candidate,
                        match_level=match_level,
                        tolerance=0
                    )

                    occupied[day].append(
                        (
                            candidate["slot_start"],
                            candidate["slot_end"]
                        )
                    )

                    remaining_courses.pop(queue_index)

            # ========================================================
            # مرحله دوم: تساهل حداکثر ۶۰ دقیقه
            # ========================================================

            for day in sorted_days:

                if not remaining_courses:
                    break

                day_prefs = day_preferences[day]

                while remaining_courses:

                    selected = choose_next_course(
                        remaining_courses=remaining_courses,
                        day_preferences=day_prefs,
                        occupied_slots=occupied[day],
                        mode="tolerance"
                    )

                    if selected is None:
                        break

                    queue_index = selected["queue_index"]
                    course = selected["course"]
                    candidate = selected["candidate"]

                    assign_course(
                        course=course,
                        instructor_code=instructor_code,
                        day=day,
                        candidate=candidate,
                        match_level="tolerance_60",
                        tolerance=60
                    )

                    occupied[day].append(
                        (
                            candidate["slot_start"],
                            candidate["slot_end"]
                        )
                    )

                    remaining_courses.pop(queue_index)

            # ========================================================
            # مرحله سوم: fallback کنترل‌شده
            # ========================================================

            if remaining_courses:

                fallback_days = list(sorted_days)

                # سپس روزهای غیرمطلوب
                for day in range(6):
                    if day not in fallback_days:
                        fallback_days.append(day)

                logger.warning(
                    f"⚠️ استاد {instructor_code} - "
                    f"{len(remaining_courses)} درس وارد fallback شدند"
                )

                for day in fallback_days:

                    if not remaining_courses:
                        break

                    # برای روز مطلوب، نزدیک‌ترین اسلات به مطلوبیت
                    if day in day_preferences:

                        while remaining_courses:

                            selected = choose_next_course(
                                remaining_courses=remaining_courses,
                                day_preferences=day_preferences[day],
                                occupied_slots=occupied[day],
                                mode="fallback"
                            )

                            if selected is None:
                                break

                            queue_index = selected["queue_index"]
                            course = selected["course"]
                            candidate = selected["candidate"]

                            assign_course(
                                course=course,
                                instructor_code=instructor_code,
                                day=day,
                                candidate=candidate,
                                match_level="preferred_day_fallback",
                                tolerance=None
                            )

                            occupied[day].append(
                                (
                                    candidate["slot_start"],
                                    candidate["slot_end"]
                                )
                            )

                            remaining_courses.pop(queue_index)

                    # برای روز غیرمطلوب، فقط اسلات آزاد
                    else:

                        while remaining_courses:

                            available = []

                            for queue_index, course in enumerate(
                                    remaining_courses
                            ):

                                for slot in get_course_slots(course):

                                    if not is_conflict(
                                            occupied[day],
                                            slot[0],
                                            slot[1]
                                    ):
                                        available.append({
                                            "queue_index": queue_index,
                                            "course": course,
                                            "slot": slot
                                        })
                                        break

                            if not available:
                                break

                            available.sort(
                                key=lambda item: (
                                    -item["course"].get(
                                        "priority_score",
                                        0
                                    ),
                                    item["queue_index"]
                                )
                            )

                            selected = available[0]

                            queue_index = selected["queue_index"]
                            course = selected["course"]
                            slot = selected["slot"]

                            candidate = {
                                "slot_start": slot[0],
                                "slot_end": slot[1],
                                "score": 0,
                                "distance": None,
                                "fully_inside": False,
                                "start_inside": False,
                                "overlap_minutes": 0
                            }

                            assign_course(
                                course=course,
                                instructor_code=instructor_code,
                                day=day,
                                candidate=candidate,
                                match_level="fallback_non_preferred_day",
                                tolerance=None
                            )

                            occupied[day].append(slot)
                            remaining_courses.pop(queue_index)

            # ========================================================
            # دروس غیرقابل تخصیص
            # ========================================================

            for course in remaining_courses:
                course["day"] = None
                course["start"] = None
                course["end"] = None
                course["schedule_match_level"] = "unassigned"
                course["schedule_tolerance"] = None
                course["schedule_match_score"] = 0
                course["unassigned_reason"] = (
                    f"هیچ اسلات آزاد و مناسب برای استاد "
                    f"{instructor_code} پیدا نشد"
                )

                unassigned.append(course)

                logger.error(
                    f"❌ درس '{course.get('course_name')}' "
                    f"برای استاد {instructor_code} زمان‌بندی نشد"
                )

        # ------------------------------------------------------------
        # کنترل نهایی
        # ------------------------------------------------------------

        processed_courses = {
            id(course)
            for course in assigned + unassigned
        }

        for course in courses_with_instructor:

            if id(course) in processed_courses:
                continue

            course["day"] = None
            course["start"] = None
            course["end"] = None
            course["schedule_match_level"] = "unassigned"
            course["schedule_tolerance"] = None
            course["unassigned_reason"] = (
                "درس پس از تخصیص استاد در هیچ مرحله‌ای زمان‌بندی نشد"
            )

            unassigned.append(course)

        return assigned, unassigned
    # ============================================================
    # مرحله ۶: کارآموزی/پروژه
    # ============================================================
    def _assign_internship_instructors(
            self,
            internship_courses: List[Dict],
            teaching_prefs: Dict,
            instructor_data: Dict
    ) -> Tuple[List[Dict], List[Dict]]:
        assigned = []
        unassigned = []

        for course in internship_courses:
            course_code = normalize_code(course.get("unique_code", ""))
            preferred_instructors = teaching_prefs.get(course_code, [])

            if not preferred_instructors:
                logger.warning(f"⚠️ کارآموزی/پروژه '{course.get('course_name')}' - هیچ استاد واجدشرایطی یافت نشد")
                course["instructor_code"] = None
                course["instructor_name"] = None
                course["final_score"] = 0
                course["manual_required"] = True
                course["unassigned_reason"] = "هیچ استاد واجد شرطی برای درس کارآموزی/پروژه ثبت نشده است"
                unassigned.append(course)
                continue

            inst_code = preferred_instructors[0]
            inst_name = instructor_data['names'].get(inst_code, inst_code)

            course["instructor_code"] = inst_code
            course["instructor_name"] = inst_name
            course["day"] = None
            course["start"] = None
            course["end"] = None
            course["final_score"] = calculate_final_score(course)
            course["manual_required"] = False
            assigned.append(course)
            logger.info(
                f"✅ کارآموزی/پروژه '{course.get('course_name')}' گروه {course.get('group_number')} → استاد {inst_name}")

        return assigned, unassigned

    # ============================================================
    # مرحله ۷: گزارش نهایی
    # ============================================================
    def _generate_final_report(
            self,
            assigned: List[Dict],
            unassigned: List[Dict],
            instructor_data: Dict,
            instructor_used_units: Dict,
            mismatch_details: Optional[List[Dict]] = None,
            total_input_courses: Optional[int] = None
    ) -> None:
        """
        تولید گزارش نهایی زمان‌بندی.

        پارامتر total_input_courses:
            تعداد کل رکوردهای ورودی سبد در مرحله اول.
            در صورت ارسال، برای محاسبه تعداد کل کلاس‌ها استفاده می‌شود.
        """

        DAY_LABELS = {
            1: "شنبه",
            2: "یکشنبه",
            3: "دوشنبه",
            4: "سه‌شنبه",
            5: "چهارشنبه",
            6: "پنجشنبه",
            7: "جمعه",
        }

        def safe_text(value, default="نامشخص") -> str:
            if value is None:
                return default

            value = str(value).strip()

            return value if value else default

        def normalize_code(value) -> str:
            if value is None:
                return ""

            return str(value).strip()

        def get_course_code(item: Dict) -> str:
            possible_keys = (
                "unique_code",
                "course_code",
                "lesson_code",
                "course_id",
                "lesson_id",
                "code",
                "id",
            )

            for key in possible_keys:
                value = item.get(key)

                if value is not None and str(value).strip():
                    return normalize_code(value)

            return ""

        def get_group_number(item: Dict) -> str:
            possible_keys = (
                "group_number",
                "group",
                "class_group",
                "group_no",
            )

            for key in possible_keys:
                value = item.get(key)

                if value is not None and str(value).strip():
                    return normalize_code(value)

            return ""

        def get_instructor_code(item: Dict) -> str:
            possible_keys = (
                "instructor_code",
                "teacher_code",
                "professor_code",
                "teacher_id",
                "instructor_id",
            )

            for key in possible_keys:
                value = item.get(key)

                if value is not None and str(value).strip():
                    return normalize_code(value)

            return ""

        def get_display_day(value) -> str:
            """
            تبدیل روزهای صفرمبنا و یک‌مبنا به نام فارسی.
            الگوریتم زمان‌بندی فعلی صفرمبنا است:
                0 شنبه
                1 یکشنبه
                2 دوشنبه
                3 سه‌شنبه
                4 چهارشنبه
                5 پنجشنبه
                6 جمعه
            """

            zero_based_days = {
                0: "شنبه",
                1: "یکشنبه",
                2: "دوشنبه",
                3: "سه‌شنبه",
                4: "چهارشنبه",
                5: "پنجشنبه",
                6: "جمعه",
            }

            one_based_days = {
                1: "شنبه",
                2: "یکشنبه",
                3: "دوشنبه",
                4: "سه‌شنبه",
                5: "چهارشنبه",
                6: "پنجشنبه",
                7: "جمعه",
            }

            if value is None:
                return "نامشخص"

            if isinstance(value, bool):
                return "نامشخص"

            if isinstance(value, int):
                return zero_based_days.get(
                    value,
                    str(value)
                )

            value_text = str(value).strip()

            if not value_text:
                return "نامشخص"

            if value_text.isdigit():
                numeric_day = int(value_text)

                # چون الگوریتم زمان‌بندی شما روز شنبه را ۰ تولید می‌کند،
                # اعداد ۰ تا ۶ صفرمبنا در نظر گرفته می‌شوند.
                return zero_based_days.get(
                    numeric_day,
                    one_based_days.get(
                        numeric_day,
                        value_text
                    )
                )

            return value_text

        def get_instructor_name(
                instructor_code,
                item: Optional[Dict] = None
        ) -> str:
            item = item or {}

            direct_name = (
                    item.get("instructor_name")
                    or item.get("teacher_name")
                    or item.get("professor_name")
            )

            if direct_name:
                return safe_text(direct_name)

            names = instructor_data.get("names") or {}

            code_text = normalize_code(instructor_code)

            if code_text in names:
                return safe_text(names[code_text])

            try:
                code_int = int(code_text)

                if code_int in names:
                    return safe_text(names[code_int])
            except (TypeError, ValueError):
                pass

            return code_text or "نامشخص"

        def get_max_units(instructor_code):
            max_units_map = instructor_data.get("max_units") or {}

            code_text = normalize_code(instructor_code)

            if code_text in max_units_map:
                return max_units_map[code_text]

            try:
                code_int = int(code_text)

                if code_int in max_units_map:
                    return max_units_map[code_int]
            except (TypeError, ValueError):
                pass

            return None

        def to_float(value, default=0.0) -> float:
            try:
                return float(value)
            except (TypeError, ValueError):
                return default

        logger.info("=" * 100)
        logger.info("📊 گزارش نهایی زمان‌بندی")
        logger.info("=" * 100)

        # ------------------------------------------------------------
        # آمار اصلی
        # ------------------------------------------------------------

        total_assigned = len(assigned or [])
        total_unassigned = len(unassigned or [])

        accounted_courses = (
                total_assigned
                + total_unassigned
        )

        if total_input_courses is not None:
            total_courses = max(
                int(total_input_courses),
                accounted_courses
            )
        else:
            total_courses = accounted_courses

        missing_from_result = max(
            total_courses - accounted_courses,
            0
        )

        success_rate = (
            total_assigned / total_courses * 100
            if total_courses > 0
            else 0.0
        )

        logger.info(
            "📚 تعداد کل کلاس‌های ورودی: %s",
            total_courses
        )

        logger.info(
            "✅ کلاس‌های تخصیص‌یافته: %s",
            total_assigned
        )

        logger.info(
            "❌ کلاس‌های تخصیص‌نیافته: %s",
            total_unassigned
        )

        logger.info(
            "⚠️ کلاس‌های خارج‌شده از خروجی تخصیص: %s",
            missing_from_result
        )

        logger.info(
            "📈 نرخ تخصیص: %.2f%%",
            success_rate
        )

        # ------------------------------------------------------------
        # گزارش وضعیت تطابق
        # ------------------------------------------------------------

        logger.info("-" * 100)
        logger.info("🔎 گزارش وضعیت تطابق")

        if mismatch_details is None:
            logger.info(
                "ℹ️ اطلاعات عدم تطابق برای گزارش ارسال نشده است"
            )
        else:
            status_counts = {
                "full": 0,
                "partial": 0,
                "none": 0,
                "unassigned": 0,
                "acceptable_time": 0,
                "preferred_time_occupied": 0,
                "real_conflict": 0,
                "unknown": 0,
            }

            for item in mismatch_details:
                status = safe_text(
                    item.get("status"),
                    "unknown"
                ).lower()

                if status not in status_counts:
                    status_counts["unknown"] += 1
                else:
                    status_counts[status] += 1

            logger.info(
                "✅ تطابق کامل: %s",
                status_counts["full"]
            )

            logger.info(
                "⚠️ تطابق نسبی: %s",
                status_counts["partial"]
            )

            logger.info(
                "❌ بدون تطابق: %s",
                status_counts["none"]
            )

            logger.info(
                "🚫 تخصیص‌نیافته: %s",
                status_counts["unassigned"]
            )

            logger.info(
                "🕒 تطابق زمانی قابل‌قبول: %s",
                status_counts["acceptable_time"]
            )

            logger.info(
                "🔒 مطلوبیت زمانی اشغال‌شده: %s",
                status_counts["preferred_time_occupied"]
            )

            logger.info(
                "⚡ تداخل واقعی: %s",
                status_counts["real_conflict"]
            )

            logger.info(
                "❔ وضعیت ناشناخته: %s",
                status_counts["unknown"]
            )

            logger.info(
                "📋 مجموع رکوردهای بررسی‌شده: %s",
                len(mismatch_details)
            )

            # --------------------------------------------------------
            # ثبت نمونه دلایل عدم تطابق
            # --------------------------------------------------------

            if mismatch_details:
                logger.info("-" * 100)
                logger.info("📝 نمونه دلایل عدم تطابق:")

                for index, item in enumerate(
                        mismatch_details[:20],
                        start=1
                ):
                    course_name = safe_text(
                        item.get("course_name")
                        or item.get("lesson_name")
                    )

                    group_number = safe_text(
                        item.get("group_number")
                        or item.get("group")
                    )

                    unique_code = (
                            get_course_code(item)
                            or "نامشخص"
                    )

                    instructor_code = get_instructor_code(item)

                    instructor_name = get_instructor_name(
                        instructor_code,
                        item
                    )

                    status = safe_text(
                        item.get("status"),
                        "نامشخص"
                    )

                    reason = safe_text(
                        item.get("reason"),
                        "دلیل ثبت نشده"
                    )

                    day = get_display_day(
                        item.get("day")
                    )

                    start = safe_text(
                        item.get("start"),
                        ""
                    )

                    end = safe_text(
                        item.get("end"),
                        ""
                    )

                    time_text = (
                        f"{day} {start}-{end}"
                        if start or end
                        else day
                    )

                    logger.info(
                        "%s. درس: %s | گروه: %s | کد: %s | "
                        "استاد: %s [کد: %s] | وضعیت: %s | "
                        "زمان: %s | دلیل: %s",
                        index,
                        course_name,
                        group_number,
                        unique_code,
                        instructor_name,
                        instructor_code or "نامشخص",
                        status,
                        time_text,
                        reason
                    )

                if len(mismatch_details) > 20:
                    logger.info(
                        "... و %s مورد دیگر",
                        len(mismatch_details) - 20
                    )

        # ------------------------------------------------------------
        # گزارش استفاده از ظرفیت اساتید
        # ------------------------------------------------------------

        logger.info("-" * 100)
        logger.info("📊 استفاده از سقف واحد اساتید:")

        if not instructor_used_units:
            logger.info(
                "ℹ️ اطلاعاتی از واحد تخصیص‌یافته به اساتید وجود ندارد"
            )
        else:
            sorted_instructors = sorted(
                instructor_used_units.items(),
                key=lambda item: str(item[0])
            )

            for inst_code, used_units in sorted_instructors:
                instructor_code = normalize_code(inst_code)

                instructor_name = get_instructor_name(
                    instructor_code
                )

                used_units_value = to_float(
                    used_units,
                    0.0
                )

                max_units = get_max_units(
                    instructor_code
                )

                if max_units is None:
                    logger.warning(
                        "⚠️ سقف واحد استاد %s [کد: %s] پیدا نشد",
                        instructor_name,
                        instructor_code
                    )

                    logger.info(
                        "👨‍🏫 استاد %s [کد: %s]: "
                        "%.0f واحد (سقف واحد نامشخص)",
                        instructor_name,
                        instructor_code,
                        used_units_value
                    )

                    continue

                max_units_value = to_float(
                    max_units,
                    0.0
                )

                if max_units_value > 0:
                    usage_percent = (
                            used_units_value
                            / max_units_value
                            * 100
                    )

                    logger.info(
                        "👨‍🏫 استاد %s [کد: %s]: "
                        "%.0f واحد از %.0f واحد (%.1f%%)",
                        instructor_name,
                        instructor_code,
                        used_units_value,
                        max_units_value,
                        usage_percent
                    )
                else:
                    logger.info(
                        "👨‍🏫 استاد %s [کد: %s]: "
                        "%.0f واحد (سقف واحد نامشخص)",
                        instructor_name,
                        instructor_code,
                        used_units_value
                    )

        # ------------------------------------------------------------
        # گزارش دروس تخصیص‌نیافته
        # ------------------------------------------------------------

        if unassigned:
            logger.info("-" * 100)
            logger.info("❌ دلایل نمونه دروس تخصیص‌نیافته:")

            for index, course in enumerate(
                    unassigned[:20],
                    start=1
            ):
                course_name = safe_text(
                    course.get("course_name")
                    or course.get("lesson_name")
                )

                group_number = safe_text(
                    course.get("group_number")
                    or course.get("group")
                )

                unique_code = (
                        get_course_code(course)
                        or "نامشخص"
                )

                reason = safe_text(
                    course.get("unassigned_reason")
                    or course.get("reason"),
                    "دلیل ثبت نشده"
                )

                logger.info(
                    "%s. درس: %s | گروه: %s | کد: %s | دلیل: %s",
                    index,
                    course_name,
                    group_number,
                    unique_code,
                    reason
                )

            if len(unassigned) > 20:
                logger.info(
                    "... و %s درس تخصیص‌نیافته دیگر",
                    len(unassigned) - 20
                )
        else:
            logger.info("-" * 100)
            logger.info(
                "✅ هیچ درس تخصیص‌نیافته‌ای وجود ندارد"
            )

        # ------------------------------------------------------------
        # نمونه زمان‌های نهایی تخصیص‌یافته
        # ------------------------------------------------------------

        if assigned:
            logger.info("-" * 100)
            logger.info(
                "📋 زمان‌های نهایی تخصیص‌یافته (نمونه):"
            )

            for item in assigned[:20]:
                course_name = safe_text(
                    item.get("course_name")
                    or item.get("lesson_name")
                )

                group_number = safe_text(
                    item.get("group_number")
                    or item.get("group")
                )

                day = get_display_day(
                    item.get("day")
                )

                start = safe_text(
                    item.get("start"),
                    ""
                )

                end = safe_text(
                    item.get("end"),
                    ""
                )

                units = item.get(
                    "units",
                    item.get("course_units", 0)
                )

                logger.info(
                    "   %s گروه %s → %s %s-%s "
                    "(واحد: %s)",
                    course_name,
                    group_number,
                    day,
                    start,
                    end,
                    safe_text(units, "0")
                )

            if len(assigned) > 20:
                logger.info(
                    "   ... و %s تخصیص دیگر",
                    len(assigned) - 20
                )

        logger.info("=" * 100)
    # ============================================================
    # تخصیص دستی
    # ============================================================
    def manual_assign(self, manual_assignments: List[Dict]) -> Dict[str, Any]:
        if not manual_assignments:
            return {"status": "error", "message": "لیست تخصیص دستی خالی است"}

        logger.info(f"🔄 مرحله دوم: تخصیص دستی {len(manual_assignments)} کلاس")

        results = []
        errors = []

        for idx, assign_data in enumerate(manual_assignments):
            instructor_code = assign_data.get("instructor_code")
            day = assign_data.get("day")
            start = assign_data.get("start")
            end = assign_data.get("end")
            course_name = assign_data.get("course_name")
            group_number = assign_data.get("group_number")
            level = assign_data.get("level")
            term = assign_data.get("term")

            if not instructor_code:
                errors.append(f"ردیف {idx + 1}: کد استاد الزامی است")
                continue

            is_internship = is_internship_or_project(assign_data)

            if not is_internship:
                if day is None or not start or not end:
                    errors.append(f"ردیف {idx + 1}: روز، ساعت شروع و پایان برای دروس عادی الزامی است")
                    continue

            instructor = self.db.query(Instructor).filter(Instructor.code == instructor_code).first()
            if not instructor:
                errors.append(f"ردیف {idx + 1}: استاد با کد {instructor_code} یافت نشد")
                continue

            result = {
                "status": "success",
                "course_name": course_name,
                "group_number": group_number,
                "instructor_code": instructor.code,
                "instructor_name": instructor.name,
                "day": day,
                "start": start,
                "end": end,
                "message": f"استاد {instructor.name} با موفقیت تخصیص داده شد"
            }
            results.append(result)

        logger.info(f"✅ مرحله دوم: {len(results)} کلاس با موفقیت تخصیص یافت، {len(errors)} خطا")

        return {
            "status": "success" if not errors else "partial",
            "results": results,
            "errors": errors,
            "total": len(manual_assignments),
            "success_count": len(results),
            "error_count": len(errors)
        }