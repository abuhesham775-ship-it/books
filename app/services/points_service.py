"""
Points Service - خدمة نظام النقاط
"""
from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import desc
from app.models.points import UserPoints, PointsTransaction, TransactionType
from app.models.user import User
from config.settings import get_settings

settings = get_settings()


class PointsService:
    """خدمة نظام النقاط"""

    def __init__(self, db: Session):
        self.db = db

    def get_or_create_user_points(self, user_id: int) -> UserPoints:
        """الحصول على نقاط المستخدم أو إنشاؤها"""
        user_points = self.db.query(UserPoints).filter(
            UserPoints.user_id == user_id
        ).first()

        if user_points:
            return user_points

        user_points = UserPoints(
            user_id=user_id,
            total_points=0,
            current_balance=0
        )
        self.db.add(user_points)
        self.db.commit()
        self.db.refresh(user_points)
        return user_points

    def get_user_points(self, user_id: int) -> Optional[UserPoints]:
        """الحصول على نقاط مستخدم"""
        return self.db.query(UserPoints).filter(
            UserPoints.user_id == user_id
        ).first()

    def add_points(
        self,
        user_id: int,
        amount: int,
        transaction_type: TransactionType,
        description: Optional[str] = None,
        reference_id: Optional[str] = None
    ) -> Optional[UserPoints]:
        """إضافة نقاط للمستخدم"""
        user_points = self.get_or_create_user_points(user_id)

        user_points.total_points += amount
        user_points.current_balance += amount
        user_points.lifetime_earned += amount

        # تسجيل المعاملة
        transaction = PointsTransaction(
            user_id=user_points.id,
            amount=amount,
            transaction_type=transaction_type,
            description=description,
            reference_id=reference_id
        )
        self.db.add(transaction)
        self.db.commit()
        self.db.refresh(user_points)
        return user_points

    def deduct_points(
        self,
        user_id: int,
        amount: int,
        description: Optional[str] = None
    ) -> tuple[bool, str]:
        """خصم نقاط من المستخدم"""
        user_points = self.get_or_create_user_points(user_id)

        if user_points.current_balance < amount:
            return False, "النقاط غير كافية"

        user_points.current_balance -= amount

        # تسجيل المعاملة
        transaction = PointsTransaction(
            user_id=user_points.id,
            amount=-amount,
            transaction_type=TransactionType.DEDUCTION,
            description=description
        )
        self.db.add(transaction)
        self.db.commit()
        self.db.refresh(user_points)
        return True, "تم الخصم بنجاح"

    def transfer_points(
        self,
        from_user_id: int,
        to_user_id: int,
        amount: int
    ) -> tuple[bool, str]:
        """تحويل نقاط بين مستخدمين"""
        # خصم من المرسل
        success, msg = self.deduct_points(
            from_user_id,
            amount,
            f"تحويل نقاط للمستخدم {to_user_id}"
        )
        if not success:
            return False, msg

        # إضافة للمرسل إليه
        self.add_points(
            to_user_id,
            amount,
            TransactionType.GIFT,
            f"استلام نقاط من المستخدم {from_user_id}"
        )
        return True, "تم التحويل بنجاح"

    def get_transactions(
        self,
        user_id: int,
        limit: int = 50
    ) -> List[PointsTransaction]:
        """الحصول على سجل المعاملات"""
        user_points = self.get_user_points(user_id)
        if not user_points:
            return []

        return self.db.query(PointsTransaction).filter(
            PointsTransaction.user_id == user_points.id
        ).order_by(
            desc(PointsTransaction.created_at)
        ).limit(limit).all()

    def add_referral_bonus(self, user_id: int, referrer_id: int) -> bool:
        """إضافة مكافأة الإحالة"""
        points = settings.points_per_referral
        self.add_points(
            user_id,
            points,
            TransactionType.REFERRAL,
            f"مكافأة إحالة - جلب مستخدم جديد"
        )
        # مكافأة المحيل أيضاً
        self.add_points(
            referrer_id,
            points,
            TransactionType.REFERRAL,
            f"مكافأة إحالة - مستخدم جديد استخدم كودك"
        )
        return True

    def add_download_points(self, user_id: int, book_id: int) -> bool:
        """إضافة نقاط لتحميل كتاب"""
        points = settings.points_per_download
        self.add_points(
            user_id,
            points,
            TransactionType.DOWNLOAD,
            f"نقاط تحميل كتاب رقم {book_id}",
            str(book_id)
        )
        return True

    def add_review_points(self, user_id: int, review_id: int) -> bool:
        """إضافة نقاط لكتابة تقييم"""
        points = settings.points_per_review
        self.add_points(
            user_id,
            points,
            TransactionType.REVIEW,
            f"نقاط كتابة تقييم رقم {review_id}",
            str(review_id)
        )
        return True

    def use_coupon(self, user_id: int, coupon_code: str, value: int, coupon_type) -> tuple[bool, str]:
        """استخدام كوبون"""
        from app.models.coupon import CouponType

        if coupon_type == CouponType.POINTS:
            return self.add_points(
                user_id,
                value,
                TransactionType.COUPON,
                f"استخدام كوبون {coupon_code}"
            ), "تم استخدام الكوبون بنجاح"
        elif coupon_type == CouponType.PERCENTAGE:
            # تطبيق نسبة مئوية
            user_points = self.get_or_create_user_points(user_id)
            earned = int(user_points.current_balance * value / 100)
            return self.add_points(
                user_id,
                earned,
                TransactionType.COUPON,
                f"استخدام كوبون {coupon_code} - {value}%"
            ), f"تم إضافة {earned} نقطة بنجاح"
        elif coupon_type == CouponType.FIXED:
            return self.add_points(
                user_id,
                value,
                TransactionType.COUPON,
                f"استخدام كوبون {coupon_code}"
            ), "تم استخدام الكوبون بنجاح"

        return False, "نوع الكوبون غير صالح"

    def get_leaderboard(self, limit: int = 10) -> List[UserPoints]:
        """لوحة المتصدرين"""
        return self.db.query(UserPoints).order_by(
            desc(UserPoints.current_balance)
        ).limit(limit).all()

    def can_download(self, user_id: int) -> tuple[bool, str]:
        """التحقق إذا كان المستخدم يمكنه التحميل"""
        user_points = self.get_user_points(user_id)
        if not user_points:
            return True, ""  # مستخدم جديد

        if user_points.current_balance < settings.points_to_deduct:
            return False, f"تحتاج على الأقل {settings.points_to_deduct} نقطة للتحميل"

        return True, ""
