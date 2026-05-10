"""
Author Model - نموذج المؤلف
"""
from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime
from sqlalchemy.orm import relationship
from app.database import Base


class Author(Base):
    """نموذج المؤلف"""
    __tablename__ = "authors"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False, index=True)
    bio = Column(Text, nullable=True)
    image_url = Column(String(1000), nullable=True)
    birth_date = Column(DateTime, nullable=True)
    death_date = Column(DateTime, nullable=True)
    country = Column(String(100), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    books = relationship("Book", back_populates="author")

    def __repr__(self):
        return f"<Author {self.id} - {self.name}>"
