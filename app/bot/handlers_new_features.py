"""
New Features Handlers - معالجات الميزات الجديدة
معالجات السوق، التحديات، الإحالة، الإشعارات، و AI
"""
from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.filters import Command

from app.database import SessionLocal
from app.services.market_service import MarketService
from app.services.challenge_service import ChallengeService
from app.services.referral_service import ReferralService
from app.services.notification_service import NotificationService
from app.services.security_service import SecurityService
from app.services.ai_service import AIService
from app.services.user_service import UserService
from app.services.book_service import BookService
from app.services.recommendation_service import RecommendationService

from app.bot.keyboards import (
    get_market_keyboard,
    get_ai_features_keyboard,
    get_challenges_keyboard,
    get_referral_keyboard,
    get_notifications_keyboard,
    get_main_menu_enhanced_keyboard,
    get_listing_keyboard,
    get_auction_keyboard,
    get_back_to_admin_keyboard,
    get_admin_market_keyboard,
    get_admin_challenges_keyboard,
    get_admin_security_keyboard,
)
from config.settings import get_settings

settings = get_settings()
router = Router()


def is_owner(telegram_id: int) -> bool:
    """التحقق من أن المستخدم هو المالك"""
    return settings.is_owner(telegram_id)


# ==========================================
# States Groups للميزات الجديدة
# ==========================================

class MarketStates(StatesGroup):
    """حالات السوق"""
    waiting_listing_price = State()
    waiting_bid_amount = State()
    waiting_search = State()


class AIStates(StatesGroup):
    """حالات الذكاء الاصطناعي"""
    waiting_question = State()
    waiting_book_content = State()


# ==========================================
# Market Handlers - معالجات السوق
# ==========================================

@router.message(F.text == "🏪 السوق")
async def market_menu(message: Message):
    """قائمة السوق"""
    ensure_user(
        message.from_user.id,
        message.from_user.username,
        message.from_user.first_name,
        message.from_user.last_name
    )

    text = "🏪 مرحباً بك في السوق!\n\nهنا يمكنك شراء وبيع الكتب."
    keyboard = get_market_keyboard()

    await message.answer(text, reply_markup=keyboard)


@router.callback_query(F.data == "market_browse")
async def callback_market_browse(callback: CallbackQuery):
    """تصفح السوق"""
    db = SessionLocal()
    try:
        service = MarketService(db)
        listings = service.get_available_listings(limit=20)

        if not listings:
            await callback.message.edit_text(
                "📭 لا توجد قوائم متاحة حالياً",
                reply_markup=get_market_keyboard()
            )
            return

        text = "🛒 القوائم المتاحة:\n\n"
        for listing in listings:
            text += f"📖 {listing['book_title'][:30]}...\n"
            text += f"💰 السعر: {listing['price']} نقطة\n\n"

        keyboard = InlineKeyboardMarkup(inline_keyboard=[])
        for listing in listings[:10]:
            keyboard.inline_keyboard.append([
                InlineKeyboardButton(
                    text=f"📖 {listing['book_title'][:20]} - {listing['price']}💰",
                    callback_data=f"market_view_{listing['id']}"
                )
            ])
        keyboard.inline_keyboard.append([
            InlineKeyboardButton(text="🔙 رجوع", callback_data="market_menu")
        ])

        await callback.message.edit_text(text, reply_markup=keyboard)
    finally:
        db.close()


@router.callback_query(F.data.startswith("market_view_"))
async def callback_market_view(callback: CallbackQuery):
    """عرض قائمة السوق"""
    listing_id = int(callback.data.split("_")[-1])

    db = SessionLocal()
    try:
        service = MarketService(db)
        listing = service.get_listing(listing_id)

        if not listing:
            await callback.answer("القائمة غير موجودة", show_alert=True)
            return

        text = f"""
📖 {listing['book_title']}

✍️ المؤلف: {listing['author_name']}
💰 السعر: {listing['price']} نقطة
📦 الحالة: {listing['condition'].value if hasattr(listing['condition'], 'value') else listing['condition']}
📅 تاريخ الإضافة: {listing['created_at']}
"""

        user = get_user_from_db(callback.from_user.id)
        is_owner_listing = user and listing['seller_id'] == user.id

        keyboard = get_listing_keyboard(listing_id, is_owner_listing)

        await callback.message.edit_text(text, reply_markup=keyboard)
    finally:
        db.close()


