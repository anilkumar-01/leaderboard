# app/models/user.py
from sqlalchemy import Column, Integer, String, DateTime, Boolean
from sqlalchemy.sql import func

from app.db.session import Base

class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, nullable=False, index=True)