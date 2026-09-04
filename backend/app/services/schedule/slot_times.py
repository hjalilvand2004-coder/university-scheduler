# slot_times.py
from __future__ import annotations

from copy import deepcopy
from typing import Any, Optional, List, Dict, Union

from fastapi import APIRouter, HTTPException, Query


# ==========================================================
# تعریف DAY_MAP و normalize_day (برای استفاده در سایر ماژول‌ها)
# ==========================================================

DAY_MAP: Dict[str, int] = {
    "شنبه": 0,
    "یکشنبه": 1,
    "دوشنبه": 2,
    "سه‌شنبه": 3,
    "سهشنبه": 3,
    "چهارشنبه": 4,
    "پنجشنبه": 5,
    "جمعه": 6,
    "sat": 0,
    "sun": 1,
    "mon": 2,
    "tue": 3,
    "wed": 4,
    "thu": 5,
    "fri": 6,
}


def normalize_day(day: str) -> str:
    """
    نرمال‌سازی نام روز برای تطابق با کلیدهای DAY_MAP.
    ورودی می‌تواند فارسی یا انگلیسی باشد، با یا بدون نیم‌فاصله.
    اگر ورودی عددی باشد، آن را به صورت رشته برگردانده و سعی می‌کند با کلیدها تطابق دهد.
    """
    if not day:
        return ""
    # حذف فاصله‌های اضافی و نیم‌فاصله
    normalized = day.strip().replace("\u200c", "").replace(" ", "")
    # حذف 'ی' و 'ک' عربی
    normalized = normalized.replace("ي", "ی").replace("ى", "ی").replace("ك", "ک")
    # اگر ورودی عددی باشد، آن را به عدد تبدیل می‌کنیم (برای روزهای انگلیسی مثل 0,1,...)
    if normalized.isdigit():
        return normalized
    # جستجوی معکوس: اگر نام در DAY_MAP موجود باشد، کلید آن را برگردانیم
    for key in DAY_MAP:
        if key == normalized:
            return key
    # اگر تطابق کامل نبود، ممکن است نام با حروف کوچک/بزرگ تفاوت داشته باشد
    for key in DAY_MAP:
        if key.lower() == normalized.lower():
            return key
    # در نهایت اگر پیدا نشد، همان ورودی را برگردانیم (احتمالاً عدد)
    return normalized


# ==========================================================
# زمان‌بندی نیمسال اول / مهر
# ==========================================================

# اسلات‌های یک واحدی (معادل ۲ واحدی اما با تعداد واحد ۱)
ONE_UNIT_SLOTS: List[str] = [
    "07:30-09:15",
    "09:16-11:00",
    "11:01-12:45",
    "13:00-14:45",
    "14:46-16:30",
    "16:31-18:15",
    "18:16-20:00",
]

TWO_UNIT_SLOTS: List[str] = [
    "07:30-09:15",
    "09:16-11:00",
    "11:01-12:45",
    "13:00-14:45",
    "14:46-16:30",
    "16:31-18:15",
    "18:16-20:00",
]

THREE_UNIT_SLOTS: List[str] = [
    "07:30-10:10",
    "10:11-12:50",
    "13:00-15:30",
    "15:31-18:00",
    "18:01-20:30",
]

FOUR_UNIT_SLOTS: List[str] = [
    "07:30-10:50",
    "12:00-16:45",
    "16:46-20:30",
]


# ==========================================================
# زمان‌بندی نیمسال دوم / بهمن
# ==========================================================

# اسلات‌های یک واحدی برای بهمن (معادل ۲ واحدی بهمن)
BAHMAN_ONE_UNIT_SLOTS: List[str] = [
    "07:30-09:05",
    "09:06-10:40",
    "10:41-12:10",
    "13:00-14:50",
    "14:51-16:40",
    "16:41-18:20",
    "18:21-20:00",
]

BAHMAN_TWO_UNIT_SLOTS: List[str] = [
    "07:30-09:05",
    "09:06-10:40",
    "10:41-12:10",
    "13:00-14:50",
    "14:51-16:40",
    "16:41-18:20",
    "18:21-20:00",
]

BAHMAN_THREE_UNIT_SLOTS: List[str] = [
    "07:30-09:50",
    "09:51-12:10",
    "13:00-15:40",
    "15:51-18:20",
    "18:21-20:50",
]

