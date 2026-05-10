"""
Notification Service - خدمة الإشعارات الذكية
"""
from typing import List, Optional, Dict
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import desc, or_, and_
from app.models.notification import (
    Notification, UserNotificationSettings, NotificationTemplate,
    NotificationType, NotificationPriority, NotificationStatus
)
from app.models.user import User


class NotificationService:
    """خدمة الإشعارات الذكية"""

    def __init__(self, db: Session):
        self.db = db

    # ==========================================
    # إعدادات الإشعارات
    # ==========================================

    def get_or_create_settings(self, user_id: int) -> UserNotificationSettings:
        """الحصول على إعدادات الإشعارات أو إنشاؤها"""
        settings = self.db.query(UserNotificationSettings).filter(
            UserNotificationSettings.user_id == user_id
        ).first()

        if not settings:
            settings = UserNotificationSettings(user_id=user_id)
            self.db.add(settings)
            self.db.commit()
            self.db.refresh(settings)

        return settings

    def update_settings(
        self,
        user_id: int,
        **kwargs
    ) -> UserNotificationSettings:
        """تحديث إعدادات الإشعارات"""
        settings = self.get_or_create_settings(user_id)

        allowed_fields = [
            'new_book', 'author_new_book', 'category_new_book',
            'price_alerts', 'wishlist_alerts', 'auction_alerts',
            'social_notifications', 'challenge_notifications',
            'points_notifications', 'level_notifications',
            'system_notifications', 'direct_messages',
            'quiet_hours_start', 'quiet_hours_end', 'timezone',
            'batch_notifications', 'batch_interval_hours',
            'email_notifications', 'push_notifications'
        ]

        for key, value in kwargs.items():
            if key in allowed_fields:
                setattr(settings, key, value)

        self.db.commit()
        self.db.refresh(settings)
        return settings

    def is_notification_enabled(
        self,
        user_id: int,
        notification_type: NotificationType
    ) -> bool:
        """التحقق من تفعيل نوع الإشعار"""
        settings = self.get_or_create_settings(user_id)

        # خريطة الربط بين النوع والاعداد
        type_to_setting = {
            NotificationType.NEW_BOOK: 'new_book',
            NotificationType.AUTHOR_NEW_BOOK: 'author_new_book',
            NotificationType.CATEGORY_NEW_BOOK: 'category_new_book',
            NotificationType.PRICE_DROP: 'price_alerts',
            NotificationType.WISHLIST_AVAILABLE: 'wishlist_alerts',
            NotificationType.AUCTION_ENDING: 'auction_alerts',
            NotificationType.NEW_REVIEW: 'social_notifications',
            NotificationType.NEW_FOLLOWER: 'social_notifications',
            NotificationType.CHALLENGE_AVAILABLE: 'challenge_notifications',
            NotificationType.CHALLENGE_COMPLETED: 'challenge_notifications',
            NotificationType.POINTS_EARNED: 'points_notifications',
            NotificationType.LEVEL_UP: 'level_notifications',
            NotificationType.SYSTEM_ANNOUNCEMENT: 'system_notifications',
            NotificationType.DIRECT_MESSAGE: 'direct_messages',
        }

        setting_name = type_to_setting.get(notification_type)
        if not setting_name:
            return True

        return getattr(settings, setting_name, True)

    # ==========================================
    # إنشاء الإشعارات
    # ==========================================

    def create_notification(
        self,
        user_id: int,
        notification_type: NotificationType,
        title: str,
        message: str,
        title_ar: str = None,
        message_ar: str = None,
        priority: NotificationPriority = NotificationPriority.NORMAL,
        related_type: str = None,
        related_id: int = None,
        action_buttons: list = None,
        action_url: str = None,
        image_url: str = None,
        scheduled_at: datetime = None
    ) -> Notification:
        """إنشاء إشعار جديد"""
        # التحقق من تفعيل الإشعار
        if not self.is_notification_enabled(user_id, notification_type):
            return None

        # التحقق من وقت الهدوء
        settings = self.get_or_create_settings(user_id)
        if settings.quiet_hours_start and settings.quiet_hours_end:
            if self._is_quiet_hours(settings):
                # جدولة الإشعار لبعد وقت الهدوء
                if not scheduled_at:
                    scheduled_at = self._get_next_active_time(settings)

        notification = Notification(
            user_id=user_id,
            notification_type=notification_type,
            priority=priority,
            title=title,
            title_ar=title_ar,
            message=message,
            message_ar=message_ar,
            related_type=related_type,
            related_id=related_id,
            action_buttons=action_buttons,
            action_url=action_url,
            image_url=image_url,
            scheduled_at=scheduled_at,
            status=NotificationStatus.PENDING if scheduled_at else NotificationStatus.SENT,
            sent_at=datetime.utcnow() if not scheduled_at else None
        )

        self.db.add(notification)
        self.db.commit()
        self.db.refresh(notification)

        return notification

    def _is_quiet_hours(self, settings: UserNotificationSettings) -> bool:
        """التحقق من وقت الهدوء"""
        from datetime import time as dt_time
        now = datetime.utcnow().time()

        start = dt_time.fromisoformat(settings.quiet_hours_start)
        end = dt_time.fromisoformat(settings.quiet_hours_end)

        if start <= end:
            return start <= now <= end
        else:  # يتجاوز منتصف الليل
            return now >= start or now <= end

    def _get_next_active_time(
        self,
        settings: UserNotificationSettings
    ) -> datetime:
        """الحصول على وقت لاحق بعد وقت الهدوء"""
        from datetime import time as dt_time

        end_time = dt_time.fromisoformat(settings.quiet_hours_end)
        now = datetime.utcnow()

        # إنشاء تاريخ انتهاء وقت الهدوء
        end_dt = now.replace(
            hour=end_time.hour,
            minute=end_time.minute,
            second=0
        )

        if end_dt <= now:
            end_dt += timedelta(days=1)

        return end_dt

    # ==========================================
    # إشعارات مجمعة
    # ==========================================

    def batch_notifications(
        self,
        user_ids: List[int],
        notification_type: NotificationType,
        title: str,
        message: str,
        **kwargs
    ) -> int:
        """إرسال إشعارات لمجموعة مستخدمين"""
        count = 0
        for user_id in user_ids:
            notification = self.create_notification(
                user_id=user_id,
                notification_type=notification_type,
                title=title,
                message=message,
                **kwargs
            )
            if notification:
                count += 1

        return count

    def schedule_daily_digest(self, user_id: int) -> None:
        """جدولة ملخص يومي"""
        settings = self.get_or_create_settings(user_id)

        if not settings.batch_notifications:
            return

        # جلب الإشعارات غير المقروءة من آخر 24 ساعة
        yesterday = datetime.utcnow() - timedelta(hours=24)

        notifications = self.db.query(Notification).filter(
            Notification.user_id == user_id,
            Notification.created_at >= yesterday,
            Notification.is_read == False,
            Notification.is_dismissed == False
        ).all()

        if not notifications:
            return

        # إنشاء إشعار ملخص
        count = len(notifications)
        message = f"لديك {count} إشعارات جديدة"

        digest = self.create_notification(
            user_id=user_id,
            notification_type=NotificationType.SYSTEM_ANNOUNCEMENT,
            title="📋 ملخص الإشعارات",
            message=message,
            priority=NotificationPriority.LOW,
            batch_id=f"digest_{user_id}_{datetime.utcnow().date()}",
            batch_count=count
        )

        # ربط الإشعارات بالملخص
        for n in notifications:
            n.batch_id = digest.batch_id

        self.db.commit()

    # ==========================================
    # إدارة الإشعارات
    # ==========================================

    def get_user_notifications(
        self,
        user_id: int,
        unread_only: bool = False,
        limit: int = 50,
        offset: int = 0
    ) -> List[Notification]:
        """الحصول على إشعارات المستخدم"""
        query = self.db.query(Notification).filter(
            Notification.user_id == user_id,
            Notification.is_dismissed == False
        )

        if unread_only:
            query = query.filter(Notification.is_read == False)

        return query.order_by(desc(Notification.created_at)).limit(limit).offset(offset).all()

    def mark_as_read(self, notification_id: int, user_id: int) -> bool:
        """تحديد الإشعار كمقروء"""
        notification = self.db.query(Notification).filter(
            Notification.id == notification_id,
            Notification.user_id == user_id
        ).first()

        if notification:
            notification.is_read = True
            notification.status = NotificationStatus.READ
            notification.read_at = datetime.utcnow()
            self.db.commit()
            return True
        return False

    def mark_all_as_read(self, user_id: int) -> int:
        """تحديد جميع الإشعارات كمقروءة"""
        count = self.db.query(Notification).filter(
            Notification.user_id == user_id,
            Notification.is_read == False
        ).update({
            Notification.is_read: True,
            Notification.status: NotificationStatus.READ,
            Notification.read_at: datetime.utcnow()
        })

        self.db.commit()
        return count

    def dismiss_notification(self, notification_id: int, user_id: int) -> bool:
        """تجاهل إشعار"""
        notification = self.db.query(Notification).filter(
            Notification.id == notification_id,
            Notification.user_id == user_id
        ).first()

        if notification:
            notification.is_dismissed = True
            notification.status = NotificationStatus.DISMISSED
            self.db.commit()
            return True
        return False

    def delete_old_notifications(self, days: int = 30) -> int:
        """حذف الإشعارات القديمة"""
        cutoff = datetime.utcnow() - timedelta(days=days)

        count = self.db.query(Notification).filter(
            Notification.created_at < cutoff,
            Notification.is_read == True
        ).delete()

        self.db.commit()
        return count

    # ==========================================
    # قوالب الإشعارات
    # ==========================================

    def get_template(
        self,
        template_code: str
    ) -> Optional[NotificationTemplate]:
        """الحصول على قالب إشعار"""
        return self.db.query(NotificationTemplate).filter(
            NotificationTemplate.template_code == template_code
        ).first()

    def render_template(
        self,
        template: NotificationTemplate,
        variables: dict
    ) -> tuple:
        """عرض قالب مع المتغيرات"""
        title = template.title_template
        message = template.message_template

        for key, value in variables.items():
            placeholder = f"{{{key}}}"
            title = title.replace(placeholder, str(value))
            message = message.replace(placeholder, str(value))

        if template.title_template_ar:
            title_ar = template.title_template_ar
            for key, value in variables.items():
                placeholder = f"{{{key}}}"
                title_ar = title_ar.replace(placeholder, str(value))
        else:
            title_ar = title

        if template.message_template_ar:
            message_ar = template.message_template_ar
            for key, value in variables.items():
                placeholder = f"{{{key}}}"
                message_ar = message_ar.replace(placeholder, str(value))
        else:
            message_ar = message

        return title_ar, message_ar

    # ==========================================
    # إحصائيات
    # ==========================================

    def get_notification_stats(self, user_id: int) -> dict:
        """إحصائيات إشعارات المستخدم"""
        total = self.db.query(func.count(Notification.id)).filter(
            Notification.user_id == user_id
        ).scalar()

        unread = self.db.query(func.count(Notification.id)).filter(
            Notification.user_id == user_id,
            Notification.is_read == False
        ).scalar()

        by_type = {}
        for ntype in NotificationType:
            count = self.db.query(func.count(Notification.id)).filter(
                Notification.user_id == user_id,
                Notification.notification_type == ntype
            ).scalar()
            by_type[ntype.value] = count

        return {
            "total": total,
            "unread": unread,
            "by_type": by_type
        }

    def get_unread_count(self, user_id: int) -> int:
        """عدد الإشعارات غير المقروءة"""
        return self.db.query(func.count(Notification.id)).filter(
            Notification.user_id == user_id,
            Notification.is_read == False
        ).scalar()
