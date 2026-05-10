"""
Analytics API - واجهة التحليلات
"""
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, desc

from app.database import get_db
from app.models.book import Book, BookCategory, BookStatus
from app.models.user import User, UserStatus
from app.models.author import Author
from app.models.review import Review
from app.models.favorite import Favorite
from app.models.download_history import DownloadHistory
from app.models.points import UserPoints, PointsTransaction
from app.models.referral_system import Referral
from app.models.notification import Notification, SmartNotification, NotificationAnalytics
from app.models.challenges import Challenge, ChallengeParticipation
from app.services.market_service import MarketService

router = APIRouter(prefix="/analytics", tags=["التحليلات"])


@router.get("/overview")
def overview(db: Session = Depends(get_db)):
    """ملخص شامل للمنصة"""
    return {
        "books": {
            "total": db.query(func.count(Book.id)).scalar() or 0,
            "active": db.query(func.count(Book.id)).filter(Book.status == BookStatus.ACTIVE).scalar() or 0,
            "pending": db.query(func.count(Book.id)).filter(Book.status == BookStatus.PENDING).scalar() or 0,
            "rejected": db.query(func.count(Book.id)).filter(Book.status == BookStatus.REJECTED).scalar() or 0,
            "downloads": db.query(func.sum(Book.download_count)).scalar() or 0,
            "views": db.query(func.sum(Book.view_count)).scalar() or 0,
        },
        "users": {
            "total": db.query(func.count(User.id)).scalar() or 0,
            "active": db.query(func.count(User.id)).filter(User.status == UserStatus.ACTIVE).scalar() or 0,
            "banned": db.query(func.count(User.id)).filter(User.status == UserStatus.BANNED).scalar() or 0,
            "premium": db.query(func.count(User.id)).filter(User.is_premium == True).scalar() or 0,
        },
        "content": {
            "authors": db.query(func.count(Author.id)).scalar() or 0,
            "categories": db.query(func.count(BookCategory.id)).scalar() or 0,
            "reviews": db.query(func.count(Review.id)).scalar() or 0,
            "favorites": db.query(func.count(Favorite.id)).scalar() or 0,
            "downloads": db.query(func.count(DownloadHistory.id)).scalar() or 0,
        },
        "points": {
            "wallets": db.query(func.count(UserPoints.id)).scalar() or 0,
            "transactions": db.query(func.count(PointsTransaction.id)).scalar() or 0,
            "balance_total": db.query(func.sum(UserPoints.current_balance)).scalar() or 0,
        },
        "referrals": {
            "total": db.query(func.count(Referral.id)).scalar() or 0,
            "active": db.query(func.count(Referral.id)).filter(Referral.is_completed == True).scalar() or 0,
        },
        "notifications": {
            "simple": db.query(func.count(Notification.id)).scalar() or 0,
            "smart": db.query(func.count(SmartNotification.id)).scalar() or 0,
            "analytics": db.query(func.count(NotificationAnalytics.id)).scalar() or 0,
        },
        "challenges": {
            "total": db.query(func.count(Challenge.id)).scalar() or 0,
            "participations": db.query(func.count(ChallengeParticipation.id)).scalar() or 0,
        },
    }


@router.get("/growth/users")
def user_growth(days: int = Query(default=30, ge=1, le=365), db: Session = Depends(get_db)):
    """نمو المستخدمين خلال فترة"""
    since = datetime.utcnow() - timedelta(days=days)
    rows = (
        db.query(func.date(User.created_at), func.count(User.id))
        .filter(User.created_at >= since)
        .group_by(func.date(User.created_at))
        .order_by(func.date(User.created_at))
        .all()
    )
    return {"days": days, "data": [{"date": str(day), "count": count} for day, count in rows]}


@router.get("/growth/downloads")
def download_growth(days: int = Query(default=30, ge=1, le=365), db: Session = Depends(get_db)):
    """نمو التحميلات خلال فترة"""
    since = datetime.utcnow() - timedelta(days=days)
    rows = (
        db.query(func.date(DownloadHistory.downloaded_at), func.count(DownloadHistory.id))
        .filter(DownloadHistory.downloaded_at >= since)
        .group_by(func.date(DownloadHistory.downloaded_at))
        .order_by(func.date(DownloadHistory.downloaded_at))
        .all()
    )
    return {"days": days, "data": [{"date": str(day), "count": count} for day, count in rows]}


@router.get("/top/books")
def top_books(limit: int = Query(default=10, ge=1, le=50), db: Session = Depends(get_db)):
    """أكثر الكتب نشاطاً"""
    books = db.query(Book).filter(Book.status == BookStatus.ACTIVE).order_by(
        desc(Book.download_count), desc(Book.average_rating)
    ).limit(limit).all()
    return {"books": books, "count": len(books)}


@router.get("/top/categories")
def top_categories(limit: int = Query(default=10, ge=1, le=50), db: Session = Depends(get_db)):
    """أكثر الأقسام استخداماً"""
    rows = (
        db.query(BookCategory, func.count(Book.id).label("books_count"))
        .outerjoin(Book, Book.category_id == BookCategory.id)
        .group_by(BookCategory.id)
        .order_by(func.count(Book.id).desc())
        .limit(limit)
        .all()
    )
    return {
        "categories": [
            {
                "id": category.id,
                "name": category.name,
                "name_ar": category.name_ar,
                "books_count": books_count,
            }
            for category, books_count in rows
        ],
        "count": len(rows),
    }


@router.get("/engagement")
def engagement(db: Session = Depends(get_db)):
    """مؤشرات التفاعل"""
    last_7 = datetime.utcnow() - timedelta(days=7)
    return {
        "reviews_7d": db.query(func.count(Review.id)).filter(Review.created_at >= last_7).scalar() or 0,
        "favorites_total": db.query(func.count(Favorite.id)).scalar() or 0,
        "downloads_7d": db.query(func.count(DownloadHistory.id)).filter(DownloadHistory.downloaded_at >= last_7).scalar() or 0,
        "new_users_7d": db.query(func.count(User.id)).filter(User.created_at >= last_7).scalar() or 0,
    }


@router.get("/market/earnings")
def market_earnings(
    start_date: datetime = None,
    end_date: datetime = None,
    db: Session = Depends(get_db)
):
    """أرباح السوق الداخلي"""
    service = MarketService(db)
    return service.get_platform_earnings(start_date=start_date, end_date=end_date)


@router.get("/notifications")
def notification_stats(db: Session = Depends(get_db)):
    """تحليلات الإشعارات"""
    total = db.query(func.count(Notification.id)).scalar() or 0
    read = db.query(func.count(Notification.id)).filter(Notification.is_read == True).scalar() or 0
    failed = db.query(func.count(Notification.id)).filter(Notification.failed_at.isnot(None)).scalar() or 0
    return {
        "total": total,
        "read": read,
        "unread": total - read,
        "failed": failed,
        "smart_total": db.query(func.count(SmartNotification.id)).scalar() or 0,
        "analytics_total": db.query(func.count(NotificationAnalytics.id)).scalar() or 0,
    }
