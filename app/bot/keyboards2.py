"""
Keyboards Module - لوحات المفاتيح
جميع لوحات المفاتيح الديناميكية والعامة للبوت
"""
from typing import List, Optional
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from app.database import SessionLocal
from app.services.category_service import CategoryService
from app.models.book import BookCategory

# ==========================================
# Reply Keyboards (أزرار الرد)
# ==========================================

def get_main_menu_keyboard(is_owner: bool = False) -> ReplyKeyboardMarkup:
    """القائمة الرئيسية"""
    keyboard = [
        [KeyboardButton(text="📚 تصفح الكتب"), KeyboardButton(text="🔍 بحث")],
        [KeyboardButton(text="👤 الملف الشخصي"), KeyboardButton(text="⚙️ الإعدادات")]
    ]
    if is_owner:
        keyboard.append([KeyboardButton(text="👑 لوحة تحكم المالك")])
    return ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True)

def get_back_keyboard() -> ReplyKeyboardMarkup:
    """زر الرجوع"""
    return ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="🔙 رجوع")]], resize_keyboard=True)

# ==========================================
# Inline Keyboards (أزرار إنلاين)
# ==========================================

def get_category_keyboard(categories: List) -> InlineKeyboardMarkup:
    """أزرار الأقسام"""
    builder = InlineKeyboardBuilder()
    for cat in categories:
        builder.add(InlineKeyboardButton(
            text=f"📁 {cat.name}",
            callback_data=f"cat_{cat.id}"
        ))
    builder.add(InlineKeyboardButton(
        text="🔙 القائمة الرئيسية",
        callback_data="main_menu"
    ))
    builder.adjust(2)
    return builder.as_markup()

def get_book_keyboard(book_id: int, is_favorite: bool = False) -> InlineKeyboardMarkup:
    """أزرار الكتاب"""
    builder = InlineKeyboardBuilder()
    # زر التحميل
    builder.add(InlineKeyboardButton(
        text="📥 تحميل الكتاب",
        callback_data=f"download_{book_id}"
    ))
    # زر المفضلة
    fav_text = "❤️ إزالة من المفضلة" if is_favorite else "🤍 إضافة للمفضلة"
    builder.add(InlineKeyboardButton(
        text=fav_text,
        callback_data=f"fav_{book_id}"
    ))
    # زر التقييم
    builder.add(InlineKeyboardButton(
        text="⭐ تقييم الكتاب",
        callback_data=f"rate_{book_id}"
    ))
    # زر المشاركة
    builder.add(InlineKeyboardButton(
        text="📤 مشاركة الكتاب",
        callback_data=f"share_{book_id}"
    ))
    builder.adjust(2)
    return builder.as_markup()

def get_rating_keyboard(book_id: int) -> InlineKeyboardMarkup:
    """أزرار التقييم"""
    builder = InlineKeyboardBuilder()
    for rating in [1, 2, 3, 4, 5]:
        builder.add(InlineKeyboardButton(
            text=f"{'⭐' * rating}{'☆' * (5 - rating)}",
            callback_data=f"rate_{rating}_{book_id}"
        ))
    builder.add(InlineKeyboardButton(
        text="🔙 إلغاء",
        callback_data=f"book_{book_id}"
    ))
    builder.adjust(5)
    return builder.as_markup()

def get_books_list_keyboard(books: List, page: int = 1) -> InlineKeyboardMarkup:
    """أزرار قائمة الكتب"""
    builder = InlineKeyboardBuilder()
    for book in books:
        builder.add(InlineKeyboardButton(
            text=f"📖 {book.title[:30]}...",
            callback_data=f"book_{book.id}"
        ))
    # أزرار التنقل
    if page > 1:
        builder.add(InlineKeyboardButton(
            text="⬅️ السابق",
            callback_data=f"page_{page - 1}"
        ))
    builder.add(InlineKeyboardButton(
        text="➡️ التالي",
        callback_data=f"page_{page + 1}"
    ))
    builder.add(InlineKeyboardButton(
        text="🔙 القائمة الرئيسية",
        callback_data="main_menu"
    ))
    builder.adjust(1)
    return builder.as_markup()

