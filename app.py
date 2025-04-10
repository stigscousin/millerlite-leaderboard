from flask import Flask, render_template, jsonify
import os
from dotenv import load_dotenv
import requests
import logging
from flask_cors import CORS
from datetime import datetime
import time

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes
load_dotenv()

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Cache for tournament data
TOURNAMENT_CACHE = {
    'data': None,
    'last_updated': None,
    'cache_duration': 300,  # Cache for 5 minutes instead of 1 minute
    'tournament_id': '2cba1945-dc1c-4131-92f4-cfdac8c45060'  # Hardcode the 2025 Masters ID
}

# Rate limiting settings
RATE_LIMIT = {
    'last_request': None,
    'min_interval': 0.5,  # Reduce minimum interval between requests to 0.5 seconds
    'retry_count': 0,
    'max_retries': 2  # Reduce max retries to 2
}

LEAGUE_MEMBERS = {
    "Charlie Burns": "Collin Morikawa",
    "Kim Jong Rein": "Bryson DeChambeau",
    "Drew Contini": "Jose Maria Olazabal",
    "Eddie Rein": "Jordan Spieth",
    "Joe DePeder": "Collin Morikawa",
    "Joe Skarbek": "Jose Maria Olazabal",
    "John Steurer": "Rory McIlroy",
    "Josh Niese": "Collin Morikawa",
    "Kyle Duffy": "Collin Morikawa",
    "Kyle O'Dowd": "Bryson DeChambeau",
    "Nick Rein": "Bryson DeChambeau",
    "Rob Suttman": "Rory McIlroy",
    "Ryan Tepe": "Brooks Koepka",
    "Sam Altenbach": "Scottie Scheffler",
    "Sam Girouard": "Collin Morikawa",
    "Sean Joyce": "Tommy Fleetwood",
    "Travis Clark": "Jon Rahm",
    "Tyler Rettig": "Rory McIlroy",
    "Zach Schafer": "Rory McIlroy"
}

SPORTSRADAR_API_KEY = os.getenv('SPORTSRADAR_API_KEY')
SPORTSRADAR_BASE_URL = "https://api.sportradar.com/golf/trial/pga/v3/en"

def make_api_request(url, headers, params):
    """Make an API request with rate limiting and retry logic."""
    current_time = time.time()
    
    # Check if we need to wait due to rate limiting
    if RATE_LIMIT['last_request'] is not None:
        time_since_last = current_time - RATE_LIMIT['last_request']
        if time_since_last < RATE_LIMIT['min_interval']:
            time.sleep(RATE_LIMIT['min_interval'] - time_since_last)
    
    try:
        response = requests.get(url, headers=headers, params=params)
        RATE_LIMIT['last_request'] = time.time()
        
        if response.status_code == 429:  # Rate limit exceeded
            if RATE_LIMIT['retry_count'] < RATE_LIMIT['max_retries']:
                RATE_LIMIT['retry_count'] += 1
                time.sleep(2 ** RATE_LIMIT['retry_count'])  # Exponential backoff
                return make_api_request(url, headers, params)
            else:
                logger.error(f"Max retries reached for rate limit")
                return None
        elif response.status_code != 200:
            logger.error(f"Error: {response.status_code}")
            logger.error(f"Response: {response.text}")
            return None
            
        RATE_LIMIT['retry_count'] = 0  # Reset retry count on success
        return response.json()
    except Exception as e:
        logger.error(f"Error making API request: {str(e)}")
        return None

def fetch_tournament_schedule(year):
    """Fetch the tournament schedule for a given year."""
    try:
        url = f"{SPORTSRADAR_BASE_URL}/{year}/tournaments/schedule.json"
        headers = {"accept": "application/json"}
        params = {"api_key": SPORTSRADAR_API_KEY}
        
        logger.info(f"Fetching {year} tournament schedule...")
        return make_api_request(url, headers, params)
    except Exception as e:
        logger.error(f"Error fetching schedule: {str(e)}")
        return None

def fetch_tournament_summary(year, tournament_id):
    """Fetch detailed tournament summary."""
    try:
        url = f"{SPORTSRADAR_BASE_URL}/{year}/tournaments/{tournament_id}/summary.json"
        headers = {"accept": "application/json"}
        params = {"api_key": SPORTSRADAR_API_KEY}
        
        logger.info(f"Fetching tournament summary...")
        return make_api_request(url, headers, params)
    except Exception as e:
        logger.error(f"Error fetching tournament summary: {str(e)}")
        return None

def fetch_tournament_leaderboard(year, tournament_id):
    """Fetch tournament leaderboard data."""
    try:
        url = f"{SPORTSRADAR_BASE_URL}/{year}/tournaments/{tournament_id}/leaderboard.json"
        headers = {"accept": "application/json"}
        params = {"api_key": SPORTSRADAR_API_KEY}
        
        logger.info(f"Fetching tournament leaderboard...")
        response = make_api_request(url, headers, params)
        if response:
            logger.info(f"Raw leaderboard response: {response}")
        return response
    except Exception as e:
        logger.error(f"Error fetching leaderboard: {str(e)}")
        return None

