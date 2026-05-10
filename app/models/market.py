"""
Market Models - نماذج السوق الداخلي
نظام بيع وشراء الكتب
"""
import enum
from datetime import datetime
from sqlalchemy import Column, Integer, String, Enum, DateTime, Boolean, Text, Float, ForeignKey, JSON
from sqlalchemy.orm import relationship
from app.database import Base


class TransactionType(enum.Enum):
    """نوع المعاملة في السوق"""
    PURCHASE = "purchase"      # شراء بنقاط
    SALE = "sale"              # بيع
    EXCHANGE = "exchange"      # تبادل
    AUCTION = "auction"        # مزاد
    GIFT = "gift"             # هدية


class TransactionStatus(enum.Enum):
    """حالة المعاملة"""
    PENDING = "pending"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    DISPUTED = "disputed"


class MarketListing(Base):
    """قائمة الكتاب في السوق"""
    __tablename__ = "market_listings"

    id = Column(Integer, primary_key=True, index=True)
    book_id = Column(Integer, ForeignKey("books.id"), nullable=False)
    seller_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    # معلومات التسعير
    price_points = Column(Integer, nullable=True)  # السعر بالنقاط
    price_coins = Column(Integer, nullable=True)    # السعر بالكوكoins
    is_auction = Column(Boolean, default=False)
    auction_end_time = Column(DateTime, nullable=True)
    starting_price = Column(Integer, nullable=True)

    # حالة البيع
    is_available = Column(Boolean, default=True)
    is_featured = Column(Boolean, default=False)

    # وصف البيع
    description = Column(Text, nullable=True)
    condition = Column(String(50), default="new")  # new, like_new, good, fair

    # إحصائيات
    view_count = Column(Integer, default=0)
    wishlist_count = Column(Integer, default=0)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    expires_at = Column(DateTime, nullable=True)

    # Relationships
    book = relationship("Book", backref="market_listings")
    seller = relationship("User", backref="listings")
    bids = relationship("AuctionBid", back_populates="listing", cascade="all, delete-orphan")
    transactions = relationship("MarketTransaction", back_populates="listing", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<MarketListing {self.id} book={self.book_id}>"


class AuctionBid(Base):
    """مزاد على كتاب"""
    __tablename__ = "auction_bids"

    id = Column(Integer, primary_key=True, index=True)
    listing_id = Column(Integer, ForeignKey("market_listings.id"), nullable=False)
    bidder_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    amount = Column(Integer, nullable=False)
    is_winning = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    listing = relationship("MarketListing", back_populates="bids")
    bidder = relationship("User", backref="bids")

    def __repr__(self):
        return f"<AuctionBid {self.id} amount={self.amount}>"


class MarketTransaction(Base):
    """معاملة في السوق"""
    __tablename__ = "market_transactions"

    id = Column(Integer, primary_key=True, index=True)
    listing_id = Column(Integer, ForeignKey("market_listings.id"), nullable=False)
    buyer_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    seller_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    transaction_type = Column(Enum(TransactionType), nullable=False)
    status = Column(Enum(TransactionStatus), default=TransactionStatus.PENDING)

    price = Column(Integer, nullable=False)  # السعر المدفوع
    platform_fee = Column(Integer, default=0)  # رسوم المنصة (20%)
    seller_earnings = Column(Integer, default=0)  # أرباح البائع (70%)
    referral_earnings = Column(Integer, default=0)  # أرباح الإحالة (10%)

    completed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # التفاصيل
    extra_data = Column(JSON, nullable=True)  # بيانات إضافية (was 'metadata')
    notes = Column(Text, nullable=True)

    # Relationships
    listing = relationship("MarketListing", back_populates="transactions")
    buyer = relationship("User", foreign_keys=[buyer_id], backref="purchases")
    seller = relationship("User", foreign_keys=[seller_id], backref="sales")

    def __repr__(self):
        return f"<MarketTransaction {self.id} type={self.transaction_type}>"


class Wishlist(Base):
    """قائمة أمنيات السوق"""
    __tablename__ = "market_wishlists"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    book_id = Column(Integer, ForeignKey("books.id"), nullable=False)
    max_price = Column(Integer, nullable=True)  # السعر المطلوب
    notify_price_drop = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    user = relationship("User", backref="market_wishlist")
    book = relationship("Book", backref="wishlist_users")

    def __repr__(self):
        return f"<Wishlist user={self.user_id} book={self.book_id}>"


class PriceHistory(Base):
    """سجل أسعار الكتاب"""
    __tablename__ = "price_history"

    id = Column(Integer, primary_key=True, index=True)
    book_id = Column(Integer, ForeignKey("books.id"), nullable=False)
    min_price = Column(Integer, nullable=True)
    max_price = Column(Integer, nullable=True)
    avg_price = Column(Float, nullable=True)
    recorded_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    book = relationship("Book", backref="price_history")

    def __repr__(self):
        return f"<PriceHistory book={self.book_id}>"