def get_user_profile_keyboard() -> InlineKeyboardMarkup:
    """أزرار الملف الشخصي"""
    builder = InlineKeyboardBuilder()
    builder.add(InlineKeyboardButton(
        text="📋 سجل التحميلات",
        callback_data="my_downloads"
    ))
    builder.add(InlineKeyboardButton(
        text="❤️ المفضلة",
        callback_data="my_favorites"
    ))
    builder.add(InlineKeyboardButton(
        text="🎁 دعوة صديق",
        callback_data="invite_friend"
    ))
    builder.add(InlineKeyboardButton(
        text="📊 لوحة النقاط",
        callback_data="points_leaderboard"
    ))
    builder.adjust(2)
    return builder.as_markup()

def get_settings_keyboard(language: str = "ar") -> InlineKeyboardMarkup:
    """أزرار الإعدادات"""
    builder = InlineKeyboardBuilder()
    # تبديل اللغة
    lang_text = "🇬🇧 English" if language == "ar" else "🇸🇦 العربية"
    builder.add(InlineKeyboardButton(
        text=f"🌐 اللغة: {lang_text}",
        callback_data="toggle_language"
    ))
    builder.add(InlineKeyboardButton(
        text="📊 إحصائياتي",
        callback_data="my_stats"
    ))
    builder.add(InlineKeyboardButton(
        text="📞 التواصل مع الدعم",
        callback_data="contact_support"
    ))
    builder.adjust(2)
    return builder.as_markup()

def get_confirm_keyboard(confirm_data: str) -> InlineKeyboardMarkup:
    """أزرار التأكيد"""
    builder = InlineKeyboardBuilder()
    builder.add(InlineKeyboardButton(
        text="✅ نعم، تأكيد",
        callback_data=f"confirm_{confirm_data}"
    ))
    builder.add(InlineKeyboardButton(
        text="❌ لا، إلغاء",
        callback_data=f"cancel_{confirm_data}"
    ))
    return builder.as_markup()

def get_empty_keyboard() -> InlineKeyboardMarkup:
    """لوحة مفاتيح فارغة"""
    return InlineKeyboardMarkup(inline_keyboard=[])

# ==========================================
# Admin Keyboards (أزرار الإدارة)
# ==========================================

def get_admin_keyboard() -> InlineKeyboardMarkup:
    """لوحة تحكم المالك (الأساسية)"""
    builder = InlineKeyboardBuilder()
    builder.add(InlineKeyboardButton(text="📊 إحصائيات", callback_data="admin_stats"))
    builder.add(InlineKeyboardButton(text="📚 إدارة الكتب", callback_data="admin_books"))
    builder.add(InlineKeyboardButton(text="📁 إدارة الأقسام", callback_data="admin_categories"))
    builder.add(InlineKeyboardButton(text="✍️ إدارة المؤلفين", callback_data="admin_authors"))
    builder.add(InlineKeyboardButton(text="📡 قنوات الإجبار", callback_data="admin_channels"))
    builder.add(InlineKeyboardButton(text="🚫 إدارة المستخدمين", callback_data="admin_users"))
    builder.add(InlineKeyboardButton(text="🤖 مساعد AI", callback_data="admin_ai"))
    builder.add(InlineKeyboardButton(text="🔙 القائمة الرئيسية", callback_data="main_menu"))
    builder.adjust(2)
    return builder.as_markup()

def get_admin_categories_keyboard() -> InlineKeyboardMarkup:
    """أزرار إدارة الأقسام"""
    builder = InlineKeyboardBuilder()
    builder.add(InlineKeyboardButton(text="📋 عرض جميع الأقسام", callback_data="admin_cat_list"))
    builder.add(InlineKeyboardButton(text="➕ إضافة قسم جديد", callback_data="admin_add_category"))
    builder.add(InlineKeyboardButton(text="🔙 رجوع للوحة التحكم", callback_data="admin_menu"))
    builder.adjust(2)
    return builder.as_markup()

def get_admin_authors_keyboard() -> InlineKeyboardMarkup:
    """أزرار إدارة المؤلفين"""
    builder = InlineKeyboardBuilder()
    builder.add(InlineKeyboardButton(text="📋 عرض جميع المؤلفين", callback_data="admin_auth_list"))
    builder.add(InlineKeyboardButton(text="➕ إضافة مؤلف جديد", callback_data="admin_add_author"))
    builder.add(InlineKeyboardButton(text="🔙 رجوع للوحة التحكم", callback_data="admin_menu"))
    builder.adjust(2)
    return builder.as_markup()

