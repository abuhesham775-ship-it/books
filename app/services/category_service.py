"""
Category Service - خدمة الأقسام
"""
from typing import List, Optional
from sqlalchemy.orm import Session
from app.models.book import BookCategory


class CategoryService:
    """خدمة إدارة الأقسام"""

    def __init__(self, db: Session):
        self.db = db

    def create(
        self,
        name: str,
        name_ar: Optional[str] = None,
        name_en: Optional[str] = None,
        description: Optional[str] = None,
        parent_id: Optional[int] = None,
        icon: Optional[str] = None,
        sort_order: int = 0
    ) -> BookCategory:
        """إنشاء قسم جديد"""
        category = BookCategory(
            name=name,
            name_ar=name_ar or name,
            name_en=name_en,
            description=description,
            parent_id=parent_id,
            icon=icon,
            sort_order=sort_order
        )
        self.db.add(category)
        self.db.commit()
        self.db.refresh(category)
        return category

    def update(
        self,
        category_id: int,
        name: Optional[str] = None,
        name_ar: Optional[str] = None,
        name_en: Optional[str] = None,
        description: Optional[str] = None,
        is_active: Optional[bool] = None,
        parent_id: Optional[int] = None,
        icon: Optional[str] = None,
        sort_order: Optional[int] = None
    ) -> Optional[BookCategory]:
        """تحديث قسم"""
        category = self.get_by_id(category_id)
        if not category:
            return None

        if name is not None:
            category.name = name
        if name_ar is not None:
            category.name_ar = name_ar
        if name_en is not None:
            category.name_en = name_en
        if description is not None:
            category.description = description
        if is_active is not None:
            category.is_active = is_active
        if parent_id is not None:
            category.parent_id = parent_id
        if icon is not None:
            category.icon = icon
        if sort_order is not None:
            category.sort_order = sort_order

        self.db.commit()
        self.db.refresh(category)
        return category

    def delete(self, category_id: int) -> bool:
        """حذف قسم"""
        category = self.get_by_id(category_id)
        if not category:
            return False

        self.db.delete(category)
        self.db.commit()
        return True

    def get_by_id(self, category_id: int) -> Optional[BookCategory]:
        """الحصول على قسم بالمعرف"""
        return self.db.query(BookCategory).filter(
            BookCategory.id == category_id
        ).first()

    def list_all(self, active_only: bool = True) -> List[BookCategory]:
        """عرض جميع الأقسام"""
        query = self.db.query(BookCategory)
        if active_only:
            query = query.filter(BookCategory.is_active == True)
        return query.order_by(BookCategory.sort_order, BookCategory.name).all()

    def get_by_name(self, name: str) -> Optional[BookCategory]:
        """الحصول على قسم بالاسم"""
        return self.db.query(BookCategory).filter(
            BookCategory.name == name
        ).first()

    def get_subcategories(self, parent_id: int) -> List[BookCategory]:
        """الحصول على الأقسام الفرعية"""
        return self.db.query(BookCategory).filter(
            BookCategory.parent_id == parent_id,
            BookCategory.is_active == True
        ).order_by(BookCategory.sort_order).all()

    def get_main_categories(self) -> List[BookCategory]:
        """الحصول على الأقسام الرئيسية فقط"""
        return self.db.query(BookCategory).filter(
            BookCategory.parent_id == None,
            BookCategory.is_active == True
        ).order_by(BookCategory.sort_order).all()

    def toggle_active(self, category_id: int) -> Optional[BookCategory]:
        """تبديل حالة القسم"""
        category = self.get_by_id(category_id)
        if not category:
            return None

        category.is_active = not category.is_active
        self.db.commit()
        self.db.refresh(category)
        return category

    def count_books(self, category_id: int) -> int:
        """عدد الكتب في القسم"""
        category = self.get_by_id(category_id)
        if not category:
            return 0
        return len(category.books)
