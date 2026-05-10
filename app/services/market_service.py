"""
Market Service - خدمة السوق الداخلي
نظام بيع وشراء الكتب
"""
from typing import List, Optional, Tuple
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import desc, func, or_
from app.models.market import (
    MarketListing, MarketTransaction, AuctionBid, Wishlist,
    TransactionType, TransactionStatus
)
from app.models.book import Book, BookStatus
from app.models.user import User
from config.settings import get_settings

settings = get_settings()


class MarketService:
    """خدمة السوق الداخلي"""

    def __init__(self, db: Session):
        self.db = db

    # ==========================================
    # إدارة القوائم
    # ==========================================

    def create_listing(
        self,
        book_id: int,
        seller_id: int,
        price_points: int = None,
        price_coins: int = None,
        is_auction: bool = False,
        description: str = None,
        condition: str = "new"
    ) -> MarketListing:
        """إنشاء قائمة بيع جديدة"""
        # التحقق من عدم وجود قائمة نشطة للكتاب
        existing = self.db.query(MarketListing).filter(
            MarketListing.book_id == book_id,
            MarketListing.seller_id == seller_id,
            MarketListing.is_available == True
        ).first()

        if existing:
            raise ValueError("لديك قائمة نشطة لهذا الكتاب")

        listing = MarketListing(
            book_id=book_id,
            seller_id=seller_id,
            price_points=price_points,
            price_coins=price_coins,
            is_auction=is_auction,
            description=description,
            condition=condition
        )

        if is_auction:
            listing.auction_end_time = datetime.utcnow() + timedelta(days=7)

        self.db.add(listing)
        self.db.commit()
        self.db.refresh(listing)
        return listing

    def get_listing(self, listing_id: int) -> Optional[MarketListing]:
        """الحصول على قائمة"""
        return self.db.query(MarketListing).filter(
            MarketListing.id == listing_id
        ).first()

    def get_listing_by_book(self, book_id: int) -> Optional[MarketListing]:
        """الحصول على قائمة الكتاب"""
        return self.db.query(MarketListing).filter(
            MarketListing.book_id == book_id,
            MarketListing.is_available == True
        ).first()

    def update_listing(
        self,
        listing_id: int,
        price_points: int = None,
        price_coins: int = None,
        description: str = None
    ) -> Optional[MarketListing]:
        """تحديث قائمة"""
        listing = self.get_listing(listing_id)
        if not listing:
            return None

        if price_points is not None:
            listing.price_points = price_points
        if price_coins is not None:
            listing.price_coins = price_coins
        if description is not None:
            listing.description = description

        self.db.commit()
        self.db.refresh(listing)
        return listing

    def remove_listing(self, listing_id: int, user_id: int) -> bool:
        """حذف قائمة"""
        listing = self.get_listing(listing_id)
        if not listing or listing.seller_id != user_id:
            return False

        listing.is_available = False
        self.db.commit()
        return True

    def get_user_listings(self, user_id: int) -> List[MarketListing]:
        """قوائم المستخدم النشطة"""
        return self.db.query(MarketListing).filter(
            MarketListing.seller_id == user_id,
            MarketListing.is_available == True
        ).order_by(desc(MarketListing.created_at)).all()

    def get_available_listings(
        self,
        limit: int = 20,
        offset: int = 0,
        category_id: int = None
    ) -> List[MarketListing]:
        """الحصول على القوائم المتاحة"""
        query = self.db.query(MarketListing).filter(
            MarketListing.is_available == True
        )

        if category_id:
            query = query.join(Book).filter(Book.category_id == category_id)

        return query.order_by(desc(MarketListing.created_at)).limit(limit).offset(offset).all()

    def get_auctions(self, limit: int = 20) -> List[MarketListing]:
        """الحصول على المزادات النشطة"""
        return self.db.query(MarketListing).filter(
            MarketListing.is_available == True,
            MarketListing.is_auction == True,
            MarketListing.auction_end_time > datetime.utcnow()
        ).order_by(MarketListing.auction_end_time).limit(limit).all()

    def get_featured_listings(self, limit: int = 10) -> List[MarketListing]:
        """الحصول على القوائم المميزة"""
        return self.db.query(MarketListing).filter(
            MarketListing.is_available == True,
            MarketListing.is_featured == True
        ).order_by(desc(MarketListing.view_count)).limit(limit).all()

    # ==========================================
    # المزادات
    # ==========================================

    def place_bid(
        self,
        listing_id: int,
        bidder_id: int,
        amount: int
    ) -> AuctionBid:
        """القيادة على مزاد"""
        listing = self.get_listing(listing_id)
        if not listing or not listing.is_auction:
            raise ValueError("المزاد غير متاح")

        if listing.auction_end_time < datetime.utcnow():
            raise ValueError("انتهى المزاد")

        if listing.seller_id == bidder_id:
            raise ValueError("لا يمكنك المزايدة على كتبك")

        # التحقق من أعلى مزايدة
        highest_bid = self.get_highest_bid(listing_id)
        min_bid = listing.starting_price or 0
        if highest_bid:
            min_bid = highest_bid.amount

        if amount <= min_bid:
            raise ValueError(f"يجب أن تكون المزايدة أعلى من {min_bid}")

        # إلغاء المزايدة السابقة الفائزة
        self.db.query(AuctionBid).filter(
            AuctionBid.listing_id == listing_id,
            AuctionBid.is_winning == True
        ).update({"is_winning": False})

        # إنشاء المزايدة الجديدة
        bid = AuctionBid(
            listing_id=listing_id,
            bidder_id=bidder_id,
            amount=amount,
            is_winning=True
        )
        self.db.add(bid)
        self.db.commit()
        self.db.refresh(bid)
        return bid

    def get_highest_bid(self, listing_id: int) -> Optional[AuctionBid]:
        """الحصول على أعلى مزايدة"""
        return self.db.query(AuctionBid).filter(
            AuctionBid.listing_id == listing_id,
            AuctionBid.is_winning == True
        ).first()

    def get_listing_bids(self, listing_id: int) -> List[AuctionBid]:
        """جميع المزايدات"""
        return self.db.query(AuctionBid).filter(
            AuctionBid.listing_id == listing_id
        ).order_by(desc(AuctionBid.amount)).all()

    def end_auction(self, listing_id: int) -> Tuple[bool, Optional[MarketTransaction]]:
        """إنهاء المزاد"""
        listing = self.get_listing(listing_id)
        if not listing or not listing.is_auction:
            return False, None

        winning_bid = self.get_highest_bid(listing_id)
        if not winning_bid:
            listing.is_available = False
            self.db.commit()
            return True, None

        # إنشاء المعاملة
        transaction = self.process_purchase(
            listing_id=listing_id,
            buyer_id=winning_bid.bidder_id,
            seller_id=listing.seller_id,
            amount=winning_bid.amount,
            transaction_type=TransactionType.AUCTION
        )

        listing.is_available = False
        self.db.commit()

        return True, transaction

    # ==========================================
    # المعاملات
    # ==========================================

    def process_purchase(
        self,
        listing_id: int,
        buyer_id: int,
        seller_id: int,
        amount: int,
        transaction_type: TransactionType = TransactionType.PURCHASE
    ) -> MarketTransaction:
        """معالجة عملية شراء"""
        # حساب العمولات
        platform_fee = int(amount * 0.20)  # 20% للمنصة
        referral_earnings = int(amount * 0.10)  # 10% للإحالة
        seller_earnings = amount - platform_fee - referral_earnings  # 70% للبائع

        transaction = MarketTransaction(
            listing_id=listing_id,
            buyer_id=buyer_id,
            seller_id=seller_id,
            transaction_type=transaction_type,
            price=amount,
            platform_fee=platform_fee,
            seller_earnings=seller_earnings,
            referral_earnings=referral_earnings,
            status=TransactionStatus.COMPLETED,
            completed_at=datetime.utcnow()
        )

        self.db.add(transaction)

        # تحديث قائمة السوق
        listing = self.get_listing(listing_id)
        if listing:
            listing.is_available = False

        self.db.commit()
        self.db.refresh(transaction)
        return transaction

    def get_user_purchases(self, user_id: int, limit: int = 20) -> List[MarketTransaction]:
        """مشتريات المستخدم"""
        return self.db.query(MarketTransaction).filter(
            MarketTransaction.buyer_id == user_id,
            MarketTransaction.status == TransactionStatus.COMPLETED
        ).order_by(desc(MarketTransaction.completed_at)).limit(limit).all()

    def get_user_sales(self, user_id: int, limit: int = 20) -> List[MarketTransaction]:
        """مبيعات المستخدم"""
        return self.db.query(MarketTransaction).filter(
            MarketTransaction.seller_id == user_id,
            MarketTransaction.status == TransactionStatus.COMPLETED
        ).order_by(desc(MarketTransaction.completed_at)).limit(limit).all()

    def get_platform_earnings(
        self,
        start_date: datetime = None,
        end_date: datetime = None
    ) -> dict:
        """إجمالي أرباح المنصة"""
        query = self.db.query(MarketTransaction).filter(
            MarketTransaction.status == TransactionStatus.COMPLETED
        )

        if start_date:
            query = query.filter(MarketTransaction.completed_at >= start_date)
        if end_date:
            query = query.filter(MarketTransaction.completed_at <= end_date)

        transactions = query.all()

        total_revenue = sum(t.platform_fee for t in transactions)
        total_sales = len(transactions)

        return {
            "total_revenue": total_revenue,
            "total_sales": total_sales,
            "average_sale": total_revenue / total_sales if total_sales > 0 else 0
        }

    # ==========================================
    # قائمة الأمنيات
    # ==========================================

    def add_to_wishlist(
        self,
        user_id: int,
        book_id: int,
        max_price: int = None
    ) -> Wishlist:
        """إضافة ل قائمة الأمنيات"""
        existing = self.db.query(Wishlist).filter(
            Wishlist.user_id == user_id,
            Wishlist.book_id == book_id
        ).first()

        if existing:
            if max_price:
                existing.max_price = max_price
                self.db.commit()
            return existing

        wishlist = Wishlist(
            user_id=user_id,
            book_id=book_id,
            max_price=max_price
        )
        self.db.add(wishlist)
        self.db.commit()
        self.db.refresh(wishlist)
        return wishlist

    def remove_from_wishlist(self, user_id: int, book_id: int) -> bool:
        """إزالة من قائمة الأمنيات"""
        wishlist = self.db.query(Wishlist).filter(
            Wishlist.user_id == user_id,
            Wishlist.book_id == book_id
        ).first()

        if wishlist:
            self.db.delete(wishlist)
            self.db.commit()
            return True
        return False

    def get_user_wishlist(self, user_id: int) -> List[Wishlist]:
        """قائمة أمنيات المستخدم"""
        return self.db.query(Wishlist).filter(
            Wishlist.user_id == user_id
        ).all()

    def check_price_alerts(self, book_id: int, current_price: int) -> List[Wishlist]:
        """التحقق من تنبيهات السعر"""
        return self.db.query(Wishlist).filter(
            Wishlist.book_id == book_id,
            Wishlist.max_price >= current_price,
            Wishlist.notify_price_drop == True
        ).all()

    # ==========================================
    # البحث والتصفية
    # ==========================================

    def search_listings(self, query: str, limit: int = 20) -> List[MarketListing]:
        """البحث في القوائم"""
        return self.db.query(MarketListing).join(Book).filter(
            MarketListing.is_available == True,
            or_(
                Book.title.ilike(f"%{query}%"),
                Book.description.ilike(f"%{query}%")
            )
        ).limit(limit).all()

    def get_price_range(self, book_id: int = None) -> dict:
        """نطاق السعر"""
        query = self.db.query(MarketListing).filter(
            MarketListing.is_available == True,
            MarketListing.price_points.isnot(None)
        )

        if book_id:
            query = query.filter(MarketListing.book_id == book_id)

        min_price = self.db.query(func.min(MarketListing.price_points)).filter(
            MarketListing.is_available == True,
            MarketListing.price_points.isnot(None)
        ).scalar()

        max_price = self.db.query(func.max(MarketListing.price_points)).filter(
            MarketListing.is_available == True,
            MarketListing.price_points.isnot(None)
        ).scalar()

        return {
            "min": min_price or 0,
            "max": max_price or 0
        }
