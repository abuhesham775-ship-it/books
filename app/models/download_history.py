"""
DownloadHistory Model - نموذج سجل التحميلات
"""
from datetime import datetime
from sqlalchemy import Column, Integer, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from app.database import Base


class DownloadHistory(Base):
    """نموذج سجل التحميلات"""
    __tablename__ = "download_histories"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    book_id = Column(Integer, ForeignKey("books.id"), nullable=False)
    downloaded_at = Column(DateTime, default=datetime.utcnow)
    file_size = Column(Integer, nullable=True)  # Size in bytes

    # Relationships
    user = relationship("User", backref="downloads")
    book = relationship("Book", back_populates="downloads")

    def __repr__(self):
        return f"<DownloadHistory user={self.user_id} book={self.book_id}>"
