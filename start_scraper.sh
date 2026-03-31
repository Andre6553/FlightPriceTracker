#!/bin/bash

# ============================================
# FlySafair Price Tracker - 24/7 Linux Runner
# ============================================

cd "$(dirname "$0")"

# Ensure headless mode is on
export HEADLESS=true

echo "============================================"
echo "  FlySafair Price Tracker - Starting..."
echo "  IP: 192.168.10.173"
echo "  Mode: Headless (SSH-optimized)"
echo "============================================"

# Activate environment
source venv/bin/activate

# Background Server
echo "-> Starting Dashboard @ http://192.168.10.173:8080/calendar"
nohup python3 local_server.py > server_log.txt 2>&1 &
SERVER_PID=$!

# Scraper Loop
echo "-> Starting Scraper Loop..."
python3 run_scraper_loop.py

# Cleanup
echo "-> Shutting down server (PID: $SERVER_PID)..."
kill $SERVER_PID
