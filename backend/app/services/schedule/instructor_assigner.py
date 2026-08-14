# app/services/schedule/instructor_assigner.py
# تخصیص استاد به دروس عادی (مرحله ۴) - نسخه نهایی با رفع مشکلات

import logging
from collections import defaultdict
from typing import List, Dict, Tuple, Optional, Any, Union

from app.utils.helpers import normalize_code
from app.services.workflow_helpers import calculate_final_score

logger = logging.getLogger(__name__)


class InstructorAssigner:
    """
    تخصیص استاد به دروس عادی با رعایت اولویت تدریس، ظرفیت واحد و چرخش استاد.
    """

    # ============================================================
    # متدهای نرمال‌سازی داده‌ها
    # ============================================================

    @staticmethod
    def _normalize_teaching_preferences(
        teaching_prefs: Union[List[Dict], Dict[str, List[str]], None]
    ) -> Dict[str, List[str]]:
        """
        تبدیل ترجیحات تدریس از فرمت لیست یا دیکشنری به فرمت استاندارد:
        { course_code: [instructor_code1, instructor_code2, ...] }
        ترتیب اساتید بر اساس اولویت (priority) صعودی است.
        """
        if not teaching_prefs:
            return {}

        # اگر از قبل به فرم استاندارد است، همان را برگردان
        if isinstance(teaching_prefs, dict):
            # اطمینان از اینکه مقادیر لیست هستند
            return {k: (v if isinstance(v, list) else []) for k, v in teaching_prefs.items()}

        # ورودی لیستی از دیکشنری‌هاست
        result = defaultdict(list)
        for pref in teaching_prefs:
            course_code = str(pref.get("unique_course_code") or pref.get("course_code") or "").strip()
            instructor_code = str(pref.get("instructor_code") or "").strip()
            if course_code and instructor_code:
                priority = int(pref.get("priority", 999))
                result[course_code].append((instructor_code, priority))

        # مرتب‌سازی بر اساس اولویت و حذف اولویت‌ها
        sorted_result = {}
        for course_code, items in result.items():
            items.sort(key=lambda x: x[1])  # مرتب‌سازی بر اساس priority
            sorted_result[course_code] = [inst for inst, _ in items]

        return sorted_result

    @staticmethod
    def _normalize_instructor_data(
        instructor_data: Union[List[Dict], Dict[str, Dict], None]
    ) -> Dict[str, Dict]:
        """
        تبدیل اطلاعات اساتید به فرمت استاندارد:
        {
            "names": { code: name, ... },
            "max_units": { code: max_units, ... },
            "cooperation_types": { code: cooperation_type, ... }
        }
        """
        if not instructor_data:
            return {"names": {}, "max_units": {}, "cooperation_types": {}}

        # اگر از قبل به فرمت استاندارد است، همان را برگردان
        if isinstance(instructor_data, dict) and "names" in instructor_data:
            return instructor_data

        # ورودی لیستی از دیکشنری‌های اساتید است
        names = {}
        max_units = {}
        cooperation_types = {}
        for inst in instructor_data:
            code = str(inst.get("code") or "").strip()
            if code:
                names[code] = inst.get("name", code)
                max_units[code] = int(inst.get("max_teaching_units", 999))
                cooperation_types[code] = inst.get("cooperation_type", "نامشخص")

        return {"names": names, "max_units": max_units, "cooperation_types": cooperation_types}

    # ============================================================
    # متد اصلی (API عمومی)
    # ============================================================

    @staticmethod
    def assign_instructors(
        courses: Optional[List[Dict]] = None,
        teaching_prefs: Optional[Union[List[Dict], Dict[str, List[str]]]] = None,
        instructor_data: Optional[Union[List[Dict], Dict[str, Dict]]] = None,
    ) -> Dict[str, Any]:
        """
        تخصیص استاد به دروس عادی با رعایت اولویت تدریس، ظرفیت واحد و چرخش استاد.
        هر رکورد ورودی به‌طور مستقل پردازش می‌شود و هیچ رکوردی حذف نمی‌شود.

        Args:
            courses: لیست دروس عادی (هر درس شامل unique_code, group_number, units, ...)
            teaching_prefs: ترجیحات تدریس - یا لیستی از دیکشنری‌ها با کلیدهای
                            unique_course_code, instructor_code, priority
                            یا دیکشنری { course_code: [instructor_code1, ...] }
            instructor_data: اطلاعات اساتید - یا لیستی از دیکشنری‌ها با کلیدهای
                             code, name, max_teaching_units, cooperation_type
                             یا دیکشنری { "names": {...}, "max_units": {...}, ... }

        Returns:
            دیکشنری با کلیدهای:
                - "assigned": لیست دروس تخصیص‌یافته
                - "unassigned": لیست دروس تخصیص‌نیافته
                - "all": لیست تمام دروس (assigned + unassigned)
        """
        courses = courses or []
        teaching_prefs = teaching_prefs or []
        instructor_data = instructor_data or []

        # نرمال‌سازی داده‌ها
        normalized_teaching = InstructorAssigner._normalize_teaching_preferences(teaching_prefs)
        normalized_instructors = InstructorAssigner._normalize_instructor_data(instructor_data)

        # اگر سبد خالی است، خروجی خالی برگردان
        if not courses:
            logger.info("📭 لیست دروس عادی خالی است")
            return {"assigned": [], "unassigned": [], "all": []}

        # فراخوانی منطق اصلی با داده‌های نرمال‌شده
        assigned, unassigned = InstructorAssigner._assign_instructors_internal(
            regular_courses=courses,
            teaching_prefs=normalized_teaching,
            instructor_data=normalized_instructors,
        )

        return {
            "assigned": assigned,
            "unassigned": unassigned,
            "all": assigned + unassigned,
        }

    # ============================================================
    # منطق اصلی تخصیص (داخلی)
    # ============================================================

    @staticmethod
    def _assign_instructors_internal(
        regular_courses: List[Dict],
        teaching_prefs: Dict[str, List[str]],
        instructor_data: Dict[str, Dict],
    ) -> Tuple[List[Dict], List[Dict]]:
        """
        منطق اصلی تخصیص استاد. این متد توسط assign_instructors فراخوانی می‌شود.
        """
        if not regular_courses:
            return [], []

        total_input = len(regular_courses)
        logger.info(f"📚 شروع تخصیص استاد به {total_input} درس عادی")

        # ============================================================
        # ۱. گروه‌بندی دروس بر اساس کد یکتا و شناسایی نامعتبرها
        # ============================================================
        groups_by_course = defaultdict(list)
        invalid_courses = []  # دروسی که unique_code معتبر ندارند
        missing_code_courses = []  # دروسی که اصلاً unique_code ندارند

        logger.info("🔄 شروع گروه‌بندی دروس بر اساس unique_code...")

        for idx, course in enumerate(regular_courses):
            raw_code = course.get("unique_code", "")
            code_norm = normalize_code(raw_code)

            if code_norm:
                groups_by_course[code_norm].append(course)
            else:
                invalid_courses.append(course)
                if not raw_code:
                    missing_code_courses.append(course)
                    logger.warning(
                        f"⚠️ درس '{course.get('course_name')}' (گروه {course.get('group_number')}) "
                        f"فاقد unique_code است"
                    )
                else:
                    logger.warning(
                        f"⚠️ درس '{course.get('course_name')}' (گروه {course.get('group_number')}) "
                        f"دارای unique_code نامعتبر است (raw='{raw_code}')"
                    )

        total_valid = sum(len(courses) for courses in groups_by_course.values())
        logger.info(f"📊 نتایج گروه‌بندی:")
        logger.info(f"   تعداد گروه‌های ساخته‌شده (کد یکتا): {len(groups_by_course)}")
        logger.info(f"   تعداد دروس معتبر در گروه‌ها: {total_valid}")
        logger.info(f"   تعداد دروس نامعتبر (بدون unique_code معتبر): {len(invalid_courses)}")
        logger.info(f"   از این تعداد، فاقد unique_code: {len(missing_code_courses)}")

        if total_valid + len(invalid_courses) != total_input:
            missing_in_grouping = total_input - (total_valid + len(invalid_courses))
            logger.error(
                f"⚠️ تعداد دروس پردازش‌شده در گروه‌بندی ({total_valid + len(invalid_courses)}) "
                f"با تعداد ورودی ({total_input}) متفاوت است! "
                f"{missing_in_grouping} درس گم‌شده در گروه‌بندی وجود دارد."
            )

        # ============================================================
        # ۲. آماده‌سازی لیست‌های خروجی
        # ============================================================
        assigned = []
        unassigned = []

        # ---- ۲-۱. درس‌های نامعتبر (فاقد unique_code معتبر) را به unassigned اضافه کن ----
        for course in invalid_courses:
            course["instructor_code"] = None
            course["instructor_name"] = None
            course["final_score"] = 0
            course["manual_required"] = True
            course["unassigned_reason"] = "کد یکتا (unique_code) برای این درس معتبر نیست یا خالی است"
            unassigned.append(course)
            logger.info(
                f"📌 درس '{course.get('course_name')}' گروه {course.get('group_number')} "
                f"به دلیل نداشتن unique_code معتبر به unassigned اضافه شد"
            )

        # اگر هیچ گروه معتبری وجود نداشت، کار تمام است
        if not groups_by_course:
            logger.warning("⚠️ هیچ درس عادی با unique_code معتبر وجود ندارد")
            return [], unassigned

        # ============================================================
        # ۳. محاسبه حداکثر امتیاز هر درس (برای مرتب‌سازی)
        # ============================================================
        course_max_score = {}
        for code, courses in groups_by_course.items():
            max_score = max((c.get("priority_score", 0) for c in courses), default=0)
            course_max_score[code] = max_score

        # مرتب‌سازی کدهای درس بر اساس امتیاز نزولی
        sorted_course_codes = sorted(
            course_max_score.keys(),
            key=lambda c: course_max_score.get(c, 0),
            reverse=True
        )

        logger.info(f"📋 {len(sorted_course_codes)} درس منحصربه‌فرد برای تخصیص استاد.")

        # ============================================================
        # ۴. تخصیص استاد به هر رکورد (بدون حذف رکوردهای تکراری)
        # ============================================================
        instructor_used_units = defaultdict(int)
        names = instructor_data.get("names", {})
        max_units = instructor_data.get("max_units", {})

        # برای هر کد درس، لیست دروس آن را دریافت و پردازش کن
        for course_code in sorted_course_codes:
            courses = groups_by_course[course_code]
            preferred_instructors = teaching_prefs.get(course_code, [])

            # مرتب‌سازی بر اساس شماره گروه (برای خروجی منظم)
            courses.sort(key=lambda c: c.get("group_number", 1))

            logger.info(
                f"🔍 پردازش course_code: {course_code}, تعداد رکوردها: {len(courses)}, "
                f"تعداد اساتید اولویت‌دار: {len(preferred_instructors)}"
            )

            # اگر هیچ استاد اولویتی برای این درس وجود ندارد
            if not preferred_instructors:
                for course in courses:
                    course["instructor_code"] = None
                    course["instructor_name"] = None
                    course["final_score"] = 0
                    course["manual_required"] = True
                    course["unassigned_reason"] = "هیچ استاد واجد شرطی برای این درس ثبت نشده است"
                    unassigned.append(course)
                    logger.warning(
                        f"⚠️ درس '{course.get('course_name')}' گروه {course.get('group_number')} "
                        f"هیچ استاد اولویتی ندارد"
                    )
                continue

            # تخصیص استاد به هر رکورد به‌طور مستقل
            num_instructors = len(preferred_instructors)
            instructor_index = 0

            for course in courses:
                units = course.get("units", 2)
                assigned_instructor = None

                # جستجوی استاد با ظرفیت کافی (چرخشی)
                for attempt in range(num_instructors):
                    inst_code = preferred_instructors[instructor_index % num_instructors]
                    current_units = instructor_used_units.get(inst_code, 0)
                    max_u = max_units.get(inst_code, 999)

                    if current_units + units <= max_u:
                        assigned_instructor = inst_code
                        instructor_index = (instructor_index + 1) % num_instructors
                        break
                    else:
                        instructor_index = (instructor_index + 1) % num_instructors

                if assigned_instructor:
                    inst_name = names.get(assigned_instructor, assigned_instructor)
                    course["instructor_code"] = assigned_instructor
                    course["instructor_name"] = inst_name
                    priority_index = preferred_instructors.index(assigned_instructor)
                    course["instructor_priority"] = priority_index + 1
                    course["final_score"] = calculate_final_score(course)
                    course["manual_required"] = False
                    instructor_used_units[assigned_instructor] += units
                    assigned.append(course)

                    logger.info(
                        f"✅ درس '{course.get('course_name')}' گروه {course.get('group_number')} "
                        f"→ استاد {inst_name} (کد {assigned_instructor})، اولویت {priority_index + 1}، "
                        f"واحد {units}"
                    )
                else:
                    course["instructor_code"] = None
                    course["instructor_name"] = None
                    course["final_score"] = 0
                    course["manual_required"] = True
                    course["unassigned_reason"] = "تمامی اساتید اولویت‌دار ظرفیت تدریس خود را تکمیل کرده‌اند"
                    unassigned.append(course)
                    logger.warning(
                        f"⚠️ درس '{course.get('course_name')}' گروه {course.get('group_number')} - "
                        f"هیچ استاد با ظرفیت کافی یافت نشد (تعداد اساتید اولویت‌دار: {num_instructors})"
                    )

        # ============================================================
        # ۵. کنترل نهایی: اطمینان از حضور همه رکوردها در خروجی
        # ============================================================
        output_ids = {id(course) for course in assigned + unassigned}
        missing_courses = [
            course for course in regular_courses
            if id(course) not in output_ids
        ]

        if missing_courses:
            logger.error(f"❌ {len(missing_courses)} درس در خروجی نهایی یافت نشد! (بازیابی...)")
            for course in missing_courses:
                course["instructor_code"] = None
                course["instructor_name"] = None
                course["final_score"] = 0
                course["manual_required"] = True
                course["unassigned_reason"] = (
                    "خطای داخلی: درس در خروجی تخصیص استاد قرار نگرفت (بازیابی شد)."
                )
                unassigned.append(course)
                logger.error(
                    f"   بازیابی: درس '{course.get('course_name')}' گروه {course.get('group_number')} "
                    f"با unique_code: {course.get('unique_code', 'ندارد')}"
                )

        # ============================================================
        # ۶. اعتبارسنجی نهایی و گزارش
        # ============================================================
        total_assigned = len(assigned)
        total_unassigned = len(unassigned)
        total_processed = total_assigned + total_unassigned

        logger.info("=" * 60)
        logger.info("📊 گزارش نهایی مرحله تخصیص استاد:")
        logger.info(f"   تعداد ورودی: {total_input}")
        logger.info(f"   تخصیص‌یافته: {total_assigned}")
        logger.info(f"   تخصیص‌نیافته: {total_unassigned}")
        logger.info(f"   مجموع خروجی: {total_processed}")

        if total_processed != total_input:
            diff = total_input - total_processed
            logger.error(
                f"⚠️ تعداد خروجی ({total_processed}) با تعداد ورودی ({total_input}) متفاوت است! "
                f"{diff} درس گم شده‌اند (با وجود بازیابی!)."
            )
        else:
            logger.info(f"✅ همه {total_input} درس عادی پردازش شدند.")

        # لاگ ظرفیت استفاده‌شده اساتید (نمونه)
        if instructor_used_units:
            logger.info("📊 استفاده از سقف واحد اساتید (نمونه):")
            sorted_instructors = sorted(instructor_used_units.items(), key=lambda x: x[1], reverse=True)[:10]
            for inst_code, used in sorted_instructors:
                max_u = max_units.get(inst_code, 999)
                logger.info(f"   {inst_code}: {used}/{max_u} واحد")
            if len(instructor_used_units) > 10:
                logger.info(f"   ... و {len(instructor_used_units) - 10} استاد دیگر")

        logger.info("=" * 60)

        return assigned, unassigned