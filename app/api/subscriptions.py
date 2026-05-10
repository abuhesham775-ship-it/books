"""
Subscriptions API - واجهة الاشتراكات والقنوات
"""
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.channel_setting import ForceJoinChannel, ChannelSetting
from app.services.channel_service import ChannelService

router = APIRouter(prefix="/subscriptions", tags=["الاشتراكات"])


class ChannelCreate(BaseModel):
    channel_id: str = Field(..., min_length=1)
    channel_name: Optional[str] = None
    channel_link: Optional[str] = None
    is_required: bool = True


class ChannelUpdate(BaseModel):
    channel_name: Optional[str] = None
    channel_link: Optional[str] = None
    is_required: Optional[bool] = None


class AutoPostCreate(BaseModel):
    channel_id: str = Field(..., min_length=1)
    channel_name: Optional[str] = None
    auto_post: bool = False
    post_template: Optional[str] = None


class AutoPostUpdate(BaseModel):
    channel_name: Optional[str] = None
    auto_post: Optional[bool] = None
    post_template: Optional[str] = None


@router.get("/channels")
def get_channels(db: Session = Depends(get_db)):
    """عرض قنوات الاشتراك الإجباري"""
    service = ChannelService(db)
    channels = service.get_all_channels()
    return {"channels": channels, "count": len(channels)}


@router.get("/channels/{channel_id}")
def get_channel(channel_id: str, db: Session = Depends(get_db)):
    """عرض قناة واحدة"""
    service = ChannelService(db)
    channel = service.get_channel(channel_id)
    if not channel:
        raise HTTPException(status_code=404, detail="القناة غير موجودة")
    return channel


@router.post("/channels")
def create_channel(payload: ChannelCreate, db: Session = Depends(get_db)):
    """إضافة قناة اشتراك إجباري"""
    service = ChannelService(db)
    channel = service.add_channel(
        channel_id=payload.channel_id,
        channel_name=payload.channel_name,
        channel_link=payload.channel_link,
        is_required=payload.is_required,
    )
    return {"message": "تمت إضافة القناة", "channel": channel}


@router.put("/channels/{channel_id}")
def update_channel(channel_id: str, payload: ChannelUpdate, db: Session = Depends(get_db)):
    """تحديث بيانات قناة"""
    service = ChannelService(db)
    channel = service.update_channel(
        channel_id=channel_id,
        channel_name=payload.channel_name,
        channel_link=payload.channel_link,
        is_required=payload.is_required,
    )
    if not channel:
        raise HTTPException(status_code=404, detail="القناة غير موجودة")
    return {"message": "تم تحديث القناة", "channel": channel}


@router.delete("/channels/{channel_id}")
def delete_channel(channel_id: str, db: Session = Depends(get_db)):
    """حذف قناة"""
    service = ChannelService(db)
    success = service.remove_channel(channel_id)
    if not success:
        raise HTTPException(status_code=404, detail="القناة غير موجودة")
    return {"message": "تم حذف القناة بنجاح"}


@router.get("/channels/required")
def get_required_channels(db: Session = Depends(get_db)):
    """القنوات الإلزامية فقط"""
    service = ChannelService(db)
    channels = [channel for channel in service.get_all_channels() if channel.is_required]
    return {"channels": channels, "count": len(channels)}


@router.get("/settings")
def get_post_settings(db: Session = Depends(get_db)):
    """إعدادات النشر التلقائي"""
    service = ChannelService(db)
    settings = service.get_all_settings()
    return {"settings": settings, "count": len(settings)}


@router.get("/settings/{channel_id}")
def get_post_setting(channel_id: str, db: Session = Depends(get_db)):
    """إعدادات قناة واحدة"""
    service = ChannelService(db)
    setting = service.get_setting(channel_id)
    if not setting:
        raise HTTPException(status_code=404, detail="إعدادات القناة غير موجودة")
    return setting


@router.post("/settings")
def create_post_setting(payload: AutoPostCreate, db: Session = Depends(get_db)):
    """إنشاء/تحديث إعدادات النشر لقناة"""
    service = ChannelService(db)
    setting = service.setup_auto_post(
        channel_id=payload.channel_id,
        channel_name=payload.channel_name,
        auto_post=payload.auto_post,
        post_template=payload.post_template,
    )
    return {"message": "تم حفظ إعدادات النشر", "setting": setting}


@router.put("/settings/{channel_id}")
def update_post_setting(channel_id: str, payload: AutoPostUpdate, db: Session = Depends(get_db)):
    """تحديث إعدادات النشر لقناة"""
    service = ChannelService(db)
    existing = service.get_setting(channel_id)
    if not existing:
        raise HTTPException(status_code=404, detail="إعدادات القناة غير موجودة")

    setting = service.setup_auto_post(
        channel_id=channel_id,
        channel_name=payload.channel_name or existing.channel_name,
        auto_post=payload.auto_post if payload.auto_post is not None else existing.auto_post,
        post_template=payload.post_template if payload.post_template is not None else existing.post_template,
    )
    return {"message": "تم تحديث الإعدادات", "setting": setting}


@router.patch("/settings/{channel_id}/toggle-auto-post")
def toggle_auto_post(channel_id: str, db: Session = Depends(get_db)):
    """تبديل حالة النشر التلقائي"""
    service = ChannelService(db)
    setting = service.toggle_auto_post(channel_id)
    if not setting:
        raise HTTPException(status_code=404, detail="إعدادات القناة غير موجودة")
    return {"message": "تم تحديث حالة النشر التلقائي", "setting": setting}


@router.get("/stats")
def get_subscription_stats(db: Session = Depends(get_db)):
    """إحصائيات القنوات والإعدادات"""
    service = ChannelService(db)
    channels = service.get_all_channels()
    settings = service.get_all_settings()
    return {
        "channels": {
            "total": len(channels),
            "required": len([c for c in channels if c.is_required]),
            "optional": len([c for c in channels if not c.is_required]),
        },
        "auto_post_settings": {
            "total": len(settings),
            "enabled": len([s for s in settings if s.auto_post]),
        }
    }
