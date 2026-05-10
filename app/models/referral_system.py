"""
Referral System Models - نماذج نظام الإحالة المتعدد المستويات
"""
import enum
from datetime import datetime
from sqlalchemy import Column, Integer, String, Enum, DateTime, Boolean, Float, ForeignKey, JSON
from sqlalchemy.orm import relationship
from app.database import Base


class ReferralLevel(enum.Enum):
    """مستوى الإحالة"""
    LEVEL_1 = 1  # أصدقاء مباشرة
    LEVEL_2 = 2  # أصدقاء الأصدقاء
    LEVEL_3 = 3  # المستوى الثالث


class ReferralStatus(enum.Enum):
    """حالة الإحالة"""
    PENDING = "pending"      # بانتظار التسجيل
    ACTIVE = "active"       # مكتملة ومفعالة
    SUSPENDED = "suspended" # معلقة
    CANCELLED = "cancelled" # ملغاة


class Referral(Base):
    """نموذج الإحالة - التعريف الموحد"""
    __tablename__ = "referrals"
    __table_args__ = {'extend_existing': True}  # 👈 أضف هذا السطر

    id = Column(Integer, primary_key=True, index=True)
    # ... باقي الكود كما هو

    # معلومات المحيل
    referrer_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    referral_code = Column(String(20), nullable=False)

    # معلومات المدعو
    referred_id = Column(Integer, ForeignKey("users.id"), nullable=True)  # بعد التسجيل
    referred_telegram_id = Column(Integer, nullable=True)  # مؤقت لحين التسجيل

    # مستوى الإحالة
    level = Column(Enum(ReferralLevel), default=ReferralLevel.LEVEL_1)

    # معلومات الإحالة الأصلية (لمعرفة سلسلة الإحالات)
    original_referrer_id = Column(Integer, ForeignKey("users.id"), nullable=True)  # المحيل الأصلي

    # الحالة والمكافآت
    status = Column(Enum(ReferralStatus), default=ReferralStatus.PENDING)
    is_completed = Column(Boolean, default=False)  # مدمج من النموذج الآخر

    # المكافآت المكتسبة
    direct_bonus = Column(Integer, default=0)  # نقاط مباشرة للمحيل
    royalty_earnings = Column(Integer, default=0)  # أرباح من تحميلات الصديق
    points_earned = Column(Integer, default=0)  # مدمج من النموذج الآخر

    # التواريخ
    created_at = Column(DateTime, default=datetime.utcnow)
    activated_at = Column(DateTime, nullable=True)  # عندما يكمل الصديق التسجيل
    completed_at = Column(DateTime, nullable=True)  # مدمج من النموذج الآخر
    last_activity_at = Column(DateTime, nullable=True)

    # تتبع النشاط
    total_referred_purchases = Column(Integer, default=0)
    total_referred_downloads = Column(Integer, default=0)

    # Relationships
    referrer = relationship("User", foreign_keys=[referrer_id], backref="referrals_made")
    referred = relationship("User", foreign_keys=[referred_id], backref="referred_by_user")
    original_referrer = relationship("User", foreign_keys=[original_referrer_id])

    def __repr__(self):
        return f"<Referral {self.id} referrer={self.referrer_id}>"

class ReferralCode(Base):
    """نموذج كود الإحالة"""
    __tablename__ = "referral_codes"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    code = Column(String(20), unique=True, nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=True)
    is_active = Column(Boolean, default=True)
    uses_count = Column(Integer, default=0)
    max_uses = Column(Integer, nullable=True)

    def __repr__(self):
        return f"<ReferralCode {self.code}>"
