"""
Review Model - نموذج التقييمات
"""
from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, Float, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from app.database import Base


class Review(Base):
    """نموذج التقييم"""
    __tablename__ = "reviews"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    book_id = Column(Integer, ForeignKey("books.id"), nullable=False)
    rating = Column(Float, nullable=False)  # 1-5
    comment = Column(Text, nullable=True)
    is_approved = Column(Integer, default=1)  # 1=approved, 0=pending, -1=rejected
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    user = relationship("User", backref="reviews")
    book = relationship("Book", back_populates="reviews")

    def __repr__(self):
        return f"<Review user={self.user_id} book={self.book_id} rating={self.rating}>"
