from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Dict, Tuple, Optional, Set
import logging
from difflib import get_close_matches

from app.models import OfferedCourse, UniqueCourse
from app.models.term_course import TermCourse
from app.models.schedule_history import ScheduleHistory
from app.models.teaching_preference import TeachingPreference
from app.models.time_preference import TimePreference
from app.services.scoring_service import calculate_course_score, Semester
from app.utils.term_normalizer import normalize_term, get_target_terms

logger = logging.getLogger(__name__)

# لیست دروس گلوگاهی (بر اساس نیازمندی)
BOTTLENECK_COURSES = {
    "ساختمان داده", "معماری کامپیوتر", "ریاضی عمومی ۱", "ریاضی عمومی ۲",
    "معادلات دیفرانسیل", "مدارهای منطقی", "برنامه‌سازی پیشرفته", "ریاضی گسسته",
    "سیستم‌عامل", "هوش مصنوعی", "مهندسی نرم‌افزار", "طراحی سیستم‌های دیجیتال"
}

# تمام مقاطع موجود
ALL_LEVELS = ["پیوسته 1394", "پیوسته 1403", "ناپیوسته"]

# آستانه امتیاز برای انتخاب (افزایش یافته)
SCORE_THRESHOLD = 10  # ← قبلاً ۱ بود


