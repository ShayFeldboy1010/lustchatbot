#!/bin/bash

# Start script for Render deployment

echo "Starting LustBot application..."

# Set default values if not provided
export PORT=${PORT:-8000}
export HOST=${HOST:-0.0.0.0}
export DEBUG=${DEBUG:-False}

# Add current directory to Python path
export PYTHONPATH=$PYTHONPATH:/app:/opt/render/project/src

# Print environment info
echo "Starting on $HOST:$PORT"
echo "Debug mode: $DEBUG"
echo "Python path: $PYTHONPATH"

# Start the application with gunicorn
exec gunicorn -c gunicorn.conf.py main:app
