"""
Pack Model - نموذج الباقات
"""
import enum
from datetime import datetime
from sqlalchemy import Column, Integer, String, Enum, DateTime, Boolean, Text
from sqlalchemy.orm import relationship
from app.database import Base


class PackType(enum.Enum):
    """نوع الباقة"""
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    YEARLY = "yearly"
    LIFETIME = "lifetime"


class Pack(Base):
    """نموذج الباقة"""
    __tablename__ = "packs"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    name_ar = Column(String(100), nullable=True)
    pack_type = Column(Enum(PackType), nullable=False)
    price = Column(Integer, nullable=False)  # Price in points
    duration_days = Column(Integer, nullable=True)  # NULL for lifetime
    features = Column(Text, nullable=True)  # JSON string of features
    is_active = Column(Boolean, default=True)
    sort_order = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<Pack {self.name}>"

    def is_lifetime(self) -> bool:
        """التحقق إذا كانت الباقة مدى الحياة"""
        return self.pack_type == PackType.LIFETIME or self.duration_days is None
