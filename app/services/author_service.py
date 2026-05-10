"""
Author Service - خدمة المؤلفين
"""
from typing import List, Optional
from sqlalchemy.orm import Session
from app.models.author import Author


class AuthorService:
    """خدمة إدارة المؤلفين"""

    def __init__(self, db: Session):
        self.db = db

    def create(
        self,
        name: str,
        bio: Optional[str] = None,
        image_url: Optional[str] = None,
        birth_date=None,
        death_date=None,
        country: Optional[str] = None,
        category_id: Optional[int] = None   # الوسيط الجديد
    ) -> Author:
        """إنشاء مؤلف جديد"""
        author = Author(
            name=name,
            bio=bio,
            image_url=image_url,
            birth_date=birth_date,
            death_date=death_date,
            country=country,
            category_id=category_id
        )
        self.db.add(author)
        self.db.commit()
        self.db.refresh(author)
        return author

    def update(
        self,
        author_id: int,
        name: Optional[str] = None,
        bio: Optional[str] = None,
        image_url: Optional[str] = None,
        birth_date=None,
        death_date=None,
        country: Optional[str] = None,
        category_id: Optional[int] = None   # إضافة اختيارية
    ) -> Optional[Author]:
        """تحديث مؤلف"""
        author = self.get_by_id(author_id)
        if not author:
            return None

        if name is not None:
            author.name = name
        if bio is not None:
            author.bio = bio
        if image_url is not None:
            author.image_url = image_url
        if birth_date is not None:
            author.birth_date = birth_date
        if death_date is not None:
            author.death_date = death_date
        if country is not None:
            author.country = country
        if category_id is not None:          # تحديث القسم إذا تم إرساله
            author.category_id = category_id

        self.db.commit()
        self.db.refresh(author)
        return author

    def delete(self, author_id: int) -> bool:
        """حذف مؤلف"""
        author = self.get_by_id(author_id)
        if not author:
            return False

        self.db.delete(author)
        self.db.commit()
        return True

    def get_by_id(self, author_id: int) -> Optional[Author]:
        """الحصول على مؤلف بالمعرف"""
        return self.db.query(Author).filter(Author.id == author_id).first()

    def get_by_name(self, name: str) -> Optional[Author]:
        """الحصول على مؤلف بالاسم"""
        return self.db.query(Author).filter(Author.name == name).first()

    def list_all(self) -> List[Author]:
        """عرض جميع المؤلفين"""
        return self.db.query(Author).order_by(Author.name).all()

    def search(self, query: str) -> List[Author]:
        """البحث عن مؤلف"""
        return self.db.query(Author).filter(
            Author.name.ilike(f"%{query}%")
        ).order_by(Author.name).all()

    def get_or_create(self, name: str, bio: Optional[str] = None) -> Author:
        """الحصول على مؤلف أو إنشاؤه إذا لم يكن موجوداً"""
        author = self.get_by_name(name)
        if author:
            return author
        return self.create(name=name, bio=bio)

    def count_books(self, author_id: int) -> int:
        """عدد كتب المؤلف"""
        author = self.get_by_id(author_id)
        if not author:
            return 0
        return len(author.books)

    def get_popular(self, limit: int = 10) -> List[Author]:
        """الحصول على أكثر المؤلفين شهرة"""
        from sqlalchemy import func
        from app.models.book import Book, BookStatus

        return self.db.query(
            Author,
            func.count(Book.id).label('book_count')
        ).join(Book).group_by(Author.id).order_by(
            func.count(Book.id).desc()
        ).limit(limit).all()
        
   def get_authors_by_category(self, category_id: int) -> List[Author]:
    """جلب المؤلفين المرتبطين مباشرة بهذا القسم"""
    return self.db.query(Author).filter(Author.category_id == category_id).all()
