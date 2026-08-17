from sqlalchemy.orm import Session
from sqlalchemy import func, Integer
from typing import List, Dict, Any, Optional
import logging
import re
from collections import defaultdict
import random

from app.models.term_course import TermCourse
from app.models.schedule_history import ScheduleHistory
from app.models.teaching_preference import TeachingPreference
from app.models.instructor import Instructor
from app.models.room import Room
from app.models.course import UniqueCourse
from app.utils.term_normalizer import normalize_term, get_target_terms
from app.optimization.cp_sat_solver import solve_room_allocation, optimize_schedule

logger = logging.getLogger(__name__)

# لیست دروس گلوگاهی معروف (برای وزن‌دهی)
BOTTLENECK_COURSES = {
    "ساختمان داده", "معماری کامپیوتر", "ریاضی عمومی ۱", "ریاضی عمومی ۲",
    "معادلات دیفرانسیل", "مدارهای منطقی", "برنامه‌سازی پیشرفته", "ریاضی گسسته",
    "سیستم‌عامل", "هوش مصنوعی", "مهندسی نرم‌افزار", "طراحی سیستم‌های دیجیتال"
}


class WorkflowService:
    def __init__(self, db: Session):
        self.db = db

    # =========================================================
    # گام ۱: یکپارچه‌سازی دروس ترمیک بر اساس ترم فرد/زوج
    # =========================================================
    def step1_integrate_courses(self, semester: str, levels: List[str], year: str = "1403") -> Dict:
        """
        دریافت دروس ترمیک بر اساس ترم‌های فرد/زوج و یکپارچه‌سازی
        """
        target_terms = [1, 3, 5, 7] if semester == "mehr" else [2, 4, 6, 8]

        term_courses = self.db.query(TermCourse).filter(
            TermCourse.level.in_(levels)
        ).all()

        integrated = []
        for tc in term_courses:
            tn = normalize_term(tc.term)
            if tn not in target_terms:
                continue
            integrated.append({
                "id": tc.id,
                "level": tc.level,
                "term": tc.term,
                "term_number": tn,
                "course_name": tc.course_name,
                "unique_code": tc.unique_course_code,
                "unique_name": tc.unique_course_name,
                "units": tc.units,
                "course_type": tc.course_type,
                "prerequisite_codes": tc.prerequisite_row_codes,
                "corequisite_codes": tc.corequisite_row_codes,
            })
        return {
            "semester": semester,
            "levels": levels,
            "year": year,
            "integrated_courses": integrated
        }

    # =========================================================
    # گام ۲: اضافه کردن دروس گلوگاهی و پیش‌نیازهای缺失
    # =========================================================
    def _parse_row_codes(self, row_codes_str: str) -> List[int]:
        """
        تبدیل رشته‌ی کدهای ردیف (مثل '1,2' یا '21، 24') به لیست اعداد
        """
        if not row_codes_str:
            return []
        cleaned = re.sub(r'[^\d]', ' ', row_codes_str)
        return [int(x) for x in cleaned.split() if x.strip()]

    def step2_add_bottleneck_courses(self, integrated_courses: List[Dict]) -> List[Dict]:
        """
        دروس گلوگاهی و پیش‌نیازهایی که در لیست مرحله اول نیستند را اضافه می‌کند.
        همچنین برای همه‌ی دروس، ستون‌های from_termic, from_prerequisite,
        from_student_demand, from_manager, weight را مقداردهی می‌کند.
        """
        if not integrated_courses:
            return []

        # ===== ۱. ساخت نقشه (level, row_number) -> TermCourse =====
        all_levels = set(c.get("level") for c in integrated_courses)
        all_term_courses = self.db.query(TermCourse).filter(
            TermCourse.level.in_(all_levels)
        ).all()
        row_to_course = {}
        for tc in all_term_courses:
            key = (tc.level, tc.row_number)
            row_to_course[key] = tc

        # ===== ۲. استخراج کدهای یکتای دروس موجود =====
        existing_codes = set()
        for c in integrated_courses:
            code = c.get("unique_code")
            if code and code != "یافت نشد":
                existing_codes.add(code)

        # ===== ۳. استخراج کدهای یکتای پیش‌نیازها =====
        prerequisite_codes = set()
        for c in integrated_courses:
            level = c.get("level")
            prereq_str = c.get("prerequisite_codes", "")
            if not prereq_str:
                continue
            row_numbers = self._parse_row_codes(prereq_str)
            for rn in row_numbers:
                tc = row_to_course.get((level, rn))
                if tc and tc.unique_course_code and tc.unique_course_code != "یافت نشد":
                    prerequisite_codes.add(tc.unique_course_code)

        # ===== ۴. افزودن دروس پیش‌نیاز که در لیست موجود نیستند =====
        new_codes = prerequisite_codes - existing_codes
        new_courses = []
        if new_codes:
            term_courses_new = self.db.query(TermCourse).filter(
                TermCourse.unique_course_code.in_(new_codes)
            ).all()
            for tc in term_courses_new:
                is_bottleneck = (
                    tc.course_name in BOTTLENECK_COURSES or
                    (tc.unique_course_code and tc.unique_course_code in BOTTLENECK_COURSES)
                )
                new_courses.append({
                    "id": tc.id,
                    "level": tc.level,
                    "term": tc.term,
                    "term_number": normalize_term(tc.term),
                    "course_name": tc.course_name,
                    "unique_code": tc.unique_course_code,
                    "unique_name": tc.unique_course_name,
                    "units": tc.units,
                    "course_type": tc.course_type,
                    "prerequisite_codes": tc.prerequisite_row_codes,
                    "corequisite_codes": tc.corequisite_row_codes,
                    "from_termic": False,
                    "from_prerequisite": True,
                    "from_student_demand": False,
                    "from_manager": False,
                    "is_bottleneck": is_bottleneck,
                })

        # ===== ۵. ساخت لیست نهایی =====
        result = []
        for c in integrated_courses:
            code = c.get("unique_code")
            is_bottleneck = (
                c.get("course_name") in BOTTLENECK_COURSES or
                (code and code in BOTTLENECK_COURSES)
            )
            new_c = c.copy()
            new_c["from_termic"] = True
            new_c["from_prerequisite"] = (code in prerequisite_codes)
            new_c["from_student_demand"] = False
            new_c["from_manager"] = False
            new_c["is_bottleneck"] = is_bottleneck
            result.append(new_c)

        for nc in new_courses:
            result.append(nc)

        # ===== ۶. محاسبه وزن =====
        for c in result:
            weight = 0
            if c.get("from_termic"):
                weight += 50
            if c.get("from_prerequisite"):
                weight += 30
            if c.get("is_bottleneck"):
                weight += 20
            if c.get("course_name") in BOTTLENECK_COURSES or \
               (c.get("unique_code") and c.get("unique_code") in BOTTLENECK_COURSES):
                weight += 20
            c["weight"] = weight

        return result

    # =========================================================
    # گام ۳: تخمین تعداد گروه بر اساس میانگین فراوانی و ظرفیت در مهر و بهمن
    # =========================================================
    def step3_estimate_demand(self, courses_with_bottleneck: List[Dict]) -> List[Dict]:
        """
        برای هر درس، میانگین تعداد دفعات ارائه در هر ترم (مهر و بهمن) را از سوابق
        به‌صورت میانگین بر روی ترم‌های مختلف محاسبه کرده و سپس بر تعداد تکرار
        آن درس در جدول جاری تقسیم می‌کند. میانگین ظرفیت‌ها نیز به‌صورت
        میانگین ساده از سوابق استخراج می‌شود.
        """
        if not courses_with_bottleneck:
            return []

        # استخراج کدهای یکتا
        codes = []
        for c in courses_with_bottleneck:
            code = c.get("unique_code")
            if code and code != "یافت نشد":
                codes.append(code)

        # ===== دریافت برآورد ظرفیت از جدول دروس یکتا =====
        estimated_capacity_map = {}
        if codes:
            unique_courses = self.db.query(UniqueCourse).filter(
                UniqueCourse.code.in_(codes)
            ).all()
            for uc in unique_courses:
                estimated_capacity_map[uc.code] = uc.estimated_capacity or 0

        # ===== شمارش تعداد تکرار هر کد یکتا در لیست جاری =====
        current_count = defaultdict(int)
        for c in courses_with_bottleneck:
            code = c.get("unique_code")
            if code and code != "یافت نشد":
                current_count[code] += 1

        if not codes:
            for course in courses_with_bottleneck:
                course["avg_in_mehr"] = 0
                course["avg_in_bahman"] = 0
                course["total_avg"] = 0
                course["avg_capacity_in_mehr"] = 0
                course["avg_capacity_in_bahman"] = 0
                course["avg_capacity"] = 0
                course["suggested_groups"] = 1
                course["estimated_capacity"] = 0
                course["required_classes"] = 1
                course["final_score"] = self._calculate_final_score(course)
            return courses_with_bottleneck

        # ===== ۱. دریافت داده‌های تاریخی برای هر کد و هر ترم =====
        history_data = self.db.query(
            ScheduleHistory.ref_unique_course_code,
            ScheduleHistory.semester,
            func.count(ScheduleHistory.id).label('cnt'),
            func.avg(ScheduleHistory.max_capacity).label('avg_cap')
        ).filter(
            ScheduleHistory.ref_unique_course_code.in_(codes),
            ScheduleHistory.max_capacity.isnot(None)
        ).group_by(
            ScheduleHistory.ref_unique_course_code,
            ScheduleHistory.semester
        ).all()

        # ===== ۲. گروه‌بندی داده‌ها بر اساس کد و نوع ترم =====
        course_hist = defaultdict(lambda: {
            'mehr': {'counts': [], 'caps': []},
            'bahman': {'counts': [], 'caps': []}
        })

        for record in history_data:
            code = record.ref_unique_course_code
            semester_val = record.semester
            cnt = record.cnt
            avg_cap = record.avg_cap or 0

            try:
                sem_int = int(semester_val)
            except (ValueError, TypeError):
                sem_int = 0

            last_digit = abs(sem_int) % 10 if sem_int else 0
            if last_digit == 1:
                course_hist[code]['mehr']['counts'].append(cnt)
                if avg_cap > 0:
                    course_hist[code]['mehr']['caps'].append(avg_cap)
            elif last_digit == 2:
                course_hist[code]['bahman']['counts'].append(cnt)
                if avg_cap > 0:
                    course_hist[code]['bahman']['caps'].append(avg_cap)

        # ===== ۳. محاسبه‌ی میانگین‌های تاریخی =====
        historical_avg_mehr = {}
        historical_avg_bahman = {}
        avg_cap_mehr = {}
        avg_cap_bahman = {}

        for code, data in course_hist.items():
            historical_avg_mehr[code] = sum(data['mehr']['counts']) / len(data['mehr']['counts']) if data['mehr']['counts'] else 0
            historical_avg_bahman[code] = sum(data['bahman']['counts']) / len(data['bahman']['counts']) if data['bahman']['counts'] else 0
            avg_cap_mehr[code] = sum(data['mehr']['caps']) / len(data['mehr']['caps']) if data['mehr']['caps'] else 0
            avg_cap_bahman[code] = sum(data['bahman']['caps']) / len(data['bahman']['caps']) if data['bahman']['caps'] else 0

        # ===== ۴. میانگین کلی ظرفیت =====
        avg_capacity_map = {}
        if codes:
            cap_records_all = self.db.query(
                ScheduleHistory.ref_unique_course_code,
                func.avg(ScheduleHistory.max_capacity).label('avg_cap')
            ).filter(
                ScheduleHistory.ref_unique_course_code.in_(codes)
            ).group_by(
                ScheduleHistory.ref_unique_course_code
            ).all()
            avg_capacity_map = {r.ref_unique_course_code: r.avg_cap or 0 for r in cap_records_all}

        # ===== ۵. ظرفیت متوسط اتاق‌ها =====
        rooms = self.db.query(Room).all()
        avg_room_cap = sum(r.capacity for r in rooms) / len(rooms) if rooms else 30

        # ===== ۶. ساخت لیست نهایی با تقسیم بر تعداد تکرار =====
        result = []
        for course in courses_with_bottleneck:
            code = course.get("unique_code")
            count_in_current = current_count.get(code, 1)

            hist_mehr = historical_avg_mehr.get(code, 0)
            hist_bahman = historical_avg_bahman.get(code, 0)

            avg_mehr = round(hist_mehr / count_in_current) if count_in_current > 0 else 0
            avg_bahman = round(hist_bahman / count_in_current) if count_in_current > 0 else 0

            total_avg = avg_mehr + avg_bahman

            avg_cap_mehr_val = round(avg_cap_mehr.get(code, 0))
            avg_cap_bahman_val = round(avg_cap_bahman.get(code, 0))
            avg_cap = avg_capacity_map.get(code, 0)
            estimated_capacity = estimated_capacity_map.get(code, 0)

            effective_capacity = estimated_capacity
            if effective_capacity <= 0:
                effective_capacity = avg_cap_mehr_val if avg_cap_mehr_val > 0 else avg_cap
            if effective_capacity <= 0:
                effective_capacity = 30

            if avg_mehr > 0 and avg_cap_mehr_val > 0:
                required_classes = round((avg_mehr * avg_cap_mehr_val) / effective_capacity)
            else:
                required_classes = 1
            required_classes = max(1, required_classes)

            # ===== تقسیم بر تعداد تکرار در لیست جاری =====
            # اگر درس در چند مقطع تکرار شده، تعداد کلاس‌های مورد نیاز بین آن‌ها تقسیم شود
            if count_in_current > 1:
                required_classes = max(1, round(required_classes / count_in_current))

            suggested_groups = required_classes

            new_course = course.copy()
            new_course["avg_in_mehr"] = avg_mehr
            new_course["avg_in_bahman"] = avg_bahman
            new_course["total_avg"] = total_avg
            new_course["avg_capacity_in_mehr"] = avg_cap_mehr_val
            new_course["avg_capacity_in_bahman"] = avg_cap_bahman_val
            new_course["avg_capacity"] = avg_cap
            new_course["suggested_groups"] = suggested_groups
            new_course["estimated_capacity"] = estimated_capacity
            new_course["required_classes"] = required_classes
            new_course["final_score"] = self._calculate_final_score(new_course)

            result.append(new_course)

        return result

    # =========================================================
    # تابع کمکی برای محاسبه امتیاز نهایی
    # =========================================================
    def _calculate_final_score(self, course: Dict) -> int:
        score = 0
        if course.get("from_termic"):
            score += 10
        if course.get("from_prerequisite"):
            score += 5
        if course.get("from_student_demand"):
            score += 5
        score += course.get("avg_in_mehr", 0)
        score += course.get("avg_in_bahman", 0) // 2
        if course.get("from_manager"):
            score += 10
        return score

    # =========================================================
    # گام ۴: چیدمان روزانه و تولید چند گروه بر اساس required_classes
    # =========================================================
    def step4_day_scheduling(self, courses_with_groups: List[Dict]) -> List[Dict]:
        if not courses_with_groups:
            return []

        two_unit_slots = [
            ("07:30", "09:15"), ("09:16", "11:00"), ("11:01", "12:45"),
            ("13:00", "14:45"), ("14:46", "16:30"), ("16:31", "18:15"), ("18:16", "20:00")
        ]
        three_unit_slots = [
            ("07:30", "10:10"), ("10:11", "12:50"), ("13:00", "15:30"),
            ("15:31", "18:00"), ("18:01", "20:30")
        ]
        days = [0, 1, 2, 3, 4, 5]

        occupancy = defaultdict(set)
        scheduled = []

        for course in courses_with_groups:
            term_number = course.get("term_number", 1)
            level = course.get("level", "")
            units = course.get("units", 2)
            slots = three_unit_slots if units == 3 else two_unit_slots
            num_groups = course.get("suggested_groups", 1)

            for group_idx in range(1, num_groups + 1):
                placed = False
                for day in days:
                    occ = occupancy.get((term_number, level), set())
                    for start, end in slots:
                        conflict = any(s < end and e > start for s, e in occ)
                        if not conflict:
                            new_course = course.copy()
                            new_course["day"] = day
                            new_course["start"] = start
                            new_course["end"] = end
                            new_course["group_number"] = group_idx
                            occ.add((start, end))
                            occupancy[(term_number, level)] = occ
                            scheduled.append(new_course)
                            placed = True
                            break
                    if placed:
                        break
                if not placed:
                    logger.warning(f"برای درس {course.get('course_name')} گروه {group_idx} زمان خالی یافت نشد")
                    new_course = course.copy()
                    new_course["day"] = 0
                    new_course["start"] = slots[0][0]
                    new_course["end"] = slots[0][1]
                    new_course["group_number"] = group_idx
                    scheduled.append(new_course)

        return scheduled

    # =========================================================
    # گام ۵: تخصیص استاد + فیلتر بر اساس امتیاز نهایی
    # =========================================================
    def step5_assign_instructors(self, scheduled_courses: List[Dict]) -> List[Dict]:
        if not scheduled_courses:
            return []

        instructors = self.db.query(Instructor).all()
        instructor_map = {inst.code: inst.name for inst in instructors}

        prefs = self.db.query(TeachingPreference).all()
        course_preferred = defaultdict(list)
        for p in prefs:
            if p.unique_course_code:
                course_preferred[p.unique_course_code].append({
                    "code": p.instructor_code,
                    "name": p.instructor_name
                })

        codes = [c.get("unique_code") for c in scheduled_courses if
                 c.get("unique_code") and c.get("unique_code") != "یافت نشد"]
        history_instructors = defaultdict(set)
        if codes:
            recs = self.db.query(ScheduleHistory).filter(
                ScheduleHistory.ref_unique_course_code.in_(codes)
            ).all()
            for r in recs:
                if r.ref_unique_course_code and r.instructor_code:
                    history_instructors[r.ref_unique_course_code].add(r.instructor_code)

        instructor_occupancy = {}

        for course in scheduled_courses:
            course["final_score"] = self._calculate_final_score(course)

            unique_code = course.get("unique_code")
            day = course.get("day")
            start = course.get("start")
            end = course.get("end")
            assigned = None

            if unique_code:
                candidates = []
                for p in course_preferred.get(unique_code, []):
                    candidates.append(p)
                for h in history_instructors.get(unique_code, []):
                    if not any(c.get("code") == h for c in candidates):
                        candidates.append({"code": h, "name": instructor_map.get(h, h)})

                for cand in candidates:
                    inst_code = cand.get("code")
                    if inst_code:
                        conflict = False
                        for (d, s, e), inst in instructor_occupancy.items():
                            if d == day and s < end and e > start and inst == inst_code:
                                conflict = True
                                break
                        if not conflict:
                            assigned = cand
                            instructor_occupancy[(day, start, end)] = inst_code
                            break

            course["instructor_code"] = assigned.get("code") if assigned else None
            course["instructor_name"] = assigned.get("name") if assigned else None

        filtered_courses = [c for c in scheduled_courses if c.get("final_score", 0) >= 15]
        logger.info(f"تعداد کل گروه‌های پس از فیلتر بر اساس امتیاز نهایی: {len(filtered_courses)}")
        return filtered_courses

    # =========================================================
    # ===== فرایندهای چهارگانه جدید (با پشتیبانی از برآورد ظرفیت) =====
    # =========================================================

    # ---------------------------------------------------------
    # فرایند ۱: شناسایی سبد دروس ترم جاری (مرحله اول + دوم کامل)
    # ---------------------------------------------------------
    def process_basket(self, semester: str, levels: List[str], year: str = "1403") -> List[Dict]:
        """
        ترکیبی از گام‌های ۱ تا ۳ (مراحل ۱ و ۲ سبد) با برآورد ظرفیت.
        خروجی: لیستی از دروس با ستون‌های کلیدی شامل estimated_capacity.
        """
        step1_result = self.step1_integrate_courses(semester, levels, year)
        integrated = step1_result.get("integrated_courses", [])

        step2_result = self.step2_add_bottleneck_courses(integrated)

        step3_result = self.step3_estimate_demand(step2_result)

        basket = []
        for course in step3_result:
            basket.append({
                "level": course.get("level"),
                "term": course.get("term"),
                "course_name": course.get("course_name"),
                "unique_code": course.get("unique_code"),
                "units": course.get("units"),
                "course_type": course.get("course_type"),
                "required_classes": course.get("required_classes", 1),
                "estimated_capacity": course.get("estimated_capacity", 0),
                "final_score": course.get("final_score", 0),
                "from_termic": course.get("from_termic", False),
                "from_prerequisite": course.get("from_prerequisite", False),
                "from_manager": course.get("from_manager", False),
                "avg_in_mehr": course.get("avg_in_mehr", 0),
                "avg_in_bahman": course.get("avg_in_bahman", 0),
                "avg_capacity_in_mehr": course.get("avg_capacity_in_mehr", 0),
                "avg_capacity_in_bahman": course.get("avg_capacity_in_bahman", 0),
            })
        return basket

    # ---------------------------------------------------------
    # متد جدید: دریافت لیست اولیه سبد (مرحله اول بدون آمار)
    # ---------------------------------------------------------
    def get_initial_basket(self, semester: str, levels: List[str], year: str = "1403") -> List[Dict]:
        """
        مرحله اول سبد: فقط لیست دروس با ستون‌های تیک و برآورد ظرفیت.
        بدون آمار فراوانی و ظرفیت تاریخی.
        """
        integrated = self.step1_integrate_courses(semester, levels, year)
        with_flags = self.step2_add_bottleneck_courses(integrated.get("integrated_courses", []))

        # دریافت برآورد ظرفیت از جدول دروس یکتا
        unique_codes = []
        for course in with_flags:
            code = course.get("unique_code")
            if code and code != "یافت نشد":
                unique_codes.append(code)

        estimated_capacity_map = {}
        if unique_codes:
            unique_courses = self.db.query(UniqueCourse).filter(
                UniqueCourse.code.in_(unique_codes)
            ).all()
            for uc in unique_courses:
                estimated_capacity_map[uc.code] = uc.estimated_capacity or 0

        initial_basket = []
        for course in with_flags:
            code = course.get("unique_code")
            estimated_cap = estimated_capacity_map.get(code, 0) if code and code != "یافت نشد" else 0
            initial_basket.append({
                "level": course.get("level"),
                "term": course.get("term"),
                "course_name": course.get("course_name"),
                "unique_code": course.get("unique_code"),
                "estimated_capacity": estimated_cap,
                "units": course.get("units"),
                "course_type": course.get("course_type"),
                "from_termic": course.get("from_termic", False),
                "from_prerequisite": course.get("from_prerequisite", False),
                "from_student_demand": course.get("from_student_demand", False),
                "from_manager": course.get("from_manager", False),
            })
        return initial_basket

    # ---------------------------------------------------------
    # متد جدید: افزودن آمار به سبد (مرحله دوم) - با تقسیم بر تعداد تکرار
    # ---------------------------------------------------------
    def add_statistics_to_basket(self, basket_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        دریافت سبد مرحله اول و افزودن ستون‌های آماری (avg_in_mehr, avg_in_bahman, ...)
        و محاسبه required_classes. تعداد کلاس‌های مورد نیاز بر اساس تکرار هر درس در لیست جاری تقسیم می‌شود.
        """
        if not basket_data:
            return []

        courses = [course.copy() for course in basket_data]

        codes = []
        for c in courses:
            code = c.get("unique_code")
            if code and code != "یافت نشد":
                codes.append(code)

        # شمارش تعداد تکرار هر کد در لیست جاری
        current_count = defaultdict(int)
        for c in courses:
            code = c.get("unique_code")
            if code and code != "یافت نشد":
                current_count[code] += 1

        if not codes:
            for c in courses:
                c["avg_in_mehr"] = 0
                c["avg_in_bahman"] = 0
                c["avg_capacity_in_mehr"] = 0
                c["avg_capacity_in_bahman"] = 0
                c["required_classes"] = 1
            return courses

        # دریافت برآورد ظرفیت (در صورت نیاز)
        estimated_capacity_map = {}
        if codes:
            unique_courses = self.db.query(UniqueCourse).filter(UniqueCourse.code.in_(codes)).all()
            for uc in unique_courses:
                estimated_capacity_map[uc.code] = uc.estimated_capacity or 0

        # داده‌های تاریخی
        history_data = self.db.query(
            ScheduleHistory.ref_unique_course_code,
            ScheduleHistory.semester,
            func.count(ScheduleHistory.id).label('cnt'),
            func.avg(ScheduleHistory.max_capacity).label('avg_cap')
        ).filter(
            ScheduleHistory.ref_unique_course_code.in_(codes),
            ScheduleHistory.max_capacity.isnot(None)
        ).group_by(
            ScheduleHistory.ref_unique_course_code,
            ScheduleHistory.semester
        ).all()

        course_hist = defaultdict(lambda: {'mehr': {'counts': [], 'caps': []}, 'bahman': {'counts': [], 'caps': []}})
        for rec in history_data:
            code = rec.ref_unique_course_code
            sem = rec.semester
            try:
                sem_int = int(sem)
            except:
                sem_int = 0
            last_digit = abs(sem_int) % 10 if sem_int else 0
            if last_digit == 1:
                course_hist[code]['mehr']['counts'].append(rec.cnt)
                if rec.avg_cap and rec.avg_cap > 0:
                    course_hist[code]['mehr']['caps'].append(rec.avg_cap)
            elif last_digit == 2:
                course_hist[code]['bahman']['counts'].append(rec.cnt)
                if rec.avg_cap and rec.avg_cap > 0:
                    course_hist[code]['bahman']['caps'].append(rec.avg_cap)

        historical_avg_mehr = {}
        historical_avg_bahman = {}
        avg_cap_mehr = {}
        avg_cap_bahman = {}
        for code, data in course_hist.items():
            historical_avg_mehr[code] = sum(data['mehr']['counts']) / len(data['mehr']['counts']) if data['mehr']['counts'] else 0
            historical_avg_bahman[code] = sum(data['bahman']['counts']) / len(data['bahman']['counts']) if data['bahman']['counts'] else 0
            avg_cap_mehr[code] = sum(data['mehr']['caps']) / len(data['mehr']['caps']) if data['mehr']['caps'] else 0
            avg_cap_bahman[code] = sum(data['bahman']['caps']) / len(data['bahman']['caps']) if data['bahman']['caps'] else 0

        avg_capacity_map = {}
        if codes:
            cap_records = self.db.query(
                ScheduleHistory.ref_unique_course_code,
                func.avg(ScheduleHistory.max_capacity).label('avg_cap')
            ).filter(ScheduleHistory.ref_unique_course_code.in_(codes)).group_by(
                ScheduleHistory.ref_unique_course_code
            ).all()
            avg_capacity_map = {r.ref_unique_course_code: r.avg_cap or 0 for r in cap_records}

        result = []
        for course in courses:
            code = course.get("unique_code")
            if not code or code == "یافت نشد":
                course["avg_in_mehr"] = 0
                course["avg_in_bahman"] = 0
                course["avg_capacity_in_mehr"] = 0
                course["avg_capacity_in_bahman"] = 0
                course["required_classes"] = 1
                if "estimated_capacity" not in course:
                    course["estimated_capacity"] = 0
                result.append(course)
                continue

            count_in_current = current_count.get(code, 1)
            avg_mehr = round(historical_avg_mehr.get(code, 0))
            avg_bahman = round(historical_avg_bahman.get(code, 0))
            avg_cap_mehr_val = round(avg_cap_mehr.get(code, 0))
            avg_cap_bahman_val = round(avg_cap_bahman.get(code, 0))
            estimated_capacity = course.get("estimated_capacity", 0) or estimated_capacity_map.get(code, 0)

            effective_capacity = estimated_capacity or avg_cap_mehr_val or avg_capacity_map.get(code, 0) or 30
            if avg_mehr > 0 and avg_cap_mehr_val > 0:
                required_classes = round((avg_mehr * avg_cap_mehr_val) / effective_capacity)
            else:
                required_classes = 1
            required_classes = max(1, required_classes)

            # ===== تقسیم بر تعداد تکرار در لیست جاری =====
            if count_in_current > 1:
                required_classes = max(1, round(required_classes / count_in_current))

            course["avg_in_mehr"] = avg_mehr
            course["avg_in_bahman"] = avg_bahman
            course["avg_capacity_in_mehr"] = avg_cap_mehr_val
            course["avg_capacity_in_bahman"] = avg_cap_bahman_val
            course["required_classes"] = required_classes
            if "estimated_capacity" not in course or course["estimated_capacity"] == 0:
                course["estimated_capacity"] = estimated_capacity
            result.append(course)

        return result

    # ---------------------------------------------------------
    # فرایند ۲: زمان‌بندی استاد و درس (بدون اتاق)
    # ---------------------------------------------------------
    def process_schedule(self, basket: List[Dict]) -> List[Dict]:
        if not basket:
            return []

        scheduled = self.step4_day_scheduling(basket)
        with_instructors = self.step5_assign_instructors(scheduled)

        for item in with_instructors:
            item.pop("room", None)
            item.pop("room_id", None)
            item.pop("room_name", None)
            item.pop("capacity", None)

        return with_instructors

    # ---------------------------------------------------------
    # فرایند ۳: تخصیص اتاق
    # ---------------------------------------------------------
    def process_rooms(self, schedule_with_instructors: List[Dict]) -> List[Dict]:
        if not schedule_with_instructors:
            return []

        rooms = self.db.query(Room).all()
        if not rooms:
            logger.warning("هیچ اتاقی در دیتابیس وجود ندارد.")
            return schedule_with_instructors

        try:
            allocated = solve_room_allocation(schedule_with_instructors, rooms)
            return allocated
        except (ImportError, AttributeError) as e:
            logger.warning(f"تابع solve_room_allocation در دسترس نیست، استفاده از روش اکتشافی. خطا: {e}")
            return self._heuristic_room_allocation(schedule_with_instructors, rooms)

    def _heuristic_room_allocation(self, schedule: List[Dict], rooms: List[Room]) -> List[Dict]:
        sorted_rooms = sorted(rooms, key=lambda r: r.capacity)
        room_occupancy = defaultdict(dict)
        allocated_schedule = []

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
                logger.warning(f"برای کلاس {item.get('course_name')} گروه {item.get('group_number')} اتاق مناسب یافت نشد.")

            allocated_schedule.append(new_item)

        return allocated_schedule

    # ---------------------------------------------------------
    # فرایند ۴: بهینه‌سازی برنامه
    # ---------------------------------------------------------
    def process_optimize(self, schedule_with_rooms: List[Dict]) -> List[Dict]:
        if not schedule_with_rooms:
            return []

        try:
            optimized = optimize_schedule(schedule_with_rooms)
            return optimized
        except (ImportError, AttributeError) as e:
            logger.warning(f"تابع optimize_schedule در دسترس نیست، استفاده از روش اکتشافی. خطا: {e}")
            return self._heuristic_optimize(schedule_with_rooms)

    def _heuristic_optimize(self, schedule: List[Dict]) -> List[Dict]:
        if len(schedule) < 2:
            return schedule

        optimized = [item.copy() for item in schedule]
        by_instructor = defaultdict(list)
        for item in optimized:
            inst = item.get("instructor_code")
            if inst:
                by_instructor[inst].append(item)

        logger.info("بهینه‌سازی اکتشافی اعمال شد (فقط کپی داده).")
        return optimized

        # app/services/workflow_service.py (افزودن متدهای جدید)

        # ... کدهای موجود ...

        # ============================================================
        # متدهای جدید برای مدیریت کلاس‌های زمان‌بندی‌شده
        # ============================================================

        def save_scheduled_classes(
                self,
                classes: List[Dict],
                workflow_id: int,
                semester: str,
                year: str = "1403"
        ) -> List[Dict]:
            """
            ذخیره‌سازی کلاس‌های زمان‌بندی‌شده (بدون اتاق) در دیتابیس
            """
            from app.models.schedule import ScheduledClass

            if not classes:
                logger.warning("لیست کلاس‌ها خالی است")
                return []

            saved_classes = []
            for cls_data in classes:
                # بررسی وجود کلاس تکراری
                existing = self.db.query(ScheduledClass).filter(
                    ScheduledClass.scenario_id == workflow_id,
                    ScheduledClass.course_code == cls_data.get("course_code"),
                    ScheduledClass.group_number == cls_data.get("group_number")
                ).first()

                if existing:
                    # به‌روزرسانی اطلاعات
                    existing.course_title = cls_data.get("course_name")
                    existing.instructor_name = cls_data.get("instructor_name")
                    existing.day = cls_data.get("day")
                    existing.start_time = cls_data.get("start")
                    existing.end_time = cls_data.get("end")
                    existing.predicted_students = cls_data.get("estimated_capacity", 0)
                    existing.semester = semester
                    existing.year = year
                    saved_classes.append(existing.to_dict() if hasattr(existing, 'to_dict') else existing)
                else:
                    new_class = ScheduledClass(
                        course_code=cls_data.get("course_code"),
                        course_title=cls_data.get("course_name"),
                        group_number=cls_data.get("group_number"),
                        instructor_name=cls_data.get("instructor_name"),
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
            logger.info(f"✅ {len(saved_classes)} کلاس زمان‌بندی‌شده ذخیره شد.")
            return [cls.to_dict() if hasattr(cls, 'to_dict') else cls for cls in saved_classes]

        def get_scheduled_classes(self, workflow_id: int) -> List[Dict]:
            """
            دریافت کلاس‌های زمان‌بندی‌شده برای یک workflow
            """
            from app.models.schedule import ScheduledClass

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
                    "semester": cls.semester,
                    "year": cls.year,
                })
            return result

        def update_workflow_status(self, workflow_id: int, status: str) -> bool:
            """
            به‌روزرسانی وضعیت workflow
            """
            from app.models.workflow import ScheduleWorkflow, WorkflowStatus

            workflow = self.db.query(ScheduleWorkflow).filter(
                ScheduleWorkflow.id == workflow_id
            ).first()
            if not workflow:
                return False

            try:
                workflow.status = WorkflowStatus(status)
                self.db.commit()
                return True
            except ValueError:
                logger.error(f"وضعیت '{status}' نامعتبر است")
                return False