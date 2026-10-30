from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..database import get_db
from ..schemas import BrandOut, CategoryOut, RetailerOut
from ..services import products as svc

router = APIRouter(tags=["catalog"])


@router.get("/categories", response_model=list[CategoryOut], summary="All categories (parents first)")
def categories(db: Session = Depends(get_db)) -> list[CategoryOut]:
    return [CategoryOut.model_validate(c) for c in svc.list_categories(db)]


@router.get("/brands", response_model=list[BrandOut], summary="All brands")
def brands(db: Session = Depends(get_db)) -> list[BrandOut]:
    return [BrandOut.model_validate(b) for b in svc.list_brands(db)]


@router.get("/retailers", response_model=list[RetailerOut], summary="All stores")
def retailers(db: Session = Depends(get_db)) -> list[RetailerOut]:
    return [RetailerOut.model_validate(r) for r in svc.list_retailers(db)]
