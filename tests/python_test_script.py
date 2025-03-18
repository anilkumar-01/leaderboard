import requests
import random
import time

API_BASE_URL = "http://localhost:8000/api/leaderboard"

# Simulate score submission
def submit_score(user_id):
    score = random.randint(100, 10000)
    data = requests.post(f"{API_BASE_URL}/submit", json={"user_id": user_id, "score": score})
    print("data", data.json())
    return data

# Fetch top players
def get_top_players():
    response = requests.get(f"{API_BASE_URL}/top")
    return response.json()

# Fetch user rank
def get_user_rank(user_id):
    response = requests.get(f"{API_BASE_URL}/rank/{user_id}")
    return response.json()

if __name__ == "__main__":
    import time
    i = 0
    while i < 5:
        print("starting the loop")
        t0 = time.time()
        user_id = random.randint(1, 1000000)
        submit_score(user_id)
        t1 = time.time()
        print("\ntime for submit", t0-t1)
        print(get_top_players())
        t2 = time.time()
        print("time for top players", t2 - t1, "\n")
        print(get_user_rank(user_id))
        print("time for get rank players", time.time() - t2, "\n")
        time.sleep(random.uniform(0.5, 2)) # Simulate real user interaction
        i +=1