from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Dict, Any, Optional
import logging
from collections import defaultdict

from app.models.term_course import TermCourse
from app.models.schedule_history import ScheduleHistory
from app.models.course import UniqueCourse
from app.models.basket_item import BasketItem  # اضافه شد
from app.utils.term_normalizer import normalize_term
from app.services.workflow_helpers import (
    parse_row_codes, calculate_final_score, is_bottleneck
)

logger = logging.getLogger(__name__)


class BasketService:
    """
    سرویس شناسایی سبد دروس ترم جاری
    شامل دو مرحله مجزا:
    - مرحله اول: یکپارچه‌سازی دروس ترمیک و افزودن دروس گلوگاهی/پیش‌نیاز با ستون‌های تیک
    - مرحله دوم: افزودن آمارهای فراوانی و ظرفیت از سوابق برنامه‌ریزی
    همچنین شامل متدهای ذخیره و بازیابی سبد در دیتابیس
    """

    def __init__(self, db: Session):
        self.db = db

    # ============================================================
    # مرحله اول: دریافت لیست اولیه دروس با ستون‌های تیک و برآورد ظرفیت
    # ============================================================
    def get_initial_basket(self, semester: str, levels: List[str], year: str = "1403") -> List[Dict[str, Any]]:
        """
        مرحله اول شناسایی سبد:
        - یکپارچه‌سازی دروس ترمیک بر اساس ترم فرد/زوج
        - افزودن دروس گلوگاهی و پیش‌نیازهای缺失
        - بازگشت لیست دروس با ستون‌های:
          level, term, course_name, unique_code, units, course_type,
          from_termic (bool), from_prerequisite (bool),
          from_student_demand (bool), from_manager (bool, قابل ویرایش توسط مدیر),
          estimated_capacity (برآورد ظرفیت از جدول دروس یکتا)
        """
        logger.info(f"شروع مرحله اول سبد - ترم: {semester}, مقاطع: {levels}")
        integrated = self._step1_integrate(semester, levels, year)
        logger.info(f"تعداد دروس یکپارچه‌شده: {len(integrated)}")

        with_flags = self._step2_add_bottleneck(integrated)
        logger.info(f"تعداد دروس پس از افزودن گلوگاهی و پیش‌نیاز: {len(with_flags)}")

        # استخراج کدهای یکتا برای دریافت برآورد ظرفیت
        unique_codes = []
        for course in with_flags:
            code = course.get("unique_code")
            if code and code != "یافت نشد":
                unique_codes.append(code)

        # دریافت برآورد ظرفیت از جدول دروس یکتا
        estimated_capacity_map = {}
        if unique_codes:
            unique_courses = self.db.query(UniqueCourse).filter(
                UniqueCourse.code.in_(unique_codes)
            ).all()
            for uc in unique_courses:
                estimated_capacity_map[uc.code] = uc.estimated_capacity or 0
            logger.info(f"تعداد برآورد ظرفیت دریافت‌شده: {len(estimated_capacity_map)}")

        # ساخت خروجی مرحله اول (با برآورد ظرفیت)
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
        logger.info(f"مرحله اول با موفقیت انجام شد، {len(initial_basket)} درس برگردانده شد.")
        return initial_basket

    # ============================================================
    # مرحله دوم: افزودن آمارهای فراوانی و ظرفیت به سبد (با تقسیم بر تکرار)
    # ============================================================
    def add_statistics_to_basket(self, basket_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        مرحله دوم شناسایی سبد:
        - دریافت لیست دروس از مرحله اول (با ستون‌های تیک و estimated_capacity)
        - محاسبه میانگین فراوانی و ظرفیت از سوابق برنامه‌ریزی
        - افزودن ستون‌های: avg_in_mehr, avg_in_bahman, avg_capacity_in_mehr, avg_capacity_in_bahman
        - محاسبه required_classes و سپس تقسیم آن بر تعداد تکرار هر درس در لیست جاری
        - بازگشت لیست کامل با حفظ تمام ستون‌های قبلی
        """
        if not basket_data:
            logger.warning("داده‌های سبد برای افزودن آمار خالی است.")
            return []

        logger.info(f"شروع مرحله دوم سبد - تعداد دروس: {len(basket_data)}")
        courses = [course.copy() for course in basket_data]

        # استخراج کدهای یکتا و شمارش تعداد تکرار هر کد در لیست جاری
        codes = []
        current_count = defaultdict(int)
        for c in courses:
            code = c.get("unique_code")
            if code and code != "یافت نشد":
                codes.append(code)
                current_count[code] += 1

        logger.info(f"تعداد کدهای یکتای معتبر: {len(codes)}")
        logger.info(f"تعداد تکرار کدها: {dict(current_count)}")

        if not codes:
            logger.warning("هیچ کد یکتای معتبری یافت نشد، ستون‌های آماری صفر می‌شوند.")
            for c in courses:
                c["avg_in_mehr"] = 0
                c["avg_in_bahman"] = 0
                c["avg_capacity_in_mehr"] = 0
                c["avg_capacity_in_bahman"] = 0
                c["required_classes"] = 1
                if "estimated_capacity" not in c:
                    c["estimated_capacity"] = 0
            return courses

        # دریافت برآورد ظرفیت از جدول دروس یکتا (در صورت نیاز)
        estimated_capacity_map = {}
        if codes:
            unique_courses = self.db.query(UniqueCourse).filter(UniqueCourse.code.in_(codes)).all()
            for uc in unique_courses:
                estimated_capacity_map[uc.code] = uc.estimated_capacity or 0
            logger.info(f"تعداد دروس یکتا یافت شده: {len(estimated_capacity_map)}")

        # دریافت داده‌های تاریخی (تعداد دفعات و میانگین ظرفیت)
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

        logger.info(f"تعداد رکوردهای تاریخی یافت شده: {len(history_data)}")

        # گروه‌بندی بر اساس کد و ترم
        course_hist = defaultdict(lambda: {'mehr': {'counts': [], 'caps': []}, 'bahman': {'counts': [], 'caps': []}})
        for rec in history_data:
            code = rec.ref_unique_course_code
            sem = rec.semester
            try:
                sem_int = int(sem)
            except:
                sem_int = 0
            last_digit = abs(sem_int) % 10 if sem_int else 0
            if last_digit == 1:  # مهر
                course_hist[code]['mehr']['counts'].append(rec.cnt)
                if rec.avg_cap and rec.avg_cap > 0:
                    course_hist[code]['mehr']['caps'].append(rec.avg_cap)
            elif last_digit == 2:  # بهمن
                course_hist[code]['bahman']['counts'].append(rec.cnt)
                if rec.avg_cap and rec.avg_cap > 0:
                    course_hist[code]['bahman']['caps'].append(rec.avg_cap)

        # محاسبه میانگین‌ها
        historical_avg_mehr = {}
        historical_avg_bahman = {}
        avg_cap_mehr = {}
        avg_cap_bahman = {}
        for code, data in course_hist.items():
            historical_avg_mehr[code] = sum(data['mehr']['counts']) / len(data['mehr']['counts']) if data['mehr']['counts'] else 0
            historical_avg_bahman[code] = sum(data['bahman']['counts']) / len(data['bahman']['counts']) if data['bahman']['counts'] else 0
            avg_cap_mehr[code] = sum(data['mehr']['caps']) / len(data['mehr']['caps']) if data['mehr']['caps'] else 0
            avg_cap_bahman[code] = sum(data['bahman']['caps']) / len(data['bahman']['caps']) if data['bahman']['caps'] else 0

        logger.info(f"تعداد کدهایی که دارای آمار مهر هستند: {len(historical_avg_mehr)}")
        logger.info(f"تعداد کدهایی که دارای آمار بهمن هستند: {len(historical_avg_bahman)}")

        # میانگین کلی ظرفیت (در صورت نیاز)
        avg_capacity_map = {}
        if codes:
            cap_records = self.db.query(
                ScheduleHistory.ref_unique_course_code,
                func.avg(ScheduleHistory.max_capacity).label('avg_cap')
            ).filter(ScheduleHistory.ref_unique_course_code.in_(codes)).group_by(
                ScheduleHistory.ref_unique_course_code
            ).all()
            avg_capacity_map = {r.ref_unique_course_code: r.avg_cap or 0 for r in cap_records}

        # افزودن ستون‌های آماری به هر درس و تقسیم required_classes بر تعداد تکرار
        result = []
        for course in courses:
            code = course.get("unique_code")
            if not code or code == "یافت نشد":
                # بدون کد معتبر، مقادیر صفر
                course["avg_in_mehr"] = 0
                course["avg_in_bahman"] = 0
                course["avg_capacity_in_mehr"] = 0
                course["avg_capacity_in_bahman"] = 0
                course["required_classes"] = 1
                if "estimated_capacity" not in course:
                    course["estimated_capacity"] = 0
                result.append(course)
                continue

            # دریافت تعداد تکرار این کد در لیست جاری
            count_in_current = current_count.get(code, 1)

            # مقادیر آماری
            avg_mehr = round(historical_avg_mehr.get(code, 0))
            avg_bahman = round(historical_avg_bahman.get(code, 0))
            avg_cap_mehr_val = round(avg_cap_mehr.get(code, 0))
            avg_cap_bahman_val = round(avg_cap_bahman.get(code, 0))
            estimated_capacity = course.get("estimated_capacity", 0) or estimated_capacity_map.get(code, 0)

            # محاسبه تعداد کلاس‌های مورد نیاز
            effective_capacity = estimated_capacity or avg_cap_mehr_val or avg_capacity_map.get(code, 0) or 30
            if avg_mehr > 0 and avg_cap_mehr_val > 0:
                required_classes = round((avg_mehr * avg_cap_mehr_val) / effective_capacity)
            else:
                required_classes = 1
            required_classes = max(1, required_classes)

            # ===== تقسیم بر تعداد تکرار در لیست جاری (نیازمندی اصلی) =====
            if count_in_current > 1:
                required_classes = max(1, round(required_classes / count_in_current))
                logger.info(f"برای کد {code} تعداد کلاس‌های مورد نیاز از {required_classes * count_in_current} به {required_classes} تقسیم شد (تعداد تکرار: {count_in_current})")

            # افزودن به دیکشنری - حفظ تمام ستون‌های قبلی
            course["avg_in_mehr"] = avg_mehr
            course["avg_in_bahman"] = avg_bahman
            course["avg_capacity_in_mehr"] = avg_cap_mehr_val
            course["avg_capacity_in_bahman"] = avg_cap_bahman_val
            course["required_classes"] = required_classes
            if "estimated_capacity" not in course or course["estimated_capacity"] == 0:
                course["estimated_capacity"] = estimated_capacity
            result.append(course)

        logger.info(f"مرحله دوم با موفقیت انجام شد، {len(result)} درس برگردانده شد.")
        return result

    # ============================================================
    # متدهای ذخیره و بازیابی سبد در دیتابیس
    # ============================================================

    def save_basket(self, basket_items: List[Dict[str, Any]], workflow_id: Optional[int] = None, semester: str = "") -> List[BasketItem]:
        """
        ذخیره‌سازی سبد دروس (کلاس‌های تولید شده) در دیتابیس
        """
        if not basket_items:
            logger.warning("لیست سبد برای ذخیره خالی است.")
            return []

        logger.info(f"شروع ذخیره‌سازی سبد - تعداد رکوردها: {len(basket_items)}")

        # حذف رکوردهای قبلی این workflow (در صورت وجود)
        if workflow_id:
            deleted = self.db.query(BasketItem).filter(BasketItem.workflow_id == workflow_id).delete()
            if deleted:
                logger.info(f"{deleted} رکورد قبلی برای workflow {workflow_id} حذف شد.")

        saved_items = []
        for item_data in basket_items:
            basket_item = BasketItem(
                level=item_data.get("level", ""),
                term=item_data.get("term", ""),
                course_name=item_data.get("course_name", ""),
                unique_code=item_data.get("unique_code", ""),
                units=item_data.get("units", 0),
                course_type=item_data.get("course_type", ""),
                estimated_capacity=item_data.get("estimated_capacity", 0),
                required_classes=item_data.get("required_classes", 1),
                group_number=item_data.get("group_number", 1),
                avg_in_mehr=item_data.get("avg_in_mehr", 0),
                avg_in_bahman=item_data.get("avg_in_bahman", 0),
                avg_capacity_in_mehr=item_data.get("avg_capacity_in_mehr", 0),
                avg_capacity_in_bahman=item_data.get("avg_capacity_in_bahman", 0),
                from_termic=item_data.get("from_termic", False),
                from_prerequisite=item_data.get("from_prerequisite", False),
                from_student_demand=item_data.get("from_student_demand", False),
                from_manager=item_data.get("from_manager", False),
                workflow_id=workflow_id,
                semester=semester or item_data.get("semester", ""),
            )
            self.db.add(basket_item)
            saved_items.append(basket_item)

        self.db.commit()
        for item in saved_items:
            self.db.refresh(item)

        logger.info(f"تعداد {len(saved_items)} رکورد سبد در دیتابیس ذخیره شد.")
        return saved_items

    def get_basket_by_workflow(self, workflow_id: int) -> List[Dict[str, Any]]:
        """
        دریافت سبد دروس بر اساس workflow_id
        """
        items = self.db.query(BasketItem).filter(BasketItem.workflow_id == workflow_id).all()
        return [item.to_dict() for item in items]

    def get_basket_by_semester(self, semester: str, level: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        دریافت سبد دروس بر اساس ترم و مقطع (اختیاری)
        """
        query = self.db.query(BasketItem).filter(BasketItem.semester == semester)
        if level:
            query = query.filter(BasketItem.level == level)
        items = query.all()
        return [item.to_dict() for item in items]

    def delete_basket_by_workflow(self, workflow_id: int) -> int:
        """
        حذف سبد دروس بر اساس workflow_id
        """
        deleted = self.db.query(BasketItem).filter(BasketItem.workflow_id == workflow_id).delete()
        self.db.commit()
        logger.info(f"{deleted} رکورد سبد برای workflow {workflow_id} حذف شد.")
        return deleted

    # ============================================================
    # متدهای کمکی (مرحله اول)
    # ============================================================

    def _step1_integrate(self, semester: str, levels: List[str], year: str) -> List[Dict]:
        """یکپارچه‌سازی دروس ترمیک بر اساس ترم فرد/زوج"""
        target_terms = [1, 3, 5, 7] if semester == "mehr" else [2, 4, 6, 8]
        term_courses = self.db.query(TermCourse).filter(TermCourse.level.in_(levels)).all()
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
        return integrated

    def _step2_add_bottleneck(self, integrated: List[Dict]) -> List[Dict]:
        """افزودن دروس گلوگاهی و پیش‌نیازهای缺失 با ستون‌های تیک"""
        if not integrated:
            return []

        # ساخت نقشه (level, row_number) -> TermCourse
        all_levels = {c.get("level") for c in integrated}
        all_term_courses = self.db.query(TermCourse).filter(TermCourse.level.in_(all_levels)).all()
        row_to_course = {}
        for tc in all_term_courses:
            row_to_course[(tc.level, tc.row_number)] = tc

        # کدهای یکتای موجود
        existing_codes = {c["unique_code"] for c in integrated if c.get("unique_code") and c["unique_code"] != "یافت نشد"}

        # کدهای یکتای پیش‌نیازها
        prerequisite_codes = set()
        for c in integrated:
            level = c.get("level")
            prereq_str = c.get("prerequisite_codes", "")
            if not prereq_str:
                continue
            for rn in parse_row_codes(prereq_str):
                tc = row_to_course.get((level, rn))
                if tc and tc.unique_course_code and tc.unique_course_code != "یافت نشد":
                    prerequisite_codes.add(tc.unique_course_code)

        # افزودن دروس پیش‌نیاز جدید
        new_codes = prerequisite_codes - existing_codes
        new_courses = []
        if new_codes:
            term_courses_new = self.db.query(TermCourse).filter(TermCourse.unique_course_code.in_(new_codes)).all()
            for tc in term_courses_new:
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
                    "is_bottleneck": is_bottleneck({"course_name": tc.course_name, "unique_code": tc.unique_course_code}),
                })

        # ساخت لیست نهایی با ستون‌های تیک
        result = []
        for c in integrated:
            code = c.get("unique_code")
            new_c = c.copy()
            new_c["from_termic"] = True
            new_c["from_prerequisite"] = code in prerequisite_codes
            new_c["from_student_demand"] = False
            new_c["from_manager"] = False
            new_c["is_bottleneck"] = is_bottleneck(c)
            result.append(new_c)

        result.extend(new_courses)

        # وزن (اختیاری، برای رتبه‌بندی)
        for c in result:
            weight = 0
            if c.get("from_termic"):
                weight += 50
            if c.get("from_prerequisite"):
                weight += 30
            if c.get("is_bottleneck"):
                weight += 20
            if is_bottleneck(c):
                weight += 20
            c["weight"] = weight

        return result

    # ============================================================
    # متدهای کمکی دیگر (در صورت نیاز)
    # ============================================================

    def update_manager_selection(self, basket_data: List[Dict[str, Any]], selected_codes: List[str]) -> List[Dict[str, Any]]:
        """
        به‌روزرسانی ستون from_manager برای دروس انتخابی توسط مدیر
        """
        selected_set = set(selected_codes)
        for course in basket_data:
            code = course.get("unique_code")
            course["from_manager"] = code in selected_set
        return basket_data