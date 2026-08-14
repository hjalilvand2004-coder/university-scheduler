# backend/check_data.py
import sys
import os
import re

# اضافه کردن مسیر پروژه به PYTHONPATH
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# ===== وارد کردن تمام مدل‌های موردنیاز (برای حل وابستگی‌ها) =====
from app.models.instructor import Instructor
from app.models.teaching_preference import TeachingPreference
from app.models.time_preference import TimePreference
from app.models.basket_item import BasketItem
from app.models.workflow import ScheduleWorkflow  # ← این برای رفع خطای relationship ضروری است

# ============================================
# توابع نرمالایز (دقیقاً مشابه کد اصلی)
# ============================================
def normalize_code(code: str) -> str:
    if not code:
        return code
    normalized = re.sub(r'[^A-Za-z0-9_]', '', code)
    return normalized.upper()

def normalize_instructor_code(code: str) -> str:
    if not code:
        return code
    cleaned = re.sub(r'\s+', '', code)
    if cleaned.isdigit():
        return str(int(cleaned))
    return cleaned

# ============================================
# اتصال به دیتابیس (با استفاده از مسیر صحیح)
# ============================================
DB_PATH = "university_scheduler.db"  # در پوشه backend
# اگر فایل در جای دیگری است، مسیر کامل را بدهید:
# DB_PATH = "sqlite:///J:/samplaeProjectPython/university-scheduler/backend/university_scheduler.db"
engine = create_engine(f'sqlite:///{DB_PATH}', echo=False)
Session = sessionmaker(bind=engine)
db = Session()

print("=" * 80)
print("🔍 بررسی داده‌های تطابق در دیتابیس")
print("=" * 80)

# ============================================
# 1. بررسی اساتید (Instructor)
# ============================================
print("\n📌 1. نمونه کدهای اساتید موجود (Instructor.code):")
instructors = db.query(Instructor).limit(10).all()
if not instructors:
    print("   ⚠️ هیچ استادی در دیتابیس یافت نشد!")
else:
    for inst in instructors:
        raw = inst.code
        norm = normalize_instructor_code(raw)
        print(f"   Raw: '{raw}'  ->  Normalized: '{norm}'  |  Name: {inst.name}")

# ============================================
# 2. بررسی مطلوبیت تدریس (TeachingPreference)
# ============================================
print("\n📌 2. نمونه مطلوبیت‌های تدریس (TeachingPreference):")
teaching_prefs = db.query(TeachingPreference).filter(
    TeachingPreference.unique_course_code.isnot(None),
    TeachingPreference.instructor_code.isnot(None)
).limit(10).all()

if not teaching_prefs:
    print("   ⚠️ هیچ رکورد TeachingPreference با کد درس و استاد غیرتهی یافت نشد!")
else:
    for tp in teaching_prefs:
        raw_course = tp.unique_course_code
        raw_instructor = tp.instructor_code
        norm_course = normalize_code(raw_course)
        norm_instructor = normalize_instructor_code(raw_instructor)
        print(f"   درس: Raw: '{raw_course}' -> Norm: '{norm_course}'")
        print(f"   استاد: Raw: '{raw_instructor}' -> Norm: '{norm_instructor}'")
        print(f"   نام استاد در رکورد: {tp.instructor_name}")
        print("   ---")

# ============================================
# 3. بررسی مطلوبیت زمان (TimePreference)
# ============================================
print("\n📌 3. نمونه مطلوبیت‌های زمان (TimePreference):")
time_prefs = db.query(TimePreference).filter(
    TimePreference.instructor_code.isnot(None)
).limit(10).all()

if not time_prefs:
    print("   ⚠️ هیچ رکورد TimePreference با کد استاد غیرتهی یافت نشد!")
else:
    for tp in time_prefs:
        raw_instructor = tp.instructor_code
        norm_instructor = normalize_instructor_code(raw_instructor)
        print(f"   استاد: Raw: '{raw_instructor}' -> Norm: '{norm_instructor}'")
        print(f"   روز: {tp.day}, شروع: {tp.start_time}, پایان: {tp.end_time}")
        print("   ---")

