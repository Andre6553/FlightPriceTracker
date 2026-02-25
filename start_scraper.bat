@echo off
title FlySafair Price Tracker
echo ============================================
echo   FlySafair Price Tracker - Running 24/7
echo   Scrapes every 1.5 hours. Close this window to stop.
echo ============================================
echo.

cd /d "%~dp0"

REM Prevent PC from sleeping while scraper is running
echo Disabling sleep (requires admin for full effect)...
powercfg /change standby-timeout-dc 0 2>nul
powercfg /change standby-timeout-ac 0 2>nul
powercfg /change hibernate-timeout-dc 0 2>nul
powercfg /change hibernate-timeout-ac 0 2>nul
echo Sleep disabled. Your PC will stay awake while this window is open.
echo.

call venv\Scripts\activate

echo.
echo Starting Background Dashboard Server...
start /b python local_server.py > nul 2>&1
echo Dashboard is running at http://127.0.0.1:8080/calendar
echo.

python main.py

REM Restore default sleep settings when scraper stops
echo.
echo Restoring default sleep settings...
powercfg /change standby-timeout-dc 10 2>nul
powercfg /change standby-timeout-ac 0 2>nul
powercfg /change hibernate-timeout-dc 180 2>nul
powercfg /change hibernate-timeout-ac 0 2>nul

pause
