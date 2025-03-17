# app/api/dependencies.py
from typing import Optional
from jose import jwt, JWTError
from fastapi import Depends, Security
from sqlalchemy.orm import Session
from fastapi.security import OAuth2PasswordBearer

from app.db.session import get_db
from app.core.errors import UnauthorizedError, NotFoundError
from app.models.user import User
from app.schemas.auth import TokenPayload
from app.core.security import oauth2_scheme
from app.config import settings

async def get_current_user(
    db: Session = Depends(get_db),
    token: str = Security(oauth2_scheme)
) -> User:
    """
    Get the current authenticated user.
    
    Args:
        db: Database session
        token: JWT token from authorization header
        
    Returns:
        User object
        
    Raises:
        UnauthorizedError: If token is invalid or user not found
    """
    try:
        payload = jwt.decode(
            token, 
            settings.SECRET_KEY, 
            algorithms=[settings.ALGORITHM]
        )
        token_data = TokenPayload(**payload)
        
        if token_data.sub is None:
            raise UnauthorizedError()
    except JWTError:
        raise UnauthorizedError()
    
    user = db.query(User).filter(User.id == token_data.sub).first()
    
    if not user:
        raise NotFoundError(detail="User not found")
    if not user.is_active:
        raise UnauthorizedError(detail="Inactive user")
        
    return user

async def get_current_active_user(
    current_user: User = Depends(get_current_user),
) -> User:
    """
    Get the current active user.
    
    Args:
        current_user: Current authenticated user
        
    Returns:
        User object
        
    Raises:
        UnauthorizedError: If user is not active
    """
    # if not current_user.is_active:
    #     raise UnauthorizedError(detail="Inactive user")
    return current_user