@router.callback_query(F.data.startswith("market_buy_"))
async def callback_market_buy(callback: CallbackQuery, state: FSMContext):
    """شراء من السوق"""
    listing_id = int(callback.data.split("_")[-1])

    db = SessionLocal()
    try:
        service = MarketService(db)
        user_service = UserService(db)

        user = user_service.get_user_by_telegram_id(callback.from_user.id)
        if not user:
            await callback.answer("الرجاء التسجيل أولاً", show_alert=True)
            return

        listing = service.get_listing(listing_id)
        if not listing:
            await callback.answer("القائمة غير موجودة", show_alert=True)
            return

        if listing['seller_id'] == user.id:
            await callback.answer("لا يمكنك شراء قائمة خاصة بك", show_alert=True)
            return

        # التحقق من الرصيد
        from app.services.points_service import PointsService
        points_service = PointsService(db)
        user_points = points_service.get_user_points(user.id)

        if not user_points or user_points.current_balance < listing['price']:
            await callback.answer("نقاطك غير كافية", show_alert=True)
            return

        # تأكيد الشراء
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="✅ تأكيد الشراء", callback_data=f"confirm_buy_{listing_id}")],
            [InlineKeyboardButton(text="❌ إلغاء", callback_data=f"market_view_{listing_id}")]
        ])

        await callback.message.edit_text(
            f"🛒 هل تريد شراء هذا الكتاب بـ {listing['price']} نقطة؟",
            reply_markup=keyboard
        )
    finally:
        db.close()


@router.callback_query(F.data.startswith("confirm_buy_"))
async def callback_confirm_buy(callback: CallbackQuery):
    """تأكيد الشراء"""
    listing_id = int(callback.data.split("_")[-1])

    db = SessionLocal()
    try:
        service = MarketService(db)
        user_service = UserService(db)

        user = user_service.get_user_by_telegram_id(callback.from_user.id)
        result = service.purchase(listing_id, user.id)

        if result:
            await callback.answer("✅ تم الشراء بنجاح!", show_alert=True)
            await callback.message.edit_text(
                "🎉 تهانينا! تم الشراء بنجاح.\nسيساعدك البائع على استلام الكتاب.",
                reply_markup=get_market_keyboard()
            )
        else:
            await callback.answer("فشل الشراء، حاول مرة أخرى", show_alert=True)
    finally:
        db.close()


@router.callback_query(F.data == "market_purchases")
async def callback_market_purchases(callback: CallbackQuery):
    """مشتريات المستخدم"""
    db = SessionLocal()
    try:
        service = MarketService(db)
        user_service = UserService(db)

        user = user_service.get_user_by_telegram_id(callback.from_user.id)
        if not user:
            await callback.answer("الرجاء التسجيل أولاً", show_alert=True)
            return

        purchases = service.get_user_purchases(user.id, limit=20)

        if not purchases:
            await callback.message.edit_text(
                "📭 لا توجد مشتريات سابقة",
                reply_markup=get_market_keyboard()
            )
            return

        text = "📦 مشترياتك:\n\n"
        for purchase in purchases:
            text += f"📖 {purchase['book_title']}\n"
            text += f"💰 السعر: {purchase['amount']} نقطة\n\n"

        await callback.message.edit_text(text, reply_markup=get_market_keyboard())
    finally:
        db.close()


@router.callback_query(F.data == "market_sales")
async def callback_market_sales(callback: CallbackQuery):
    """مبيعات المستخدم"""
    db = SessionLocal()
    try:
        service = MarketService(db)
        user_service = UserService(db)

        user = user_service.get_user_by_telegram_id(callback.from_user.id)
        if not user:
            await callback.answer("الرجاء التسجيل أولاً", show_alert=True)
            return

        sales = service.get_user_sales(user.id, limit=20)

        if not sales:
            await callback.message.edit_text(
                "📭 لا توجد مبيعات سابقة",
                reply_markup=get_market_keyboard()
            )
            return

        text = "💰 مبيعاتك:\n\n"
        for sale in sales:
            text += f"📖 {sale['book_title']}\n"
            text += f"💰 السعر: {sale['amount']} نقطة\n\n"

        await callback.message.edit_text(text, reply_markup=get_market_keyboard())
    finally:
        db.close()