class CourseSelector:
    def __init__(self, db: Session):
        self.db = db
        # کش برای تطبیق فازی نام دروس (بهبود عملکرد)
        self._unique_course_cache = None
        self._offered_title_cache = None

    def _find_unique_code_by_name(self, course_name: str) -> Optional[str]:
        """
        پیدا کردن کد یکتا بر اساس نام درس با استفاده از تطبیق فازی
        """
        if not course_name:
            return None

        # کش کردن لیست عناوین برای بهبود عملکرد
        if self._offered_title_cache is None:
            offered_titles = self.db.query(OfferedCourse.unique_title).distinct().all()
            self._offered_title_cache = [t[0] for t in offered_titles if t[0]]

        # ابتدا روی OfferedCourse.unique_title جستجو می‌کنیم
        matches = get_close_matches(course_name, self._offered_title_cache, n=1, cutoff=0.6)
        if matches:
            offered = self.db.query(OfferedCourse).filter(
                OfferedCourse.unique_title == matches[0]
            ).first()
            if offered and offered.unique_code:
                logger.debug(f"✅ تطبیق نام '{course_name}' → '{matches[0]}' با کد {offered.unique_code}")
                return offered.unique_code

        # اگر پیدا نشد، روی UniqueCourse.title جستجو می‌کنیم
        if self._unique_course_cache is None:
            unique_titles = self.db.query(UniqueCourse.title).distinct().all()
            self._unique_course_cache = [t[0] for t in unique_titles if t[0]]

        matches = get_close_matches(course_name, self._unique_course_cache, n=1, cutoff=0.6)
        if matches:
            unique_course = self.db.query(UniqueCourse).filter(
                UniqueCourse.title == matches[0]
            ).first()
            if unique_course:
                logger.debug(f"✅ تطبیق نام '{course_name}' → '{matches[0]}' با کد {unique_course.code}")
                return unique_course.code

        logger.warning(f"⚠️ نتوانستیم کد یکتایی برای '{course_name}' پیدا کنیم")
        return None

    def _get_term_number(self, term_str: str) -> int:
        """نرمالیزه کردن ترم و برگرداندن عدد"""
        return normalize_term(term_str)

    def select_courses(
            self,
            semester: Semester,
            levels: Optional[List[str]] = None,
            demand_threshold: int = 10,
            max_courses: int = 60,  # ← کاهش به ۶۰
            include_prerequisites: bool = True
    ) -> Tuple[List[Dict], List[Dict]]:
        """
        انتخاب هوشمندانه دروس مناسب برای ترم جاری بر اساس:
        - سیاست نیمسال (مهر: ترم‌های فرد، بهمن: ترم‌های زوج)
        - همه مقاطع مشخص‌شده
        - دروس پیش‌نیاز (حتی اگر در ترم‌های دیگر باشند)
        - امتیازدهی و داده‌های تاریخی
        - مطلوبیت اساتید
        - گلوگاهی بودن
        """
        # تعیین ترم‌های هدف بر اساس نیمسال (به صورت اعداد)
        target_term_numbers = get_target_terms(semester)
        term_type = "فرد" if semester == Semester.MEHR else "زوج"

        # تعیین مقاطع هدف
        target_levels = levels if levels else ALL_LEVELS

        logger.info("=" * 60)
        logger.info(f"📊 شروع انتخاب دروس - نیمسال: {semester.value}, ترم‌های هدف: {target_term_numbers}, مقاطع: {target_levels}")
        logger.info("=" * 60)

        # 1. دریافت همه دروس ترمیک برای مقاطع هدف (بدون فیلتر ترم)
        all_term_courses = self.db.query(TermCourse).filter(
            TermCourse.level.in_(target_levels)
        ).all()

        if not all_term_courses:
            logger.warning(f"هیچ درسی برای مقاطع {target_levels} یافت نشد")
            return [], []

        # فیلتر کردن بر اساس ترم نرمالیزه‌شده
        term_courses = []
        for tc in all_term_courses:
            term_number = self._get_term_number(tc.term)
            if term_number in target_term_numbers:
                # ذخیره term_number در شیء برای استفاده بعدی
                tc._term_number = term_number
                term_courses.append(tc)

        if not term_courses:
            logger.warning(f"هیچ درسی برای ترم‌های {target_term_numbers} در مقاطع {target_levels} یافت نشد")
            return [], []

        logger.info(f"📚 تعداد دروس ترمیک پس از فیلتر ترم: {len(term_courses)}")

        # 2. دریافت دروس ارائه
        offered_courses = {
            oc.unique_code: oc for oc in self.db.query(OfferedCourse).all()
        }
        logger.info(f"📖 تعداد دروس ارائه: {len(offered_courses)}")

        # 3. دریافت داده‌های تاریخی
        historical_demand = {}
        history_records = self.db.query(
            ScheduleHistory.ref_unique_course_code,
            func.count(ScheduleHistory.id).label('count'),
            func.avg(ScheduleHistory.max_capacity).label('avg_capacity')
        ).group_by(ScheduleHistory.ref_unique_course_code).all()

        for record in history_records:
            if record.ref_unique_course_code:
                historical_demand[record.ref_unique_course_code] = {
                    'count': record.count,
                    'avg_capacity': record.avg_capacity or 0
                }
        logger.info(f"📊 تعداد دروس با سابقه تاریخی: {len(historical_demand)}")

        # 4. دریافت مطلوبیت‌های تدریس
        teaching_prefs = self.db.query(TeachingPreference).all()
        course_instructors = {}
        for tp in teaching_prefs:
            if tp.unique_course_code:
                if tp.unique_course_code not in course_instructors:
                    course_instructors[tp.unique_course_code] = []
                course_instructors[tp.unique_course_code].append({
                    'name': tp.instructor_name,
                    'status': tp.status,
                    'cooperation_type': tp.cooperation_type
                })
        logger.info(f"👨‍🏫 تعداد دروس با استاد واجد شرایط: {len(course_instructors)}")

        # 5. پردازش هر درس
        selected = []
        rejected = []
        selected_codes = set()

        logger.info("🔄 شروع پردازش دروس...")

        for idx, tc in enumerate(term_courses, 1):
            term_number = getattr(tc, '_term_number', self._get_term_number(tc.term))

            # پیدا کردن کد یکتا (با تطبیق فازی در صورت نیاز)
            unique_code = tc.unique_course_code
            if not unique_code or unique_code == "یافت نشد":
                # تلاش برای پیدا کردن کد یکتا از طریق نام
                found_code = self._find_unique_code_by_name(tc.course_name)
                if found_code:
                    unique_code = found_code
                    logger.info(f"🔍 کد یکتا برای '{tc.course_name}' از طریق تطبیق نام پیدا شد: {found_code}")
                else:
                    logger.warning(f"⚠️ برای درس '{tc.course_name}' کد یکتا پیدا نشد")

            # پیدا کردن درس ارائه مربوطه
            offered = offered_courses.get(unique_code)

            # استخراج پیش‌نیازها
            prerequisites = []
            prerequisite_codes = []
            if tc.prerequisite_row_codes:
                try:
                    codes = [int(x.strip()) for x in tc.prerequisite_row_codes.split(',') if x.strip()]
                    prereq_courses = self.db.query(TermCourse).filter(
                        TermCourse.row_number.in_(codes),
                        TermCourse.level == tc.level,
                    ).all()
                    for p in prereq_courses:
                        prerequisites.append(p.course_name)
                        if p.unique_course_code and p.unique_course_code != "یافت نشد":
                            prerequisite_codes.append(p.unique_course_code)
                        else:
                            found_prereq_code = self._find_unique_code_by_name(p.course_name)
                            if found_prereq_code:
                                prerequisite_codes.append(found_prereq_code)
                except Exception as e:
                    logger.warning(f"خطا در استخراج پیش‌نیازهای {tc.course_name}: {e}")

            if offered and offered.prerequisite and offered.prerequisite != '-':
                prerequisites.append(offered.prerequisite)

            # استخراج هم‌نیازها
            corequisites = []
            if tc.corequisite_row_codes:
                try:
                    codes = [int(x.strip()) for x in tc.corequisite_row_codes.split(',') if x.strip()]
                    coreq_courses = self.db.query(TermCourse).filter(
                        TermCourse.row_number.in_(codes),
                        TermCourse.level == tc.level,
                    ).all()
                    for c in coreq_courses:
                        corequisites.append(c.course_name)
                except Exception as e:
                    logger.warning(f"خطا در استخراج هم‌نیازهای {tc.course_name}: {e}")

            if offered and offered.corequisite and offered.corequisite != '-':
                corequisites.append(offered.corequisite)

            # داده‌های تاریخی
            hist_data = historical_demand.get(unique_code, {'count': 0, 'avg_capacity': 0})
            historical_count = hist_data['count']
            avg_capacity = hist_data['avg_capacity']

            # بررسی وجود استاد
            instructors = course_instructors.get(unique_code, [])
            has_instructor = len(instructors) > 0

            # گلوگاهی بودن
            is_bottleneck = (
                tc.course_name in BOTTLENECK_COURSES or
                (unique_code and unique_code in BOTTLENECK_COURSES) or
                len(prerequisites) > 2
            )

            # محاسبه امتیاز پایه
            course_data = {
                "id": tc.id,
                "title": tc.course_name,
                "code": unique_code,
                "chart_term": tc.approximate_term or term_number,
                "active": True,
                "chart_required": True,
                "graduation_critical": is_bottleneck,
                "bottleneck": is_bottleneck,
                "historical_demand": avg_capacity or historical_count * 10,
                "direct_requests": 0,
            }

            score, reasons = calculate_course_score(course_data, semester)

            # ===== افزایش امتیاز بر اساس داده‌های تاریخی =====
            if historical_count > 0:
                bonus = min(historical_count * 5, 30)
                score += bonus
                reasons.append(f"📊 این درس در {historical_count} ترم گذشته ارائه شده است")

            if avg_capacity > 30:
                score += 10
                reasons.append(f"📊 میانگین ظرفیت {avg_capacity:.0f} نفر در ترم‌های گذشته")

            # ===== تعیین اولویت‌ها =====
            # 1. دروس با سابقه بالا (≥ ۳ بار) حتماً انتخاب شوند
            must_select = historical_count >= 3

            # 2. دروس گلوگاهی
            is_critical_bottleneck = (
                is_bottleneck and
                (historical_count >= 2 or unique_code in BOTTLENECK_COURSES)
            )

            # 3. دروس با استاد واجد شرایط
            has_qualified_instructor = has_instructor and len(instructors) > 0

            # ===== سایر امتیازات =====
            if is_bottleneck:
                score += 15
                reasons.append("🎯 درس گلوگاهی - ارائه آن ضروری است")
            if offered:
                score += 5
                reasons.append("📖 درس در جدول دروس ارائه موجود است")
            if has_qualified_instructor:
                score += 8
                reasons.append(f"👨‍🏫 {len(instructors)} استاد واجد شرایط وجود دارد")
            if prerequisites:
                score += 3
                reasons.append(f"🔗 دارای {len(prerequisites)} پیش‌نیاز")

            # ===== افزایش امتیاز برای دروس با تقاضای بالا =====
            if avg_capacity > 25:
                score += 5
                reasons.append(f"📈 تقاضای بالا (میانگین ظرفیت {avg_capacity:.0f})")

            # ===== کاهش امتیاز دروس عمومی و اختیاری =====
            if tc.course_type in ["عمومی", "اختیاری", "تمرکز تخصصی اختیاری", "درس های اختیاری همه گرایش ها"]:
                score -= 20
                reasons.append("⚠️ درس عمومی/اختیاری - اولویت کمتر")

            course_info = {
                "term_course_id": tc.id,
                "course_name": tc.course_name,
                "unique_course_code": unique_code,
                "unique_course_name": tc.unique_course_name,
                "units": tc.units,  # ← واحد درس
                "course_type": tc.course_type,
                "approximate_term": tc.approximate_term or term_number,
                "term_number": term_number,
                "prerequisite_row_codes": tc.prerequisite_row_codes,
                "corequisite_row_codes": tc.corequisite_row_codes,
                "description": tc.description,
                "score": round(score, 2),
                "reasons": reasons,
                "offered_course": offered,
                "has_instructor": has_instructor,
                "instructors": instructors,
                "is_bottleneck": is_bottleneck,
                "historical_count": historical_count,
                "avg_capacity": avg_capacity,
                "prerequisites": prerequisites,
                "prerequisite_codes": prerequisite_codes,
                "corequisites": corequisites,
                "year_identified": tc.year_identified,
                "level": tc.level,
                "term": tc.term,
                "must_select": must_select,
                "is_critical_bottleneck": is_critical_bottleneck,
                "has_qualified_instructor": has_qualified_instructor,
                "priority_score": score,
            }

            # ===== تصمیم‌گیری با آستانه بالاتر =====
            # - دروس با سابقه ≥ ۳ بار: حتماً انتخاب
            # - دروس گلوگاهی بحرانی: حتماً انتخاب
            # - دروس با امتیاز ≥ SCORE_THRESHOLD: انتخاب
            if must_select or is_critical_bottleneck or score >= SCORE_THRESHOLD:
                selected.append(course_info)
                if unique_code:
                    selected_codes.add(unique_code)
                logger.debug(f"✅ انتخاب: {tc.course_name} (امتیاز: {score:.1f}, دفعات: {historical_count})")
            else:
                rejected.append(course_info)

        logger.info(f"📊 تعداد دروس انتخاب‌شده اولیه: {len(selected)}")

        # 7. اضافه کردن دروس پیش‌نیاز
        if include_prerequisites:
            prereq_codes_to_add = set()
            for course in selected:
                prereq_codes_to_add.update(course.get("prerequisite_codes", []))

            prereq_codes_to_add = {c for c in prereq_codes_to_add if c and c != "یافت نشد"}

            if prereq_codes_to_add:
                logger.info(f"🔗 تعداد کدهای پیش‌نیاز برای اضافه شدن: {len(prereq_codes_to_add)}")
                prereq_courses = self.db.query(TermCourse).filter(
                    TermCourse.unique_course_code.in_(prereq_codes_to_add)
                ).all()

                for pc in prereq_courses:
                    if pc.unique_course_code not in selected_codes:
                        offered = offered_courses.get(pc.unique_course_code)
                        # محاسبه امتیاز برای پیش‌نیاز
                        course_data = {
                            "id": pc.id,
                            "title": pc.course_name,
                            "code": pc.unique_course_code,
                            "chart_term": pc.approximate_term or self._get_term_number(pc.term),
                            "active": True,
                            "chart_required": True,
                            "graduation_critical": False,
                            "bottleneck": False,
                            "historical_demand": 0,
                            "direct_requests": 0,
                        }
                        score, reasons = calculate_course_score(course_data, semester)
                        score += 20  # امتیاز ویژه برای پیش‌نیازها
                        reasons.append("🔗 این درس به عنوان پیش‌نیاز دروس انتخابی اضافه شده است")

                        prereq_info = {
                            "term_course_id": pc.id,
                            "course_name": pc.course_name,
                            "unique_course_code": pc.unique_course_code,
                            "unique_course_name": pc.unique_course_name,
                            "units": pc.units,
                            "course_type": pc.course_type,
                            "approximate_term": pc.approximate_term,
                            "term_number": self._get_term_number(pc.term),
                            "prerequisite_row_codes": pc.prerequisite_row_codes,
                            "corequisite_row_codes": pc.corequisite_row_codes,
                            "description": pc.description,
                            "score": round(score, 2),
                            "reasons": reasons,
                            "offered_course": offered,
                            "has_instructor": False,
                            "instructors": [],
                            "is_bottleneck": False,
                            "historical_count": 0,
                            "avg_capacity": 0,
                            "prerequisites": [],
                            "prerequisite_codes": [],
                            "corequisites": [],
                            "year_identified": pc.year_identified,
                            "level": pc.level,
                            "term": pc.term,
                            "is_prerequisite": True,
                            "must_select": True,
                            "priority_score": score,
                        }
                        selected.append(prereq_info)
                        if pc.unique_course_code:
                            selected_codes.add(pc.unique_course_code)
                        logger.info(f"➕ پیش‌نیاز اضافه شد: {pc.course_name} (از ترم {pc.term})")

        # 8. مرتب‌سازی بر اساس امتیاز (نزولی)
        selected.sort(key=lambda x: x["score"], reverse=True)

        # 9. محدودیت نهایی: فقط در صورت نیاز برش بزنیم
        if len(selected) > max_courses:
            logger.info(f"⚠️ تعداد دروس انتخابی ({len(selected)}) بیشتر از حد مجاز ({max_courses}) است")
            # اولویت با دروس با must_select=True
            must_select_courses = [c for c in selected if c.get("must_select", False)]
            other_courses = [c for c in selected if not c.get("must_select", False)]
            other_courses.sort(key=lambda x: x["score"], reverse=True)
            selected = must_select_courses + other_courses[:max_courses - len(must_select_courses)]
            if len(selected) > max_courses:
                selected = selected[:max_courses]

        # 10. گزارش نهایی
        logger.info("=" * 60)
        logger.info(f"✅ تعداد دروس انتخاب‌شده نهایی: {len(selected)}")
        logger.info(f"❌ تعداد دروس ردشده: {len(rejected)}")

        # نمایش ۱۵ درس اول برای بررسی
        logger.info("📋 ۱۵ درس برتر انتخاب‌شده:")
        logger.info("-" * 60)
        for i, course in enumerate(selected[:15], 1):
            logger.info(
                f"  {i:2}. {course['course_name'][:30]:<30} "
                f"(امتیاز: {course['score']:6.1f}) "
                f"- {course.get('level', '')[:12]} - {course.get('term', '')[:8]} "
                f"- دفعات: {course.get('historical_count', 0)}"
            )
        if len(selected) > 15:
            logger.info(f"  ... و {len(selected) - 15} درس دیگر")

        # نمایش ۵ درس اول ردشده
        if rejected:
            logger.info("📋 ۵ درس برتر ردشده:")
            rejected_sorted = sorted(rejected, key=lambda x: x["score"], reverse=True)
            for i, course in enumerate(rejected_sorted[:5], 1):
                logger.info(
                    f"  {i:2}. {course['course_name'][:30]:<30} "
                    f"(امتیاز: {course['score']:6.1f}) "
                    f"- دلیل: امتیاز پایین"
                )

        logger.info("=" * 60)

        return selected, rejected