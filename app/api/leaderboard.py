# app/api/leaderboard.py
from typing import Any, List
from fastapi import APIRouter, Depends, Path, Query
from sqlalchemy.orm import Session
from sqlalchemy import text, func
from sqlalchemy.sql.expression import desc

from app.db.session import get_db
from app.core.errors import NotFoundError
from app.models.user import User
from app.models.game import GameSession, Leaderboard
from app.schemas.leaderboard import ScoreSubmit, LeaderboardResponse, LeaderboardEntry, PlayerRank
from app.schemas.base import MessageResponse, ResponseBase
from app.api.dependencies import get_current_active_user

router = APIRouter(prefix="/leaderboard", tags=["leaderboard"])

def update_leaderboard_ranks(db: Session):
    """
    Update all ranks in the leaderboard based on total scores.
    
    Args:
        db: Database session
    """
    # Update ranks using window function in raw SQL
    # This is more efficient than doing it in Python
    db.execute(text("""
        UPDATE leaderboard
        SET rank = ranks.rank
        FROM (
            SELECT user_id, RANK() OVER (ORDER BY total_score DESC) as rank
            FROM leaderboard
        ) ranks
        WHERE leaderboard.user_id = ranks.user_id
    """))
    db.commit()

@router.post("/submit", response_model=ResponseBase[MessageResponse], status_code=201)
async def submit_score(
    *,
    db: Session = Depends(get_db),
    score_data: ScoreSubmit,
    # current_user: User = Depends(get_current_active_user)
) -> Any:
    """
    Submit a new score for the current authenticated user.
    
    Args:
        db: Database session
        score_data: Score data
        current_user: Current authenticated user
        
    Returns:
        Message that score was submitted successfully
    """
    user = db.query(User).filter(User.id == score_data.user_id).first()
    
    if not user:
        raise NotFoundError(detail="User not found")

    # Insert the new game session
    new_session = GameSession(
        user_id=score_data.user_id,
        score=score_data.score,
        game_mode=score_data.game_mode
    )
    db.add(new_session)
    
    # Update leaderboard
    leaderboard_entry = db.query(Leaderboard).filter(
        Leaderboard.user_id == score_data.user_id
    ).first()
    
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
    
    db.commit()
    
    # Update ranks after committing the transaction
    update_leaderboard_ranks(db)
    
    return ResponseBase[MessageResponse](
        success=True,
        message="Score submitted successfully",
        data=MessageResponse(message="Score submitted successfully")
    )

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

# @router.get("/my-rank", response_model=PlayerRank)
# async def get_my_rank(
#     *,
#     db: Session = Depends(get_db),
#     current_user: User = Depends(get_current_active_user)
# ) -> Any:
#     """
#     Get the current authenticated user's rank.
    
#     Args:
#         db: Database session
#         current_user: Current authenticated user
        
#     Returns:
#         Current user's rank
#     """
#     # Get player's rank
#     entry = db.query(
#         Leaderboard.rank,
#         Leaderboard.total_score
#     ).filter(
#         Leaderboard.user_id == current_user.id
#     ).first()
    
#     if not entry:
#         raise NotFoundError(detail="You have not yet been ranked")
    
#     return PlayerRank(
#         user_id=current_user.id,
#         username=current_user.username,
#         rank=entry.rank,
#         total_score=entry.total_score
#     )
