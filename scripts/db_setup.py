# scripts/db_setup.py
import os
import sys

# Add parent directory to path so we can import app modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text
from app.db.session import engine, Base, SessionLocal
from app.core.security import get_password_hash
from app.models.user import User
from app.models.game import Leaderboard

def setup_database():
    """Create all tables and initialize test data"""
    print("Creating database tables...")
    Base.metadata.create_all(bind=engine)
    
    # Create database session
    # db = SessionLocal()
    
    # try:
        # Check if test users exist
        # test_user_exists = db.query(User).filter(User.username == "testuser").first()
        # if not test_user_exists:
        #     print("Creating test users...")
        #     # Create test users
        #     test_users = [
        #         User(
        #             username=f"testuser{i}",
        #             email=f"testuser{i}@example.com",
        #             hashed_password=get_password_hash("password"),
        #             is_active=True
        #         ) for i in range(1, 6)
        #     ]
        #     db.add_all(test_users)
        #     db.commit()
            
        #     # Initialize leaderboard entries for test users
        #     for i, user in enumerate(test_users):
        #         # Add some initial scores so we have data to work with
        #         test_leaderboard = Leaderboard(
        #             user_id=user.id,
        #             total_score=(5-i) * 100  # Different scores for ranking
        #         )
        #         db.add(test_leaderboard)
        #     db.commit()
        
        # Update leaderboard ranks
        # print("Updating leaderboard ranks...")
        # db.execute(text("""
        #     UPDATE leaderboard
        #     SET rank = ranks.rank
        #     FROM (
        #         SELECT user_id, RANK() OVER (ORDER BY total_score DESC) as rank
        #         FROM leaderboard
        #     ) ranks
        #     WHERE leaderboard.user_id = ranks.user_id
        # """))
        # db.commit()
        
        # print("Database setup completed successfully!")
    
    # except Exception as e:
    #     print(f"Error setting up database: {e}")
    #     db.rollback()
    
    # finally:
    #     db.close()

def add_indexes():
    """Add performance indexes to the database"""
    print("Adding performance indexes...")
    db = SessionLocal()
    
    try:
        # Add indexes for better performance
        db.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_game_sessions_user_id ON game_sessions(user_id);
            CREATE INDEX IF NOT EXISTS idx_leaderboard_user_id ON leaderboard(user_id);
            CREATE INDEX IF NOT EXISTS idx_leaderboard_rank ON leaderboard(rank);
            CREATE INDEX IF NOT EXISTS idx_leaderboard_total_score ON leaderboard(total_score DESC);
        """))
        db.commit()
        print("Indexes added successfully!")
    
    except Exception as e:
        print(f"Error adding indexes: {e}")
        db.rollback()
    
    finally:
        db.close()

if __name__ == "__main__":
    setup_database()
    add_indexes()