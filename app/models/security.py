"""
Security & Audit Models - نماذج الأمان والتدقيق
"""
import enum
from datetime import datetime
from sqlalchemy import Column, Integer, String, Enum, DateTime, Boolean, ForeignKey, JSON, Text
# IPAddress removed from import
from sqlalchemy.orm import relationship
from app.database import Base


class AuditAction(enum.Enum):
    """أنواع إجراءات التدقيق"""
    # المستخدم
    USER_LOGIN = "user_login"
    USER_LOGOUT = "user_logout"
    USER_REGISTER = "user_register"
    USER_PROFILE_UPDATE = "user_profile_update"
    USER_PASSWORD_CHANGE = "user_password_change"

    # الكتب
    BOOK_CREATE = "book_create"
    BOOK_UPDATE = "book_update"
    BOOK_DELETE = "book_delete"
    BOOK_DOWNLOAD = "book_download"
    BOOK_VIEW = "book_view"

    # إدارة
    ADMIN_LOGIN = "admin_login"
    ADMIN_ACTION = "admin_action"
    PERMISSION_CHANGE = "permission_change"

    # المال
    POINTS_EARN = "points_earn"
    POINTS_SPEND = "points_spend"
    POINTS_TRANSFER = "points_transfer"
    PURCHASE = "purchase"
    SALE = "sale"

    # الأمان
    LOGIN_FAILED = "login_failed"
    SUSPICIOUS_ACTIVITY = "suspicious_activity"
    RATE_LIMIT_EXCEEDED = "rate_limit_exceeded"
    IP_BLOCKED = "ip_blocked"
    USER_BANNED = "user_banned"
    USER_UNBANNED = "user_unbanned"


