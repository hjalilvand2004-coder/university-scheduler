from fastapi import APIRouter, HTTPException, UploadFile, File, Depends
from sqlalchemy.orm import Session
import pandas as pd
from io import BytesIO
import re
import logging

from app.core.database import get_db
from app.models.schedule_history import ScheduleHistory

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/schedule-history", tags=["Schedule History"])

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

# ============================================
# CRUD
# ============================================

@router.get("/")
async def get_all(db: Session = Depends(get_db)):
    return db.query(ScheduleHistory).all()

@router.post("/")
async def create(data: dict, db: Session = Depends(get_db)):
    new = ScheduleHistory(**data)
    db.add(new)
    db.commit()
    db.refresh(new)
    return new

@router.put("/{id}")
async def update(id: int, data: dict, db: Session = Depends(get_db)):
    item = db.query(ScheduleHistory).filter(ScheduleHistory.id == id).first()
    if not item:
        raise HTTPException(status_code=404, detail="رکورد پیدا نشد")
    for key, value in data.items():
        setattr(item, key, value)
    db.commit()
    db.refresh(item)
    return item

@router.delete("/{id}")
async def delete(id: int, db: Session = Depends(get_db)):
    item = db.query(ScheduleHistory).filter(ScheduleHistory.id == id).first()
    if not item:
        raise HTTPException(status_code=404, detail="رکورد پیدا نشد")
    db.delete(item)
    db.commit()
    return {"message": "رکورد با موفقیت حذف شد"}

# ============================================
# بارگذاری اکسل
# ============================================

@router.post("/upload")
async def upload_excel(file: UploadFile = File(...), db: Session = Depends(get_db)):
    try:
        contents = await file.read()
        df = pd.read_excel(BytesIO(contents))
        df.columns = [normalize_column_name(col) for col in df.columns]
        logger.info(f"ستون‌های شناسایی‌شده در فایل سوابق: {list(df.columns)}")
        df = df.where(pd.notnull(df), None)
        records = df.to_dict(orient="records")

        # نگاشت ستون‌های فایل به فیلدهای مدل
        column_map = {
            "نیمسال ارائه": "semester",
            "نام درس": "course_name",
            "کد دانشکده استخراج‌شده": "faculty_code",
            "نام دانشکده تمیز": "faculty_name_clean",
            "کد گروه آموزشی": "department_code",
            "نام گروه آموزشی تمیز": "department_name_clean",
            "کد استاد مرجع": "instructor_code",
            "نام استاد تمیز": "instructor_name_clean",
            "حداکثر ظرفیت": "max_capacity",
            "مقطع ارائه درس": "level",
            "نوع درس": "course_type",
            "روز کلاس": "day",
            "ساعت شروع کلاس": "start_time",
            "ساعت پایان کلاس": "end_time",
            "تاریخ امتحان": "exam_date",
            "ساعت شروع امتحان": "exam_start_time",
            "ساعت پایان امتحان": "exam_end_time",
            "عنوان درس مرجع": "ref_course_title",
            "کد درس یکتا مرجع": "ref_unique_course_code",
            "عنوان درس یکتا مرجع": "ref_unique_course_title",
            "کد کلاس استخراج‌شده": "class_code",
            "نام کلاس": "class_name"
        }

        required_cols = ["نیمسال ارائه", "نام درس"]  # حداقل ستون‌های ضروری
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

                if not data.get("semester") or not data.get("course_name"):
                    errors.append(f"ردیف {idx}: نیمسال یا نام درس خالی است")
                    continue

                # تبدیل ظرفیت به عدد صحیح
                if data.get("max_capacity") is not None:
                    try:
                        data["max_capacity"] = int(data["max_capacity"])
                    except:
                        errors.append(f"ردیف {idx}: ظرفیت باید عدد باشد")
                        continue

                db.add(ScheduleHistory(**data))
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
        logger.error(f"خطا در بارگذاری سوابق: {str(e)}")
        raise HTTPException(status_code=400, detail=f"خطا در بارگذاری فایل: {str(e)}")