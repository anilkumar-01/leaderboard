# app/api/__init__.py
"""
API routes package
"""
from fastapi import APIRouter

from app.api import auth, leaderboard

api_router = APIRouter()
api_router.include_router(auth.router, tags=["auth"])
api_router.include_router(leaderboard.router, tags=["leaderboard"])