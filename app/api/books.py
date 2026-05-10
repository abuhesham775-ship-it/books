"""
Books API - واجهة برمجة الكتب
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from app.database import get_db
from app.services.book_service import BookService
from app.services.author_service import AuthorService
from app.services.category_service import CategoryService
from app.schemas.book import BookCreate, BookResponse, BookUpdate

router = APIRouter(prefix="/books", tags=["الكتب"])


@router.get("/", response_model=List[BookResponse])
def get_books(
    category_id: Optional[int] = None,
    status: str = "active",
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db)
):
    """الحصول على قائمة الكتب"""
    service = BookService(db)

    if category_id:
        books = service.get_books_by_category(category_id, limit=limit, offset=offset)
    else:
        from app.models.book import BookStatus
        status_enum = BookStatus.ACTIVE if status == "active" else None
        books = service.get_all_books(status=status_enum)

    return books


@router.get("/trending", response_model=List[BookResponse])
def get_trending_books(
    limit: int = Query(default=10, ge=1, le=50),
    db: Session = Depends(get_db)
):
    """الحصول على الكتب الرائجة"""
    service = BookService(db)
    return service.get_trending_books(limit=limit)


@router.get("/featured", response_model=List[BookResponse])
def get_featured_books(
    limit: int = Query(default=10, ge=1, le=50),
    db: Session = Depends(get_db)
):
    """الحصول على الكتب المميزة"""
    service = BookService(db)
    return service.get_featured_books(limit=limit)


@router.get("/recent", response_model=List[BookResponse])
def get_recent_books(
    limit: int = Query(default=10, ge=1, le=50),
    db: Session = Depends(get_db)
):
    """الحصول على أحدث الكتب"""
    service = BookService(db)
    return service.get_recent_books(limit=limit)


@router.get("/search")
def search_books(
    q: str = Query(..., min_length=1),
    limit: int = Query(default=20, ge=1, le=50),
    db: Session = Depends(get_db)
):
    """البحث عن الكتب"""
    service = BookService(db)
    books = service.search_books(q, limit=limit)
    return {"books": books, "count": len(books)}


@router.get("/{book_id}", response_model=BookResponse)
def get_book(
    book_id: int,
    db: Session = Depends(get_db)
):
    """الحصول على كتاب محدد"""
    service = BookService(db)
    book = service.get_book(book_id)

    if not book:
        raise HTTPException(status_code=404, detail="الكتاب غير موجود")

    return book


@router.post("/", response_model=BookResponse)
def create_book(
    book_data: BookCreate,
    db: Session = Depends(get_db)
):
    """إنشاء كتاب جديد"""
    service = BookService(db)
    book = service.create_book(**book_data.model_dump())
    return book


@router.put("/{book_id}", response_model=BookResponse)
def update_book(
    book_id: int,
    book_data: BookUpdate,
    db: Session = Depends(get_db)
):
    """تحديث كتاب"""
    service = BookService(db)
    book = service.update_book(book_id, **book_data.model_dump(exclude_unset=True))

    if not book:
        raise HTTPException(status_code=404, detail="الكتاب غير موجود")

    return book


@router.delete("/{book_id}")
def delete_book(
    book_id: int,
    db: Session = Depends(get_db)
):
    """حذف كتاب"""
    service = BookService(db)
    success = service.delete_book(book_id)

    if not success:
        raise HTTPException(status_code=404, detail="الكتاب غير موجود")

    return {"message": "تم حذف الكتاب بنجاح"}


@router.post("/{book_id}/approve")
def approve_book(
    book_id: int,
    db: Session = Depends(get_db)
):
    """الموافقة على كتاب"""
    service = BookService(db)
    book = service.approve_book(book_id)

    if not book:
        raise HTTPException(status_code=404, detail="الكتاب غير موجود")

    return {"message": "تم الموافقة على الكتاب", "book": book}


@router.post("/{book_id}/reject")
def reject_book(
    book_id: int,
    reason: str = None,
    db: Session = Depends(get_db)
):
    """رفض كتاب"""
    service = BookService(db)
    book = service.reject_book(book_id, reason)

    if not book:
        raise HTTPException(status_code=404, detail="الكتاب غير موجود")

    return {"message": "تم رفض الكتاب", "book": book}
