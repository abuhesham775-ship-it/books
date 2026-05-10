"""
Recommendations API - واجهة برمجة التوصيات
"""
from typing import List
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from app.database import get_db
from app.services.recommendation_service import RecommendationService

router = APIRouter(prefix="/recommendations", tags=["التوصيات"])


@router.get("/personalized")
def get_personalized(
    telegram_id: int,
    limit: int = Query(default=10, ge=1, le=20),
    db: Session = Depends(get_db)
):
    """الحصول على توصيات مخصصة"""
    from app.services.user_service import UserService

    user_service = UserService(db)
    user = user_service.get_user_by_telegram_id(telegram_id)

    if not user:
        raise HTTPException(status_code=404, detail="المستخدم غير موجود")

    service = RecommendationService(db)
    books = service.get_personalized_recommendations(user.id, limit=limit)
    return {"books": books, "count": len(books)}


@router.get("/similar/{book_id}")
async def get_similar_books(
    book_id: int,
    limit: int = Query(default=5, ge=1, le=20),
    db: Session = Depends(get_db)
):
    """كتب مشابهة"""
    service = RecommendationService(db)
    books = await service.get_similar_books(book_id, limit=limit)
    return {"books": books, "count": len(books)}


@router.get("/user/{telegram_id}/stats")
def get_user_stats(
    telegram_id: int,
    db: Session = Depends(get_db)
):
    """إحصائيات سلوك المستخدم"""
    from app.services.user_service import UserService

    user_service = UserService(db)
    user = user_service.get_user_by_telegram_id(telegram_id)

    if not user:
        raise HTTPException(status_code=404, detail="المستخدم غير موجود")

    service = RecommendationService(db)
    return service.get_user_behavior_stats(user.id)


@router.get("/user/{telegram_id}/rec-stats")
def get_rec_stats(
    telegram_id: int,
    db: Session = Depends(get_db)
):
    """إحصائيات التوصيات"""
    from app.services.user_service import UserService

    user_service = UserService(db)
    user = user_service.get_user_by_telegram_id(telegram_id)

    if not user:
        raise HTTPException(status_code=404, detail="المستخدم غير موجود")

    service = RecommendationService(db)
    return service.get_recommendation_stats(user.id)
