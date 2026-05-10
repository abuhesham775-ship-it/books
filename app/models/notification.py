"""
Notification Models - نماذج الإشعارات (بسيطة + متقدمة)
"""
import enum
from datetime import datetime
from sqlalchemy import Column, Integer, String, Enum, DateTime, Boolean, Text, ForeignKey, JSON
from sqlalchemy.orm import relationship
from app.database import Base


# ============ النموذج البسيط (الأساسي) ============
class NotificationType(enum.Enum):
    BOOK_ADDED = "book_added"
    BOOK_APPROVED = "book_approved"
    BOOK_REJECTED = "book_rejected"
    POINTS_EARNED = "points_earned"
    POINTS_DEDUCTED = "points_deducted"
    REFERRAL_BONUS = "referral_bonus"
    COUPON_APPLIED = "coupon_applied"
    PACK_PURCHASED = "pack_purchased"
    SYSTEM = "system"


class Notification(Base):
    __tablename__ = "notifications"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    notification_type = Column(Enum(NotificationType), nullable=False)
    title = Column(String(255), nullable=False)
    message = Column(Text, nullable=False)
    is_read = Column(Boolean, default=False)
    extra_data = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    sent_at = Column(DateTime, nullable=True)
    failed_at = Column(DateTime, nullable=True)
    error_message = Column(Text, nullable=True)

    user = relationship("User", backref="user_notifications")

    def __repr__(self):
        return f"<Notification {self.id} to {self.user_id}>"


# ============ النموذج المتقدم (الإشعارات الذكية) ============
class SmartNotificationType(enum.Enum):
    NEW_BOOK = "new_book"
    BOOK_UPDATE = "book_update"
    AUTHOR_NEW_BOOK = "author_new_book"
    CATEGORY_NEW_BOOK = "category_new_book"
    PRICE_DROP = "price_drop"
    WISHLIST_AVAILABLE = "wishlist_available"
    AUCTION_ENDING = "auction_ending"
    OUTBID = "outbid"
    NEW_REVIEW = "new_review"
    NEW_FOLLOWER = "new_follower"
    FRIEND_ACTIVITY = "friend_activity"
    CHALLENGE_INVITE = "challenge_invite"
    POINTS_EARNED_ADV = "points_earned"
    POINTS_EXPIRED = "points_expired"
    LEVEL_UP = "level_up"
    REFERRAL_SIGNUP = "referral_signup"
    CHALLENGE_AVAILABLE = "challenge_available"
    CHALLENGE_COMPLETED = "challenge_completed"
    CHALLENGE_EXPIRED = "challenge_expired"
    BADGE_EARNED = "badge_earned"
    STREAK_BONUS = "streak_bonus"
    SYSTEM_ANNOUNCEMENT = "system_announcement"
    MAINTENANCE = "maintenance"
    POLICY_UPDATE = "policy_update"
    DIRECT_MESSAGE = "direct_message"
    REPLY = "reply"
    MENTION = "mention"


class NotificationPriority(enum.Enum):
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"


class NotificationStatus(enum.Enum):
    PENDING = "pending"
    SENT = "sent"
    DELIVERED = "delivered"
    READ = "read"
    FAILED = "failed"
    DISMISSED = "dismissed"


