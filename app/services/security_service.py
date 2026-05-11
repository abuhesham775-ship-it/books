"""
Security Service - خدمة الأمان والتدقيق
"""
from typing import List, Optional, Dict, Tuple
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import desc, func, and_
from app.models.security import (
    AuditLog, SecurityEvent, RateLimit, IPBlacklist,
    SpamReport, ContentWatermark, AccessLog, BackupRecord,
    AuditAction, ThreatLevel
)
from app.models.user import User
from config.settings import get_settings

settings = get_settings()


class SecurityService:
    """خدمة الأمان والتدقيق"""

    def __init__(self, db: Session):
        self.db = db

    # ==========================================
    # سجل التدقيق
    # ==========================================

    def log_action(
        self,
        action: AuditAction,
        user_id: int = None,
        admin_id: int = None,
        entity_type: str = None,
        entity_id: int = None,
        old_value: dict = None,
        new_value: dict = None,
        ip_address: str = None,
        status: str = "success",
        error_message: str = None,
        metadata: dict = None
    ) -> AuditLog:
        """تسجيل إجراء في سجل التدقيق"""
        log = AuditLog(
            user_id=user_id,
            admin_id=admin_id,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            old_value=old_value,
            new_value=new_value,
            ip_address=ip_address,
            status=status,
            error_message=error_message,
            metadata=metadata
        )

        self.db.add(log)
        self.db.commit()
        self.db.refresh(log)
        return log

    def get_audit_logs(
        self,
        user_id: int = None,
        action: AuditAction = None,
        start_date: datetime = None,
        end_date: datetime = None,
        limit: int = 100
    ) -> List[AuditLog]:
        """الحصول على سجلات التدقيق"""
        query = self.db.query(AuditLog)

        if user_id:
            query = query.filter(AuditLog.user_id == user_id)
        if action:
            query = query.filter(AuditLog.action == action)
        if start_date:
            query = query.filter(AuditLog.created_at >= start_date)
        if end_date:
            query = query.filter(AuditLog.created_at <= end_date)

        return query.order_by(desc(AuditLog.created_at)).limit(limit).all()

    def get_recent_logs(self, limit: int = 20) -> List[dict]:
        """واجهة توافقية لآخر السجلات"""
        logs = self.get_audit_logs(limit=limit)
        return [
            {
                "action": getattr(log.action, "value", str(log.action)),
                "user_id": log.user_id,
                "admin_id": log.admin_id,
                "timestamp": log.created_at.strftime("%Y-%m-%d %H:%M:%S") if getattr(log, "created_at", None) else None,
                "status": log.status,
                "entity_type": log.entity_type,
                "entity_id": log.entity_id,
            }
            for log in logs
        ]

    def get_security_stats(self) -> dict:
        """إحصائيات الأمان العامة"""
        suspicious_events = self.db.query(func.count(SecurityEvent.id)).scalar() or 0
        blocked_users = self.db.query(func.count(RateLimit.id)).filter(RateLimit.is_blocked == True).scalar() or 0
        api_requests = self.db.query(func.sum(RateLimit.current_count)).scalar() or 0
        failed_attempts = self.db.query(func.count(AccessLog.id)).filter(AccessLog.status == "failed").scalar() or 0
        return {
            "suspicious_events": suspicious_events,
            "blocked_users": blocked_users,
            "api_requests": api_requests,
            "failed_attempts": failed_attempts,
        }

    def get_blocked_ips(self, limit: int = 20) -> List[dict]:
        """القائمة السوداء بصيغة توافقية للواجهات"""
        entries = self.db.query(IPBlacklist).order_by(desc(IPBlacklist.created_at)).limit(limit).all()
        active = [entry for entry in entries if entry.is_active()]
        return [
            {
                "ip_address": entry.ip_address,
                "reason": entry.reason,
                "threat_level": getattr(entry.threat_level, "value", str(entry.threat_level)),
                "blocked_until": entry.blocked_until.strftime("%Y-%m-%d %H:%M:%S") if entry.blocked_until else None,
            }
            for entry in active
        ]

    # ==========================================
    # حدود معدل الطلبات
    # ==========================================

    def check_rate_limit(
        self,
        identifier: str,
        identifier_type: str = "user",
        limit_type: str = "requests"
    ) -> Tuple[bool, Optional[RateLimit]]:
        """التحقق من حدود معدل الطلبات"""
        rate_limit = self.db.query(RateLimit).filter(
            RateLimit.identifier == identifier,
            RateLimit.identifier_type == identifier_type,
            RateLimit.limit_type == limit_type
        ).first()

        if not rate_limit:
            # إنشاء حد جديد
            rate_limit = RateLimit(
                identifier=identifier,
                identifier_type=identifier_type,
                limit_type=limit_type,
                limit_value=100,  # default
                window_seconds=60,
                current_count=0,
                window_start=datetime.utcnow()
            )
            self.db.add(rate_limit)
            self.db.commit()
            self.db.refresh(rate_limit)

        # التحقق من الحظر
        if rate_limit.is_rate_limited():
            return True, rate_limit

        # التحقق من انتهاء النافذة الزمنية
        if rate_limit.window_start:
            elapsed = (datetime.utcnow() - rate_limit.window_start).total_seconds()
            if elapsed > rate_limit.window_seconds:
                rate_limit.current_count = 0
                rate_limit.window_start = datetime.utcnow()
                self.db.commit()

        return rate_limit.current_count >= rate_limit.limit_value, rate_limit

    def increment_rate_limit(self, identifier: str, identifier_type: str = "user") -> None:
        """زيادة عداد حد المعدل"""
        rate_limit = self.db.query(RateLimit).filter(
            RateLimit.identifier == identifier,
            RateLimit.identifier_type == identifier_type
        ).first()

        if rate_limit:
            rate_limit.increment()
            self.db.commit()

    def block_user(
        self,
        identifier: str,
        identifier_type: str,
        duration_minutes: int,
        reason: str
    ) -> None:
        """حظر مستخدم مؤقتاً"""
        rate_limit = self.db.query(RateLimit).filter(
            RateLimit.identifier == identifier,
            RateLimit.identifier_type == identifier_type
        ).first()

        if rate_limit:
            rate_limit.is_blocked = True
            rate_limit.blocked_until = datetime.utcnow() + timedelta(minutes=duration_minutes)
            rate_limit.block_reason = reason
            self.db.commit()

    # ==========================================
    # القائمة السوداء للـ IP
    # ==========================================

    def add_to_blacklist(
        self,
        ip_address: str,
        reason: str,
        blocked_by: int,
        duration_minutes: int = None,
        threat_level: ThreatLevel = ThreatLevel.MEDIUM
    ) -> IPBlacklist:
        """إضافة IP للقائمة السوداء"""
        existing = self.db.query(IPBlacklist).filter(
            IPBlacklist.ip_address == ip_address
        ).first()

        if existing:
            return existing

        blocked_until = None
        if duration_minutes:
            blocked_until = datetime.utcnow() + timedelta(minutes=duration_minutes)

        blacklist = IPBlacklist(
            ip_address=ip_address,
            reason=reason,
            blocked_by=blocked_by,
            blocked_until=blocked_until,
            threat_level=threat_level,
            is_permanent=duration_minutes is None
        )

        self.db.add(blacklist)
        self.db.commit()
        self.db.refresh(blacklist)
        return blacklist

    def is_blacklisted(self, ip_address: str) -> bool:
        """التحقق إذا كان IP في القائمة السوداء"""
        entry = self.db.query(IPBlacklist).filter(
            IPBlacklist.ip_address == ip_address
        ).first()

        if not entry:
            return False

        return entry.is_active()

    def remove_from_blacklist(self, ip_address: str) -> bool:
        """إزالة IP من القائمة السوداء"""
        entry = self.db.query(IPBlacklist).filter(
            IPBlacklist.ip_address == ip_address
        ).first()

        if entry:
            entry.is_permanent = False
            entry.blocked_until = datetime.utcnow()
            self.db.commit()
            return True
        return False

    # ==========================================
    # حماية المحتوى
    # ==========================================

    def apply_watermark(
        self,
        book_id: int,
        user_id: int,
        download_id: str,
        ip_address: str = None
    ) -> ContentWatermark:
        """تطبيق علامة مائية على المحتوى"""
        import uuid

        watermark = ContentWatermark(
            book_id=book_id,
            user_id=user_id,
            download_id=download_id or str(uuid.uuid4()),
            watermark_data={
                "user_id": user_id,
                "book_id": book_id,
                "timestamp": datetime.utcnow().isoformat()
            },
            ip_address=ip_address
        )

        self.db.add(watermark)
        self.db.commit()
        self.db.refresh(watermark)
        return watermark

    def track_content_download(
        self,
        book_id: int,
        user_id: int,
        ip_address: str = None
    ) -> None:
        """تتبع تحميل المحتوى"""
        watermark = self.apply_watermark(
            book_id=book_id,
            user_id=user_id,
            download_id=str(datetime.utcnow().timestamp()),
            ip_address=ip_address
        )

        # تسجيل الحدث
        self.log_action(
            action=AuditAction.BOOK_DOWNLOAD,
            user_id=user_id,
            entity_type="book",
            entity_id=book_id,
            ip_address=ip_address,
            metadata={"watermark_id": watermark.id}
        )

    # ==========================================
    # تقارير السبام
    # ==========================================

    def report_spam(
        self,
        reporter_id: int,
        reported_user_id: int = None,
        reported_content_type: str = None,
        reported_content_id: int = None,
        spam_type: str = None,
        description: str = None
    ) -> SpamReport:
        """الإبلاغ عن سبام"""
        report = SpamReport(
            reporter_id=reporter_id,
            reported_user_id=reported_user_id,
            reported_content_type=reported_content_type,
            reported_content_id=reported_content_id,
            spam_type=spam_type,
            description=description
        )

        self.db.add(report)
        self.db.commit()
        self.db.refresh(report)
        return report

    def get_pending_reports(self, limit: int = 20) -> List[SpamReport]:
        """الحصول على التقارير المعلقة"""
        return self.db.query(SpamReport).filter(
            SpamReport.status == "pending"
        ).order_by(desc(SpamReport.created_at)).limit(limit).all()

    def resolve_report(
        self,
        report_id: int,
        reviewer_id: int,
        action: str,
        notes: str = None
    ) -> SpamReport:
        """حل تقرير"""
        report = self.db.query(SpamReport).get(report_id)
        if not report:
            raise ValueError("التقرير غير موجود")

        report.status = action  # resolved, dismissed
        report.reviewed_by = reviewer_id
        report.reviewed_at = datetime.utcnow()
        report.resolution_notes = notes

        # اتخاذ إجراء حسب نوع التقرير
        if action == "resolved" and report.reported_user_id:
            # يمكن حظر المستخدم هنا
            pass

        self.db.commit()
        self.db.refresh(report)
        return report

    # ==========================================
    # الأحداث الأمنية
    # ==========================================

    def log_security_event(
        self,
        event_type: str,
        user_id: int = None,
        user_telegram_id: int = None,
        threat_level: ThreatLevel = ThreatLevel.LOW,
        description: str = None,
        ip_address: str = None,
        metadata: dict = None
    ) -> SecurityEvent:
        """تسجيل حدث أمني"""
        event = SecurityEvent(
            user_id=user_id,
            user_telegram_id=user_telegram_id,
            event_type=event_type,
            threat_level=threat_level,
            description=description,
            ip_address=ip_address,
            metadata=metadata
        )

        self.db.add(event)

        # تنبيه للحالات الحرجة
        if threat_level in [ThreatLevel.HIGH, ThreatLevel.CRITICAL]:
            # يمكن إرسال إشعار للمشرف هنا
            pass

        self.db.commit()
        self.db.refresh(event)
        return event

    def get_security_events(
        self,
        user_id: int = None,
        threat_level: ThreatLevel = None,
        start_date: datetime = None,
        limit: int = 100
    ) -> List[SecurityEvent]:
        """الحصول على الأحداث الأمنية"""
        query = self.db.query(SecurityEvent)

        if user_id:
            query = query.filter(SecurityEvent.user_id == user_id)
        if threat_level:
            query = query.filter(SecurityEvent.threat_level == threat_level)
        if start_date:
            query = query.filter(SecurityEvent.created_at >= start_date)

        return query.order_by(desc(SecurityEvent.created_at)).limit(limit).all()

    def resolve_security_event(
        self,
        event_id: int,
        resolved_by: int,
        notes: str
    ) -> SecurityEvent:
        """حل حدث أمني"""
        event = self.db.query(SecurityEvent).get(event_id)
        if not event:
            raise ValueError("الحدث غير موجود")

        event.is_resolved = True
        event.resolved_by = resolved_by
        event.resolved_at = datetime.utcnow()
        event.resolution_notes = notes

        self.db.commit()
        self.db.refresh(event)
        return event

    # ==========================================
    # سجلات الوصول
    # ==========================================

    def log_access(
        self,
        user_id: int = None,
        user_telegram_id: int = None,
        access_type: str = "api",
        endpoint: str = None,
        method: str = None,
        status_code: int = None,
        response_time_ms: int = None,
        ip_address: str = None,
        user_agent: str = None
    ) -> AccessLog:
        """تسجيل الوصول"""
        log = AccessLog(
            user_id=user_id,
            user_telegram_id=user_telegram_id,
            access_type=access_type,
            endpoint=endpoint,
            method=method,
            status_code=status_code,
            response_time_ms=response_time_ms,
            ip_address=ip_address,
            user_agent=user_agent
        )

        self.db.add(log)
        self.db.commit()
        return log

    def get_access_stats(
        self,
        start_date: datetime = None,
        end_date: datetime = None
    ) -> dict:
        """إحصائيات الوصول"""
        query = self.db.query(AccessLog)
        if start_date:
            query = query.filter(AccessLog.created_at >= start_date)
        if end_date:
            query = query.filter(AccessLog.created_at <= end_date)

        total_requests = query.count()
        avg_response_time = query.with_entities(
            func.avg(AccessLog.response_time_ms)
        ).scalar() or 0

        error_count = query.filter(
            AccessLog.status_code >= 400
        ).count()

        return {
            "total_requests": total_requests,
            "average_response_time_ms": round(avg_response_time, 2),
            "error_count": error_count,
            "error_rate": round(error_count / total_requests * 100, 2) if total_requests > 0 else 0
        }

    # ==========================================
    # النسخ الاحتياطي
    # ==========================================

    def create_backup(
        self,
        backup_type: str = "full"
    ) -> BackupRecord:
        """إنشاء نسخة احتياطية"""
        backup = BackupRecord(
            backup_type=backup_type,
            status="pending"
        )

        self.db.add(backup)
        self.db.commit()
        self.db.refresh(backup)

        # يمكن تنفيذ النسخ الفعلي هنا
        # أو استخدام Celery لمهام الخلفية

        return backup

    def get_backup_status(self) -> dict:
        """الحصول على حالة النسخ الاحتياطي"""
        last_backup = self.db.query(BackupRecord).filter(
            BackupRecord.status == "completed"
        ).order_by(desc(BackupRecord.completed_at)).first()

        if not last_backup:
            return {"status": "no_backup", "last_backup": None}

        age_hours = (datetime.utcnow() - last_backup.completed_at).total_seconds() / 3600

        return {
            "status": "ok" if age_hours < 24 else "stale",
            "last_backup": last_backup.completed_at,
            "age_hours": round(age_hours, 2),
            "size": last_backup.file_size,
            "type": last_backup.backup_type
        }
