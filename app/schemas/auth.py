# app/schemas/auth.py
from pydantic import BaseModel, EmailStr, validator
from typing import Optional
from datetime import datetime

class UserBase(BaseModel):
    """Base user schema."""
    username: str
    email: EmailStr
    is_active: bool = True

class UserCreate(UserBase):
    """Schema for user creation."""
    password: str
    
    @validator('password')
    def password_must_be_strong(cls, v):
        if len(v) < 8:
            raise ValueError('password must be at least 8 characters')
        return v
    
    @validator('username')
    def username_must_be_valid(cls, v):
        if len(v) < 3:
            raise ValueError('username must be at least 3 characters')
        if not v.isalnum():
            raise ValueError('username must be alphanumeric')
        return v

class UserLogin(BaseModel):
    """Schema for user login."""
    username: str
    password: str

class UserResponse(UserBase):
    """Schema for user response."""
    id: int
    join_date: datetime
    
    class Config:
        from_attributes = True

class Token(BaseModel):
    """Schema for JWT token."""
    access_token: str
    token_type: str = "bearer"

class TokenPayload(BaseModel):
    """Schema for token payload."""
    sub: Optional[int] = None