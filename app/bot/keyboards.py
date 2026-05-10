"""
Keyboards Module - لوحات المفاتيح
جميع لوحات المفاتيح الديناميكية والعامة للبوت
"""
from functools import lru_cache
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
        [KeyboardButton(text="👤 ملفي الشخصي"), KeyboardButton(text="🎁 نقاطي")],
        [KeyboardButton(text="❤️ المفضلة"), KeyboardButton(text="📥 سجل التحميلات")],
        [KeyboardButton(text="⚙️ الإعدادات")]
    ]

    if is_owner:
        keyboard.append([KeyboardButton(text="👑 لوحة تحكم المالك")])

    return ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True)


def get_back_keyboard() -> ReplyKeyboardMarkup:
    """زر الرجوع"""
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="🔙 رجوع")]],
        resize_keyboard=True
    )


# ==========================================
# Inline Keyboards (أزرار Inline)
# ==========================================

def get_category_keyboard(categories: List[BookCategory] = None) -> InlineKeyboardMarkup:
    """أزرار الأقسام للتصفح - ديناميكية من قاعدة البيانات"""
    from app.database import SessionLocal
    from app.services.category_service import CategoryService
    from aiogram.utils.keyboard import InlineKeyboardBuilder
    
    builder = InlineKeyboardBuilder()
    
    # إذا لم يتم تمرير الأقسام، نجلبها من قاعدة البيانات
    if categories is None:
        categories = _load_active_categories()
    
    if not categories:
        # إذا لم توجد أقسام، نعرض زر لإضافتها (للمالك فقط)
        builder.add(InlineKeyboardButton(
            text="📚 لا توجد أقسام، أضف قسم جديد",
            callback_data="admin_categories"
        ))
    else:
        for cat in categories:
            icon = cat.icon or "📁"
            name = cat.name_ar or cat.name
            builder.add(InlineKeyboardButton(
                text=f"{icon} {name}",
                callback_data=f"cat_{cat.id}"
            ))
    
    builder.adjust(2)
    return builder.as_markup()

def _load_active_categories() -> List[BookCategory]:
    db = SessionLocal()
    try:
        return CategoryService(db).list_all(active_only=True)
    finally:
        db.close()

