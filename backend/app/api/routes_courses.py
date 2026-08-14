from fastapi import APIRouter, HTTPException, UploadFile, File, Depends, Query
from sqlalchemy.orm import Session
import pandas as pd
from io import BytesIO
from typing import Optional
import logging

from app.core.database import get_db
from app.models import UniqueCourse, OfferedCourse
from app.schemas.course import Semester
from app.services.scoring_service import rank_courses
from app.data.sample_data import sample_courses, sample_instructors

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/courses", tags=["Courses"])


# ============================================
# APIهای دروس یکتا (با دیتابیس)
# ============================================

@router.get("/unique")
async def get_unique_courses(db: Session = Depends(get_db)):
    """دریافت لیست تمام دروس یکتا از دیتابیس"""
    return db.query(UniqueCourse).all()


@router.post("/unique")
async def create_unique_course(course: dict, db: Session = Depends(get_db)):
    """ایجاد درس یکتا جدید در دیتابیس"""
    new_course = UniqueCourse(
        code=course.get("code"),
        title=course.get("title"),
        status=course.get("status", "active"),
        group=course.get("group", "continuous_before_1403"),
        estimated_capacity=course.get("estimated_capacity", 0),
    )
    db.add(new_course)
    db.commit()
    db.refresh(new_course)
    return new_course


@router.put("/unique/{course_id}")
async def update_unique_course(course_id: int, course: dict, db: Session = Depends(get_db)):
    """ویرایش درس یکتا در دیتابیس"""
    db_course = db.query(UniqueCourse).filter(UniqueCourse.id == course_id).first()
    if not db_course:
        raise HTTPException(status_code=404, detail="درس پیدا نشد")

    db_course.code = course.get("code", db_course.code)
    db_course.title = course.get("title", db_course.title)
    db_course.status = course.get("status", db_course.status)
    db_course.group = course.get("group", db_course.group)
    db_course.estimated_capacity = course.get("estimated_capacity", db_course.estimated_capacity)

    db.commit()
    db.refresh(db_course)
    return db_course


@router.delete("/unique/{course_id}")
async def delete_unique_course(course_id: int, db: Session = Depends(get_db)):
    """حذف درس یکتا از دیتابیس"""
    db_course = db.query(UniqueCourse).filter(UniqueCourse.id == course_id).first()
    if not db_course:
        raise HTTPException(status_code=404, detail="درس پیدا نشد")

    db.delete(db_course)
    db.commit()
    return {"message": "درس با موفقیت حذف شد"}


# ============================================
# APIهای دروس ارائه (با دیتابیس)
# ============================================

@router.get("/offered")
async def get_offered_courses(db: Session = Depends(get_db)):
    """دریافت لیست تمام دروس ارائه از دیتابیس"""
    return db.query(OfferedCourse).all()


@router.post("/offered")
async def create_offered_course(course: dict, db: Session = Depends(get_db)):
    """ایجاد درس ارائه جدید در دیتابیس"""
    new_course = OfferedCourse(
        row_number=course.get("row_number", 0),
        offered_title=course.get("offered_title"),
        unique_code=course.get("unique_code"),
        unique_title=course.get("unique_title"),
        theoretical_hours=course.get("theoretical_hours", 0),
        practical_hours=course.get("practical_hours", 0),
        prerequisite=course.get("prerequisite", ""),
        corequisite=course.get("corequisite", ""),
        year=course.get("year", ""),
        course_type=course.get("course_type", "theory"),
        is_active=course.get("is_active", True),
        type_course=course.get("type_course", ""),
    )
    db.add(new_course)
    db.commit()
    db.refresh(new_course)
    return new_course


@router.put("/offered/{course_id}")
async def update_offered_course(course_id: int, course: dict, db: Session = Depends(get_db)):
    """ویرایش درس ارائه در دیتابیس"""
    db_course = db.query(OfferedCourse).filter(OfferedCourse.id == course_id).first()
    if not db_course:
        raise HTTPException(status_code=404, detail="درس پیدا نشد")

    for key, value in course.items():
        if hasattr(db_course, key):
            setattr(db_course, key, value)

    db.commit()
    db.refresh(db_course)
    return db_course


