"""
Subscription Models - نماذج الاشتراكات وخطط العضوية
"""
import enum
from datetime import datetime, timedelta
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Float, ForeignKey, JSON, Enum
from sqlalchemy.orm import relationship
from app.database import Base


class SubscriptionStatus(enum.Enum):
    ACTIVE = "active"
    EXPIRED = "expired"
    CANCELLED = "cancelled"
    PENDING = "pending"


class SubscriptionPlan(Base):
    """خطة اشتراك"""
    __tablename__ = "subscription_plans"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(120), nullable=False, unique=True)
    description = Column(String(500), nullable=True)
    price_points = Column(Integer, default=0)
    duration_days = Column(Integer, default=30)
    benefits = Column(JSON, nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    subscriptions = relationship("UserSubscription", back_populates="plan")

    def __repr__(self):
        return f"<SubscriptionPlan {self.name}>"


class UserSubscription(Base):
    """اشتراك المستخدم"""
    __tablename__ = "user_subscriptions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    plan_id = Column(Integer, ForeignKey("subscription_plans.id"), nullable=False)
    status = Column(Enum(SubscriptionStatus), default=SubscriptionStatus.ACTIVE)
    started_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=False)
    auto_renew = Column(Boolean, default=False)
    metadata = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    plan = relationship("SubscriptionPlan", back_populates="subscriptions")

    def is_active_subscription(self) -> bool:
        return self.status == SubscriptionStatus.ACTIVE and self.expires_at > datetime.utcnow()

    def remaining_days(self) -> int:
        if not self.expires_at:
            return 0
        diff = self.expires_at - datetime.utcnow()
        return max(int(diff.total_seconds() // 86400), 0)

    def __repr__(self):
        return f"<UserSubscription user={self.user_id} plan={self.plan_id} status={self.status}>"
