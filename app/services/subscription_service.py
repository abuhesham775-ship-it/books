"""
Subscription Service - خدمة الاشتراكات وخطط العضوية
"""
from datetime import datetime, timedelta
from typing import List, Optional
from sqlalchemy.orm import Session
from app.models.subscription import SubscriptionPlan, UserSubscription, SubscriptionStatus
from app.models.user import User
from app.services.user_service import UserService
from app.services.points_service import PointsService


class SubscriptionService:
    """خدمة الاشتراكات"""

    def __init__(self, db: Session):
        self.db = db
        self.user_service = UserService(db)
        self.points_service = PointsService(db)

    def list_plans(self, active_only: bool = True) -> List[SubscriptionPlan]:
        query = self.db.query(SubscriptionPlan)
        if active_only:
            query = query.filter(SubscriptionPlan.is_active == True)
        return query.order_by(SubscriptionPlan.duration_days, SubscriptionPlan.price_points).all()

    def get_plan(self, plan_id: int) -> Optional[SubscriptionPlan]:
        return self.db.query(SubscriptionPlan).filter(SubscriptionPlan.id == plan_id).first()

    def create_plan(
        self,
        name: str,
        description: str = None,
        price_points: int = 0,
        duration_days: int = 30,
        benefits: dict = None,
        is_active: bool = True
    ) -> SubscriptionPlan:
        plan = SubscriptionPlan(
            name=name,
            description=description,
            price_points=price_points,
            duration_days=duration_days,
            benefits=benefits or {},
            is_active=is_active
        )
        self.db.add(plan)
        self.db.commit()
        self.db.refresh(plan)
        return plan

    def get_user_subscription(self, user_id: int) -> Optional[UserSubscription]:
        now = datetime.utcnow()
        subscription = self.db.query(UserSubscription).filter(
            UserSubscription.user_id == user_id,
            UserSubscription.expires_at > now,
            UserSubscription.status == SubscriptionStatus.ACTIVE
        ).order_by(UserSubscription.expires_at.desc()).first()
        return subscription

    def subscribe_user(
        self,
        user_id: int,
        plan_id: int,
        auto_renew: bool = False
    ) -> UserSubscription:
        plan = self.get_plan(plan_id)
        if not plan or not plan.is_active:
            raise ValueError("خطة الاشتراك غير متاحة")

        user = self.user_service.get_user_by_id(user_id)
        if not user:
            raise ValueError("المستخدم غير موجود")

        if plan.price_points > 0:
            success, msg = self.points_service.deduct_points(user_id, plan.price_points, f"اشتراك {plan.name}")
            if not success:
                raise ValueError(msg)

        expires_at = datetime.utcnow() + timedelta(days=plan.duration_days)
        subscription = UserSubscription(
            user_id=user_id,
            plan_id=plan.id,
            status=SubscriptionStatus.ACTIVE,
            started_at=datetime.utcnow(),
            expires_at=expires_at,
            auto_renew=auto_renew,
            metadata={"benefits": plan.benefits or {}}
        )
        self.db.add(subscription)
        self.db.commit()
        self.db.refresh(subscription)

        self.user_service.update_user(
            telegram_id=user.telegram_id,
            is_premium=True
        )
        return subscription

    def cancel_subscription(self, subscription_id: int) -> Optional[UserSubscription]:
        subscription = self.db.query(UserSubscription).filter(UserSubscription.id == subscription_id).first()
        if not subscription:
            return None
        subscription.status = SubscriptionStatus.CANCELLED
        self.db.commit()
        self.db.refresh(subscription)

        user = self.user_service.get_user_by_id(subscription.user_id)
        if user:
            self.user_service.update_user(user.telegram_id, is_premium=False)

        return subscription

    def refresh_subscriptions(self) -> int:
        now = datetime.utcnow()
        expired = self.db.query(UserSubscription).filter(
            UserSubscription.expires_at <= now,
            UserSubscription.status == SubscriptionStatus.ACTIVE
        ).all()
        count = 0
        for subscription in expired:
            subscription.status = SubscriptionStatus.EXPIRED
            count += 1
            user = self.user_service.get_user_by_id(subscription.user_id)
            if user:
                self.user_service.update_user(user.telegram_id, is_premium=False)
        self.db.commit()
        return count

    def is_user_premium(self, user_id: int) -> bool:
        subscription = self.get_user_subscription(user_id)
        return subscription is not None and subscription.is_active_subscription()
