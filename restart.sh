#!/bin/bash

# Kill any existing Flask process
pkill -f "python app.py"

# Start Flask app
python app.py 