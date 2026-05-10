"""
Notifications API - واجهة برمجة الإشعارات
"""
from typing import List
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from app.database import get_db
from app.services.notification_service import NotificationService

router = APIRouter(prefix="/notifications", tags=["الإشعارات"])


@router.get("/user/{telegram_id}")
def get_notifications(
    telegram_id: int,
    unread_only: bool = False,
    limit: int = Query(default=50, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """إشعارات المستخدم"""
    from app.services.user_service import UserService

    user_service = UserService(db)
    user = user_service.get_user_by_telegram_id(telegram_id)

    if not user:
        raise HTTPException(status_code=404, detail="المستخدم غير موجود")

    service = NotificationService(db)
    return {
        "notifications": service.get_user_notifications(
            user.id,
            unread_only=unread_only,
            limit=limit
        )
    }


@router.get("/user/{telegram_id}/unread-count")
def get_unread_count(
    telegram_id: int,
    db: Session = Depends(get_db)
):
    """عدد الإشعارات غير المقروءة"""
    from app.services.user_service import UserService

    user_service = UserService(db)
    user = user_service.get_user_by_telegram_id(telegram_id)

    if not user:
        raise HTTPException(status_code=404, detail="المستخدم غير موجود")

    service = NotificationService(db)
    return {"count": service.get_unread_count(user.id)}


@router.get("/user/{telegram_id}/stats")
def get_notification_stats(
    telegram_id: int,
    db: Session = Depends(get_db)
):
    """إحصائيات الإشعارات"""
    from app.services.user_service import UserService

    user_service = UserService(db)
    user = user_service.get_user_by_telegram_id(telegram_id)

    if not user:
        raise HTTPException(status_code=404, detail="المستخدم غير موجود")

    service = NotificationService(db)
    return service.get_notification_stats(user.id)


@router.post("/user/{telegram_id}/read/{notification_id}")
def mark_as_read(
    telegram_id: int,
    notification_id: int,
    db: Session = Depends(get_db)
):
    """تحديد كمقروء"""
    from app.services.user_service import UserService

    user_service = UserService(db)
    user = user_service.get_user_by_telegram_id(telegram_id)

    if not user:
        raise HTTPException(status_code=404, detail="المستخدم غير موجود")

    service = NotificationService(db)
    success = service.mark_as_read(notification_id, user.id)

    if not success:
        raise HTTPException(status_code=404, detail="الإشعار غير موجود")

    return {"success": True}


@router.post("/user/{telegram_id}/read-all")
def mark_all_as_read(
    telegram_id: int,
    db: Session = Depends(get_db)
):
    """تحديد الكل كمقروء"""
    from app.services.user_service import UserService

    user_service = UserService(db)
    user = user_service.get_user_by_telegram_id(telegram_id)

    if not user:
        raise HTTPException(status_code=404, detail="المستخدم غير موجود")

    service = NotificationService(db)
    count = service.mark_all_as_read(user.id)
    return {"count": count}
