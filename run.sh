#!/bin/bash
nohup python3 app.py > flask.log 2>&1 &
echo "Flask app is running in the background. Check flask.log for output."
echo "To stop the app, run: pkill -f 'python3 app.py'" 