# app/db/base.py
from app.db.session import Base

# Import all models to ensure they are registered with SQLAlchemy
# This is needed for Alembic migrations
from app.models.user import User
from app.models.game import GameSession, Leaderboard