"""
Handlers Module - المعالجات الأساسية
معالجات بسيطة للأوامر العامة
"""
from aiogram import Router
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from app.database import SessionLocal
from app.services.user_service import UserService
from app.services.channel_service import ChannelService
from app.bot.keyboards import get_main_menu_enhanced_keyboard

router = Router()


class UploadStates(StatesGroup):
    """حالات رفع الكتاب"""
    waiting_title = State()
    waiting_description = State()
    waiting_file = State()



@router.message(Command("start"))
async def cmd_start(message: Message, state: FSMContext):
    """أمر البداية"""
    db = SessionLocal()
    try:
        user_service = UserService(db)
        user_service.get_or_create_user(
            telegram_id=message.from_user.id,
            username=message.from_user.username,
            first_name=message.from_user.first_name,
            last_name=message.from_user.last_name
        )

        channel_service = ChannelService(db)
        is_subscribed, not_subscribed = True, []
        if message.bot is not None:
            is_subscribed, not_subscribed = await channel_service.check_all_subscriptions(message.bot, message.from_user.id)

        if not is_subscribed:
            keyboard = InlineKeyboardMarkup(inline_keyboard=[])
            for channel in not_subscribed:
                if channel.channel_link:
                    keyboard.inline_keyboard.append([
                        InlineKeyboardButton(
                            text=f"📢 الانضمام لـ {channel.channel_name or channel.channel_id}",
                            url=channel.channel_link,
                        )
                    ])
            keyboard.inline_keyboard.append([
                InlineKeyboardButton(text="✅ تم الاشتراك", callback_data="check_subscription")
            ])
            channels_text = "\n".join(
                f"• {channel.channel_name or channel.channel_id}" for channel in not_subscribed
            ) or "• لا توجد قنوات محددة حالياً"
            await message.answer(
                f"⚠️ يجب الاشتراك بالقنوات التالية أولاً:\n\n{channels_text}",
                reply_markup=keyboard,
            )
            return

        welcome_text = """
🎉 **مرحباً بك في مكتبة Smart Books!**

📚 **الميزات الرئيسية:**
• 🌟 آلاف الكتب المجانية
• 🔍 بحث ذكي وسريع
• 📖 قراءة وتحميل فوري
• ⭐ تقييم ومراجعات
• ❤️ إضافة للمفضلة

🚀 **الميزات المتقدمة:**
• 🏪 سوق الكتب للبيع والشراء
• 🤖 مساعد AI للتوصيات
• 🏆 نظام التحديات والشارات
• 💰 نظام النقاط والمكافآت
• 👥 نظام الإحالة

💡 **كيفية البدء:**
اختر من الأزرار أدناه أو اكتب أمر للبدء!
        """

        await message.answer(
            welcome_text,
            reply_markup=get_main_menu_enhanced_keyboard(True if user_service.is_owner(message.from_user.id) else False)
        )
    finally:
        db.close()

@router.message(Command("help"))
async def cmd_help(message: Message):
    """أمر المساعدة"""
    help_text = """
📚 أوامر البوت:

📚 تصفح الكتب - استعرض مكتبة الكتب
🔍 بحث - ابحث عن كتاب
🏪 السوق - سوق الكتب للشراء والبيع
🤖 مساعد AI - مساعد ذكي للأسئلة
👤 ملفي الشخصي - معلومات حسابك
🎁 نقاطي - رصيد نقاطك
🏆 التحديات - تحديات وشارات
🎯 الإحالة - ادعُ أصدقاءك
📬 إشعاراتي - إشعاراتك
❤️ المفضلة - كتبك المفضلة
📥 سجل التحميلات - آخر ما حمّلته
⚙️ الإعدادات - إعداداتك

💡 نصائح:
• استخدم الأزرار للتوجيه السريع
• شارك رابط الإحالة مع أصدقائك للحصول على نقاط
• أكمل التحديات لكسب الشارات
• تابع التسلسل اليومي لمضاعفة النقاط
    """
    await message.answer(help_text)


@router.message(Command("cancel"))
async def cmd_cancel(message: Message, state: FSMContext):
    """إلغاء العملية الحالية"""
    current_state = await state.get_state()
    if current_state is None:
        await message.answer("لا توجد عملية لإلغائها.")
        return

    await state.clear()
    await message.answer("تم الإلغاء. اختر من القائمة الرئيسية.")