BAHMAN_FOUR_UNIT_SLOTS: List[str] = [
    "07:30-10:40",
    "13:00-16:20",
    "16:41-20:20",
]


# ==========================================================
# داده اصلی همه ترم‌ها
# ==========================================================

SCHEDULES: Dict[str, Dict[int, List[str]]] = {
    "semester_1": {
        1: ONE_UNIT_SLOTS,
        2: TWO_UNIT_SLOTS,
        3: THREE_UNIT_SLOTS,
        4: FOUR_UNIT_SLOTS,
    },
    "semester_2": {
        1: BAHMAN_ONE_UNIT_SLOTS,
        2: BAHMAN_TWO_UNIT_SLOTS,
        3: BAHMAN_THREE_UNIT_SLOTS,
        4: BAHMAN_FOUR_UNIT_SLOTS,
    },
    "summer": {
        1: BAHMAN_ONE_UNIT_SLOTS,
        2: BAHMAN_TWO_UNIT_SLOTS,
        3: BAHMAN_THREE_UNIT_SLOTS,
        4: BAHMAN_FOUR_UNIT_SLOTS,
    },
}


# ==========================================================
# ساخت دیکشنری TERM_ALIASES به صورت خودکار با نگاشت صحیح
# ==========================================================

def _build_term_aliases() -> Dict[str, str]:
    """
    ساخت نگاشت کامل برای نام‌های مختلف ترم به کلیدهای استاندارد.
    قاعده: ترم‌های فرد (۱،۳،۵،۷،۹) -> semester_1
            ترم‌های زوج (۲،۴،۶،۸،۱۰) -> semester_2
            همچنین "مهر" و "نیمسال اول" -> semester_1
            "بهمن" و "نیمسال دوم" -> semester_2
            "تابستان" و "نیمسال تابستان" -> summer
    """
    aliases = {
        # نام‌های ثابت اصلی
        "semester_1": "semester_1",
        "semester1": "semester_1",
        "semester 1": "semester_1",
        "first": "semester_1",
        "first semester": "semester_1",
        "fall": "semester_1",
        "mehr": "semester_1",
        "meher": "semester_1",
        "مهر": "semester_1",
        "نیمسال اول": "semester_1",
        "نیم سال اول": "semester_1",
        "ترم اول": "semester_1",

        "semester_2": "semester_2",
        "semester2": "semester_2",
        "semester 2": "semester_2",
        "second": "semester_2",
        "second semester": "semester_2",
        "spring": "semester_2",
        "bahman": "semester_2",
        "بهمن": "semester_2",
        "نیمسال دوم": "semester_2",
        "نیم سال دوم": "semester_2",
        "ترم دوم": "semester_2",

        "summer": "summer",
        "summer semester": "summer",
        "تابستان": "summer",
        "نیمسال تابستان": "summer",
        "نیم سال تابستان": "summer",
        "ترم تابستان": "summer",
        "term summer": "summer",
    }

    # نگاشت اعداد فارسی و انگلیسی
    # ترم‌های فرد -> semester_1, ترم‌های زوج -> semester_2
    persian_numbers = {
        1: "یک", 2: "دو", 3: "سه", 4: "چهار", 5: "پنج",
        6: "شش", 7: "هفت", 8: "هشت", 9: "نه", 10: "ده"
    }
    persian_ordinal = {
        1: "اول", 2: "دوم", 3: "سوم", 4: "چهارم", 5: "پنجم",
        6: "ششم", 7: "هفتم", 8: "هشتم", 9: "نهم", 10: "دهم"
    }

    for num in range(1, 11):
        # تعیین ترم هدف
        if num % 2 == 1:  # فرد
            target = "semester_1"
        else:  # زوج
            target = "semester_2"

        # فارسی بدون پسوند (مثلاً "ترم یک")
        aliases[f"ترم {persian_numbers[num]}"] = target
        # فارسی با پسوند "م" (مثلاً "ترم اول")
        aliases[f"ترم {persian_ordinal[num]}"] = target
        # انگلیسی (مثلاً "term 1")
        aliases[f"term {num}"] = target

        # همچنین معادل انگلیسی با حروف
        english_words = {
            1: "one", 2: "two", 3: "three", 4: "four", 5: "five",
            6: "six", 7: "seven", 8: "eight", 9: "nine", 10: "ten"
        }
        english_ordinal = {
            1: "first", 2: "second", 3: "third", 4: "fourth", 5: "fifth",
            6: "sixth", 7: "seventh", 8: "eighth", 9: "ninth", 10: "tenth"
        }
        aliases[f"term {english_words[num]}"] = target
        aliases[f"{english_ordinal[num]} semester"] = target

        # فارسی با رقم (مثلاً "ترم ۴")
        persian_digit = str(num).translate(str.maketrans("0123456789", "۰۱۲۳۴۵۶۷۸۹"))
        aliases[f"ترم {persian_digit}"] = target

    return aliases


