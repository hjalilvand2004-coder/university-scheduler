from fastapi import APIRouter, HTTPException, UploadFile, File, Depends
from sqlalchemy.orm import Session
import pandas as pd
from io import BytesIO
import re
import logging

from app.core.database import get_db
from app.models.instructor import Instructor
from app.models.room import Room

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/professors-rooms",
    tags=["Professors & Rooms"],
)


# ===== توابع کمکی =====
def normalize_column_name(col: str) -> str:
    """نرمال‌سازی نام ستون: حذف فاصله‌های اضافی و کاراکترهای خاص"""
    if not isinstance(col, str):
        return col
    col = col.strip()
    col = re.sub(r'\s+', ' ', col)
    return col


def clean_value(value):
    """پاکسازی و تبدیل مقدار"""
    if pd.isna(value):
        return None
    if isinstance(value, float) and value.is_integer():
        return int(value)
    if isinstance(value, str):
        return value.strip()
    return value


# ============================================
# APIهای اساتید (همان‌طور که بود)
# ============================================

@router.get("/instructors/list")
async def get_instructors(db: Session = Depends(get_db)):
    return db.query(Instructor).all()


@router.post("/instructors")
async def create_instructor(data: dict, db: Session = Depends(get_db)):
    new = Instructor(**data)
    db.add(new)
    db.commit()
    db.refresh(new)
    return new


@router.put("/instructors/{id}")
async def update_instructor(id: int, data: dict, db: Session = Depends(get_db)):
    item = db.query(Instructor).filter(Instructor.id == id).first()
    if not item:
        raise HTTPException(status_code=404, detail="استاد پیدا نشد")
    for key, value in data.items():
        setattr(item, key, value)
    db.commit()
    db.refresh(item)
    return item


@router.delete("/instructors/{id}")
async def delete_instructor(id: int, db: Session = Depends(get_db)):
    item = db.query(Instructor).filter(Instructor.id == id).first()
    if not item:
        raise HTTPException(status_code=404, detail="استاد پیدا نشد")
    db.delete(item)
    db.commit()
    return {"message": "استاد با موفقیت حذف شد"}


@router.post("/upload/instructors")
async def upload_instructors_excel(file: UploadFile = File(...), db: Session = Depends(get_db)):
    try:
        contents = await file.read()
        df = pd.read_excel(BytesIO(contents))
        df.columns = [normalize_column_name(col) for col in df.columns]
        df = df.where(pd.notnull(df), None)
        records = df.to_dict(orient="records")
        added = 0
        errors = []

        column_map = {
            "ردیف": "row_number",
            "کد": "code",
            "نام و نام خانوادگی": "name",
            "نام کاربری": "username",
            "گروه": "group",
            "نوع همکاری": "cooperation_type"
        }

        required_cols = ["کد", "نام و نام خانوادگی"]
        missing_cols = [col for col in required_cols if col not in df.columns]
        if missing_cols:
            raise HTTPException(
                status_code=400,
                detail=f"ستون‌های ضروری در فایل وجود ندارند: {', '.join(missing_cols)}"
            )

        for idx, rec in enumerate(records, start=1):
            try:
                data = {}
                for excel_col, model_field in column_map.items():
                    data[model_field] = clean_value(rec.get(excel_col))

                if not data.get("code") or not data.get("name"):
                    errors.append(f"ردیف {idx}: کد یا نام خالی است")
                    continue

                db.add(Instructor(**data))
                added += 1
            except Exception as e:
                errors.append(f"ردیف {idx}: {str(e)}")

        if added == 0 and errors:
            raise HTTPException(
                status_code=400,
                detail=f"هیچ رکوردی بارگذاری نشد. خطاها: {', '.join(errors[:5])}"
            )

        db.commit()
        return {
            "message": f"بارگذاری اساتید با موفقیت انجام شد. {added} رکورد اضافه شد.",
            "count": added,
            "errors": errors if errors else []
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"خطا در بارگذاری اساتید: {str(e)}")
        raise HTTPException(status_code=400, detail=f"خطا در بارگذاری فایل: {str(e)}")


# ============================================
# APIهای اتاق‌ها (اصلاح‌شده نهایی)
# ============================================

@router.get("/rooms/list")
async def get_rooms(db: Session = Depends(get_db)):
    return db.query(Room).all()


@router.post("/rooms")
async def create_room(data: dict, db: Session = Depends(get_db)):
    try:
        if "capacity" in data and data["capacity"] is not None:
            data["capacity"] = int(data["capacity"])
        new = Room(**data)
        db.add(new)
        db.commit()
        db.refresh(new)
        return new
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"خطا در ایجاد اتاق: {str(e)}")


