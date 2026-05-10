"""
Favorite Model - نموذج المفضلة
"""
from datetime import datetime
from sqlalchemy import Column, Integer, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from app.database import Base


class Favorite(Base):
    """نموذج المفضلة"""
    __tablename__ = "favorites"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    book_id = Column(Integer, ForeignKey("books.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    user = relationship("User", backref="favorites")
    book = relationship("Book", back_populates="favorites")

    def __repr__(self):
        return f"<Favorite user={self.user_id} book={self.book_id}>"
