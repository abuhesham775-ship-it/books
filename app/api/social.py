"""
Social API - واجهة النظام الاجتماعي والمتابعة
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from app.database import get_db
from app.services.social_service import SocialService
from app.services.user_service import UserService
from app.schemas.user import UserResponse
from app.models.social import ActivityFeed

router = APIRouter(prefix="/social", tags=["المجتمع"])


class FollowRequest(BaseModel):
    telegram_id: int
    target_telegram_id: int


@router.post("/follow")
def follow_user(payload: FollowRequest, db: Session = Depends(get_db)):
    service = SocialService(db)
    user_service = UserService(db)

    user = user_service.get_user_by_telegram_id(payload.telegram_id)
    target = user_service.get_user_by_telegram_id(payload.target_telegram_id)
    if not user or not target:
        raise HTTPException(status_code=404, detail="المستخدم غير موجود")

    success = service.follow_user(user.id, target.id)
    if not success:
        raise HTTPException(status_code=400, detail="غير قادر على المتابعة")

    return {"message": "تمت المتابعة"}


class UnfollowRequest(BaseModel):
    telegram_id: int
    target_telegram_id: int


@router.post("/unfollow")
def unfollow_user(payload: UnfollowRequest, db: Session = Depends(get_db)):
    service = SocialService(db)
    user_service = UserService(db)

    user = user_service.get_user_by_telegram_id(payload.telegram_id)
    target = user_service.get_user_by_telegram_id(payload.target_telegram_id)
    if not user or not target:
        raise HTTPException(status_code=404, detail="المستخدم غير موجود")

    success = service.unfollow_user(user.id, target.id)
    if not success:
        raise HTTPException(status_code=400, detail="غير قادر على إلغاء المتابعة")

    return {"message": "تم إلغاء المتابعة"}


@router.get("/followers/{telegram_id}", response_model=List[UserResponse])
def list_followers(telegram_id: int, db: Session = Depends(get_db)):
    service = SocialService(db)
    user_service = UserService(db)
    user = user_service.get_user_by_telegram_id(telegram_id)
    if not user:
        raise HTTPException(status_code=404, detail="المستخدم غير موجود")

    followers = service.get_followers(user.id)
    return followers


@router.get("/following/{telegram_id}", response_model=List[UserResponse])
def list_following(telegram_id: int, db: Session = Depends(get_db)):
    service = SocialService(db)
    user_service = UserService(db)
    user = user_service.get_user_by_telegram_id(telegram_id)
    if not user:
        raise HTTPException(status_code=404, detail="المستخدم غير موجود")

    following = service.get_following(user.id)
    return following


@router.get("/feed/{telegram_id}")
def get_user_feed(telegram_id: int, limit: int = Query(default=25, ge=1, le=100), db: Session = Depends(get_db)):
    service = SocialService(db)
    user_service = UserService(db)
    user = user_service.get_user_by_telegram_id(telegram_id)
    if not user:
        raise HTTPException(status_code=404, detail="المستخدم غير موجود")

    feed = service.get_activity_feed(user.id, limit)
    return {"feed": [
        {
            "id": activity.id,
            "actor_id": activity.actor_id,
            "activity_type": activity.activity_type.value,
            "description": activity.description,
            "target_book_id": activity.target_book_id,
            "created_at": activity.created_at,
        }
        for activity in feed
    ]}


@router.get("/global-feed")
def get_global_feed(limit: int = Query(default=25, ge=1, le=100), db: Session = Depends(get_db)):
    service = SocialService(db)
    feed = service.get_global_feed(limit)
    return {"feed": [
        {
            "id": activity.id,
            "user_id": activity.user_id,
            "actor_id": activity.actor_id,
            "activity_type": activity.activity_type.value,
            "description": activity.description,
            "target_book_id": activity.target_book_id,
            "created_at": activity.created_at,
        }
        for activity in feed
    ]}