@router.callback_query(F.data == "market_menu")
async def callback_market_menu(callback: CallbackQuery):
    """العودة لقائمة السوق"""
    text = "🏪 السوق"
    keyboard = get_market_keyboard()
    await callback.message.edit_text(text, reply_markup=keyboard)


# ==========================================
# Challenges Handlers - معالجات التحديات
# ==========================================

@router.message(F.text == "🏆 التحديات")
async def challenges_menu(message: Message):
    """قائمة التحديات"""
    ensure_user(
        message.from_user.id,
        message.from_user.username,
        message.from_user.first_name,
        message.from_user.last_name
    )

    text = "🏆 مرحباً بك في التحديات!\n\nاكسب الشارات والمكافآت من خلال إكمال التحديات."
    keyboard = get_challenges_keyboard()

    await message.answer(text, reply_markup=keyboard)


@router.callback_query(F.data == "challenges_available")
async def callback_challenges_available(callback: CallbackQuery):
    """التحديات المتاحة"""
    db = SessionLocal()
    try:
        service = ChallengeService(db)
        user_service = UserService(db)

        user = user_service.get_user_by_telegram_id(callback.from_user.id)
        if not user:
            await callback.answer("الرجاء التسجيل أولاً", show_alert=True)
            return

        challenges = service.get_available_challenges(user.id)

        if not challenges:
            await callback.message.edit_text(
                "📭 لا توجد تحديات متاحة حالياً",
                reply_markup=get_challenges_keyboard()
            )
            return

        text = "🏆 التحديات المتاحة:\n\n"
        for challenge in challenges:
            text += f"📌 {challenge['title']}\n"
            text += f"💰 المكافأة: {challenge['points_reward']} نقطة\n"
            text += f"⏰ المدة: {challenge.get('duration_days', 'غير محدد')} يوم\n\n"

        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔙 رجوع", callback_data="challenges_menu")]
        ])
        await callback.message.edit_text(text, reply_markup=keyboard)
    finally:
        db.close()


@router.callback_query(F.data == "challenges_active")
async def callback_challenges_active(callback: CallbackQuery):
    """تحدياتي النشطة"""
    db = SessionLocal()
    try:
        service = ChallengeService(db)
        user_service = UserService(db)

        user = user_service.get_user_by_telegram_id(callback.from_user.id)
        if not user:
            await callback.answer("الرجاء التسجيل أولاً", show_alert=True)
            return

        participations = service.get_active_challenges(user.id)

        if not participations:
            await callback.message.edit_text(
                "📭 لا توجد تحديات نشطة",
                reply_markup=get_challenges_keyboard()
            )
            return

        text = "📋 تحدياتك النشطة:\n\n"
        for p in participations:
            text += f"📌 {p['challenge_title']}\n"
            text += f"📊 التقدم: {p['progress']}/{p['target']}\n\n"

        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔙 رجوع", callback_data="challenges_menu")]
        ])
        await callback.message.edit_text(text, reply_markup=keyboard)
    finally:
        db.close()


@router.callback_query(F.data == "challenges_badges")
async def callback_challenges_badges(callback: CallbackQuery):
    """شارات المستخدم"""
    db = SessionLocal()
    try:
        service = ChallengeService(db)
        user_service = UserService(db)

        user = user_service.get_user_by_telegram_id(callback.from_user.id)
        if not user:
            await callback.answer("الرجاء التسجيل أولاً", show_alert=True)
            return

        badges = service.get_user_badges(user.id)

        if not badges:
            await callback.message.edit_text(
                "🎖️ لم تحصل على أي شارات بعد!\nأكمل التحديات لكسب الشارات.",
                reply_markup=get_challenges_keyboard()
            )
            return

        text = "🎖️ شاراتك:\n\n"
        for badge in badges:
            text += f"🏅 {badge['name']}\n"
            text += f"📝 {badge['description']}\n\n"

        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔙 رجوع", callback_data="challenges_menu")]
        ])
        await callback.message.edit_text(text, reply_markup=keyboard)
    finally:
        db.close()


