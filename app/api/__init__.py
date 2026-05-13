"""
API Module - واجهات برمجة التطبيقات
"""
from app.api.users import router as users_router
from app.api.books import router as books_router
from app.api.categories import router as categories_router
from app.api.search import router as search_router
from app.api.subscriptions import router as subscriptions_router
from app.api.points import router as points_router
from app.api.admin import router as admin_router
from app.api.referral import router as referral_router
from app.api.analytics import router as analytics_router
from app.api.ai import router as ai_router
from app.api.market import router as market_router
from app.api.recommendations import router as recommendations_router
from app.api.challenges import router as challenges_router
from app.api.notifications import router as notifications_router
from app.api.social import router as social_router

__all__ = [
    "users_router",
    "books_router",
    "categories_router",
    "search_router",
    "subscriptions_router",
    "points_router",
    "admin_router",
    "referral_router",
    "analytics_router",
    "ai_router",
    "market_router",
    "recommendations_router",
    "challenges_router",
    "notifications_router",
    "social_router",
]
