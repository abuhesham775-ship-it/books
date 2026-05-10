"""
Coupon Model - نموذج الكوبونات
"""
import enum
from datetime import datetime
from sqlalchemy import Column, Integer, String, Enum, DateTime, Boolean, Text, ForeignKey
from sqlalchemy.orm import relationship
from app.database import Base


class CouponType(enum.Enum):
    """نوع الكوبون"""
    PERCENTAGE = "percentage"
    FIXED = "fixed"
    POINTS = "points"


class Coupon(Base):
    """نموذج الكوبون"""
    __tablename__ = "coupons"

    id = Column(Integer, primary_key=True, index=True)
    code = Column(String(50), unique=True, nullable=False, index=True)
    coupon_type = Column(Enum(CouponType), nullable=False)
    value = Column(Integer, nullable=False)  # Percentage or fixed amount or points
    min_purchase = Column(Integer, default=0)
    max_uses = Column(Integer, nullable=True)
    used_count = Column(Integer, default=0)
    is_active = Column(Boolean, default=True)
    starts_at = Column(DateTime, nullable=True)
    expires_at = Column(DateTime, nullable=True)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)  # For user-specific coupons
    user = relationship("User", backref="coupons")

    def __repr__(self):
        return f"<Coupon {self.code}>"

    def is_valid(self) -> bool:
        """التحقق من صحة الكوبون"""
        if not self.is_active:
            return False
        if self.max_uses and self.used_count >= self.max_uses:
            return False
        now = datetime.utcnow()
        if self.starts_at and now < self.starts_at:
            return False
        if self.expires_at and now > self.expires_at:
            return False
        return True
