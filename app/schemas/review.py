"""
Review Schemas - مخططات التقييمات
"""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, field_validator


class ReviewCreate(BaseModel):
    """مخطط إنشاء تقييم"""
    book_id: int
    rating: float = Field(..., ge=1, le=5)
    comment: Optional[str] = Field(None, max_length=1000)

    @field_validator('rating')
    @classmethod
    def validate_rating(cls, v):
        if v < 1 or v > 5:
            raise ValueError('التقييم يجب أن يكون بين 1 و 5')
        return v


class ReviewUpdate(BaseModel):
    """مخطط تحديث تقييم"""
    rating: Optional[float] = Field(None, ge=1, le=5)
    comment: Optional[str] = None


class ReviewResponse(BaseModel):
    """مخطط استجابة التقييم"""
    id: int
    user_id: int
    book_id: int
    rating: float
    comment: Optional[str] = None
    is_approved: int
    created_at: datetime
    user_first_name: Optional[str] = None
    user_username: Optional[str] = None

    class Config:
        from_attributes = True


class BookRatingResponse(BaseModel):
    """مخطط تقييمات الكتاب"""
    book_id: int
    average_rating: float
    total_ratings: int
    reviews: list[ReviewResponse]
    total_pages: int
    current_page: int
