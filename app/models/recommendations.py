"""
Recommendations Models - نماذج التوصيات
نظام تحليل سلوك المستخدم والتوصيات الذكية
"""
import enum
from datetime import datetime
from sqlalchemy import Column, Integer, String, Enum, DateTime, Float, ForeignKey, JSON, Text, Boolean
from sqlalchemy.orm import relationship
from app.database import Base


class RecommendationType(enum.Enum):
    """نوع التوصية"""
    SIMILAR_BOOKS = "similar_books"
    SAME_AUTHOR = "same_author"
    SAME_CATEGORY = "same_category"
    TRENDING = "trending"
    PERSONALIZED = "personalized"
    MOOD_BASED = "mood_based"
    RARE_FINDS = "rare_finds"


class UserBehavior(Base):
    """سجل سلوك المستخدم"""
    __tablename__ = "user_behaviors"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    # نوع السلوك
    behavior_type = Column(String(50), nullable=False)  # view, download, favorite, rating, search, share
    book_id = Column(Integer, ForeignKey("books.id"), nullable=True)
    category_id = Column(Integer, ForeignKey("book_categories.id"), nullable=True)
    author_id = Column(Integer, ForeignKey("authors.id"), nullable=True)

    # سياق السلوك
    search_query = Column(String(500), nullable=True)
    rating_given = Column(Float, nullable=True)
    time_spent_seconds = Column(Integer, nullable=True)

    # بيانات إضافية
    extra_data = Column(JSON, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    user = relationship("User", backref="behaviors")
    book = relationship("Book", backref="behaviors")
    category = relationship("BookCategory", backref="user_behaviors")
    author = relationship("Author", backref="user_behaviors")

    def __repr__(self):
        return f"<UserBehavior {self.id} user={self.user_id} type={self.behavior_type}>"


class UserPreference(Base):
    """تفضيلات المستخدم"""
    __tablename__ = "user_preferences"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, unique=True)

    # التفضيلات learned
    preferred_categories = Column(JSON, nullable=True)  # [1, 2, 3]
    preferred_authors = Column(JSON, nullable=True)    # [1, 2, 3]
    preferred_language = Column(String(10), nullable=True)

    # أنماط القراءة
    avg_session_length = Column(Integer, default=0)  # بالدقائق
    preferred_reading_time = Column(String(20), nullable=True)  # morning, evening, etc.

    # نشاط المستخدم
    engagement_score = Column(Float, default=0.0)  # 0-100
    freshness_score = Column(Float, default=0.0)    # مدى حداثة الاهتمامات

    # تحليل المشاعر
    preferred_moods = Column(JSON, nullable=True)  # ["adventure", "romance"]
    avoided_content = Column(JSON, nullable=True)  # ["horror", "violence"]

    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_recalculated = Column(DateTime, nullable=True)

    # Relationships
    user = relationship("User", backref="preferences")

    def __repr__(self):
        return f"<UserPreference user={self.user_id}>"


class Recommendation(Base):
    """توصية واحدة"""
    __tablename__ = "recommendations"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    book_id = Column(Integer, ForeignKey("books.id"), nullable=False)

    recommendation_type = Column(Enum(RecommendationType), nullable=False)
    score = Column(Float, default=0.0)  # confidence score 0-1

    # سبب التوصية
    reason = Column(Text, nullable=True)
    based_on_book_id = Column(Integer, ForeignKey("books.id"), nullable=True)
    based_on_category_id = Column(Integer, ForeignKey("book_categories.id"), nullable=True)

    # السياق
    context = Column(String(50), nullable=True)  # home, search, category, etc.
    user_mood = Column(String(50), nullable=True)

    # حالة العرض
    is_shown = Column(Integer, default=0)  # عدد مرات العرض
    is_clicked = Column(Integer, default=0)
    is_converted = Column(Integer, default=0)  # هل تم التحميل

    created_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=True)

    # Relationships
    user = relationship("User", backref="recommendations")
    book = relationship("Book", foreign_keys=[book_id])
    based_on_book = relationship("Book", foreign_keys=[based_on_book_id])
    based_on_category = relationship("BookCategory", foreign_keys=[based_on_category_id])

    def __repr__(self):
        return f"<Recommendation user={self.user_id} book={self.book_id}>"


class ReadingHistory(Base):
    """سجل القراءة"""
    __tablename__ = "reading_history"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    book_id = Column(Integer, ForeignKey("books.id"), nullable=False)

    # التقدم
    current_page = Column(Integer, default=0)
    total_pages = Column(Integer, nullable=True)
    progress_percent = Column(Float, default=0.0)

    # التوقيت
    started_at = Column(DateTime, nullable=True)
    last_read_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)

    # ملاحظات المستخدم
    notes = Column(Text, nullable=True)
    bookmarks = Column(JSON, nullable=True)  # [{"page": 10, "note": "important"}]

    # التقييم الشخصي
    personal_rating = Column(Float, nullable=True)
    personal_review = Column(Text, nullable=True)

    is_favorite_quote = Column(Boolean, default=False)
    favorite_quote = Column(Text, nullable=True)

    # Relationships
    user = relationship("User", backref="reading_history")
    book = relationship("Book", backref="reading_history")

    def __repr__(self):
        return f"<ReadingHistory user={self.user_id} book={self.book_id}>"


class UserSegment(Base):
    """قطاع المستخدم"""
    __tablename__ = "user_segments"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False, unique=True)
    name_ar = Column(String(100), nullable=True)
    description = Column(Text, nullable=True)

    # معايير القطاع
    criteria = Column(JSON, nullable=True)  # قواعد التصنيف

    # إحصائيات القطاع
    user_count = Column(Integer, default=0)
    avg_engagement = Column(Float, default=0.0)
    avg_spending = Column(Float, default=0.0)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<UserSegment {self.name}>"


class UserSegmentMembership(Base):
    """عضوية المستخدم في القطاعات"""
    __tablename__ = "user_segment_memberships"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    segment_id = Column(Integer, ForeignKey("user_segments.id"), nullable=False)

    affinity_score = Column(Float, default=0.0)  # درجة الانتماء
    is_primary = Column(Boolean, default=False)  # القطاع الأساسي

    assigned_at = Column(DateTime, default=datetime.utcnow)
    last_updated = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    user = relationship("User", backref="segment_memberships")
    segment = relationship("UserSegment", backref="members")

    def __repr__(self):
        return f"<UserSegmentMembership user={self.user_id} segment={self.segment_id}>"
