"""
Handlers Features Module - جميع المعالجات الجديدة
الملف الرئيسي للبوت مع جميع الميزات
"""
import asyncio
import os
import io
import csv
import logging
from typing import Union, Callable, Any, Awaitable, Dict, Optional
from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery, Update, TelegramObject, ErrorEvent  # أضف ErrorEvent
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.filters.callback_data import CallbackData
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.enums import ChatType
from aiogram.dispatcher.middlewares.base import BaseMiddleware

from app.database import SessionLocal
from app.services.user_service import UserService
from app.services.book_service import BookService
from app.services.category_service import CategoryService
from app.services.author_service import AuthorService
from app.services.channel_service import ChannelService
from app.services.points_service import PointsService
from app.services.search_service import SearchService
from app.services.ai_service import ai_service
from app.services.security_service import SecurityService
from app.services.referral_service import ReferralService
from app.services.challenge_service import ChallengeService
from app.services.market_service import MarketService
from app.models.book import BookStatus
from app.models.user import UserStatus
from app.models.points import TransactionType
from config.settings import get_settings
from app.bot.keyboards import (
    get_main_menu_keyboard,
    get_main_menu_enhanced_keyboard,
    get_category_keyboard,
    get_book_keyboard,
    get_rating_keyboard,
    get_books_list_keyboard,
    get_books_list_keyboard_paginated,
    get_user_profile_keyboard,
    get_settings_keyboard,
    get_admin_keyboard,
    get_admin_keyboard_enhanced,
    get_admin_categories_keyboard,
    get_admin_authors_keyboard,
    get_admin_channels_keyboard,
    get_admin_users_keyboard,
    get_admin_book_actions_keyboard,
    get_admin_books_keyboard,
    get_admin_market_keyboard,
    get_admin_challenges_keyboard,
    get_admin_security_keyboard,
    get_confirm_keyboard,
    get_back_to_admin_keyboard,
    get_search_type_keyboard,
    get_back_keyboard
)
from app.utils.helpers import format_book_info, format_user_profile, truncate_text

settings = get_settings()
router = Router()
logger = logging.getLogger(__name__)

# ==========================================
# Middleware للحد من معدل الطلبات
# ==========================================

class RateLimitMiddleware(BaseMiddleware):
    """ميدلوير للحد من معدل الطلبات"""

    def __init__(self):
        self.user_requests = {}
        self.rate_limit = 10  # طلبات في الدقيقة
        self.time_window = 60  # ثانية

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any]
    ) -> Any:
        if isinstance(event, (Message, CallbackQuery)) and event.from_user:
            user_id = event.from_user.id
            if settings.is_owner(user_id):
                return await handler(event, data)

            current_time = asyncio.get_running_loop().time()

            if user_id not in self.user_requests:
                self.user_requests[user_id] = []

            # تنظيف الطلبات القديمة
            self.user_requests[user_id] = [
                req_time for req_time in self.user_requests[user_id]
                if current_time - req_time < self.time_window
            ]

            if len(self.user_requests[user_id]) >= self.rate_limit:
                if isinstance(event, Message):
                    await event.answer("⚠️ تم تجاوز حد الطلبات. يرجى الانتظار دقيقة قبل المحاولة مرة أخرى.")
                elif isinstance(event, CallbackQuery):
                    await event.answer("⚠️ تم تجاوز حد الطلبات. يرجى الانتظار.", show_alert=True)
                return

            self.user_requests[user_id].append(current_time)

        return await handler(event, data)

# ==========================================
# Middleware للاشتراك الإجباري
# ==========================================

class ForceJoinMiddleware(BaseMiddleware):
    """ميدلوير لفحص الاشتراك الإجباري"""

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any]
    ) -> Any:
        if not isinstance(event, (Message, CallbackQuery)) or not event.from_user:
            return await handler(event, data)

        user_id = event.from_user.id
        if settings.is_owner(user_id):
            return await handler(event, data)

        db = SessionLocal()
        try:
            user_service = UserService(db)
            if user_service.is_banned(user_id):
                if isinstance(event, Message):
                    await event.answer("🚫 حسابك محظور. لا يمكنك استخدام البوت.")
                else:
                    await event.answer("🚫 حسابك محظور.", show_alert=True)
                return

            # السماح بالمفاتيح الخاصة بالتحقق من الاشتراك
            if isinstance(event, CallbackQuery) and event.data == "check_subscription":
                return await handler(event, data)

            # السماح بأوامر المساعدة الأساسية بدون فحص اشتراك
            if isinstance(event, Message) and event.text and event.text.startswith('/'):
                if event.text in ['/start', '/help', '/cancel']:
                    return await handler(event, data)

            channel_service = ChannelService(db)
            bot = data.get('bot') or getattr(event, 'bot', None)
            if not bot:
                return await handler(event, data)

            is_subscribed, not_subscribed = await channel_service.check_all_subscriptions(
                bot, user_id
            )

            if not is_subscribed:
                keyboard = InlineKeyboardMarkup(inline_keyboard=[])
                for channel in not_subscribed:
                    if channel.channel_link:
                        keyboard.inline_keyboard.append([
                            InlineKeyboardButton(
                                text=f"📢 الانضمام لـ {channel.channel_name or channel.channel_id}",
                                url=channel.channel_link
                            )
                        ])
                keyboard.inline_keyboard.append([
                    InlineKeyboardButton(
                        text="✅ تم الاشتراك",
                        callback_data="check_subscription"
                    )
                ])

                if isinstance(event, Message):
                    await event.answer(
                        "⚠️ يجب الاشتراك بالقنوات التالية أولاً:",
                        reply_markup=keyboard
                    )
                else:
                    await event.answer(
                        "⚠️ يجب الاشتراك بالقنوات التالية أولاً:",
                        reply_markup=keyboard,
                        show_alert=True
                    )
                return

            return await handler(event, data)
        finally:
            db.close()


# ==========================================
# States Groups
# ==========================================

class UserStates(StatesGroup):
    """حالات المستخدم"""
    main = State()
    browsing = State()
    searching = State()
    profile = State()


class AdminStates(StatesGroup):
    """حالات الإدارة"""
    waiting_category_name = State()
    waiting_category_edit = State()
    waiting_author_name = State()
    waiting_author_edit = State()
    waiting_channel_id = State()
    waiting_channel_link = State()
    waiting_user_id = State()
    waiting_broadcast = State()
    waiting_search = State()
    waiting_book_title = State()
    waiting_book_author = State()
    waiting_book_description = State()
    waiting_book_file = State()
    waiting_book_category = State()
    waiting_reject_reason = State()
    waiting_message_user = State()
    waiting_ai_question = State()
    waiting_author_category = State()
    waiting_book_category = State()
    waiting_book_author_select = State()


# ==========================================
# Helper Functions
# ==========================================

def is_owner(telegram_id: int) -> bool:
    """التحقق من أن المستخدم هو المالك"""
    return settings.is_owner(telegram_id)


def get_user_from_event(event) -> Optional[dict]:
    """الحصول على بيانات المستخدم من الحدث"""
    if hasattr(event, 'from_user'):
        return {
            'telegram_id': event.from_user.id,
            'username': event.from_user.username,
            'first_name': event.from_user.first_name,
            'last_name': event.from_user.last_name
        }
    return None


def ensure_user(telegram_id: int, username: str = None, first_name: str = None, last_name: str = None):
    """التأكد من وجود المستخدم وإنشاؤه"""
    db = SessionLocal()
    try:
        user_service = UserService(db)
        user = user_service.get_or_create_user(
            telegram_id=telegram_id,
            username=username,
            first_name=first_name,
            last_name=last_name
        )
        return user
    finally:
        db.close()



def resolve_book_file_path(stored_path: Optional[str]) -> Optional[str]:
    """Resolve stored book file paths across different deployment layouts."""
    if not stored_path:
        return None

    cleaned = stored_path.strip().strip('"').strip("'")
    if cleaned.startswith("file://"):
        cleaned = cleaned.replace("file://", "", 1)

    candidates = [cleaned]
    if not os.path.isabs(cleaned):
        project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
        candidates.extend([
            os.path.join(project_root, cleaned),
            os.path.join(project_root, settings.upload_folder, os.path.basename(cleaned)),
            os.path.join(project_root, "uploads", os.path.basename(cleaned)),
            os.path.abspath(cleaned),
        ])

    for candidate in candidates:
        if candidate and os.path.exists(candidate):
            return candidate
    return None


def safe_edit_text(message_or_callback, text: str, reply_markup=None):
    """Edit message text without crashing on identical content."""
    try:
        return message_or_callback.edit_text(text, reply_markup=reply_markup)
    except TelegramBadRequest as exc:
        if "message is not modified" in str(exc).lower():
            return None
        raise


# ==========================================
# Command Handlers - أوامر المالك النصية
# ==========================================

@router.message(Command("stats"))
async def cmd_stats(message: Message):
    """عرض الإحصائيات"""
    if not is_owner(message.from_user.id):
        await message.answer("غير مصرح لك بهذا الأمر.")
        return

    db = SessionLocal()
    try:
        book_service = BookService(db)
        user_service = UserService(db)

        book_stats = book_service.get_statistics()
        user_stats = user_service.get_statistics()

        stats_text = f"""
📊 إحصائيات المكتبة:

📚 الكتب:
• الإجمالي: {book_stats['total']}
• النشطة: {book_stats['active']}
• قيد المراجعة: {book_stats['pending']}
• المرفوضة: {book_stats['rejected']}
• إجمالي التحميلات: {book_stats['total_downloads']}
• متوسط التقييم: {book_stats['average_rating']}

👥 المستخدمين:
• الإجمالي: {user_stats['total']}
• النشطين: {user_stats['active']}
• المحظورين: {user_stats['banned']}
• إجمالي التحميلات: {user_stats['total_downloads']}
• المميزين: {user_stats['premium']}
        """
        await message.answer(stats_text)
    finally:
        db.close()


@router.message(Command("exportcsv"))
async def cmd_export_csv(message: Message):
    """تصدير بيانات الكتب كـ CSV"""
    if not is_owner(message.from_user.id):
        await message.answer("غير مصرح لك بهذا الأمر.")
        return

    db = SessionLocal()
    try:
        book_service = BookService(db)
        books = book_service.get_all_books(status=BookStatus.ACTIVE)

        # إنشاء ملف CSV في الذاكرة
        output = io.StringIO()
        writer = csv.writer(output)

        # كتابة Headers
        writer.writerow(['ID', 'العنوان', 'المؤلف', 'القسم', 'التحميلات', 'التقييم', 'تاريخ الإنشاء'])

        # كتابة البيانات
        for book in books:
            writer.writerow([
                book.id,
                book.title,
                book.author.name if book.author else '',
                book.category.name if book.category else '',
                book.download_count,
                book.average_rating,
                book.created_at.strftime('%Y-%m-%d')
            ])

        # إنشاء ملف
        output.seek(0)
        bytes_io = io.BytesIO(output.getvalue().encode('utf-8'))
        bytes_io.name = 'books_export.csv'

        await message.answer_document(
            document=bytes_io,
            caption="📤 تم تصدير بيانات الكتب"
        )
    finally:
        db.close()


@router.message(Command("listcategories"))
async def cmd_list_categories(message: Message):
    """عرض قائمة الأقسام"""
    if not is_owner(message.from_user.id):
        await message.answer("غير مصرح لك بهذا الأمر.")
        return

    db = SessionLocal()
    try:
        category_service = CategoryService(db)
        categories = category_service.list_all()

        if not categories:
            await message.answer("لا توجد أقسام حالياً.")
            return

        text = "📁 الأقسام:\n\n"
        for i, cat in enumerate(categories, 1):
            text += f"{i}. {cat.name} (ID: {cat.id})\n"

        await message.answer(text)
    finally:
        db.close()


@router.message(Command("listauthors"))
async def cmd_list_authors(message: Message):
    """عرض قائمة المؤلفين"""
    if not is_owner(message.from_user.id):
        await message.answer("غير مصرح لك بهذا الأمر.")
        return

    db = SessionLocal()
    try:
        author_service = AuthorService(db)
        authors = author_service.list_all()

        if not authors:
            await message.answer("لا توجد مؤلفين حالياً.")
            return

        text = "✍️ المؤلفين:\n\n"
        for i, auth in enumerate(authors, 1):
            text += f"{i}. {auth.name} (ID: {auth.id})\n"

        await message.answer(text)
    finally:
        db.close()


@router.message(Command("listchannels"))
async def cmd_list_channels(message: Message):
    """عرض قائمة قنوات الاشتراك الإجباري"""
    if not is_owner(message.from_user.id):
        await message.answer("غير مصرح لك بهذا الأمر.")
        return

    db = SessionLocal()
    try:
        channel_service = ChannelService(db)
        channels = channel_service.get_all_channels()

        if not channels:
            await message.answer("لا توجد قنوات اشتراك إجباري.")
            return

        text = "📡 قنوات الاشتراك الإجباري:\n\n"
        for ch in channels:
            status = "مطلوب" if ch.is_required else "اختياري"
            text += f"• {ch.channel_name or ch.channel_id}\n  الحالة: {status}\n"

        await message.answer(text)
    finally:
        db.close()


@router.message(Command("aifind"))
async def cmd_ai_find(message: Message):
    """البحث الذكي بالذكاء الاصطناعي"""
    if not is_owner(message.from_user.id):
        await message.answer("غير مصرح لك بهذا الأمر.")
        return

    # الحصول على نص البحث بعد الأمر
    query = message.text.replace('/aifind', '').strip()
    if not query:
        await message.answer("الاستخدام: /aifind [نص البحث]")
        return

    db = SessionLocal()
    try:
        search_service = SearchService(db)
        books, authors = search_service.text_search(query, limit=5)

        if not books and not authors:
            await message.answer(f"لم يتم العثور على نتائج لـ: {query}")
            return

        response = f"🔍 نتائج البحث عن: {query}\n\n"

        if books:
            response += "📚 الكتب:\n"
            for book in books:
                response += f"• {book.title}\n"

        if authors:
            response += "\n✍️ المؤلفين:\n"
            for auth in authors:
                response += f"• {auth.name}\n"

        await message.answer(response)
    finally:
        db.close()


