"""
Smart Books Library Bot - Main Entry Point
FastAPI + Telegram Bot Integration with Lifecycle Management
"""
import asyncio
import os
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.redis import RedisStorage
from aiogram.fsm.storage.memory import MemoryStorage
from config.settings import get_settings
from app.database import init_db, engine, Base
from app.bot.handlers_router import handlers_router
from app.bot.handlers_features import ForceJoinMiddleware, RateLimitMiddleware

# Import API routers
from app.api import (
    books, users, points, reviews, search,
    categories, subscriptions, admin,
    referral, analytics, ai,
    market, recommendations, challenges, notifications,
    social
)

# إعداد السجلات
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

try:
    settings = get_settings()
except Exception as e:
    logger.error(f"Failed to load settings: {e}")
    raise

# إنشاء كائنات البوت
bot = None
dp = None
bot_task = None


async def start_bot():
    try:
        global bot, dp
        # ... باقي الكود ...
    except Exception as e:
        logger.error(f"Bot failed to start: {e}", exc_info=True)
    # اختيار التخزين
    if settings.redis_url:
        try:
            storage = RedisStorage.from_url(settings.redis_url)
            logger.info("Using Redis storage")
        except Exception as e:
            logger.warning(f"Failed to connect to Redis: {e}, falling back to MemoryStorage")
            storage = MemoryStorage()
    else:
        storage = MemoryStorage()
        logger.info("Using Memory storage")

    bot = Bot(token=settings.telegram_bot_token)
    dp = Dispatcher(storage=storage)
    dp.update.middleware(RateLimitMiddleware())
    dp.update.middleware(ForceJoinMiddleware())
    dp.include_router(handlers_router)

    logger.info("Starting Telegram Bot...")
    logger.info(f"Bot token: {'*' * 10}...{settings.telegram_bot_token[-4:] if settings.telegram_bot_token else 'None'}")
    logger.info(f"Admin ID: {settings.telegram_admin_id}")
    logger.info(f"Redis URL: {'*' * 10}...{settings.redis_url[-4:] if settings.redis_url else 'None'}")
    await dp.start_polling(bot)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """إدارة دورة حياة التطبيق"""
    global bot_task

    # ========== Startup ==========
    logger.info("Starting application...")

    # تهيئة قاعدة البيانات
    logger.info("Initializing database...")
    try:
        init_db()
        logger.info("Database initialized successfully")
    except Exception as e:
        logger.error(f"Database initialization failed: {e}")

    # بدء البوت في خلفية
    logger.info("Starting bot in background...")
    bot_task = asyncio.create_task(start_bot())

    yield

    # ========== Shutdown ==========
    logger.info("Shutting down application...")

    # إيقاف البوت
    if bot:
        logger.info("Stopping bot...")
        await bot.session.close()

    if bot_task:
        bot_task.cancel()
        try:
            await bot_task
        except asyncio.CancelledError:
            logger.info("Bot task cancelled")

    # إغلاق قاعدة البيانات
    logger.info("Closing database connection...")
    engine.dispose()

    logger.info("Application shutdown complete")


# إنشاء تطبيق FastAPI
app = FastAPI(
    title="Smart Books Library API",
    description="API للمكتبة الرقمية الذكية",
    version="1.0.0",
    lifespan=lifespan
)

# إضافة CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# تسجيل راوترات API
app.include_router(books.router, prefix="/api")
app.include_router(users.router, prefix="/api")
app.include_router(points.router, prefix="/api")
app.include_router(reviews.router, prefix="/api")
app.include_router(search.router, prefix="/api")
app.include_router(categories.router, prefix="/api")
app.include_router(subscriptions.router, prefix="/api")
app.include_router(admin.router, prefix="/api")
app.include_router(referral.router, prefix="/api")
app.include_router(analytics.router, prefix="/api")
app.include_router(ai.router, prefix="/api")
app.include_router(market.router, prefix="/api")
app.include_router(recommendations.router, prefix="/api")
app.include_router(challenges.router, prefix="/api")
app.include_router(notifications.router, prefix="/api")
app.include_router(social.router, prefix="/api")

@app.get("/")
def root():
    """ الصفحة الرئيسية """
    return {
        "name": "Smart Books Library API",
        "version": "1.0.0",
        "status": "running"
    }


@app.get("/health")
def health_check():
    """فحص حالة التطبيق"""
    return {
        "status": "healthy",
        "database": "connected",
        "bot": "running" if bot else "stopped"
    }


@app.get("/stats")
def get_stats():
    """إحصائيات سريعة"""
    from app.database import SessionLocal
    from app.services.book_service import BookService
    from app.services.user_service import UserService

    db = SessionLocal()
    try:
        book_service = BookService(db)
        user_service = UserService(db)

        return {
            "books": book_service.get_statistics(),
            "users": user_service.get_statistics()
        }
    finally:
        db.close()


# نقطة الوصول للبوت (للاستخدام الداخلي)
def get_bot() -> Bot:
    """الحصول على كائن البوت"""
    return bot


def get_dp() -> Dispatcher:
    """الحصول على كائن Dispatcher"""
    return dp


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host=settings.fastapi_host,
        port=settings.fastapi_port,
        reload=settings.debug,
        log_level=settings.log_level.lower()
    )
