from fastapi import APIRouter, HTTPException, UploadFile, File, Depends
from sqlalchemy.orm import Session
import pandas as pd
from io import BytesIO
import re
import logging

from app.core.database import get_db
from app.models.term_course import TermCourse
from app.services.schedule.slot_times import normalize_term

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/term-courses", tags=["Term Courses"])

# ===== توابع کمکی =====
def normalize_column_name(col: str) -> str:
    if not isinstance(col, str):
        return col
    col = col.strip()
    col = re.sub(r'\s+', ' ', col)
    return col

def clean_record(record: dict) -> dict:
    cleaned = {}
    for key, value in record.items():
        if pd.isna(value):
            cleaned[key] = None
        elif isinstance(value, float) and value.is_integer():
            cleaned[key] = int(value)
        elif isinstance(value, str):
            cleaned[key] = value.strip()
        else:
            cleaned[key] = value
    return cleaned

def normalize_term_field(term_value) -> str:
    if not term_value:
        return term_value
    try:
        return normalize_term(str(term_value))
    except ValueError as e:
        logger.warning(f"ترم '{term_value}' نامعتبر است: {e}")
        return term_value

def term_course_to_dict(term_course: TermCourse) -> dict:
    """
    تبدیل مدل TermCourse به دیکشنری با تمام فیلدها
    """
    return {
        "id": term_course.id,
        "level": term_course.level,
        "term": term_course.term,
        "row_number": term_course.row_number,
        "course_name": term_course.course_name,
        "units": term_course.units,
        "capacity": term_course.capacity,           # ← فیلد جدید
        "course_type": term_course.course_type,
        "approximate_term": term_course.approximate_term,
        "description": term_course.description,
        "prerequisite_row_codes": term_course.prerequisite_row_codes,
        "corequisite_row_codes": term_course.corequisite_row_codes,
        "unique_course_code": term_course.unique_course_code,
        "unique_course_name": term_course.unique_course_name,
        "year_identified": term_course.year_identified,
    }

# ============================================
# CRUD
# ============================================

@router.get("/")
async def get_all(db: Session = Depends(get_db)):
    courses = db.query(TermCourse).all()
    result = [term_course_to_dict(course) for course in courses]
    if result:
        logger.info(f"نمونه خروجی term-courses (اولین رکورد): {result[0]}")
    return result

@router.post("/")
async def create(data: dict, db: Session = Depends(get_db)):
    if "term" in data and data["term"]:
        data["term"] = normalize_term_field(data["term"])
    new = TermCourse(**data)
    db.add(new)
    db.commit()
    db.refresh(new)
    return term_course_to_dict(new)

@router.put("/{id}")
async def update(id: int, data: dict, db: Session = Depends(get_db)):
    item = db.query(TermCourse).filter(TermCourse.id == id).first()
    if not item:
        raise HTTPException(status_code=404, detail="رکورد پیدا نشد")
    if "term" in data and data["term"]:
        data["term"] = normalize_term_field(data["term"])
    for key, value in data.items():
        setattr(item, key, value)
    db.commit()
    db.refresh(item)
    return term_course_to_dict(item)

@router.delete("/{id}")
async def delete(id: int, db: Session = Depends(get_db)):
    item = db.query(TermCourse).filter(TermCourse.id == id).first()
    if not item:
        raise HTTPException(status_code=404, detail="رکورد پیدا نشد")
    db.delete(item)
    db.commit()
    return {"message": "رکورد با موفقیت حذف شد"}

# ============================================
# بارگذاری اکسل (با اضافه کردن ظرفیت)
# ============================================

@router.post("/upload")
async def upload_excel(file: UploadFile = File(...), db: Session = Depends(get_db)):
    try:
        contents = await file.read()
        df = pd.read_excel(BytesIO(contents))
        df.columns = [normalize_column_name(col) for col in df.columns]
        logger.info(f"ستون‌های شناسایی‌شده در فایل دروس ترمیک: {list(df.columns)}")
        df = df.where(pd.notnull(df), None)
        records = df.to_dict(orient="records")

        # نگاشت ستون‌های فایل به فیلدهای مدل (با اضافه شدن ظرفیت)
        column_map = {
            "مقطع ارائه": "level",
            "ترم": "term",
            "ردیف": "row_number",
            "نام درس": "course_name",
            "واحد": "units",
            "ظرفیت درس": "capacity",          # ← فیلد جدید
            "نوع درس": "course_type",
            "ترم تقریبی": "approximate_term",
            "توضیح": "description",
            "کد ردیف پیش نیازش": "prerequisite_row_codes",
            "کد ردیف همنیازش": "corequisite_row_codes",
            "کد درس یکتا": "unique_course_code",
            "نام درس یکتا": "unique_course_name",
            "سال شناسایی": "year_identified"
        }

        required_cols = ["مقطع ارائه", "ترم", "نام درس"]
        missing_cols = [col for col in required_cols if col not in df.columns]
        if missing_cols:
            raise HTTPException(
                status_code=400,
                detail=f"ستون‌های ضروری وجود ندارند: {', '.join(missing_cols)}"
            )

        added = 0
        errors = []

        for idx, rec in enumerate(records, start=1):
            try:
                rec = clean_record(rec)
                data = {}
                for excel_col, model_field in column_map.items():
                    data[model_field] = rec.get(excel_col)

                if not data.get("level") or not data.get("term") or not data.get("course_name"):
                    errors.append(f"ردیف {idx}: مقطع، ترم یا نام درس خالی است")
                    continue

                if data.get("term"):
                    data["term"] = normalize_term_field(data["term"])

                # اعتبارسنجی واحد
                if data.get("units") is not None:
                    try:
                        data["units"] = int(data["units"])
                        if data["units"] not in [1, 2, 3, 4]:
                            errors.append(f"ردیف {idx}: واحد باید 1، 2، 3 یا 4 باشد (مقدار: {data['units']})")
                            continue
                    except:
                        errors.append(f"ردیف {idx}: واحد باید عدد باشد")
                        continue
                else:
                    data["units"] = 0

                # اعتبارسنجی ظرفیت (اختیاری)
                if data.get("capacity") is not None:
                    try:
                        data["capacity"] = int(data["capacity"])
                        if data["capacity"] < 0:
                            errors.append(f"ردیف {idx}: ظرفیت نباید منفی باشد")
                            continue
                    except:
                        errors.append(f"ردیف {idx}: ظرفیت باید عدد باشد")
                        continue
                else:
                    data["capacity"] = 0

                if data.get("approximate_term") is not None:
                    try:
                        data["approximate_term"] = int(data["approximate_term"])
                    except:
                        errors.append(f"ردیف {idx}: ترم تقریبی باید عدد باشد")
                        continue

                db.add(TermCourse(**data))
                added += 1
            except Exception as e:
                errors.append(f"ردیف {idx}: {str(e)}")
                logger.error(f"خطا در ردیف {idx}: {str(e)}")

        db.commit()

        if added == 0 and errors:
            raise HTTPException(
                status_code=400,
                detail=f"هیچ رکوردی بارگذاری نشد. خطاها: {', '.join(errors[:5])}"
            )

        return {
            "message": f"بارگذاری با موفقیت انجام شد. {added} رکورد اضافه شد.",
            "count": added,
            "errors": errors if errors else []
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"خطا در بارگذاری دروس ترمیک: {str(e)}")
        raise HTTPException(status_code=400, detail=f"خطا در بارگذاری فایل: {str(e)}")