# ==========================================
# Button Handlers - معالجات الأزرار
# ==========================================

@router.message(F.text == "📚 تصفح الكتب")
async def browse_books(message: Message):
    """تصفح الكتب"""
    user = ensure_user(
        message.from_user.id,
        message.from_user.username,
        message.from_user.first_name,
        message.from_user.last_name
    )

    text = "📚 اختر قسمًا للتصفح:\n\n"
    keyboard = get_category_keyboard()

    await message.answer(text, reply_markup=keyboard)


@router.message(F.text == "🔍 بحث")
async def search_books(message: Message):
    """البحث عن الكتب"""
    user = ensure_user(
        message.from_user.id,
        message.from_user.username,
        message.from_user.first_name,
        message.from_user.last_name
    )

    text = "🔍 كيف تريد البحث؟"
    keyboard = get_search_type_keyboard()

    await message.answer(text, reply_markup=keyboard)


@router.message(F.text == "👤 ملفي الشخصي")
async def my_profile(message: Message):
    """عرض الملف الشخصي"""
    db = SessionLocal()
    try:
        user_service = UserService(db)
        points_service = PointsService(db)

        user = user_service.get_or_create_user(
            message.from_user.id,
            message.from_user.username,
            message.from_user.first_name,
            message.from_user.last_name
        )

        user_points = points_service.get_user_points(user.id)
        points = user_points.current_balance if user_points else 0

        profile_text = format_user_profile(user, points)
        keyboard = get_user_profile_keyboard()

        await message.answer(profile_text, reply_markup=keyboard)
    finally:
        db.close()


@router.message(F.text == "🎁 نقاطي")
async def my_points(message: Message):
    """عرض نقاطي"""
    db = SessionLocal()
    try:
        user_service = UserService(db)
        points_service = PointsService(db)

        user = user_service.get_or_create_user(
            message.from_user.id,
            message.from_user.username,
            message.from_user.first_name,
            message.from_user.last_name
        )

        user_points = points_service.get_or_create_user_points(user.id)
        transactions = points_service.get_transactions(user.id, limit=10)

        text = f"""
🎁 نقاطي

💰 الرصيد الحالي: {user_points.current_balance}
📊 إجمالي المكتسب: {user_points.lifetime_earned}
📈 المستوى: {user.level}

📋 آخر المعاملات:
"""

        for trans in transactions:
            trans_type_text = {
                TransactionType.REFERRAL: "إحالة",
                TransactionType.DOWNLOAD: "تحميل",
                TransactionType.REVIEW: "تقييم",
                TransactionType.PURCHASE: "شراء",
                TransactionType.DEDUCTION: "خصم",
                TransactionType.COUPON: "كوبون",
                TransactionType.GIFT: "هدية"
            }.get(trans.transaction_type, str(trans.transaction_type))

            sign = "+" if trans.amount > 0 else ""
            text += f"• {trans_type_text}: {sign}{trans.amount}\n"

        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📊 لوحة المتصدرين", callback_data="points_leaderboard")]
        ])

        await message.answer(text, reply_markup=keyboard)
    finally:
        db.close()


@router.message(F.text == "❤️ المفضلة")
async def my_favorites(message: Message):
    """عرض المفضلة"""
    db = SessionLocal()
    try:
        user_service = UserService(db)
        book_service = BookService(db)

        user = user_service.get_or_create_user(
            message.from_user.id,
            message.from_user.username,
            message.from_user.first_name,
            message.from_user.last_name
        )

        favorites = user_service.get_user_favorites(message.from_user.id)

        if not favorites:
            await message.answer("📭 لا توجد كتب في المفضلة لديك.")
            return

        text = "❤️ كتبك المفضلة:\n\n"
        books = []
        for fav in favorites:
            book = book_service.get_book(fav.book_id)
            if book:
                books.append(book)
                text += f"📖 {truncate_text(book.title, 40)}\n"

        keyboard = get_books_list_keyboard(books[:10]) if books else None

        await message.answer(text, reply_markup=keyboard)
    finally:
        db.close()


@router.message(F.text == "📥 سجل التحميلات")
async def download_history(message: Message):
    """عرض سجل التحميلات"""
    db = SessionLocal()
    try:
        user_service = UserService(db)
        book_service = BookService(db)

        user = user_service.get_or_create_user(
            message.from_user.id,
            message.from_user.username,
            message.from_user.first_name,
            message.from_user.last_name
        )

        downloads = user_service.get_user_downloads(message.from_user.id, limit=20)

        if not downloads:
            await message.answer("📭 لا توجد تحميلات سابقة.")
            return

        text = "📥 سجل التحميلات:\n\n"
        books = []
        for dl in downloads:
            book = book_service.get_book(dl.book_id)
            if book:
                books.append(book)
                text += f"📖 {truncate_text(book.title, 40)}\n📅 {dl.downloaded_at.strftime('%Y-%m-%d')}\n\n"

        keyboard = get_books_list_keyboard(books) if books else None

        await message.answer(text, reply_markup=keyboard)
    finally:
        db.close()


@router.message(F.text == "⚙️ الإعدادات")
async def settings_menu(message: Message):
    """قائمة الإعدادات"""
    ensure_user(
        message.from_user.id,
        message.from_user.username,
        message.from_user.first_name,
        message.from_user.last_name
    )

    db = SessionLocal()
    try:
        user_service = UserService(db)
        user_obj = user_service.get_user_by_telegram_id(message.from_user.id)
        language = user_obj.language if user_obj else "ar"

        text = "⚙️ الإعدادات"
        keyboard = get_settings_keyboard(language)

        await message.answer(text, reply_markup=keyboard)
    finally:
        db.close()


@router.message(F.text == "👑 لوحة تحكم المالك")
async def admin_panel(message: Message):
    """لوحة تحكم المالك"""
    if not is_owner(message.from_user.id):
        await message.answer("غير مصرح لك.")
        return

    text = "👑 مرحباً أيها المالك!\n\nاختر مما يلي:"
    keyboard = get_admin_keyboard_enhanced()

    await message.answer(text, reply_markup=keyboard)


@router.message(F.text == "🔙 رجوع")
async def go_back(message: Message):
    """الرجوع للقائمة الرئيسية"""
    user = ensure_user(
        message.from_user.id,
        message.from_user.username,
        message.from_user.first_name,
        message.from_user.last_name
    )

    text = "🏠 القائمة الرئيسية"
    keyboard = get_main_menu_keyboard(is_owner(message.from_user.id))

    await message.answer(text, reply_markup=keyboard)


# ==========================================
# Callback Handlers - معالجات الأازرار Callback
# ==========================================

@router.callback_query(F.data == "main_menu")
async def callback_main_menu(callback: CallbackQuery):
    text = "🏠 القائمة الرئيسية"
    keyboard = get_main_menu_keyboard(is_owner(callback.from_user.id))
    await callback.message.delete()
    await callback.message.answer(text, reply_markup=keyboard)

# @router.callback_query(F.data.startswith("cat_"))
# async def callback_category(callback: CallbackQuery):
#     """عرض كتب القسم"""
#     category_id = int(callback.data.split("_")[1])

#     db = SessionLocal()
#     try:
#         book_service = BookService(db)
#         category_service = CategoryService(db)

#         category = category_service.get_by_id(category_id)
#         if not category:
#             await callback.answer("القسم غير موجود", show_alert=True)
#             return

#         books = book_service.get_books_by_category(category_id, limit=20)

#         name = category.name_ar or category.name
#         text = f"📁 {name}\n\n📚 عدد الكتب: {len(books)}\n\nاختر كتاباً:"

#         keyboard = get_books_list_keyboard(books) if books else None

#         await callback.message.edit_text(text, reply_markup=keyboard)
#     finally:
#         db.close()

@router.callback_query(F.data.startswith("cat_"))
async def callback_category(callback: CallbackQuery):
    """عرض مؤلفي القسم بدلاً من الكتب مباشرة"""
    category_id = int(callback.data.split("_")[1])
    
    db = SessionLocal()
    try:
        category_service = CategoryService(db)
        author_service = AuthorService(db)
        
        category = category_service.get_by_id(category_id)
        if not category:
            await callback.answer("القسم غير موجود", show_alert=True)
            return
        
        # جلب المؤلفين الذين لديهم كتب في هذا القسم
        authors = author_service.get_authors_by_category(category_id)
        
        if not authors:
            await callback.message.edit_text(
                f"📁 {category.name}\n\nلا يوجد مؤلفون في هذا القسم حالياً.",
                reply_markup=get_back_keyboard()
            )
            return
        
        # بناء لوحة مفاتيح للمؤلفين
        from aiogram.utils.keyboard import InlineKeyboardBuilder
        builder = InlineKeyboardBuilder()
        for author in authors:
            builder.add(InlineKeyboardButton(
                text=f"✍️ {author.name}",
                callback_data=f"author_cat_{category_id}_{author.id}"
            ))
        builder.adjust(2)
        builder.row(InlineKeyboardButton(text="🔙 رجوع", callback_data="main_menu"))
        
        await callback.message.edit_text(
            f"📁 {category.name}\n\nاختر المؤلف لعرض كتبه:",
            reply_markup=builder.as_markup()
        )
    finally:
        db.close()

@router.callback_query(F.data.startswith("author_cat_"))
async def callback_author_books(callback: CallbackQuery):
    """عرض كتب المؤلف في قسم معين مع التصفح"""
    parts = callback.data.split("_")
    if len(parts) < 4:
        await callback.answer("بيانات غير صحيحة", show_alert=True)
        return
    
    category_id = int(parts[2])
    author_id = int(parts[3])
    page = int(parts[4]) if len(parts) > 4 else 1
    
    db = SessionLocal()
    try:
        book_service = BookService(db)
        category_service = CategoryService(db)
        author_service = AuthorService(db)
        
        category = category_service.get_by_id(category_id)
        author = author_service.get_by_id(author_id)
        if not category or not author:
            await callback.answer("البيانات غير موجودة", show_alert=True)
            return
        
        # جلب العدد الإجمالي للكتب
        from app.models.book import Book
        total_books = db.query(Book).filter(
            Book.category_id == category_id,
            Book.author_id == author_id,
            Book.status == BookStatus.ACTIVE
        ).count()
        
        # جلب الكتب مع التصفح
        limit = 10
        offset = (page - 1) * limit
        books = book_service.get_books_by_category_and_author(category_id, author_id, limit=limit, offset=offset)
        
        # fallback: بعض الكتب قد تكون مرتبطة بالمؤلف فقط دون القسم بشكل صحيح
        if not books:
            books = book_service.get_books_by_author(author_id, limit=limit, offset=offset)
            total_books = len(books) if page == 1 else max(total_books, len(books))
        
        if not books and page == 1:
            await callback.message.edit_text(
                f"📚 لا توجد كتب للمؤلف {author.name} في قسم {category.name}",
                reply_markup=get_back_keyboard()
            )
            return
        
        text = f"📁 {category.name} > 👤 {author.name}\n\n📚 الكتب المتاحة (صفحة {page}/{ (total_books + limit - 1) // limit }):"
        
        keyboard = get_books_list_keyboard_paginated(books, page, total_books, limit, f"author_cat_{category_id}_{author_id}")
        
        await callback.message.edit_text(text, reply_markup=keyboard)
    except Exception as e:
        logging.error(f"Error in callback_author_books: {e}")
        await callback.answer("حدث خطأ، حاول مرة أخرى", show_alert=True)
    finally:
        db.close()
@router.callback_query(F.data.startswith("book_"))
async def callback_book(callback: CallbackQuery):
    """عرض تفاصيل الكتاب"""
    book_id = int(callback.data.split("_")[1])

    db = SessionLocal()
    try:
        book_service = BookService(db)
        user_service = UserService(db)

        book = book_service.get_book(book_id)
        if not book:
            await callback.answer("الكتاب غير موجود", show_alert=True)
            return

        user = user_service.get_user_by_telegram_id(callback.from_user.id)
        is_favorite = False
        if user:
            from app.models.favorite import Favorite
            fav = db.query(Favorite).filter(
                Favorite.user_id == user.id,
                Favorite.book_id == book_id
            ).first()
            is_favorite = fav is not None

        book_info = format_book_info(book)
        keyboard = get_book_keyboard(book_id, is_favorite)

        await callback.message.edit_text(book_info, reply_markup=keyboard)
    except Exception as e:
        logging.error(f"Error in callback_book: {e}")
        await callback.answer("حدث خطأ في عرض الكتاب", show_alert=True)
    finally:
        db.close()


@router.callback_query(F.data.startswith("fav_"))
async def callback_favorite(callback: CallbackQuery):
    """إضافة/إزالة من المفضلة"""
    book_id = int(callback.data.split("_")[1])

    db = SessionLocal()
    try:
        user_service = UserService(db)
        from app.models.favorite import Favorite

        user = user_service.get_or_create_user(
            callback.from_user.id,
            callback.from_user.username,
            callback.from_user.first_name,
            callback.from_user.last_name
        )

        # البحث عن المفضلة
        fav = db.query(Favorite).filter(
            Favorite.user_id == user.id,
            Favorite.book_id == book_id
        ).first()

        if fav:
            # إزالة من المفضلة
            db.delete(fav)
            db.commit()
            await callback.answer("❌Removed from favorites")
        else:
            # إضافة للمفضلة
            new_fav = Favorite(user_id=user.id, book_id=book_id)
            db.add(new_fav)
            db.commit()
            await callback.answer("✅Added to favorites")

        # تحديث عرض الكتاب
        book_service = BookService(db)
        book = book_service.get_book(book_id)

        if book:
            book_info = format_book_info(book)
            keyboard = get_book_keyboard(book_id, fav is None)
            await callback.message.edit_text(book_info, reply_markup=keyboard)

    finally:
        db.close()


