"""
Book Service - خدمة الكتب
"""
from typing import List, Optional
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import desc, func
from app.models.book import Book, BookCategory, BookStatus
from app.models.author import Author
from app.models.review import Review
from app.models.download_history import DownloadHistory


class BookService:
    """خدمة إدارة الكتب"""

    def __init__(self, db: Session):
        self.db = db

    def get_book(self, book_id: int) -> Optional[Book]:
        """الحصول على كتاب بالمعرف"""
        return self.db.query(Book).filter(Book.id == book_id).first()

    def get_book_by_title(self, title: str) -> Optional[Book]:
        """الحصول على كتاب بالعنوان"""
        return self.db.query(Book).filter(Book.title == title).first()

    def create_book(
        self,
        title: str,
        author_id: Optional[int] = None,
        description: Optional[str] = None,
        category_id: Optional[int] = None,
        file_path: Optional[str] = None,
        cover_image: Optional[str] = None,
        language: str = "ar",
        isbn: Optional[str] = None,
        publication_year: Optional[int] = None,
        page_count: Optional[int] = None,
        status: BookStatus = BookStatus.PENDING
    ) -> Book:
        """إنشاء كتاب جديد"""
        book = Book(
            title=title,
            author_id=author_id,
            description=description,
            category_id=category_id,
            file_path=file_path,
            cover_image=cover_image,
            language=language,
            isbn=isbn,
            publication_year=publication_year,
            page_count=page_count,
            status=status
        )
        self.db.add(book)
        self.db.commit()
        self.db.refresh(book)
        return book

    def update_book(
        self,
        book_id: int,
        title: Optional[str] = None,
        author_id: Optional[int] = None,
        description: Optional[str] = None,
        category_id: Optional[int] = None,
        file_path: Optional[str] = None,
        cover_image: Optional[str] = None,
        language: Optional[str] = None,
        isbn: Optional[str] = None,
        publication_year: Optional[int] = None,
        page_count: Optional[int] = None,
        status: Optional[BookStatus] = None,
        rejection_reason: Optional[str] = None
    ) -> Optional[Book]:
        """تحديث كتاب"""
        book = self.get_book(book_id)
        if not book:
            return None

        if title is not None:
            book.title = title
        if author_id is not None:
            book.author_id = author_id
        if description is not None:
            book.description = description
        if category_id is not None:
            book.category_id = category_id
        if file_path is not None:
            book.file_path = file_path
        if cover_image is not None:
            book.cover_image = cover_image
        if language is not None:
            book.language = language
        if isbn is not None:
            book.isbn = isbn
        if publication_year is not None:
            book.publication_year = publication_year
        if page_count is not None:
            book.page_count = page_count
        if status is not None:
            book.status = status
        if rejection_reason is not None:
            book.rejection_reason = rejection_reason

        self.db.commit()
        self.db.refresh(book)
        return book

    def delete_book(self, book_id: int) -> bool:
        """حذف كتاب"""
        book = self.get_book(book_id)
        if not book:
            return False

        self.db.delete(book)
        self.db.commit()
        return True

    def approve_book(self, book_id: int) -> Optional[Book]:
        """الموافقة على كتاب"""
        return self.update_book(book_id, status=BookStatus.ACTIVE)

    def reject_book(self, book_id: int, reason: Optional[str] = None) -> Optional[Book]:
        """رفض كتاب"""
        return self.update_book(book_id, status=BookStatus.REJECTED, rejection_reason=reason)

    def get_trending_books(self, limit: int = 10) -> List[Book]:
        """الحصول على الكتب الرائجة"""
        return self.db.query(Book).filter(
            Book.status == BookStatus.ACTIVE
        ).order_by(
            desc(Book.download_count)
        ).limit(limit).all()

    def get_featured_books(self, limit: int = 10) -> List[Book]:
        """الحصول على الكتب المميزة"""
        return self.db.query(Book).filter(
            Book.status == BookStatus.ACTIVE
        ).order_by(
            desc(Book.average_rating)
        ).limit(limit).all()

    def get_recent_books(self, limit: int = 10) -> List[Book]:
        """الحصول على أحدث الكتب"""
        return self.db.query(Book).filter(
            Book.status == BookStatus.ACTIVE
        ).order_by(
            desc(Book.created_at)
        ).limit(limit).all()

    def get_books_by_category(self, category_id: int, limit: int = 20, offset: int = 0) -> List[Book]:
        """الحصول على كتب القسم"""
        return self.db.query(Book).filter(
            Book.category_id == category_id,
            Book.status == BookStatus.ACTIVE
        ).order_by(
            desc(Book.created_at)
        ).limit(limit).offset(offset).all()

    def get_pending_books(self, limit: int = 20) -> List[Book]:
        """الحصول على الكتب قيد المراجعة"""
        return self.db.query(Book).filter(
            Book.status == BookStatus.PENDING
        ).order_by(
            Book.created_at
        ).limit(limit).all()

    def search_books(self, query: str, limit: int = 20) -> List[Book]:
        """البحث في الكتب"""
        return self.db.query(Book).filter(
            Book.title.ilike(f"%{query}%"),
            Book.status == BookStatus.ACTIVE
        ).limit(limit).all()

    def add_rating(self, book_id: int, rating: float) -> Optional[Book]:
        """إضافة تقييم للكتاب"""
        book = self.get_book(book_id)
        if not book:
            return None

        # حساب المتوسط الجديد
        total = book.average_rating * book.total_ratings + rating
        book.total_ratings += 1
        book.average_rating = total / book.total_ratings

        self.db.commit()
        self.db.refresh(book)
        return book

    def increment_download(self, book_id: int) -> Optional[Book]:
        """زيادة عدد التحميلات"""
        book = self.get_book(book_id)
        if not book:
            return None

        book.download_count += 1
        self.db.commit()
        self.db.refresh(book)
        return book

    def get_all_books(self, status: BookStatus = None, limit: int = None, offset: int = 0):
        query = self.db.query(Book)
        if status is not None:
            query = query.filter(Book.status == status)
        if limit:
            query = query.limit(limit)
        if offset:
            query = query.offset(offset)
        return query.all()

    def count_books(self, status: Optional[BookStatus] = None) -> int:
        """عدد الكتب"""
        query = self.db.query(func.count(Book.id))
        if status:
            query = query.filter(Book.status == status)
        return query.scalar()
        
    def get_books_by_category_and_author(self, category_id: int, author_id: int, limit: int = None, offset: int = 0) -> List[Book]:
        """جلب كتب قسم معين لمؤلف معين"""
        query = self.db.query(Book).filter(
            Book.category_id == category_id,
            Book.author_id == author_id,
            Book.status == BookStatus.ACTIVE
        )
        if limit:
            query = query.limit(limit).offset(offset)
        return query.all()

    def get_books_by_author(self, author_id: int, limit: int = 20, offset: int = 0) -> List[Book]:
        """الحصول على كتب مؤلف معين"""
        query = self.db.query(Book).filter(
            Book.author_id == author_id,
            Book.status == BookStatus.ACTIVE
        ).order_by(desc(Book.created_at))
        if limit is not None:
            query = query.limit(limit)
        if offset:
            query = query.offset(offset)
        return query.all()

    
    def get_statistics(self) -> dict:
        """إحصائيات الكتب"""
        total = self.count_books()
        active = self.count_books(BookStatus.ACTIVE)
        pending = self.count_books(BookStatus.PENDING)
        rejected = self.count_books(BookStatus.REJECTED)

        total_downloads = self.db.query(func.sum(Book.download_count)).scalar() or 0
        avg_rating = self.db.query(func.avg(Book.average_rating)).scalar() or 0

        return {
            "total": total,
            "active": active,
            "pending": pending,
            "rejected": rejected,
            "total_downloads": total_downloads,
            "average_rating": round(avg_rating, 2)
        }