class ThreatLevel(enum.Enum):
    """مستوى التهديد"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class AuditLog(Base):
    """سجل التدقيق"""
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)

    # المستخدم والصلاحية
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    user_telegram_id = Column(Integer, nullable=True)
    admin_id = Column(Integer, ForeignKey("users.id"), nullable=True)

    # نوع الإجراء
    action = Column(Enum(AuditAction), nullable=False)

    # التفاصيل
    entity_type = Column(String(50), nullable=True)  # book, user, transaction
    entity_id = Column(Integer, nullable=True)

    # البيانات
    old_value = Column(JSON, nullable=True)
    new_value = Column(JSON, nullable=True)
    extra_data = Column(JSON, nullable=True)  # تم تغيير الاسم من metadata

    # معلومات الاتصال
    ip_address = Column(String(50), nullable=True)
    user_agent = Column(String(500), nullable=True)
    device_info = Column(JSON, nullable=True)

    # النتيجة
    status = Column(String(20), default="success")  # success, failed
    error_message = Column(Text, nullable=True)

    # التوقيت
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    user = relationship("User", foreign_keys=[user_id])
    admin = relationship("User", foreign_keys=[admin_id])

    def __repr__(self):
        return f"<AuditLog {self.id} action={self.action}>"


class SecurityEvent(Base):
    """حدث أمني"""
    __tablename__ = "security_events"

    id = Column(Integer, primary_key=True, index=True)

    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    user_telegram_id = Column(Integer, nullable=True)

    # نوع التهديد
    event_type = Column(String(100), nullable=False)
    threat_level = Column(Enum(ThreatLevel), default=ThreatLevel.LOW)

    # التفاصيل
    description = Column(Text, nullable=True)
    source = Column(String(50), nullable=True)  # api, bot, admin

    # سياق الحدث
    ip_address = Column(String(50), nullable=True)
    user_agent = Column(String(500), nullable=True)
    endpoint = Column(String(500), nullable=True)
    request_data = Column(JSON, nullable=True)

    # النتيجة
    is_resolved = Column(Boolean, default=False)
    resolved_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    resolved_at = Column(DateTime, nullable=True)
    resolution_notes = Column(Text, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<SecurityEvent {self.id} type={self.event_type}>"


class RateLimit(Base):
    """حدود معدل الطلبات"""
    __tablename__ = "rate_limits"

    id = Column(Integer, primary_key=True, index=True)

    identifier = Column(String(100), nullable=False)  # user_id, ip, endpoint
    identifier_type = Column(String(20), nullable=False)  # user, ip, global

    #界限
    limit_type = Column(String(50), default="requests")  # requests, messages, downloads
    limit_value = Column(Integer, default=100)  # max requests
    window_seconds = Column(Integer, default=60)  # time window

    # العداد
    current_count = Column(Integer, default=0)
    window_start = Column(DateTime, nullable=True)

    # حالة الحظر
    is_blocked = Column(Boolean, default=False)
    blocked_until = Column(DateTime, nullable=True)
    block_reason = Column(Text, nullable=True)

    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<RateLimit {self.identifier}>"

    def is_rate_limited(self) -> bool:
        """هل تم تجاوز الحد"""
        if self.is_blocked:
            if self.blocked_until and datetime.utcnow() < self.blocked_until:
                return True
            else:
                self.is_blocked = False
        return self.current_count >= self.limit_value

    def increment(self) -> None:
        """زيادة العداد"""
        now = datetime.utcnow()
        if self.window_start is None or (now - self.window_start).total_seconds() > self.window_seconds:
            self.current_count = 1
            self.window_start = now
        else:
            self.current_count += 1


class IPBlacklist(Base):
    """قائمة IPs المحظورة"""
    __tablename__ = "ip_blacklist"

    id = Column(Integer, primary_key=True, index=True)
    ip_address = Column(String(50), nullable=False, unique=True)

    # سبب الحظر
    reason = Column(Text, nullable=True)
    threat_level = Column(Enum(ThreatLevel), default=ThreatLevel.MEDIUM)

    # صاحب القرار
    blocked_by = Column(Integer, ForeignKey("users.id"), nullable=True)

    # مدة الحظر
    is_permanent = Column(Boolean, default=False)
    blocked_until = Column(DateTime, nullable=True)

    # إحصائيات
    total_attempts = Column(Integer, default=0)
    last_attempt_at = Column(DateTime, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<IPBlacklist {self.ip_address}>"

    def is_active(self) -> bool:
        """هل الحظر لا يزال نشطاً"""
        if self.is_permanent:
            return True
        if self.blocked_until and datetime.utcnow() < self.blocked_until:
            return True
        return False


class SpamReport(Base):
    """تقرير السبام"""
    __tablename__ = "spam_reports"

    id = Column(Integer, primary_key=True, index=True)

    reporter_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    reported_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    reported_content_type = Column(String(50), nullable=True)  # message, review, book
    reported_content_id = Column(Integer, nullable=True)

    # تفاصيل التقرير
    spam_type = Column(String(50), nullable=True)  # advertisement, harassment, inappropriate, etc.
    description = Column(Text, nullable=True)
    evidence = Column(JSON, nullable=True)  # روابط، صور

    # الحالة
    status = Column(String(20), default="pending")  # pending, investigating, resolved, dismissed
    reviewed_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    reviewed_at = Column(DateTime, nullable=True)
    resolution_notes = Column(Text, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    reporter = relationship("User", foreign_keys=[reporter_id])
    reported_user = relationship("User", foreign_keys=[reported_user_id])
    reviewer = relationship("User", foreign_keys=[reviewed_by])

    def __repr__(self):
        return f"<SpamReport {self.id}>"


class ContentWatermark(Base):
    """علامة مائية للمحتوى"""
    __tablename__ = "content_watermarks"

    id = Column(Integer, primary_key=True, index=True)
    book_id = Column(Integer, ForeignKey("books.id"), nullable=False)

    # معلومات العلامة
    watermark_type = Column(String(50), default="visible")  # visible, invisible, metadata

    # البيانات المضمنة
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    download_id = Column(String(100), nullable=False)
    watermark_data = Column(JSON, nullable=True)

    # التوقيت والمكان
    applied_at = Column(DateTime, default=datetime.utcnow)
    file_path = Column(String(500), nullable=True)

    # حالة العلامة
    is_active = Column(Boolean, default=True)

    # معلومات إضافية
    device_info = Column(JSON, nullable=True)
    ip_address = Column(String(50), nullable=True)

    # Relationships
    book = relationship("Book", backref="watermarks")
    user = relationship("User", backref="watermarks")

    def __repr__(self):
        return f"<ContentWatermark book={self.book_id}>"


class AccessLog(Base):
    """سجل الوصول"""
    __tablename__ = "access_logs"

    id = Column(Integer, primary_key=True, index=True)

    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    user_telegram_id = Column(Integer, nullable=True)

    # نوع الوصول
    access_type = Column(String(50), nullable=False)  # api, bot_command, admin, web
    endpoint = Column(String(500), nullable=True)
    method = Column(String(10), nullable=True)  # GET, POST, etc.

    # الاستجابة
    status_code = Column(Integer, nullable=True)
    response_time_ms = Column(Integer, nullable=True)

    # معلومات الاتصال
    ip_address = Column(String(50), nullable=True)
    user_agent = Column(String(500), nullable=True)
    session_id = Column(String(100), nullable=True)

    # البيانات
    request_data = Column(JSON, nullable=True)
    response_data = Column(JSON, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<AccessLog {self.id}>"


class BackupRecord(Base):
    """سجل النسخ الاحتياطي"""
    __tablename__ = "backup_records"

    id = Column(Integer, primary_key=True, index=True)

    # معلومات النسخة
    backup_type = Column(String(50), default="full")  # full, incremental, database_only
    file_path = Column(String(500), nullable=True)
    file_size = Column(Integer, nullable=True)

    # حالة النسخة
    status = Column(String(20), default="pending")  # pending, running, completed, failed
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)

    # الأخطاء
    error_message = Column(Text, nullable=True)

    # معلومات إضافية
    compressed = Column(Boolean, default=True)
    encrypted = Column(Boolean, default=False)
    retention_days = Column(Integer, default=30)

    # التحقق
    checksum = Column(String(100), nullable=True)
    verified_at = Column(DateTime, nullable=True)
    verified_by = Column(Integer, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<BackupRecord {self.id} type={self.backup_type}>"