@router.callback_query(F.data.startswith("rate_"))
async def callback_rating(callback: CallbackQuery):
    """تقييم الكتاب"""
    parts = callback.data.split("_")

    if len(parts) == 2:
        # طلب التقييم
        book_id = int(parts[1])
        keyboard = get_rating_keyboard(book_id)
        await callback.message.edit_text(
            "⭐ اختر تقييمك للكتاب:",
            reply_markup=keyboard
        )
    else:
        # حفظ التقييم
        rating = int(parts[1])
        book_id = int(parts[2])

        db = SessionLocal()
        try:
            book_service = BookService(db)
            points_service = PointsService(db)
            user_service = UserService(db)

            book = book_service.get_book(book_id)
            if book:
                book_service.add_rating(book_id, float(rating))

                # إضافة نقاط للتقييم
                user = user_service.get_or_create_user(
                    callback.from_user.id,
                    callback.from_user.username,
                    callback.from_user.first_name,
                    callback.from_user.last_name
                )
                points_service.add_review_points(user.id, book_id)

                await callback.answer(f"⭐ شكراً لك! تم تسجيل تقييم {rating}")

                # العودة لعرض الكتاب
                book_info = format_book_info(book)
                keyboard = get_book_keyboard(book_id, False)
                await callback.message.edit_text(book_info, reply_markup=keyboard)
        finally:
            db.close()


@router.callback_query(F.data.startswith("download_"))
async def callback_download(callback: CallbackQuery):
    """تحميل الكتاب"""
    book_id = int(callback.data.split("_")[1])

    db = SessionLocal()
    try:
        book_service = BookService(db)
        user_service = UserService(db)
        points_service = PointsService(db)

        book = book_service.get_book(book_id)
        if not book:
            await callback.answer("الكتاب غير موجود", show_alert=True)
            return

        resolved_path = resolve_book_file_path(book.file_path)
        if not resolved_path:
            await callback.answer("الكتاب غير متاح للتحميل حالياً", show_alert=True)
            return

        user = user_service.get_or_create_user(
            callback.from_user.id,
            callback.from_user.username,
            callback.from_user.first_name,
            callback.from_user.last_name
        )

        # التحقق من النقاط
        can_download, msg = points_service.can_download(user.id)
        if not can_download:
            await callback.answer(msg, show_alert=True)
            return

        # خصم النقاط
        from config.settings import get_settings
        s = get_settings()
        points_service.deduct_points(user.id, s.points_to_deduct, f"تحميل كتاب {book.title}")

        # إضافة نقاط التحميل
        points_service.add_download_points(user.id, book_id)

        # تحديث إحصائيات الكتاب
        book_service.increment_download(book_id)
        user_service.increment_downloads(callback.from_user.id)

        # إرسال الملف
        with open(resolved_path, 'rb') as file:
            await callback.message.answer_document(
                document=file,
                caption=f"📥 {book.title}"
            )

        await callback.answer("✅ تم تحميل الكتاب بنجاح!")

        # تسجيل التحميل
        from app.models.download_history import DownloadHistory
        download = DownloadHistory(user_id=user.id, book_id=book_id)
        db.add(download)
        db.commit()

    finally:
        db.close()


# ==========================================
# Admin Callback Handlers - معالجات الإدارة
# ==========================================

@router.callback_query(F.data == "admin_pending_books")
async def callback_admin_pending_books(callback: CallbackQuery):
    """كتب قيد المراجعة"""
    if not is_owner(callback.from_user.id):
        await callback.answer("غير مصرح لك", show_alert=True)
        return

    db = SessionLocal()
    try:
        book_service = BookService(db)
        books = book_service.get_pending_books(limit=20)

        if not books:
            await callback.message.edit_text(
                "✅ لا توجد كتب قيد المراجعة",
                reply_markup=get_back_to_admin_keyboard()
            )
            return

        text = "📚 كتب قيد المراجعة:\n\n"
        for book in books:
            text += f"📖 {truncate_text(book.title, 35)}\n   ID: {book.id}\n\n"

        keyboard = InlineKeyboardMarkup(inline_keyboard=[])
        for book in books[:10]:
            keyboard.inline_keyboard.append([
                InlineKeyboardButton(
                    text=f"📖 {truncate_text(book.title, 20)}",
                    callback_data=f"admin_book_review_{book.id}"
                )
            ])
        keyboard.inline_keyboard.append([
            InlineKeyboardButton(text="🔙 رجوع", callback_data="admin_menu")
        ])

        await callback.message.edit_text(text, reply_markup=keyboard)
    finally:
        db.close()


@router.callback_query(F.data.startswith("admin_book_review_"))
async def callback_admin_book_review(callback: CallbackQuery):
    """مراجعة كتاب"""
    if not is_owner(callback.from_user.id):
        await callback.answer("غير مصرح لك", show_alert=True)
        return

    book_id = int(callback.data.split("_")[-1])

    db = SessionLocal()
    try:
        book_service = BookService(db)
        book = book_service.get_book(book_id)

        if not book:
            await callback.answer("الكتاب غير موجود", show_alert=True)
            return

        text = f"📖 {book.title}\n\n"
        if book.author:
            text += f"✍️ المؤلف: {book.author.name}\n"
        if book.description:
            text += f"📝 الوصف: {truncate_text(book.description, 200)}\n"
        text += f"📅 التاريخ: {book.created_at.strftime('%Y-%m-%d')}"

        keyboard = get_admin_book_actions_keyboard(book_id)
        await callback.message.edit_text(text, reply_markup=keyboard)
    finally:
        db.close()


@router.callback_query(F.data.startswith("admin_book_approve_"))
async def callback_admin_book_approve(callback: CallbackQuery):
    """الموافقة على كتاب"""
    if not is_owner(callback.from_user.id):
        await callback.answer("غير مصرح لك", show_alert=True)
        return

    book_id = int(callback.data.split("_")[-1])

    db = SessionLocal()
    try:
        book_service = BookService(db)
        book_service.approve_book(book_id)
        await callback.answer("✅ تم الموافقة على الكتاب", show_alert=True)
        await callback.message.edit_text(
            "✅ تم الموافقة على الكتاب بنجاح",
            reply_markup=get_back_to_admin_keyboard()
        )
    finally:
        db.close()


@router.callback_query(F.data.startswith("admin_book_reject_"))
async def callback_admin_book_reject(callback: CallbackQuery):
    """رفض كتاب"""
    if not is_owner(callback.from_user.id):
        await callback.answer("غير مصرح لك", show_alert=True)
        return

    book_id = int(callback.data.split("_")[-1])
    # TODO: طلب سبب الرفض من المستخدم

    db = SessionLocal()
    try:
        book_service = BookService(db)
        book_service.reject_book(book_id, "لم يتوافق مع معايير المكتبة")
        await callback.answer("❌ تم رفض الكتاب", show_alert=True)
        await callback.message.edit_text(
            "❌ تم رفض الكتاب",
            reply_markup=get_back_to_admin_keyboard()
        )
    finally:
        db.close()


@router.callback_query(F.data == "admin_delete_book")
async def callback_admin_delete_book_start(callback: CallbackQuery, state: FSMContext):
    if not is_owner(callback.from_user.id):
        return
    await callback.message.edit_text("🗑️ أرسل ID الكتاب الذي تريد حذفه:")
    await state.set_state(AdminStates.waiting_book_title) # استخدام حالة موجودة مؤقتاً أو إضافة حالة جديدة

@router.callback_query(F.data.startswith("admin_book_delete_"))
async def callback_admin_book_delete(callback: CallbackQuery):
    """حذف كتاب"""
    if not is_owner(callback.from_user.id):
        await callback.answer("غير مصرح لك", show_alert=True)
        return

    book_id = int(callback.data.split("_")[-1])

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ نعم", callback_data=f"confirm_delete_book_{book_id}")],
        [InlineKeyboardButton(text="❌ لا", callback_data="admin_menu")]
    ])

    await callback.message.edit_text(
        "⚠️ هل أنت متأكد من حذف هذا الكتاب؟",
        reply_markup=keyboard
    )


@router.callback_query(F.data.startswith("confirm_delete_book_"))
async def callback_confirm_delete_book(callback: CallbackQuery):
    """تأكيد حذف كتاب"""
    if not is_owner(callback.from_user.id):
        await callback.answer("غير مصرح لك", show_alert=True)
        return

    book_id = int(callback.data.split("_")[-1])

    db = SessionLocal()
    try:
        book_service = BookService(db)
        book_service.delete_book(book_id)
        await callback.answer("🗑️ تم حذف الكتاب", show_alert=True)
        await callback.message.edit_text(
            "🗑️ تم حذف الكتاب بنجاح",
            reply_markup=get_back_to_admin_keyboard()
        )
    finally:
        db.close()
# ==========================================
# رفع كتاب جديد (Admin Upload Book)
# ==========================================

@router.callback_query(F.data == "admin_upload_book")
async def callback_admin_upload_book(callback: CallbackQuery, state: FSMContext):
    if not is_owner(callback.from_user.id):
        await callback.answer("غير مصرح لك", show_alert=True)
        return

    db = SessionLocal()
    try:
        category_service = CategoryService(db)
        categories = category_service.list_all(active_only=False)
        if not categories:
            await callback.message.edit_text("📭 لا توجد أقسام. أضف قسماً أولاً.", reply_markup=get_admin_books_keyboard())
            return

        from aiogram.utils.keyboard import InlineKeyboardBuilder
        builder = InlineKeyboardBuilder()
        for cat in categories:
            builder.add(InlineKeyboardButton(
                text=cat.name,
                callback_data=f"upload_cat_{cat.id}"
            ))
        builder.row(InlineKeyboardButton(text="🔙 إلغاء", callback_data="admin_books"))
        await callback.message.edit_text("📁 اختر القسم الذي سينتمي إليه الكتاب:", reply_markup=builder.as_markup())
        await state.set_state(AdminStates.waiting_book_category)
    finally:
        db.close()
@router.callback_query(AdminStates.waiting_book_category, F.data.startswith("upload_cat_"))
async def process_book_category_choice(callback: CallbackQuery, state: FSMContext):
    if not is_owner(callback.from_user.id):
        return
    category_id = int(callback.data.split("_")[-1])
    await state.update_data(book_category_id=category_id)

    # الآن نعرض المؤلفين المرتبطين بهذا القسم (أو كل المؤلفين إذا لم يوجد)
    db = SessionLocal()
    try:
        author_service = AuthorService(db)
        authors = author_service.get_authors_by_category(category_id)  # المؤلفون المرتبطون مباشرة
        if not authors:
            # إذا لم يوجد مؤلفين، نعطي خيار إدخال اسم مؤلف جديد مع رسالة
            await callback.message.edit_text(
                "✍️ لا يوجد مؤلفين في هذا القسم. أرسل اسم المؤلف الجديد:",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="🔙 إلغاء", callback_data="admin_books")]
                ])
            )
            # نستخدم حالة waiting_book_author (الموجودة) لقبول اسم المؤلف
            await state.set_state(AdminStates.waiting_book_author)
        else:
            from aiogram.utils.keyboard import InlineKeyboardBuilder
            builder = InlineKeyboardBuilder()
            for author in authors:
                builder.add(InlineKeyboardButton(
                    text=author.name,
                    callback_data=f"upload_author_{author.id}"
                ))
            builder.row(InlineKeyboardButton(text="✍️ إضافة مؤلف جديد", callback_data="upload_new_author"))
            builder.row(InlineKeyboardButton(text="🔙 إلغاء", callback_data="admin_books"))
            await callback.message.edit_text("✍️ اختر المؤلف:", reply_markup=builder.as_markup())
            await state.set_state(AdminStates.waiting_book_author_select)
    finally:
        db.close()
        
@router.message(AdminStates.waiting_book_title)
async def process_book_title(message: Message, state: FSMContext):
    if not is_owner(message.from_user.id):
        return
    await state.update_data(title=message.text.strip())
    await message.answer("✍️ أرسل اسم المؤلف (يمكنك كتابة اسم جديد أو اختيار من القائمة لاحقاً):")
    await state.set_state(AdminStates.waiting_book_author)

@router.message(AdminStates.waiting_book_author)
async def process_book_author(message: Message, state: FSMContext):
    if not is_owner(message.from_user.id):
        return
    await state.update_data(author=message.text.strip())
    await message.answer("📝 أرسل وصف الكتاب (اختياري، يمكنك كتابة /skip للتخطي):")
    await state.set_state(AdminStates.waiting_book_description)

@router.message(AdminStates.waiting_book_description)
async def process_book_description(message: Message, state: FSMContext):
    if not is_owner(message.from_user.id):
        return
    desc = message.text.strip()
    if desc == "/skip":
        desc = None
    await state.update_data(description=desc)
    await message.answer("📂 أرسل ملف الكتاب (PDF أو EPUB):")
    await state.set_state(AdminStates.waiting_book_file)