TERM_ALIASES = _build_term_aliases()


# ==========================================================
# تابع جدید برای دریافت لیست الگوهای جستجوی ترم در دیتابیس
# ==========================================================

def get_term_search_patterns(canonical_term: str) -> List[str]:
    """
    برای یک ترم استاندارد (semester_1, semester_2, summer)
    لیستی از عبارت‌هایی که باید در دیتابیس جستجو شوند را برمی‌گرداند.
    مثال: semester_1 -> ['ترم یک', 'ترم اول', 'ترم ۱', 'ترم اول', ...]
           semester_2 -> ['ترم دو', 'ترم دوم', 'ترم ۲', 'ترم چهارم', ...]
    این تابع برای سرویس‌هایی مانند basket_service که نیاز به جستجوی دروس بر اساس ترم دارند، مفید است.
    """
    if canonical_term == "semester_1":
        # ترم‌های فرد: یک، سه، پنج، هفت، نه
        return [
            "ترم یک", "ترم اول", "ترم ۱",
            "ترم سه", "ترم سوم", "ترم ۳",
            "ترم پنج", "ترم پنجم", "ترم ۵",
            "ترم هفت", "ترم هفتم", "ترم ۷",
            "ترم نه", "ترم نهم", "ترم ۹",
        ]
    elif canonical_term == "semester_2":
        # ترم‌های زوج: دو، چهار، شش، هشت، ده
        return [
            "ترم دو", "ترم دوم", "ترم ۲",
            "ترم چهار", "ترم چهارم", "ترم ۴",
            "ترم شش", "ترم ششم", "ترم ۶",
            "ترم هشت", "ترم هشتم", "ترم ۸",
            "ترم ده", "ترم دهم", "ترم ۱۰",
        ]
    elif canonical_term == "summer":
        return ["تابستان", "ترم تابستان", "نیمسال تابستان"]
    else:
        return [canonical_term]


# ==========================================================
# توابع کمکی عمومی
# ==========================================================

def normalize_text(value: str) -> str:
    """
    یکسان‌سازی متن فارسی/انگلیسی برای جستجوی بهتر.
    مثال:
    ي -> ی
    ك -> ک
    حذف نیم‌فاصله و تبدیل underline به فاصله.
    """
    if not value:
        return ""
    return (
        value.strip()
        .lower()
        .replace("ي", "ی")
        .replace("ى", "ی")
        .replace("ك", "ک")
        .replace("\u200c", " ")
        .replace("_", " ")
    )


def normalize_term(term: str) -> str:
    """
    تبدیل نام‌های مختلف ترم به کلید استاندارد:
    semester_1 | semester_2 | summer
    """
    if not term:
        return "semester_1"  # مقدار پیش‌فرض

    normalized = normalize_text(term)
    normalized = " ".join(normalized.split())
    if normalized in TERM_ALIASES:
        return TERM_ALIASES[normalized]
    valid_terms = [
        "مهر / mehr / semester_1",
        "بهمن / bahman / semester_2",
        "تابستان / summer",
    ]
    raise ValueError(
        f"ترم '{term}' معتبر نیست. مقادیر قابل قبول: {', '.join(valid_terms)}"
    )


def time_to_minutes(time_value: str) -> int:
    """تبدیل HH:MM به دقیقه برای مقایسه ساعت‌ها."""
    hour, minute = map(int, time_value.split(":"))
    return (hour * 60) + minute


def minutes_to_time(minutes: int) -> str:
    """تبدیل دقیقه به رشته HH:MM."""
    hours = minutes // 60
    mins = minutes % 60
    return f"{hours:02d}:{mins:02d}"


