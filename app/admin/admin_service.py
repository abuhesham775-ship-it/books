"""
Admin Service - خدمة لوحة تحكم الإدارة
"""
from typing import List, Optional, Dict
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.models.admin import AdminUser, AdminLog, AdminRole
from app.models.user import User, UserStatus
from app.models.book import Book, BookStatus, BookCategory
from app.models.points import UserPoints
from app.models.author import Author


class AdminService:
    """خدمة لوحة تحكم الإدارة"""

    def __init__(self, db: Session):
        self.db = db

    # ==========================================
    # إدارة الكتب
    # ==========================================

    def get_pending_books(self, limit: int = 50) -> List[Book]:
        """الحصول على الكتب قيد المراجعة"""
        return self.db.query(Book).filter(
            Book.status == BookStatus.PENDING
        ).order_by(Book.created_at.desc()).limit(limit).all()

    def approve_book(self, book_id: int) -> Optional[Book]:
        """الموافقة على كتاب"""
        book = self.db.query(Book).filter(Book.id == book_id).first()
        if not book:
            return None

        book.status = BookStatus.ACTIVE
        self.db.commit()
        self.db.refresh(book)
        return book

    def reject_book(self, book_id: int, reason: str = None) -> Optional[Book]:
        """رفض كتاب"""
        book = self.db.query(Book).filter(Book.id == book_id).first()
        if not book:
            return None

        book.status = BookStatus.REJECTED
        book.rejection_reason = reason
        self.db.commit()
        self.db.refresh(book)
        return book

    def delete_book(self, book_id: int) -> bool:
        """حذف كتاب"""
        book = self.db.query(Book).filter(Book.id == book_id).first()
        if not book:
            return False

        self.db.delete(book)
        self.db.commit()
        return True

    def get_all_books(self, status: BookStatus = None) -> List[Book]:
        """الحصول على جميع الكتب"""
        query = self.db.query(Book)
        if status:
            query = query.filter(Book.status == status)
        return query.order_by(Book.created_at.desc()).all()

    # ==========================================
    # إدارة المستخدمين
    # ==========================================

    def get_all_users(self, status: UserStatus = None) -> List[User]:
        """الحصول على جميع المستخدمين"""
        query = self.db.query(User)
        if status:
            query = query.filter(User.status == status)
        return query.order_by(User.created_at.desc()).all()

    def ban_user(self, telegram_id: int) -> Optional[User]:
        """حظر مستخدم"""
        user = self.db.query(User).filter(User.telegram_id == telegram_id).first()
        if not user:
            return None

        user.status = UserStatus.BANNED
        self.db.commit()
        self.db.refresh(user)
        return user

    def unban_user(self, telegram_id: int) -> Optional[User]:
        """إلغاء حظر مستخدم"""
        user = self.db.query(User).filter(User.telegram_id == telegram_id).first()
        if not user:
            return None

        user.status = UserStatus.ACTIVE
        self.db.commit()
        self.db.refresh(user)
        return user

    def search_users(self, query: str) -> List[User]:
        """البحث عن مستخدمين"""
        return self.db.query(User).filter(
            (User.username.ilike(f"%{query}%")) |
            (User.first_name.ilike(f"%{query}%")) |
            (User.telegram_id == query)
        ).limit(50).all()

    # ==========================================
    # الإحصائيات
    # ==========================================

    def get_statistics(self) -> Dict:
        """الحصول على إحصائيات شاملة"""
        # إحصائيات الكتب
        total_books = self.db.query(func.count(Book.id)).scalar()
        active_books = self.db.query(func.count(Book.id)).filter(
            Book.status == BookStatus.ACTIVE
        ).scalar()
        pending_books = self.db.query(func.count(Book.id)).filter(
            Book.status == BookStatus.PENDING
        ).scalar()
        total_downloads = self.db.query(func.sum(Book.download_count)).scalar() or 0

        # إحصائيات المستخدمين
        total_users = self.db.query(func.count(User.id)).scalar()
        active_users = self.db.query(func.count(User.id)).filter(
            User.status == UserStatus.ACTIVE
        ).scalar()
        banned_users = self.db.query(func.count(User.id)).filter(
            User.status == UserStatus.BANNED
        ).scalar()

        # إحصائيات النقاط
        total_points = self.db.query(func.sum(UserPoints.current_balance)).scalar() or 0

        # إحصائيات المؤلفين والقسام
        total_authors = self.db.query(func.count(Author.id)).scalar()
        total_categories = self.db.query(func.count(BookCategory.id)).scalar()

        #增长率
        today = datetime.utcnow().date()
        week_ago = today - timedelta(days=7)
        month_ago = today - timedelta(days=30)

        new_users_today = self.db.query(func.count(User.id)).filter(
            User.created_at >= today
        ).scalar()

        new_users_week = self.db.query(func.count(User.id)).filter(
            User.created_at >= week_ago
        ).scalar()

        new_users_month = self.db.query(func.count(User.id)).filter(
            User.created_at >= month_ago
        ).scalar()

        return {
            "books": {
                "total": total_books,
                "active": active_books,
                "pending": pending_books,
                "total_downloads": total_downloads
            },
            "users": {
                "total": total_users,
                "active": active_users,
                "banned": banned_users,
                "new_today": new_users_today,
                "new_week": new_users_week,
                "new_month": new_users_month
            },
            "points": {
                "total": total_points
            },
            "content": {
                "authors": total_authors,
                "categories": total_categories
            }
        }

    def get_top_books(self, limit: int = 10) -> List[Book]:
        """الحصول على أكثر الكتب تحميلاً"""
        return self.db.query(Book).filter(
            Book.status == BookStatus.ACTIVE
        ).order_by(Book.download_count.desc()).limit(limit).all()

    def get_top_users(self, limit: int = 10) -> List[UserPoints]:
        """الحصول على أكثر المستخدمين نقاطاً"""
        return self.db.query(UserPoints).order_by(
            UserPoints.current_balance.desc()
        ).limit(limit).all()

    # ==========================================
    # سجلات المشرفين
    # ==========================================

    def add_log(
        self,
        admin_id: int,
        action: str,
        entity_type: str = None,
        entity_id: int = None,
        details: str = None
    ) -> AdminLog:
        """إضافة سجل للمشرف"""
        log = AdminLog(
            admin_id=admin_id,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            details=details
        )
        self.db.add(log)
        self.db.commit()
        self.db.refresh(log)
        return log

    def get_logs(self, admin_id: int = None, limit: int = 100) -> List[AdminLog]:
        """الحصول على سجلات المشرفين"""
        query = self.db.query(AdminLog)
        if admin_id:
            query = query.filter(AdminLog.admin_id == admin_id)
        return query.order_by(AdminLog.created_at.desc()).limit(limit).all()

    # ==========================================
    # إدارة المشرفين
    # ==========================================

    def add_admin(self, user_id: int, role: AdminRole = AdminRole.MODERATOR) -> AdminUser:
        """إضافة مشرف"""
        admin = AdminUser(
            user_id=user_id,
            role=role,
            is_active=True
        )
        self.db.add(admin)
        self.db.commit()
        self.db.refresh(admin)
        return admin

    def remove_admin(self, user_id: int) -> bool:
        """إزالة مشرف"""
        admin = self.db.query(AdminUser).filter(
            AdminUser.user_id == user_id
        ).first()
        if not admin:
            return False

        self.db.delete(admin)
        self.db.commit()
        return True

    def get_admin(self, user_id: int) -> Optional[AdminUser]:
        """الحصول على مشرف"""
        return self.db.query(AdminUser).filter(
            AdminUser.user_id == user_id
        ).first()

    def get_all_admins(self) -> List[AdminUser]:
        """الحصول على جميع المشرفين"""
        return self.db.query(AdminUser).filter(
            AdminUser.is_active == True
        ).all()

    # ==========================================
    # تصدير البيانات
    # ==========================================

    def export_books_csv(self) -> List[List]:
        """تصدير الكتب كـ CSV"""
        books = self.get_all_books(status=BookStatus.ACTIVE)

        data = []
        data.append(["ID", "العنوان", "المؤلف", "القسم", "التحميلات", "التقييم", "تاريخ الإنشاء"])

        for book in books:
            data.append([
                book.id,
                book.title,
                book.author.name if book.author else "",
                book.category.name if book.category else "",
                book.download_count,
                round(book.average_rating, 2),
                book.created_at.strftime("%Y-%m-%d")
            ])

        return data

    def export_users_csv(self) -> List[List]:
        """تصدير المستخدمين كـ CSV"""
        users = self.get_all_users()

        data = []
        data.append(["ID", "معرف تيليجرام", "الاسم", "الحالة", "التحميلات", "النقاط", "تاريخ الإنشاء"])

        for user in users:
            data.append([
                user.id,
                user.telegram_id,
                f"{user.first_name or ''} {user.last_name or ''}".strip(),
                user.status.value,
                user.total_downloads,
                user.points.current_balance if user.points else 0,
                user.created_at.strftime("%Y-%m-%d")
            ])

        return data