@router.message(AdminStates.waiting_book_file, F.document)
async def process_book_file(message: Message, state: FSMContext, bot: Bot):
    if not is_owner(message.from_user.id):
        return
    data = await state.get_data()
    title = data.get("title")
    author_name = data.get("author")
    description = data.get("description")
    category_id = data.get("book_category_id")
    doc = message.document
    
    # التحقق من نوع الملف
    allowed_extensions = ['.pdf', '.epub', '.fb2', '.mobi', '.txt']
    file_name = doc.file_name.lower()
    if not any(file_name.endswith(ext) for ext in allowed_extensions):
        await message.answer("⚠️ نوع الملف غير مدعوم. يرجى إرسال ملف PDF أو EPUB أو FB2 أو MOBI أو TXT فقط.")
        return
    
    # التحقق من حجم الملف
    max_size = 100 * 1024 * 1024  # 100MB
    if doc.file_size and doc.file_size > max_size:
        await message.answer(f"⚠️ حجم الملف كبير جداً. الحد الأقصى هو {max_size // (1024*1024)}MB.")
        return
    
    # تأكد من وجود مجلد uploads
    os.makedirs(settings.upload_folder, exist_ok=True)
    file_path = os.path.abspath(os.path.join(settings.upload_folder, f"{doc.file_id}_{doc.file_name}"))
    
    try:
        await bot.download(doc, destination=file_path)
    except Exception as e:
        logging.error(f"Error downloading file: {e}")
        await message.answer("⚠️ فشل في تحميل الملف. حاول مرة أخرى.")
        return
    
    db = SessionLocal()
    try:
        # التعامل مع المؤلف
        author_service = AuthorService(db)
        author = author_service.get_by_name(author_name)
        if not author:
            author = author_service.create(name=author_name)
        book_service = BookService(db)
        book = book_service.create_book(
            title=title,
            author_id=author.id,
            description=description,
            file_path=file_path,
            category_id=category_id,
            status=BookStatus.ACTIVE,
        )
        await message.answer(f"✅ تم رفع الكتاب '{book.title}' بنجاح وأصبح متاحاً للمراجعة والظهور.")
    except Exception as e:
        logging.error(f"Error saving book: {e}")
        await message.answer(f"⚠️ حدث خطأ أثناء حفظ الكتاب: {e}")
        # حذف الملف إذا فشل الحفظ
        if os.path.exists(file_path):
            os.remove(file_path)
    finally:
        db.close()
        await state.clear()
    # العودة إلى لوحة إدارة الكتب
    await message.answer("📚 تم تسجيل الكتاب بنجاح.", reply_markup=get_admin_books_keyboard())

# ==========================================
# Admin Category Management - إدارة الأقسام (كود متكامل)
# ==========================================

@router.callback_query(F.data == "admin_categories")
async def callback_admin_categories(callback: CallbackQuery):
    """لوحة إدارة الأقسام الرئيسية"""
    if not is_owner(callback.from_user.id):
        await callback.answer("غير مصرح لك", show_alert=True)
        return
    text = "📁 إدارة الأقسام"
    keyboard = get_admin_categories_keyboard()
    await callback.message.edit_text(text, reply_markup=keyboard)


@router.callback_query(F.data == "admin_cat_list")
async def callback_admin_cat_list(callback: CallbackQuery):
    """عرض جميع الأقسام مع أزرار تعديل/حذف لكل قسم"""
    if not is_owner(callback.from_user.id):
        await callback.answer("غير مصرح لك", show_alert=True)
        return

    db = SessionLocal()
    try:
        category_service = CategoryService(db)
        categories = category_service.list_all(active_only=False)

        if not categories:
            await callback.message.edit_text(
                "📭 لا توجد أقسام حالياً.",
                reply_markup=get_back_to_admin_keyboard()
            )
            return

        from aiogram.utils.keyboard import InlineKeyboardBuilder
        builder = InlineKeyboardBuilder()
        for cat in categories:
            status_icon = "✅" if cat.is_active else "❌"
            builder.row(
                InlineKeyboardButton(
                    text=f"{status_icon} {cat.name} (ID: {cat.id})",
                    callback_data="ignore"
                ),
                InlineKeyboardButton(
                    text="✏️ تعديل",
                    callback_data=f"admin_cat_edit_{cat.id}"
                ),
                InlineKeyboardButton(
                    text="🗑️ حذف",
                    callback_data=f"admin_cat_delete_{cat.id}"
                )
            )
        builder.row(InlineKeyboardButton(text="🔙 رجوع", callback_data="admin_categories"))
        await callback.message.edit_text(
            "📁 قائمة الأقسام:\nاختر القسم ثم اضغط تعديل أو حذف.",
            reply_markup=builder.as_markup()
        )
    finally:
        db.close()


@router.callback_query(F.data == "admin_add_category")
async def callback_admin_add_category(callback: CallbackQuery, state: FSMContext):
    """طلب إضافة قسم جديد"""
    if not is_owner(callback.from_user.id):
        await callback.answer("غير مصرح لك", show_alert=True)
        return
    await callback.message.edit_text("📝 أرسل اسم القسم الجديد (بالعربية أو الإنجليزية):")
    await state.set_state(AdminStates.waiting_category_name)


@router.message(AdminStates.waiting_category_name)
async def process_new_category(message: Message, state: FSMContext):
    """حفظ القسم الجديد في قاعدة البيانات"""
    if not is_owner(message.from_user.id):
        await message.answer("غير مصرح لك")
        return

    name = message.text.strip()
    if not name:
        await message.answer("⚠️ الاسم لا يمكن أن يكون فارغاً. أرسل الاسم مرة أخرى:")
        return

    db = SessionLocal()
    try:
        category_service = CategoryService(db)
        existing = category_service.get_by_name(name)
        if existing:
            await message.answer(f"❌ القسم '{name}' موجود مسبقاً.")
            return

        new_cat = category_service.create(name=name)
        await message.answer(f"✅ تم إضافة القسم '{new_cat.name}' بنجاح.")
        await message.answer("📁 ارجع إلى إدارة الأقسام من القائمة.", reply_markup=get_admin_categories_keyboard())
    except Exception as e:
        await message.answer(f"⚠️ حدث خطأ أثناء الإضافة: {e}")
    finally:
        db.close()
        await state.clear()


@router.callback_query(F.data.startswith("admin_cat_edit_"))
async def callback_admin_cat_edit(callback: CallbackQuery, state: FSMContext):
    """بدء عملية تعديل قسم (طلب الاسم الجديد)"""
    if not is_owner(callback.from_user.id):
        await callback.answer("غير مصرح لك", show_alert=True)
        return

    category_id = int(callback.data.split("_")[-1])
    await state.update_data(category_id=category_id)
    await callback.message.edit_text("✏️ أرسل الاسم الجديد للقسم:")
    await state.set_state(AdminStates.waiting_category_edit)


@router.message(AdminStates.waiting_category_edit)
async def process_edit_category(message: Message, state: FSMContext):
    """تحديث القسم بالاسم الجديد"""
    if not is_owner(message.from_user.id):
        return

    data = await state.get_data()
    category_id = data.get("category_id")
    new_name = message.text.strip()

    if not new_name:
        await message.answer("⚠️ الاسم لا يمكن أن يكون فارغاً.")
        return

    db = SessionLocal()
    try:
        category_service = CategoryService(db)
        updated_cat = category_service.update(category_id, name=new_name)
        if updated_cat:
            await message.answer(f"✅ تم تحديث القسم إلى '{updated_cat.name}'.")
        else:
            await message.answer("❌ القسم غير موجود.")
        await message.answer("📁 ارجع إلى إدارة الأقسام.", reply_markup=get_admin_categories_keyboard())
    except Exception as e:
        await message.answer(f"⚠️ حدث خطأ أثناء التحديث: {e}")
    finally:
        db.close()
        await state.clear()


@router.callback_query(F.data.startswith("admin_cat_delete_"))
async def callback_admin_cat_delete(callback: CallbackQuery):
    """حذف قسم نهائياً"""
    if not is_owner(callback.from_user.id):
        await callback.answer("غير مصرح لك", show_alert=True)
        return

    category_id = int(callback.data.split("_")[-1])
    db = SessionLocal()
    try:
        category_service = CategoryService(db)
        success = category_service.delete(category_id)
        if success:
            await callback.answer("🗑️ تم حذف القسم بنجاح", show_alert=True)
            # تحديث القائمة
            await callback_admin_cat_list(callback)
        else:
            await callback.answer("❌ لم يتم الحذف (ربما القسم غير موجود)", show_alert=True)
    except Exception as e:
        await callback.answer(f"⚠️ خطأ أثناء الحذف: {e}", show_alert=True)
    finally:
        db.close()

@router.message(Command("exportcsv"))
async def cmd_export_csv(message: Message):
    if not is_owner(message.from_user.id):
        await message.answer("غير مصرح لك بهذا الأمر.")
        return
    db = SessionLocal()
    try:
        book_service = BookService(db)
        books = book_service.get_all_books(status=BookStatus.ACTIVE)
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(['ID', 'العنوان', 'المؤلف', 'القسم', 'التحميلات', 'التقييم'])
        for book in books:
            writer.writerow([
                book.id,
                book.title,
                book.author.name if book.author else '',
                book.category.name if book.category else '',
                book.download_count,
                book.average_rating
            ])
        output.seek(0)
        bytes_io = io.BytesIO(output.getvalue().encode('utf-8'))
        from aiogram.types import BufferedInputFile
        file = BufferedInputFile(bytes_io.getvalue(), filename='books_export.csv')
        await message.answer_document(document=file, caption="📤 تم تصدير البيانات")
    except Exception as e:
        await message.answer(f"⚠️ خطأ أثناء التصدير: {e}")
    finally:
        db.close()
        
@router.callback_query(F.data == "admin_menu")
async def callback_admin_menu(callback: CallbackQuery):
    """العودة للوحة تحكم المالك"""
    if not is_owner(callback.from_user.id):
        await callback.answer("غير مصرح لك", show_alert=True)
        return
    text = "👑 لوحة تحكم المالك\n\nاختر من الخيارات التالية:"
    keyboard = get_admin_keyboard_enhanced()
    await callback.message.edit_text(text, reply_markup=keyboard)

@router.callback_query(F.data == "admin_books")
async def callback_admin_books(callback: CallbackQuery):
    """إدارة الكتب"""
    if not is_owner(callback.from_user.id):
        await callback.answer("غير مصرح لك", show_alert=True)
        return
    text = "📚 إدارة الكتب"
    keyboard = get_admin_books_keyboard()
    await callback.message.edit_text(text, reply_markup=keyboard)

@router.callback_query(F.data == "admin_book_list")
async def callback_admin_book_list(callback: CallbackQuery):
    if not is_owner(callback.from_user.id):
        return
    db = SessionLocal()
    try:
        book_service = BookService(db)
        books = book_service.get_all_books(limit=10)
        if not books:
            await callback.message.edit_text("📭 لا توجد كتب حالياً.", reply_markup=get_admin_books_keyboard())
            return
        text = "📚 قائمة الكتب (آخر 10):\n\n"
        for b in books:
            text += f"• {b.title} (ID: {b.id})\n"
        await callback.message.edit_text(text, reply_markup=get_admin_books_keyboard())
    finally:
        db.close()

@router.callback_query(F.data == "admin_pending_books")
async def callback_admin_pending_books(callback: CallbackQuery):
    if not is_owner(callback.from_user.id):
        return
    db = SessionLocal()
    try:
        book_service = BookService(db)
        books = book_service.get_all_books(status=BookStatus.PENDING)
        if not books:
            await callback.message.edit_text("📭 لا توجد كتب قيد المراجعة.", reply_markup=get_admin_books_keyboard())
            return
        text = "⏳ كتب قيد المراجعة:\n\n"
        for b in books:
            text += f"• {b.title} (ID: {b.id})\n"
        await callback.message.edit_text(text, reply_markup=get_admin_books_keyboard())
    finally:
        db.close()

@router.callback_query(F.data == "admin_authors")
async def callback_admin_authors(callback: CallbackQuery):
    """إدارة المؤلفين"""
    if not is_owner(callback.from_user.id):
        await callback.answer("غير مصرح لك", show_alert=True)
        return
    text = "✍️ إدارة المؤلفين"
    keyboard = get_admin_authors_keyboard()
    await callback.message.edit_text(text, reply_markup=keyboard)

@router.callback_query(F.data == "admin_auth_list")
async def callback_admin_auth_list(callback: CallbackQuery):
    """عرض المؤلفين مع خيارات التعديل والحذف"""
    if not is_owner(callback.from_user.id):
        await callback.answer("غير مصرح لك", show_alert=True)
        return
    db = SessionLocal()
    try:
        author_service = AuthorService(db)
        authors = author_service.list_all()
        if not authors:
            await callback.message.edit_text("📭 لا يوجد مؤلفون حالياً.", reply_markup=get_admin_authors_keyboard())
            return
        from aiogram.utils.keyboard import InlineKeyboardBuilder
        builder = InlineKeyboardBuilder()
        for auth in authors:
            builder.row(
                InlineKeyboardButton(text=auth.name, callback_data="ignore"),
                InlineKeyboardButton(text="✏️", callback_data=f"admin_auth_edit_{auth.id}"),
                InlineKeyboardButton(text="🗑️", callback_data=f"admin_auth_delete_{auth.id}")
            )
        builder.row(InlineKeyboardButton(text="🔙 رجوع", callback_data="admin_authors"))
        await callback.message.edit_text("✍️ قائمة المؤلفين:", reply_markup=builder.as_markup())
    finally:
        db.close()

