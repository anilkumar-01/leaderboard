# app/schemas/base.py
from pydantic import BaseModel
from typing import Generic, TypeVar, Optional, Any

# Type variable for generic response models
T = TypeVar('T')

class MessageResponse(BaseModel):
    """Response model with a message."""
    message: str

class ResponseBase(BaseModel, Generic[T]):
    """Base response model with status and data."""
    success: bool = True
    message: Optional[str] = None
    data: Optional[T] = None

    class Config:
        arbitrary_types_allowed = True