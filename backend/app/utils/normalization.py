# app/utils/normalization.py
# توابع نرمال‌سازی کدها و روزها.
import re

def normalize_code(code: str) -> str:
    """
    نرمال‌سازی کد درس (حذف کاراکترهای غیرمجاز و تبدیل به حروف بزرگ)
    """
    if not code:
        return code
    normalized = re.sub(r'[^A-Za-z0-9_]', '', code)
    return normalized.upper()

def normalize_instructor_code(code: str) -> str:
    """
    نرمال‌سازی کد استاد (حذف فاصله‌ها و تبدیل اعداد به فرمت ساده)
    """
    if not code:
        return code
    cleaned = re.sub(r'\s+', '', code)
    if cleaned.isdigit():
        return str(int(cleaned))
    return cleaned

def normalize_day(day: str) -> str:
    """
    نرمال‌سازی نام روز (حذف فاصله‌های اضافی و نیم‌فاصله)
    """
    if not day:
        return day
    day = day.replace("\u200c", " ")  # حذف نیم‌فاصله
    day = " ".join(day.split())       # حذف فاصله‌های اضافی
    return day.replace(" ", "")