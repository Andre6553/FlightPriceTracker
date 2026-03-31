#!/bin/bash

# FlySafair Price Tracker - Remote Setup Script
# This runs once on your Linux PC.

echo "--- 📦 Installing System Dependencies ---"
sudo apt update
sudo apt install python3 python3-pip python3-venv -y

echo "--- 🐍 Setting up Virtual Environment ---"
python3 -m venv venv
./venv/bin/pip install -r requirements_scraper.txt

echo "--- 🌐 Installing Playwright Browsers ---"
./venv/bin/playwright install --with-deps chromium

chmod +x start_scraper.sh

echo "============================================"
echo "   Setup Complete! "
echo "   Run ./start_scraper.sh to begin."
echo "============================================"
