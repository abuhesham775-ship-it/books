"""
Search API - واجهة برمجة البحث
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from app.database import get_db
from app.services.search_service import SearchService

router = APIRouter(prefix="/search", tags=["البحث"])


@router.get("/")
async def search(
    q: str = Query(..., min_length=1),
    type: str = Query(default="text", regex="^(text|semantic)$"),
    limit: int = Query(default=20, ge=1, le=50),
    db: Session = Depends(get_db)
):
    """البحث في الكتب والمؤلفين"""
    service = SearchService(db)

    if type == "semantic":
        results = await service.semantic_search(q, limit=limit)
        books = [book for book, score in results]
    else:
        books, authors = service.text_search(q, limit=limit)

    return {
        "query": q,
        "type": type,
        "books": books if type == "text" else [book for book, _ in books],
        "count": len(books) if type == "text" else len([book for book, _ in books])
    }


@router.get("/author/{author_name}")
def search_by_author(
    author_name: str,
    limit: int = Query(default=20, ge=1, le=50),
    db: Session = Depends(get_db)
):
    """البحث عن كتب مؤلف"""
    service = SearchService(db)
    books = service.search_by_author(author_name, limit=limit)

    return {
        "author": author_name,
        "books": books,
        "count": len(books)
    }


@router.get("/category/{category_name}")
def search_by_category(
    category_name: str,
    limit: int = Query(default=20, ge=1, le=50),
    db: Session = Depends(get_db)
):
    """البحث عن كتب قسم"""
    service = SearchService(db)
    books = service.search_by_category(category_name, limit=limit)

    return {
        "category": category_name,
        "books": books,
        "count": len(books)
    }


@router.get("/year/{year}")
def search_by_year(
    year: int,
    limit: int = Query(default=20, ge=1, le=50),
    db: Session = Depends(get_db)
):
    """البحث عن كتب سنة معينة"""
    service = SearchService(db)
    books = service.search_by_year(year, limit=limit)

    return {
        "year": year,
        "books": books,
        "count": len(books)
    }


@router.get("/advanced")
def advanced_search(
    q: Optional[str] = None,
    author: Optional[str] = None,
    category: Optional[str] = None,
    year_from: Optional[int] = None,
    year_to: Optional[int] = None,
    min_rating: Optional[float] = None,
    language: Optional[str] = None,
    limit: int = Query(default=20, ge=1, le=50),
    db: Session = Depends(get_db)
):
    """بحث متقدم"""
    service = SearchService(db)
    books = service.advanced_search(
        query=q,
        author=author,
        category=category,
        year_from=year_from,
        year_to=year_to,
        min_rating=min_rating,
        language=language,
        limit=limit
    )

    return {
        "filters": {
            "query": q,
            "author": author,
            "category": category,
            "year_from": year_from,
            "year_to": year_to,
            "min_rating": min_rating,
            "language": language
        },
        "books": books,
        "count": len(books)
    }


@router.get("/{book_id}/recommendations")
def get_recommendations(
    book_id: int,
    limit: int = Query(default=5, ge=1, le=20),
    db: Session = Depends(get_db)
):
    """الحصول على توصيات كتب مشابهة"""
    service = SearchService(db)
    books = service.get_recommendations(book_id, limit=limit)

    return {
        "book_id": book_id,
        "recommendations": books,
        "count": len(books)
    }
