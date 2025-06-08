#!/bin/bash
# Simple script to keep the Flask server running
echo "Starting Vehicle Scraper API Server..."

while true; do
    echo "$(date): Starting Flask server..."
    python main.py
    echo "$(date): Server stopped, restarting in 5 seconds..."
    sleep 5
done