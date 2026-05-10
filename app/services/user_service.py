"""
User Service - خدمة المستخدمين
"""
from typing import List, Optional
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.models.user import User, UserStatus
from app.models.favorite import Favorite
from app.models.download_history import DownloadHistory
from config.settings import get_settings

settings = get_settings()


class UserService:
    """خدمة إدارة المستخدمين"""

    def __init__(self, db: Session):
        self.db = db

    def get_or_create_user(
        self,
        telegram_id: int,
        username: Optional[str] = None,
        first_name: Optional[str] = None,
        last_name: Optional[str] = None,
        language: str = "ar"
    ) -> User:
        """الحصول على مستخدم أو إنشاؤه إذا لم يكن موجوداً"""
        user = self.get_user_by_telegram_id(telegram_id)
        if user:
            # تحديث آخر نشاط
            user.last_active = datetime.utcnow()
            if username and not user.username:
                user.username = username
            self.db.commit()
            return user

        # إنشاء مستخدم جديد
        import random
        import string
        referral_code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))

        user = User(
            telegram_id=telegram_id,
            username=username,
            first_name=first_name,
            last_name=last_name,
            language=language,
            referral_code=referral_code,
            status=UserStatus.ACTIVE
        )
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)
        return user

    def get_user_by_telegram_id(self, telegram_id: int) -> Optional[User]:
        """الحصول على مستخدم بمعرف تيليجرام"""
        return self.db.query(User).filter(User.telegram_id == telegram_id).first()

    def get_user_by_id(self, user_id: int) -> Optional[User]:
        """الحصول على مستخدم بالمعرف"""
        return self.db.query(User).filter(User.id == user_id).first()

    def get_all_users(self, status: Optional[UserStatus] = None) -> List[User]:
        """الحصول على جميع المستخدمين"""
        query = self.db.query(User)
        if status:
            query = query.filter(User.status == status)
        return query.order_by(User.created_at.desc()).all()

    def ban_user(self, telegram_id: int) -> Optional[User]:
        """حظر مستخدم"""
        user = self.get_user_by_telegram_id(telegram_id)
        if not user:
            return None

        user.status = UserStatus.BANNED
        self.db.commit()
        self.db.refresh(user)
        return user

    def unban_user(self, telegram_id: int) -> Optional[User]:
        """إلغاء حظر مستخدم"""
        user = self.get_user_by_telegram_id(telegram_id)
        if not user:
            return None

        user.status = UserStatus.ACTIVE
        self.db.commit()
        self.db.refresh(user)
        return user

    def suspend_user(self, telegram_id: int) -> Optional[User]:
        """تعليق مستخدم"""
        user = self.get_user_by_telegram_id(telegram_id)
        if not user:
            return None

        user.status = UserStatus.SUSPENDED
        self.db.commit()
        self.db.refresh(user)
        return user

    def update_user(
        self,
        telegram_id: int,
        first_name: Optional[str] = None,
        last_name: Optional[str] = None,
        language: Optional[str] = None,
        is_premium: Optional[bool] = None
    ) -> Optional[User]:
        """تحديث بيانات المستخدم"""
        user = self.get_user_by_telegram_id(telegram_id)
        if not user:
            return None

        if first_name is not None:
            user.first_name = first_name
        if last_name is not None:
            user.last_name = last_name
        if language is not None:
            user.language = language
        if is_premium is not None:
            user.is_premium = is_premium

        self.db.commit()
        self.db.refresh(user)
        return user

    def increment_downloads(self, telegram_id: int) -> Optional[User]:
        """زيادة عدد التحميلات"""
        user = self.get_user_by_telegram_id(telegram_id)
        if not user:
            return None

        user.total_downloads += 1
        self.db.commit()
        self.db.refresh(user)
        return user

    def level_up(self, telegram_id: int) -> Optional[User]:
        """ترقية مستوى المستخدم"""
        user = self.get_user_by_telegram_id(telegram_id)
        if not user:
            return None

        # قواعد الترقية (يمكنك تعديلها)
        downloads_needed = {
            1: 0,
            2: 10,
            3: 25,
            4: 50,
            5: 100,
            6: 200,
            7: 500,
            8: 1000
        }

        for level, needed in sorted(downloads_needed.items(), key=lambda x: x[1], reverse=True):
            if user.total_downloads >= needed:
                if user.level < level:
                    user.level = level
                    self.db.commit()
                    self.db.refresh(user)
                break

        return user

    def get_user_favorites(self, telegram_id: int) -> List[Favorite]:
        """الحصول على المفضلة للمستخدم"""
        user = self.get_user_by_telegram_id(telegram_id)
        if not user:
            return []
        return self.db.query(Favorite).filter(Favorite.user_id == user.id).all()

    def get_user_downloads(self, telegram_id: int, limit: int = 20) -> List[DownloadHistory]:
        """الحصول على سجل التحميلات للمستخدم"""
        user = self.get_user_by_telegram_id(telegram_id)
        if not user:
            return []
        return self.db.query(DownloadHistory).filter(
            DownloadHistory.user_id == user.id
        ).order_by(DownloadHistory.downloaded_at.desc()).limit(limit).all()

    def is_owner(self, telegram_id: int) -> bool:
        """التحقق من أن المستخدم هو المالك"""
        return settings.is_owner(telegram_id)

    def is_banned(self, telegram_id: int) -> bool:
        """التحقق إذا كان المستخدم محظوراً"""
        user = self.get_user_by_telegram_id(telegram_id)
        return user and user.status == UserStatus.BANNED

    def count_users(self, status: Optional[UserStatus] = None) -> int:
        """عدد المستخدمين"""
        query = self.db.query(func.count(User.id))
        if status:
            query = query.filter(User.status == status)
        return query.scalar()

    def get_statistics(self) -> dict:
        """إحصائيات المستخدمين"""
        total = self.count_users()
        active = self.count_users(UserStatus.ACTIVE)
        banned = self.count_users(UserStatus.BANNED)

        total_downloads = self.db.query(func.sum(User.total_downloads)).scalar() or 0
        premium_count = self.db.query(func.count(User.id)).filter(User.is_premium == True).scalar()

        return {
            "total": total,
            "active": active,
            "banned": banned,
            "total_downloads": total_downloads,
            "premium": premium_count
        }

    def search_users(self, query: str) -> List[User]:
        """البحث عن مستخدمين"""
        return self.db.query(User).filter(
            (User.username.ilike(f"%{query}%")) |
            (User.first_name.ilike(f"%{query}%")) |
            (User.telegram_id == query)
        ).limit(50).all()
