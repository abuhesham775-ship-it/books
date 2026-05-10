"""
User Schemas - مخططات المستخدم
"""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class UserCreate(BaseModel):
    """مخطط إنشاء مستخدم"""
    telegram_id: int
    username: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    language: str = "ar"


class UserUpdate(BaseModel):
    """مخطط تحديث مستخدم"""
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    language: Optional[str] = None
    is_premium: Optional[bool] = None


class UserResponse(BaseModel):
    """مخطط استجابة المستخدم"""
    id: int
    telegram_id: int
    username: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    status: str
    total_downloads: int
    level: int
    is_premium: bool
    language: str
    referral_code: Optional[str] = None
    created_at: datetime
    last_active: Optional[datetime] = None

    class Config:
        from_attributes = True


class UserProfile(BaseModel):
    """مخطط الملف الشخصي"""
    id: int
    telegram_id: int
    username: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    total_downloads: int
    level: int
    is_premium: bool
    current_points: int = 0
    lifetime_points: int = 0
    favorite_count: int = 0
    download_count: int = 0

    class Config:
        from_attributes = True
