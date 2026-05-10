"""
User Model - نموذج المستخدم
"""
import enum
from datetime import datetime
from sqlalchemy import Column, Integer, BigInteger, String, Boolean, DateTime, Enum, Text  # أضف BigInteger
from sqlalchemy.orm import relationship
from app.database import Base


class UserStatus(enum.Enum):
    """حالة المستخدم"""
    ACTIVE = "active"
    INACTIVE = "inactive"
    BANNED = "banned"
    SUSPENDED = "suspended"


class User(Base):
    """نموذج المستخدم"""
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    telegram_id = Column(BigInteger, unique=True, index=True, nullable=False)  # غير إلى BigInteger
    username = Column(String(255), nullable=True)
    first_name = Column(String(255), nullable=True)
    last_name = Column(String(255), nullable=True)
    status = Column(Enum(UserStatus), default=UserStatus.ACTIVE, nullable=False)
    total_downloads = Column(Integer, default=0)
    level = Column(Integer, default=1)
    is_premium = Column(Boolean, default=False)
    language = Column(String(10), default="ar")
    referral_code = Column(String(20), unique=True, nullable=True)
    referred_by = Column(BigInteger, nullable=True)  # يُفضل أيضاً BigInteger
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_active = Column(DateTime, nullable=True)
    bio = Column(Text, nullable=True)

    # Relationships
    smart_notifications = relationship("SmartNotification", back_populates="user", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<User {self.telegram_id} - {self.first_name}>"
