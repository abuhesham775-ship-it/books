"""
Social Service - خدمة النظام الاجتماعي وموجز النشاط
"""
from datetime import datetime
from typing import List
from sqlalchemy.orm import Session
from sqlalchemy import desc, func
from app.models.social import FollowRelationship, ActivityFeed, ActivityType
from app.models.user import User
from app.services.user_service import UserService


class SocialService:
    """خدمة المجتمع الاجتماعي"""

    def __init__(self, db: Session):
        self.db = db
        self.user_service = UserService(db)

    def follow_user(self, follower_id: int, following_id: int) -> bool:
        if follower_id == following_id:
            return False

        existing = self.db.query(FollowRelationship).filter(
            FollowRelationship.follower_id == follower_id,
            FollowRelationship.following_id == following_id,
            FollowRelationship.is_active == True
        ).first()
        if existing:
            return False

        relation = FollowRelationship(
            follower_id=follower_id,
            following_id=following_id
        )
        self.db.add(relation)
        self.db.commit()
        self.record_activity(
            user_id=following_id,
            actor_id=follower_id,
            activity_type=ActivityType.FOLLOW,
            description=f"{self.user_service.get_user_by_id(follower_id).first_name or follower_id} تابعك"
        )
        return True

    def unfollow_user(self, follower_id: int, following_id: int) -> bool:
        relation = self.db.query(FollowRelationship).filter(
            FollowRelationship.follower_id == follower_id,
            FollowRelationship.following_id == following_id,
            FollowRelationship.is_active == True
        ).first()
        if not relation:
            return False
        relation.is_active = False
        self.db.commit()
        return True

    def get_followers(self, user_id: int) -> List[User]:
        rows = self.db.query(FollowRelationship).filter(
            FollowRelationship.following_id == user_id,
            FollowRelationship.is_active == True
        ).all()
        return [self.user_service.get_user_by_id(r.follower_id) for r in rows if self.user_service.get_user_by_id(r.follower_id)]

    def get_following(self, user_id: int) -> List[User]:
        rows = self.db.query(FollowRelationship).filter(
            FollowRelationship.follower_id == user_id,
            FollowRelationship.is_active == True
        ).all()
        return [self.user_service.get_user_by_id(r.following_id) for r in rows if self.user_service.get_user_by_id(r.following_id)]

    def is_following(self, follower_id: int, following_id: int) -> bool:
        return self.db.query(FollowRelationship).filter(
            FollowRelationship.follower_id == follower_id,
            FollowRelationship.following_id == following_id,
            FollowRelationship.is_active == True
        ).count() > 0

    def get_trending_users(self, limit: int = 10) -> List[User]:
        subquery = self.db.query(
            FollowRelationship.following_id,
            func.count(FollowRelationship.id).label("followers")
        ).filter(
            FollowRelationship.is_active == True
        ).group_by(
            FollowRelationship.following_id
        ).order_by(desc("followers")).limit(limit).subquery()

        users = self.db.query(User).join(subquery, User.id == subquery.c.following_id).all()
        return users

    def record_activity(
        self,
        user_id: int,
        actor_id: int = None,
        activity_type: ActivityType = ActivityType.GENERIC,
        description: str = None,
        target_user_id: int = None,
        target_book_id: int = None,
        metadata: dict = None
    ) -> ActivityFeed:
        activity = ActivityFeed(
            user_id=user_id,
            actor_id=actor_id,
            activity_type=activity_type,
            target_user_id=target_user_id,
            target_book_id=target_book_id,
            description=description,
            metadata=metadata or {}
        )
        self.db.add(activity)
        self.db.commit()
        self.db.refresh(activity)
        return activity

    def get_activity_feed(self, user_id: int, limit: int = 20) -> List[ActivityFeed]:
        return self.db.query(ActivityFeed).filter(
            ActivityFeed.user_id == user_id
        ).order_by(desc(ActivityFeed.created_at)).limit(limit).all()

    def get_global_feed(self, limit: int = 20) -> List[ActivityFeed]:
        return self.db.query(ActivityFeed).order_by(desc(ActivityFeed.created_at)).limit(limit).all()