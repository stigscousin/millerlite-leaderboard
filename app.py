from flask import Flask, render_template, jsonify
import os
from dotenv import load_dotenv
import requests
import logging
from flask_cors import CORS
from datetime import datetime
import time
import json

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

# Cache for tournament data
TOURNAMENT_CACHE = {
    'data': None,
    'last_updated': None,
    'cache_duration': 600,  # Increase cache duration to 10 minutes
    'tournament_id': '2cba1945-dc1c-4131-92f4-cfdac8c45060'  # Hardcode the 2025 Masters ID
}

# Rate limiting settings
RATE_LIMIT = {
    'last_request': None,
    'min_interval': 1.0,  # Increase minimum interval between requests to 1 second
    'retry_count': 0,
    'max_retries': 3  # Increase max retries to 3
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

PAYOUT_STRUCTURE = {
    1: 4200000,
    2: 2268000,
    3: 1428000,
    4: 1008000,
    5: 840000,
    6: 756000,
    7: 703500,
    8: 651000,
    9: 609000,
    10: 567000,
    11: 525000,
    12: 483000,
    13: 441000,
    14: 399000,
    15: 378000,
    16: 357000,
    17: 336000,
    18: 315000,
    19: 294000,
    20: 273000,
    21: 252000,
    22: 235200,
    23: 218400,
    24: 201600,
    25: 184800,
    26: 168000,
    27: 161700,
    28: 155400,
    29: 149100,
    30: 142800,
    31: 136500,
    32: 130200,
    33: 123900,
    34: 118650,
    35: 113400,
    36: 108150,
    37: 102900,
    38: 98700,
    39: 94500,
    40: 90300,
    41: 86100,
    42: 81900,
    43: 77700,
    44: 73500,
    45: 69300,
    46: 65100,
    47: 60900,
    48: 57540,
    49: 54600,
    50: 52920
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
        max_sequence = 0
        
        # Find the round with the highest sequence number
        for round_data in rounds:
            sequence = round_data.get('sequence', 0)
            if sequence > max_sequence:
                max_sequence = sequence
                current_round = round_data
        
        # Initialize today and thru with default values
        today = "-"
        thru = "-"
        
        # Get today's score and thru
        if current_round:
            thru = current_round.get('thru', 0)
            # If thru is 18, set it to 'F' to indicate finished
            if thru == 18:
                thru = 'F'
            # If thru is 0, they haven't started yet
            elif thru == 0:
                thru = '-'
                today = '-'  # Set today to '-' if they haven't started
            else:
                today = current_round.get('score', '-')
                # Format today's score
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
                    "position_number": float('inf'),
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
    app.run(host='127.0.0.1', port=5002) 