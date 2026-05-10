"""
Channel Settings Models - نماذج منفصلة للاشتراك الإجباري وإعدادات النشر
"""
from datetime import datetime
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text
from app.database import Base


class ForceJoinChannel(Base):
    """نموذج قنوات الاشتراك الإجباري"""
    __tablename__ = "force_join_channels"

   
    id = Column(Integer, primary_key=True, index=True)
    channel_id = Column(String(100), unique=True, nullable=False, index=True)
    channel_name = Column(String(255), nullable=True)
    channel_link = Column(String(500), nullable=True)
    is_required = Column(Boolean, default=True)
    auto_post = Column(Boolean, default=False)
    post_template = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<ForceJoinChannel {self.channel_id}>"


class ChannelSetting(Base):
    """نموذج إعدادات النشر التلقائي"""
    __tablename__ = "channel_post_settings"

    id = Column(Integer, primary_key=True, index=True)
    channel_id = Column(String(100), unique=True, nullable=False, index=True)
    channel_name = Column(String(255), nullable=True)
    auto_post = Column(Boolean, default=False)
    post_template = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<ChannelSetting {self.channel_id}>"
