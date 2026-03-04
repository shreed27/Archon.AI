from sqlalchemy.orm import Session
from ..database.models import User
from datetime import datetime


class UsageTracker:
    def __init__(self, db: Session):
        self.db = db

    def track_usage(self, email: str, tokens: int):
        user = self.db.query(User).filter(User.email == email).first()
        if user:
            user.tokens_used += tokens
            user.requests_today += 1
            self.db.commit()
            return True
        return False

    def check_rate_limit(self, email: str):
        user = self.db.query(User).filter(User.email == email).first()
        if user:
            # Simple daily reset logic could go here or in a separate cron
            if user.requests_today >= 50:
                return False
        return True