def parse_slot(slot: str) -> Dict[str, Any]:
    """
    تبدیل نمونه:
    07:30-09:15

    به:
    {
        "slot": "07:30-09:15",
        "start": "07:30",
        "end": "09:15",
        "start_minutes": 450,
        "end_minutes": 555
    }
    """
    start, end = slot.split("-")
    return {
        "slot": slot,
        "start": start,
        "end": end,
        "start_minutes": time_to_minutes(start),
        "end_minutes": time_to_minutes(end),
    }


def get_period_name(start_minutes: int) -> str:
    """
    دسته‌بندی بر مبنای ساعت شروع کلاس:
    morning: قبل از 12
    afternoon: از 12 تا قبل از 17
    evening: از 17 به بعد
    """
    if start_minutes < 12 * 60:
        return "morning"
    if start_minutes < 17 * 60:
        return "afternoon"
    return "evening"


def get_period_title(period: str) -> str:
    titles = {
        "morning": "صبح",
        "afternoon": "بعدازظهر",
        "evening": "عصر",
    }
    return titles.get(period, period)


def normalize_period(period: Optional[str]) -> Optional[str]:
    """
    حالت‌های قابل قبول:
    morning / صبح
    afternoon / بعدازظهر
    evening / عصر / شب
    """
    if not period:
        return None
    value = normalize_text(period)
    value = " ".join(value.split())
    aliases = {
        "morning": "morning",
        "am": "morning",
        "صبح": "morning",
        "afternoon": "afternoon",
        "pm": "afternoon",
        "بعدازظهر": "afternoon",
        "بعد از ظهر": "afternoon",
        "evening": "evening",
        "night": "evening",
        "عصر": "evening",
        "شب": "evening",
    }
    if value not in aliases:
        raise ValueError(
            "period باید یکی از مقادیر morning، afternoon، evening "
            "یا صبح، بعدازظهر، عصر باشد."
        )
    return aliases[value]


# ==========================================================
# توابع اصلی جستجو و دریافت اسلات‌ها
# ==========================================================

def get_slots(
    term: str,
    units: Optional[int] = None,
    period: Optional[str] = None,
    start_after: Optional[str] = None,
    end_before: Optional[str] = None,
) -> Dict[str, Any]:
    """
    دریافت زمان‌بندی بر اساس ترم، تعداد واحد و فیلترهای ساعت.

    نمونه:
        get_slots(term="mehr", units=2, period="morning")
        get_slots(term="بهمن", units=3)
        get_slots(term="summer", units=4, period="afternoon")
        get_slots(term="مهر", units=2, start_after="10:00")
        get_slots(term="semester_1", units=1)
        get_slots(term="ترم چهارم", units=2)  # پشتیبانی از ترم چهارم
    """
    canonical_term = normalize_term(term)
    normalized_period = normalize_period(period)

    # بررسی معتبر بودن واحد
    if units is not None and units not in SCHEDULES[canonical_term]:
        available_units = sorted(SCHEDULES[canonical_term].keys())
        raise ValueError(
            f"برای {units} واحد زمان‌بندی تعریف نشده است. "
            f"مقادیر مجاز: {', '.join(map(str, available_units))}"
        )

    start_after_minutes = time_to_minutes(start_after) if start_after else None
    end_before_minutes = time_to_minutes(end_before) if end_before else None

    units_to_search = [units] if units else sorted(SCHEDULES[canonical_term].keys())

    result: List[Dict[str, Any]] = []

    for unit_count in units_to_search:
        for slot in SCHEDULES[canonical_term][unit_count]:
            item = parse_slot(slot)
            item["units"] = unit_count
            item["period"] = get_period_name(item["start_minutes"])
            item["period_title"] = get_period_title(item["period"])

            # فیلتر صبح / بعدازظهر / عصر
            if normalized_period and item["period"] != normalized_period:
                continue

            # کلاس‌هایی که ساعت شروعشان بعد از مقدار موردنظر باشد
            if start_after_minutes is not None and item["start_minutes"] < start_after_minutes:
                continue

            # کلاس‌هایی که ساعت پایانشان قبل از مقدار موردنظر باشد
            if end_before_minutes is not None and item["end_minutes"] > end_before_minutes:
                continue

            # حذف فیلدهای دقیقه برای خروجی تمیزتر
            item.pop("start_minutes")
            item.pop("end_minutes")
            result.append(item)

    return {
        "term_input": term,
        "term": canonical_term,
        "term_title": {
            "semester_1": "نیمسال اول (مهر)",
            "semester_2": "نیمسال دوم (بهمن)",
            "summer": "نیمسال تابستان",
        }[canonical_term],
        "filters": {
            "units": units,
            "period": normalized_period,
            "start_after": start_after,
            "end_before": end_before,
        },
        "count": len(result),
        "slots": result,
    }