@router.delete("/offered/{course_id}")
async def delete_offered_course(course_id: int, db: Session = Depends(get_db)):
    """حذف درس ارائه از دیتابیس"""
    db_course = db.query(OfferedCourse).filter(OfferedCourse.id == course_id).first()
    if not db_course:
        raise HTTPException(status_code=404, detail="درس پیدا نشد")

    db.delete(db_course)
    db.commit()
    return {"message": "درس با موفقیت حذف شد"}


# ============================================
# بارگذاری اکسل (با دیتابیس) - بهبودیافته
# ============================================

def _safe_str(value):
    """تبدیل ایمن به رشته و حذف فاصله‌های اضافی"""
    if value is None:
        return ""
    return str(value).strip()


def _safe_int(value, default=0):
    """تبدیل ایمن به عدد صحیح"""
    if value is None:
        return default
    try:
        return int(float(value))
    except (ValueError, TypeError):
        return default


@router.post("/upload/unique")
async def upload_unique_excel(file: UploadFile = File(...), db: Session = Depends(get_db)):
    """بارگذاری فایل اکسل برای دروس یکتا و ذخیره در دیتابیس"""
    try:
        # بررسی اینکه فایل خالی نباشد
        contents = await file.read()
        if not contents:
            raise HTTPException(status_code=400, detail="فایل خالی است")

        # خواندن فایل اکسل
        try:
            df = pd.read_excel(BytesIO(contents))
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"خطا در خواندن فایل اکسل: {str(e)}")

        # اگر دیتافریم خالی است
        if df.empty:
            raise HTTPException(status_code=400, detail="فایل اکسل هیچ داده‌ای ندارد")

        # پاک کردن رکوردهای خالی
        df = df.where(pd.notnull(df), None)
        records = df.to_dict(orient="records")
        added_count = 0
        errors = []

        for idx, record in enumerate(records):
            try:
                # خواندن ستون‌ها با تطابق نام‌های مختلف
                code = _safe_str(record.get("کد درس یکتا") or record.get("کد") or record.get("code"))
                title = _safe_str(record.get("عنوان درس یکتا") or record.get("عنوان") or record.get("title"))
                status = _safe_str(record.get("وضعیت") or record.get("status") or "active")
                group = _safe_str(record.get("گروه") or record.get("group") or "continuous_before_1403")
                estimated_capacity = _safe_int(record.get("برآورد ظرفیت") or record.get("estimated_capacity") or 0)

                if not code or not title:
                    errors.append(f"ردیف {idx+2}: کد یا عنوان درس خالی است")
                    continue

                # بررسی تکراری نبودن کد
                existing = db.query(UniqueCourse).filter(UniqueCourse.code == code).first()
                if existing:
                    errors.append(f"ردیف {idx+2}: کد '{code}' قبلاً در دیتابیس وجود دارد")
                    continue

                new_course = UniqueCourse(
                    code=code,
                    title=title,
                    status=status,
                    group=group,
                    estimated_capacity=estimated_capacity,
                )
                db.add(new_course)
                added_count += 1
            except Exception as e:
                errors.append(f"ردیف {idx+2}: خطا - {str(e)}")

        # اگر هیچ رکوردی اضافه نشد و خطا وجود دارد
        if added_count == 0 and errors:
            raise HTTPException(status_code=400, detail=f"هیچ رکوردی اضافه نشد. خطاها: {'; '.join(errors[:5])}")

        # اگر همه رکوردها خطا داشتند
        if errors and added_count == 0:
            raise HTTPException(status_code=400, detail=f"همه رکوردها خطا داشتند: {'; '.join(errors[:5])}")

        db.commit()
        return {
            "message": "بارگذاری با موفقیت انجام شد",
            "count": added_count,
            "errors": errors[:10] if errors else []  # فقط ۱۰ خطای اول
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"خطای غیرمنتظره در بارگذاری دروس یکتا: {e}")
        raise HTTPException(status_code=400, detail=f"خطا در بارگذاری فایل: {str(e)}")


