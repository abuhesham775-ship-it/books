"""
Challenges API - واجهة برمجة التحديات
"""
from typing import List
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from app.database import get_db
from app.services.challenge_service import ChallengeService

router = APIRouter(prefix="/challenges", tags=["التحديات"])


@router.get("/available/{telegram_id}")
def get_available(
    telegram_id: int,
    db: Session = Depends(get_db)
):
    """التحديات المتاحة"""
    from app.services.user_service import UserService

    user_service = UserService(db)
    user = user_service.get_user_by_telegram_id(telegram_id)

    if not user:
        raise HTTPException(status_code=404, detail="المستخدم غير موجود")

    service = ChallengeService(db)
    challenges = service.get_available_challenges(user.id)
    return {"challenges": challenges, "count": len(challenges)}


@router.get("/active/{telegram_id}")
def get_active(
    telegram_id: int,
    db: Session = Depends(get_db)
):
    """التحديات النشطة"""
    from app.services.user_service import UserService

    user_service = UserService(db)
    user = user_service.get_user_by_telegram_id(telegram_id)

    if not user:
        raise HTTPException(status_code=404, detail="المستخدم غير موجود")

    service = ChallengeService(db)
    participations = service.get_active_challenges(user.id)
    return {"participations": participations, "count": len(participations)}


@router.get("/badges")
def get_all_badges(db: Session = Depends(get_db)):
    """جميع الشارات"""
    service = ChallengeService(db)
    return {"badges": service.get_all_badges()}


@router.get("/user/{telegram_id}/badges")
def get_user_badges(
    telegram_id: int,
    db: Session = Depends(get_db)
):
    """شارات المستخدم"""
    from app.services.user_service import UserService

    user_service = UserService(db)
    user = user_service.get_user_by_telegram_id(telegram_id)

    if not user:
        raise HTTPException(status_code=404, detail="المستخدم غير موجود")

    service = ChallengeService(db)
    badges = service.get_user_badges(user.id)
    return {"badges": badges, "count": len(badges)}


@router.get("/user/{telegram_id}/stats")
def get_stats(
    telegram_id: int,
    db: Session = Depends(get_db)
):
    """إحصائيات التحديات"""
    from app.services.user_service import UserService

    user_service = UserService(db)
    user = user_service.get_user_by_telegram_id(telegram_id)

    if not user:
        raise HTTPException(status_code=404, detail="المستخدم غير موجود")

    service = ChallengeService(db)
    return service.get_challenge_stats(user.id)


@router.get("/leaderboard/{leaderboard_type}")
def get_leaderboard(
    leaderboard_type: str = "weekly",
    limit: int = Query(default=10, ge=1, le=50),
    db: Session = Depends(get_db)
):
    """لوحة المتصدرين"""
    service = ChallengeService(db)
    return {"leaderboard": service.get_leaderboard(leaderboard_type, limit=limit)}


@router.get("/user/{telegram_id}/rank/{leaderboard_type}")
def get_user_rank(
    telegram_id: int,
    leaderboard_type: str = "weekly",
    db: Session = Depends(get_db)
):
    """ترتيب المستخدم"""
    from app.services.user_service import UserService

    user_service = UserService(db)
    user = user_service.get_user_by_telegram_id(telegram_id)

    if not user:
        raise HTTPException(status_code=404, detail="المستخدم غير موجود")

    service = ChallengeService(db)
    rank = service.get_user_rank(user.id, leaderboard_type)
    return {"rank": rank}


@router.get("/streak/{telegram_id}")
def get_streak(
    telegram_id: int,
    db: Session = Depends(get_db)
):
    """التسلسل اليومي"""
    from app.services.user_service import UserService

    user_service = UserService(db)
    user = user_service.get_user_by_telegram_id(telegram_id)

    if not user:
        raise HTTPException(status_code=404, detail="المستخدم غير موجود")

    service = ChallengeService(db)
    streak = service.update_daily_streak(user.id)
    return {
        "current_streak": streak.current_streak,
        "longest_streak": streak.longest_streak,
        "multiplier": streak.streak_bonus_multiplier
    }