class SmartNotification(Base):
    __tablename__ = "smart_notifications"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    notification_type = Column(Enum(SmartNotificationType), nullable=False)
    priority = Column(Enum(NotificationPriority), default=NotificationPriority.NORMAL)
    title = Column(String(200), nullable=False)
    title_ar = Column(String(200), nullable=True)
    message = Column(Text, nullable=False)
    message_ar = Column(Text, nullable=True)
    related_type = Column(String(50), nullable=True)
    related_id = Column(Integer, nullable=True)
    action_buttons = Column(JSON, nullable=True)
    action_url = Column(String(500), nullable=True)
    image_url = Column(String(500), nullable=True)
    thumbnail_url = Column(String(500), nullable=True)
    status = Column(Enum(NotificationStatus), default=NotificationStatus.PENDING)
    is_read = Column(Boolean, default=False)
    is_dismissed = Column(Boolean, default=False)
    scheduled_at = Column(DateTime, nullable=True)
    sent_at = Column(DateTime, nullable=True)
    read_at = Column(DateTime, nullable=True)
    failed_at = Column(DateTime, nullable=True)
    failure_reason = Column(Text, nullable=True)
    retry_count = Column(Integer, default=0)
    batch_id = Column(String(100), nullable=True)
    batch_count = Column(Integer, default=1)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="smart_notifications")
    preferences = relationship("NotificationPreference", back_populates="notification", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<SmartNotification {self.id} type={self.notification_type}>"


class UserNotificationSettings(Base):
    __tablename__ = "user_notification_settings"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, unique=True)
    new_book = Column(Boolean, default=True)
    author_new_book = Column(Boolean, default=True)
    category_new_book = Column(Boolean, default=False)
    price_alerts = Column(Boolean, default=True)
    wishlist_alerts = Column(Boolean, default=True)
    auction_alerts = Column(Boolean, default=True)
    social_notifications = Column(Boolean, default=True)
    challenge_notifications = Column(Boolean, default=True)
    points_notifications = Column(Boolean, default=True)
    level_notifications = Column(Boolean, default=True)
    system_notifications = Column(Boolean, default=True)
    direct_messages = Column(Boolean, default=True)
    quiet_hours_start = Column(String(10), default="22:00")
    quiet_hours_end = Column(String(10), default="08:00")
    timezone = Column(String(50), default="UTC")
    batch_notifications = Column(Boolean, default=True)
    batch_interval_hours = Column(Integer, default=24)
    email_notifications = Column(Boolean, default=False)
    push_notifications = Column(Boolean, default=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = relationship("User", backref="notification_settings")

    def __repr__(self):
        return f"<UserNotificationSettings user={self.user_id}>"


class NotificationPreference(Base):
    __tablename__ = "notification_preferences"
    id = Column(Integer, primary_key=True, index=True)
    notification_id = Column(Integer, ForeignKey("smart_notifications.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    is_enabled = Column(Boolean, default=True)
    last_interaction = Column(DateTime, nullable=True)

    notification = relationship("SmartNotification", back_populates="preferences")
    user = relationship("User")

    def __repr__(self):
        return f"<NotificationPreference notification={self.notification_id}>"


class NotificationTemplate(Base):
    __tablename__ = "notification_templates"
    id = Column(Integer, primary_key=True, index=True)
    template_code = Column(String(100), nullable=False, unique=True)
    notification_type = Column(Enum(SmartNotificationType), nullable=False)
    title_template = Column(String(200), nullable=False)
    title_template_ar = Column(String(200), nullable=True)
    message_template = Column(Text, nullable=False)
    message_template_ar = Column(Text, nullable=True)
    icon = Column(String(100), nullable=True)
    default_image_url = Column(String(500), nullable=True)
    default_buttons = Column(JSON, nullable=True)
    is_active = Column(Boolean, default=True)
    available_variables = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<NotificationTemplate {self.template_code}>"


class NotificationSchedule(Base):
    __tablename__ = "notification_schedules"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False)
    notification_type = Column(Enum(SmartNotificationType), nullable=False)
    target_criteria = Column(JSON, nullable=True)
    scheduled_at = Column(DateTime, nullable=True)
    repeat_interval = Column(String(50), nullable=True)
    repeat_count = Column(Integer, default=1)
    data = Column(JSON, nullable=True)
    status = Column(String(20), default="pending")
    sent_count = Column(Integer, default=0)
    failed_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<NotificationSchedule {self.name}>"


class NotificationAnalytics(Base):
    __tablename__ = "notification_analytics"
    id = Column(Integer, primary_key=True, index=True)
    notification_id = Column(Integer, ForeignKey("smart_notifications.id"), nullable=False)
    delivered_at = Column(DateTime, nullable=True)
    read_at = Column(DateTime, nullable=True)
    clicked_at = Column(DateTime, nullable=True)
    action_taken_at = Column(DateTime, nullable=True)
    time_to_deliver = Column(Integer, nullable=True)
    time_to_read = Column(Integer, nullable=True)
    time_to_action = Column(Integer, nullable=True)
    action_type = Column(String(50), nullable=True)
    action_data = Column(JSON, nullable=True)

    notification = relationship("SmartNotification", backref="analytics")

    def __repr__(self):
        return f"<NotificationAnalytics notification={self.notification_id}>"
