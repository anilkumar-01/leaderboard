Gaming Leaderboard API
A RESTful API for tracking and displaying player performance in games, built with FastAPI and PostgreSQL.

Features
User Authentication - Register and login with JWT tokens
Score Submission - Submit game scores
Leaderboard - View top players ranked by total score
Player Ranking - Check a specific player's current ranking

Project Structure
The project follows a modular structure for better organization and maintainability:

gaming_leaderboard/
│
├── app/                              # Main application package
│   ├── api/                          # API endpoints
│   ├── core/                         # Core functionality
│   ├── db/                           # Database related code
│   ├── models/                       # SQLAlchemy ORM models
│   └── schemas/                      # Pydantic models
│
├── scripts/                          # Utility scripts
└── tests/                            # test cases