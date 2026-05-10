"""
Users API - واجهة برمجة المستخدمين
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from app.database import get_db
from app.services.user_service import UserService
from app.schemas.user import UserResponse, UserUpdate

router = APIRouter(prefix="/users", tags=["المستخدمين"])


@router.get("/", response_model=List[UserResponse])
def get_users(
    status: Optional[str] = None,
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db)
):
    """الحصول على قائمة المستخدمين"""
    from app.models.user import UserStatus

    service = UserService(db)
    status_enum = UserStatus[status.upper()] if status else None
    users = service.get_all_users(status=status_enum)

    return users[offset:offset + limit]


@router.get("/search")
def search_users(
    q: str = Query(..., min_length=1),
    db: Session = Depends(get_db)
):
    """البحث عن مستخدمين"""
    service = UserService(db)
    users = service.search_users(q)
    return {"users": users, "count": len(users)}


@router.get("/{telegram_id}", response_model=UserResponse)
def get_user(
    telegram_id: int,
    db: Session = Depends(get_db)
):
    """الحصول على مستخدم بمعرف تيليجرام"""
    service = UserService(db)
    user = service.get_user_by_telegram_id(telegram_id)

    if not user:
        raise HTTPException(status_code=404, detail="المستخدم غير موجود")

    return user


@router.put("/{telegram_id}", response_model=UserResponse)
def update_user(
    telegram_id: int,
    user_data: UserUpdate,
    db: Session = Depends(get_db)
):
    """تحديث مستخدم"""
    service = UserService(db)
    user = service.update_user(telegram_id, **user_data.model_dump(exclude_unset=True))

    if not user:
        raise HTTPException(status_code=404, detail="المستخدم غير موجود")

    return user


@router.post("/{telegram_id}/ban")
def ban_user(
    telegram_id: int,
    db: Session = Depends(get_db)
):
    """حظر مستخدم"""
    service = UserService(db)
    user = service.ban_user(telegram_id)

    if not user:
        raise HTTPException(status_code=404, detail="المستخدم غير موجود")

    return {"message": "تم حظر المستخدم", "user": user}


@router.post("/{telegram_id}/unban")
def unban_user(
    telegram_id: int,
    db: Session = Depends(get_db)
):
    """إلغاء حظر مستخدم"""
    service = UserService(db)
    user = service.unban_user(telegram_id)

    if not user:
        raise HTTPException(status_code=404, detail="المستخدم غير موجود")

    return {"message": "تم إلغاء حظر المستخدم", "user": user}


@router.get("/{telegram_id}/favorites")
def get_user_favorites(
    telegram_id: int,
    db: Session = Depends(get_db)
):
    """الحصول على كتب المستخدم المفضلة"""
    service = UserService(db)
    favorites = service.get_user_favorites(telegram_id)
    return {"favorites": favorites, "count": len(favorites)}


@router.get("/{telegram_id}/downloads")
def get_user_downloads(
    telegram_id: int,
    limit: int = Query(default=20, ge=1, le=50),
    db: Session = Depends(get_db)
):
    """الحصول على سجل تحميلات المستخدم"""
    service = UserService(db)
    downloads = service.get_user_downloads(telegram_id, limit=limit)
    return {"downloads": downloads, "count": len(downloads)}
