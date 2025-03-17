# app/api/leaderboard.py
from typing import Any, List
from fastapi import APIRouter, Depends, Path, Query
from sqlalchemy.orm import Session
from sqlalchemy import text, func
from sqlalchemy.sql.expression import desc
from sqlalchemy.exc import SQLAlchemyError

from app.db.session import get_db
from app.core.errors import NotFoundError, BadRequestError
from app.models.user import User
from app.models.game import GameSession, Leaderboard
from app.schemas.leaderboard import ScoreSubmit, LeaderboardResponse, LeaderboardEntry, PlayerRank
from app.schemas.base import MessageResponse, ResponseBase
from app.api.dependencies import get_current_active_user

router = APIRouter(prefix="/leaderboard", tags=["leaderboard"])

def update_leaderboard_ranks(db: Session):
    """
    Update ALL ranks in the leaderboard based on total scores.
    This function recalculates and updates ranks for all users when called,
    ensuring the entire leaderboard is consistent.
    
    Args:
        db: Database session
    """
    # Lock the entire leaderboard table to prevent concurrent updates
    # during rank recalculation
    try:
        # First, obtain an advisory lock to prevent concurrent rank updates
        # This ensures that only one rank update process runs at a time
        db.execute(text("SELECT pg_advisory_xact_lock(42)"))
        
        # Update all ranks using window function in raw SQL
        # The RANK() function ensures proper rank assignment even with ties
        import time
        t1 = time.time()
        db.execute(text("""
            UPDATE leaderboard
            SET rank = ranks.rank
            FROM (
                SELECT 
                    user_id, 
                    RANK() OVER (ORDER BY total_score DESC) as rank
                FROM leaderboard
                FOR UPDATE
            ) ranks
            WHERE leaderboard.user_id = ranks.user_id
        """))
        
        db.commit()
        print("time taken", time.time()- t1)
        
        # Log or metric could be added here to track ranking update frequency
    except SQLAlchemyError as e:
        db.rollback()
        # Log the error details for monitoring
        print(f"Error updating leaderboard ranks: {str(e)}")
        raise

@router.post("/submit", response_model=ResponseBase[MessageResponse], status_code=201)
async def submit_score(
    *,
    db: Session = Depends(get_db),
    score_data: ScoreSubmit,
    # current_user: User = Depends(get_current_active_user)
) -> Any:
    """
    Submit a new score for the current authenticated user.
    Uses database transactions to handle concurrent requests safely.
    After updating the user's score, this recalculates all user ranks
    to ensure the entire leaderboard remains consistent.
    
    Args:
        db: Database session
        score_data: Score data (score must be between 0 and 10000)
        current_user: Current authenticated user
        
    Returns:
        Message that score was submitted successfully
    """
    # Create a new session for the score submission transaction
    try:
        # Start transaction for score update
        # Get user's leaderboard entry with FOR UPDATE lock to prevent race conditions
        # Double-check score range (server-side validation in addition to schema validation)
        if score_data.score < 0 or score_data.score > 10000:
            raise BadRequestError(f"Score must be between 0 and 10000, got {score_data.score}")
        
        leaderboard_entry = db.query(Leaderboard).filter(
            Leaderboard.user_id == score_data.user_id
        ).with_for_update().first()
        
        # Insert the new game session
        new_session = GameSession(
            user_id=score_data.user_id,
            score=score_data.score,
            game_mode=score_data.game_mode
        )
        db.add(new_session)
        
        # Store original score for determining if ranking update is needed
        original_score = 0
        if leaderboard_entry:
            original_score = leaderboard_entry.total_score
            # Update existing leaderboard entry
            leaderboard_entry.total_score += score_data.score
        else:
            # Create new leaderboard entry
            new_leaderboard_entry = Leaderboard(
                user_id=score_data.user_id,
                total_score=score_data.score
            )
            db.add(new_leaderboard_entry)
        
        # Commit the transaction to save the score update
        db.commit()
        
        # If score was added successfully, update all ranks in the leaderboard
        # This ensures that all users' ranks are updated correctly
        update_leaderboard_ranks(db)
        
        return ResponseBase[MessageResponse](
            success=True,
            message="Score submitted successfully",
            data=MessageResponse(message="Score submitted successfully and all ranks updated")
        )
    except SQLAlchemyError as e:
        db.rollback()
        raise BadRequestError(f"Error submitting score: {str(e)}")

@router.get("/top", response_model=LeaderboardResponse)
async def get_leaderboard(
    *,
    db: Session = Depends(get_db),
    limit: int = Query(10, ge=1, le=100, description="Number of entries to return"),
    page: int = Query(1, ge=1, description="Page number")
) -> Any:
    """
    Get top players from the leaderboard.
    
    Args:
        db: Database session
        limit: Maximum number of entries to return
        page: Page number for pagination
        
    Returns:
        Leaderboard entries
    """
    offset = (page - 1) * limit
    
    try:
        # Get total entries
        total_entries = db.query(Leaderboard).count()
        
        # Get top players ordered by rank
        entries = db.query(
            Leaderboard.rank,
            Leaderboard.total_score,
            Leaderboard.user_id,
            User.username
        ).join(
            User, Leaderboard.user_id == User.id
        ).order_by(
            Leaderboard.rank
        ).offset(offset).limit(limit).all()
        
        leaderboard_entries = [
            LeaderboardEntry(
                rank=entry.rank,
                user_id=entry.user_id,
                username=entry.username,
                total_score=entry.total_score
            ) for entry in entries
        ]
        
        return LeaderboardResponse(
            total_entries=total_entries,
            leaderboard=leaderboard_entries
        )
    except SQLAlchemyError as e:
        raise BadRequestError(f"Error retrieving leaderboard: {str(e)}")

@router.get("/rank/{user_id}", response_model=PlayerRank)
async def get_player_rank(
    *,
    db: Session = Depends(get_db),
    user_id: int = Path(..., description="User ID to get rank for")
) -> Any:
    """
    Get a player's current rank.
    
    Args:
        db: Database session
        user_id: ID of the user to get rank for
        
    Returns:
        Player rank
    """
    try:
        # Check if user exists
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise NotFoundError(detail="User not found")
        
        # Get player's rank
        entry = db.query(
            Leaderboard.rank,
            Leaderboard.total_score,
            User.username
        ).join(
            User, Leaderboard.user_id == User.id
        ).filter(
            Leaderboard.user_id == user_id
        ).first()
        
        if not entry:
            raise NotFoundError(detail="Player has not yet been ranked")
        
        return PlayerRank(
            user_id=user_id,
            username=entry.username,
            rank=entry.rank,
            total_score=entry.total_score
        )
    except SQLAlchemyError as e:
        raise BadRequestError(f"Error retrieving player rank: {str(e)}")