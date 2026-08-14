# app/services/schedule/report_generator.py

import logging
from collections import defaultdict, Counter
from typing import List, Dict, Optional, Tuple, Union

from app.utils.helpers import get_day_name, slot_overlap, calculate_time_match_score

logger = logging.getLogger(__name__)


class ReportGenerator:
    """تولید گزارش‌های نهایی و بررسی تطابق"""

    # ============================================================
    # توابع کمکی برای نرمال‌سازی داده‌ها
    # ============================================================
    @staticmethod
    def _normalize_instructor_data(
        instructor_data: Union[List[Dict], Dict, None]
    ) -> Dict:
        """
        تبدیل instructor_data به فرمت استاندارد:
        {
            'names': {code: name, ...},
            'max_units': {code: max_units, ...},
            'cooperation_types': {code: cooperation_type, ...}
        }
        """
        if not instructor_data:
            return {"names": {}, "max_units": {}, "cooperation_types": {}}

        # اگر از قبل فرمت استاندارد دارد
        if isinstance(instructor_data, dict) and "names" in instructor_data:
            return instructor_data

        names = {}
        max_units = {}
        cooperation_types = {}

        if isinstance(instructor_data, list):
            for inst in instructor_data:
                if not isinstance(inst, dict):
                    continue
                code = inst.get("code") or inst.get("instructor_code") or inst.get("employee_code") or ""
                if code:
                    code = str(code).strip()
                    names[code] = inst.get("name", code)
                    max_units[code] = int(inst.get("max_teaching_units") or inst.get("max_units") or 999)
                    cooperation_types[code] = inst.get("cooperation_type", "نامشخص")
        else:
            # اگر دیکشنری است اما فرمت استاندارد ندارد، سعی می‌کنیم آن را تبدیل کنیم
            for key, value in instructor_data.items():
                if isinstance(value, dict):
                    code = str(key).strip()
                    names[code] = value.get("name", code)
                    max_units[code] = int(value.get("max_teaching_units") or value.get("max_units") or 999)
                    cooperation_types[code] = value.get("cooperation_type", "نامشخص")

        return {
            "names": names,
            "max_units": max_units,
            "cooperation_types": cooperation_types,
        }

    @staticmethod
    def _normalize_preferences(
        prefs: Union[List[Dict], Dict, None]
    ) -> Dict:
        """
        تبدیل teaching_prefs یا time_prefs به فرمت دیکشنری استاندارد.
        برای teaching_prefs:
            {course_code: [instructor_code1, instructor_code2, ...]}
        برای time_prefs:
            {instructor_code: [(day, start, end, priority), ...]}
        """
        if not prefs:
            return {}

        # اگر از قبل دیکشنری است، همان را برگردان
        if isinstance(prefs, dict):
            return prefs

        # اگر لیست است، تبدیل می‌کنیم
        if isinstance(prefs, list):
            # تشخیص نوع: teaching_prefs یا time_prefs
            if prefs and "unique_course_code" in prefs[0]:
                # teaching_prefs
                result = defaultdict(list)
                for pref in prefs:
                    if not isinstance(pref, dict):
                        continue
                    course_code = pref.get("unique_course_code") or pref.get("course_code")
                    instructor_code = pref.get("instructor_code")
                    if course_code and instructor_code:
                        result[course_code].append(instructor_code)
                return dict(result)
            elif prefs and "instructor_code" in prefs[0]:
                # time_prefs
                from app.utils.helpers import get_day_name
                day_map = {
                    "شنبه": 0, "یکشنبه": 1, "دوشنبه": 2,
                    "سه‌شنبه": 3, "سهشنبه": 3,
                    "چهارشنبه": 4, "پنجشنبه": 5,
                }
                result = defaultdict(list)
                for pref in prefs:
                    if not isinstance(pref, dict):
                        continue
                    instructor = pref.get("instructor_code")
                    if not instructor:
                        continue
                    day_name = pref.get("day", "").strip().replace("\u200c", "").replace(" ", "")
                    day_num = day_map.get(day_name)
                    if day_num is None:
                        continue
                    start = pref.get("start_time") or pref.get("start")
                    end = pref.get("end_time") or pref.get("end")
                    priority = pref.get("priority", 999)
                    if start and end:
                        result[instructor].append((day_num, start, end, priority))
                return dict(result)

        return {}

    # ============================================================
    # متد build_mismatch_details - نسخه نهایی با استفاده از schedule_mode
    # ============================================================
    @staticmethod
    def build_mismatch_details(
            assigned: List[Dict],
            unassigned: List[Dict],
            teaching_prefs: Union[List[Dict], Dict],
            time_prefs: Union[List[Dict], Dict],
            instructor_data: Union[List[Dict], Dict]
    ) -> List[Dict]:
        """
        ساخت لیست جزئیات عدم تطابق برای نمایش در فرانت‌اند.

        منطق صحیح:
        - وضعیت تطابق هر درس مستقیماً از فیلد schedule_mode که توسط time_scheduler ذخیره شده است، گرفته می‌شود.
        - این روش تضمین می‌کند که گزارش با منطق زمان‌بند کاملاً هماهنگ است.
        - در صورتی که schedule_mode موجود نباشد (برای سازگاری با داده‌های قدیمی)، از منطق جایگزین استفاده می‌شود.
        """
        # نرمال‌سازی داده‌ها
        normalized_instructor = ReportGenerator._normalize_instructor_data(instructor_data)
        normalized_time_prefs = ReportGenerator._normalize_preferences(time_prefs)
        normalized_teaching_prefs = ReportGenerator._normalize_preferences(teaching_prefs)

        mismatch_details = []

        # ------------------------------------------------------------
        # ۱. تابع تعیین وضعیت تطابق بر اساس schedule_mode
        # ------------------------------------------------------------
        def get_match_status_from_mode(course: Dict) -> Tuple[str, Optional[str]]:
            """
            وضعیت تطابق را بر اساس فیلد schedule_mode تعیین می‌کند.
            """
            mode = course.get("schedule_match_level") or course.get("schedule_mode")

            if mode == "full" or mode == "strict":
                return "full", None

            if mode == "tolerance_60" or mode == "tolerance":
                return "partial", "زمان تخصیص‌یافته با مطلوبیت استاد با تساهل ۶۰ دقیقه تطابق دارد"

            if mode == "preferred_day_fallback":
                return "none", "درس در روز ترجیحی استاد زمان‌بندی شده اما خارج از بازه‌های مطلوب است"

            if mode == "fallback_non_preferred_day" or mode == "fallback":
                return "none", "درس در روز غیرترجیحی استاد زمان‌بندی شده است"

            if mode == "no_preference_default" or mode == "no_preference":
                return "no_preference", "استاد مطلوبیت زمانی ثبت نکرده است"

            if mode == "unassigned":
                return "no_assignment", "درس زمان‌بندی نشده است"

            # اگر mode وجود نداشت یا ناشناخته بود، از منطق جایگزین استفاده کن
            return None, None

        # ------------------------------------------------------------
        # ۲. تابع جایگزین (برای داده‌های قدیمی یا زمانی که schedule_mode موجود نیست)
        # ------------------------------------------------------------
        def determine_match_status_fallback(course):
            """
            منطق جایگزین برای زمانی که schedule_mode موجود نیست.
            این منطق باید با تعریف strict در time_scheduler هماهنگ باشد.
            در time_scheduler، strict به این معناست که start_inside == True.
            """
            if not course.get("instructor_code") or course.get("day") is None or not course.get("start"):
                return {
                    "status": "no_assignment",
                    "reason": "درس تخصیص کامل ندارد (استاد، روز یا زمان مشخص نشده)"
                }

            instructor_code = course["instructor_code"]
            day = course["day"]
            start = course["start"]
            end = course["end"]

            time_pref_list = normalized_time_prefs.get(instructor_code, [])
            if not time_pref_list:
                return {
                    "status": "no_preference",
                    "reason": "استاد مطلوبیت زمانی ثبت نکرده است"
                }

            # ---- بررسی strict (همانند time_scheduler) ----
            # در time_scheduler، strict = start_inside
            def start_inside(slot_start, pref_start, pref_end):
                slot_s = time_to_minutes(slot_start)
                pref_s = time_to_minutes(pref_start)
                pref_e = time_to_minutes(pref_end)
                return pref_s <= slot_s < pref_e

            strict_match = any(
                d == day and start_inside(start, s, e)
                for d, s, e, _ in time_pref_list
            )

            if strict_match:
                return {
                    "status": "full",
                    "reason": None
                }

            # ---- بررسی tolerance (با تساهل ۹۰ دقیقه) ----
            tolerance_match = False
            for d, s, e, p in time_pref_list:
                if d == day:
                    score = calculate_time_match_score(start, end, s, e, p, max_tolerance_minutes=90)
                    if score > 0:
                        tolerance_match = True
                        break

            if tolerance_match:
                return {
                    "status": "partial",
                    "reason": "زمان تخصیص‌یافته با مطلوبیت استاد با تساهل ۹۰ دقیقه تطابق دارد"
                }

            # ---- بررسی روز ----
            day_match = any(d == day for d, _, _, _ in time_pref_list)
            if day_match:
                return {
                    "status": "none",
                    "reason": "زمان تخصیص‌یافته خارج از بازه‌های مطلوب استاد است (اگرچه روز تطابق دارد)"
                }

            return {
                "status": "none",
                "reason": "روز تخصیص‌یافته در مطلوبیت‌های روز استاد نیست"
            }

        # ------------------------------------------------------------
        # ۳. ساخت mismatch_details برای دروس تخصیص‌یافته
        # ------------------------------------------------------------
        for item in assigned:
            # اولویت اول: استفاده از schedule_mode
            status, reason = get_match_status_from_mode(item)

            if status is None:
                # اگر schedule_mode وجود نداشت، از منطق جایگزین استفاده کن
                match_info = determine_match_status_fallback(item)
                status = match_info["status"]
                reason = match_info["reason"]

            # فقط مواردی که وضعیت "full" ندارند به لیست اضافه می‌شوند
            if status != "full":
                mismatch_details.append({
                    "course_name": item.get("course_name"),
                    "group_number": item.get("group_number"),
                    "instructor_code": item.get("instructor_code"),
                    "instructor_name": item.get("instructor_name"),
                    "day": item.get("day"),
                    "start": item.get("start"),
                    "end": item.get("end"),
                    "status": status,
                    "reason": reason,
                    "level": item.get("level"),
                    "term": item.get("term"),
                    "unique_code": item.get("unique_code"),
                    "is_assigned": True,
                    "schedule_mode": item.get("schedule_match_level") or item.get("schedule_mode"),
                })

        # ------------------------------------------------------------
        # ۴. ساخت mismatch_details برای دروس تخصیص‌نیافته
        # ------------------------------------------------------------
        for item in unassigned:
            reason = item.get("unassigned_reason", "دلیل نامشخص")
            # تشخیص پروژه/کارآموزی برای جدا کردن از زمان‌بندی عادی
            is_internship = item.get("is_internship") or "کارآموزی" in item.get("course_name", "") or "پروژه" in item.get("course_name", "")
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
                "is_assigned": False,
                "is_internship": is_internship,
            })

        # ------------------------------------------------------------
        # ۵. اعتبارسنجی و لاگ‌گذاری
        # ------------------------------------------------------------
        # شمارش وضعیت‌ها بر اساس mismatch_details
        status_counts = Counter(item["status"] for item in mismatch_details)
        logger.info(f"📊 آمار وضعیت‌های عدم تطابق: {dict(status_counts)}")

        # محاسبه تعداد کلاس‌های تخصیص‌یافته با مشکل (غیر از full)
        total_assigned_with_issues = sum(
            1 for item in mismatch_details
            if item.get("is_assigned") and item["status"] != "full"
        )
        total_unassigned = sum(1 for item in mismatch_details if not item.get("is_assigned"))

        logger.info(f"✅ تأیید: تخصیص‌یافته با مشکل = {total_assigned_with_issues}, تخصیص‌نیافته = {total_unassigned}")
        logger.info(f"📌 مجموع موارد عدم تطابق = {len(mismatch_details)}")

        return mismatch_details

    # ============================================================
    # متد generate_report (با پشتیبانی از فرمت‌های مختلف داده)
    # ============================================================
    @staticmethod
    def generate_report(
            assigned: List[Dict],
            unassigned: List[Dict],
            instructor_data: Union[List[Dict], Dict],
            instructor_used_units: Dict,
            mismatch_details: Optional[List[Dict]] = None,
            total_input_courses: Optional[int] = None
    ) -> None:
        """
        تولید گزارش نهایی زمان‌بندی و چاپ آن در لاگ.
        """
        # نرمال‌سازی instructor_data به فرمت استاندارد
        normalized_instructor = ReportGenerator._normalize_instructor_data(instructor_data)

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
                return zero_based_days.get(value, str(value))
            value_text = str(value).strip()
            if not value_text:
                return "نامشخص"
            if value_text.isdigit():
                numeric_day = int(value_text)
                return zero_based_days.get(numeric_day, one_based_days.get(numeric_day, value_text))
            return value_text

        def get_instructor_name(instructor_code, item: Optional[Dict] = None) -> str:
            item = item or {}
            direct_name = (
                    item.get("instructor_name")
                    or item.get("teacher_name")
                    or item.get("professor_name")
            )
            if direct_name:
                return safe_text(direct_name)
            names = normalized_instructor.get("names") or {}
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
            max_units_map = normalized_instructor.get("max_units") or {}
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

        total_assigned = len(assigned or [])
        total_unassigned = len(unassigned or [])
        accounted_courses = total_assigned + total_unassigned
        if total_input_courses is not None:
            total_courses = max(int(total_input_courses), accounted_courses)
        else:
            total_courses = accounted_courses
        missing_from_result = max(total_courses - accounted_courses, 0)
        success_rate = (total_assigned / total_courses * 100) if total_courses > 0 else 0.0

        logger.info(f"📚 تعداد کل کلاس‌های ورودی: {total_courses}")
        logger.info(f"✅ کلاس‌های تخصیص‌یافته: {total_assigned}")
        logger.info(f"❌ کلاس‌های تخصیص‌نیافته: {total_unassigned}")
        logger.info(f"⚠️ کلاس‌های خارج‌شده از خروجی تخصیص: {missing_from_result}")
        logger.info(f"📈 نرخ تخصیص: {success_rate:.2f}%")

        logger.info("-" * 100)
        logger.info("🔎 گزارش وضعیت تطابق")
        if mismatch_details is None:
            logger.info("ℹ️ اطلاعات عدم تطابق برای گزارش ارسال نشده است")
        else:
            status_counts = {
                "full": 0,
                "partial": 0,
                "none": 0,
                "unassigned": 0,
                "no_preference": 0,
                "no_assignment": 0,
                "unknown": 0,
            }
            for item in mismatch_details:
                status = safe_text(item.get("status"), "unknown").lower()
                if status not in status_counts:
                    status_counts["unknown"] += 1
                else:
                    status_counts[status] += 1

            logger.info(f"✅ تطابق کامل: {status_counts['full']}")
            logger.info(f"⚠️ تطابق نسبی (با تساهل): {status_counts['partial']}")
            logger.info(f"❌ بدون تطابق: {status_counts['none']}")
            logger.info(f"🚫 تخصیص‌نیافته: {status_counts['unassigned']}")
            logger.info(f"➖ مطلوبیت زمانی ثبت نشده: {status_counts['no_preference']}")
            logger.info(f"❔ وضعیت ناشناخته: {status_counts['unknown']}")
            logger.info(f"📋 مجموع رکوردهای بررسی‌شده: {len(mismatch_details)}")

            if mismatch_details:
                logger.info("-" * 100)
                logger.info("📝 نمونه دلایل عدم تطابق:")
                for index, item in enumerate(mismatch_details[:20], start=1):
                    course_name = safe_text(item.get("course_name") or item.get("lesson_name"))
                    group_number = safe_text(item.get("group_number") or item.get("group"))
                    unique_code = get_course_code(item) or "نامشخص"
                    instructor_code = get_instructor_code(item)
                    instructor_name = get_instructor_name(instructor_code, item)
                    status = safe_text(item.get("status"), "نامشخص")
                    reason = safe_text(item.get("reason"), "دلیل ثبت نشده")
                    day = get_display_day(item.get("day"))
                    start = safe_text(item.get("start"), "")
                    end = safe_text(item.get("end"), "")
                    time_text = f"{day} {start}-{end}" if start or end else day
                    logger.info(
                        "%s. درس: %s | گروه: %s | کد: %s | استاد: %s [کد: %s] | وضعیت: %s | زمان: %s | دلیل: %s",
                        index, course_name, group_number, unique_code,
                        instructor_name, instructor_code or "نامشخص",
                        status, time_text, reason
                    )
                if len(mismatch_details) > 20:
                    logger.info(f"... و {len(mismatch_details) - 20} مورد دیگر")

        logger.info("-" * 100)
        logger.info("📊 استفاده از سقف واحد اساتید:")
        if not instructor_used_units:
            logger.info("ℹ️ اطلاعاتی از واحد تخصیص‌یافته به اساتید وجود ندارد")
        else:
            sorted_instructors = sorted(instructor_used_units.items(), key=lambda item: str(item[0]))
            for inst_code, used_units in sorted_instructors:
                instructor_code = normalize_code(inst_code)
                instructor_name = get_instructor_name(instructor_code)
                used_units_value = to_float(used_units, 0.0)
                max_units = get_max_units(instructor_code)
                if max_units is None:
                    logger.warning(f"⚠️ سقف واحد استاد {instructor_name} [کد: {instructor_code}] پیدا نشد")
                    logger.info(
                        f"👨‍🏫 استاد {instructor_name} [کد: {instructor_code}]: {used_units_value:.0f} واحد (سقف واحد نامشخص)")
                    continue
                max_units_value = to_float(max_units, 0.0)
                if max_units_value > 0:
                    usage_percent = (used_units_value / max_units_value) * 100
                    logger.info(
                        f"👨‍🏫 استاد {instructor_name} [کد: {instructor_code}]: "
                        f"{used_units_value:.0f} واحد از {max_units_value:.0f} واحد ({usage_percent:.1f}%)"
                    )
                else:
                    logger.info(
                        f"👨‍🏫 استاد {instructor_name} [کد: {instructor_code}]: "
                        f"{used_units_value:.0f} واحد (سقف واحد نامشخص)"
                    )

        if unassigned:
            logger.info("-" * 100)
            logger.info("❌ دلایل نمونه دروس تخصیص‌نیافته:")
            for index, course in enumerate(unassigned[:20], start=1):
                course_name = safe_text(course.get("course_name") or course.get("lesson_name"))
                group_number = safe_text(course.get("group_number") or course.get("group"))
                unique_code = get_course_code(course) or "نامشخص"
                reason = safe_text(course.get("unassigned_reason") or course.get("reason"), "دلیل ثبت نشده")
                logger.info(
                    "%s. درس: %s | گروه: %s | کد: %s | دلیل: %s",
                    index, course_name, group_number, unique_code, reason
                )
            if len(unassigned) > 20:
                logger.info(f"... و {len(unassigned) - 20} درس تخصیص‌نیافته دیگر")
        else:
            logger.info("-" * 100)
            logger.info("✅ هیچ درس تخصیص‌نیافته‌ای وجود ندارد")

        if assigned:
            logger.info("-" * 100)
            logger.info("📋 زمان‌های نهایی تخصیص‌یافته (نمونه):")
            for item in assigned[:20]:
                course_name = safe_text(item.get("course_name") or item.get("lesson_name"))
                group_number = safe_text(item.get("group_number") or item.get("group"))
                day = get_display_day(item.get("day"))
                start = safe_text(item.get("start"), "")
                end = safe_text(item.get("end"), "")
                units = item.get("units", item.get("course_units", 0))
                logger.info(
                    "   %s گروه %s → %s %s-%s (واحد: %s)",
                    course_name, group_number, day, start, end, safe_text(units, "0")
                )
            if len(assigned) > 20:
                logger.info(f"   ... و {len(assigned) - 20} تخصیص دیگر")

        logger.info("=" * 100)


# ============================================================
# تابع کمکی time_to_minutes (برای استفاده در این ماژول)
# ============================================================
def time_to_minutes(t: str) -> int:
    try:
        h, m = map(int, t.split(':'))
        return h * 60 + m
    except:
        return 0