@router.callback_query(F.data == "admin_add_author")
async def callback_admin_add_author(callback: CallbackQuery, state: FSMContext):
    if not is_owner(callback.from_user.id):
        return
    db = SessionLocal()
    try:
        category_service = CategoryService(db)
        categories = category_service.list_all(active_only=False)
        if not categories:
            await callback.message.edit_text(
                "📭 لا توجد أقسام. أضف قسماً أولاً.",
                reply_markup=get_admin_authors_keyboard()
            )
            return
        from aiogram.utils.keyboard import InlineKeyboardBuilder
        builder = InlineKeyboardBuilder()
        for cat in categories:
            builder.add(InlineKeyboardButton(
                text=cat.name,
                callback_data=f"admin_author_cat_{cat.id}"
            ))
        builder.row(InlineKeyboardButton(
            text="🔙 إلغاء",
            callback_data="admin_authors"
        ))
        await callback.message.edit_text(
            "اختر القسم الذي سينتمي إليه المؤلف:",
            reply_markup=builder.as_markup()
        )
        await state.set_state(AdminStates.waiting_author_category)
    finally:
        db.close()
@router.callback_query(AdminStates.waiting_author_category, F.data.startswith("admin_author_cat_"))
async def process_author_category_choice(callback: CallbackQuery, state: FSMContext):
    if not is_owner(callback.from_user.id):
        return
    category_id = int(callback.data.split("_")[-1])
    await state.update_data(author_category_id=category_id)
    await callback.message.edit_text("✍️ أرسل اسم المؤلف الجديد:")
    await state.set_state(AdminStates.waiting_author_name)
    
@router.message(AdminStates.waiting_author_name)
async def process_add_author(message: Message, state: FSMContext):
    if not is_owner(message.from_user.id):
        return
    data = await state.get_data()
    category_id = data.get("author_category_id")   # هذا السطر الجديد
    name = message.text.strip()

    db = SessionLocal()
    try:
        author_service = AuthorService(db)
        author_service.create(name=name, category_id=category_id)  # تمرير القسم
        await message.answer(
            f"✅ تم إضافة المؤلف '{name}' وربطه بالقسم بنجاح.",
            reply_markup=get_admin_authors_keyboard()
        )
    except Exception as e:
        logging.error(f"Error adding author: {e}")
        await message.answer("⚠️ فشل في إضافة المؤلف.")
    finally:
        db.close()
        await state.clear()

@router.callback_query(F.data.startswith("admin_auth_delete_"))
async def callback_admin_delete_author(callback: CallbackQuery):
    if not is_owner(callback.from_user.id):
        return
    author_id = int(callback.data.split("_")[-1])
    db = SessionLocal()
    try:
        author_service = AuthorService(db)
        author_service.delete(author_id)
        await callback.answer("🗑️ تم حذف المؤلف")
        await callback_admin_auth_list(callback)
    finally:
        db.close()

@router.callback_query(F.data == "admin_channels")
async def callback_admin_channels(callback: CallbackQuery):
    """إدارة القنوات"""
    if not is_owner(callback.from_user.id):
        await callback.answer("غير مصرح لك", show_alert=True)
        return
    text = "📡 إدارة قنوات الاشتراك الإجباري"
    keyboard = get_admin_channels_keyboard()
    await callback.message.edit_text(text, reply_markup=keyboard)

@router.callback_query(F.data == "admin_ch_list")
async def callback_admin_ch_list(callback: CallbackQuery):
    """عرض القنوات مع خيار الحذف"""
    if not is_owner(callback.from_user.id):
        await callback.answer("غير مصرح لك", show_alert=True)
        return
    db = SessionLocal()
    try:
        channel_service = ChannelService(db)
        channels = channel_service.get_all_channels()
        if not channels:
            await callback.message.edit_text("📭 لا توجد قنوات حالياً.", reply_markup=get_admin_channels_keyboard())
            return
        from aiogram.utils.keyboard import InlineKeyboardBuilder
        builder = InlineKeyboardBuilder()
        for ch in channels:
            builder.row(
                InlineKeyboardButton(text=ch.channel_name or ch.channel_id, callback_data="ignore"),
                InlineKeyboardButton(text="🗑️", callback_data=f"admin_ch_delete_{ch.channel_id}")
            )
        builder.row(InlineKeyboardButton(text="🔙 رجوع", callback_data="admin_channels"))
        await callback.message.edit_text("📡 قائمة القنوات:", reply_markup=builder.as_markup())
    finally:
        db.close()

@router.callback_query(F.data == "admin_add_channel")
async def callback_admin_add_channel(callback: CallbackQuery, state: FSMContext):
    if not is_owner(callback.from_user.id):
        return
    await callback.message.edit_text("📡 أرسل معرف القناة (مثال: @channel_id أو ID الرقمي):")
    await state.set_state(AdminStates.waiting_channel_id)

@router.message(AdminStates.waiting_channel_id)
async def process_add_channel_id(message: Message, state: FSMContext):
    if not is_owner(message.from_user.id):
        return
    channel_id = message.text.strip()
    await state.update_data(channel_id=channel_id)
    await message.answer("🔗 أرسل رابط القناة:")
    await state.set_state(AdminStates.waiting_channel_link)

@router.message(AdminStates.waiting_channel_link)
async def process_add_channel_link(message: Message, state: FSMContext, bot: Bot):
    if not is_owner(message.from_user.id):
        return
    link = message.text.strip()
    data = await state.get_data()
    channel_id = data.get("channel_id")

    # التحقق من صحة القناة
    try:
        chat = await bot.get_chat(channel_id)
        if chat.type not in ['channel', 'supergroup']:
            await message.answer("⚠️ المعرف لا يشير إلى قناة صالحة (يجب أن تكون قناة أو مجموعة سوبر).")
            return
    except Exception as e:
        await message.answer(f"⚠️ لا يمكن الوصول إلى القناة. تأكد من أن البوت مشرف في القناة أو أن المعرف صحيح.\nالخطأ: {e}")
        return

    db = SessionLocal()
    try:
        channel_service = ChannelService(db)
        channel_service.add_channel(channel_id=channel_id, channel_link=link)
        await message.answer(f"✅ تم إضافة القناة {channel_id} بنجاح.", reply_markup=get_admin_channels_keyboard())
    finally:
        db.close()
        await state.clear()

@router.callback_query(F.data.startswith("admin_ch_delete_"))
async def callback_admin_delete_channel(callback: CallbackQuery):
    if not is_owner(callback.from_user.id):
        return
    channel_id = callback.data.replace("admin_ch_delete_", "")
    db = SessionLocal()
    try:
        channel_service = ChannelService(db)
        channel_service.remove_channel(channel_id)
        await callback.answer("🗑️ تم حذف القناة")
        await callback_admin_ch_list(callback)
    finally:
        db.close()

@router.callback_query(F.data == "admin_ch_settings")
async def callback_admin_ch_settings(callback: CallbackQuery):
    if not is_owner(callback.from_user.id):
        return
    await callback.message.edit_text("⚙️ إعدادات النشر\n\n(قيد التطوير)", reply_markup=get_admin_channels_keyboard())

@router.callback_query(F.data == "admin_users_list")
async def callback_admin_users_list(callback: CallbackQuery):
    if not is_owner(callback.from_user.id):
        await callback.answer("غير مصرح لك", show_alert=True)
        return

    db = SessionLocal()
    try:
        channel_service = ChannelService(db)
        channels = channel_service.get_all_channels()

        if not channels:
            await callback.message.edit_text(
                "لا توجد قنوات اشتراك إجباري",
                reply_markup=get_admin_channels_keyboard()
            )
            return

        text = "📡 قنوات الاشتراك:\n\n"
        for ch in channels:
            status = "مطلوب" if ch.is_required else "اختياري"
            text += f"📢 {ch.channel_name or ch.channel_id}\n   الحالة: {status}\n\n"

        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔙 رجوع", callback_data="admin_channels")]
        ])
        await callback.message.edit_text(text, reply_markup=keyboard)
    finally:
        db.close()


@router.callback_query(F.data == "admin_users")
async def callback_admin_users(callback: CallbackQuery):
    """إدارة المستخدمين"""
    if not is_owner(callback.from_user.id):
        await callback.answer("غير مصرح لك", show_alert=True)
        return

    text = "🚫 إدارة المستخدمين"
    keyboard = get_admin_users_keyboard()
    await callback.message.edit_text(text, reply_markup=keyboard)


@router.callback_query(F.data == "admin_users_list")
async def callback_admin_users_list(callback: CallbackQuery):
    """عرض المستخدمين"""
    if not is_owner(callback.from_user.id):
        await callback.answer("غير مصرح لك", show_alert=True)
        return

    db = SessionLocal()
    try:
        user_service = UserService(db)
        users = user_service.get_all_users()[:30]

        text = "👥 قائمة المستخدمين:\n\n"
        for user in users:
            status_emoji = {"active": "✅", "banned": "🚫", "suspended": "⚠️"}.get(
                user.status.value, "❓"
            )
            name = user.first_name or user.username or user.telegram_id
            text += f"{status_emoji} {name}\n   ID: {user.telegram_id}\n"

        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔙 رجوع", callback_data="admin_users")]
        ])
        await callback.message.edit_text(text, reply_markup=keyboard)
    finally:
        db.close()


@router.callback_query(F.data == "check_subscription")
async def callback_check_subscription(callback: CallbackQuery):
    """فحص الاشتراك"""
    db = SessionLocal()
    try:
        channel_service = ChannelService(db)
        bot = callback.bot

        is_subscribed, not_subscribed = await channel_service.check_all_subscriptions(
            bot, callback.from_user.id
        )

        if is_subscribed:
            await callback.answer("✅ تم التحقق من اشتراكك!", show_alert=True)
            await callback.message.edit_text(
                "✅ شكراً لك! تم التحقق من اشتراكك.\n\nاختر من القائمة:",
                reply_markup=get_main_menu_keyboard(is_owner(callback.from_user.id))
            )
        else:
            await callback.answer("⚠️ لازلت غير مشترك", show_alert=True)
    finally:
        db.close()


@router.callback_query(F.data == "points_leaderboard")
async def callback_points_leaderboard(callback: CallbackQuery):
    """لوحة النقاط"""
    db = SessionLocal()
    try:
        points_service = PointsService(db)
        top_users = points_service.get_leaderboard(limit=10)

        text = "🏆 لوحة المتصدرين:\n\n"
        medals = ["🥇", "🥈", "🥉"]

        for i, up in enumerate(top_users, 1):
            medal = medals[i-1] if i <= 3 else f"{i}."
            text += f"{medal} نقاط: {up.current_balance}\n"

        if not top_users:
            text = "لا توجد بيانات بعد"

        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔙 رجوع", callback_data="my_points")]
        ])
        await callback.message.edit_text(text, reply_markup=keyboard)
    finally:
        db.close()


@router.callback_query(F.data == "toggle_language")
async def callback_toggle_language(callback: CallbackQuery):
    """تبديل اللغة"""
    db = SessionLocal()
    try:
        user_service = UserService(db)
        user = user_service.get_or_create_user(
            callback.from_user.id,
            callback.from_user.username,
            callback.from_user.first_name,
            callback.from_user.last_name,
        )

        user.language = "en" if (user.language or "ar") == "ar" else "ar"
        db.commit()
        db.refresh(user)

        await callback.answer("🌐 تم تغيير اللغة", show_alert=True)

        text = "⚙️ الإعدادات"
        keyboard = get_settings_keyboard(user.language)
        await safe_edit_text(callback.message, text, reply_markup=keyboard)
    finally:
        db.close()


@router.callback_query(F.data == "my_stats")
async def callback_my_stats(callback: CallbackQuery):
    """عرض إحصاءات المستخدم الشخصية"""
    db = SessionLocal()
    try:
        user_service = UserService(db)
        points_service = PointsService(db)

        user = user_service.get_user_by_telegram_id(callback.from_user.id)
        if not user:
            await callback.answer("لم يتم العثور على حسابك.", show_alert=True)
            return

        user_points = points_service.get_user_points(user.id)
        balance = user_points.current_balance if user_points else 0

        text = "👤 إحصائياتي\n\n"
        text += f"• الاسم: {user.first_name or user.username or user.telegram_id}\n"
        text += f"• الحالة: {user.status.value}\n"
        text += f"• المستوى: {user.level}\n"
        text += f"• النقاط الحالية: {balance}\n"
        text += f"• إجمالي التحميلات: {user.total_downloads}\n"
        text += f"• العضوية المميزة: {'نعم' if user.is_premium else 'لا'}\n"
        text += f"• كود الإحالة: {user.referral_code or 'غير متوفر'}\n"

        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔙 القائمة الرئيسية", callback_data="main_menu")]
        ])
        await callback.message.edit_text(text, reply_markup=keyboard)
    finally:
        db.close()



@router.callback_query(F.data == "search_text")
async def callback_search_text(callback: CallbackQuery, state: FSMContext):
    """البحث النصي"""
    await state.update_data(search_mode="text")
    await callback.message.edit_text("🔍 أدخل نص البحث:")
    await state.set_state(AdminStates.waiting_search)


@router.callback_query(F.data == "search_ai")
async def callback_search_ai(callback: CallbackQuery, state: FSMContext):
    """البحث الذكي بالذكاء الاصطناعي"""
    await state.update_data(search_mode="ai")
    await callback.message.edit_text("🤖 أدخل ما تريد البحث عنه بالذكاء الاصطناعي:")
    await state.set_state(AdminStates.waiting_search)


@router.callback_query(F.data == "search_category")
async def callback_search_category(callback: CallbackQuery, state: FSMContext):
    """البحث حسب القسم"""
    await state.update_data(search_mode="category")
    await callback.message.edit_text("📚 أدخل اسم القسم الذي تريد البحث فيه:")
    await state.set_state(AdminStates.waiting_search)


@router.callback_query(F.data == "search_author")
async def callback_search_author(callback: CallbackQuery, state: FSMContext):
    """البحث حسب المؤلف"""
    await state.update_data(search_mode="author")
    await callback.message.edit_text("✍️ أدخل اسم المؤلف الذي تريد البحث عنه:")
    await state.set_state(AdminStates.waiting_search)