def get_full_schedule(term: str) -> Dict[str, Any]:
    """
    دریافت کل برنامه یک ترم بدون فیلتر.
    """
    canonical_term = normalize_term(term)
    result: Dict[str, Any] = {
        "term_input": term,
        "term": canonical_term,
        "term_title": {
            "semester_1": "نیمسال اول (مهر)",
            "semester_2": "نیمسال دوم (بهمن)",
            "summer": "نیمسال تابستان",
        }[canonical_term],
        "schedule": {},
    }
    for units, slots in SCHEDULES[canonical_term].items():
        result["schedule"][f"{units}_units"] = [
            {
                "slot": slot,
                "start": parse_slot(slot)["start"],
                "end": parse_slot(slot)["end"],
                "period": get_period_name(parse_slot(slot)["start_minutes"]),
            }
            for slot in slots
        ]
    return result


def get_all_schedules() -> Dict[str, Any]:
    """دریافت برنامه کامل تمام ترم‌ها."""
    return {
        "semester_1": get_full_schedule("مهر"),
        "semester_2": get_full_schedule("بهمن"),
        "summer": get_full_schedule("تابستان"),
    }


# ==========================================================
# توابع اضافی برای اعتبارسنجی و ابزارهای مفید
# ==========================================================

def is_valid_slot(slot: str, term: str, units: int) -> bool:
    """
    بررسی اینکه آیا یک اسلات معین برای ترم و تعداد واحد داده شده معتبر است یا خیر.
    """
    try:
        slots = get_slots(term=term, units=units)
        existing_slots = [s["slot"] for s in slots["slots"]]
        return slot in existing_slots
    except ValueError:
        return False


def get_slot_by_time(start: str, end: str, term: str, units: int) -> Optional[Dict[str, Any]]:
    """
    دریافت اطلاعات یک اسلات بر اساس زمان شروع و پایان، ترم و تعداد واحد.
    اگر اسلات معتبر باشد، اطلاعات آن را برمی‌گرداند، در غیر این صورت None.
    """
    try:
        slots = get_slots(term=term, units=units)
        for s in slots["slots"]:
            if s["start"] == start and s["end"] == end:
                return s
        return None
    except ValueError:
        return None


def find_closest_slot(
    start: str,
    term: str,
    units: int,
    tolerance_minutes: int = 30,
) -> Optional[Dict[str, Any]]:
    """
    نزدیک‌ترین اسلات معتبر به یک زمان شروع مشخص را پیدا می‌کند.
    tolerance_minutes حداکثر تفاوت مجاز بر حسب دقیقه است.
    """
    try:
        slots = get_slots(term=term, units=units)
        target_min = time_to_minutes(start)
        best = None
        best_diff = float("inf")
        for s in slots["slots"]:
            diff = abs(time_to_minutes(s["start"]) - target_min)
            if diff < best_diff:
                best_diff = diff
                best = s
        if best_diff <= tolerance_minutes:
            return best
        return None
    except ValueError:
        return None


# ==========================================================
# FastAPI Router
# ==========================================================

router = APIRouter(
    prefix="/slot-times",
    tags=["Slot Times / زمان‌بندی کلاس‌ها"],
)


