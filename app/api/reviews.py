"""
Reviews API - واجهة برمجة التقييمات
"""
from typing import List
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from app.database import get_db
from app.services.book_service import BookService
from app.schemas.review import ReviewCreate, ReviewResponse

router = APIRouter(prefix="/reviews", tags=["التقييمات"])


@router.get("/book/{book_id}", response_model=List[ReviewResponse])
def get_book_reviews(
    book_id: int,
    limit: int = Query(default=20, ge=1, le=50),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db)
):
    """الحصول على تقييمات كتاب"""
    from app.models.review import Review

    reviews = db.query(Review).filter(
        Review.book_id == book_id,
        Review.is_approved == 1
    ).order_by(Review.created_at.desc()).limit(limit).offset(offset).all()

    return reviews


@router.post("/", response_model=ReviewResponse)
def create_review(
    review_data: ReviewCreate,
    telegram_id: int,
    db: Session = Depends(get_db)
):
    """إنشاء تقييم جديد"""
    from app.services.user_service import UserService
    from app.services.points_service import PointsService
    from app.models.review import Review

    # التحقق من المستخدم
    user_service = UserService(db)
    user = user_service.get_user_by_telegram_id(telegram_id)

    if not user:
        raise HTTPException(status_code=404, detail="المستخدم غير موجود")

    # التحقق من الكتاب
    book_service = BookService(db)
    book = book_service.get_book(review_data.book_id)

    if not book:
        raise HTTPException(status_code=404, detail="الكتاب غير موجود")

    # التحقق من عدم وجود تقييم سابق
    existing = db.query(Review).filter(
        Review.user_id == user.id,
        Review.book_id == review_data.book_id
    ).first()

    if existing:
        raise HTTPException(status_code=400, detail="لقد قيّمت هذا الكتاب من قبل")

    # إنشاء التقييم
    review = Review(
        user_id=user.id,
        book_id=review_data.book_id,
        rating=review_data.rating,
        comment=review_data.comment
    )
    db.add(review)

    # تحديث متوسط تقييم الكتاب
    book_service.add_rating(review_data.book_id, review_data.rating)

    # إضافة نقاط
    points_service = PointsService(db)
    points_service.add_review_points(user.id, review.id)

    db.commit()
    db.refresh(review)

    return review


@router.delete("/{review_id}")
def delete_review(
    review_id: int,
    db: Session = Depends(get_db)
):
    """حذف تقييم"""
    from app.models.review import Review

    review = db.query(Review).filter(Review.id == review_id).first()

    if not review:
        raise HTTPException(status_code=404, detail="التقييم غير موجود")

    db.delete(review)
    db.commit()

    return {"message": "تم حذف التقييم بنجاح"}
