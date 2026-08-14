from fastapi import APIRouter, HTTPException, UploadFile, File, Depends
from sqlalchemy.orm import Session
import pandas as pd
from io import BytesIO
import re
import logging

from app.core.database import get_db
from app.models.time_preference import TimePreference

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/time-preferences", tags=["Time Preferences"])

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
    return db.query(TimePreference).all()

@router.post("/")
async def create(data: dict, db: Session = Depends(get_db)):
    new = TimePreference(**data)
    db.add(new)
    db.commit()
    db.refresh(new)
    return new

@router.put("/{id}")
async def update(id: int, data: dict, db: Session = Depends(get_db)):
    item = db.query(TimePreference).filter(TimePreference.id == id).first()
    if not item:
        raise HTTPException(status_code=404, detail="رکورد پیدا نشد")
    for key, value in data.items():
        setattr(item, key, value)
    db.commit()
    db.refresh(item)
    return item

@router.delete("/{id}")
async def delete(id: int, db: Session = Depends(get_db)):
    item = db.query(TimePreference).filter(TimePreference.id == id).first()
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
        logger.info(f"ستون‌های شناسایی‌شده در فایل مطلوبیت‌های زمان‌بندی: {list(df.columns)}")
        df = df.where(pd.notnull(df), None)
        records = df.to_dict(orient="records")

        column_map = {
            "روز": "day",
            "نوع همکاری": "cooperation_type",
            "زمان پایان": "end_time",
            "گروه تخصصی": "expert_group",
            "ردیف": "row_number",
            "وضعیت": "status",
            "کد استاد": "instructor_code",
            "استاد": "instructor_name",
            "یوزرنیم استاد": "instructor_username",
            "زمان شروع": "start_time",
            "گروه زمانی": "time_group",
            "اولویت": "priority"  # ← اضافه شود
        }

        required_cols = ["روز", "استاد", "زمان شروع", "زمان پایان"]
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

                # تبدیل وضعیت به Boolean
                if data.get("status") is not None:
                    if isinstance(data["status"], str):
                        data["status"] = data["status"].lower() in ["true", "1", "yes", "فعال"]
                    else:
                        data["status"] = bool(data["status"])
                else:
                    data["status"] = False

                if not data.get("day") or not data.get("instructor_name"):
                    errors.append(f"ردیف {idx}: روز یا نام استاد خالی است")
                    continue

                db.add(TimePreference(**data))
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
        logger.error(f"خطا در بارگذاری مطلوبیت‌های زمان‌بندی: {str(e)}")
        raise HTTPException(status_code=400, detail=f"خطا در بارگذاری فایل: {str(e)}")