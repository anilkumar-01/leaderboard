# app/core/security.py
from datetime import datetime, timedelta
from typing import Optional, Union, Any

from jose import jwt
from passlib.context import CryptContext
from fastapi.security import OAuth2PasswordBearer

from app.config import settings

# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# OAuth2 password bearer token scheme
oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.API_V1_PREFIX}/auth/login")

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against a hash."""
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    """Generate a hash from a password."""
    return pwd_context.hash(password)

def create_access_token(
    subject: Union[str, Any], 
    expires_delta: Optional[timedelta] = None
) -> str:
    """
    Create a JWT access token.
    
    Args:
        subject: The subject of the token (typically user ID)
        expires_delta: Token expiration time delta
        
    Returns:
        JWT access token as string
    """
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(
            minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
        )
    
    to_encode = {"exp": expire, "sub": str(subject)}
    encoded_jwt = jwt.encode(
        to_encode, 
        settings.SECRET_KEY, 
        algorithm=settings.ALGORITHM
    )
    return encoded_jwt