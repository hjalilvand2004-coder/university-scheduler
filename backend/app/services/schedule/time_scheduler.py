# app/services/schedule/time_scheduler.py
# زمان‌بندی دروس هر استاد (مرحله 5) - با رعایت سقف واحد
#
# منطق اجرا:
# 1) strict:
#    اسلات‌هایی که با بازه مطلوب همپوشانی دارند (حتی اگر کاملاً داخل نباشند) مجاز هستند.
#    اولویت با اسلات‌های کاملاً داخل بازه است.
#
# 2) صف حلقوی تساهل‌دار:
#    دور اول: 30 دقیقه تساهل برای شروع کلاس
#    هر دور جدید: 60 دقیقه افزایش تساهل
#    مثال: 30، 90، 150، 210، ...
#
# 3) fallback در روزهای مطلوب:
#    انتخاب سراسری بهترین گزینه بین تمام روزهای مطلوب.
#
# 4) fallback در روزهای غیرمطلوب:
#    فقط پس از پایان تمام گزینه‌های روزهای مطلوب.
#
# نکته:
# - بازه دقیق 12:00 تا 16:00 به 13:00 تا 17:00 تبدیل می‌شود.
# - فقط از اسلات‌های ثابت TWO_UNIT_SLOTS و THREE_UNIT_SLOTS استفاده می‌شود.
# - سقف واحد استاد رعایت می‌شود.
# - اولویت با دروس با واحد بیشتر است.

import logging
from collections import defaultdict
from typing import List, Dict, Tuple, Optional, Any, Union

from app.utils.constants import TWO_UNIT_SLOTS, THREE_UNIT_SLOTS
from app.utils.helpers import time_to_minutes, slot_overlap, get_day_name

logger = logging.getLogger(__name__)


