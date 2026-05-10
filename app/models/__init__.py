"""
Models Module - نماذج قاعدة البيانات
"""
from app.models.user import User
from app.models.book import Book, BookCategory
from app.models.author import Author
from app.models.favorite import Favorite
from app.models.download_history import DownloadHistory
from app.models.channel_setting import ForceJoinChannel, ChannelSetting
from app.models.points import UserPoints, PointsTransaction
from app.models.review import Review
# from app.models.referral import Referral  ⬅️ احذف هذا السطر تماماً
from app.models.coupon import Coupon
from app.models.pack import Pack
from app.models.notification import Notification
from app.models.admin import AdminUser, AdminLog
from app.models.subscription import SubscriptionPlan, UserSubscription
from app.models.social import FollowRelationship, ActivityFeed, ActivityType

# Marketplace Models
from app.models.market import (
    MarketListing,
    AuctionBid,
    MarketTransaction,
    Wishlist,
    PriceHistory,
)

# Recommendations Models
from app.models.recommendations import (
    UserBehavior,
    UserPreference,
    Recommendation,
    ReadingHistory,
    UserSegment,
)

# Referral System Models
from app.models.referral_system import (
    Referral,                # ✅ أضف هذا الاستيراد
    ReferralCode,
    ReferralSettings,
    ReferralEarning,
    ReferralBadge,
    ReferralLevel,
    ReferralLink,            # يمكن إضافتها إن احتجتها لاحقاً
    ReferralEvent,           # يمكن إضافتها إن احتجتها لاحقاً
    UserReferralBadge,
)

# Challenges Models
from app.models.challenges import (
    Challenge,
    ChallengeParticipation,
    Badge,
    Milestone,
    DailyStreak,
    Leaderboard,
)


# Security Models
from app.models.security import (
    AuditLog,
    SecurityEvent,
    RateLimit,
    IPBlacklist,
)
from app.models.notification import (
    Notification,
    SmartNotification,
    UserNotificationSettings,
    NotificationTemplate,
    NotificationSchedule,
    NotificationAnalytics,
    NotificationPreference,
)
__all__ = [
    "User",
    "Book",
    "BookCategory",
    "Author",
    "Favorite",
    "DownloadHistory",
    "ForceJoinChannel",
    "ChannelSetting",
    "UserPoints",
    "PointsTransaction",
    "Review",
    "Referral",
    "Coupon",
    "Pack",
    "Notification",
    "AdminUser",
    "AdminLog",
    # Marketplace
    "MarketListing",
    "AuctionBid",
    "MarketTransaction",
    "Wishlist",
    "PriceHistory",
    # Recommendations
    "UserBehavior",
    "UserPreference",
    "Recommendation",
    "ReadingHistory",
    "UserSegment",
    # Referral System
    "ReferralCode",
    "ReferralSettings",
    "ReferralEarning",
    "ReferralBadge",
    "ReferralLevel",
    # Challenges
    "Challenge",
    "ChallengeParticipation",
    "Badge",
    "Milestone",
    "DailyStreak",
    "Leaderboard",
    # Smart Notifications
    "NotificationTemplate",
    "UserNotificationSettings",
    "SubscriptionPlan",
    "UserSubscription",
    "FollowRelationship",
    "ActivityFeed",
    "ActivityType",
    # Security
    "AuditLog",
    "SecurityEvent",
    "RateLimit",
    "IPBlacklist",
]