def get_admin_channels_keyboard() -> InlineKeyboardMarkup:
    """أزرار إدارة القنوات"""
    builder = InlineKeyboardBuilder()
    builder.add(InlineKeyboardButton(text="📋 عرض القنوات", callback_data="admin_ch_list"))
    builder.add(InlineKeyboardButton(text="➕ إضافة قناة", callback_data="admin_add_channel"))
    builder.add(InlineKeyboardButton(text="📡 إعدادات النشر", callback_data="admin_ch_settings"))
    builder.add(InlineKeyboardButton(text="🔙 رجوع للوحة التحكم", callback_data="admin_menu"))
    builder.adjust(2)
    return builder.as_markup()

def get_admin_users_keyboard() -> InlineKeyboardMarkup:
    """أزرار إدارة المستخدمين"""
    builder = InlineKeyboardBuilder()
    builder.add(InlineKeyboardButton(text="👥 عرض المستخدمين", callback_data="admin_users_list"))
    builder.add(InlineKeyboardButton(text="🚫 حظر مستخدم", callback_data="admin_user_ban"))
    builder.add(InlineKeyboardButton(text="🔙 رجوع للوحة التحكم", callback_data="admin_menu"))
    builder.adjust(2)
    return builder.as_markup()

def get_admin_books_keyboard() -> InlineKeyboardMarkup:
    """لوحة إدارة الكتب المتخصصة"""
    builder = InlineKeyboardBuilder()
    builder.add(InlineKeyboardButton(text="📋 قائمة الكتب", callback_data="admin_book_list"))
    builder.add(InlineKeyboardButton(text="⏳ قيد المراجعة", callback_data="admin_pending_books"))
    builder.add(InlineKeyboardButton(text="📤 رفع كتاب", callback_data="admin_upload_book"))
    builder.add(InlineKeyboardButton(text="🗑️ حذف كتاب", callback_data="admin_delete_book"))
    builder.add(InlineKeyboardButton(text="📥 تصدير CSV", callback_data="admin_export_csv"))
    builder.add(InlineKeyboardButton(text="🔙 رجوع", callback_data="admin_menu"))
    builder.adjust(2)
    return builder.as_markup()

def get_back_to_admin_keyboard() -> InlineKeyboardMarkup:
    """زر الرجوع للوحة التحكم"""
    builder = InlineKeyboardBuilder()
    builder.add(InlineKeyboardButton(text="🔙 رجوع للوحة التحكم", callback_data="admin_menu"))
    return builder.as_markup()

def get_admin_keyboard_enhanced() -> InlineKeyboardMarkup:
    """لوحة تحكم المالك المحسنة (المستخدمة حالياً)"""
    builder = InlineKeyboardBuilder()
    builder.add(InlineKeyboardButton(text="📊 إحصائيات متقدمة", callback_data="admin_stats"))
    builder.add(InlineKeyboardButton(text="📚 إدارة الكتب", callback_data="admin_books"))
    builder.add(InlineKeyboardButton(text="📁 إدارة الأقسام", callback_data="admin_categories"))
    builder.add(InlineKeyboardButton(text="✍️ إدارة المؤلفين", callback_data="admin_authors"))
    builder.add(InlineKeyboardButton(text="📡 قنوات الإجبار", callback_data="admin_channels"))
    builder.add(InlineKeyboardButton(text="🚫 إدارة المستخدمين", callback_data="admin_users"))
    builder.add(InlineKeyboardButton(text="🏪 إدارة السوق", callback_data="admin_market"))
    builder.add(InlineKeyboardButton(text="🏆 إدارة التحديات", callback_data="admin_challenges"))
    builder.add(InlineKeyboardButton(text="🤖 مساعد AI", callback_data="admin_ai"))
    builder.add(InlineKeyboardButton(text="🔒 الأمان والتدقيق", callback_data="admin_security"))
    builder.add(InlineKeyboardButton(text="🔔 إدارة الإشعارات", callback_data="admin_notifications"))
    builder.add(InlineKeyboardButton(text="🎯 إدارة الإحالات", callback_data="admin_referral"))
    builder.add(InlineKeyboardButton(text="📊 لوحة المتصدرين", callback_data="admin_leaderboard"))
    builder.add(InlineKeyboardButton(text="📤 رفع كتاب", callback_data="admin_upload_book"))
    builder.add(InlineKeyboardButton(text="📤 تصدير CSV", callback_data="admin_export_csv"))
    builder.add(InlineKeyboardButton(text="🗑️ حذف كتاب", callback_data="admin_delete_book"))
    builder.adjust(2)
    return builder.as_markup()

