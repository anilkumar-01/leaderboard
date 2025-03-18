# app/schemas/leaderboard.py
from pydantic import BaseModel, field_validator, Field
from typing import List, Optional

from app.core.errors import BadRequestError

class ScoreSubmit(BaseModel):
    """Schema for score submission."""
    user_id: int 
    score: int = Field(..., ge=0, le=10000)
    game_mode: Optional[str] = "default"
    
    @field_validator('score')
    def score_must_be_in_valid_range(cls, v):
        if v < 0 or v > 10000:
             raise BadRequestError(f"Score must be between 0 and 10000, got {v}")
        return v
    
class LeaderboardEntry(BaseModel):
    """Schema for a leaderboard entry."""
    rank: int
    user_id: int
    username: str
    total_score: int
    
    class ConfigDict:
        from_attributes = True

class LeaderboardResponse(BaseModel):
    """Schema for leaderboard response."""
    total_entries: int
    leaderboard: List[LeaderboardEntry]
    
    class ConfigDict:
        from_attributes = True

class PlayerRank(BaseModel):
    """Schema for player rank response."""
    user_id: int
    username: str
    rank: int
    total_score: int
    
    class ConfigDict:
        from_attributes = True