"""
Book Model - نموذج الكتاب
"""
import enum
from datetime import datetime
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Enum, Text, Float, ForeignKey
from sqlalchemy.orm import relationship
from app.database import Base


class BookStatus(enum.Enum):
    """حالة الكتاب"""
    ACTIVE = "active"
    INACTIVE = "inactive"
    ARCHIVED = "archived"
    PENDING = "pending"
    REJECTED = "rejected"


class Book(Base):
    """نموذج الكتاب"""
    __tablename__ = "books"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(500), nullable=False, index=True)
    author_id = Column(Integer, ForeignKey("authors.id"), nullable=True)
    description = Column(Text, nullable=True)
    category_id = Column(Integer, ForeignKey("book_categories.id"), nullable=True)
    file_path = Column(String(1000), nullable=True)
    cover_image = Column(String(1000), nullable=True)
    status = Column(Enum(BookStatus), default=BookStatus.PENDING, nullable=False)
    download_count = Column(Integer, default=0)
    view_count = Column(Integer, default=0)
    average_rating = Column(Float, default=0.0)
    total_ratings = Column(Integer, default=0)
    language = Column(String(10), default="ar")
    isbn = Column(String(20), nullable=True)
    publication_year = Column(Integer, nullable=True)
    page_count = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    rejection_reason = Column(Text, nullable=True)

    # Relationships
    category = relationship("BookCategory", back_populates="books")
    author = relationship("Author", back_populates="books")
    favorites = relationship("Favorite", back_populates="book", cascade="all, delete-orphan")
    downloads = relationship("DownloadHistory", back_populates="book", cascade="all, delete-orphan")
    reviews = relationship("Review", back_populates="book", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Book {self.id} - {self.title}>"


class BookCategory(Base):
    """نموذج قسم الكتب"""
    __tablename__ = "book_categories"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    name_ar = Column(String(255), nullable=True)
    name_en = Column(String(255), nullable=True)
    description = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True)
    parent_id = Column(Integer, ForeignKey("book_categories.id"), nullable=True)
    icon = Column(String(50), nullable=True)
    sort_order = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    books = relationship("Book", back_populates="category")
    parent = relationship("BookCategory", remote_side=[id], backref="subcategories")

    def __repr__(self):
        return f"<BookCategory {self.id} - {self.name}>"