# ============================================
# 4. بررسی سبد دروس (BasketItem)
# ============================================
print("\n📌 4. نمونه کدهای یکتا در سبد (BasketItem.unique_code):")
basket_items = db.query(BasketItem).filter(
    BasketItem.unique_code.isnot(None)
).limit(10).all()

if not basket_items:
    print("   ⚠️ هیچ رکورد BasketItem با کد یکتا یافت نشد!")
    print("   (توجه: اگر سبد هنوز ذخیره نشده، این بخش خالی است)")
else:
    for item in basket_items:
        raw = item.unique_code
        norm = normalize_code(raw)
        print(f"   Raw: '{raw}'  ->  Normalized: '{norm}'  |  درس: {item.course_name}")

# ============================================
# 5. بررسی تطابق‌ها (مقایسه)
# ============================================
print("\n" + "=" * 80)
print("🔗 5. تحلیل تطابق‌ها:")
print("=" * 80)

# مجموعه‌ها برای مقایسه (با نرمالایز کردن)
instructor_set = set(normalize_instructor_code(i.code) for i in db.query(Instructor).all() if i.code)
teaching_instructor_set = set(normalize_instructor_code(tp.instructor_code) for tp in db.query(TeachingPreference).filter(TeachingPreference.instructor_code.isnot(None)).all())
time_instructor_set = set(normalize_instructor_code(tp.instructor_code) for tp in db.query(TimePreference).filter(TimePreference.instructor_code.isnot(None)).all())

# کدهای درس
basket_codes_set = set(normalize_code(b.unique_code) for b in db.query(BasketItem).filter(BasketItem.unique_code.isnot(None)).all())
teaching_course_set = set(normalize_code(tp.unique_course_code) for tp in db.query(TeachingPreference).filter(TeachingPreference.unique_course_code.isnot(None)).all())

print(f"👨‍🏫 تعداد کدهای استاد موجود در دیتابیس: {len(instructor_set)}")
print(f"📖 تعداد کدهای استاد در TeachingPreference: {len(teaching_instructor_set)}")
print(f"⏰ تعداد کدهای استاد در TimePreference: {len(time_instructor_set)}")

# بررسی تطابق استاد
common_instructors = instructor_set & teaching_instructor_set
print(f"\n✅ تعداد کدهای استاد مشترک بین Instructor و TeachingPreference: {len(common_instructors)}")
if len(common_instructors) == 0 and teaching_instructor_set:
    print("   ❌ مشکل: هیچ کد استادی در TeachingPreference با Instructor تطابق ندارد!")
    print(f"   نمونه کدهای استاد در TeachingPreference: {list(teaching_instructor_set)[:5]}")
    print(f"   نمونه کدهای استاد در Instructor: {list(instructor_set)[:5]}")

common_time_instructors = instructor_set & time_instructor_set
print(f"\n✅ تعداد کدهای استاد مشترک بین Instructor و TimePreference: {len(common_time_instructors)}")
if len(common_time_instructors) == 0 and time_instructor_set:
    print("   ❌ مشکل: هیچ کد استادی در TimePreference با Instructor تطابق ندارد!")
    print(f"   نمونه کدهای استاد در TimePreference: {list(time_instructor_set)[:5]}")

# بررسی تطابق درس
print(f"\n📚 تعداد کدهای درس در سبد (BasketItem): {len(basket_codes_set)}")
print(f"📚 تعداد کدهای درس در TeachingPreference: {len(teaching_course_set)}")
common_courses = basket_codes_set & teaching_course_set
print(f"✅ تعداد کدهای درس مشترک بین سبد و TeachingPreference: {len(common_courses)}")
if len(common_courses) == 0 and teaching_course_set and basket_codes_set:
    print("   ❌ مشکل: هیچ کد درسی در TeachingPreference با سبد تطابق ندارد!")
    print(f"   نمونه کدهای درس در سبد: {list(basket_codes_set)[:5]}")
    print(f"   نمونه کدهای درس در TeachingPreference: {list(teaching_course_set)[:5]}")

db.close()
print("\n✅ بررسی به پایان رسید.")