@router.callback_query(F.data == "search_external")
async def callback_search_external(callback: CallbackQuery, state: FSMContext):
    """البحث الخارجي عن الكتب"""
    await state.update_data(search_mode="external")
    await callback.message.edit_text("🌐 أدخل كلمة البحث للبحث في المصادر الخارجية:")
    await state.set_state(AdminStates.waiting_search)

@router.message(AdminStates.waiting_search)
async def handle_search(message: Message, state: FSMContext):
    """معالجة البحث"""
    query = (message.text or "").strip()
    if not query:
        await message.answer("⚠️ أدخل نصاً صالحاً للبحث.")
        return

    data = await state.get_data()
    mode = data.get("search_mode", "text")

    db = SessionLocal()
    try:
        search_service = SearchService(db)
        books = []
        authors = []

        if mode == "ai":
            results = await search_service.semantic_search(query, limit=10)
            books = [book for book, _score in results]
        elif mode == "external":
            external = await search_service.search_external_sources(query, limit=10)
            if not external:
                await message.answer(f"لم يتم العثور على نتائج خارجية لـ: {query}")
                return
            text = f"🌐 نتائج خارجية عن: {query}\n\n"
            for item in external:
                text += f"• {item.get('title') or 'بدون عنوان'}\n"
                if item.get("author"):
                    text += f"  ✍️ {item.get('author')}\n"
                if item.get("year"):
                    text += f"  📅 {item.get('year')}\n"
                text += f"  المصدر: {item.get('source')}\n\n"
            keyboard = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔙 رجوع", callback_data="search_text")]])
            await message.answer(text, reply_markup=keyboard)
            return
        elif mode == "category":
            books = search_service.search_by_category(query, limit=10)
        elif mode == "author":
            books = search_service.search_by_author(query, limit=10)
        else:
            books, authors = search_service.text_search(query, limit=10)

        if not books and not authors:
            await message.answer(f"لم يتم العثور على نتائج لـ: {query}")
            return

        text = f"🔍 نتائج البحث عن: {query}\n\n"

        if books:
            text += "📚 الكتب:\n"
            for book in books[:10]:
                text += f"• {truncate_text(book.title, 40)}\n"

        if authors:
            text += "\n✍️ المؤلفين:\n"
            for auth in authors[:10]:
                text += f"• {auth.name}\n"

        keyboard = get_books_list_keyboard(books) if books else None
        await message.answer(text, reply_markup=keyboard)
    finally:
        db.close()
        await state.clear()
@router.callback_query(F.data == "admin_ai")
async def callback_admin_ai(callback: CallbackQuery, state: FSMContext):
    """مساعد AI"""
    if not is_owner(callback.from_user.id):
        await callback.answer("غير مصرح لك", show_alert=True)
        return

    await callback.message.edit_text(
        "🤖 مرحباً! أنا مساعد الذكاء الاصطناعي.\n\nأخبرني بما تحتاجه وسأساعدك.",
        reply_markup=get_back_to_admin_keyboard()
    )
    await state.set_state(AdminStates.waiting_ai_question)


@router.message(AdminStates.waiting_ai_question)
async def handle_ai_question(message: Message, state: FSMContext):
    """معالجة سؤال AI"""
    question = message.text

    if message.text == "🔙 رجوع":
        await state.clear()
        keyboard = get_admin_keyboard()
        await message.answer("👑 لوحة تحكم المالك", reply_markup=keyboard)
        return

    # استخدام AI للإجابة
    answer = await ai_service.answer_question(question, "أنت مساعد لمكتبة كتب عربية")

    await message.answer(f"🤖 {answer}")
    await state.clear()


# ==========================================
# New Admin Features Handlers - معالجات الميزات الجديدة للإدارة
# ==========================================

@router.callback_query(F.data == "admin_stats")
async def callback_admin_stats(callback: CallbackQuery):
    if not is_owner(callback.from_user.id):
        await callback.answer("غير مصرح لك", show_alert=True)
        return

    db = SessionLocal()
    try:
        book_service = BookService(db)
        user_service = UserService(db)
        points_service = PointsService(db)

        book_stats = book_service.get_statistics()
        user_stats = user_service.get_statistics()
        top_users = points_service.get_leaderboard(limit=5)

        text = "📊 إحصائيات متقدمة:\n\n"
        text += f"📚 الكتب: {book_stats['total']} | نشطة: {book_stats['active']} | مراجعة: {book_stats['pending']}\n"
        text += f"📥 التحميلات: {book_stats['total_downloads']} | متوسط التقييم: {book_stats['average_rating']}\n\n"
        text += f"👥 المستخدمين: {user_stats['total']} | نشطون: {user_stats['active']} | محظورون: {user_stats['banned']}\n"
        text += f"💎 مميزون: {user_stats['premium']}\n\n"
        text += "🏆 أفضل المستخدمين بالنقاط:\n"

        if top_users:
            for i, up in enumerate(top_users, 1):
                text += f"{i}. {up.user.first_name or up.user.username or up.user.telegram_id}: {up.current_balance} نقاط\n"
        else:
            text += "لا توجد بيانات بعد.\n"

        keyboard = get_back_to_admin_keyboard()
        await callback.message.edit_text(text, reply_markup=keyboard)
    finally:
        db.close()

@router.callback_query(F.data == "admin_users")
async def callback_admin_users(callback: CallbackQuery):
    if not is_owner(callback.from_user.id):
        await callback.answer("غير مصرح لك", show_alert=True)
        return
    await callback.message.edit_text("🚫 إدارة المستخدمين\n\n(قيد التطوير)", reply_markup=get_back_to_admin_keyboard())

@router.callback_query(F.data == "admin_broadcast")
async def callback_admin_broadcast(callback: CallbackQuery, state: FSMContext):
    if not is_owner(callback.from_user.id):
        await callback.answer("غير مصرح لك", show_alert=True)
        return

    await callback.message.edit_text(
        "📢 أرسل الآن نص الرسالة التي ترغب في إرسالها إلى جميع المستخدمين.\n\nيمكنك كتابة رسالة قصيرة أو تضمين روابط.",
        reply_markup=get_back_to_admin_keyboard()
    )
    await state.set_state(AdminStates.waiting_broadcast)

@router.message(AdminStates.waiting_broadcast)
async def process_broadcast_message(message: Message, state: FSMContext, bot: Bot):
    if not is_owner(message.from_user.id):
        return

    broadcast_text = message.text.strip()
    if not broadcast_text:
        await message.answer("⚠️ يرجى كتابة نص الرسالة قبل الإرسال.")
        return

    db = SessionLocal()
    try:
        user_service = UserService(db)
        users = user_service.get_all_users(status=UserStatus.ACTIVE)

        success = 0
        failure = 0

        for user in users:
            try:
                await bot.send_message(user.telegram_id, f"📢 إعلان من مكتبة Smart Books:\n\n{broadcast_text}")
                success += 1
            except Exception as e:
                logger.warning(f"Broadcast failed for {user.telegram_id}: {e}")
                failure += 1
            await asyncio.sleep(0.05)

        await message.answer(
            f"✅ تم إرسال الرسالة إلى {success} مستخدمين.\n⚠️ فشل الإرسال إلى {failure} مستخدمين."
        )
    finally:
        db.close()
        await state.clear()

@router.callback_query(F.data == "admin_market")
async def callback_admin_market(callback: CallbackQuery):
    """إدارة السوق"""
    if not is_owner(callback.from_user.id):
        await callback.answer("غير مصرح لك", show_alert=True)
        return
    text = "🏪 إدارة السوق"
    keyboard = get_admin_market_keyboard()
    await callback.message.edit_text(text, reply_markup=keyboard)

@router.callback_query(F.data == "admin_challenges")
async def callback_admin_challenges(callback: CallbackQuery):
    """إدارة التحديات"""
    if not is_owner(callback.from_user.id):
        await callback.answer("غير مصرح لك", show_alert=True)
        return
    text = "🏆 إدارة التحديات"
    keyboard = get_admin_challenges_keyboard()
    await callback.message.edit_text(text, reply_markup=keyboard)

@router.callback_query(F.data == "admin_security")
async def callback_admin_security(callback: CallbackQuery):
    """إدارة الأمان"""
    if not is_owner(callback.from_user.id):
        await callback.answer("غير مصرح لك", show_alert=True)
        return
    text = "🔒 إدارة الأمان والتدقيق"
    keyboard = get_admin_security_keyboard()
    await callback.message.edit_text(text, reply_markup=keyboard)

@router.callback_query(F.data == "admin_ai")
async def callback_admin_ai(callback: CallbackQuery):
    if not is_owner(callback.from_user.id):
        return
    await callback.message.edit_text("🤖 مساعد AI\n\nأرسل سؤالك وسأقوم بالرد عليك باستخدام الذكاء الاصطناعي.", reply_markup=get_back_to_admin_keyboard())

@router.callback_query(F.data == "admin_export_csv")
async def callback_admin_export_csv(callback: CallbackQuery):
    if not is_owner(callback.from_user.id):
        return
    await callback.answer("📤 جاري تصدير البيانات...")
    # يمكن استدعاء cmd_export_csv هنا أو تنفيذ المنطق مباشرة
    await callback.message.answer("استخدم الأمر /exportcsv لتصدير البيانات حالياً.")

@router.callback_query(F.data == "admin_upload_book")
async def callback_admin_upload_book(callback: CallbackQuery, state: FSMContext):
    if not is_owner(callback.from_user.id):
        return
    await callback.message.edit_text("📚 أرسل عنوان الكتاب الجديد:")
    await state.set_state(AdminStates.waiting_book_title)


@router.callback_query(F.data == "admin_audit_log")
async def callback_admin_audit_log(callback: CallbackQuery):
    """سجل التدقيق"""
    if not is_owner(callback.from_user.id):
        await callback.answer("غير مصرح لك", show_alert=True)
        return

    db = SessionLocal()
    try:
        service = SecurityService(db)
        logs = service.get_recent_logs(limit=20)

        text = "📋 سجل التدقيق:\n\n"
        for log in logs:
            text += f"📌 {log.get('action', '')}\n"
            text += f"👤 المستخدم: {log.get('user_id', 'N/A')}\n"
            text += f"📅 {log.get('timestamp', '')}\n\n"

        if not logs:
            text = "📋 لا توجد سجلات تدقيق"

        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔙 رجوع", callback_data="admin_security")]
        ])
        await callback.message.edit_text(text, reply_markup=keyboard)
    finally:
        db.close()


@router.callback_query(F.data == "admin_security_stats")
async def callback_admin_security_stats(callback: CallbackQuery):
    """إحصائيات الأمان"""
    if not is_owner(callback.from_user.id):
        await callback.answer("غير مصرح لك", show_alert=True)
        return

    db = SessionLocal()
    try:
        service = SecurityService(db)
        stats = service.get_security_stats()

        text = f"""
🔒 إحصائيات الأمان:

🚨 الأحداث المشبوهة: {stats.get('suspicious_events', 0)}
🚫 المحظورين: {stats.get('blocked_users', 0)}
📊 طلبات API: {stats.get('api_requests', 0)}
⚠️ محاولات الوصول الفاشلة: {stats.get('failed_attempts', 0)}
        """

        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔙 رجوع", callback_data="admin_security")]
        ])
        await callback.message.edit_text(text, reply_markup=keyboard)
    finally:
        db.close()


@router.callback_query(F.data == "admin_blacklist")
async def callback_admin_blacklist(callback: CallbackQuery):
    """القائمة السوداء"""
    if not is_owner(callback.from_user.id):
        await callback.answer("غير مصرح لك", show_alert=True)
        return

    db = SessionLocal()
    try:
        service = SecurityService(db)
        blocked = service.get_blocked_ips(limit=20)

        text = "🚫 القائمة السوداء:\n\n"
        for ip in blocked:
            text += f"🔒 {ip.get('ip_address', '')}\n"
            text += f"   السبب: {ip.get('reason', 'غير محدد')}\n\n"

        if not blocked:
            text = "🚫 لا توجد عناوين محظورة"

        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="➕ إضافة عنوان", callback_data="admin_add_blacklist")],
            [InlineKeyboardButton(text="🔙 رجوع", callback_data="admin_security")]
        ])
        await callback.message.edit_text(text, reply_markup=keyboard)
    finally:
        db.close()


@router.callback_query(F.data == "admin_referral")
async def callback_admin_referral(callback: CallbackQuery):
    """إدارة الإحالات"""
    if not is_owner(callback.from_user.id):
        await callback.answer("غير مصرح لك", show_alert=True)
        return

    db = SessionLocal()
    try:
        service = ReferralService(db)
        stats = service.get_referral_stats(0)  # Platform-wide

        text = f"""
🎯 إحصائيات الإحالة للمنصة:

👥 إجمالي المحيلين: {stats.get('total_referrals', 0)}
💰 إجمالي الأرباح الموزعة: {stats.get('total_earnings', 0)} نقطة
🎖️ الشارات الممنوحة: {stats.get('badges_count', 0)}
        """

        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📊 لوحة أفضل المحيلين", callback_data="admin_referral_leaderboard")],
            [InlineKeyboardButton(text="⚙️ إعدادات الإحالة", callback_data="admin_referral_settings")],
            [InlineKeyboardButton(text="🔙 رجوع", callback_data="admin_menu")]
        ])
        await callback.message.edit_text(text, reply_markup=keyboard)
    finally:
        db.close()


