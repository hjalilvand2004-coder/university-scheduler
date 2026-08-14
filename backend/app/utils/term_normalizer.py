"""
ابزارهای نرمالیزه‌سازی ترم‌ها برای تطابق با داده‌های ناهمگون
"""


def normalize_term(term_str: str) -> int:
    """
    تبدیل عبارت ترم به عدد صحیح

    مثال‌ها:
        "ترم یک" → 1
        "ترم اول" → 1
        "ترم دو" → 2
        "ترم دوم" → 2
        "ترم سه" → 3
        "ترم سوم" → 3
        "ترم چهارم" → 4
        "ترم پنجم" → 5
        "ترم ششم" → 6
        "ترم هفتم" → 7
        "ترم هشتم" → 8
    """
    if not term_str:
        return 0

    # حذف کلمه "ترم" و فضای اضافی
    clean = term_str.replace("ترم", "").strip()

    # نگاشت کلمات به اعداد
    mapping = {
        "یک": 1, "اول": 1,
        "دو": 2, "دوم": 2,
        "سه": 3, "سوم": 3,
        "چهار": 4, "چهارم": 4,
        "پنج": 5, "پنجم": 5,
        "شش": 6, "ششم": 6,
        "هفت": 7, "هفتم": 7,
        "هشت": 8, "هشتم": 8,
    }

    return mapping.get(clean, 0)


def is_odd_term(term_number: int) -> bool:
    """بررسی فرد بودن ترم"""
    return term_number % 2 == 1


def is_even_term(term_number: int) -> bool:
    """بررسی زوج بودن ترم"""
    return term_number % 2 == 0


def get_target_terms(semester):
    """
    دریافت لیست ترم‌های هدف بر اساس نیمسال
    """
    from app.schemas.course import Semester
    if semester == Semester.MEHR:
        return [1, 3, 5, 7]  # ترم‌های فرد
    else:
        return [2, 4, 6, 8]  # ترم‌های زوج