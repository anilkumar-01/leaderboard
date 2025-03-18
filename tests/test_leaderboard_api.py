# tests/test_leaderboard_api.py
import pytest
from fastapi.testclient import TestClient
import json
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import app
from app.db.session import get_db, Base
from app.core.security import get_password_hash
from app.models.user import User
from app.models.game import Leaderboard

# Create a test database in-memory
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Override the get_db dependency
def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db

# Create a test client
client = TestClient(app)

# Create authentication token for tests
def get_auth_token(user_id: int):
    # This is a simplified version just for tests
    # In a real app, you'd use your actual authentication system
    from app.core.security import create_access_token
    token = create_access_token(subject=user_id)
    return token

# Setup test data
@pytest.fixture(scope="function")
def setup_test_db():
    # Create the tables
    Base.metadata.create_all(bind=engine)
    
    # Create a database session
    db = TestingSessionLocal()
    
    try:
        # Create test users
        test_users = []
        for i in range(1, 6):
            user = User(
                id=i,
                username=f"testuser{i}",
                hashed_password=get_password_hash("password"),
            )
            db.add(user)
            test_users.append(user)
        
        db.commit()
        
        # Initialize leaderboard with test data
        leaderboard_entries = []
        for i, user in enumerate(test_users):
            entry = Leaderboard(
                user_id=user.id,
                total_score=(5-i) * 100,  # user1: 500, user2: 400, etc.
                rank=i+1
            )
            db.add(entry)
            leaderboard_entries.append(entry)
        
        db.commit()
        
        yield
    
    finally:
        # Clean up
        db.close()
        Base.metadata.drop_all(bind=engine)

#----------------------------
# Test Submit Score API
#----------------------------
@pytest.mark.parametrize(
    "user_id,score,expected_status,expected_message", [
        (1, 100, 201, "Score submitted successfully"),  # Valid submission
        (1, 0, 201, "Score submitted successfully"),    # Zero score (valid)
        (1, 10000, 201, "Score submitted successfully"), # Max score (valid)
        (1, -10, 400, "Score must be between 0 and 10000"), # Negative score
        (1, 10001, 400, "Score must be between 0 and 10000"), # Score too high
        (999, 100, 404, "User not found"),  # Non-existent user
    ]
)
def test_submit_score(setup_test_db, user_id, score, expected_status, expected_message):
    """Test the score submission endpoint with various scenarios"""

    
    # Prepare request data
    payload = {
        "user_id": user_id,
        "score": score,
        "game_mode": "classic"
    }
    
    # Send request
    response = client.post(
        "/api/leaderboard/submit",
        json=payload,
    )
    
    # Check status code
    assert response.status_code == expected_status
    
    # Check response content
    response_data = response.json()
    
    if expected_status == 201:
        assert response_data["success"] == True
        assert expected_message in response_data["data"]["message"]
    else:
        assert expected_message in response_data["detail"]

def test_submit_score_rate_limit(setup_test_db):
    """Test rate limiting on score submission endpoint"""
    
    
    # Send multiple requests to trigger rate limit
    payload = {
        "user_id": 1,
        "score": 100,
        "game_mode": "classic"
    }
    
    # The rate limit is set to 10 requests per minute
    # Send 12 requests to ensure we hit the limit
    for i in range(12):
        response = client.post(
            "/api/leaderboard/submit",
            json=payload
        )
        
        # Check if rate limit was exceeded
        if response.status_code == 429:
            # Verify rate limit headers exist
            assert "X-RateLimit-Limit" in response.headers
            assert "X-RateLimit-Remaining" in response.headers
            assert "X-RateLimit-Reset" in response.headers
            assert "Retry-After" in response.headers
            return
    
    # If we didn't get a 429, the test should fail
    # (unless rate limiting is disabled in test environment)
    assert False, "Rate limit was not triggered"

#----------------------------
# Test Get Leaderboard API
#----------------------------
def test_get_leaderboard_default(setup_test_db):
    """Test getting the default leaderboard (top 10)"""
    
    response = client.get("/api/leaderboard/top")
    
    # Check status code
    assert response.status_code == 200
    
    # Check response content
    data = response.json()
    assert "leaderboard" in data
    assert "total_entries" in data
    assert data["total_entries"] == 5  # We created 5 test users
    
    # Check leaderboard entries
    leaderboard = data["leaderboard"]
    assert len(leaderboard) == 5
    
    # Check ranking order (should be descending by score)
    for i, entry in enumerate(leaderboard):
        assert entry["rank"] == i + 1
        if i > 0:
            assert entry["total_score"] <= leaderboard[i-1]["total_score"]