@router.put("/rooms/{id}")
async def update_room(id: int, data: dict, db: Session = Depends(get_db)):
    item = db.query(Room).filter(Room.id == id).first()
    if not item:
        raise HTTPException(status_code=404, detail="اتاق پیدا نشد")
    for key, value in data.items():
        if key == "capacity" and value is not None:
            value = int(value)
        setattr(item, key, value)
    db.commit()
    db.refresh(item)
    return item


@router.delete("/rooms/{id}")
async def delete_room(id: int, db: Session = Depends(get_db)):
    item = db.query(Room).filter(Room.id == id).first()
    if not item:
        raise HTTPException(status_code=404, detail="اتاق پیدا نشد")
    db.delete(item)
    db.commit()
    return {"message": "اتاق با موفقیت حذف شد"}


@router.post("/upload/rooms")
async def upload_rooms_excel(file: UploadFile = File(...), db: Session = Depends(get_db)):
    """
    بارگذاری فایل اکسل اتاق‌ها
    فرمت ستون‌ها: ردیف, کد کلاس, نام کلاس, ظرفیت کلاس, گروه, نوع مکان
    """
    try:
        # 1. خواندن فایل
        contents = await file.read()
        df = pd.read_excel(BytesIO(contents))

        # 2. نرمال‌سازی نام ستون‌ها (حذف فاصله‌های اضافی)
        df.columns = [normalize_column_name(col) for col in df.columns]

        # 3. لاگ نام ستون‌ها برای دیباگ
        logger.info(f"ستون‌های شناسایی‌شده در فایل اتاق‌ها: {list(df.columns)}")

        # 4. جایگزینی NaN با None
        df = df.where(pd.notnull(df), None)

        # 5. تبدیل به لیست دیکشنری
        records = df.to_dict(orient="records")

        # 6. نگاشت ستون‌ها (با نام‌های دقیق)
        column_map = {
            "ردیف": "row_number",
            "کد کلاس": "code",
            "نام کلاس": "name",
            "ظرفیت کلاس": "capacity",
            "گروه": "group",
            "نوع مکان": "place_type"
        }

        # 7. بررسی وجود ستون‌های ضروری
        required_cols = ["کد کلاس", "نام کلاس"]
        missing_cols = [col for col in required_cols if col not in df.columns]
        if missing_cols:
            raise HTTPException(
                status_code=400,
                detail=f"ستون‌های ضروری در فایل وجود ندارند: {', '.join(missing_cols)}"
            )

        added = 0
        errors = []

        # 8. پردازش هر رکورد
        for idx, rec in enumerate(records, start=1):
            try:
                # 8.1 ساخت دیکشنری داده با استفاده از نگاشت
                data = {}
                for excel_col, model_field in column_map.items():
                    value = rec.get(excel_col)
                    data[model_field] = clean_value(value)

                # 8.2 اعتبارسنجی و تبدیل ظرفیت
                capacity_value = data.get("capacity")
                if capacity_value is None:
                    errors.append(f"ردیف {idx}: ظرفیت خالی است")
                    continue

                try:
                    # اگر رشته است، اعداد را استخراج کنید
                    if isinstance(capacity_value, str):
                        # حذف همه کاراکترهای غیرعددی به جز نقطه
                        clean_cap = re.sub(r'[^\d.]', '', capacity_value)
                        if clean_cap:
                            data["capacity"] = int(float(clean_cap))
                        else:
                            errors.append(f"ردیف {idx}: مقدار ظرفیت نامعتبر است ('{capacity_value}')")
                            continue
                    else:
                        data["capacity"] = int(capacity_value)
                except (ValueError, TypeError) as e:
                    errors.append(f"ردیف {idx}: ظرفیت باید عدد باشد (دریافت: '{capacity_value}')")
                    continue

                # 8.3 اعتبارسنجی کد و نام
                if not data.get("code") or not data.get("name"):
                    errors.append(f"ردیف {idx}: کد کلاس یا نام کلاس خالی است")
                    continue

                # 8.4 ایجاد و ذخیره در دیتابیس
                new_room = Room(**data)
                db.add(new_room)
                added += 1

            except Exception as e:
                errors.append(f"ردیف {idx}: {str(e)}")
                logger.error(f"خطا در ردیف {idx}: {str(e)}")

        # 9. اگر همه رکوردها خطا داشتند
        if added == 0 and errors:
            raise HTTPException(
                status_code=400,
                detail=f"هیچ رکوردی بارگذاری نشد. خطاها: {', '.join(errors[:5])}"
            )

        # 10. ذخیره نهایی در دیتابیس
        db.commit()

        return {
            "message": f"بارگذاری اتاق‌ها با موفقیت انجام شد. {added} رکورد اضافه شد.",
            "count": added,
            "errors": errors if errors else []
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"خطا در بارگذاری اتاق‌ها: {str(e)}")
        raise HTTPException(status_code=400, detail=f"خطا در بارگذاری فایل: {str(e)}")

