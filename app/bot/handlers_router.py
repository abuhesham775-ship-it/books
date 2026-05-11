"""
Bot Router - تجميع راوترات البوت
"""
from aiogram import Router
from app.bot.handlers_features import router as main_features_router
from app.bot.handlers_new_features import router as secondary_features_router
from app.bot.handlers import router as old_handlers_router

# دمج الراوترات - الميزات الرئيسية أولاً ثم الميزات الثانوية ثم الأوامر القديمة
combined_router = Router()
combined_router.include_router(main_features_router)
combined_router.include_router(secondary_features_router)
combined_router.include_router(old_handlers_router)

handlers_router = combined_router
