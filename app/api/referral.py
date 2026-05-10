"""
Referral API - واجهة برمجة الإحالة
"""
from typing import List
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from app.database import get_db
from app.services.referral_service import ReferralService

router = APIRouter(prefix="/referral", tags=["الإحالة"])


@router.get("/stats/{telegram_id}")
def get_referral_stats(
    telegram_id: int,
    db: Session = Depends(get_db)
):
    """إحصائيات الإحالة"""
    from app.services.user_service import UserService

    user_service = UserService(db)
    user = user_service.get_user_by_telegram_id(telegram_id)

    if not user:
        raise HTTPException(status_code=404, detail="المستخدم غير موجود")

    service = ReferralService(db)
    return service.get_referral_stats(user.id)


@router.get("/earnings/{telegram_id}")
def get_earnings(
    telegram_id: int,
    db: Session = Depends(get_db)
):
    """أرباح الإحالة"""
    from app.services.user_service import UserService

    user_service = UserService(db)
    user = user_service.get_user_by_telegram_id(telegram_id)

    if not user:
        raise HTTPException(status_code=404, detail="المستخدم غير موجود")

    service = ReferralService(db)
    return service.get_referral_earnings(user.id)


@router.get("/history/{telegram_id}")
def get_history(
    telegram_id: int,
    limit: int = Query(default=20, ge=1, le=50),
    db: Session = Depends(get_db)
):
    """سجل الإحالات"""
    from app.services.user_service import UserService

    user_service = UserService(db)
    user = user_service.get_user_by_telegram_id(telegram_id)

    if not user:
        raise HTTPException(status_code=404, detail="المستخدم غير موجود")

    service = ReferralService(db)
    return {"history": service.get_referral_history(user.id, limit=limit)}


@router.get("/link/{telegram_id}")
def get_referral_link(
    telegram_id: int,
    db: Session = Depends(get_db)
):
    """رابط الإحالة"""
    from app.services.user_service import UserService

    user_service = UserService(db)
    user = user_service.get_user_by_telegram_id(telegram_id)

    if not user:
        raise HTTPException(status_code=404, detail="المستخدم غير موجود")

    service = ReferralService(db)
    link = service.get_or_create_referral_link(user.id)
    return {
        "code": link.custom_code,
        "link": link.telegram_link,
        "clicks": link.total_clicks,
        "signups": link.total_signups
    }


@router.get("/badges/{telegram_id}")
def get_badges(
    telegram_id: int,
    db: Session = Depends(get_db)
):
    """شارات المستخدم"""
    from app.services.user_service import UserService

    user_service = UserService(db)
    user = user_service.get_user_by_telegram_id(telegram_id)

    if not user:
        raise HTTPException(status_code=404, detail="المستخدم غير موجود")

    service = ReferralService(db)
    badges = service.get_user_badges(user.id)
    return {"badges": badges, "count": len(badges)}


@router.get("/top")
def get_top_referrers(
    limit: int = Query(default=10, ge=1, le=50),
    db: Session = Depends(get_db)
):
    """أفضل المحيلين"""
    service = ReferralService(db)
    return {"top": service.get_top_referrers(limit=limit)}
