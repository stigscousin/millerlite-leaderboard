import os
import requests
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# SportsRadar API configuration
SPORTSRADAR_API_KEY = os.getenv('SPORTSRADAR_API_KEY')
SPORTSRADAR_BASE_URL = "https://api.sportradar.com/golf/trial/pga/v3/en"

def fetch_leaderboard():
    """Fetch tournament leaderboard data."""
    try:
        url = f"{SPORTSRADAR_BASE_URL}/2025/tournaments/2cba1945-dc1c-4131-92f4-cfdac8c45060/leaderboard.json"
        headers = {"accept": "application/json"}
        params = {"api_key": SPORTSRADAR_API_KEY}
        
        print(f"Making API request to: {url}")
        response = requests.get(url, headers=headers, params=params)
        
        if response.status_code != 200:
            print(f"Error: {response.status_code}")
            print(f"Response: {response.text}")
            return None
            
        return response.json()
    except Exception as e:
        print(f"Error fetching leaderboard: {str(e)}")
        return None

if __name__ == "__main__":
    if not SPORTSRADAR_API_KEY:
        print("Error: SPORTSRADAR_API_KEY not found in environment variables")
    else:
        data = fetch_leaderboard()
        if data:
            import json
            print("\n=== RAW API RESPONSE ===")
            print(json.dumps(data, indent=2))
            print("=======================") 