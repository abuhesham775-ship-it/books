"""
Points Schemas - مخططات النقاط
"""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel


class PointsResponse(BaseModel):
    """مخطط استجابة النقاط"""
    user_id: int
    total_points: int
    current_balance: int
    lifetime_earned: int
    level: int = 1

    class Config:
        from_attributes = True


class TransactionResponse(BaseModel):
    """مخطط استجابة المعاملة"""
    id: int
    amount: int
    transaction_type: str
    description: Optional[str] = None
    reference_id: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class PointsTransfer(BaseModel):
    """مخطط تحويل النقاط"""
    to_user_id: int
    amount: int


class CouponUse(BaseModel):
    """مخطط استخدام كوبون"""
    code: str


class PointsHistoryResponse(BaseModel):
    """مخطط سجل النقاط"""
    transactions: list[TransactionResponse]
    total_pages: int
    current_page: int