def get_admin_market_keyboard() -> InlineKeyboardMarkup:
    """أزرار إدارة السوق"""
    builder = InlineKeyboardBuilder()
    builder.add(InlineKeyboardButton(text="📋 عرض القوائم", callback_data="admin_market_listings"))
    builder.add(InlineKeyboardButton(text="🔨 إدارة المزادات", callback_data="admin_market_auctions"))
    builder.add(InlineKeyboardButton(text="⚙️ إعدادات السوق", callback_data="admin_market_settings"))
    builder.add(InlineKeyboardButton(text="🔙 رجوع للوحة التحكم", callback_data="admin_menu"))
    builder.adjust(2)
    return builder.as_markup()

def get_admin_challenges_keyboard() -> InlineKeyboardMarkup:
    """أزرار إدارة التحديات"""
    builder = InlineKeyboardBuilder()
    builder.add(InlineKeyboardButton(text="🏆 عرض التحديات", callback_data="admin_ch_list"))
    builder.add(InlineKeyboardButton(text="➕ إضافة تحدي", callback_data="admin_ch_add"))
    builder.add(InlineKeyboardButton(text="🔙 رجوع للوحة التحكم", callback_data="admin_menu"))
    builder.adjust(2)
    return builder.as_markup()

def get_admin_security_keyboard() -> InlineKeyboardMarkup:
    """أزرار إدارة الأمان"""
    builder = InlineKeyboardBuilder()
    builder.add(InlineKeyboardButton(text="📋 سجل التدقيق", callback_data="admin_audit_log"))
    builder.add(InlineKeyboardButton(text="🚫 القائمة السوداء", callback_data="admin_blacklist"))
    builder.add(InlineKeyboardButton(text="🔙 رجوع للوحة التحكم", callback_data="admin_menu"))
    builder.adjust(2)
    return builder.as_markup()

def get_admin_book_actions_keyboard(book_id: int) -> InlineKeyboardMarkup:
    """أزرار مراجعة كتاب محدد"""
    builder = InlineKeyboardBuilder()
    builder.add(InlineKeyboardButton(text="✅ موافقة", callback_data=f"admin_book_approve_{book_id}"))
    builder.add(InlineKeyboardButton(text="❌ رفض", callback_data=f"admin_book_reject_{book_id}"))
    builder.add(InlineKeyboardButton(text="🗑️ حذف", callback_data=f"admin_book_delete_{book_id}"))
    builder.add(InlineKeyboardButton(text="🔙 رجوع", callback_data="admin_pending_books"))
    builder.adjust(2)
    return builder.as_markup()

def get_main_menu_enhanced_keyboard(is_owner: bool = False) -> ReplyKeyboardMarkup:
    """القائمة الرئيسية المحسنة"""
    keyboard = [
        [KeyboardButton(text="📚 تصفح الكتب"), KeyboardButton(text="🔍 بحث")],
        [KeyboardButton(text="🏪 السوق"), KeyboardButton(text="🤖 مساعد AI")],
        [KeyboardButton(text="👤 ملفي الشخصي"), KeyboardButton(text="🎁 نقاطي")],
        [KeyboardButton(text="🏆 التحديات"), KeyboardButton(text="🎯 الإحالة")],
        [KeyboardButton(text="📬 إشعاراتي"), KeyboardButton(text="❤️ المفضلة")],
        [KeyboardButton(text="📥 سجل التحميلات"), KeyboardButton(text="⚙️ الإعدادات")]
    ]
    if is_owner:
        keyboard.append([KeyboardButton(text="👑 لوحة تحكم المالك")])
    return ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True)