@router.callback_query(F.data == "challenges_stats")
async def callback_challenges_stats(callback: CallbackQuery):
    """إحصائيات التحديات"""
    db = SessionLocal()
    try:
        service = ChallengeService(db)
        user_service = UserService(db)

        user = user_service.get_user_by_telegram_id(callback.from_user.id)
        if not user:
            await callback.answer("الرجاء التسجيل أولاً", show_alert=True)
            return

        stats = service.get_challenge_stats(user.id)

        text = f"""
📊 إحصائيات التحديات:

🏆 التحديات المكتملة: {stats.get('completed', 0)}
📋 التحديات النشطة: {stats.get('active', 0)}
🎖️ الشارات: {stats.get('badges_count', 0)}
🔥 التسلسل الحالي: {stats.get('current_streak', 0)}
📈 أطول تسلسل: {stats.get('longest_streak', 0)}
"""

        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔙 رجوع", callback_data="challenges_menu")]
        ])
        await callback.message.edit_text(text, reply_markup=keyboard)
    finally:
        db.close()


@router.callback_query(F.data == "challenges_leaderboard")
async def callback_challenges_leaderboard(callback: CallbackQuery):
    """لوحة المتصدرين"""
    db = SessionLocal()
    try:
        service = ChallengeService(db)

        leaderboard = service.get_leaderboard("weekly", limit=10)

        if not leaderboard:
            await callback.message.edit_text(
                "📭 لا توجد بيانات بعد",
                reply_markup=get_challenges_keyboard()
            )
            return

        medals = ["🥇", "🥈", "🥉"]
        text = "🥇 لوحة المتصدرين الأسبوعية:\n\n"

        for i, entry in enumerate(leaderboard):
            medal = medals[i] if i < 3 else f"{i+1}."
            text += f"{medal} {entry.get('user_name', 'مستخدم')}: {entry.get('score', 0)} نقطة\n"

        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔙 رجوع", callback_data="challenges_menu")]
        ])
        await callback.message.edit_text(text, reply_markup=keyboard)
    finally:
        db.close()


@router.callback_query(F.data == "challenges_streak")
async def callback_challenges_streak(callback: CallbackQuery):
    """التسلسل اليومي"""
    db = SessionLocal()
    try:
        service = ChallengeService(db)
        user_service = UserService(db)

        user = user_service.get_user_by_telegram_id(callback.from_user.id)
        if not user:
            await callback.answer("الرجاء التسجيل أولاً", show_alert=True)
            return

        streak = service.update_daily_streak(user.id)

        text = f"""
🔥 التسلسل اليومي:

📅 التسلسل الحالي: {streak.current_streak} يوم
🏆 أطول تسلسل: {streak.longest_streak} يوم
⚡ المضاعف: {streak.streak_bonus_multiplier}x
"""

        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔙 رجوع", callback_data="challenges_menu")]
        ])
        await callback.message.edit_text(text, reply_markup=keyboard)
    finally:
        db.close()


@router.callback_query(F.data == "challenges_menu")
async def callback_challenges_menu(callback: CallbackQuery):
    """العودة لقائمة التحديات"""
    text = "🏆 التحديات"
    keyboard = get_challenges_keyboard()
    await callback.message.edit_text(text, reply_markup=keyboard)


# ==========================================
# AI Assistant Handlers - معالجات الذكاء الاصطناعي
# ==========================================

@router.message(F.text == "🤖 مساعد AI")
async def ai_menu(message: Message):
    """قائمة مساعد AI"""
    ensure_user(
        message.from_user.id,
        message.from_user.username,
        message.from_user.first_name,
        message.from_user.last_name
    )

    text = "🤖 مرحباً! أنا مساعدك الذكي.\n\nيمكنني مساعدتك في:"
    keyboard = get_ai_features_keyboard()

    await message.answer(text, reply_markup=keyboard)


@router.callback_query(F.data == "ai_question")
async def callback_ai_question(callback: CallbackQuery, state: FSMContext):
    """سؤال عن الكتاب"""
    await callback.message.edit_text(
        "📖 أرسل لي نص الكتاب أو ملخصه، ثم اطرح سؤالك.",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔙 رجوع", callback_data="ai_menu")]
        ])
    )
    await state.set_state(AIStates.waiting_book_content)


@router.callback_query(F.data == "ai_menu")
async def callback_ai_menu(callback: CallbackQuery):
    """العودة لقائمة AI"""
    text = "🤖 مساعد الذكاء الاصطناعي"
    keyboard = get_ai_features_keyboard()
    await callback.message.edit_text(text, reply_markup=keyboard)


# ==========================================
# Referral Handlers - معالجات الإحالة
# ==========================================

