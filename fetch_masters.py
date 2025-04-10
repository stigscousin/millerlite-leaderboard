import os
import requests
import json
from dotenv import load_dotenv
from datetime import datetime

# Load environment variables
load_dotenv()

# SportsRadar API configuration
SPORTSRADAR_API_KEY = os.getenv('SPORTSRADAR_API_KEY')
SPORTSRADAR_BASE_URL = "https://api.sportradar.com/golf/trial/pga/v3/en"

def fetch_tournament_schedule(year):
    """Fetch the tournament schedule for a given year."""
    try:
        url = f"{SPORTSRADAR_BASE_URL}/{year}/tournaments/schedule.json"
        headers = {"accept": "application/json"}
        params = {"api_key": SPORTSRADAR_API_KEY}
        
        print(f"Fetching {year} tournament schedule...")
        response = requests.get(url, headers=headers, params=params)
        
        if response.status_code != 200:
            print(f"Error: {response.status_code}")
            print(f"Response: {response.text}")
            return None
            
        schedule_data = response.json()
        return schedule_data
    except Exception as e:
        print(f"Error fetching schedule: {str(e)}")
        return None

def fetch_tournament_summary(year, tournament_id):
    """Fetch detailed tournament summary."""
    try:
        url = f"{SPORTSRADAR_BASE_URL}/{year}/tournaments/{tournament_id}/summary.json"
        headers = {"accept": "application/json"}
        params = {"api_key": SPORTSRADAR_API_KEY}
        
        print(f"Fetching tournament summary...")
        response = requests.get(url, headers=headers, params=params)
        
        if response.status_code != 200:
            print(f"Error: {response.status_code}")
            print(f"Response: {response.text}")
            return None
            
        summary_data = response.json()
        return summary_data
    except Exception as e:
        print(f"Error fetching tournament summary: {str(e)}")
        return None

def fetch_tournament_leaderboard(year, tournament_id):
    """Fetch tournament leaderboard data."""
    try:
        url = f"{SPORTSRADAR_BASE_URL}/{year}/tournaments/{tournament_id}/leaderboard.json"
        headers = {"accept": "application/json"}
        params = {"api_key": SPORTSRADAR_API_KEY}
        
        print(f"Fetching tournament leaderboard...")
        response = requests.get(url, headers=headers, params=params)
        
        if response.status_code != 200:
            print(f"Error: {response.status_code}")
            print(f"Response: {response.text}")
            return None
            
        leaderboard_data = response.json()
        return leaderboard_data
    except Exception as e:
        print(f"Error fetching leaderboard: {str(e)}")
        return None

def display_leaderboard(leaderboard_data, tournament_info=None):
    """Display the leaderboard in a formatted way."""
    if tournament_info:
        print(f"\n{tournament_info.get('name', 'Tournament')} Leaderboard")
        print(f"Venue: {tournament_info.get('venue', {}).get('name', 'N/A')}")
        print(f"Course: {tournament_info.get('venue', {}).get('courses', [{}])[0].get('name', 'N/A')}")
        print(f"Date: {tournament_info.get('start_date', 'N/A')} - {tournament_info.get('end_date', 'N/A')}")
        print("------------------------")

    if not leaderboard_data or 'leaderboard' not in leaderboard_data:
        print("No leaderboard data available")
        return

    print("\nCurrent Standings:")
    print("------------------------")
    for player in leaderboard_data.get('leaderboard', []):
        name = f"{player.get('first_name', '')} {player.get('last_name', '')}"
        position = player.get('position', 'N/A')
        tied = '(T)' if player.get('tied', False) else ''
        score = player.get('score', 'E')
        if score == 0:
            score = 'E'
        elif score is not None:
            score = f"{'+' if score > 0 else ''}{score}"
        
        # Get round information
        rounds = player.get('rounds', [])
        current_round = next((r for r in rounds if r.get('sequence') == len(rounds)), None)
        thru = current_round.get('thru', 0) if current_round else 'F'
        today = current_round.get('score', 'N/A') if current_round else 'N/A'
        
        if today == 0:
            today = 'E'
        elif today is not None and today != 'N/A':
            today = f"{'+' if today > 0 else ''}{today}"

        print(f"{position}{tied}. {name:<30} {score:<5} (Today: {today}, Thru: {thru})")

if __name__ == "__main__":
    if not SPORTSRADAR_API_KEY:
        print("Error: SPORTSRADAR_API_KEY not found in environment variables")
        print("Please create a .env file with your API key")
    else:
        # Get current year
        current_year = 2025  # Hardcoding to 2025 since that's the tournament we want
        
        # Fetch tournament schedule
        schedule = fetch_tournament_schedule(current_year)
        if schedule:
            masters_tournament = None
            for tournament in schedule.get('tournaments', []):
                if 'masters' in tournament.get('name', '').lower():
                    masters_tournament = tournament
                    break
            
            if masters_tournament:
                tournament_id = masters_tournament['id']
                
                # Fetch tournament summary for additional details
                summary = fetch_tournament_summary(current_year, tournament_id)
                
                # Fetch and display leaderboard
                leaderboard = fetch_tournament_leaderboard(current_year, tournament_id)
                if leaderboard:
                    display_leaderboard(leaderboard, masters_tournament)
            else:
                print(f"Could not find Masters tournament in {current_year} schedule") 