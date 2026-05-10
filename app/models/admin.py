"""
Admin Models - نماذج المشرفين
"""
import enum
from datetime import datetime
from sqlalchemy import Column, Integer, String, Enum, DateTime, Text, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from app.database import Base


class AdminRole(enum.Enum):
    """دور المشرف"""
    OWNER = "owner"
    ADMIN = "admin"
    MODERATOR = "moderator"


class AdminUser(Base):
    """نموذج المستخدم المشرف"""
    __tablename__ = "admin_users"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, unique=True)
    role = Column(Enum(AdminRole), default=AdminRole.MODERATOR, nullable=False)
    is_active = Column(Boolean, default=True)
    can_manage_books = Column(Boolean, default=False)
    can_manage_users = Column(Boolean, default=False)
    can_manage_categories = Column(Boolean, default=False)
    can_manage_authors = Column(Boolean, default=False)
    can_view_stats = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    user = relationship("User", backref="admin_profile")
    logs = relationship("AdminLog", back_populates="admin", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<AdminUser {self.user_id} role={self.role}>"

    def has_permission(self, permission: str) -> bool:
        """التحقق من صلاحية معينة"""
        if self.role == AdminRole.OWNER:
            return True
        return getattr(self, f"can_{permission}", False)


class AdminLog(Base):
    """نموذج سجل المشرفين"""
    __tablename__ = "admin_logs"

    id = Column(Integer, primary_key=True, index=True)
    admin_id = Column(Integer, ForeignKey("admin_users.id"), nullable=False)
    action = Column(String(100), nullable=False)
    entity_type = Column(String(50), nullable=True)  # book, user, category, etc.
    entity_id = Column(Integer, nullable=True)
    details = Column(Text, nullable=True)
    ip_address = Column(String(50), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    admin = relationship("AdminUser", back_populates="logs")

    def __repr__(self):
        return f"<AdminLog {self.action} by {self.admin_id}>"
