"""
Search Service - خدمة البحث
"""
from typing import List, Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import or_, func
from app.models.book import Book, BookStatus
from app.models.author import Author
from app.services.ai_service import ai_service


class SearchService:
    """خدمة البحث المتقدم"""

    def __init__(self, db: Session):
        self.db = db

    def text_search(
        self,
        query: str,
        limit: int = 20,
        include_authors: bool = True
    ) -> Tuple[List[Book], List[Author]]:
        """البحث النصي في الكتب والمؤلفين"""
        # البحث في الكتب
        books = self.db.query(Book).filter(
            or_(
                Book.title.ilike(f"%{query}%"),
                Book.description.ilike(f"%{query}%"),
                Book.isbn.ilike(f"%{query}%")
            ),
            Book.status == BookStatus.ACTIVE
        ).limit(limit).all()

        # البحث في المؤلفين
        authors = []
        if include_authors:
            authors = self.db.query(Author).filter(
                or_(
                    Author.name.ilike(f"%{query}%"),
                    Author.bio.ilike(f"%{query}%")
                )
            ).limit(limit).all()

        return books, authors

    async def semantic_search(
        self,
        query: str,
        limit: int = 10
    ) -> List[Tuple[Book, float]]:
        """البحث الدلالي باستخدام الذكاء الاصطناعي"""
        query_embedding = await ai_service.generate_embeddings(query)
        if not query_embedding:
            # fallback للبحث النصي
            books, _ = self.text_search(query, limit)
            return [(book, 0.0) for book in books]

        # في بيئة production، سيتم استخدام pgvector للبحث الدلالي
        # هنا نستخدم البحث النصي كـ fallback
        books, _ = self.text_search(query, limit * 2)
        results = []

        for book in books:
            # إنشاء embedding للكتاب
            book_text = f"{book.title} {book.description or ''}"
            book_embedding = await ai_service.generate_embeddings(book_text)

            if book_embedding:
                similarity = await ai_service.similarity_score(query, book_text)
                results.append((book, similarity))

        # ترتيب النتائج حسب التشابه
        results.sort(key=lambda x: x[1], reverse=True)
        return results[:limit]

    def search_by_author(self, author_name: str, limit: int = 20) -> List[Book]:
        """البحث عن كتب مؤلف معين"""
        books = self.db.query(Book).join(Author).filter(
            or_(
                Author.name.ilike(f"%{author_name}%"),
                Author.id.in_(
                    self.db.query(Author.id).filter(
                        Author.name.ilike(f"%{author_name}%")
                    )
                )
            ),
            Book.status == BookStatus.ACTIVE
        ).limit(limit).all()

        return books

    def search_by_category(self, category_name: str, limit: int = 20) -> List[Book]:
        """البحث عن كتب قسم معين"""
        from app.models.book import BookCategory

        category = self.db.query(BookCategory).filter(
            or_(
                BookCategory.name.ilike(f"%{category_name}%"),
                BookCategory.name_ar.ilike(f"%{category_name}%")
            )
        ).first()

        if not category:
            return []

        return self.db.query(Book).filter(
            Book.category_id == category.id,
            Book.status == BookStatus.ACTIVE
        ).order_by(Book.download_count.desc()).limit(limit).all()

    def search_by_year(self, year: int, limit: int = 20) -> List[Book]:
        """البحث عن كتب سنة معينة"""
        return self.db.query(Book).filter(
            Book.publication_year == year,
            Book.status == BookStatus.ACTIVE
        ).order_by(Book.download_count.desc()).limit(limit).all()

    def get_recommendations(
        self,
        book_id: int,
        limit: int = 5
    ) -> List[Book]:
        """الحصول على توصيات كتب مشابهة"""
        book = self.db.query(Book).filter(Book.id == book_id).first()
        if not book:
            return []

        # توصيات من نفس القسم
        if book.category_id:
            similar = self.db.query(Book).filter(
                Book.category_id == book.category_id,
                Book.id != book_id,
                Book.status == BookStatus.ACTIVE
            ).order_by(Book.average_rating.desc()).limit(limit).all()

            if len(similar) >= limit:
                return similar

        # أو نفس المؤلف
        if book.author_id:
            similar = self.db.query(Book).filter(
                Book.author_id == book.author_id,
                Book.id != book_id,
                Book.status == BookStatus.ACTIVE
            ).order_by(Book.download_count.desc()).limit(limit).all()

            if similar:
                return similar

        # ترتيب حسب التقييم
        return self.db.query(Book).filter(
            Book.id != book_id,
            Book.status == BookStatus.ACTIVE
        ).order_by(Book.average_rating.desc()).limit(limit).all()

    def advanced_search(
        self,
        query: Optional[str] = None,
        author: Optional[str] = None,
        category: Optional[str] = None,
        year_from: Optional[int] = None,
        year_to: Optional[int] = None,
        min_rating: Optional[float] = None,
        language: Optional[str] = None,
        limit: int = 20
    ) -> List[Book]:
        """بحث متقدم مع فلاتر متعددة"""
        q = self.db.query(Book).filter(Book.status == BookStatus.ACTIVE)

        if query:
            q = q.filter(
                or_(
                    Book.title.ilike(f"%{query}%"),
                    Book.description.ilike(f"%{query}%")
                )
            )

        if author:
            q = q.join(Author).filter(Author.name.ilike(f"%{author}%"))

        if category:
            from app.models.book import BookCategory
            cat = self.db.query(BookCategory).filter(
                BookCategory.name.ilike(f"%{category}%")
            ).first()
            if cat:
                q = q.filter(Book.category_id == cat.id)

        if year_from:
            q = q.filter(Book.publication_year >= year_from)

        if year_to:
            q = q.filter(Book.publication_year <= year_to)

        if min_rating:
            q = q.filter(Book.average_rating >= min_rating)

        if language:
            q = q.filter(Book.language == language)

        return q.order_by(Book.download_count.desc()).limit(limit).all()
