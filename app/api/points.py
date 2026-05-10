"""
Points API - واجهة برمجة النقاط
"""
from typing import List
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from app.database import get_db
from app.services.points_service import PointsService
from app.schemas.points import PointsResponse, TransactionResponse, PointsTransfer

router = APIRouter(prefix="/points", tags=["النقاط"])


@router.get("/{user_id}", response_model=PointsResponse)
def get_user_points(
    user_id: int,
    db: Session = Depends(get_db)
):
    """الحصول على نقاط مستخدم"""
    service = PointsService(db)
    points = service.get_user_points(user_id)

    if not points:
        # إنشاء نقاط جديدة للمستخدم
        points = service.get_or_create_user_points(user_id)

    return points


@router.get("/{user_id}/transactions", response_model=List[TransactionResponse])
def get_user_transactions(
    user_id: int,
    limit: int = Query(default=50, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """الحصول على سجل معاملات نقاط المستخدم"""
    service = PointsService(db)
    transactions = service.get_transactions(user_id, limit=limit)
    return transactions


@router.post("/transfer")
def transfer_points(
    transfer_data: PointsTransfer,
    from_telegram_id: int,
    db: Session = Depends(get_db)
):
    """تحويل نقاط بين مستخدمين"""
    from app.services.user_service import UserService

    user_service = UserService(db)

    # الحصول على معرفات المستخدمين
    from_user = user_service.get_user_by_telegram_id(from_telegram_id)
    to_user = user_service.get_user_by_telegram_id(transfer_data.to_user_id)

    if not from_user:
        raise HTTPException(status_code=404, detail="المستخدم المرسل غير موجود")
    if not to_user:
        raise HTTPException(status_code=404, detail="المستخدم المستقبل غير موجود")

    service = PointsService(db)
    success, message = service.transfer_points(
        from_user.id,
        to_user.id,
        transfer_data.amount
    )

    if not success:
        raise HTTPException(status_code=400, detail=message)

    return {"message": message}


@router.get("/leaderboard", response_model=List[PointsResponse])
def get_leaderboard(
    limit: int = Query(default=10, ge=1, le=50),
    db: Session = Depends(get_db)
):
    """الحصول على لوحة المتصدرين"""
    service = PointsService(db)
    leaderboard = service.get_leaderboard(limit=limit)
    return leaderboard