class ReferralSettings(Base):
    """إعدادات برنامج الإحالة"""
    __tablename__ = "referral_settings"

    id = Column(Integer, primary_key=True, index=True)

    # مكافآت المستوى الأول
    level_1_direct_bonus = Column(Integer, default=50)
    level_1_royalty_percent = Column(Float, default=10.0)  # % من تحميلات الصديق

    # مكافآت المستوى الثاني
    level_2_direct_bonus = Column(Integer, default=20)
    level_2_royalty_percent = Column(Float, default=5.0)

    # مكافآت المستوى الثالث
    level_3_direct_bonus = Column(Integer, default=10)
    level_3_royalty_percent = Column(Float, default=2.0)

    # حدود
    max_referral_chain = Column(Integer, default=3)
    min_payout = Column(Integer, default=100)  # الحد الأدنى للسحب

    # إعدادات عامة
    is_active = Column(Boolean, default=True)
    allow_multiplier_events = Column(Boolean, default=True)

    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<ReferralSettings id={self.id}>"


class ReferralEarning(Base):
    """أرباح الإحالة"""
    __tablename__ = "referral_earnings"

    id = Column(Integer, primary_key=True, index=True)
    referral_id = Column(Integer, ForeignKey("referrals.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)  # من يستلم الأرباح

    # تفاصيل الأرباح
    source_type = Column(String(50), nullable=False)  # download, purchase, review
    source_id = Column(Integer, nullable=True)  # معرف المصدر
    amount = Column(Integer, nullable=False)
    royalty_percent = Column(Float, nullable=True)

    # الحالة
    is_paid = Column(Boolean, default=False)
    paid_at = Column(DateTime, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    referral = relationship("Referral", backref="earnings")
    user = relationship("User", backref="referral_earnings")

    def __repr__(self):
        return f"<ReferralEarning {self.id} amount={self.amount}>"


class ReferralBadge(Base):
    """شارات المكافآت الخاصة"""
    __tablename__ = "referral_badges"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False, unique=True)
    name_ar = Column(String(100), nullable=True)
    description = Column(String(500), nullable=True)

    # المتطلبات
    required_referrals = Column(Integer, nullable=False)
    badge_type = Column(String(50), default="bronze")  # bronze, silver, gold, platinum

    # المميزات
    bonus_multiplier = Column(Float, default=1.0)  # مضاعف النقاط
    vip_days = Column(Integer, default=0)  # أيام VIP مجانية
    exclusive_badge = Column(Boolean, default=False)

    icon = Column(String(100), nullable=True)  # رابط الأيقونة

    created_at = Column(DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<ReferralBadge {self.name}>"


class UserReferralBadge(Base):
    """شارات المستخدم المكتسبة"""
    __tablename__ = "user_referral_badges"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    badge_id = Column(Integer, ForeignKey("referral_badges.id"), nullable=False)

    earned_at = Column(DateTime, default=datetime.utcnow)
    is_displayed = Column(Boolean, default=True)

    # Relationships
    user = relationship("User", backref="referral_badges")
    badge = relationship("ReferralBadge", backref="users_earned")

    def __repr__(self):
        return f"<UserReferralBadge user={self.user_id} badge={self.badge_id}>"


class ReferralLink(Base):
    """روابط الإحالة المخصصة"""
    __tablename__ = "referral_links"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    custom_code = Column(String(20), nullable=True, unique=True)

    # تتبع الروابط
    total_clicks = Column(Integer, default=0)
    total_signups = Column(Integer, default=0)
    conversion_rate = Column(Float, default=0.0)

    # الروابط المخصصة
    telegram_link = Column(String(500), nullable=True)
    custom_landing_url = Column(String(500), nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    user = relationship("User", backref="referral_links")

    def __repr__(self):
        return f"<ReferralLink user={self.user_id}>"


class ReferralEvent(Base):
    """أحداث برنامج الإحالة"""
    __tablename__ = "referral_events"

    id = Column(Integer, primary_key=True, index=True)

    event_type = Column(String(50), nullable=False)  # signup, first_download, milestone, badge_earned
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    # تفاصيل الحدث
    referral_id = Column(Integer, ForeignKey("referrals.id"), nullable=True)
    points_earned = Column(Integer, default=0)

    # البيانات الإضافية
    extra_data = Column(JSON, nullable=True)  # تم تغيير الاسم من metadata إلى extra_data

    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    user = relationship("User", backref="referral_events")
    referral = relationship("Referral", backref="events")

    def __repr__(self):
        return f"<ReferralEvent {self.event_type} user={self.user_id}>"
