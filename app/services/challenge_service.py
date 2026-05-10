"""
Challenge Service - خدمة التحديات والإنجازات
"""
from typing import List, Optional, Dict
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import desc, func
from app.models.challenges import (
    Challenge, ChallengeParticipation, Badge, UserBadge,
    Milestone, UserMilestone, DailyStreak, LeaderboardEntry,
    ChallengeCategory, ChallengeFrequency, ChallengeStatus
)
from app.models.user import User
from app.models.book import Book
from app.models.points import UserPoints, PointsTransaction, TransactionType


class ChallengeService:
    """خدمة التحديات والإنجازات"""

    def __init__(self, db: Session):
        self.db = db

    # ==========================================
    # التحديات
    # ==========================================

    def get_available_challenges(self, user_id: int) -> List[Challenge]:
        """الحصول على التحديات المتاحة للمستخدم"""
        now = datetime.utcnow()

        # التحديات النشطة
        challenges = self.db.query(Challenge).filter(
            Challenge.is_active == True,
            Challenge.starts_at <= now,
            (Challenge.ends_at.is_(None) | (Challenge.ends_at > now))
        ).order_by(Challenge.sort_order).all()

        # تصفية التحديات المشاركة فيها
        available = []
        for challenge in challenges:
            participation = self.get_participation(user_id, challenge.id)
            if not participation or participation.status == ChallengeStatus.NOT_STARTED:
                available.append(challenge)

        return available

    def get_active_challenges(self, user_id: int) -> List[ChallengeParticipation]:
        """الحصول على التحديات النشطة للمستخدم"""
        return self.db.query(ChallengeParticipation).filter(
            ChallengeParticipation.user_id == user_id,
            ChallengeParticipation.status == ChallengeStatus.IN_PROGRESS
        ).all()

    def join_challenge(
        self,
        user_id: int,
        challenge_id: int
    ) -> ChallengeParticipation:
        """الانضمام لتحدي"""
        challenge = self.db.query(Challenge).get(challenge_id)
        if not challenge or not challenge.is_available():
            raise ValueError("التحدي غير متاح")

        # التحقق من عدم المشاركة مسبقاً
        existing = self.get_participation(user_id, challenge_id)
        if existing:
            return existing

        # حساب وقت انتهاء التحدي
        expires_at = None
        if challenge.time_limit_hours:
            expires_at = datetime.utcnow() + timedelta(hours=challenge.time_limit_hours)

        participation = ChallengeParticipation(
            challenge_id=challenge_id,
            user_id=user_id,
            status=ChallengeStatus.IN_PROGRESS,
            expires_at=expires_at
        )

        # تحديث عدد المشاركين
        challenge.current_participants += 1

        self.db.add(participation)
        self.db.commit()
        self.db.refresh(participation)

        return participation

    def get_participation(
        self,
        user_id: int,
        challenge_id: int
    ) -> Optional[ChallengeParticipation]:
        """الحصول على مشاركة مستخدم في تحدي"""
        return self.db.query(ChallengeParticipation).filter(
            ChallengeParticipation.user_id == user_id,
            ChallengeParticipation.challenge_id == challenge_id
        ).first()

    def update_progress(
        self,
        user_id: int,
        challenge_id: int,
        new_progress: int
    ) -> Optional[ChallengeParticipation]:
        """تحديث تقدم المستخدم في التحدي"""
        participation = self.get_participation(user_id, challenge_id)
        if not participation:
            return None

        challenge = self.db.query(Challenge).get(challenge_id)
        if not challenge:
            return None

        # التحقق من انتهاء الوقت
        if participation.expires_at and participation.expires_at < datetime.utcnow():
            participation.status = ChallengeStatus.EXPIRED
            self.db.commit()
            return participation

        participation.progress = new_progress
        participation.progress_percent = min(
            (new_progress / challenge.target_value) * 100,
            100
        )
        participation.last_updated = datetime.utcnow()

        # التحقق من اكتمال التحدي
        if new_progress >= challenge.target_value:
            participation.status = ChallengeStatus.COMPLETED
            participation.completed_at = datetime.utcnow()

            # منح المكافأة
            self.award_challenge_reward(participation)

        self.db.commit()
        self.db.refresh(participation)
        return participation

    def award_challenge_reward(
        self,
        participation: ChallengeParticipation
    ) -> None:
        """منح مكافأة التحدي"""
        challenge = self.db.query(Challenge).get(participation.challenge_id)
        if not challenge:
            return

        # منح النقاط
        if challenge.reward_points > 0:
            self._add_points(
                participation.user_id,
                challenge.reward_points,
                f"مكافأة التحدي: {challenge.name}"
            )

        # منح الشارة
        if challenge.reward_badge_id:
            self.award_badge(participation.user_id, challenge.reward_badge_id)

        # تحديث حالة المكافأة
        participation.reward_claimed = True
        participation.reward_claimed_at = datetime.utcnow()

        self.db.commit()

    def _add_points(self, user_id: int, amount: int, description: str) -> None:
        """إضافة نقاط"""
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
            transaction_type=TransactionType.GIFT,
            description=description
        )
        self.db.add(transaction)
        self.db.commit()

    # ==========================================
    # الشارات
    # ==========================================

    def get_all_badges(self) -> List[Badge]:
        """الحصول على جميع الشارات"""
        return self.db.query(Badge).order_by(Badge.badge_tier).all()

    def award_badge(
        self,
        user_id: int,
        badge_id: int,
        source_type: str = "challenge",
        source_id: int = None
    ) -> Optional[UserBadge]:
        """منح شارة للمستخدم"""
        # التحقق من عدم وجود الشارة مسبقاً
        existing = self.db.query(UserBadge).filter(
            UserBadge.user_id == user_id,
            UserBadge.badge_id == badge_id
        ).first()

        if existing:
            return existing

        badge = UserBadge(
            user_id=user_id,
            badge_id=badge_id,
            earned_from_type=source_type,
            earned_from_challenge_id=source_id
        )

        self.db.add(badge)
        self.db.commit()
        self.db.refresh(badge)

        return badge

    def get_user_badges(self, user_id: int) -> List[UserBadge]:
        """شارات المستخدم"""
        return self.db.query(UserBadge).filter(
            UserBadge.user_id == user_id,
            UserBadge.is_displayed == True
        ).order_by(desc(UserBadge.earned_at)).all()

    def check_and_award_badges(
        self,
        user_id: int,
        trigger_type: str,
        trigger_value: int
    ) -> List[Badge]:
        """التحقق ومنح الشارات المستحقة"""
        # البحث عن الشارات التي تطابق الشرط
        badges = self.db.query(Badge).filter(
            Badge.requirements.contains({trigger_type: trigger_value})
        ).all()

        earned = []
        for badge in badges:
            if self._check_badge_requirements(user_id, badge, trigger_type, trigger_value):
                result = self.award_badge(user_id, badge.id)
                if result:
                    earned.append(badge)

        return earned

    def _check_badge_requirements(
        self,
        user_id: int,
        badge: Badge,
        current_type: str,
        current_value: int
    ) -> bool:
        """التحقق من استيفاء متطلبات الشارة"""
        requirements = badge.requirements or {}

        for req_type, req_value in requirements.items():
            if req_type == current_type:
                if current_value < req_value:
                    return False
            else:
                # التحقق من الشروط الأخرى
                if req_type == "downloads":
                    count = self.db.query(func.count()).filter().scalar()  # تحتاج implementation
                # يمكن إضافة شروط أخرى حسب الحاجة

        return True

    # ==========================================
    # التسلسل اليومي
    # ==========================================

    def update_daily_streak(self, user_id: int) -> DailyStreak:
        """تحديث التسلسل اليومي"""
        streak = self.db.query(DailyStreak).filter(
            DailyStreak.user_id == user_id
        ).first()

        now = datetime.utcnow()
        today = now.date()

        if not streak:
            streak = DailyStreak(
                user_id=user_id,
                current_streak=1,
                longest_streak=1,
                last_activity_date=now,
                streak_started_at=now
            )
            self.db.add(streak)
        else:
            last_date = streak.last_activity_date.date() if streak.last_activity_date else None

            if last_date == today:
                # لا تغيير
                pass
            elif last_date == today - timedelta(days=1):
                # يوم متتالي
                streak.current_streak += 1
                streak.last_activity_date = now

                if streak.current_streak > streak.longest_streak:
                    streak.longest_streak = streak.current_streak
            else:
                # كسر التسلسل
                streak.current_streak = 1
                streak.last_activity_date = now
                streak.streak_started_at = now

            # تحديث المضاعف
            streak.streak_bonus_multiplier = 1.0 + (streak.current_streak * 0.1)

        self.db.commit()
        self.db.refresh(streak)
        return streak

    # ==========================================
    # المعالم/الإنجازات
    # ==========================================

    def check_milestones(self, user_id: int) -> List[Milestone]:
        """التحقق من المعالم المكتسبة"""
        milestones = self.db.query(Milestone).filter(
            Milestone.is_active == True
        ).all()

        earned = []
        for milestone in milestones:
            user_milestone = self.db.query(UserMilestone).filter(
                UserMilestone.user_id == user_id,
                UserMilestone.milestone_id == milestone.id,
                UserMilestone.is_completed == True
            ).first()

            if user_milestone:
                continue

            # حساب التقدم
            progress = self._calculate_milestone_progress(user_id, milestone)

            if progress >= milestone.target_value:
                # إكمال المعلم
                user_milestone = UserMilestone(
                    user_id=user_id,
                    milestone_id=milestone.id,
                    progress=progress,
                    is_completed=True,
                    completed_at=datetime.utcnow(),
                    reward_claimed=True
                )
                self.db.add(user_milestone)

                # منح المكافأة
                if milestone.reward_points > 0:
                    self._add_points(
                        user_id,
                        milestone.reward_points,
                        f"إنجاز: {milestone.name}"
                    )

                if milestone.reward_badge_id:
                    self.award_badge(user_id, milestone.reward_badge_id)

                earned.append(milestone)

        if earned:
            self.db.commit()

        return earned

    def _calculate_milestone_progress(
        self,
        user_id: int,
        milestone: Milestone
    ) -> int:
        """حساب التقدم نحو معلم"""
        from app.models.download_history import DownloadHistory

        if milestone.milestone_type == "downloads":
            return self.db.query(func.count(DownloadHistory.id)).filter(
                DownloadHistory.user_id == user_id
            ).scalar() or 0

        # يمكن إضافة أنواع أخرى
        return 0

    # ==========================================
    # لوحة المتصدرين
    # ==========================================

    def update_leaderboard(
        self,
        leaderboard_type: str,
        period_start: datetime,
        period_end: datetime
    ) -> None:
        """تحديث لوحة المتصدرين"""
        # جلب أعلى النقاط في الفترة
        from app.models.points import UserPoints, PointsTransaction

        results = self.db.query(
            PointsTransaction.user_id,
            func.sum(PointsTransaction.amount).label('score')
        ).filter(
            PointsTransaction.created_at >= period_start,
            PointsTransaction.created_at <= period_end,
            PointsTransaction.amount > 0
        ).group_by(
            PointsTransaction.user_id
        ).order_by(
            desc('score')
        ).limit(100).all()

        # حذف الإدخالات القديمة
        self.db.query(LeaderboardEntry).filter(
            LeaderboardEntry.leaderboard_type == leaderboard_type
        ).delete()

        # إضافة الإدخالات الجديدة
        for rank, (user_id, score) in enumerate(results, 1):
            entry = LeaderboardEntry(
                leaderboard_type=leaderboard_type,
                period_start=period_start,
                period_end=period_end,
                user_id=user_id,
                rank=rank,
                score=int(score),
                score_type="points"
            )
            self.db.add(entry)

        self.db.commit()

    def get_leaderboard(
        self,
        leaderboard_type: str = "weekly",
        limit: int = 10
    ) -> List[dict]:
        """الحصول على لوحة المتصدرين"""
        entries = self.db.query(LeaderboardEntry).filter(
            LeaderboardEntry.leaderboard_type == leaderboard_type
        ).order_by(LeaderboardEntry.rank).limit(limit).all()

        results = []
        for entry in entries:
            user = self.db.query(User).get(entry.user_id)
            results.append({
                "rank": entry.rank,
                "user_id": entry.user_id,
                "name": user.first_name if user else "مستخدم",
                "score": entry.score,
                "score_type": entry.score_type
            })

        return results

    def get_user_rank(self, user_id: int, leaderboard_type: str = "weekly") -> Optional[int]:
        """ترتيب المستخدم في لوحة المتصدرين"""
        entry = self.db.query(LeaderboardEntry).filter(
            LeaderboardEntry.leaderboard_type == leaderboard_type,
            LeaderboardEntry.user_id == user_id
        ).first()

        return entry.rank if entry else None

    # ==========================================
    # إحصائيات
    # ==========================================

    def get_challenge_stats(self, user_id: int) -> dict:
        """إحصائيات التحديات"""
        total_challenges = self.db.query(ChallengeParticipation).filter(
            ChallengeParticipation.user_id == user_id
        ).count()

        completed = self.db.query(ChallengeParticipation).filter(
            ChallengeParticipation.user_id == user_id,
            ChallengeParticipation.status == ChallengeStatus.COMPLETED
        ).count()

        active = self.db.query(ChallengeParticipation).filter(
            ChallengeParticipation.user_id == user_id,
            ChallengeParticipation.status == ChallengeStatus.IN_PROGRESS
        ).count()

        return {
            "total_participated": total_challenges,
            "completed": completed,
            "active": active,
            "completion_rate": round(completed / total_challenges * 100, 2) if total_challenges > 0 else 0
        }

    def get_badge_stats(self, user_id: int) -> dict:
        """إحصائيات الشارات"""
        total_badges = self.db.query(UserBadge).filter(
            UserBadge.user_id == user_id
        ).count()

        by_type = {}
        badges = self.db.query(UserBadge).filter(
            UserBadge.user_id == user_id
        ).all()

        for badge in badges:
            badge_obj = self.db.query(Badge).get(badge.badge_id)
            if badge_obj:
                badge_type = badge_obj.badge_type
                by_type[badge_type] = by_type.get(badge_type, 0) + 1

        return {
            "total_badges": total_badges,
            "by_type": by_type
        }