def test_get_leaderboard_pagination(setup_test_db):
    """Test leaderboard pagination"""
    
    # Test with limit=2 and page=2
    response = client.get("/api/leaderboard/top?limit=2&page=2")
    
    # Check status code
    assert response.status_code == 200
    
    # Check response content
    data = response.json()
    assert "leaderboard" in data
    
    # Should only return 2 entries (limit=2)
    assert len(data["leaderboard"]) == 2
    
    # Check if it's the correct page
    # Page 2 with limit 2 should have entries with rank 3 and 4
    entries = data["leaderboard"]
    assert entries[0]["rank"] == 3
    assert entries[1]["rank"] == 4

def test_get_leaderboard_invalid_params(setup_test_db):
    """Test leaderboard with invalid parameters"""
    
    # Test with negative limit
    response = client.get("/api/leaderboard/top?limit=-1")
    assert response.status_code == 422  # Validation error
    
    # Test with too large limit
    response = client.get("/api/leaderboard/top?limit=1000")
    assert response.status_code == 422  # FastAPI validation should catch this
    
    # Test with negative page
    response = client.get("/api/leaderboard/top?page=-1")
    assert response.status_code == 422  # Validation error

def test_get_leaderboard_caching(setup_test_db):
    """Test that leaderboard results are cached"""
    
    # Make initial request
    response1 = client.get("/api/leaderboard/top")
    assert response1.status_code == 200
    
    
    # Submit a new score that should affect the leaderboard
    payload = {
        "user_id": 1,
        "score": 1000,  # This should put user 1 way ahead
        "game_mode": "classic"
    }
    
    submit_response = client.post(
        "/api/leaderboard/submit",
        json=payload
    )
    assert submit_response.status_code == 201
    
    # Make second request immediately - should still get cached results
    response2 = client.get("/api/leaderboard/top")
    assert response2.status_code == 200
    
    # Compare responses - they should match if cached
    assert response1.json() == response2.json()

#----------------------------
# Test Get Player Rank API
#----------------------------
@pytest.mark.parametrize(
    "user_id,expected_status,check_content", [
        (1, 200, True),       # Existing user
        (5, 200, True),       # Existing user
        (999, 404, False),    # Non-existent user
    ]
)
def test_get_player_rank(setup_test_db, user_id, expected_status, check_content):
    """Test getting a player's rank with various scenarios"""
    
    # Send request
    response = client.get(f"/api/leaderboard/rank/{user_id}")
    
    # Check status code
    assert response.status_code == expected_status
    
    # Check response content if needed
    if check_content:
        data = response.json()
        assert "user_id" in data
        assert "username" in data
        assert "rank" in data
        assert "total_score" in data
        
        assert data["user_id"] == user_id
        
        # User 1 should be rank 1 with 500 points in our test data
        if user_id == 1:
            assert data["rank"] == 1
            assert data["total_score"] == 500
            assert data["username"] == "testuser1"

def test_get_player_rank_after_update(setup_test_db):
    """Test that player rank updates correctly after score submission"""
    
    # First, get user 2's initial rank
    initial_response = client.get("/api/leaderboard/rank/2")
    assert initial_response.status_code == 200
    initial_data = initial_response.json()
    
    # User 2 should be rank 2 with 400 points initially
    assert initial_data["rank"] == 2
    assert initial_data["total_score"] == 400
    
    # Submit a big score for user 2 to overtake user 1
    payload = {
        "user_id" : 2,
        "score": 200,  # This should put user 2 ahead (400 + 200 > 500)
        "game_mode": "classic"
    }
    
    submit_response = client.post(
        "/api/leaderboard/submit",
        json=payload
    )
    assert submit_response.status_code == 201
    
    # Force rank update to run synchronously for testing
    # In a real app, this might be background task
    db = TestingSessionLocal()
    try:
        # Update ranks manually (mimicking the background task)
        db.execute("""
            UPDATE leaderboard
            SET rank = ranks.rank
            FROM (
                SELECT user_id, RANK() OVER (ORDER BY total_score DESC) as rank
                FROM leaderboard
            ) ranks
            WHERE leaderboard.user_id = ranks.user_id
        """)
        db.commit()
    finally:
        db.close()
    
    # Clear cache to see the new results
    # In real app this would happen through cache invalidation
    from app.core.cache import invalidate_player_rank_cache
    invalidate_player_rank_cache()
    
    # Now get user 2's rank again - should be rank 1
    updated_response = client.get("/api/leaderboard/rank/2")
    assert updated_response.status_code == 200
    updated_data = updated_response.json()
    
    # User 2 should now be rank 1 with 600 points
    assert updated_data["rank"] == 1
    assert updated_data["total_score"] == 600
    
    # And user 1 should now be rank 2
    user1_response = client.get("/api/leaderboard/rank/1")
    assert user1_response.status_code == 200
    user1_data = user1_response.json()
    assert user1_data["rank"] == 2