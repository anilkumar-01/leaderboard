# app/api/auth.py
from datetime import timedelta
from typing import Any

from fastapi import APIRouter, Depends, status, Body
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.core.errors import BadRequestError, UnauthorizedError, ConflictError
from app.core.security import verify_password, get_password_hash, create_access_token
from app.config import settings
from app.db.session import get_db
from app.models.user import User
from app.models.game import Leaderboard
from app.schemas.auth import UserCreate, UserResponse, Token
from app.schemas.base import ResponseBase

router = APIRouter(prefix="/auth", tags=["auth"])

@router.post("/signup", response_model=ResponseBase[UserResponse], status_code=status.HTTP_201_CREATED)
def signup(
    *,
    db: Session = Depends(get_db),
    user_in: UserCreate = Body(...)
) -> Any:
    """
    Create new user.
    
    Args:
        db: Database session
        user_in: User data
        
    Returns:
        ResponseBase with user data
    """
    # Check if username already exists
    if db.query(User).filter(User.username == user_in.username).first():
        raise ConflictError(detail="Username already registered")
    
    # Create new user
    user = User(
        username=user_in.username,
        hashed_password=get_password_hash(user_in.password)
    )
    
    db.add(user)
    db.commit()
    db.refresh(user)
    
    return ResponseBase[UserResponse](
        success=True,
        message="User created successfully",
        data=UserResponse.model_validate(user)
    )

@router.post("/login", response_model=Token)
def login(
    db: Session = Depends(get_db),
    form_data: OAuth2PasswordRequestForm = Depends()
) -> Any:
    """
    Login user and return JWT token.
    
    Args:
        db: Database session
        form_data: Login form data (username and password)
        
    Returns:
        JWT token
    """
    # Get user by username
    user = db.query(User).filter(User.username == form_data.username).first()
    
    # Verify user exists and password is correct
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise UnauthorizedError(detail="Incorrect username or password")
    
    # Create access token
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        subject=user.id, expires_delta=access_token_expires
    )
    
    return Token(access_token=access_token)