@router.post("/upload/offered")
async def upload_offered_excel(file: UploadFile = File(...), db: Session = Depends(get_db)):
    """بارگذاری فایل اکسل برای دروس ارائه و ذخیره در دیتابیس"""
    try:
        contents = await file.read()
        if not contents:
            raise HTTPException(status_code=400, detail="فایل خالی است")

        try:
            df = pd.read_excel(BytesIO(contents))
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"خطا در خواندن فایل اکسل: {str(e)}")

        if df.empty:
            raise HTTPException(status_code=400, detail="فایل اکسل هیچ داده‌ای ندارد")

        df = df.where(pd.notnull(df), None)
        records = df.to_dict(orient="records")
        added_count = 0
        errors = []

        for idx, record in enumerate(records):
            try:
                row_number = _safe_int(record.get("row_number") or record.get("شماره ردیف") or 0)
                offered_title = _safe_str(record.get("عنوان درس در مقطع ارایه") or record.get("offered_title"))
                unique_code = _safe_str(record.get("کد یکتا") or record.get("unique_code"))
                unique_title = _safe_str(record.get("عنوان درس یکتا") or record.get("unique_title"))
                theoretical_hours = _safe_int(record.get("نظری") or record.get("theoretical_hours") or 0)
                practical_hours = _safe_int(record.get("عملی") or record.get("practical_hours") or 0)
                prerequisite = _safe_str(record.get("prerequisite") or record.get("پیش‌نیاز") or "")
                corequisite = _safe_str(record.get("corequisite") or record.get("هم‌نیاز") or "")
                year = _safe_str(record.get("year") or record.get("سال") or "")
                course_type = _safe_str(record.get("type_coures") or record.get("course_type") or "theory")
                is_active = record.get("is_active") or record.get("فعال") or True
                type_course = _safe_str(record.get("نوع درس3") or record.get("type_course") or "")

                if not offered_title or not unique_code:
                    errors.append(f"ردیف {idx+2}: عنوان درس یا کد یکتا خالی است")
                    continue

                # بررسی تکراری نبودن unique_code با داده‌های موجود (اختیاری)
                # می‌توانید بر اساس نیاز این بخش را اضافه کنید

                new_course = OfferedCourse(
                    row_number=row_number,
                    offered_title=offered_title,
                    unique_code=unique_code,
                    unique_title=unique_title,
                    theoretical_hours=theoretical_hours,
                    practical_hours=practical_hours,
                    prerequisite=prerequisite,
                    corequisite=corequisite,
                    year=year,
                    course_type=course_type,
                    is_active=is_active,
                    type_course=type_course,
                )
                db.add(new_course)
                added_count += 1
            except Exception as e:
                errors.append(f"ردیف {idx+2}: خطا - {str(e)}")

        if added_count == 0 and errors:
            raise HTTPException(status_code=400, detail=f"هیچ رکوردی اضافه نشد. خطاها: {'; '.join(errors[:5])}")

        db.commit()
        return {
            "message": "بارگذاری با موفقیت انجام شد",
            "count": added_count,
            "errors": errors[:10] if errors else []
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"خطای غیرمنتظره در بارگذاری دروس ارائه: {e}")
        raise HTTPException(status_code=400, detail=f"خطا در بارگذاری فایل: {str(e)}")


# ============================================
# سایر APIها
# ============================================

@router.get("/instructors")
async def get_instructors():
    """نمونه داده‌های اساتید (برای تست)"""
    return sample_instructors()


@router.get("/teaching-history")
async def get_teaching_history():
    """نمونه تاریخچه تدریس (برای تست)"""
    return [
        {"professor": "دکتر احمدی", "course": "مبانی کامپیوتر", "semester": "مهر", "year": "1402", "students": 42},
        {"professor": "دکتر احمدی", "course": "ساختمان داده", "semester": "مهر", "year": "1402", "students": 35},
        {"professor": "دکتر رضایی", "course": "ریاضی عمومی ۱", "semester": "مهر", "year": "1402", "students": 48},
        {"professor": "دکتر رضایی", "course": "سیستم‌عامل", "semester": "بهمن", "year": "1402", "students": 30},
    ]


@router.get("/ranked")
async def get_ranked_courses(semester: Semester = Semester.MEHR):
    """دریافت دروس رتبه‌بندی‌شده بر اساس نیمسال (برای تست)"""
    courses = sample_courses()
    return {"semester": semester, "items": rank_courses(courses, semester)}