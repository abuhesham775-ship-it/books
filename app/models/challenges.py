"""
Challenges & Achievements Models - نماذج التحديات والإنجازات
"""
import enum
from datetime import datetime
from sqlalchemy import Column, Integer, String, Enum, DateTime, Boolean, Float, ForeignKey, JSON, Text
from sqlalchemy.orm import relationship
from app.database import Base


class ChallengeCategory(enum.Enum):
    """فئة التحدي"""
    READING = "reading"           # تحديات القراءة
    ENGAGEMENT = "engagement"     # التفاعل
    SOCIAL = "social"            # اجتماعي
    COLLECTION = "collection"     # جمع الكتب
    LEARNING = "learning"        # التعلم


class ChallengeFrequency(enum.Enum):
    """تكرار التحدي"""
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    ONE_TIME = "one_time"
    LIMITED = "limited"


class ChallengeStatus(enum.Enum):
    """حالة التحدي للمستخدم"""
    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    EXPIRED = "expired"
    REWARDED = "rewarded"


class Challenge(Base):
    """التحدي"""
    __tablename__ = "challenges"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False)
    name_ar = Column(String(200), nullable=True)
    description = Column(Text, nullable=True)
    description_ar = Column(Text, nullable=True)

    category = Column(Enum(ChallengeCategory), nullable=False)
    frequency = Column(Enum(ChallengeFrequency), default=ChallengeFrequency.ONE_TIME)

    # متطلبات التحدي
    requirements = Column(JSON, nullable=False)  # {"downloads": 3, "days": 7}
    target_value = Column(Integer, nullable=False)
    current_value = Column(Integer, default=0)

    # المكافآت
    reward_points = Column(Integer, default=0)
    reward_badge_id = Column(Integer, ForeignKey("badges.id"), nullable=True)
    reward_items = Column(JSON, nullable=True)  # [{"type": "vip_days", "value": 7}]

    # التوقيت
    starts_at = Column(DateTime, nullable=True)
    ends_at = Column(DateTime, nullable=True)
    time_limit_hours = Column(Integer, nullable=True)  # للم تحدد

    # الحالة والأولوية
    is_active = Column(Boolean, default=True)
    is_featured = Column(Boolean, default=False)
    sort_order = Column(Integer, default=0)
    difficulty = Column(String(20), default="medium")  # easy, medium, hard, expert

    # الحدود
    max_participants = Column(Integer, nullable=True)
    current_participants = Column(Integer, default=0)

    # الأيقونة
    icon = Column(String(100), nullable=True)
    image_url = Column(String(500), nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    badge = relationship("Badge", backref="challenge_rewards")
    participations = relationship("ChallengeParticipation", back_populates="challenge", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Challenge {self.name}>"

    def is_available(self) -> bool:
        """هل التحدي متاح"""
        if not self.is_active:
            return False
        now = datetime.utcnow()
        if self.starts_at and now < self.starts_at:
            return False
        if self.ends_at and now > self.ends_at:
            return False
        if self.max_participants and self.current_participants >= self.max_participants:
            return False
        return True


class ChallengeParticipation(Base):
    """مشاركة المستخدم في التحدي"""
    __tablename__ = "challenge_participations"

    id = Column(Integer, primary_key=True, index=True)
    challenge_id = Column(Integer, ForeignKey("challenges.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    status = Column(Enum(ChallengeStatus), default=ChallengeStatus.IN_PROGRESS)

    progress = Column(Integer, default=0)
    progress_percent = Column(Float, default=0.0)

    started_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)
    expires_at = Column(DateTime, nullable=True)

    # المكافأة
    reward_claimed = Column(Boolean, default=False)
    reward_claimed_at = Column(DateTime, nullable=True)

    # بيانات إضافية - تم تغيير الاسم من metadata إلى extra_data
    extra_data = Column(JSON, nullable=True)

    last_updated = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    challenge = relationship("Challenge", back_populates="participations")
    user = relationship("User", backref="challenge_participations")

    def __repr__(self):
        return f"<ChallengeParticipation challenge={self.challenge_id} user={self.user_id}>"


class Badge(Base):
    """الشارة"""
    __tablename__ = "badges"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False, unique=True)
    name_ar = Column(String(100), nullable=True)
    description = Column(Text, nullable=True)
    description_ar = Column(Text, nullable=True)

    badge_type = Column(String(50), default="bronze")  # bronze, silver, gold, platinum, special

    # متطلبات الحصول على الشارة
    requirements = Column(JSON, nullable=False)  # {"downloads": 100, "reviews": 10}
    badge_category = Column(String(50), nullable=True)  # reading, social, vip, special

    # المميزات
    multiplier = Column(Float, default=1.0)  # مضاعف النقاط
    exclusive_access = Column(JSON, nullable=True)  # ["premium_books", "early_access"]

    # الأيقونة
    icon = Column(String(100), nullable=True)
    image_url = Column(String(500), nullable=True)
    badge_tier = Column(Integer, default=1)  # مستوى الشارة

    rarity = Column(String(20), default="common")  # common, rare, epic, legendary

    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    users = relationship("UserBadge", back_populates="badge", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Badge {self.name}>"


class UserBadge(Base):
    """شارة المستخدم"""
    __tablename__ = "user_badges"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    badge_id = Column(Integer, ForeignKey("badges.id"), nullable=False)

    earned_at = Column(DateTime, default=datetime.utcnow)
    is_displayed = Column(Boolean, default=True)
    display_order = Column(Integer, default=0)

    # مصدر الشارة
    earned_from_challenge_id = Column(Integer, ForeignKey("challenges.id"), nullable=True)
    earned_from_type = Column(String(50), nullable=True)  # challenge, milestone, special, purchase

    # بيانات إضافية - تم تغيير الاسم من metadata إلى extra_data
    extra_data = Column(JSON, nullable=True)

    # Relationships
    user = relationship("User", backref="badges")
    badge = relationship("Badge", back_populates="users")
    challenge = relationship("Challenge", foreign_keys=[earned_from_challenge_id])

    def __repr__(self):
        return f"<UserBadge user={self.user_id} badge={self.badge_id}>"


class Milestone(Base):
    """معلم/إنجاز رئيسي"""
    __tablename__ = "milestones"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False)
    name_ar = Column(String(200), nullable=True)
    description = Column(Text, nullable=True)

    # نوع المعلم
    milestone_type = Column(String(50), nullable=False)  # downloads, reviews, referrals, etc.
    target_value = Column(Integer, nullable=False)

    # المكافآت
    reward_points = Column(Integer, default=0)
    reward_badge_id = Column(Integer, ForeignKey("badges.id"), nullable=True)

    # الأولوية
    sort_order = Column(Integer, default=0)
    is_active = Column(Boolean, default=True)

    created_at = Column(DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<Milestone {self.name}>"


class UserMilestone(Base):
    """إنجازات المستخدم"""
    __tablename__ = "user_milestones"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    milestone_id = Column(Integer, ForeignKey("milestones.id"), nullable=False)

    progress = Column(Integer, default=0)
    is_completed = Column(Boolean, default=False)
    completed_at = Column(DateTime, nullable=True)
    reward_claimed = Column(Boolean, default=False)

    # Relationships
    user = relationship("User", backref="milestones")
    milestone = relationship("Milestone", backref="user_progress")

    def __repr__(self):
        return f"<UserMilestone user={self.user_id} milestone={self.milestone_id}>"


class DailyStreak(Base):
    """التسلسل اليومي"""
    __tablename__ = "daily_streaks"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    current_streak = Column(Integer, default=0)
    longest_streak = Column(Integer, default=0)

    last_activity_date = Column(DateTime, nullable=True)
    streak_started_at = Column(DateTime, nullable=True)

    # المكافآت
    streak_bonus_multiplier = Column(Float, default=1.0)  # يزداد مع طول التسلسل

    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    user = relationship("User", backref="daily_streaks")

    def __repr__(self):
        return f"<DailyStreak user={self.user_id} streak={self.current_streak}>"


class LeaderboardEntry(Base):
    """إدخال لوحة المتصدرين"""
    __tablename__ = "leaderboard_entries"

    id = Column(Integer, primary_key=True, index=True)

    leaderboard_type = Column(String(50), nullable=False)  # weekly, monthly, all_time, category
    period_start = Column(DateTime, nullable=True)
    period_end = Column(DateTime, nullable=True)

    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    rank = Column(Integer, nullable=False)
    score = Column(Integer, default=0)
    score_type = Column(String(50), default="points")  # points, downloads, reviews

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    user = relationship("User", backref="leaderboard_entries")

    def __repr__(self):
        return f"<LeaderboardEntry user={self.user_id} rank={self.rank}>"
# في نهاية الملف، بعد تعريف LeaderboardEntry
Leaderboard = LeaderboardEntry
