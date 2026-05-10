"""
Social Models - نماذج النظام الاجتماعي والمتابعة
"""
import enum
from datetime import datetime
from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Text, JSON, Enum
from sqlalchemy.orm import relationship
from app.database import Base


class ActivityType(enum.Enum):
    FOLLOW = "follow"
    BOOK_DOWNLOAD = "book_download"
    REVIEW_POSTED = "review_posted"
    CHALLENGE_COMPLETED = "challenge_completed"
    ACHIEVEMENT_UNLOCKED = "achievement_unlocked"
    MARKET_PURCHASE = "market_purchase"
    MARKET_SALE = "market_sale"
    GENERIC = "generic"


class FollowRelationship(Base):
    """علاقة المتابعة"""
    __tablename__ = "follow_relationships"

    id = Column(Integer, primary_key=True, index=True)
    follower_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    following_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    is_active = Column(Boolean, default=True)

    follower = relationship("User", foreign_keys=[follower_id], backref="following")
    following = relationship("User", foreign_keys=[following_id], backref="followers")

    def __repr__(self):
        return f"<Follow follower={self.follower_id} following={self.following_id}>"


class ActivityFeed(Base):
    """سجل الأنشطة للمجتمع"""
    __tablename__ = "activity_feed"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    actor_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    activity_type = Column(Enum(ActivityType), default=ActivityType.GENERIC)
    target_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    target_book_id = Column(Integer, ForeignKey("books.id"), nullable=True)
    description = Column(Text, nullable=True)
    extra_data = Column(JSON, nullable=True)   # تم تغيير الاسم من metadata إلى extra_data
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", foreign_keys=[user_id], backref="activity_entries")
    actor = relationship("User", foreign_keys=[actor_id], backref="actions")

    def __repr__(self):
        return f"<ActivityFeed user={self.user_id} type={self.activity_type}>"
