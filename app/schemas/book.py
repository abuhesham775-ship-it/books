"""
Book Schemas - مخططات الكتب
"""
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field


class BookCreate(BaseModel):
    """مخطط إنشاء كتاب"""
    title: str = Field(..., min_length=1, max_length=500)
    author_id: Optional[int] = None
    description: Optional[str] = None
    category_id: Optional[int] = None
    file_path: Optional[str] = None
    cover_image: Optional[str] = None
    language: str = "ar"
    isbn: Optional[str] = None
    publication_year: Optional[int] = None
    page_count: Optional[int] = None


class BookUpdate(BaseModel):
    """مخطط تحديث كتاب"""
    title: Optional[str] = None
    author_id: Optional[int] = None
    description: Optional[str] = None
    category_id: Optional[int] = None
    file_path: Optional[str] = None
    cover_image: Optional[str] = None
    language: Optional[str] = None
    isbn: Optional[str] = None
    publication_year: Optional[int] = None
    page_count: Optional[int] = None
    status: Optional[str] = None


class AuthorInfo(BaseModel):
    """معلومات المؤلف"""
    id: int
    name: str
    bio: Optional[str] = None

    class Config:
        from_attributes = True


class CategoryInfo(BaseModel):
    """معلومات القسم"""
    id: int
    name: str
    name_ar: Optional[str] = None
    icon: Optional[str] = None

    class Config:
        from_attributes = True


class BookResponse(BaseModel):
    """مخطط استجابة الكتاب"""
    id: int
    title: str
    author_id: Optional[int] = None
    author: Optional[AuthorInfo] = None
    description: Optional[str] = None
    category_id: Optional[int] = None
    category: Optional[CategoryInfo] = None
    file_path: Optional[str] = None
    cover_image: Optional[str] = None
    status: str
    download_count: int
    view_count: int
    average_rating: float
    total_ratings: int
    language: str
    isbn: Optional[str] = None
    publication_year: Optional[int] = None
    page_count: Optional[int] = None
    created_at: datetime

    class Config:
        from_attributes = True


class BookListResponse(BaseModel):
    """مخطط قائمة الكتب"""
    books: List[BookResponse]
    total: int
    page: int
    per_page: int
    total_pages: int


class CategoryCreate(BaseModel):
    """مخطط إنشاء قسم"""
    name: str = Field(..., min_length=1, max_length=255)
    name_ar: Optional[str] = None
    name_en: Optional[str] = None
    description: Optional[str] = None
    parent_id: Optional[int] = None
    icon: Optional[str] = None
    sort_order: int = 0


class CategoryUpdate(BaseModel):
    """مخطط تحديث قسم"""
    name: Optional[str] = None
    name_ar: Optional[str] = None
    name_en: Optional[str] = None
    description: Optional[str] = None
    is_active: Optional[bool] = None
    parent_id: Optional[int] = None
    icon: Optional[str] = None
    sort_order: Optional[int] = None


class CategoryResponse(BaseModel):
    """مخطط استجابة القسم"""
    id: int
    name: str
    name_ar: Optional[str] = None
    name_en: Optional[str] = None
    description: Optional[str] = None
    is_active: bool
    parent_id: Optional[int] = None
    icon: Optional[str] = None
    sort_order: int
    books_count: int = 0

    class Config:
        from_attributes = True