@router.message(F.text == "🎯 الإحالة")
async def referral_menu(message: Message):
    """قائمة الإحالة"""
    ensure_user(
        message.from_user.id,
        message.from_user.username,
        message.from_user.first_name,
        message.from_user.last_name
    )

    text = "🎯 نظام الإحالة!\n\nادعُ أصدقاءك واحصل على مكافآت."
    keyboard = get_referral_keyboard()

    await message.answer(text, reply_markup=keyboard)


@router.callback_query(F.data == "referral_link")
async def callback_referral_link(callback: CallbackQuery):
    """رابط الإحالة"""
    db = SessionLocal()
    try:
        service = ReferralService(db)
        user_service = UserService(db)

        user = user_service.get_user_by_telegram_id(callback.from_user.id)
        if not user:
            await callback.answer("الرجاء التسجيل أولاً", show_alert=True)
            return

        link = service.get_or_create_referral_link(user.id)

        text = f"""
🔗 رابط الإحالة الخاص بك:

https://t.me/{callback.bot.username}?start={link.code}

📊 الإحصائيات:
• النقرات: {link.total_clicks}
• التسجيلات: {link.total_signups}
"""

        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📤 مشاركة الرابط", switch_inline_query=f"انضم إلى مكتبة الكتب عبر هذا الرابط: https://t.me/{callback.bot.username}?start={link.code}")],
            [InlineKeyboardButton(text="🔙 رجوع", callback_data="referral_menu")]
        ])
        await callback.message.edit_text(text, reply_markup=keyboard)
    finally:
        db.close()


@router.callback_query(F.data == "referral_stats")
async def callback_referral_stats(callback: CallbackQuery):
    """إحصائيات الإحالة"""
    db = SessionLocal()
    try:
        service = ReferralService(db)
        user_service = UserService(db)

        user = user_service.get_user_by_telegram_id(callback.from_user.id)
        if not user:
            await callback.answer("الرجاء التسجيل أولاً", show_alert=True)
            return

        stats = service.get_referral_stats(user.id)

        text = f"""
📊 إحصائيات الإحالة:

👥 المحيلين المباشر: {stats.get('direct_referrals', 0)}
👥 إجمالي المحيلين: {stats.get('total_referrals', 0)}
💰 إجمالي الأرباح: {stats.get('total_earnings', 0)} نقطة
🎖️ الشارات: {stats.get('badges_count', 0)}
"""

        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔙 رجوع", callback_data="referral_menu")]
        ])
        await callback.message.edit_text(text, reply_markup=keyboard)
    finally:
        db.close()


@router.callback_query(F.data == "referral_earnings")
async def callback_referral_earnings(callback: CallbackQuery):
    """أرباح الإحالة"""
    db = SessionLocal()
    try:
        service = ReferralService(db)
        user_service = UserService(db)

        user = user_service.get_user_by_telegram_id(callback.from_user.id)
        if not user:
            await callback.answer("الرجاء التسجيل أولاً", show_alert=True)
            return

        earnings = service.get_referral_earnings(user.id)

        text = "💰 أرباح الإحالة:\n\n"
        for earning in earnings:
            text += f"📌 من المحيل رقم: {earning.get('referred_id', 'N/A')}\n"
            text += f"💰 المبلغ: {earning.get('amount', 0)} نقطة\n\n"

        if not earnings:
            text = "📭 لا توجد أرباح بعد.\nقم بدعوة أصدقاءك لكسب المكافآت!"

        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔙 رجوع", callback_data="referral_menu")]
        ])
        await callback.message.edit_text(text, reply_markup=keyboard)
    finally:
        db.close()


@router.callback_query(F.data == "referral_menu")
async def callback_referral_menu(callback: CallbackQuery):
    """العودة لقائمة الإحالة"""
    text = "🎯 الإحالة"
    keyboard = get_referral_keyboard()
    await callback.message.edit_text(text, reply_markup=keyboard)


# ==========================================
# Notifications Handlers - معالجات الإشعارات
# ==========================================

@router.message(F.text == "📬 إشعاراتي")
async def notifications_menu(message: Message):
    """قائمة الإشعارات"""
    ensure_user(
        message.from_user.id,
        message.from_user.username,
        message.from_user.first_name,
        message.from_user.last_name
    )

    text = "📬 إشعاراتك"
    keyboard = get_notifications_keyboard()

    await message.answer(text, reply_markup=keyboard)


