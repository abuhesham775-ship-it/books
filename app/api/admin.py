"""
Admin API - واجهة الإدارة
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.admin.admin_service import AdminService
from app.models.admin import AdminRole
from app.models.book import BookStatus
from app.models.user import UserStatus

router = APIRouter(prefix="/admin", tags=["الإدارة"])


@router.get("/stats")
def get_admin_stats(db: Session = Depends(get_db)):
    """إحصائيات عامة للوحة الإدارة"""
    service = AdminService(db)
    return service.get_statistics()


@router.get("/books/pending")
def get_pending_books(limit: int = Query(default=50, ge=1, le=100), db: Session = Depends(get_db)):
    """الكتب بانتظار المراجعة"""
    service = AdminService(db)
    books = service.get_pending_books(limit=limit)
    return {"books": books, "count": len(books)}


@router.get("/books")
def get_books(
    status: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """عرض جميع الكتب أو حسب الحالة"""
    service = AdminService(db)

    status_enum = None
    if status:
        try:
            status_enum = BookStatus[status.upper()]
        except KeyError:
            raise HTTPException(status_code=400, detail="حالة الكتاب غير صحيحة")

    books = service.get_all_books(status=status_enum)
    return {"books": books, "count": len(books)}


@router.post("/books/{book_id}/approve")
def approve_book(book_id: int, db: Session = Depends(get_db)):
    """الموافقة على كتاب"""
    service = AdminService(db)
    book = service.approve_book(book_id)
    if not book:
        raise HTTPException(status_code=404, detail="الكتاب غير موجود")
    return {"message": "تمت الموافقة على الكتاب", "book": book}


@router.post("/books/{book_id}/reject")
def reject_book(book_id: int, reason: Optional[str] = None, db: Session = Depends(get_db)):
    """رفض كتاب"""
    service = AdminService(db)
    book = service.reject_book(book_id, reason)
    if not book:
        raise HTTPException(status_code=404, detail="الكتاب غير موجود")
    return {"message": "تم رفض الكتاب", "book": book}


@router.delete("/books/{book_id}")
def delete_book(book_id: int, db: Session = Depends(get_db)):
    """حذف كتاب"""
    service = AdminService(db)
    success = service.delete_book(book_id)
    if not success:
        raise HTTPException(status_code=404, detail="الكتاب غير موجود")
    return {"message": "تم حذف الكتاب بنجاح"}


@router.get("/users")
def get_users(
    status: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """عرض المستخدمين"""
    service = AdminService(db)

    status_enum = None
    if status:
        try:
            status_enum = UserStatus[status.upper()]
        except KeyError:
            raise HTTPException(status_code=400, detail="حالة المستخدم غير صحيحة")

    users = service.get_all_users(status=status_enum)
    return {"users": users, "count": len(users)}


@router.post("/users/{telegram_id}/ban")
def ban_user(telegram_id: int, db: Session = Depends(get_db)):
    """حظر مستخدم"""
    service = AdminService(db)
    user = service.ban_user(telegram_id)
    if not user:
        raise HTTPException(status_code=404, detail="المستخدم غير موجود")
    return {"message": "تم حظر المستخدم", "user": user}


@router.post("/users/{telegram_id}/unban")
def unban_user(telegram_id: int, db: Session = Depends(get_db)):
    """فك حظر مستخدم"""
    service = AdminService(db)
    user = service.unban_user(telegram_id)
    if not user:
        raise HTTPException(status_code=404, detail="المستخدم غير موجود")
    return {"message": "تم إلغاء حظر المستخدم", "user": user}


@router.get("/logs")
def get_logs(admin_id: Optional[int] = None, limit: int = Query(default=100, ge=1, le=500), db: Session = Depends(get_db)):
    """سجلات الإدارة"""
    service = AdminService(db)
    logs = service.get_logs(admin_id=admin_id, limit=limit)
    return {"logs": logs, "count": len(logs)}


@router.get("/top-books")
def get_top_books(limit: int = Query(default=10, ge=1, le=50), db: Session = Depends(get_db)):
    """أكثر الكتب تحميلاً"""
    service = AdminService(db)
    books = service.get_top_books(limit=limit)
    return {"books": books, "count": len(books)}


@router.get("/top-users")
def get_top_users(limit: int = Query(default=10, ge=1, le=50), db: Session = Depends(get_db)):
    """أكثر المستخدمين نقاطاً"""
    service = AdminService(db)
    users = service.get_top_users(limit=limit)
    return {"users": users, "count": len(users)}


@router.get("/admins")
def get_admins(db: Session = Depends(get_db)):
    """جميع المشرفين النشطين"""
    service = AdminService(db)
    return {"admins": service.get_all_admins(), "count": len(service.get_all_admins())}


@router.post("/admins")
def add_admin(user_id: int, role: AdminRole = AdminRole.MODERATOR, db: Session = Depends(get_db)):
    """إضافة مشرف جديد"""
    service = AdminService(db)
    admin = service.add_admin(user_id=user_id, role=role)
    return {"message": "تمت إضافة المشرف", "admin": admin}


@router.delete("/admins/{user_id}")
def remove_admin(user_id: int, db: Session = Depends(get_db)):
    """إزالة صلاحية المشرف"""
    service = AdminService(db)
    success = service.remove_admin(user_id)
    if not success:
        raise HTTPException(status_code=404, detail="المشرف غير موجود")
    return {"message": "تمت إزالة المشرف بنجاح"}


@router.get("/export/books")
def export_books_csv(db: Session = Depends(get_db)):
    """تصدير بيانات الكتب كقائمة CSV جاهزة"""
    service = AdminService(db)
    return {"rows": service.export_books_csv()}


@router.get("/export/users")
def export_users_csv(db: Session = Depends(get_db)):
    """تصدير بيانات المستخدمين كقائمة CSV جاهزة"""
    service = AdminService(db)
    return {"rows": service.export_users_csv()}