class TimeScheduler:
    @staticmethod
    def _normalize_instructor_data(
        instructor_data: Optional[Union[List[Dict], Dict]]
    ) -> Dict[str, Any]:
        """
        تبدیل اطلاعات اساتید به فرمت استاندارد:
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
                    # فرض می‌کنیم key کد استاد است
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
    def _normalize_time_prefs(
        time_prefs: Optional[Union[List[Dict], Dict]]
    ) -> Dict[str, List[Tuple[int, str, str, int]]]:
        """
        تبدیل ترجیحات زمانی به فرمت استاندارد:
        {
            instructor_code: [
                (day_number, "start", "end", priority),
                ...
            ]
        }
        """
        if not time_prefs:
            return {}

        # اگر از قبل فرمت استاندارد دارد
        if isinstance(time_prefs, dict):
            # اطمینان از اینکه مقادیر لیست هستند و هر آیتم tuple با ۴ عنصر است
            result = {}
            for inst, items in time_prefs.items():
                if not isinstance(items, list):
                    continue
                normalized_items = []
                for item in items:
                    if isinstance(item, tuple) and len(item) >= 3:
                        day = item[0]
                        start = item[1]
                        end = item[2]
                        priority = item[3] if len(item) > 3 else 999
                        normalized_items.append((day, start, end, priority))
                    elif isinstance(item, dict):
                        # فرض می‌کنیم دیکشنری با کلیدهای day, start_time, end_time, priority
                        day = item.get("day")
                        start = item.get("start_time") or item.get("start")
                        end = item.get("end_time") or item.get("end")
                        priority = item.get("priority", 999)
                        if day is not None and start and end:
                            normalized_items.append((day, start, end, priority))
                if normalized_items:
                    result[inst] = normalized_items
            return result

        # اگر لیست است (فرمت تست)
        if isinstance(time_prefs, list):
            result = defaultdict(list)
            for pref in time_prefs:
                if not isinstance(pref, dict):
                    continue
                inst = pref.get("instructor_code")
                if not inst:
                    continue
                # نام روز را به عدد تبدیل کنید (مشابه day_map در back-end)
                day_name = pref.get("day", "").strip()
                day_map = {
                    "شنبه": 0, "یکشنبه": 1, "دوشنبه": 2,
                    "سه‌شنبه": 3, "سهشنبه": 3,
                    "چهارشنبه": 4, "پنجشنبه": 5,
                }
                # ممکن است day_name شامل نیم‌فاصله باشد، آن را حذف کنیم
                day_name_clean = day_name.replace("\u200c", "").replace(" ", "")
                day_num = day_map.get(day_name_clean)
                if day_num is None:
                    logger.warning(f"روز ناشناخته: {day_name} برای استاد {inst}")
                    continue
                start = pref.get("start_time") or pref.get("start")
                end = pref.get("end_time") or pref.get("end")
                priority = pref.get("priority", 999)
                if start and end:
                    result[inst].append((day_num, start, end, priority))
            return dict(result)

        return {}

    @staticmethod
    def assign_full_schedule(
        courses: Optional[List[Dict]] = None,
        instructor_data: Optional[Union[List[Dict], Dict]] = None,
        time_prefs: Optional[Union[List[Dict], Dict]] = None,
    ) -> Dict[str, List[Dict]]:
        """
        زمان‌بندی دروس دارای استاد.

        Args:
            courses: فهرست درس‌ها که instructor_code دارند.
            instructor_data: اطلاعات استاد (لیست یا دیکشنری).
            time_prefs: مطلوبیت زمان استاد (لیست یا دیکشنری).

        Returns:
            دیکشنری با کلیدهای 'scheduled' و 'unscheduled'
        """
        courses = courses or []
        instructor_data = instructor_data or {}
        time_prefs = time_prefs or {}

        # نرمال‌سازی داده‌ها
        normalized_instructor_data = TimeScheduler._normalize_instructor_data(instructor_data)
        normalized_time_prefs = TimeScheduler._normalize_time_prefs(time_prefs)

        assigned, unassigned = TimeScheduler._assign_full_schedule_internal(
            courses_with_instructor=courses,
            time_prefs=normalized_time_prefs,
            instructor_data=normalized_instructor_data,
        )

        return {"scheduled": assigned, "unscheduled": unassigned}

    @staticmethod
    def _assign_full_schedule_internal(
        courses_with_instructor: List[Dict],
        time_prefs: Dict,
        instructor_data: Dict
    ) -> Tuple[List[Dict], List[Dict]]:
        """
        زمان‌بندی دروس دارای استاد.

        Args:
            courses_with_instructor:
                فهرست درس‌ها که instructor_code دارند.

            time_prefs:
                دیکشنری مطلوبیت زمان استاد.
                ساختار مورد انتظار:
                {
                    instructor_code: [
                        (day_number, "start", "end", priority),
                        ...
                    ]
                }

            instructor_data:
                اطلاعات استاد شامل سقف واحد تدریس.
                ساختار مورد انتظار:
                {
                    'max_units': {instructor_code: max_units, ...},
                    'names': {...},
                    ...
                }

        Returns:
            Tuple[List[Dict], List[Dict]]:
                assigned, unassigned
        """

        if not courses_with_instructor:
            logger.info("📭 لیست دروس با استاد خالی است")
            return [], []

        total_input = len(courses_with_instructor)

        logger.info(
            "⏳ شروع زمان‌بندی برای %s درس با استاد مشخص",
            total_input
        )

        assigned: List[Dict] = []
        unassigned: List[Dict] = []

        # ============================================================
        # توابع کمکی عمومی
        # ============================================================
        def safe_int(value: Any, default: int = 0) -> int:
            """تبدیل امن مقدار به int."""
            try:
                if value is None or value == "":
                    return default
                return int(value)
            except (ValueError, TypeError):
                return default

        def get_course_units(course: Dict) -> int:
            """
            تعداد واحد درس.

            اگر مقدار نامعتبر یا خالی بود، 2 واحد در نظر گرفته می‌شود.
            """
            units = safe_int(course.get("units"), 2)
            return max(1, units)

        def sort_slots(
                slots: List[Tuple[str, str]]
        ) -> List[Tuple[str, str]]:
            """مرتب‌سازی اسلات‌ها بر اساس زمان شروع و پایان."""
            return sorted(
                list(slots),
                key=lambda slot: (
                    time_to_minutes(slot[0]),
                    time_to_minutes(slot[1]),
                )
            )

        def is_conflict(
                occupied_slots: List[Tuple[str, str]],
                start: str,
                end: str
        ) -> bool:
            """بررسی تداخل یک اسلات با اسلات‌های اشغال‌شده روز."""
            return any(
                slot_overlap(start, end, occupied_start, occupied_end)
                for occupied_start, occupied_end in occupied_slots
            )

        def get_course_slots(course: Dict) -> List[Tuple[str, str]]:
            """
            دریافت اسلات‌های ثابت مجاز برای درس.

            نکته مهم:
            این تابع هیچ ساعت جدیدی، نظیر 15:31، تولید نمی‌کند.
            اگر اسلات 15:31 لازم است، باید صراحتاً در constants تعریف شود.
            """
            units = get_course_units(course)

            if units == 3:
                return sort_slots(THREE_UNIT_SLOTS)

            return sort_slots(TWO_UNIT_SLOTS)

        def normalize_preference_window(
                start: str,
                end: str
        ) -> Tuple[str, str]:
            """
            اصلاح بازۀ مطلوب خاص مورد درخواست.

            بازه:
                12:00 تا 16:00
            به:
                13:00 تا 17:00
            تبدیل می‌شود.

            سایر بازه‌ها بدون تغییر باقی می‌مانند.
            """
            if start == "12:00" and end == "16:00":
                return "13:00", "17:00"

            return start, end

        def get_instructor_record(instructor_code: str) -> Dict:
            """
            بازیابی اطلاعات استاد از ساختارهای رایج instructor_data.

            ساختارهای قابل پشتیبانی:
            1) { instructor_code: {...} }
            2) [{ "code": "...", ... }, ...]
            3) [{ "instructor_code": "...", ... }, ...]
            """
            if not instructor_data:
                return {}

            if isinstance(instructor_data, dict):
                direct_record = instructor_data.get(instructor_code)

                if isinstance(direct_record, dict):
                    return direct_record

                for key in ("instructors", "data", "items", "results"):
                    records = instructor_data.get(key)

                    if not isinstance(records, list):
                        continue

                    for record in records:
                        if not isinstance(record, dict):
                            continue

                        code = (
                            record.get("instructor_code")
                            or record.get("code")
                            or record.get("employee_code")
                            or record.get("national_code")
                            or record.get("id")
                        )

                        if str(code) == str(instructor_code):
                            return record

            if isinstance(instructor_data, list):
                for record in instructor_data:
                    if not isinstance(record, dict):
                        continue

                    code = (
                        record.get("instructor_code")
                        or record.get("code")
                        or record.get("employee_code")
                        or record.get("national_code")
                        or record.get("id")
                    )

                    if str(code) == str(instructor_code):
                        return record

            return {}

        def get_instructor_unit_limit(
                instructor_code: str
        ) -> Optional[int]:
            """
            دریافت سقف واحد تدریس استاد.

            اگر سقف یافت نشود یا مقدار آن صفر/منفی باشد، None برمی‌گردد؛
            یعنی برای آن استاد سقف واحد شناخته‌شده‌ای اعمال نمی‌شود.

            نام فیلدهای پشتیبانی‌شده:
            - max_teaching_units
            - max_units
            - teaching_capacity
            - unit_capacity
            - max_weekly_units
            - max_teaching_load
            - weekly_unit_limit
            - teaching_unit_limit
            """

            # ============================================================
            # ۱. بررسی مستقیم کلید 'max_units' در instructor_data
            #    (ساختار مورد استفاده در orchestrator)
            # ============================================================
            if isinstance(instructor_data, dict):
                max_units_map = instructor_data.get("max_units")

                if isinstance(max_units_map, dict):
                    value = safe_int(max_units_map.get(instructor_code), 0)
                    if value > 0:
                        logger.info(
                            "✅ سقف واحد استاد %s از max_units: %s",
                            instructor_code,
                            value
                        )
                        return value
                    else:
                        logger.warning(
                            "⚠️ سقف واحد استاد %s در max_units صفر یا نامعتبر است (مقدار: %s). "
                            "سقف نامحدود در نظر گرفته می‌شود.",
                            instructor_code,
                            value
                        )
                        return None

            # ============================================================
            # ۲. جستجوی رکورد استاد در ساختارهای دیگر
            # ============================================================
            record = get_instructor_record(instructor_code)

            if not record:
                logger.warning(
                    "⚠️ رکوردی برای استاد %s یافت نشد. سقف واحد نامحدود در نظر گرفته می‌شود.",
                    instructor_code
                )
                return None

            possible_keys = (
                "max_teaching_units",
                "max_units",
                "teaching_capacity",
                "unit_capacity",
                "max_weekly_units",
                "max_teaching_load",
                "weekly_unit_limit",
                "teaching_unit_limit",
            )

            for key in possible_keys:
                if key not in record:
                    continue

                value = safe_int(record.get(key), 0)

                if value > 0:
                    logger.info(
                        "✅ سقف واحد استاد %s از رکورد (%s): %s",
                        instructor_code,
                        key,
                        value
                    )
                    return value

            logger.warning(
                "⚠️ سقف واحد برای استاد %s در هیچ فیلدی یافت نشد. نامحدود در نظر گرفته می‌شود.",
                instructor_code
            )
            return None

        def get_interval_metrics(
                slot_start: str,
                slot_end: str,
                pref_start: str,
                pref_end: str
        ) -> Dict[str, Any]:
            """
            محاسبه کیفیت هم‌خوانی اسلات با بازه مطلوب.
            """
            slot_start_min = time_to_minutes(slot_start)
            slot_end_min = time_to_minutes(slot_end)

            pref_start_min = time_to_minutes(pref_start)
            pref_end_min = time_to_minutes(pref_end)

            fully_inside = (
                slot_start_min >= pref_start_min
                and slot_end_min <= pref_end_min
            )

            start_inside = (
                pref_start_min <= slot_start_min < pref_end_min
            )

            end_inside = (
                pref_start_min < slot_end_min <= pref_end_min
            )

            overlap_start = max(slot_start_min, pref_start_min)
            overlap_end = min(slot_end_min, pref_end_min)

            overlap_minutes = max(0, overlap_end - overlap_start)

            slot_duration = max(1, slot_end_min - slot_start_min)
            overlap_ratio = overlap_minutes / slot_duration

            # فاصله کامل اسلات از بازه:
            # اگر اسلات با بازه همپوشانی داشته باشد، فاصله صفر است.
            if slot_end_min < pref_start_min:
                distance = pref_start_min - slot_end_min
            elif slot_start_min > pref_end_min:
                distance = slot_start_min - pref_end_min
            else:
                distance = 0

            # فاصله زمان شروع اسلات از شروع بازه مطلوب.
            start_offset_from_preference = (
                slot_start_min - pref_start_min
            )

            start_before_preference = max(
                0,
                pref_start_min - slot_start_min
            )

            start_after_preference = max(
                0,
                slot_start_min - pref_start_min
            )

            return {
                "fully_inside": fully_inside,
                "start_inside": start_inside,
                "end_inside": end_inside,
                "overlap_minutes": overlap_minutes,
                "overlap_ratio": overlap_ratio,
                "distance": distance,
                "slot_start_minutes": slot_start_min,
                "slot_end_minutes": slot_end_min,
                "pref_start_minutes": pref_start_min,
                "pref_end_minutes": pref_end_min,
                "start_offset_from_preference": start_offset_from_preference,
                "start_before_preference": start_before_preference,
                "start_after_preference": start_after_preference,
            }

        def is_candidate_allowed(
                metrics: Dict[str, Any],
                mode: str,
                tolerance_minutes: int = 0,
        ) -> bool:
            """
            بررسی مجاز بودن کاندیدا در مرحله انتخابی.

            strict:
                اسلات‌هایی که با بازه مطلوب همپوشانی داشته باشند (overlap_minutes > 0)
                مجاز هستند. اسلات‌های کاملاً داخل بازه اولویت بالاتری دارند.

            tolerance:
                زمان شروع اسلات می‌تواند تا tolerance_minutes دقیقه
                قبل یا بعد از شروع بازه مطلوب باشد.

                مثال برای بازه 16:00:
                tolerance = 30:
                    15:30 -> مجاز
                    16:00 -> مجاز
                    16:30 -> مجاز
                    15:00 -> غیرمجاز
            """
            if mode == "strict":
                # تغییر: به جای fully_inside، overlap_minutes > 0 را شرط می‌کنیم
                return metrics["overlap_minutes"] > 0

            if mode == "tolerance":
                start_offset = metrics["start_offset_from_preference"]

                return (
                    -tolerance_minutes
                    <= start_offset
                    <= tolerance_minutes
                )

            if mode == "fallback":
                return True

            return False

        def get_candidate_sort_key(
                candidate: Dict[str, Any]
        ) -> Tuple:
            """
            کلید مرتب‌سازی کیفیت اسلات.

            ترتیب:
            1. کاملاً داخل بازه مطلوب
            2. شروع داخل بازه مطلوب
            3. همپوشانی بیشتر
            4. فاصله کمتر از بازه
            5. فاصله کمتر شروع از شروع مطلوب
            6. اولویت بهتر روز
            7. زمان شروع زودتر
            """
            return (
                -int(candidate["fully_inside"]),
                -int(candidate["start_inside"]),
                -candidate["overlap_minutes"],
                candidate["distance"],
                abs(candidate["start_offset_from_preference"]),
                candidate["priority"],
                candidate["slot_start_minutes"],
                candidate["slot_end_minutes"],
            )

        def get_best_candidate(
                course: Dict,
                day_preferences: List[Tuple[str, str, int]],
                occupied_slots: List[Tuple[str, str]],
                mode: str,
                tolerance_minutes: int = 0,
                debug: bool = False,
        ) -> Optional[Dict[str, Any]]:
            """
            پیدا کردن بهترین اسلات برای یک درس در یک روز مشخص.
            """
            candidates: List[Dict[str, Any]] = []

            # پیدا کردن آخرین زمان پایان در occupied_slots برای تشویق اسلات‌های پشت‌سرهم
            last_end_min = 0
            if occupied_slots:
                for occ_start, occ_end in occupied_slots:
                    end_min = time_to_minutes(occ_end)
                    if end_min > last_end_min:
                        last_end_min = end_min

            course_name = course.get("course_name", "نامشخص")
            group = course.get("group_number", "نامشخص")
            instructor_code = course.get("instructor_code", "نامشخص")

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
                        pref_end=pref_end,
                    )

                    if not is_candidate_allowed(
                            metrics=metrics,
                            mode=mode,
                            tolerance_minutes=tolerance_minutes
                    ):
                        continue

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
                    score -= (
                        abs(
                            metrics["start_offset_from_preference"]
                        ) * 0.25
                    )

                    # ====== تشویق اسلات‌های بلافاصله بعد از آخرین کلاس ======
                    slot_start_min = time_to_minutes(slot_start)
                    if last_end_min > 0 and (slot_start_min - last_end_min) <= 5:
                        score += 200.0  # امتیاز تشویقی قابل توجه
                        if debug:
                            logger.info(
                                f"   🔹 تشویق پشت‌سرهم: {slot_start}-{slot_end} "
                                f"(فاصله از آخرین کلاس: {slot_start_min - last_end_min} دقیقه) → +200 امتیاز"
                            )

                    candidates.append({
                        "slot_start": slot_start,
                        "slot_end": slot_end,
                        "priority": pref_priority,
                        "score": score,
                        **metrics,
                    })

            if not candidates:
                if debug:
                    logger.info(f"   ❌ هیچ کاندیدایی برای {course_name} گروه {group} یافت نشد")
                return None

            # مرتب‌سازی کاندیداها
            candidates.sort(key=get_candidate_sort_key)

            # لاگ دقیق برای استاد خاص (کد 256)
            if instructor_code == "256" and debug:
                logger.info(f"   📋 کاندیداهای {course_name} گروه {group} در حالت {mode} (تساهل: {tolerance_minutes}):")
                for i, cand in enumerate(candidates[:10]):  # فقط 10 تای اول
                    logger.info(
                        f"      {i+1}. {cand['slot_start']}-{cand['slot_end']} | "
                        f"fully_inside={cand['fully_inside']} | "
                        f"start_inside={cand['start_inside']} | "
                        f"overlap={cand['overlap_minutes']} | "
                        f"distance={cand['distance']} | "
                        f"offset={cand['start_offset_from_preference']} | "
                        f"priority={cand['priority']} | "
                        f"score={cand['score']:.2f}"
                    )

            return candidates[0]

        def choose_next_course_for_day(
                remaining_courses: List[Dict],
                day_preferences: List[Tuple[str, str, int]],
                occupied_slots: List[Tuple[str, str]],
                mode: str,
                tolerance_minutes: int,
                used_units: int,
                max_units: Optional[int],
                debug: bool = False,
        ) -> Optional[Dict[str, Any]]:
            """
            بهترین درس برای یک روز در صف حلقوی.

            در این تابع سقف واحد استاد نیز بررسی می‌شود.
            اولویت با دروس با واحد بیشتر است.
            """
            options: List[Dict[str, Any]] = []

            for queue_index, course in enumerate(remaining_courses):
                course_units = get_course_units(course)

                # ============================================================
                # بررسی سقف واحد
                # ============================================================
                if (
                    max_units is not None
                    and used_units + course_units > max_units
                ):
                    logger.debug(
                        "⛔ درس '%s' (واحد %s) برای استاد با سقف %s رد شد (مصرف فعلی: %s)",
                        course.get("course_name"),
                        course_units,
                        max_units,
                        used_units
                    )
                    continue

                candidate = get_best_candidate(
                    course=course,
                    day_preferences=day_preferences,
                    occupied_slots=occupied_slots,
                    mode=mode,
                    tolerance_minutes=tolerance_minutes,
                    debug=debug,
                )

                if candidate is None:
                    continue

                options.append({
                    "queue_index": queue_index,
                    "course": course,
                    "candidate": candidate,
                    "course_units": course_units,
                })

            if not options:
                return None

            # کلید مرتب‌سازی: اولویت با واحد بیشتر، سپس امتیاز اولویت، سپس کیفیت کاندیدا
            def choose_key(item: Dict[str, Any]) -> Tuple:
                candidate = item["candidate"]
                course = item["course"]
                course_units = item["course_units"]

                return (
                    -course_units,  # 3 > 2 > 1
                    -course.get("priority_score", 0),
                    -int(candidate["fully_inside"]),
                    -int(candidate["start_inside"]),
                    -candidate["overlap_minutes"],
                    candidate["distance"],
                    abs(candidate["start_offset_from_preference"]),
                    candidate["priority"],
                    candidate["slot_start_minutes"],
                    item["queue_index"],
                )

            options.sort(key=choose_key)

            # لاگ انتخاب نهایی برای استاد خاص
            if debug and options:
                selected = options[0]
                course = selected["course"]
                candidate = selected["candidate"]
                logger.info(
                    f"   ✅ انتخاب نهایی: {course.get('course_name')} گروه {course.get('group_number')} "
                    f"(واحد {selected['course_units']}) → {candidate['slot_start']}-{candidate['slot_end']} "
                    f"(امتیاز: {candidate['score']:.2f})"
                )

            return options[0]

        def choose_global_fallback_candidate(
                remaining_courses: List[Dict],
                sorted_days: List[int],
                day_preferences: Dict[int, List[Tuple[str, str, int]]],
                occupied: Dict[int, List[Tuple[str, str]]],
                used_units: int,
                max_units: Optional[int],
                debug: bool = False,
        ) -> Optional[Dict[str, Any]]:
            """
            انتخاب سراسری بهترین کاندیدا در fallback روزهای مطلوب.

            تفاوت مهم با حلقه قدیمی:
            این تابع روزها را یکی‌یکی پر نمی‌کند؛
            همه روزهای مطلوب و همه درس‌های باقی‌مانده را با هم مقایسه می‌کند.
            """
            options: List[Dict[str, Any]] = []

            for day in sorted_days:
                for queue_index, course in enumerate(remaining_courses):
                    course_units = get_course_units(course)

                    # ============================================================
                    # بررسی سقف واحد
                    # ============================================================
                    if (
                        max_units is not None
                        and used_units + course_units > max_units
                    ):
                        continue

                    candidate = get_best_candidate(
                        course=course,
                        day_preferences=day_preferences[day],
                        occupied_slots=occupied[day],
                        mode="fallback",
                        debug=debug,
                    )

                    if candidate is None:
                        continue

                    options.append({
                        "day": day,
                        "queue_index": queue_index,
                        "course": course,
                        "candidate": candidate,
                        "course_units": course_units,
                    })

            if not options:
                return None

            def fallback_key(item: Dict[str, Any]) -> Tuple:
                candidate = item["candidate"]
                course = item["course"]
                course_units = item["course_units"]

                return (
                    -course_units,
                    -course.get("priority_score", 0),
                    -int(candidate["fully_inside"]),
                    -int(candidate["start_inside"]),
                    -candidate["overlap_minutes"],
                    candidate["distance"],
                    abs(candidate["start_offset_from_preference"]),
                    candidate["priority"],
                    candidate["slot_start_minutes"],
                    item["day"],
                    item["queue_index"],
                )

            options.sort(key=fallback_key)

            # لاگ انتخاب نهایی برای استاد خاص
            if debug and options:
                selected = options[0]
                course = selected["course"]
                candidate = selected["candidate"]
                day = selected["day"]
                logger.info(
                    f"   🌍 انتخاب سراسری: {course.get('course_name')} گروه {course.get('group_number')} "
                    f"(واحد {selected['course_units']}) در روز {get_day_name(day)} → "
                    f"{candidate['slot_start']}-{candidate['slot_end']} (امتیاز: {candidate['score']:.2f})"
                )

            return options[0]

        def assign_course(
                course: Dict,
                instructor_code: str,
                day: int,
                candidate: Dict[str, Any],
                match_level: str,
                tolerance: Optional[int],
        ) -> None:
            """
            ثبت تخصیص نهایی درس.
            """
            course["day"] = day
            course["start"] = candidate["slot_start"]
            course["end"] = candidate["slot_end"]

            course["schedule_match_level"] = match_level
            course["schedule_tolerance"] = tolerance
            course["schedule_match_score"] = round(
                candidate.get("score", 0.0),
                2
            )

            course["schedule_distance_minutes"] = candidate.get(
                "distance"
            )

            course["schedule_fully_inside_preference"] = candidate.get(
                "fully_inside",
                False,
            )

            course["schedule_start_inside_preference"] = candidate.get(
                "start_inside",
                False,
            )

            course["schedule_overlap_minutes"] = candidate.get(
                "overlap_minutes",
                0,
            )

            course["schedule_start_offset_from_preference"] = (
                candidate.get("start_offset_from_preference")
            )

            assigned.append(course)

        def mark_course_unassigned(
                course: Dict,
                reason: str,
                match_level: str = "unassigned",
        ) -> None:
            """ثبت درس تخصیص‌نیافته."""
            course["day"] = None
            course["start"] = None
            course["end"] = None

            course["schedule_match_level"] = match_level
            course["schedule_tolerance"] = None
            course["schedule_match_score"] = 0
            course["schedule_distance_minutes"] = None
            course["schedule_fully_inside_preference"] = False
            course["schedule_start_inside_preference"] = False
            course["schedule_overlap_minutes"] = 0
            course["schedule_start_offset_from_preference"] = None
            course["unassigned_reason"] = reason

            unassigned.append(course)

        def run_round_robin_phase(
                instructor_code: str,
                remaining_courses: List[Dict],
                sorted_days: List[int],
                day_preferences: Dict[int, List[Tuple[str, str, int]]],
                occupied: Dict[int, List[Tuple[str, str]]],
                mode: str,
                match_level: str,
                used_units_ref: Dict[str, int],
                max_units: Optional[int],
                initial_tolerance: int = 0,
                tolerance_increment_per_round: int = 0,
        ) -> int:
            """
            اجرای تخصیص با صف حلقوی.

            در هر دور:
                هر روز مطلوب حداکثر یک درس دریافت می‌کند.

            برای mode='tolerance':
                - دور اول: initial_tolerance
                - هر دور بعد: initial_tolerance + (round - 1) * increment

            مثال:
                initial_tolerance=30
                tolerance_increment_per_round=60

                دور اول: 30 دقیقه
                دور دوم: 90 دقیقه
                دور سوم: 150 دقیقه
            """
            assigned_in_phase = 0
            round_number = 0

            # فعال‌سازی debug برای استاد خاص
            debug = (instructor_code == "256")

            while remaining_courses:
                round_number += 1
                assigned_in_round = False

                if mode == "tolerance":
                    current_tolerance = (
                        initial_tolerance
                        + (
                            (round_number - 1)
                            * tolerance_increment_per_round
                        )
                    )
                else:
                    current_tolerance = 0

                logger.debug(
                    "🔄 استاد %s | مرحله %s | دور %s | تساهل شروع: %s دقیقه",
                    instructor_code,
                    mode,
                    round_number,
                    current_tolerance,
                )

                if debug:
                    logger.info(f"🔍 === مرحله {mode} دور {round_number} برای استاد {instructor_code} ===")

                for day in sorted_days:
                    if not remaining_courses:
                        break

                    if debug:
                        logger.info(f"   📅 روز {get_day_name(day)}:")

                    selected = choose_next_course_for_day(
                        remaining_courses=remaining_courses,
                        day_preferences=day_preferences[day],
                        occupied_slots=occupied[day],
                        mode=mode,
                        tolerance_minutes=current_tolerance,
                        used_units=used_units_ref["value"],
                        max_units=max_units,
                        debug=debug,
                    )

                    if selected is None:
                        if debug:
                            logger.info(f"      ❌ هیچ درس مناسبی برای این روز یافت نشد")
                        continue

                    queue_index = selected["queue_index"]
                    course = selected["course"]
                    candidate = selected["candidate"]
                    course_units = selected["course_units"]

                    if debug:
                        logger.info(
                            f"      ✅ انتخاب: {course.get('course_name')} گروه {course.get('group_number')} "
                            f"(واحد {course_units}) → {candidate['slot_start']}-{candidate['slot_end']}"
                        )

                    assign_course(
                        course=course,
                        instructor_code=instructor_code,
                        day=day,
                        candidate=candidate,
                        match_level=match_level,
                        tolerance=(
                            current_tolerance
                            if mode == "tolerance"
                            else None
                        ),
                    )

                    occupied[day].append(
                        (
                            candidate["slot_start"],
                            candidate["slot_end"],
                        )
                    )

                    remaining_courses.pop(queue_index)

                    used_units_ref["value"] += course_units

                    assigned_in_phase += 1
                    assigned_in_round = True

                    logger.info(
                        "✅ استاد %s | درس=%s | واحد=%s | روز=%s | %s-%s | "
                        "مرحله=%s | تساهل=%s | واحد مصرف‌شده=%s/%s",
                        instructor_code,
                        course.get("course_name"),
                        course_units,
                        get_day_name(day),
                        candidate["slot_start"],
                        candidate["slot_end"],
                        match_level,
                        current_tolerance if mode == "tolerance" else "-",
                        used_units_ref["value"],
                        max_units if max_units is not None else "نامحدود",
                    )

                # اگر در یک دور هیچ تخصیصی نداشتیم، ادامه دادن بی‌فایده است.
                if not assigned_in_round:
                    break

            return assigned_in_phase

        def run_non_preferred_fallback(
                instructor_code: str,
                remaining_courses: List[Dict],
                preferred_days: List[int],
                occupied: Dict[int, List[Tuple[str, str]]],
                used_units_ref: Dict[str, int],
                max_units: Optional[int],
        ) -> int:
            """
            fallback برای روزهای غیرمطلوب.

            این مرحله بعد از اتمام strict، tolerance و fallback
            در روزهای مطلوب اجرا می‌شود.

            تخصیص نیز حلقوی است تا یک روز غیرمطلوب بی‌دلیل کامل پر نشود.
            """
            non_preferred_days = [
                day
                for day in range(6)
                if day not in preferred_days
            ]

            assigned_in_phase = 0

            while remaining_courses:
                assigned_in_round = False

                for day in non_preferred_days:
                    if not remaining_courses:
                        break

                    available: List[Dict[str, Any]] = []

                    for queue_index, course in enumerate(remaining_courses):
                        course_units = get_course_units(course)

                        # ============================================================
                        # بررسی سقف واحد
                        # ============================================================
                        if (
                            max_units is not None
                            and used_units_ref["value"] + course_units > max_units
                        ):
                            continue

                        for slot_start, slot_end in get_course_slots(course):
                            if is_conflict(
                                    occupied[day],
                                    slot_start,
                                    slot_end
                            ):
                                continue

                            available.append({
                                "queue_index": queue_index,
                                "course": course,
                                "course_units": course_units,
                                "slot_start": slot_start,
                                "slot_end": slot_end,
                            })
                            break

                    if not available:
                        continue

                    # اولویت با دروس با واحد بیشتر
                    available.sort(
                        key=lambda item: (
                            -item["course_units"],
                            -item["course"].get("priority_score", 0),
                            time_to_minutes(item["slot_start"]),
                            item["queue_index"],
                        )
                    )

                    selected = available[0]

                    queue_index = selected["queue_index"]
                    course = selected["course"]
                    course_units = selected["course_units"]

                    candidate = {
                        "slot_start": selected["slot_start"],
                        "slot_end": selected["slot_end"],
                        "score": 0.0,
                        "distance": None,
                        "fully_inside": False,
                        "start_inside": False,
                        "overlap_minutes": 0,
                        "start_offset_from_preference": None,
                    }

                    assign_course(
                        course=course,
                        instructor_code=instructor_code,
                        day=day,
                        candidate=candidate,
                        match_level="fallback_non_preferred_day",
                        tolerance=None,
                    )

                    occupied[day].append(
                        (
                            selected["slot_start"],
                            selected["slot_end"],
                        )
                    )

                    remaining_courses.pop(queue_index)
                    used_units_ref["value"] += course_units

                    assigned_in_phase += 1
                    assigned_in_round = True

                    logger.info(
                        "⚠️ fallback غیرمطلوب | استاد=%s | درس=%s | واحد=%s | روز=%s | "
                        "%s-%s | مصرف=%s/%s",
                        instructor_code,
                        course.get("course_name"),
                        course_units,
                        get_day_name(day),
                        selected["slot_start"],
                        selected["slot_end"],
                        used_units_ref["value"],
                        max_units if max_units is not None else "نامحدود",
                    )

                if not assigned_in_round:
                    break

            return assigned_in_phase

        # ============================================================
        # گروه‌بندی دروس بر اساس استاد
        # ============================================================
        courses_by_instructor = defaultdict(list)
        no_instructor_courses: List[Dict] = []

        for course in courses_with_instructor:
            instructor_code = course.get("instructor_code")

            if instructor_code:
                courses_by_instructor[instructor_code].append(course)
                continue

            mark_course_unassigned(
                course=course,
                reason="درس در مرحله تخصیص استاد ندارد",
                match_level="no_instructor",
            )

            no_instructor_courses.append(course)

        if no_instructor_courses:
            logger.warning(
                "⚠️ %s درس بدون استاد به unassigned منتقل شد.",
                len(no_instructor_courses),
            )

        logger.info(
            "👨‍🏫 تعداد اساتید: %s",
            len(courses_by_instructor),
        )

        # ============================================================
        # شمارنده‌های گزارش
        # ============================================================
        total_assigned_strict = 0
        total_assigned_tolerance = 0
        total_assigned_preferred_fallback = 0
        total_assigned_non_preferred_fallback = 0
        total_assigned_no_preference = 0

        # ============================================================
        # زمان‌بندی مستقل هر استاد
        # ============================================================
        for instructor_code, instructor_courses in courses_by_instructor.items():
            initial_count = len(instructor_courses)

            # مرتب‌سازی بر اساس واحد نزولی (بیشتر → اولویت بالاتر)
            remaining_courses = sorted(
                list(instructor_courses),
                key=lambda course: (
                    -course.get("units", 2),           # اولویت با واحد بیشتر
                    -course.get("priority_score", 0),  # سپس امتیاز اولویت
                    course.get("course_name", ""),
                    str(course.get("group_number", "")),
                )
            )

            instructor_unit_limit = get_instructor_unit_limit(
                instructor_code
            )

            used_units_ref = {"value": 0}

            logger.info(
                "👤 استاد %s: %s درس | سقف واحد=%s",
                instructor_code,
                initial_count,
                (
                    instructor_unit_limit
                    if instructor_unit_limit is not None
                    else "تعریف نشده (نامحدود)"
                ),
            )

            prefs = list(time_prefs.get(instructor_code, []))
            occupied = defaultdict(list)

            # --------------------------------------------------------
            # استاد بدون مطلوبیت زمانی
            # --------------------------------------------------------
            if not prefs:
                logger.warning(
                    "⚠️ استاد %s مطلوبیت زمانی ندارد؛ "
                    "تخصیص پیش‌فرض با رعایت سقف واحد اجرا می‌شود.",
                    instructor_code,
                )

                for course in list(remaining_courses):
                    course_units = get_course_units(course)

                    # ============================================================
                    # بررسی سقف واحد
                    # ============================================================
                    if (
                        instructor_unit_limit is not None
                        and used_units_ref["value"] + course_units
                        > instructor_unit_limit
                    ):
                        remaining_courses.remove(course)

                        mark_course_unassigned(
                            course=course,
                            reason=(
                                f"سقف واحد تدریس استاد {instructor_code} "
                                f"تکمیل شده است "
                                f"({used_units_ref['value']}/{instructor_unit_limit})"
                            ),
                            match_level="unit_limit_reached",
                        )

                        continue

                    selected_day = None
                    selected_slot = None

                    for day in range(6):
                        for slot_start, slot_end in get_course_slots(course):
                            if not is_conflict(
                                    occupied[day],
                                    slot_start,
                                    slot_end
                            ):
                                selected_day = day
                                selected_slot = (slot_start, slot_end)
                                break

                        if selected_slot is not None:
                            break

                    remaining_courses.remove(course)

                    if selected_slot is None:
                        mark_course_unassigned(
                            course=course,
                            reason=(
                                f"برای استاد {instructor_code} "
                                f"اسلات آزاد پیدا نشد"
                            ),
                        )
                        continue

                    candidate = {
                        "slot_start": selected_slot[0],
                        "slot_end": selected_slot[1],
                        "score": 0.0,
                        "distance": None,
                        "fully_inside": False,
                        "start_inside": False,
                        "overlap_minutes": 0,
                        "start_offset_from_preference": None,
                    }

                    assign_course(
                        course=course,
                        instructor_code=instructor_code,
                        day=selected_day,
                        candidate=candidate,
                        match_level="no_preference_default",
                        tolerance=None,
                    )

                    occupied[selected_day].append(selected_slot)
                    used_units_ref["value"] += course_units
                    total_assigned_no_preference += 1

                    logger.info(
                        "✅ استاد %s (بدون مطلوبیت) | درس=%s | واحد=%s | روز=%s | %s-%s | مصرف=%s/%s",
                        instructor_code,
                        course.get("course_name"),
                        course_units,
                        get_day_name(selected_day),
                        selected_slot[0],
                        selected_slot[1],
                        used_units_ref["value"],
                        instructor_unit_limit if instructor_unit_limit is not None else "نامحدود",
                    )

                logger.info(
                    "✅ استاد %s بدون مطلوبیت: %s واحد تخصیص یافت.",
                    instructor_code,
                    used_units_ref["value"],
                )

                continue

            # --------------------------------------------------------
            # آماده‌سازی مطلوبیت‌های زمانی
            # --------------------------------------------------------
            day_preferences = defaultdict(list)

            for day_num, start, end, priority in prefs:
                normalized_start, normalized_end = (
                    normalize_preference_window(start, end)
                )

                if (
                    normalized_start != start
                    or normalized_end != end
                ):
                    logger.info(
                        "🕒 اصلاح بازه مطلوب استاد %s در %s: %s-%s => %s-%s",
                        instructor_code,
                        get_day_name(day_num),
                        start,
                        end,
                        normalized_start,
                        normalized_end,
                    )

                day_preferences[day_num].append(
                    (
                        normalized_start,
                        normalized_end,
                        priority,
                    )
                )

            for day in day_preferences:
                day_preferences[day].sort(
                    key=lambda item: (
                        item[2],
                        time_to_minutes(item[0]),
                        time_to_minutes(item[1]),
                    )
                )

            sorted_days = sorted(
                day_preferences.keys(),
                key=lambda day: (
                    min(
                        pref[2]
                        for pref in day_preferences[day]
                    ),
                    day,
                )
            )

            logger.info(
                "📅 ترتیب روزهای استاد %s: %s",
                instructor_code,
                [
                    (
                        get_day_name(day),
                        min(
                            pref[2]
                            for pref in day_preferences[day]
                        ),
                        [
                            f"{pref[0]}-{pref[1]}"
                            for pref in day_preferences[day]
                        ],
                    )
                    for day in sorted_days
                ],
            )

            # --------------------------------------------------------
            # مرحله 1: strict
            # اسلات‌های همپوشان با بازه مطلوب مجاز هستند.
            # تخصیص به‌صورت صف حلقوی با اولویت واحد بیشتر
            # --------------------------------------------------------
            strict_count = run_round_robin_phase(
                instructor_code=instructor_code,
                remaining_courses=remaining_courses,
                sorted_days=sorted_days,
                day_preferences=day_preferences,
                occupied=occupied,
                mode="strict",
                match_level="full",
                used_units_ref=used_units_ref,
                max_units=instructor_unit_limit,
            )

            total_assigned_strict += strict_count

            logger.info(
                "   مرحله strict برای استاد %s: %s درس",
                instructor_code,
                strict_count,
            )

            # --------------------------------------------------------
            # مرحله 2: tolerance صف حلقوی
            #
            # دور اول: 30 دقیقه
            # هر دور بعدی: +60 دقیقه
            # --------------------------------------------------------
            tolerance_count = run_round_robin_phase(
                instructor_code=instructor_code,
                remaining_courses=remaining_courses,
                sorted_days=sorted_days,
                day_preferences=day_preferences,
                occupied=occupied,
                mode="tolerance",
                match_level="tolerance_progressive",
                used_units_ref=used_units_ref,
                max_units=instructor_unit_limit,
                initial_tolerance=30,
                tolerance_increment_per_round=60,
            )

            total_assigned_tolerance += tolerance_count

            logger.info(
                "   مرحله tolerance تدریجی برای استاد %s: %s درس",
                instructor_code,
                tolerance_count,
            )

            # --------------------------------------------------------
            # مرحله 3: fallback سراسری در روزهای مطلوب
            # --------------------------------------------------------
            preferred_fallback_count = 0

            while remaining_courses:
                selected = choose_global_fallback_candidate(
                    remaining_courses=remaining_courses,
                    sorted_days=sorted_days,
                    day_preferences=day_preferences,
                    occupied=occupied,
                    used_units=used_units_ref["value"],
                    max_units=instructor_unit_limit,
                    debug=(instructor_code == "256"),
                )

                if selected is None:
                    break

                queue_index = selected["queue_index"]
                course = selected["course"]
                candidate = selected["candidate"]
                day = selected["day"]
                course_units = selected["course_units"]

                assign_course(
                    course=course,
                    instructor_code=instructor_code,
                    day=day,
                    candidate=candidate,
                    match_level="preferred_day_fallback",
                    tolerance=None,
                )

                occupied[day].append(
                    (
                        candidate["slot_start"],
                        candidate["slot_end"],
                    )
                )

                remaining_courses.pop(queue_index)
                used_units_ref["value"] += course_units
                preferred_fallback_count += 1

                logger.info(
                    "🔁 fallback مطلوب | استاد=%s | درس=%s | واحد=%s | روز=%s | "
                    "%s-%s | مصرف=%s/%s",
                    instructor_code,
                    course.get("course_name"),
                    course_units,
                    get_day_name(day),
                    candidate["slot_start"],
                    candidate["slot_end"],
                    used_units_ref["value"],
                    (
                        instructor_unit_limit
                        if instructor_unit_limit is not None
                        else "نامحدود"
                    ),
                )

            total_assigned_preferred_fallback += preferred_fallback_count

            logger.info(
                "   مرحله fallback سراسری روزهای مطلوب برای استاد %s: %s درس",
                instructor_code,
                preferred_fallback_count,
            )

            # --------------------------------------------------------
            # مرحله 4: fallback روزهای غیرمطلوب
            # --------------------------------------------------------
            non_preferred_fallback_count = run_non_preferred_fallback(
                instructor_code=instructor_code,
                remaining_courses=remaining_courses,
                preferred_days=sorted_days,
                occupied=occupied,
                used_units_ref=used_units_ref,
                max_units=instructor_unit_limit,
            )

            total_assigned_non_preferred_fallback += (
                non_preferred_fallback_count
            )

            logger.info(
                "   مرحله fallback روزهای غیرمطلوب برای استاد %s: %s درس",
                instructor_code,
                non_preferred_fallback_count,
            )

            # --------------------------------------------------------
            # درس‌های باقی‌مانده
            # --------------------------------------------------------
            if remaining_courses:
                for course in remaining_courses:
                    course_units = get_course_units(course)

                    if (
                        instructor_unit_limit is not None
                        and used_units_ref["value"] + course_units
                        > instructor_unit_limit
                    ):
                        reason = (
                            f"سقف واحد تدریس استاد {instructor_code} "
                            f"تکمیل شده است "
                            f"({used_units_ref['value']}/{instructor_unit_limit})"
                        )
                        level = "unit_limit_reached"
                    else:
                        reason = (
                            f"هیچ اسلات آزاد و مناسب برای استاد "
                            f"{instructor_code} پیدا نشد"
                        )
                        level = "unassigned"

                    mark_course_unassigned(
                        course=course,
                        reason=reason,
                        match_level=level,
                    )

                    logger.error(
                        "❌ درس '%s' گروه %s برای استاد %s تخصیص نیافت: %s",
                        course.get("course_name"),
                        course.get("group_number"),
                        instructor_code,
                        reason,
                    )

            assigned_count_for_instructor = (
                initial_count - len(remaining_courses)
            )

            logger.info(
                "📊 استاد %s: %s تخصیص یافت | %s تخصیص‌نیافته | "
                "واحد مصرف‌شده=%s/%s",
                instructor_code,
                assigned_count_for_instructor,
                len(remaining_courses),
                used_units_ref["value"],
                (
                    instructor_unit_limit
                    if instructor_unit_limit is not None
                    else "نامحدود"
                ),
            )

        # ============================================================
        # کنترل نهایی: هیچ درس ورودی نباید گم شود
        # ============================================================
        processed_courses = {
            id(course)
            for course in assigned + unassigned
        }

        missing_courses: List[Dict] = []

        for course in courses_with_instructor:
            if id(course) in processed_courses:
                continue

            mark_course_unassigned(
                course=course,
                reason=(
                    "درس پس از تخصیص استاد در هیچ مرحله‌ای "
                    "زمان‌بندی نشد (گم‌شده)"
                ),
            )

            missing_courses.append(course)

        if missing_courses:
            logger.error(
                "❌ %s درس گم‌شده به unassigned افزوده شد.",
                len(missing_courses),
            )

            for course in missing_courses:
                logger.error(
                    "   درس '%s' گروه %s",
                    course.get("course_name"),
                    course.get("group_number"),
                )

        # ============================================================
        # گزارش نهایی
        # ============================================================
        total_assigned = len(assigned)
        total_unassigned = len(unassigned)
        total_output = total_assigned + total_unassigned

        logger.info("=" * 75)
        logger.info("📊 خلاصه نهایی زمان‌بندی:")
        logger.info("   تعداد ورودی: %s", total_input)

        logger.info(
            "   تخصیص‌یافته: %s "
            "(strict: %s، tolerance: %s، fallback مطلوب: %s، "
            "fallback غیرمطلوب: %s، بدون مطلوبیت: %s)",
            total_assigned,
            total_assigned_strict,
            total_assigned_tolerance,
            total_assigned_preferred_fallback,
            total_assigned_non_preferred_fallback,
            total_assigned_no_preference,
        )

        logger.info(
            "   تخصیص‌نیافته: %s",
            total_unassigned,
        )

        if total_output != total_input:
            logger.error(
                "⚠️ تعداد خروجی (%s) با تعداد ورودی (%s) متفاوت است. "
                "%s درس گم شده‌اند.",
                total_output,
                total_input,
                total_input - total_output,
            )
        else:
            logger.info(
                "✅ همه %s درس در خروجی حضور دارند.",
                total_input,
            )

        logger.info("=" * 75)

        return assigned, unassigned