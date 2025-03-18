# app/api/leaderboard.py
from typing import Any, List
from fastapi import APIRouter, Depends, Path, Query, BackgroundTasks
from sqlalchemy.orm import Session
from sqlalchemy import text, func, desc
from sqlalchemy.exc import SQLAlchemyError

from app.db.session import get_db
from app.core.errors import NotFoundError, BadRequestError
from app.models.user import User
from app.models.game import GameSession, Leaderboard
from app.schemas.leaderboard import ScoreSubmit, LeaderboardResponse, LeaderboardEntry, PlayerRank
from app.schemas.base import MessageResponse, ResponseBase
from app.api.dependencies import get_current_active_user
from app.core.cache import (
    cached_leaderboard, cached_player_rank, 
    invalidate_leaderboard_cache, invalidate_player_rank_cache
)
from app.core.rate_limiter import submit_score_limiter, get_player_rank_limiter, get_leaderboard_limiter

import time
router = APIRouter(prefix="/leaderboard", tags=["leaderboard"])

async def update_leaderboard_ranks_background(db: Session):
    """
    Update ALL ranks in the leaderboard based on total scores.
    This runs as a background task to avoid blocking the API response.
    
    Args:
        db: Database session
    """
    try:
        # First, obtain an advisory lock to prevent concurrent rank updates
        db.execute(text("SELECT pg_advisory_xact_lock(42)"))
        
        # Update all ranks using window function in raw SQL
        db.execute(text("""
            UPDATE leaderboard
            SET rank = ranks.rank
            FROM (
                SELECT 
                    user_id, 
                    RANK() OVER (ORDER BY total_score DESC) as rank
                FROM leaderboard
            ) ranks
            WHERE leaderboard.user_id = ranks.user_id
        """))
        
        db.commit()
        
        # Invalidate caches after ranks update
        invalidate_leaderboard_cache()
        
    except SQLAlchemyError as e:
        db.rollback()
        print(f"Error updating leaderboard ranks: {str(e)}")

@router.post("/submit", response_model=ResponseBase[MessageResponse], status_code=201)
async def submit_score(
    *,
    db: Session = Depends(get_db),
    score_data: ScoreSubmit,
    # current_user: User = Depends(get_current_active_user),
    background_tasks: BackgroundTasks,
    _: bool = Depends(submit_score_limiter) 
) -> Any:
    """
    Submit a new score for the current authenticated user.
    Optimized for performance by running rank updates as a background task
    and using proper transaction isolation.
    
    Args:
        db: Database session
        score_data: Score data (score must be between 0 and 10000)
        current_user: Current authenticated user
        background_tasks: FastAPI background tasks
        
    Returns:
        Message that score was submitted successfully
    """
    # Validate user in db
    user = db.query(User).filter(User.id == score_data.user_id)
    if not user:
        raise NotFoundError(f"User not found")

    # Validate score range
    if score_data.score < 0 or score_data.score > 10000:
        raise BadRequestError(f"Score must be between 0 and 10000, got {score_data.score}")
    
    try:
        # Start transaction for score update with row-level locking
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
        
        if leaderboard_entry:
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
        
        # Immediately invalidate this user's rank cache
        invalidate_player_rank_cache(score_data.user_id)
        
        # Schedule rank updates as a background task
        # This prevents the API from blocking while ranks are recalculated
        background_tasks.add_task(update_leaderboard_ranks_background, db)
       
        return ResponseBase[MessageResponse](
            success=True,
            message="Score submitted successfully",
            data=MessageResponse(message="Score submitted successfully and ranks will be updated shortly")
        )
    except SQLAlchemyError as e:
        db.rollback()
        raise BadRequestError(f"Error submitting score: {str(e)}")

@router.get("/top", response_model=LeaderboardResponse)
@cached_leaderboard
async def get_leaderboard(
    *,
    db: Session = Depends(get_db),
    limit: int = Query(10, ge=1, le=100, description="Number of entries to return"),
    page: int = Query(1, ge=1, description="Page number"),
    _: bool = Depends(get_leaderboard_limiter) 
) -> Any:
    """
    Get top players from the leaderboard.
    Optimized with query tuning and caching.
    
    Args:
        db: Database session
        limit: Maximum number of entries to return
        page: Page number for pagination
        
    Returns:
        Leaderboard entries
    """
    offset = (page - 1) * limit
    
    try:
        # Use count query optimization for total entries
        total_entries = db.query(func.count(Leaderboard.id)).scalar()
        
        # Use a single optimized query with joins and explicit columns to select
        # This reduces the amount of data transferred from the database
        entries = db.query(
            Leaderboard.rank.label('rank'),
            Leaderboard.total_score.label('total_score'),
            Leaderboard.user_id.label('user_id'),
            User.username.label('username')
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
@cached_player_rank
async def get_player_rank(
    *,
    db: Session = Depends(get_db),
    user_id: int = Path(..., description="User ID to get rank for"),
    _: bool = Depends(get_player_rank_limiter) 
) -> Any:
    """
    Get a player's current rank.
    Optimized with caching and query optimization.
    
    Args:
        db: Database session
        user_id: ID of the user to get rank for
        
    Returns:
        Player rank
    """
    try:
        # Use a single optimized query with a direct join rather than two separate queries
        entry = db.query(
            Leaderboard.rank.label('rank'),
            Leaderboard.total_score.label('total_score'),
            User.username.label('username'),
            User.id.label('user_id')
        ).join(
            User, Leaderboard.user_id == User.id
        ).filter(
            User.id == user_id
        ).first()
        
        if not entry:
            # Check if user exists but has no rank
            user = db.query(User).filter(User.id == user_id).first()
            if not user:
                raise NotFoundError(detail="User not found")
            else:
                raise NotFoundError(detail="Player has not yet been ranked")
        
        return PlayerRank(
            user_id=entry.user_id,
            username=entry.username,
            rank=entry.rank,
            total_score=entry.total_score
        )
    except SQLAlchemyError as e:
        raise BadRequestError(f"Error retrieving player rank: {str(e)}")