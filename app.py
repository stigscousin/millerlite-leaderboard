from flask import Flask, render_template, jsonify
import os
from dotenv import load_dotenv
import requests
import logging
from flask_cors import CORS
from datetime import datetime
import time
import json
import pytz
from werkzeug.middleware.dispatcher import DispatcherMiddleware

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes
load_dotenv()

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('flask.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Add URL prefix for all routes
app.config['APPLICATION_ROOT'] = '/millerlite'
app.wsgi_app = DispatcherMiddleware(app.wsgi_app, {
    '/millerlite': app.wsgi_app
})

# Cache for tournament data
TOURNAMENT_CACHE = {
    'data': None,
    'last_updated': None,
    'cache_duration': 600,  # Increase cache duration to 10 minutes
    'tournament_id': 'ae058906-abf0-4341-9c30-646b3ab4581f'  # RBC Heritage 2025 ID
}

# Rate limiting settings
RATE_LIMIT = {
    'last_request': None,
    'min_interval': 1.0,  # Increase minimum interval between requests to 1 second
    'retry_count': 0,
    'max_retries': 3  # Increase max retries to 3
}

LEAGUE_MEMBERS = {
    "Charlie Burns": "Scottie Scheffler",
    "Donald Rein": "Jordan Spieth",
    "Drew Contini": "Ryan Gerard",
    "Eddie Rein": "Xander Schauffele",
    "Joe DePeder": "Russell Henley",
    "Joe Skarbek": "Ryan Gerard",
    "John Steurer": "Patrick Cantlay",
    "Josh Niese": "Sahith Theegala",
    "Kyle Duffy": "Scottie Scheffler",
    "Kyle O'Dowd": "Collin Morikawa",
    "Nick Rein": "Patrick Cantlay",
    "Rob Suttman": "Patrick Cantlay",
    "Ryan Tepe": "Patrick Cantlay",
    "Sam Altenbach": "Xander Schauffele",
    "Sam Girouard": "Viktor Hovland",
    "Sean Joyce": "Corey Conners",
    "Travis Clark": "Xander Schauffele",
    "Tyler Rettig": "Ryan Gerard",
    "Zach Schafer": "Ryan Gerard"
}

PAYOUT_STRUCTURE = {
    1: 3600000,
    2: 2160000,
    3: 1360000,
    4: 960000,
    5: 800000,
    6: 720000,
    7: 670000,
    8: 620000,
    9: 580000,
    10: 540000,
    11: 500000,
    12: 460000,
    13: 420000,
    14: 380000,
    15: 360000,
    16: 340000,
    17: 320000,
    18: 300000,
    19: 280000,
    20: 260000,
    21: 240000,
    22: 223000,
    23: 207500,
    24: 190000,
    25: 175000,
    26: 159000,
    27: 152500,
    28: 146000,
    29: 140000,
    30: 134000,
    31: 128500,
    32: 122500,
    33: 116500,
    34: 111000,
    35: 106500,
    36: 101500,
    37: 96500,
    38: 92500,
    39: 88500,
    40: 84000,
    41: 80000,
    42: 76000,
    43: 72000,
    44: 68000,
    45: 64000,
    46: 60000,
    47: 56000,
    48: 53000,
    49: 50000,
    50: 49000,
    51: 48000,
    52: 47000,
    53: 46000,
    54: 46000,
    55: 45500,
    56: 45000,
    57: 44500,
    58: 44000,
    59: 43000,
    60: 42500,
    61: 42500,
    62: 42000,
    63: 41500,
    64: 41000,
    65: 40500,
    66: 40000,
    67: 39500,
    68: 39000,
    69: 38000,
    70: 37500
}

SPORTSRADAR_API_KEY = os.getenv('SPORTSRADAR_API_KEY')
SPORTSRADAR_BASE_URL = "https://api.sportradar.com/golf/trial/pga/v3/en"

def log_memory_usage():
    """Log current memory usage."""
    import psutil
    process = psutil.Process()
    memory_info = process.memory_info()
    logger.info(f"Memory usage: {memory_info.rss / 1024 / 1024:.2f} MB")

def make_api_request(url, headers, params):
    """Make an API request with rate limiting and retry logic."""
    current_time = time.time()
    log_memory_usage()  # Log memory usage before request
    
    # Check if we need to wait due to rate limiting
    if RATE_LIMIT['last_request'] is not None:
        time_since_last = current_time - RATE_LIMIT['last_request']
        if time_since_last < RATE_LIMIT['min_interval']:
            time.sleep(RATE_LIMIT['min_interval'] - time_since_last)
    
    try:
        logger.info(f"Making API request to: {url}")
        response = requests.get(url, headers=headers, params=params, timeout=10)
        RATE_LIMIT['last_request'] = time.time()
        
        if response.status_code == 429:  # Rate limit exceeded
            logger.warning("Rate limit exceeded")
            if RATE_LIMIT['retry_count'] < RATE_LIMIT['max_retries']:
                RATE_LIMIT['retry_count'] += 1
                wait_time = min(2 ** RATE_LIMIT['retry_count'], 30)
                logger.info(f"Retrying in {wait_time} seconds (attempt {RATE_LIMIT['retry_count']})")
                time.sleep(wait_time)
                return make_api_request(url, headers, params)
            else:
                logger.error("Max retries reached for rate limit")
                return None
        elif response.status_code != 200:
            logger.error(f"API Error: {response.status_code}")
            logger.error(f"Response: {response.text}")
            return None
            
        RATE_LIMIT['retry_count'] = 0
        log_memory_usage()  # Log memory usage after successful request
        return response.json()
    except requests.exceptions.Timeout:
        logger.error("Request timed out")
        return None
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
            logger.info("=== RAW API RESPONSE ===")
            logger.info(json.dumps(response, indent=2))
            logger.info("=======================")
        return response
    except Exception as e:
        logger.error(f"Error fetching leaderboard: {str(e)}")
        return None

def get_cached_data():
    """Get cached tournament data or fetch new data if needed."""
    current_time = time.time()
    
    # Check if we have cached data and if it's still valid
    if TOURNAMENT_CACHE['data'] and TOURNAMENT_CACHE['last_updated']:
        time_since_update = current_time - TOURNAMENT_CACHE['last_updated']
        
        # Get current time in PT
        pt_time = datetime.now().astimezone(pytz.timezone('America/Los_Angeles'))
        current_hour = pt_time.hour
        
        # Only update if:
        # 1. Cache is expired (10 minutes)
        # 2. Current time is between 5am and 5pm PT
        if time_since_update < TOURNAMENT_CACHE['cache_duration'] or current_hour < 5 or current_hour >= 17:
            logger.info("Using cached data")
            return TOURNAMENT_CACHE['data']
    
    logger.info("Forcing fresh data fetch...")
    
    year = 2025
    tournament_id = TOURNAMENT_CACHE['tournament_id']
    
    # Get leaderboard data directly since we know the tournament ID
    logger.info(f"Fetching leaderboard data for year {year} and tournament {tournament_id}")
    leaderboard_data = fetch_tournament_leaderboard(year, tournament_id)
    
    if leaderboard_data:
        logger.info("Successfully fetched fresh leaderboard data")
        TOURNAMENT_CACHE['data'] = {
            'tournament': {
                'id': tournament_id,
                'name': 'RBC Heritage',  # Fixed tournament name
                'start_date': '2025-04-17',
                'end_date': '2025-04-20',
                'venue': {'name': 'Harbour Town Golf Links'},
                'round': leaderboard_data.get('round', 1)
            },
            'leaderboard': leaderboard_data
        }
        TOURNAMENT_CACHE['last_updated'] = time.time()
        return TOURNAMENT_CACHE['data']
    else:
        logger.error("Failed to fetch leaderboard data")
        return None

def get_projected_payout(position):
    """Get the projected payout for a given position."""
    if position == "CUT":
        return "-"
    try:
        # Handle tied positions (e.g., "T1")
        if isinstance(position, str) and position.startswith('T'):
            pos = int(position[1:])
        else:
            pos = int(position)
            
        if pos in PAYOUT_STRUCTURE:
            return PAYOUT_STRUCTURE[pos]  # Return raw number, let frontend handle formatting
        return "-"
    except (ValueError, TypeError):
        return "-"

def process_leaderboard_data(leaderboard_data):
    """Process leaderboard data into a format suitable for the frontend."""
    processed_data = {}
    
    if not leaderboard_data or 'leaderboard' not in leaderboard_data:
        logger.warning("No leaderboard data available")
        return processed_data
        
    logger.info("=== PROCESSING LEADERBOARD DATA ===")
    for player in leaderboard_data.get('leaderboard', []):
        name = f"{player.get('first_name', '')} {player.get('last_name', '')}"
        logger.info(f"\nProcessing player: {name}")
        logger.info(f"Raw player data: {json.dumps(player, indent=2)}")
        
        position = player.get('position', '-')
        tied = player.get('tied', False)
        score = player.get('score', 'E')
        if score == 0:
            score = 'E'
        elif score is not None:
            score = f"{'+' if score > 0 else ''}{score}"
        
        # Check if player is cut
        status = player.get('status', '')
        if status == 'CUT':
            processed_data[name] = {
                "position": "CUT",
                "position_number": 9999 if not str(position).isdigit() else int(position),
                "tied": False,  # Set tied to False for cut players
                "score": score,
                "today": "-",
                "thru": "-",
                "payout": "-"
            }
            continue
        
        # Get round information
        rounds = player.get('rounds', [])
        current_round = None
        current_round_number = leaderboard_data.get('round', 1)  # Get current tournament round
        
        # Find the current round
        for round_data in rounds:
            if round_data.get('sequence') == current_round_number:
                current_round = round_data
                break
        
        # Initialize today and thru with default values
        today = "-"
        thru = "-"
        
        # Get today's score and thru
        if current_round:
            thru = current_round.get('thru', 0)
            # If thru is 18, set it to 'F' to indicate finished
            if thru == 18:
                thru = 'F'
            
            # Get today's score
            today = current_round.get('score', '-')
            if today == 0:
                today = 'E'
            elif today is not None and today != '-':
                today = f"{'+' if today > 0 else ''}{today}"
            
        processed_data[name] = {
            "position": position,
            "position_number": 9999 if not str(position).isdigit() else int(position),
            "tied": tied,
            "score": score,
            "today": today,
            "thru": thru,
            "payout": get_projected_payout(position)
        }
        
        logger.info(f"Processed data for {name}: {json.dumps(processed_data[name], indent=2)}")
    
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
                    "position_number": 9999,
                    "tied": False,
                    "score": "N/A",
                    "today": "N/A",
                    "thru": "N/A",
                    "payout": "-"
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
    app.run(host='127.0.0.1', port=5002, debug=True) 