def get_book_keyboard(book_id: int, is_favorite: bool = False) -> InlineKeyboardMarkup:
    """أزرار الكتاب"""
    builder = InlineKeyboardBuilder()

    # زر التحميل
    builder.add(InlineKeyboardButton(
        text="📥 تحميل الكتاب",
        callback_data=f"download_{book_id}"
    ))

    # زر المفضلة
    if is_favorite:
        builder.add(InlineKeyboardButton(
            text="❤️ إزالة من المفضلة",
            callback_data=f"fav_{book_id}"
        ))
    else:
        builder.add(InlineKeyboardButton(
            text="🤍 إضافة للمفضلة",
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


def get_books_list_keyboard_paginated(books: List, page: int, total_books: int, limit: int, prefix: str) -> InlineKeyboardMarkup:
    """أزرار قائمة الكتب مع التصفح"""
    builder = InlineKeyboardBuilder()

    for book in books:
        builder.add(InlineKeyboardButton(
            text=f"📖 {book.title[:30]}...",
            callback_data=f"book_{book.id}"
        ))

    # أزرار التنقل
    nav_buttons = []
    if page > 1:
        nav_buttons.append(InlineKeyboardButton(
            text="⬅️ السابق",
            callback_data=f"{prefix}_{page - 1}"
        ))

    total_pages = (total_books + limit - 1) // limit
    if page < total_pages:
        nav_buttons.append(InlineKeyboardButton(
            text="➡️ التالي",
            callback_data=f"{prefix}_{page + 1}"
        ))

    if nav_buttons:
        builder.row(*nav_buttons)

    builder.add(InlineKeyboardButton(
        text="🔙 رجوع",
        callback_data=f"cat_{prefix.split('_')[2]}" if "author_cat" in prefix else "main_menu"
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
    """لوحة تحكم المالك"""
    builder = InlineKeyboardBuilder()

    builder.add(InlineKeyboardButton(
        text="📊 إحصائيات متقدمة",
        callback_data="admin_stats"
    ))
    builder.add(InlineKeyboardButton(
        text="📚 كتب قيد المراجعة",
        callback_data="admin_pending_books"
    ))
    builder.add(InlineKeyboardButton(
        text="📁 إدارة الأقسام",
        callback_data="admin_categories"
    ))
    builder.add(InlineKeyboardButton(
        text="✍️ إدارة المؤلفين",
        callback_data="admin_authors"
    ))
    builder.add(InlineKeyboardButton(
        text="📡 قنوات الإجبار",
        callback_data="admin_channels"
    ))
    builder.add(InlineKeyboardButton(
        text="🚫 إدارة المستخدمين",
        callback_data="admin_users"
    ))
    builder.add(InlineKeyboardButton(
        text="🤖 مساعد AI",
        callback_data="admin_ai"
    ))
    builder.add(InlineKeyboardButton(
        text="📤 رفع كتاب",
        callback_data="admin_upload_book"
    ))
    builder.add(InlineKeyboardButton(
        text="📤 تصدير CSV",
        callback_data="admin_export_csv"
    ))
    builder.add(InlineKeyboardButton(
        text="🗑️ حذف كتاب",
        callback_data="admin_delete_book"
    ))
    builder.add(InlineKeyboardButton(
        text="✏️ تعديل كتاب",
        callback_data="admin_edit_book"
    ))

    builder.adjust(2)
    return builder.as_markup()


def get_admin_categories_keyboard() -> InlineKeyboardMarkup:
    """أزرار إدارة الأقسام"""
    builder = InlineKeyboardBuilder()
    builder.add(InlineKeyboardButton(text="📋 عرض جميع الأقسام", callback_data="admin_cat_list"))
    builder.add(InlineKeyboardButton(text="➕ إضافة قسم جديد", callback_data="admin_add_category"))  # تغيير من admin_cat_add
    builder.add(InlineKeyboardButton(
        text="✏️ تعديل قسم",
        callback_data="admin_cat_edit"
    ))
    builder.add(InlineKeyboardButton(
        text="🗑️ حذف قسم",
        callback_data="admin_cat_delete"
    ))
    builder.add(InlineKeyboardButton(
        text="🔙 رجوع للوحة التحكم",
        callback_data="admin_menu"
    ))

    builder.adjust(2)
    return builder.as_markup()


def get_admin_authors_keyboard() -> InlineKeyboardMarkup:
    """أزرار إدارة المؤلفين"""
    builder = InlineKeyboardBuilder()
    builder = InlineKeyboardBuilder()
    builder.add(InlineKeyboardButton(text="📋 عرض جميع المؤلفين", callback_data="admin_auth_list"))
    builder.add(InlineKeyboardButton(text="➕ إضافة مؤلف جديد", callback_data="admin_add_author"))  # تغيير من admin_auth_add
    builder.add(InlineKeyboardButton(
        text="✏️ تعديل مؤلف",
        callback_data="admin_auth_edit"
    ))
    builder.add(InlineKeyboardButton(
        text="🗑️ حذف مؤلف",
        callback_data="admin_auth_delete"
    ))
    builder.add(InlineKeyboardButton(
        text="🔙 رجوع للوحة التحكم",
        callback_data="admin_menu"
    ))

    builder.adjust(2)
    return builder.as_markup()


def get_admin_channels_keyboard() -> InlineKeyboardMarkup:
    """أزرار إدارة القنوات"""
    builder = InlineKeyboardBuilder()
    builder.add(InlineKeyboardButton(text="📋 عرض القنوات", callback_data="admin_ch_list"))
    builder.add(InlineKeyboardButton(text="➕ إضافة قناة", callback_data="admin_add_channel"))  # تغيير من admin_ch_add
    builder.add(InlineKeyboardButton(
        text="🗑️ حذف قناة",
        callback_data="admin_ch_delete"
    ))
    builder.add(InlineKeyboardButton(
        text="📡 إعدادات النشر",
        callback_data="admin_ch_settings"
    ))
    builder.add(InlineKeyboardButton(
        text="🔙 رجوع للوحة التحكم",
        callback_data="admin_menu"
    ))

    builder.adjust(2)
    return builder.as_markup()


def get_admin_users_keyboard() -> InlineKeyboardMarkup:
    """أزرار إدارة المستخدمين"""
    builder = InlineKeyboardBuilder()

    builder.add(InlineKeyboardButton(
        text="👥 عرض جميع المستخدمين",
        callback_data="admin_users_list"
    ))
    builder.add(InlineKeyboardButton(
        text="🔍 البحث عن مستخدم",
        callback_data="admin_users_search"
    ))
    builder.add(InlineKeyboardButton(
        text="🚫 حظر مستخدم",
        callback_data="admin_user_ban"
    ))
    builder.add(InlineKeyboardButton(
        text="✅ فك حظر مستخدم",
        callback_data="admin_user_unban"
    ))
    builder.add(InlineKeyboardButton(
        text="📤 رسالة لمستخدم",
        callback_data="admin_user_message"
    ))
    builder.add(InlineKeyboardButton(
        text="📢 رسالة للجميع",
        callback_data="admin_broadcast"
    ))
    builder.add(InlineKeyboardButton(
        text="🔙 رجوع للوحة التحكم",
        callback_data="admin_menu"
    ))

    builder.adjust(2)
    return builder.as_markup()


def get_admin_book_actions_keyboard(book_id: int) -> InlineKeyboardMarkup:
    """أزرار إجراءات الكتاب في الإدارة"""
    builder = InlineKeyboardBuilder()

    builder.add(InlineKeyboardButton(
        text="✅ الموافقة",
        callback_data=f"admin_book_approve_{book_id}"
    ))
    builder.add(InlineKeyboardButton(
        text="❌ الرفض",
        callback_data=f"admin_book_reject_{book_id}"
    ))
    builder.add(InlineKeyboardButton(
        text="✏️ تعديل",
        callback_data=f"admin_book_edit_{book_id}"
    ))
    builder.add(InlineKeyboardButton(
        text="🗑️ حذف",
        callback_data=f"admin_book_delete_{book_id}"
    ))

    builder.adjust(2)
    return builder.as_markup()


def get_back_to_admin_keyboard() -> InlineKeyboardMarkup:
    """زر الرجوع للإدارة"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text="🔙 رجوع للوحة التحكم",
            callback_data="admin_menu"
        )]
    ])


def get_search_type_keyboard() -> InlineKeyboardMarkup:
    """أزرار نوع البحث"""
    builder = InlineKeyboardBuilder()

    builder.add(InlineKeyboardButton(
        text="🔤 بحث نصي",
        callback_data="search_text"
    ))
    builder.add(InlineKeyboardButton(
        text="🤖 بحث ذكي AI",
        callback_data="search_ai"
    ))
    builder.add(InlineKeyboardButton(
        text="📚 حسب القسم",
        callback_data="search_category"
    ))
    builder.add(InlineKeyboardButton(
        text="✍️ حسب المؤلف",
        callback_data="search_author"
    ))

    builder.adjust(2)
    return builder.as_markup()


# ==========================================
# New Feature Keyboards - أزرار الميزات الجديدة
# ==========================================

def get_market_keyboard() -> InlineKeyboardMarkup:
    """أزرار السوق"""
    builder = InlineKeyboardBuilder()

    builder.add(InlineKeyboardButton(
        text="🛒 تصفح السوق",
        callback_data="market_browse"
    ))
    builder.add(InlineKeyboardButton(
        text="🔍 البحث في السوق",
        callback_data="market_search"
    ))
    builder.add(InlineKeyboardButton(
        text="📦 مشترياتي",
        callback_data="market_purchases"
    ))
    builder.add(InlineKeyboardButton(
        text="💰 مبيعاتي",
        callback_data="market_sales"
    ))
    builder.add(InlineKeyboardButton(
        text="💜 قائمة أمنياتي",
        callback_data="market_wishlist"
    ))

    builder.adjust(2)
    return builder.as_markup()


def get_ai_features_keyboard() -> InlineKeyboardMarkup:
    """أزرار ميزات الذكاء الاصطناعي"""
    builder = InlineKeyboardBuilder()

    builder.add(InlineKeyboardButton(
        text="📝 ملخص سريع",
        callback_data="ai_summary_quick"
    ))
    builder.add(InlineKeyboardButton(
        text="📖 ملخص تفصيلي",
        callback_data="ai_summary_detailed"
    ))
    builder.add(InlineKeyboardButton(
        text="❓ سؤال عن الكتاب",
        callback_data="ai_question"
    ))
    builder.add(InlineKeyboardButton(
        text="👤 تحليل الشخصيات",
        callback_data="ai_characters"
    ))
    builder.add(InlineKeyboardButton(
        text="🎭 تحليل المشاعر",
        callback_data="ai_sentiment"
    ))
    builder.add(InlineKeyboardButton(
        text="📊 تحليل الموضوعات",
        callback_data="ai_themes"
    ))

    builder.adjust(2)
    return builder.as_markup()


def get_challenges_keyboard() -> InlineKeyboardMarkup:
    """أزرار التحديات"""
    builder = InlineKeyboardBuilder()

    builder.add(InlineKeyboardButton(
        text="🏆 التحديات المتاحة",
        callback_data="challenges_available"
    ))
    builder.add(InlineKeyboardButton(
        text="📋 تحدياتي النشطة",
        callback_data="challenges_active"
    ))
    builder.add(InlineKeyboardButton(
        text="🎖️ شاراتي",
        callback_data="challenges_badges"
    ))
    builder.add(InlineKeyboardButton(
        text="📊 إحصائياتي",
        callback_data="challenges_stats"
    ))
    builder.add(InlineKeyboardButton(
        text="🥇 لوحة المتصدرين",
        callback_data="challenges_leaderboard"
    ))
    builder.add(InlineKeyboardButton(
        text="🔥 التسلسل اليومي",
        callback_data="challenges_streak"
    ))

    builder.adjust(2)
    return builder.as_markup()


def get_referral_keyboard() -> InlineKeyboardMarkup:
    """أزرار الإحالة"""
    builder = InlineKeyboardBuilder()

    builder.add(InlineKeyboardButton(
        text="🔗 رابط الإحالة",
        callback_data="referral_link"
    ))
    builder.add(InlineKeyboardButton(
        text="📊 إحصائيات الإحالة",
        callback_data="referral_stats"
    ))
    builder.add(InlineKeyboardButton(
        text="💰 أرباحي",
        callback_data="referral_earnings"
    ))
    builder.add(InlineKeyboardButton(
        text="🎖️ شارات الإحالة",
        callback_data="referral_badges"
    ))
    builder.add(InlineKeyboardButton(
        text="👥 أفضل المحيلين",
        callback_data="referral_top"
    ))

    builder.adjust(2)
    return builder.as_markup()


def get_notifications_keyboard() -> InlineKeyboardMarkup:
    """أزرار الإشعارات"""
    builder = InlineKeyboardBuilder()

    builder.add(InlineKeyboardButton(
        text="📬 جميع الإشعارات",
        callback_data="notifications_all"
    ))
    builder.add(InlineKeyboardButton(
        text="🔔 غير المقروءة",
        callback_data="notifications_unread"
    ))
    builder.add(InlineKeyboardButton(
        text="📊 إحصائيات",
        callback_data="notifications_stats"
    ))
    builder.add(InlineKeyboardButton(
        text="⚙️ إعدادات الإشعارات",
        callback_data="notifications_settings"
    ))

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


def get_listing_keyboard(listing_id: int, is_owner_listing: bool = False) -> InlineKeyboardMarkup:
    """أزرار قائمة السوق"""
    builder = InlineKeyboardBuilder()

    builder.add(InlineKeyboardButton(
        text="🛒 اشتري الآن",
        callback_data=f"market_buy_{listing_id}"
    ))
    builder.add(InlineKeyboardButton(
        text="💜 إضافة للقائمة",
        callback_data=f"market_add_wish_{listing_id}"
    ))

    if is_owner_listing:
        builder.add(InlineKeyboardButton(
            text="✏️ تعديل",
            callback_data=f"market_edit_{listing_id}"
        ))
        builder.add(InlineKeyboardButton(
            text="🗑️ حذف",
            callback_data=f"market_delete_{listing_id}"
        ))

    builder.add(InlineKeyboardButton(
        text="📖 عرض الكتاب",
        callback_data=f"market_book_{listing_id}"
    ))

    builder.adjust(2)
    return builder.as_markup()


def get_auction_keyboard(auction_id: int) -> InlineKeyboardMarkup:
    """أزرار المزاد"""
    builder = InlineKeyboardBuilder()

    builder.add(InlineKeyboardButton(
        text="💰 المزايدة",
        callback_data=f"market_bid_{auction_id}"
    ))
    builder.add(InlineKeyboardButton(
        text="📊 مزاداتي",
        callback_data=f"market_my_bids_{auction_id}"
    ))
    builder.add(InlineKeyboardButton(
        text="📖 عرض الكتاب",
        callback_data=f"market_book_auc_{auction_id}"
    ))

    builder.adjust(2)
    return builder.as_markup()


# ==========================================
# Admin Keyboards Enhanced - أزرار الإدارة المحسنة
# ==========================================

def get_admin_keyboard_enhanced() -> InlineKeyboardMarkup:
    """لوحة تحكم المالك المحسنة"""
    builder = InlineKeyboardBuilder()

    builder.add(InlineKeyboardButton(
        text="📊 إحصائيات متقدمة",
        callback_data="admin_stats"
    ))
    builder.add(InlineKeyboardButton(
        text="📚 إدارة الكتب",
        callback_data="admin_books"
    ))
    builder.add(InlineKeyboardButton(
        text="📁 إدارة الأقسام",
        callback_data="admin_categories"
    ))
    builder.add(InlineKeyboardButton(
        text="✍️ إدارة المؤلفين",
        callback_data="admin_authors"
    ))
    builder.add(InlineKeyboardButton(
        text="📡 قنوات الإجبار",
        callback_data="admin_channels"
    ))
    builder.add(InlineKeyboardButton(
        text="🚫 إدارة المستخدمين",
        callback_data="admin_users"
    ))
    builder.add(InlineKeyboardButton(
        text="🏪 إدارة السوق",
        callback_data="admin_market"
    ))
    builder.add(InlineKeyboardButton(
        text="🏆 إدارة التحديات",
        callback_data="admin_challenges"
    ))
    builder.add(InlineKeyboardButton(
        text="🤖 مساعد AI",
        callback_data="admin_ai"
    ))
    builder.add(InlineKeyboardButton(
        text="🔒 الأمان والتدقيق",
        callback_data="admin_security"
    ))
    builder.add(InlineKeyboardButton(
        text="🔔 إدارة الإشعارات",
        callback_data="admin_notifications"
    ))
    builder.add(InlineKeyboardButton(
        text="🎯 إدارة الإحالات",
        callback_data="admin_referral"
    ))
    builder.add(InlineKeyboardButton(
        text="📊 لوحة المتصدرين",
        callback_data="admin_leaderboard"
    ))
    builder.add(InlineKeyboardButton(
        text="📤 رفع كتاب",
        callback_data="admin_upload_book"
    ))
    builder.add(InlineKeyboardButton(
        text="📤 تصدير CSV",
        callback_data="admin_export_csv"
    ))
    builder.add(InlineKeyboardButton(
        text="🗑️ حذف كتاب",
        callback_data="admin_delete_book"
    ))

    builder.adjust(2)
    return builder.as_markup()


def get_admin_market_keyboard() -> InlineKeyboardMarkup:
    """أزرار إدارة السوق"""
    builder = InlineKeyboardBuilder()

    builder.add(InlineKeyboardButton(
        text="📋 عرض القوائم",
        callback_data="admin_market_listings"
    ))
    builder.add(InlineKeyboardButton(
        text="🔨 إدارة المزادات",
        callback_data="admin_market_auctions"
    ))
    builder.add(InlineKeyboardButton(
        text="📊 إحصائيات السوق",
        callback_data="admin_market_stats"
    ))
    builder.add(InlineKeyboardButton(
        text="⚙️ إعدادات السوق",
        callback_data="admin_market_settings"
    ))
    builder.add(InlineKeyboardButton(
        text="🔙 رجوع للوحة التحكم",
        callback_data="admin_menu"
    ))

    builder.adjust(2)
    return builder.as_markup()


def get_admin_challenges_keyboard() -> InlineKeyboardMarkup:
    """أزرار إدارة التحديات"""
    builder = InlineKeyboardBuilder()

    builder.add(InlineKeyboardButton(
        text="🏆 عرض التحديات",
        callback_data="admin_ch_list"
    ))
    builder.add(InlineKeyboardButton(
        text="➕ إضافة تحدي",
        callback_data="admin_ch_add"
    ))
    builder.add(InlineKeyboardButton(
        text="🎖️ إدارة الشارات",
        callback_data="admin_badges"
    ))
    builder.add(InlineKeyboardButton(
        text="📊 لوحة المتصدرين",
        callback_data="admin_ch_leaderboard"
    ))
    builder.add(InlineKeyboardButton(
        text="🔙 رجوع للوحة التحكم",
        callback_data="admin_menu"
    ))

    builder.adjust(2)
    return builder.as_markup()


def get_admin_security_keyboard() -> InlineKeyboardMarkup:
    """أزرار إدارة الأمان"""
    builder = InlineKeyboardBuilder()

    builder.add(InlineKeyboardButton(
        text="📋 سجل التدقيق",
        callback_data="admin_audit_log"
    ))
    builder.add(InlineKeyboardButton(
        text="🚨 أحداث الأمان",
        callback_data="admin_security_events"
    ))
    builder.add(InlineKeyboardButton(
        text="🚫 القائمة السوداء",
        callback_data="admin_blacklist"
    ))
    builder.add(InlineKeyboardButton(
        text="📊 إحصائيات الأمان",
        callback_data="admin_security_stats"
    ))
    builder.add(InlineKeyboardButton(
        text="🔙 رجوع للوحة التحكم",
        callback_data="admin_menu"
    ))

    builder.adjust(2)
    return builder.as_markup()
def get_admin_books_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.add(InlineKeyboardButton(text="📋 قائمة الكتب", callback_data="admin_book_list"))
    builder.add(InlineKeyboardButton(text="⏳ قيد المراجعة", callback_data="admin_pending_books"))
    builder.add(InlineKeyboardButton(text="📤 رفع كتاب", callback_data="admin_upload_book"))
    builder.add(InlineKeyboardButton(text="🗑️ حذف كتاب", callback_data="admin_delete_book"))
    builder.add(InlineKeyboardButton(text="📥 تصدير CSV", callback_data="admin_export_csv"))
    builder.add(InlineKeyboardButton(text="🔙 رجوع", callback_data="admin_menu"))
    builder.adjust(2)
    return builder.as_markup()
def get_books_list_keyboard(books: list) -> InlineKeyboardMarkup:
    """نسخة مبسطة للتوافق مع الاستدعاءات القديمة - بدون تصفّح"""
    # يمكنك استدعاء النسخة المبنيّة على التصفح مع قيم افتراضية
    return get_books_list_keyboard_paginated(
        books=books,
        page=1,
        total_books=len(books),
        limit=len(books),
        prefix="books"
    )
