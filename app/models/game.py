# app/models/game.py
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, UniqueConstraint, CheckConstraint
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from app.db.session import Base

class GameSession(Base):
    __tablename__ = "game_sessions"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    score = Column(Integer, nullable=False)
    game_mode = Column(String, nullable=True)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationship with User model
    user = relationship("User", backref="game_sessions")

    __table_args__ = (
        # Add database constraint for score range
        CheckConstraint('score >= 0 AND score <= 10000', name='check_score_range'),
    )

class Leaderboard(Base):
    __tablename__ = "leaderboard"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True)
    total_score = Column(Integer, nullable=False, default=0, index=True)
    rank = Column(Integer, index=True)
    
    # Relationship with User model
    user = relationship("User", backref="leaderboard_entry")
    
    __table_args__ = (
        # Index for efficient ranking queries
        UniqueConstraint('user_id', name='uix_leaderboard_user'),
    )