@router.get("/terms")
def available_terms() -> Dict[str, Any]:
    """نمایش ترم‌های قابل قبول و نام‌های جایگزین آن‌ها."""
    # دریافت واحدهای مجاز از اولین ترم (همه ترم‌ها واحدهای مشابه دارند)
    first_term = next(iter(SCHEDULES.values()))
    available_units = sorted(first_term.keys())

    return {
        "terms": [
            {
                "key": "semester_1",
                "title": "نیمسال اول (مهر)",
                "aliases": ["مهر", "mehr", "semester_1", "نیمسال اول", "ترم یک", "ترم اول", "ترم سه", "ترم سوم", "ترم پنجم", "ترم هفتم"],
            },
            {
                "key": "semester_2",
                "title": "نیمسال دوم (بهمن)",
                "aliases": ["بهمن", "bahman", "semester_2", "نیمسال دوم", "ترم دو", "ترم دوم", "ترم چهارم", "ترم ششم", "ترم هشتم"],
            },
            {
                "key": "summer",
                "title": "نیمسال تابستان",
                "aliases": ["تابستان", "summer", "نیمسال تابستان", "ترم تابستان"],
            },
        ],
        "available_units": available_units,
        "available_periods": {
            "morning": "صبح",
            "afternoon": "بعدازظهر",
            "evening": "عصر",
        },
    }


@router.get("/schedule")
def api_get_full_schedule(
    term: str = Query(..., description="مثال: مهر، mehr، بهمن، bahman، تابستان، summer، ترم یک، ترم دو، ترم چهارم، ..."),
) -> Dict[str, Any]:
    """
    کل برنامه یک ترم.

    نمونه درخواست:
    /slot-times/schedule?term=mehr
    /slot-times/schedule?term=بهمن
    /slot-times/schedule?term=ترم یک
    /slot-times/schedule?term=ترم چهارم
    """
    try:
        return get_full_schedule(term)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error))


@router.get("/search")
def api_search_slots(
    term: str = Query(..., description="مثال: مهر، mehr، بهمن، bahman، تابستان، summer، ترم یک، ترم دو، ترم چهارم، ..."),
    units: Optional[int] = Query(None, description="تعداد واحد: 1، 2، 3 یا 4"),
    period: Optional[str] = Query(None, description="morning / afternoon / evening یا صبح / بعدازظهر / عصر"),
    start_after: Optional[str] = Query(None, description="مثال: 10:00"),
    end_before: Optional[str] = Query(None, description="مثال: 14:00"),
) -> Dict[str, Any]:
    """
    جستجوی زمان‌بندی کلاس.

    مثال‌ها:
    /slot-times/search?term=mehr&units=2&period=morning
    /slot-times/search?term=مهر&units=3
    /slot-times/search?term=bahman&units=4&period=afternoon
    /slot-times/search?term=summer&units=2&start_after=10:00
    /slot-times/search?term=semester_1&units=1
    /slot-times/search?term=ترم یک&units=2
    /slot-times/search?term=ترم چهارم&units=2
    """
    try:
        return get_slots(
            term=term,
            units=units,
            period=period,
            start_after=start_after,
            end_before=end_before,
        )
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error))


@router.get("/validate")
def validate_slot(
    slot: str = Query(..., description="مثال: 07:30-09:15"),
    term: str = Query(..., description="ترم مورد نظر"),
    units: int = Query(..., description="تعداد واحد: 1، 2، 3 یا 4"),
) -> Dict[str, Any]:
    """
    اعتبارسنجی یک اسلات مشخص برای ترم و واحد داده شده.
    """
    try:
        is_valid = is_valid_slot(slot, term, units)
        return {
            "slot": slot,
            "term": term,
            "units": units,
            "is_valid": is_valid,
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/closest")
def find_closest(
    start: str = Query(..., description="زمان شروع مدنظر، مثال: 10:00"),
    term: str = Query(..., description="ترم مورد نظر"),
    units: int = Query(..., description="تعداد واحد: 1، 2، 3 یا 4"),
    tolerance: int = Query(30, description="حداکثر تفاوت مجاز بر حسب دقیقه"),
) -> Dict[str, Any]:
    """
    پیدا کردن نزدیک‌ترین اسلات معتبر به یک زمان شروع مشخص.
    """
    try:
        closest = find_closest_slot(start, term, units, tolerance)
        if closest:
            return {
                "requested_start": start,
                "term": term,
                "units": units,
                "closest_slot": closest,
                "found": True,
            }
        else:
            return {
                "requested_start": start,
                "term": term,
                "units": units,
                "found": False,
                "message": f"هیچ اسلاتی در محدوده {tolerance} دقیقه‌ای یافت نشد.",
            }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))