# app/services/schedule/data_preparer.py
# آماده‌سازی داده‌های ورودی (مرحله ۱).
import re
from typing import List, Dict

from app.utils.helpers import normalize_code
from app.services.schedule.slot_times import normalize_term

class DataPreparer:
    @staticmethod
    def prepare(basket: List[Dict]) -> List[Dict]:
        """
        آماده‌سازی و نرمال‌سازی داده‌های درس‌های موجود در سبد.

        این تابع فیلدهای缺失 را تکمیل کرده، کد یکتا را نرمال‌سازی می‌کند
        و با استفاده از normalize_term، نام ترم را یکسان‌سازی و کلید استاندارد آن را ذخیره می‌کند.

        Args:
            basket: لیست دیکشنری‌های درس

        Returns:
            لیست درس‌های آماده‌شده
        """
        prepared = []
        for course in basket:
            new_course = course.copy()

            # ۱. نرمال‌سازی کد یکتا
            if "unique_code" in new_course:
                new_course["unique_code"] = normalize_code(new_course["unique_code"])

            # ۲. نرمال‌سازی و اعتبارسنجی ترم
            term_raw = new_course.get("term", "").strip()
            term_key = None
            term_number = None

            if term_raw:
                try:
                    term_key = normalize_term(term_raw)
                    # استخراج شماره ترم از کلید استاندارد
                    if term_key == "semester_1":
                        term_number = 1
                    elif term_key == "semester_2":
                        term_number = 2
                    elif term_key == "summer":
                        term_number = 3  # یا هر عدد دیگری برای تابستان
                except ValueError:
                    # اگر ترم نامعتبر بود، از روش قبلی استفاده می‌کنیم
                    term_key = None
                    # شماره ترم را از رشته استخراج می‌کنیم
                    match = re.search(r'\d+', term_raw)
                    term_number = int(match.group()) if match else 1
            else:
                # اگر ترم خالی بود، پیش‌فرض می‌گذاریم
                term_number = 1

            # اگر term_key مشخص نشد، از term_number برای تعیین کلید استفاده می‌کنیم
            if term_key is None:
                if term_number % 2 == 1:
                    term_key = "semester_1"
                else:
                    term_key = "semester_2"

            # ذخیره کلید استاندارد ترم در درس (برای استفاده در مراحل بعد)
            new_course["term_key"] = term_key
            # اگر term_number از قبل تعیین نشده یا از روش قبلی است، مقدار آن را تنظیم می‌کنیم
            if "term_number" not in new_course or new_course["term_number"] is None:
                new_course["term_number"] = term_number
            # همچنین می‌توانیم فیلد term را با کلید استاندارد به‌روز کنیم (اختیاری)
            # new_course["term"] = term_key

            # ۳. تکمیل فیلدهای缺失
            if "group_number" not in new_course:
                new_course["group_number"] = 1

            if "is_prerequisite" not in new_course:
                new_course["is_prerequisite"] = False

            if "student_demand" not in new_course:
                new_course["student_demand"] = 0

            if "units" not in new_course or new_course["units"] is None:
                new_course["units"] = 2  # مقدار پیش‌فرض

            # ۴. مقداردهی اولیه برای وضعیت تخصیص
            new_course["unassigned_reason"] = None

            prepared.append(new_course)

        return prepared