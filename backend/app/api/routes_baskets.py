from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload
from typing import List
from app.core.database import get_db
from app.models.basket import Basket
from app.models.basket_item import BasketItem
from app.schemas.basket import BasketCreate, BasketOut, BasketItemOut

router = APIRouter(prefix="/baskets", tags=["baskets"])  # اضافه کردن prefix

@router.post("/", response_model=BasketOut)
def create_basket(basket: BasketCreate, db: Session = Depends(get_db)):
    db_basket = Basket(title=basket.title, semester=basket.semester, year=basket.year)
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
    new_item = BasketItem(basket_id=basket_id, **item_data)
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