@router.callback_query(F.data == "admin_notifications")
async def callback_admin_notifications(callback: CallbackQuery):
    """إدارة الإشعارات"""
    if not is_owner(callback.from_user.id):
        await callback.answer("غير مصرح لك", show_alert=True)
        return

    text = """
🔔 إدارة الإشعارات:

📨 يمكنك إرسال إشعارات للمستخدمين
📊 عرض إحصائيات الإشعارات
⚙️ إدارة قوالب الإشعارات
"""

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📨 إرسال إشعار", callback_data="admin_send_notification")],
        [InlineKeyboardButton(text="📊 إحصائيات الإشعارات", callback_data="admin_notification_stats")],
        [InlineKeyboardButton(text="🔙 رجوع", callback_data="admin_menu")]
    ])
    await callback.message.edit_text(text, reply_markup=keyboard)


@router.callback_query(F.data == "admin_leaderboard")
async def callback_admin_leaderboard(callback: CallbackQuery):
    """لوحة المتصدرين"""
    if not is_owner(callback.from_user.id):
        await callback.answer("غير مصرح لك", show_alert=True)
        return

    db = SessionLocal()
    try:
        challenge_service = ChallengeService(db)
        points_service = PointsService(db)

        text = "📊 لوحات المتصدرين:\n\n"

        # Points leaderboard
        text += "💰 نقاط المستخدمين:\n"
        top_points = points_service.get_leaderboard(limit=5)
        for i, up in enumerate(top_points, 1):
            text += f"{i}. نقاط: {up.current_balance}\n"

        text += "\n🏆 التحديات:\n"
        top_challenges = challenge_service.get_leaderboard("weekly", limit=5)
        for i, entry in enumerate(top_challenges, 1):
            text += f"{i}. {entry.get('user_name', 'مستخدم')}: {entry.get('score', 0)}\n"

        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔙 رجوع", callback_data="admin_menu")]
        ])
        await callback.message.edit_text(text, reply_markup=keyboard)
    finally:
        db.close()


@router.callback_query(F.data == "admin_market_stats")
async def callback_admin_market_stats(callback: CallbackQuery):
    """إحصائيات السوق"""
    if not is_owner(callback.from_user.id):
        await callback.answer("غير مصرح لك", show_alert=True)
        return

    db = SessionLocal()
    try:
        service = MarketService(db)
        stats = service.get_platform_earnings()

        text = f"""
🏪 إحصائيات السوق:

💰 إجمالي الإيرادات: {stats.get('total_earnings', 0)} نقطة
📦 إجمالي المعاملات: {stats.get('total_transactions', 0)}
🏆 المبيعات: {stats.get('sales_count', 0)}
🔨 المزادات: {stats.get('auctions_count', 0)}
        """

        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔙 رجوع", callback_data="admin_market")]
        ])
        await callback.message.edit_text(text, reply_markup=keyboard)
    finally:
        db.close()



@router.callback_query(F.data == "contact_support")
async def callback_contact_support(callback: CallbackQuery):
    """التواصل مع الدعم"""
    support_lines = [
        "📞 الدعم والتواصل",
        "",
        "• إذا كانت لديك مشكلة تقنية، تواصل مع مشرف البوت.",
    ]
    if settings.telegram_admin_id:
        support_lines.append(f"• معرف المشرف: {settings.telegram_admin_id}")
    support_lines.append("• يمكنك أيضاً إرسال وصف المشكلة هنا، وسأعرضه لك كنص مرجعي.")
    await callback.message.edit_text("\n".join(support_lines), reply_markup=get_back_keyboard())


@router.callback_query(F.data.startswith("admin_book_view_"))
async def callback_admin_book_view(callback: CallbackQuery):
    """عرض تفاصيل كتاب داخل لوحة الإدارة"""
    if not is_owner(callback.from_user.id):
        await callback.answer("غير مصرح لك", show_alert=True)
        return

    book_id = int(callback.data.split("_")[-1])
    db = SessionLocal()
    try:
        book_service = BookService(db)
        book = book_service.get_book(book_id)
        if not book:
            await callback.answer("الكتاب غير موجود", show_alert=True)
            return

        status = getattr(book.status, 'value', str(book.status))
        text = f"📖 {book.title}\n\n"
        text += f"🆔 ID: {book.id}\n"
        text += f"👤 المؤلف: {book.author.name if book.author else 'غير معروف'}\n"
        text += f"📁 القسم: {book.category.name if book.category else 'غير محدد'}\n"
        text += f"📌 الحالة: {status}\n"
        if book.description:
            text += f"\n📝 {truncate_text(book.description, 250)}\n"

        keyboard = get_admin_book_actions_keyboard(book.id) if book.status == BookStatus.PENDING else get_back_to_admin_keyboard()
        await callback.message.edit_text(text, reply_markup=keyboard)
    finally:
        db.close()


@router.callback_query(F.data.startswith("admin_auth_edit_"))
async def callback_admin_auth_edit(callback: CallbackQuery, state: FSMContext):
    """بدء تعديل اسم المؤلف"""
    if not is_owner(callback.from_user.id):
        await callback.answer("غير مصرح لك", show_alert=True)
        return

    author_id = int(callback.data.split("_")[-1])
    await state.update_data(author_id=author_id)
    await callback.message.edit_text("✏️ أرسل الاسم الجديد للمؤلف:")
    await state.set_state(AdminStates.waiting_author_edit)


@router.message(AdminStates.waiting_author_edit)
async def process_author_edit(message: Message, state: FSMContext):
    """حفظ تعديل المؤلف"""
    if not is_owner(message.from_user.id):
        return

    data = await state.get_data()
    author_id = data.get("author_id")
    new_name = (message.text or "").strip()
    if not new_name:
        await message.answer("⚠️ الاسم لا يمكن أن يكون فارغاً.")
        return

    db = SessionLocal()
    try:
        author_service = AuthorService(db)
        updated = author_service.update(author_id, name=new_name)
        if not updated:
            await message.answer("❌ المؤلف غير موجود.")
            return
        await message.answer(f"✅ تم تحديث المؤلف إلى: {updated.name}", reply_markup=get_admin_authors_keyboard())
    finally:
        db.close()
        await state.clear()


@router.callback_query(F.data == "admin_market_listings")
async def callback_admin_market_listings(callback: CallbackQuery):
    """عرض القوائم في السوق"""
    if not is_owner(callback.from_user.id):
        await callback.answer("غير مصرح لك", show_alert=True)
        return

    db = SessionLocal()
    try:
        service = MarketService(db)
        listings = service.get_available_listings(limit=10)
        text = f"📋 القوائم المتاحة في السوق: {len(listings)}\n\n"
        for listing in listings[:10]:
            text += f"• {getattr(listing, 'title', 'قائمة')} (ID: {listing.id})\n"
        await callback.message.edit_text(text or "📭 لا توجد قوائم حالياً.", reply_markup=get_admin_market_keyboard())
    finally:
        db.close()


@router.callback_query(F.data == "admin_market_auctions")
async def callback_admin_market_auctions(callback: CallbackQuery):
    """عرض المزادات في السوق"""
    if not is_owner(callback.from_user.id):
        await callback.answer("غير مصرح لك", show_alert=True)
        return

    db = SessionLocal()
    try:
        service = MarketService(db)
        auctions = service.get_auctions(limit=10)
        text = f"🔨 المزادات النشطة: {len(auctions)}\n\n"
        for item in auctions[:10]:
            text += f"• {getattr(item, 'title', 'مزاد')} (ID: {item.id})\n"
        await callback.message.edit_text(text or "📭 لا توجد مزادات حالياً.", reply_markup=get_admin_market_keyboard())
    finally:
        db.close()


@router.callback_query(F.data == "admin_market_settings")
async def callback_admin_market_settings(callback: CallbackQuery):
    """إعدادات السوق"""
    if not is_owner(callback.from_user.id):
        await callback.answer("غير مصرح لك", show_alert=True)
        return

    db = SessionLocal()
    try:
        service = MarketService(db)
        stats = service.get_platform_earnings()
        text = (
            "⚙️ إعدادات السوق\n\n"
            f"💰 إجمالي الإيرادات: {stats.get('total_earnings', 0)}\n"
            f"📦 إجمالي المعاملات: {stats.get('total_transactions', 0)}\n"
            f"🏆 المبيعات: {stats.get('sales_count', 0)}\n"
            f"🔨 المزادات: {stats.get('auctions_count', 0)}\n"
        )
        await callback.message.edit_text(text, reply_markup=get_admin_market_keyboard())
    finally:
        db.close()


@router.callback_query(F.data == "admin_ch_add")
async def callback_admin_ch_add(callback: CallbackQuery):
    """إضافة تحدي جديد (إشعار/بوابة)"""
    if not is_owner(callback.from_user.id):
        await callback.answer("غير مصرح لك", show_alert=True)
        return
    await callback.message.edit_text(
        "🏆 إضافة تحدي جديد\n\nهذه الواجهة جاهزة كمدخل، لكن إنشاء التحديات التفصيلي يحتاج نموذج إدخال منفصل.\nيمكنك الآن الرجوع إلى لوحة التحديات أو ربطها بنقطة نهاية API لاحقاً.",
        reply_markup=get_admin_challenges_keyboard()
    )


@router.callback_query(F.data == "admin_referral_leaderboard")
async def callback_admin_referral_leaderboard(callback: CallbackQuery):
    """لوحة أفضل المحيلين"""
    if not is_owner(callback.from_user.id):
        await callback.answer("غير مصرح لك", show_alert=True)
        return

    db = SessionLocal()
    try:
        service = ReferralService(db)
        top = service.get_top_referrers(limit=10)
        text = "🎯 أفضل المحيلين:\n\n"
        if not top:
            text += "لا توجد بيانات بعد.\n"
        else:
            for i, item in enumerate(top, 1):
                text += f"{i}. {item.get('name') or item.get('telegram_id')} - {item.get('referrals', 0)}\n"
        await callback.message.edit_text(
            text,
            reply_markup=InlineKeyboardMarkup(
                inline_keyboard=[[InlineKeyboardButton(text='🔙 رجوع', callback_data='admin_referral')]]
            ),
        )
    finally:
        db.close()


@router.callback_query(F.data == "admin_referral_settings")
async def callback_admin_referral_settings(callback: CallbackQuery):
    """إعدادات الإحالة"""
    if not is_owner(callback.from_user.id):
        await callback.answer("غير مصرح لك", show_alert=True)
        return

    db = SessionLocal()
    try:
        service = ReferralService(db)
        stats = service.get_referral_stats(0)
        text = (
            "⚙️ إعدادات الإحالة\n\n"
            f"👥 إجمالي الإحالات: {stats.get('direct_referrals', 0)}\n"
            f"✅ النشطة: {stats.get('active_direct', 0)}\n"
            f"💰 إجمالي الأرباح: {stats.get('total_earnings', 0)}\n"
        )
        await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text='🔙 رجوع', callback_data='admin_referral')]]))
    finally:
        db.close()


# ==========================================
# Error Handler
# ==========================================

@router.error()
async def error_handler(event: ErrorEvent):
    """معالج الأخطاء العام للبوت"""
    error = event.exception
    logging.error(f"Unhandled error: {type(error).__name__}: {error}")
    # يمكنك أيضاً تسجيل الخطأ في قاعدة البيانات أو إرسال رسالة للمالك
    return True

# ==========================================
# الإصلاحات الإضافية لمعالجات المالك (Fixes)
# ==========================================

@router.callback_query(F.data == "admin_books")
async def callback_admin_books(callback: CallbackQuery):
    """لوحة إدارة الكتب"""
    if not is_owner(callback.from_user.id): return
    text = "📚 إدارة الكتب\n\nاختر من الخيارات التالية:"
    from app.bot.keyboards import get_admin_books_keyboard
    await callback.message.edit_text(text, reply_markup=get_admin_books_keyboard())

@router.callback_query(F.data == "admin_book_list")
async def callback_admin_book_list(callback: CallbackQuery):
    """عرض قائمة الكتب للإدارة"""
    if not is_owner(callback.from_user.id): return
    db = SessionLocal()
    try:
        book_service = BookService(db)
        books = book_service.get_all_books(limit=20)
        if not books:
            await callback.answer("لا توجد كتب حالياً", show_alert=True)
            return
        
        from aiogram.utils.keyboard import InlineKeyboardBuilder
        builder = InlineKeyboardBuilder()
        for book in books:
            builder.row(InlineKeyboardButton(text=f"📖 {book.title}", callback_data=f"admin_book_view_{book.id}"))
        builder.row(InlineKeyboardButton(text="🔙 رجوع", callback_data="admin_books"))
        await callback.message.edit_text("📋 قائمة الكتب المسجلة:", reply_markup=builder.as_markup())
    finally:
        db.close()

@router.callback_query(F.data == "admin_authors")
async def callback_admin_authors(callback: CallbackQuery):
    """لوحة إدارة المؤلفين"""
    if not is_owner(callback.from_user.id): return
    text = "✍️ إدارة المؤلفين"
    from app.bot.keyboards import get_admin_authors_keyboard
    await callback.message.edit_text(text, reply_markup=get_admin_authors_keyboard())

@router.callback_query(F.data == "admin_auth_list")
async def callback_admin_auth_list(callback: CallbackQuery):
    """عرض جميع المؤلفين مع خيارات التعديل والحذف"""
    if not is_owner(callback.from_user.id): return
    db = SessionLocal()
    try:
        author_service = AuthorService(db)
        authors = author_service.list_all()
        if not authors:
            from app.bot.keyboards import get_admin_authors_keyboard
            await callback.message.edit_text("📭 لا يوجد مؤلفون حالياً.", reply_markup=get_admin_authors_keyboard())
            return

        from aiogram.utils.keyboard import InlineKeyboardBuilder
        builder = InlineKeyboardBuilder()
        for auth in authors:
            builder.row(
                InlineKeyboardButton(text=f"👤 {auth.name}", callback_data="ignore"),
                InlineKeyboardButton(text="✏️", callback_data=f"admin_auth_edit_{auth.id}"),
                InlineKeyboardButton(text="🗑️", callback_data=f"admin_auth_delete_{auth.id}")
            )
        builder.row(InlineKeyboardButton(text="🔙 رجوع", callback_data="admin_authors"))
        await callback.message.edit_text("✍️ قائمة المؤلفين:", reply_markup=builder.as_markup())
    finally:
        db.close()

