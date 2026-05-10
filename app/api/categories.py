"""
Categories API - واجهة الأقسام
"""
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.book import Book, BookCategory, BookStatus
from app.schemas.book import CategoryCreate, CategoryResponse, CategoryUpdate, BookResponse
from app.services.category_service import CategoryService

router = APIRouter(prefix="/categories", tags=["الأقسام"])


def _category_to_response(category: BookCategory, db: Session) -> CategoryResponse:
    service = CategoryService(db)
    return CategoryResponse(
        id=category.id,
        name=category.name,
        name_ar=category.name_ar,
        name_en=category.name_en,
        description=category.description,
        is_active=category.is_active,
        parent_id=category.parent_id,
        icon=category.icon,
        sort_order=category.sort_order,
        books_count=service.count_books(category.id),
    )


@router.get("/", response_model=list[CategoryResponse])
def list_categories(
    active_only: bool = True,
    db: Session = Depends(get_db)
):
    """عرض جميع الأقسام"""
    service = CategoryService(db)
    categories = service.list_all(active_only=active_only)
    return [_category_to_response(category, db) for category in categories]


@router.get("/main", response_model=list[CategoryResponse])
def get_main_categories(db: Session = Depends(get_db)):
    """الأقسام الرئيسية فقط"""
    service = CategoryService(db)
    categories = service.get_main_categories()
    return [_category_to_response(category, db) for category in categories]


@router.get("/{category_id}", response_model=CategoryResponse)
def get_category(category_id: int, db: Session = Depends(get_db)):
    """الحصول على قسم محدد"""
    service = CategoryService(db)
    category = service.get_by_id(category_id)
    if not category:
        raise HTTPException(status_code=404, detail="القسم غير موجود")
    return _category_to_response(category, db)


@router.get("/{category_id}/subcategories", response_model=list[CategoryResponse])
def get_subcategories(category_id: int, db: Session = Depends(get_db)):
    """الأقسام الفرعية"""
    service = CategoryService(db)
    category = service.get_by_id(category_id)
    if not category:
        raise HTTPException(status_code=404, detail="القسم غير موجود")
    subcategories = service.get_subcategories(category_id)
    return [_category_to_response(subcategory, db) for subcategory in subcategories]


@router.get("/{category_id}/books", response_model=list[BookResponse])
def get_category_books(
    category_id: int,
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db)
):
    """كتب قسم معين"""
    service = CategoryService(db)
    category = service.get_by_id(category_id)
    if not category:
        raise HTTPException(status_code=404, detail="القسم غير موجود")

    books = db.query(Book).filter(
        Book.category_id == category_id,
        Book.status == BookStatus.ACTIVE
    ).order_by(Book.created_at.desc()).limit(limit).offset(offset).all()
    return books


@router.get("/tree")
def get_categories_tree(db: Session = Depends(get_db)):
    """شجرة الأقسام"""
    service = CategoryService(db)
    roots = service.get_main_categories()
    tree = []
    for category in roots:
        tree.append({
            "category": _category_to_response(category, db),
            "subcategories": [_category_to_response(sub, db) for sub in service.get_subcategories(category.id)]
        })
    return {"tree": tree, "count": len(tree)}


@router.post("/", response_model=CategoryResponse)
def create_category(payload: CategoryCreate, db: Session = Depends(get_db)):
    """إنشاء قسم جديد"""
    service = CategoryService(db)
    category = service.create(**payload.model_dump())
    return _category_to_response(category, db)


@router.put("/{category_id}", response_model=CategoryResponse)
def update_category(category_id: int, payload: CategoryUpdate, db: Session = Depends(get_db)):
    """تحديث قسم"""
    service = CategoryService(db)
    category = service.update(category_id, **payload.model_dump(exclude_unset=True))
    if not category:
        raise HTTPException(status_code=404, detail="القسم غير موجود")
    return _category_to_response(category, db)


@router.delete("/{category_id}")
def delete_category(category_id: int, db: Session = Depends(get_db)):
    """حذف قسم"""
    service = CategoryService(db)
    success = service.delete(category_id)
    if not success:
        raise HTTPException(status_code=404, detail="القسم غير موجود")
    return {"message": "تم حذف القسم بنجاح"}


@router.patch("/{category_id}/toggle")
def toggle_category(category_id: int, db: Session = Depends(get_db)):
    """تفعيل/إلغاء تفعيل قسم"""
    service = CategoryService(db)
    category = service.toggle_active(category_id)
    if not category:
        raise HTTPException(status_code=404, detail="القسم غير موجود")
    return {"message": "تم تحديث حالة القسم", "category": _category_to_response(category, db)}
