"""
Recommendation Service - خدمة التوصيات الذكية
نظام تحليل سلوك المستخدم والتوصيات المخصصة
"""
from typing import List, Optional, Tuple, Dict
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import desc, func, and_
from app.models.recommendations import (
    UserBehavior, UserPreference, Recommendation, ReadingHistory,
    RecommendationType, UserSegment, UserSegmentMembership
)
from app.models.book import Book, BookStatus
from app.models.user import User
from app.services.ai_service import ai_service


class RecommendationService:
    """خدمة التوصيات الذكية"""

    def __init__(self, db: Session):
        self.db = db

    # ==========================================
    # تسجيل السلوك
    # ==========================================

    def record_behavior(
        self,
        user_id: int,
        behavior_type: str,
        book_id: int = None,
        category_id: int = None,
        author_id: int = None,
        search_query: str = None,
        rating_given: float = None,
        time_spent: int = None,
        metadata: dict = None
    ) -> UserBehavior:
        """تسجيل سلوك مستخدم"""
        behavior = UserBehavior(
            user_id=user_id,
            behavior_type=behavior_type,
            book_id=book_id,
            category_id=category_id,
            author_id=author_id,
            search_query=search_query,
            rating_given=rating_given,
            time_spent_seconds=time_spent,
            metadata=metadata
        )

        self.db.add(behavior)
        self.db.commit()
        self.db.refresh(behavior)

        # تحديث التفضيلات بعد كل سلوك
        self.update_preferences(user_id)

        return behavior

    def update_preferences(self, user_id: int) -> UserPreference:
        """تحديث تفضيلات المستخدم بناءً على سلوكه"""
        pref = self.get_or_create_preferences(user_id)

        # تحليل الكتب المفضلة
        favorites = self.db.query(UserBehavior).filter(
            UserBehavior.user_id == user_id,
            UserBehavior.behavior_type == "favorite",
            UserBehavior.book_id.isnot(None)
        ).all()

        if favorites:
            book_ids = [f.book_id for f in favorites]
            books = self.db.query(Book).filter(Book.id.in_(book_ids)).all()

            # التصنيفات المفضلة
            categories = [b.category_id for b in books if b.category_id]
            if categories:
                pref.preferred_categories = list(set(categories))

            # المؤلفين المفضلين
            authors = [b.author_id for b in books if b.author_id]
            if authors:
                pref.preferred_authors = list(set(authors))

        # حساب درجة التفاعل
        recent_behaviors = self.db.query(UserBehavior).filter(
            UserBehavior.user_id == user_id,
            UserBehavior.created_at >= datetime.utcnow() - timedelta(days=7)
        ).count()

        pref.engagement_score = min(recent_behaviors / 50 * 100, 100)
        pref.last_recalculated = datetime.utcnow()

        self.db.commit()
        self.db.refresh(pref)
        return pref

    def get_or_create_preferences(self, user_id: int) -> UserPreference:
        """الحصول على تفضيلات أو إنشاؤها"""
        pref = self.db.query(UserPreference).filter(
            UserPreference.user_id == user_id
        ).first()

        if not pref:
            pref = UserPreference(user_id=user_id)
            self.db.add(pref)
            self.db.commit()
            self.db.refresh(pref)

        return pref

    # ==========================================
    # التوصيات
    # ==========================================

    def get_personalized_recommendations(
        self,
        user_id: int,
        limit: int = 10,
        force_refresh: bool = False
    ) -> List[Book]:
        """الحصول على توصيات مخصصة للمستخدم"""
        # التحقق من التوصيات المحفوظة
        if not force_refresh:
            saved = self.db.query(Recommendation).filter(
                Recommendation.user_id == user_id,
                Recommendation.expires_at > datetime.utcnow(),
                Recommendation.is_shown < 3
            ).order_by(desc(Recommendation.score)).limit(limit).all()

            if len(saved) >= limit:
                return [self.db.query(Book).get(r.book_id) for r in saved[:limit]]

        # الحصول على تفضيلات المستخدم
        pref = self.get_or_create_preferences(user_id)

        # بناء التوصيات
        recommendations = []

        # 1. كتب من تصنيفات مفضلة
        if pref.preferred_categories:
            similar = self.db.query(Book).filter(
                Book.category_id.in_(pref.preferred_categories),
                Book.status == BookStatus.ACTIVE
            ).order_by(desc(Book.average_rating)).limit(limit // 2).all()
            recommendations.extend(similar)

        # 2. كتب من مؤلفين مفضلين
        if pref.preferred_authors:
            author_books = self.db.query(Book).filter(
                Book.author_id.in_(pref.preferred_authors),
                Book.status == BookStatus.ACTIVE
            ).order_by(desc(Book.download_count)).limit(limit // 2).all()
            recommendations.extend(author_books)

        # 3. كتب رائجة جديدة
        trending = self.db.query(Book).filter(
            Book.status == BookStatus.ACTIVE,
            Book.created_at >= datetime.utcnow() - timedelta(days=30)
        ).order_by(desc(Book.download_count)).limit(limit // 3).all()
        recommendations.extend(trending)

        # إزالة التكرارات
        seen = set()
        unique_recommendations = []
        for book in recommendations:
            if book.id not in seen:
                seen.add(book.id)
                unique_recommendations.append(book)

        # حفظ التوصيات
        for book in unique_recommendations[:limit]:
            self.save_recommendation(
                user_id=user_id,
                book_id=book.id,
                rec_type=RecommendationType.PERSONALIZED,
                score=0.8,
                reason="مخصص لك"
            )

        return unique_recommendations[:limit]

    async def get_similar_books(
        self,
        book_id: int,
        limit: int = 5,
        use_ai: bool = True
    ) -> List[Book]:
        """الحصول على كتب مشابهة لكتاب معين"""
        book = self.db.query(Book).filter(Book.id == book_id).first()
        if not book:
            return []

        similar = []

        # كتب من نفس المؤلف
        if book.author_id:
            author_books = self.db.query(Book).filter(
                Book.author_id == book.author_id,
                Book.id != book_id,
                Book.status == BookStatus.ACTIVE
            ).limit(limit // 2).all()
            similar.extend(author_books)

        # كتب من نفس التصنيف
        if book.category_id:
            category_books = self.db.query(Book).filter(
                Book.category_id == book.category_id,
                Book.id != book_id,
                Book.status == BookStatus.ACTIVE
            ).order_by(desc(Book.average_rating)).limit(limit).all()
            similar.extend(category_books)

        # استخدام AI للتشابه الدلالي
        if use_ai and book.description:
            try:
                book_text = f"{book.title} {book.description}"
                similar_ai = await self.get_ai_similar_books(book_text, limit)
                similar.extend(similar_ai)
            except Exception:
                pass

        # إزالة التكرارات
        seen = set()
        unique = []
        for b in similar:
            if b.id not in seen:
                seen.add(b.id)
                unique.append(b)

        return unique[:limit]

    async def get_ai_similar_books(
        self,
        book_text: str,
        limit: int = 5
    ) -> List[Book]:
        """استخدام AI لإيجاد كتب مشابهة"""
        # البحث عن كتب ذات تشابه عالي
        all_books = self.db.query(Book).filter(
            Book.status == BookStatus.ACTIVE,
            Book.description.isnot(None)
        ).limit(100).all()

        similarities = []
        for book in all_books:
            text = f"{book.title} {book.description}"
            try:
                score = await ai_service.similarity_score(book_text, text)
                similarities.append((book, score))
            except Exception:
                continue

        similarities.sort(key=lambda x: x[1], reverse=True)
        return [book for book, _ in similarities[:limit]]

    def save_recommendation(
        self,
        user_id: int,
        book_id: int,
        rec_type: RecommendationType,
        score: float,
        reason: str = None,
        based_on_book_id: int = None
    ) -> Recommendation:
        """حفظ توصية"""
        rec = Recommendation(
            user_id=user_id,
            book_id=book_id,
            recommendation_type=rec_type,
            score=score,
            reason=reason,
            based_on_book_id=based_on_book_id,
            expires_at=datetime.utcnow() + timedelta(days=7)
        )
        self.db.add(rec)
        self.db.commit()
        self.db.refresh(rec)
        return rec

    def mark_recommendation_clicked(self, user_id: int, book_id: int) -> bool:
        """تحديد أن التوصية تم النقر عليها"""
        rec = self.db.query(Recommendation).filter(
            Recommendation.user_id == user_id,
            Recommendation.book_id == book_id,
            Recommendation.is_shown > 0
        ).first()

        if rec:
            rec.is_clicked += 1
            self.db.commit()
            return True
        return False

    # ==========================================
    # سجل القراءة
    # ==========================================

    def start_reading(self, user_id: int, book_id: int) -> ReadingHistory:
        """بدء قراءة كتاب"""
        existing = self.db.query(ReadingHistory).filter(
            ReadingHistory.user_id == user_id,
            ReadingHistory.book_id == book_id
        ).first()

        if existing:
            existing.last_read_at = datetime.utcnow()
            self.db.commit()
            return existing

        book = self.db.query(Book).filter(Book.id == book_id).first()
        history = ReadingHistory(
            user_id=user_id,
            book_id=book_id,
            total_pages=book.page_count if book else None,
            started_at=datetime.utcnow(),
            last_read_at=datetime.utcnow()
        )
        self.db.add(history)
        self.db.commit()
        self.db.refresh(history)
        return history

    def update_reading_progress(
        self,
        user_id: int,
        book_id: int,
        current_page: int
    ) -> Optional[ReadingHistory]:
        """تحديث تقدم القراءة"""
        history = self.db.query(ReadingHistory).filter(
            ReadingHistory.user_id == user_id,
            ReadingHistory.book_id == book_id
        ).first()

        if not history:
            history = self.start_reading(user_id, book_id)

        history.current_page = current_page
        history.last_read_at = datetime.utcnow()

        if history.total_pages:
            history.progress_percent = (current_page / history.total_pages) * 100

        if history.progress_percent >= 100:
            history.completed_at = datetime.utcnow()

        self.db.commit()
        self.db.refresh(history)
        return history

    def add_bookmark(
        self,
        user_id: int,
        book_id: int,
        page: int,
        note: str = None
    ) -> Optional[ReadingHistory]:
        """إضافة إشارة مرجعية"""
        history = self.db.query(ReadingHistory).filter(
            ReadingHistory.user_id == user_id,
            ReadingHistory.book_id == book_id
        ).first()

        if history:
            bookmarks = history.bookmarks or []
            bookmarks.append({"page": page, "note": note})
            history.bookmarks = bookmarks
            self.db.commit()
            self.db.refresh(history)

        return history

    # ==========================================
    # القطاعات
    # ==========================================

    def get_user_segments(self, user_id: int) -> List[UserSegment]:
        """الحصول على قطاعات المستخدم"""
        memberships = self.db.query(UserSegmentMembership).filter(
            UserSegmentMembership.user_id == user_id
        ).all()

        segments = []
        for m in memberships:
            segment = self.db.query(UserSegment).get(m.segment_id)
            if segment:
                segments.append(segment)

        return segments

    def assign_segment(self, user_id: int, segment_id: int, is_primary: bool = False) -> None:
        """تعيين مستخدم لقطاع"""
        existing = self.db.query(UserSegmentMembership).filter(
            UserSegmentMembership.user_id == user_id,
            UserSegmentMembership.segment_id == segment_id
        ).first()

        if existing:
            return

        membership = UserSegmentMembership(
            user_id=user_id,
            segment_id=segment_id,
            is_primary=is_primary
        )
        self.db.add(membership)

        # تحديث عدد أعضاء القطاع
        segment = self.db.query(UserSegment).get(segment_id)
        if segment:
            segment.user_count += 1

        self.db.commit()

    # ==========================================
    # الإحصائيات
    # ==========================================

    def get_user_behavior_stats(self, user_id: int) -> dict:
        """إحصائيات سلوك المستخدم"""
        from app.models.points import UserPoints

        # إحصائيات عامة
        total_behaviors = self.db.query(func.count(UserBehavior.id)).filter(
            UserBehavior.user_id == user_id
        ).scalar()

        downloads = self.db.query(func.count(UserBehavior.id)).filter(
            UserBehavior.user_id == user_id,
            UserBehavior.behavior_type == "download"
        ).scalar()

        favorites = self.db.query(func.count(UserBehavior.id)).filter(
            UserBehavior.user_id == user_id,
            UserBehavior.behavior_type == "favorite"
        ).scalar()

        # الكتب المقروءة
        reading = self.db.query(ReadingHistory).filter(
            ReadingHistory.user_id == user_id,
            ReadingHistory.completed_at.isnot(None)
        ).count()

        # النقاط
        points = self.db.query(UserPoints).filter(
            UserPoints.user_id == user_id
        ).first()

        return {
            "total_behaviors": total_behaviors,
            "total_downloads": downloads,
            "total_favorites": favorites,
            "completed_books": reading,
            "current_points": points.current_balance if points else 0
        }

    def get_recommendation_stats(self, user_id: int) -> dict:
        """إحصائيات التوصيات"""
        shown = self.db.query(func.count(Recommendation.id)).filter(
            Recommendation.user_id == user_id
        ).scalar()

        clicked = self.db.query(func.count(Recommendation.id)).filter(
            Recommendation.user_id == user_id,
            Recommendation.is_clicked > 0
        ).scalar()

        converted = self.db.query(func.count(Recommendation.id)).filter(
            Recommendation.user_id == user_id,
            Recommendation.is_converted > 0
        ).scalar()

        click_rate = (clicked / shown * 100) if shown > 0 else 0
        conversion_rate = (converted / shown * 100) if shown > 0 else 0

        return {
            "total_shown": shown,
            "clicked": clicked,
            "converted": converted,
            "click_rate": round(click_rate, 2),
            "conversion_rate": round(conversion_rate, 2)
        }