# @router.callback_query(F.data == "admin_add_author")
# async def callback_admin_add_author(callback: CallbackQuery, state: FSMContext):
#   """بدء إضافة مؤلف"""
#    if not is_owner(callback.from_user.id): return
#    await callback.message.edit_text("✍️ أرسل اسم المؤلف الجديد:")
#    await state.set_state(AdminStates.waiting_author_name)

@router.callback_query(F.data == "admin_add_channel")
async def callback_admin_add_channel(callback: CallbackQuery, state: FSMContext):
    """بدء إضافة قناة"""
    if not is_owner(callback.from_user.id): return
    await callback.message.edit_text("📡 أرسل معرف القناة (مثلاً @channel_id أو ID القناة):")
    await state.set_state(AdminStates.waiting_channel_id)

@router.callback_query(F.data == "admin_notifications")
async def callback_admin_notifications(callback: CallbackQuery):
    if not is_owner(callback.from_user.id): return
    await callback.message.edit_text("🔔 إدارة الإشعارات\n\n(قيد التطوير)", reply_markup=get_back_to_admin_keyboard())

@router.callback_query(F.data == "admin_referral")
async def callback_admin_referral(callback: CallbackQuery):
    if not is_owner(callback.from_user.id): return
    await callback.message.edit_text("🎯 إدارة الإحالات\n\n(قيد التطوير)", reply_markup=get_back_to_admin_keyboard())

@router.callback_query(F.data == "admin_leaderboard")
async def callback_admin_leaderboard(callback: CallbackQuery):
    if not is_owner(callback.from_user.id): return
    await callback.message.edit_text("📊 لوحة المتصدرين\n\n(قيد التطوير)", reply_markup=get_back_to_admin_keyboard())

@router.callback_query(F.data == "admin_security")
async def callback_admin_security(callback: CallbackQuery):
    if not is_owner(callback.from_user.id): return
    from app.bot.keyboards import get_admin_security_keyboard
    await callback.message.edit_text("🔒 الأمان والتدقيق", reply_markup=get_admin_security_keyboard())

@router.callback_query(F.data == "admin_market")
async def callback_admin_market_main(callback: CallbackQuery):
    if not is_owner(callback.from_user.id): return
    from app.bot.keyboards import get_admin_market_keyboard
    await callback.message.edit_text("🏪 إدارة السوق", reply_markup=get_admin_market_keyboard())

@router.callback_query(F.data == "admin_challenges")
async def callback_admin_challenges_main(callback: CallbackQuery):
    if not is_owner(callback.from_user.id): return
    from app.bot.keyboards import get_admin_challenges_keyboard
    await callback.message.edit_text("🏆 إدارة التحديات", reply_markup=get_admin_challenges_keyboard())


# ==========================================

# ==========================================
# Missing/Compatibility Handlers
# ==========================================

@router.callback_query(F.data == "my_downloads")
async def callback_my_downloads(callback: CallbackQuery):
    db = SessionLocal()
    try:
        user_service = UserService(db)
        book_service = BookService(db)
        user_service.get_or_create_user(callback.from_user.id, callback.from_user.username, callback.from_user.first_name, callback.from_user.last_name)
        downloads = user_service.get_user_downloads(callback.from_user.id, limit=10)
        if not downloads:
            await callback.answer("لا توجد تحميلات سابقة", show_alert=True)
            return
        text = "📥 سجل التحميلات:\n\n"
        books = []
        for dl in downloads:
            book = book_service.get_book(dl.book_id)
            if book:
                books.append(book)
                text += f"• {truncate_text(book.title, 40)}\n"
        await callback.message.edit_text(text, reply_markup=get_books_list_keyboard(books) if books else get_back_keyboard())
    finally:
        db.close()

@router.callback_query(F.data == "my_favorites")
async def callback_my_favorites(callback: CallbackQuery):
    db = SessionLocal()
    try:
        user_service = UserService(db)
        book_service = BookService(db)
        user = user_service.get_or_create_user(callback.from_user.id, callback.from_user.username, callback.from_user.first_name, callback.from_user.last_name)
        favorites = user_service.get_user_favorites(callback.from_user.id)
        if not favorites:
            await callback.answer("لا توجد مفضلة حالياً", show_alert=True)
            return
        books = []
        for fav in favorites:
            book = book_service.get_book(fav.book_id)
            if book:
                books.append(book)
        text = "❤️ كتبك المفضلة:\n\n" + "\n".join(f"• {truncate_text(book.title, 40)}" for book in books)
        await callback.message.edit_text(text, reply_markup=get_books_list_keyboard(books) if books else get_back_keyboard())
    finally:
        db.close()

@router.callback_query(F.data == "invite_friend")
async def callback_invite_friend(callback: CallbackQuery):
    db = SessionLocal()
    try:
        user_service = UserService(db)
        user = user_service.get_or_create_user(callback.from_user.id, callback.from_user.username, callback.from_user.first_name, callback.from_user.last_name)
        bot_username = callback.bot.username if callback.bot and callback.bot.username else "your_bot"
        link = f"https://t.me/{bot_username}?start={user.referral_code}"
        await callback.message.edit_text(f"🎁 رابط الإحالة الخاص بك:\n\n{link}", reply_markup=get_back_keyboard())
    finally:
        db.close()

@router.callback_query(F.data == "referral_top")
async def callback_referral_top(callback: CallbackQuery):
    db = SessionLocal()
    try:
        service = ReferralService(db)
        top = service.get_top_referrers(limit=10)
        if not top:
            await callback.message.edit_text("لا توجد بيانات إحالة بعد.", reply_markup=get_referral_keyboard())
            return
        text = "👥 أفضل المحيلين:\n\n" + "\n".join(f"{i+1}. {item.get('name') or item.get('telegram_id')} - {item.get('referrals', 0)}" for i, item in enumerate(top))
        await callback.message.edit_text(text, reply_markup=get_referral_keyboard())
    finally:
        db.close()

@router.callback_query(F.data == "referral_badges")
async def callback_referral_badges(callback: CallbackQuery):
    db = SessionLocal()
    try:
        service = ReferralService(db)
        user = UserService(db).get_or_create_user(callback.from_user.id, callback.from_user.username, callback.from_user.first_name, callback.from_user.last_name)
        badges = service.get_user_badges(user.id)
        text = "🎖️ شارات الإحالة:\n\n" + ("\n".join(f"• {b.name}" for b in badges) if badges else "لا توجد شارات بعد")
        await callback.message.edit_text(text, reply_markup=get_referral_keyboard())
    finally:
        db.close()

@router.callback_query(F.data == "notifications_settings")
async def callback_notifications_settings(callback: CallbackQuery):
    await callback.message.edit_text("⚙️ إعدادات الإشعارات\n\n(قيد التطوير)", reply_markup=get_notifications_keyboard())

@router.callback_query(F.data == "admin_badges")
async def callback_admin_badges(callback: CallbackQuery):
    if not is_owner(callback.from_user.id):
        await callback.answer("غير مصرح لك", show_alert=True)
        return
    await callback.message.edit_text("🎖️ إدارة الشارات\n\n(قيد التطوير)", reply_markup=get_admin_challenges_keyboard())

@router.callback_query(F.data == "admin_security_events")
async def callback_admin_security_events(callback: CallbackQuery):
    if not is_owner(callback.from_user.id):
        await callback.answer("غير مصرح لك", show_alert=True)
        return
    db = SessionLocal()
    try:
        service = SecurityService(db)
        logs = service.get_recent_logs(limit=10)
        if logs:
            text = "🚨 أحداث الأمان\n\n" + "\n".join(f"• {item.get('action')} @ {item.get('timestamp') or ''}" for item in logs)
        else:
            text = "🚨 أحداث الأمان\n\nلا توجد أحداث"
        await callback.message.edit_text(text, reply_markup=get_admin_security_keyboard())
    finally:
        db.close()

@router.callback_query(F.data == "admin_user_ban")
async def callback_admin_user_ban(callback: CallbackQuery, state: FSMContext):
    if not is_owner(callback.from_user.id):
        return
    await state.update_data(user_action="ban")
    await callback.message.edit_text("🚫 أرسل Telegram ID للمستخدم الذي تريد حظره:")
    await state.set_state(AdminStates.waiting_user_id)

@router.callback_query(F.data == "admin_user_unban")
async def callback_admin_user_unban(callback: CallbackQuery, state: FSMContext):
    if not is_owner(callback.from_user.id):
        return
    await state.update_data(user_action="unban")
    await callback.message.edit_text("✅ أرسل Telegram ID للمستخدم الذي تريد إلغاء حظره:")
    await state.set_state(AdminStates.waiting_user_id)

@router.callback_query(F.data == "admin_user_message")
async def callback_admin_user_message(callback: CallbackQuery, state: FSMContext):
    if not is_owner(callback.from_user.id):
        return
    await state.update_data(user_action="message")
    await callback.message.edit_text("📤 أرسل Telegram ID للمستخدم الذي تريد مراسلته:")
    await state.set_state(AdminStates.waiting_user_id)

@router.callback_query(F.data == "admin_users_search")
async def callback_admin_users_search(callback: CallbackQuery, state: FSMContext):
    if not is_owner(callback.from_user.id):
        return
    await state.update_data(user_action="search")
    await callback.message.edit_text("🔍 أرسل اسم المستخدم أو Telegram ID للبحث:")
    await state.set_state(AdminStates.waiting_user_id)

@router.message(AdminStates.waiting_user_id)
async def process_admin_user_id(message: Message, state: FSMContext, bot: Bot):
    if not is_owner(message.from_user.id):
        return
    data = await state.get_data()
    action = data.get("user_action")
    query = (message.text or "").strip()
    db = SessionLocal()
    try:
        user_service = UserService(db)
        if action == "search":
            users = user_service.search_users(query)
            if users:
                text = "👥 نتائج البحث:\n\n" + "\n".join(f"• {u.first_name or u.username or u.telegram_id} ({u.telegram_id})" for u in users)
            else:
                text = "👥 نتائج البحث:\n\nلا توجد نتائج"
            await message.answer(text, reply_markup=get_admin_users_keyboard())
        else:
            try:
                telegram_id = int(query)
            except ValueError:
                await message.answer("⚠️ أرسل رقم Telegram ID صالحاً.")
                return
            user = user_service.get_user_by_telegram_id(telegram_id)
            if not user:
                await message.answer("❌ المستخدم غير موجود.", reply_markup=get_admin_users_keyboard())
                return
            if action == "ban":
                user_service.ban_user(telegram_id)
                await message.answer("🚫 تم حظر المستخدم.", reply_markup=get_admin_users_keyboard())
            elif action == "unban":
                user_service.unban_user(telegram_id)
                await message.answer("✅ تم إلغاء حظر المستخدم.", reply_markup=get_admin_users_keyboard())
            elif action == "message":
                await state.update_data(target_user_id=telegram_id)
                await message.answer("📨 أرسل الرسالة الآن:")
                await state.set_state(AdminStates.waiting_message_user)
                return
    finally:
        db.close()
        if action != "message":
            await state.clear()

@router.message(AdminStates.waiting_message_user)
async def process_admin_user_message(message: Message, state: FSMContext, bot: Bot):
    if not is_owner(message.from_user.id):
        return
    data = await state.get_data()
    target_user_id = data.get("target_user_id")
    if not target_user_id:
        await message.answer("⚠️ لم يتم تحديد المستخدم.")
        await state.clear()
        return
    try:
        await bot.send_message(target_user_id, f"📨 رسالة من الإدارة:\n\n{message.text}")
        await message.answer("✅ تم إرسال الرسالة بنجاح.", reply_markup=get_admin_users_keyboard())
    except Exception as e:
        await message.answer(f"⚠️ فشل إرسال الرسالة: {e}", reply_markup=get_admin_users_keyboard())
    finally:
        await state.clear()

@router.callback_query(F.data == "ai_summary_quick")
async def callback_ai_summary_quick(callback: CallbackQuery):
    await callback.message.edit_text("📝 الملخص السريع\n\nأرسل عنوان الكتاب أو النص المطلوب تلخيصه.", reply_markup=get_back_keyboard())

@router.callback_query(F.data == "ai_summary_detailed")
async def callback_ai_summary_detailed(callback: CallbackQuery):
    await callback.message.edit_text("📖 الملخص التفصيلي\n\nأرسل عنوان الكتاب أو النص المطلوب تلخيصه.", reply_markup=get_back_keyboard())

@router.callback_query(F.data == "ai_characters")
async def callback_ai_characters(callback: CallbackQuery):
    await callback.message.edit_text("👥 تحليل الشخصيات\n\n(قيد التطوير)", reply_markup=get_back_keyboard())

@router.callback_query(F.data == "ai_sentiment")
async def callback_ai_sentiment(callback: CallbackQuery):
    await callback.message.edit_text("😊 تحليل المشاعر\n\n(قيد التطوير)", reply_markup=get_back_keyboard())

@router.callback_query(F.data == "ai_themes")
async def callback_ai_themes(callback: CallbackQuery):
    await callback.message.edit_text("🧩 تحليل الموضوعات\n\n(قيد التطوير)", reply_markup=get_back_keyboard())
