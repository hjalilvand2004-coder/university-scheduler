from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload
from typing import List
from app.core.database import get_db
from app.models.basket import Basket
from app.models.basket_item import BasketItem
from app.schemas.basket import BasketCreate, BasketOut, BasketItemOut

# ===== وارد کردن توابع از slot_times و helpers =====
from app.services.schedule.slot_times import normalize_term, time_to_minutes
from app.utils.helpers import normalize_day, DAY_MAP

router = APIRouter(prefix="/baskets", tags=["baskets"])

# ===== تابع کمکی برای نرمال‌سازی semester =====
def normalize_semester(semester: str) -> str:
    if not semester:
        return semester
    try:
        return normalize_term(semester)
    except ValueError:
        # اگر ترم نامعتبر بود، همان مقدار برگردانده می‌شود
        return semester

# ===== تابع کمکی برای نرمال‌سازی آیتم سبد =====
def normalize_basket_item_data(item_data: dict) -> dict:
    """نرمال‌سازی فیلدهای day و زمان در آیتم سبد در صورت وجود"""
    data = item_data.copy()
    if "day" in data and data["day"] is not None:
        day_norm = normalize_day(str(data["day"]))
        if day_norm in DAY_MAP:
            data["day"] = DAY_MAP[day_norm]
    if "start_time" in data and data["start_time"]:
        # بررسی ساده برای فرمت زمان
        try:
            time_to_minutes(data["start_time"])
        except:
            pass  # اگر نامعتبر بود، تغییر نمی‌دهیم
    if "end_time" in data and data["end_time"]:
        try:
            time_to_minutes(data["end_time"])
        except:
            pass
    return data


@router.post("/", response_model=BasketOut)
def create_basket(basket: BasketCreate, db: Session = Depends(get_db)):
    # نرمال‌سازی semester
    semester = normalize_semester(basket.semester)
    db_basket = Basket(title=basket.title, semester=semester, year=basket.year)
    db.add(db_basket)
    db.commit()
    db.refresh(db_basket)
    return db_basket


@router.get("/", response_model=List[BasketOut])
def list_baskets(db: Session = Depends(get_db)):
    baskets = db.query(Basket).options(joinedload(Basket.items)).order_by(Basket.created_at.desc()).all()
    return baskets


@router.get("/{basket_id}", response_model=BasketOut)
def get_basket(basket_id: int, db: Session = Depends(get_db)):
    basket = db.query(Basket).options(joinedload(Basket.items)).filter(Basket.id == basket_id).first()
    if not basket:
        raise HTTPException(status_code=404, detail="Basket not found")
    return basket


@router.post("/{basket_id}/items", response_model=BasketItemOut)
def add_item_to_basket(basket_id: int, item_data: dict, db: Session = Depends(get_db)):
    basket = db.query(Basket).filter(Basket.id == basket_id).first()
    if not basket:
        raise HTTPException(status_code=404, detail="Basket not found")
    # نرمال‌سازی داده‌های آیتم
    normalized_item_data = normalize_basket_item_data(item_data)
    new_item = BasketItem(basket_id=basket_id, **normalized_item_data)
    db.add(new_item)
    db.commit()
    db.refresh(new_item)
    return new_item


@router.delete("/{basket_id}")
def delete_basket(basket_id: int, db: Session = Depends(get_db)):
    basket = db.query(Basket).filter(Basket.id == basket_id).first()
    if not basket:
        raise HTTPException(status_code=404, detail="Basket not found")
    db.delete(basket)
    db.commit()
    return {"status": "deleted"}


@router.delete("/{basket_id}/items")
def delete_all_items(basket_id: int, db: Session = Depends(get_db)):
    basket = db.query(Basket).filter(Basket.id == basket_id).first()
    if not basket:
        raise HTTPException(status_code=404, detail="Basket not found")
    db.query(BasketItem).filter(BasketItem.basket_id == basket_id).delete()
    db.commit()
    return {"status": "items deleted"}