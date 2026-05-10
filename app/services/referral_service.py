"""
Referral System Service - خدمة نظام الإحالة المتعدد المستويات
"""
from typing import List, Optional, Tuple, Dict
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import desc, func
from app.models.referral_system import (
    Referral, ReferralSettings, ReferralEarning, ReferralBadge,
    UserReferralBadge, ReferralLink, ReferralEvent,
    ReferralLevel, ReferralStatus
)
from app.models.user import User
from app.models.points import UserPoints, PointsTransaction, TransactionType
from config.settings import get_settings

settings = get_settings()


class ReferralService:
    """خدمة نظام الإحالة المتعدد المستويات"""

    def __init__(self, db: Session):
        self.db = db
        self._settings = self._get_or_create_settings()

    def _get_or_create_settings(self) -> ReferralSettings:
        """الحصول على إعدادات الإحالة أو إنشاؤها"""
        settings = self.db.query(ReferralSettings).first()
        if not settings:
            settings = ReferralSettings()
            self.db.add(settings)
            self.db.commit()
            self.db.refresh(settings)
        return settings

    # ==========================================
    # الإحالات الأساسية
    # ==========================================

    def create_referral(
        self,
        referrer_id: int,
        referred_telegram_id: int,
        referral_code: str
    ) -> Referral:
        """إنشاء إحالة جديدة"""
        # التحقق من وجود الإحالة مسبقاً
        existing = self.db.query(Referral).filter(
            Referral.referrer_id == referrer_id,
            Referral.referred_telegram_id == referred_telegram_id
        ).first()

        if existing:
            return existing

        referral = Referral(
            referrer_id=referrer_id,
            referred_telegram_id=referred_telegram_id,
            referral_code=referral_code,
            level=ReferralLevel.LEVEL_1
        )

        self.db.add(referral)
        self.db.commit()
        self.db.refresh(referral)

        # تسجيل الحدث
        self.record_event(
            user_id=referrer_id,
            event_type="signup",
            referral_id=referral.id,
            metadata={"referred_id": referred_telegram_id}
        )

        return referral

    def activate_referral(
        self,
        referred_telegram_id: int,
        referred_user_id: int
    ) -> Optional[Referral]:
        """تفعيل إحالة عند تسجيل المستخدم"""
        referral = self.db.query(Referral).filter(
            Referral.referred_telegram_id == referred_telegram_id,
            Referral.status == ReferralStatus.PENDING
        ).first()

        if not referral:
            return None

        # تحديث حالة الإحالة
        referral.referred_id = referred_user_id
        referral.status = ReferralStatus.ACTIVE
        referral.activated_at = datetime.utcnow()

        # منح المكافأة المباشرة
        bonus = self._settings.level_1_direct_bonus
        self._add_points(referral.referrer_id, bonus, "إحالة صديق جديد")

        referral.direct_bonus = bonus

        # تحديث إحصائيات المحيل
        referral.last_activity_at = datetime.utcnow()

        self.db.commit()
        self.db.refresh(referral)

        # منح الشارات إذا استوفى الشروط
        self.check_and_award_badges(referral.referrer_id)

        # معالجة سلسلة الإحالات (مستويات أعلى)
        self._process_referral_chain(referral)

        return referral

    def _process_referral_chain(self, referral: Referral) -> None:
        """معالجة سلسلة الإحالات للمستويات الأعلى"""
        referrer = self.db.query(User).get(referral.referrer_id)

        if not referrer or not referrer.referred_by:
            return

        # البحث عن المحيل الأصلي
        original_referrer = self.db.query(User).filter(
            User.telegram_id == referrer.referred_by
        ).first()

        if not original_referrer:
            return

        # إنشاء إحالة للمستوى الثاني
        level2_referral = Referral(
            referrer_id=original_referrer.id,
            referred_id=referral.referred_id,
            referral_code=referral.referral_code,
            level=ReferralLevel.LEVEL_2,
            original_referrer_id=original_referrer.id
        )
        self.db.add(level2_referral)

        # منح نقاط المستوى الثاني
        bonus = self._settings.level_2_direct_bonus
        self._add_points(original_referrer.id, bonus, "إحالة من المستوى الثاني")

        self.db.commit()

    def _add_points(self, user_id: int, amount: int, description: str) -> None:
        """إضافة نقاط للمستخدم"""
        points = self.db.query(UserPoints).filter(
            UserPoints.user_id == user_id
        ).first()

        if not points:
            points = UserPoints(user_id=user_id, total_points=0, current_balance=0)
            self.db.add(points)
            self.db.flush()

        points.total_points += amount
        points.current_balance += amount
        points.lifetime_earned += amount

        transaction = PointsTransaction(
            user_id=points.id,
            amount=amount,
            transaction_type=TransactionType.REFERRAL,
            description=description
        )
        self.db.add(transaction)
        self.db.commit()

    # ==========================================
    # أرباح الإحالة
    # ==========================================

    def record_royalty(
        self,
        user_id: int,
        source_type: str,
        source_id: int,
        source_amount: int
    ) -> None:
        """تسجيل أرباح الإحالة عند تحميل أو شراء"""
        # البحث عن الإحالات النشطة للمستخدم
        referrals = self.db.query(Referral).filter(
            Referral.referred_id == user_id,
            Referral.status == ReferralStatus.ACTIVE
        ).all()

        for referral in referrals:
            # حساب نسبة الأرباح
            if referral.level == ReferralLevel.LEVEL_1:
                royalty_percent = self._settings.level_1_royalty_percent
            elif referral.level == ReferralLevel.LEVEL_2:
                royalty_percent = self._settings.level_2_royalty_percent
            else:
                royalty_percent = self._settings.level_3_royalty_percent

            royalty_amount = int(source_amount * royalty_percent / 100)

            if royalty_amount > 0:
                # تسجيل الأرباح
                earning = ReferralEarning(
                    referral_id=referral.id,
                    user_id=referral.referrer_id,
                    source_type=source_type,
                    source_id=source_id,
                    amount=royalty_amount,
                    royalty_percent=royalty_percent
                )
                self.db.add(earning)

                # إضافة النقاط
                self._add_points(
                    referral.referrer_id,
                    royalty_amount,
                    f"أرباح من نشاط صديق - {source_type}"
                )

                # تحديث إحصائيات الإحالة
                referral.royalty_earnings += royalty_amount
                referral.total_referred_downloads += 1

        self.db.commit()

    def get_referral_earnings(self, user_id: int) -> dict:
        """الحصول على أرباح الإحالة"""
        earnings = self.db.query(ReferralEarning).filter(
            ReferralEarning.user_id == user_id,
            ReferralEarning.is_paid == False
        ).all()

        total_pending = sum(e.amount for e in earnings)
        total_paid = self.db.query(func.sum(ReferralEarning.amount)).filter(
            ReferralEarning.user_id == user_id,
            ReferralEarning.is_paid == True
        ).scalar() or 0

        return {
            "pending": total_pending,
            "total_earned": total_paid + total_pending,
            "total_paid": total_paid,
            "transactions": len(earnings)
        }

    # ==========================================
    # الشارات
    # ==========================================

    def get_all_badges(self) -> List[ReferralBadge]:
        """الحصول على جميع شارات الإحالة"""
        return self.db.query(ReferralBadge).all()

    def check_and_award_badges(self, user_id: int) -> List[ReferralBadge]:
        """التحقق ومنح الشارات المكتسبة"""
        # عدد الإحالات النشطة
        active_referrals = self.db.query(Referral).filter(
            Referral.referrer_id == user_id,
            Referral.status == ReferralStatus.ACTIVE
        ).count()

        # الشارات المستحقة
        earned_badges = []
        badges = self.db.query(ReferralBadge).filter(
            ReferralBadge.required_referrals <= active_referrals
        ).all()

        for badge in badges:
            # التحقق من عدم وجود الشارة مسبقاً
            existing = self.db.query(UserReferralBadge).filter(
                UserReferralBadge.user_id == user_id,
                UserReferralBadge.badge_id == badge.id
            ).first()

            if not existing:
                user_badge = UserReferralBadge(
                    user_id=user_id,
                    badge_id=badge.id
                )
                self.db.add(user_badge)
                earned_badges.append(badge)

        if earned_badges:
            self.db.commit()

        return earned_badges

    def get_user_badges(self, user_id: int) -> List[UserReferralBadge]:
        """شارات المستخدم المكتسبة"""
        return self.db.query(UserReferralBadge).filter(
            UserReferralBadge.user_id == user_id
        ).all()

    # ==========================================
    # إحصائيات الإحالة
    # ==========================================

    def get_referral_stats(self, user_id: int) -> dict:
        """إحصائيات الإحالة للمستخدم"""
        # الإحالات المباشرة
        direct_referrals = self.db.query(Referral).filter(
            Referral.referrer_id == user_id,
            Referral.level == ReferralLevel.LEVEL_1
        ).all()

        active_direct = len([r for r in direct_referrals if r.status == ReferralStatus.ACTIVE])

        # الإحالات من المستوى الثاني
        level2_count = self.db.query(Referral).filter(
            Referral.original_referrer_id == user_id,
            Referral.level == ReferralLevel.LEVEL_2,
            Referral.status == ReferralStatus.ACTIVE
        ).count()

        # أرباح الإحالة
        total_earnings = self.db.query(func.sum(Referral.direct_bonus)).filter(
            Referral.referrer_id == user_id
        ).scalar() or 0

        royalty_total = self.db.query(func.sum(ReferralEarning.amount)).filter(
            ReferralEarning.user_id == user_id
        ).scalar() or 0

        return {
            "direct_referrals": len(direct_referrals),
            "active_direct": active_direct,
            "level2_referrals": level2_count,
            "total_direct_bonus": total_earnings,
            "total_royalty": royalty_total,
            "total_earnings": total_earnings + royalty_total
        }

    def get_top_referrers(self, limit: int = 10) -> List[dict]:
        """أفضل المحيلين"""
        results = self.db.query(
            User.id,
            User.telegram_id,
            User.first_name,
            func.count(Referral.id).label('count')
        ).join(
            Referral, Referral.referrer_id == User.id
        ).filter(
            Referral.status == ReferralStatus.ACTIVE
        ).group_by(
            User.id, User.telegram_id, User.first_name
        ).order_by(
            desc('count')
        ).limit(limit).all()

        return [
            {
                "user_id": r.id,
                "telegram_id": r.telegram_id,
                "name": r.first_name,
                "referrals": r.count
            }
            for r in results
        ]

    # ==========================================
    # روابط الإحالة
    # ==========================================

    def get_or_create_referral_link(self, user_id: int) -> ReferralLink:
        """الحصول على رابط الإحالة أو إنشاؤه"""
        link = self.db.query(ReferralLink).filter(
            ReferralLink.user_id == user_id
        ).first()

        if not link:
            # إنشاء كود مخصص
            user = self.db.query(User).get(user_id)
            custom_code = f"REF{user.telegram_id}" if user else f"REF{user_id}"

            link = ReferralLink(
                user_id=user_id,
                custom_code=custom_code,
                telegram_link=f"https://t.me/YOUR_BOT?start={custom_code}"
            )
            self.db.add(link)
            self.db.commit()
            self.db.refresh(link)

        return link

    def track_link_click(self, user_id: int) -> None:
        """تتبع نقر على رابط الإحالة"""
        link = self.db.query(ReferralLink).filter(
            ReferralLink.user_id == user_id
        ).first()

        if link:
            link.total_clicks += 1
            self.db.commit()

    # ==========================================
    # الأحداث
    # ==========================================

    def record_event(
        self,
        user_id: int,
        event_type: str,
        referral_id: int = None,
        points_earned: int = 0,
        metadata: dict = None
    ) -> ReferralEvent:
        """تسجيل حدث إحالة"""
        event = ReferralEvent(
            user_id=user_id,
            event_type=event_type,
            referral_id=referral_id,
            points_earned=points_earned,
            metadata=metadata
        )
        self.db.add(event)
        self.db.commit()
        self.db.refresh(event)
        return event

    def get_referral_history(self, user_id: int, limit: int = 20) -> List[dict]:
        """سجل الإحالات للمستخدم"""
        referrals = self.db.query(Referral).filter(
            Referral.referrer_id == user_id
        ).order_by(desc(Referral.created_at)).limit(limit).all()

        history = []
        for ref in referrals:
            history.append({
                "id": ref.id,
                "level": ref.level.value,
                "status": ref.status.value,
                "activated_at": ref.activated_at,
                "direct_bonus": ref.direct_bonus,
                "royalty_earnings": ref.royalty_earnings,
                "created_at": ref.created_at
            })

        return history
