"""
Points Models - نموذج نظام النقاط
"""
import enum
from datetime import datetime
from sqlalchemy import Column, Integer, String, Enum, DateTime, Text, ForeignKey
from sqlalchemy.orm import relationship
from app.database import Base


class TransactionType(enum.Enum):
    """نوع المعاملة"""
    REFERRAL = "referral"
    DOWNLOAD = "download"
    REVIEW = "review"
    PURCHASE = "purchase"
    DEDUCTION = "deduction"
    COUPON = "coupon"
    GIFT = "gift"


class UserPoints(Base):
    """نموذج نقاط المستخدم"""
    __tablename__ = "user_points"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, unique=True)
    total_points = Column(Integer, default=0)
    current_balance = Column(Integer, default=0)
    lifetime_earned = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    user = relationship("User", backref="points")
    transactions = relationship("PointsTransaction", back_populates="user_points", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<UserPoints user={self.user_id} balance={self.current_balance}>"


class PointsTransaction(Base):
    """نموذج معاملات النقاط"""
    __tablename__ = "points_transactions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("user_points.id"), nullable=False)
    amount = Column(Integer, nullable=False)
    transaction_type = Column(Enum(TransactionType), nullable=False)
    description = Column(Text, nullable=True)
    reference_id = Column(String(100), nullable=True)  # For linking to related entity
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    user_points = relationship("UserPoints", back_populates="transactions")

    def __repr__(self):
        return f"<PointsTransaction {self.transaction_type} {self.amount}>"