def get_cached_data():
    """Get cached tournament data or fetch new data if needed."""
    current_time = time.time()
    
    if (TOURNAMENT_CACHE['data'] is None or 
        TOURNAMENT_CACHE['last_updated'] is None or 
        current_time - TOURNAMENT_CACHE['last_updated'] > TOURNAMENT_CACHE['cache_duration']):
        
        year = 2025
        tournament_id = TOURNAMENT_CACHE['tournament_id']
        
        # Get leaderboard data directly since we know the tournament ID
        leaderboard_data = fetch_tournament_leaderboard(year, tournament_id)
        if leaderboard_data:
            TOURNAMENT_CACHE['data'] = {
                'tournament': {
                    'id': tournament_id,
                    'name': 'The Masters Tournament',
                    'start_date': '2025-04-10',
                    'end_date': '2025-04-13',
                    'venue': {'name': 'Augusta National Golf Club'},
                    'round': leaderboard_data.get('round', 1)
                },
                'leaderboard': leaderboard_data
            }
            TOURNAMENT_CACHE['last_updated'] = current_time
            return TOURNAMENT_CACHE['data']
        else:
            logger.error("Failed to fetch leaderboard data")
            return None
    
    return TOURNAMENT_CACHE['data']

def process_leaderboard_data(leaderboard_data):
    """Process leaderboard data into a format suitable for the frontend."""
    processed_data = {}
    
    if not leaderboard_data or 'leaderboard' not in leaderboard_data:
        return processed_data
        
    for player in leaderboard_data.get('leaderboard', []):
        name = f"{player.get('first_name', '')} {player.get('last_name', '')}"
        position = player.get('position', 'N/A')
        tied = player.get('tied', False)
        score = player.get('score', 'E')
        if score == 0:
            score = 'E'
        elif score is not None:
            score = f"{'+' if score > 0 else ''}{score}"
        
        # Get round information
        rounds = player.get('rounds', [])
        current_round = None
        current_round_number = leaderboard_data.get('round', 1)
        
        # Find the current round
        for round_data in rounds:
            if round_data.get('sequence') == current_round_number:
                current_round = round_data
                break
        
        # Get today's score and thru
        if current_round:
            thru = current_round.get('thru', 'F')
            # If thru is 18, set it to 'F' to indicate finished
            if thru == 18:
                thru = 'F'
            today = current_round.get('score', 'N/A')
            
            # Format today's score
            if today == 0:
                today = 'E'
            elif today is not None and today != 'N/A':
                today = f"{'+' if today > 0 else ''}{today}"
        else:
            thru = 'N/A'
            today = 'N/A'
            
        processed_data[name] = {
            "position": position,
            "position_number": 9999 if not str(position).isdigit() else int(position),
            "tied": tied,
            "score": score,
            "today": today,
            "thru": thru
        }
    
    return processed_data

@app.route('/')
def index():
    return render_template('index.html', members=LEAGUE_MEMBERS)

@app.route('/api/tournaments/current')
def get_current_tournament_info():
    cached_data = get_cached_data()
    
    if not cached_data:
        return jsonify({
            "status": "error",
            "message": "Unable to fetch tournament data"
        })
    
    tournament_info = cached_data['tournament']
    return jsonify({
        "status": "success",
        "data": {
            "id": tournament_info.get('id'),
            "name": tournament_info.get('name', ''),
            "start_date": tournament_info.get('start_date', ''),
            "end_date": tournament_info.get('end_date', ''),
            "venue": tournament_info.get('venue', {}),
            "round": tournament_info.get('round', 'N/A')
        }
    })

@app.route('/api/leaderboard')
def get_leaderboard():
    try:
        cached_data = get_cached_data()
        
        if not cached_data:
            return jsonify({
                "status": "error",
                "message": "Unable to fetch tournament data"
            })
        
        # Process leaderboard data
        processed_data = process_leaderboard_data(cached_data['leaderboard'])
        
        # Process league members data
        league_data = {}
        for member, player in LEAGUE_MEMBERS.items():
            if player in processed_data:
                league_data[member] = {
                    "player": player,
                    "position_number": processed_data[player]["position_number"],
                    **processed_data[player]
                }
            else:
                league_data[member] = {
                    "player": player,
                    "position": "N/A",
                    "position_number": float('inf'),
                    "tied": False,
                    "score": "N/A",
                    "today": "N/A",
                    "thru": "N/A"
                }
        
        # Sort league data by position
        sorted_league_data = dict(sorted(
            league_data.items(),
            key=lambda x: x[1]["position_number"]
        ))
        
        return jsonify({
            "status": "success",
            "tournament": cached_data['tournament'],
            "data": sorted_league_data
        })
        
    except Exception as e:
        logger.error(f"Error in get_leaderboard: {str(e)}")
        return jsonify({
            "status": "error",
            "message": f"Server error: {str(e)}"
        })

if __name__ == '__main__':
    app.run(host='127.0.0.1', port=5002) 