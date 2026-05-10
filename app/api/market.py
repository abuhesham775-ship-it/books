"""
Market API - واجهة برمجة السوق الداخلي
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from app.database import get_db
from app.services.market_service import MarketService
from app.schemas.book import BookResponse

router = APIRouter(prefix="/market", tags=["السوق"])


@router.get("/listings")
def get_listings(
    limit: int = Query(default=20, ge=1, le=50),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db)
):
    """الحصول على قوائم السوق المتاحة"""
    service = MarketService(db)
    listings = service.get_available_listings(limit=limit, offset=offset)
    return {"listings": listings, "count": len(listings)}


@router.get("/auctions")
def get_auctions(
    limit: int = Query(default=10, ge=1, le=30),
    db: Session = Depends(get_db)
):
    """الحصول على المزادات النشطة"""
    service = MarketService(db)
    auctions = service.get_auctions(limit=limit)
    return {"auctions": auctions, "count": len(auctions)}


@router.get("/featured")
def get_featured(
    limit: int = Query(default=10, ge=1, le=20),
    db: Session = Depends(get_db)
):
    """الحصول على القوائم المميزة"""
    service = MarketService(db)
    listings = service.get_featured_listings(limit=limit)
    return {"listings": listings, "count": len(listings)}


@router.get("/search")
def search_market(
    q: str = Query(..., min_length=1),
    limit: int = Query(default=20, ge=1, le=50),
    db: Session = Depends(get_db)
):
    """البحث في السوق"""
    service = MarketService(db)
    listings = service.search_listings(q, limit=limit)
    return {"listings": listings, "count": len(listings)}


@router.get("/user/{telegram_id}/listings")
def get_user_listings(
    telegram_id: int,
    db: Session = Depends(get_db)
):
    """قوائم المستخدم للبيع"""
    from app.services.user_service import UserService

    user_service = UserService(db)
    user = user_service.get_user_by_telegram_id(telegram_id)

    if not user:
        raise HTTPException(status_code=404, detail="المستخدم غير موجود")

    service = MarketService(db)
    listings = service.get_user_listings(user.id)
    return {"listings": listings, "count": len(listings)}


@router.get("/user/{telegram_id}/purchases")
def get_user_purchases(
    telegram_id: int,
    limit: int = Query(default=20, ge=1, le=50),
    db: Session = Depends(get_db)
):
    """مشتريات المستخدم"""
    from app.services.user_service import UserService

    user_service = UserService(db)
    user = user_service.get_user_by_telegram_id(telegram_id)

    if not user:
        raise HTTPException(status_code=404, detail="المستخدم غير موجود")

    service = MarketService(db)
    purchases = service.get_user_purchases(user.id, limit=limit)
    return {"purchases": purchases, "count": len(purchases)}


@router.get("/user/{telegram_id}/sales")
def get_user_sales(
    telegram_id: int,
    limit: int = Query(default=20, ge=1, le=50),
    db: Session = Depends(get_db)
):
    """مبيعات المستخدم"""
    from app.services.user_service import UserService

    user_service = UserService(db)
    user = user_service.get_user_by_telegram_id(telegram_id)

    if not user:
        raise HTTPException(status_code=404, detail="المستخدم غير موجود")

    service = MarketService(db)
    sales = service.get_user_sales(user.id, limit=limit)
    return {"sales": sales, "count": len(sales)}


@router.get("/stats")
def get_market_stats(
    db: Session = Depends(get_db)
):
    """إحصائيات السوق"""
    service = MarketService(db)
    earnings = service.get_platform_earnings()
    return earnings


@router.get("/price-range")
def get_price_range(
    db: Session = Depends(get_db)
):
    """نطاق الأسعار"""
    service = MarketService(db)
    return service.get_price_range()