@router.callback_query(F.data == "notifications_all")
async def callback_notifications_all(callback: CallbackQuery):
    """جميع الإشعارات"""
    db = SessionLocal()
    try:
        service = NotificationService(db)
        user_service = UserService(db)

        user = user_service.get_user_by_telegram_id(callback.from_user.id)
        if not user:
            await callback.answer("الرجاء التسجيل أولاً", show_alert=True)
            return

        notifications = service.get_user_notifications(user.id, limit=20)

        if not notifications:
            await callback.message.edit_text(
                "📭 لا توجد إشعارات",
                reply_markup=get_notifications_keyboard()
            )
            return

        text = "📬 إشعاراتك:\n\n"
        for notif in notifications:
            status = "🔵" if not notif.get('is_read') else "⚪"
            text += f"{status} {notif.get('title', 'إشعار')}\n"
            text += f"   {notif.get('message', '')[:50]}...\n\n"

        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="✅ تحديد الكل كمقروء", callback_data="notifications_mark_all")],
            [InlineKeyboardButton(text="🔙 رجوع", callback_data="notifications_menu")]
        ])
        await callback.message.edit_text(text, reply_markup=keyboard)
    finally:
        db.close()


@router.callback_query(F.data == "notifications_unread")
async def callback_notifications_unread(callback: CallbackQuery):
    """الإشعارات غير المقروءة"""
    db = SessionLocal()
    try:
        service = NotificationService(db)
        user_service = UserService(db)

        user = user_service.get_user_by_telegram_id(callback.from_user.id)
        if not user:
            await callback.answer("الرجاء التسجيل أولاً", show_alert=True)
            return

        notifications = service.get_user_notifications(user.id, unread_only=True, limit=20)
        count = service.get_unread_count(user.id)

        text = f"🔔 لديك {count} إشعارات غير مقروءة:\n\n"
        for notif in notifications:
            text += f"📌 {notif.get('title', 'إشعار')}\n"
            text += f"   {notif.get('message', '')[:50]}...\n\n"

        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="✅ تحديد الكل كمقروء", callback_data="notifications_mark_all")],
            [InlineKeyboardButton(text="🔙 رجوع", callback_data="notifications_menu")]
        ])
        await callback.message.edit_text(text, reply_markup=keyboard)
    finally:
        db.close()


@router.callback_query(F.data == "notifications_mark_all")
async def callback_notifications_mark_all(callback: CallbackQuery):
    """تحديد الكل كمقروء"""
    db = SessionLocal()
    try:
        service = NotificationService(db)
        user_service = UserService(db)

        user = user_service.get_user_by_telegram_id(callback.from_user.id)
        if not user:
            await callback.answer("الرجاء التسجيل أولاً", show_alert=True)
            return

        count = service.mark_all_as_read(user.id)
        await callback.answer(f"✅ تم تحديد {count} إشعارات كمقروءة", show_alert=True)

        keyboard = get_notifications_keyboard()
        await callback.message.edit_text("📬 تم تحديث الإشعارات", reply_markup=keyboard)
    finally:
        db.close()


@router.callback_query(F.data == "notifications_stats")
async def callback_notifications_stats(callback: CallbackQuery):
    """إحصائيات الإشعارات"""
    db = SessionLocal()
    try:
        service = NotificationService(db)
        user_service = UserService(db)

        user = user_service.get_user_by_telegram_id(callback.from_user.id)
        if not user:
            await callback.answer("الرجاء التسجيل أولاً", show_alert=True)
            return

        stats = service.get_notification_stats(user.id)

        text = f"""
📊 إحصائيات الإشعارات:

📬 الإجمالي: {stats.get('total', 0)}
🔔 غير المقروءة: {stats.get('unread', 0)}
📖 المقروءة: {stats.get('read', 0)}
"""

        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔙 رجوع", callback_data="notifications_menu")]
        ])
        await callback.message.edit_text(text, reply_markup=keyboard)
    finally:
        db.close()


@router.callback_query(F.data == "notifications_menu")
async def callback_notifications_menu(callback: CallbackQuery):
    """العودة لقائمة الإشعارات"""
    text = "📬 إشعاراتي"
    keyboard = get_notifications_keyboard()
    await callback.message.edit_text(text, reply_markup=keyboard)


# ==========================================
# Helper Functions
# ==========================================

def get_user_from_db(telegram_id: int):
    """الحصول على المستخدم من قاعدة البيانات"""
    db = SessionLocal()
    try:
        user_service = UserService(db)
        return user_service.get_user_by_telegram_id(telegram_id)
    finally:
        db.close()


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