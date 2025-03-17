# app/schemas/leaderboard.py
from pydantic import BaseModel, validator
from typing import List, Optional

class ScoreSubmit(BaseModel):
    """Schema for score submission."""
    user_id: int
    score: int
    game_mode: Optional[str] = "default"
    
    # @validator('score')
    # def score_must_be_positive(cls, v):
    #     if v < 0:
    #         raise ValueError('score must be non-negative')
    #     return v
    
class LeaderboardEntry(BaseModel):
    """Schema for a leaderboard entry."""
    rank: int
    user_id: int
    username: str
    total_score: int
    
    class Config:
        from_attributes = True

class LeaderboardResponse(BaseModel):
    """Schema for leaderboard response."""
    total_entries: int
    leaderboard: List[LeaderboardEntry]
    
    class Config:
        from_attributes = True

class PlayerRank(BaseModel):
    """Schema for player rank response."""
    user_id: int
    username: str
    rank: int
    total_score: int
    
    class Config:
        from_attributes = True