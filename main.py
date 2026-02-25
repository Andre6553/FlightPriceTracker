"""
FlySafair Price Tracker - Main Controller
Runs the scraper on a schedule and generates reports after each run.
Uses time-based catch-up logic so missed runs (due to PC sleep) are handled.
"""
import time
import asyncio
from scraper import run_scraper
from analyzer import run_analysis
from datetime import datetime, timedelta

# How often to check prices (in hours) - 1.5 hours (90 mins) to fit the 75min scrape
CHECK_INTERVAL_HOURS = 1.5

import json

def set_status(is_running, duration=None, next_run=None):
    try:
        # Load existing status to preserve other fields if needed
        status_data = {}
        try:
            with open("status.json", "r") as f:
                status_data = json.load(f)
        except Exception:
            pass
            
        status_data["running"] = is_running
        if duration is not None:
            status_data["last_duration_seconds"] = duration
        if next_run is not None:
            status_data["next_run_iso"] = next_run.isoformat()
            
        with open("status.json", "w") as f:
            json.dump(status_data, f)
    except Exception:
        pass

def get_next_grid_run(base_time, interval_hours):
    """Calculates the next run time locked to a fixed grid (e.g. 0:00, 1:30, 3:00)."""
    interval_mins = int(interval_hours * 60)
    # Start from midnight of the base_time day
    midnight = base_time.replace(hour=0, minute=0, second=0, microsecond=0)
    # Seconds since midnight
    seconds_since_midnight = (base_time - midnight).total_seconds()
    minutes_since_midnight = int(seconds_since_midnight // 60)
    
    # Find how many intervals have already passed today
    intervals_done = minutes_since_midnight // interval_mins
    # Next one is intervals_done + 1
    next_min = (intervals_done + 1) * interval_mins
    
    return midnight + timedelta(minutes=next_min)

def job(next_run_val=None):
    print(f"\n{'=' * 60}")
    print(f"  SCHEDULED JOB - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'=' * 60}")

    set_status(True, next_run=next_run_val)

    # Run the scraper
    start_time = time.time()
    try:
        asyncio.run(run_scraper())
    except Exception as e:
        print(f"Error during scraping: {e}")
        
    end_time = time.time()
    duration_seconds = end_time - start_time
    print(f"  -> Scrape completed in {duration_seconds:.1f} seconds")

    # Generate updated reports
    print("\n--- Generating Reports ---")
    try:
        run_analysis()
    except Exception as e:
        print(f"Error during analysis: {e}")
        
    set_status(False, duration=int(duration_seconds))

if __name__ == "__main__":
    # Track the next scheduled run time
    next_run = get_next_grid_run(datetime.now(), CHECK_INTERVAL_HOURS)
    
    # Run once immediately on startup, ONLY if we aren't too close to the next hour
    # For a 90 min interval, we skip if we are within 20 mins of the next slot
    time_until_next = (next_run - datetime.now()).total_seconds() / 60
    if time_until_next > 20:
        print(f"Starting initial baseline scrape (Next scheduled run in {time_until_next:.1f} mins)...")
        job(next_run_val=next_run)
        # Re-calculate next_run AFTER the baseline so we don't immediately trigger another run
        next_run = get_next_grid_run(datetime.now(), CHECK_INTERVAL_HOURS)
    else:
        print(f"Too close to the next scheduled run ({next_run.strftime('%H:%M')}). Skipping startup scrape.")

    # Update status with initial next_run
    set_status(False, next_run=next_run)

    try:
        while True:
            now = datetime.now()

            if now >= next_run:
                # Time to run! This also catches up after sleep.
                # If we missed multiple intervals (e.g. PC was asleep for 5 hours),
                # we run once now and schedule the next from current time.
                missed_hours = (now - next_run).total_seconds() / 3600
                if missed_hours > 1:
                    print(f"\n  *** PC was asleep for ~{missed_hours:.1f} hours — running catch-up check now ***")

                # Calculate the NEXT grid point after this job finishes
                job(next_run_val=next_run)
                
                # Move to the next slot in the grid
                next_run = get_next_grid_run(datetime.now(), CHECK_INTERVAL_HOURS)
                # If the job ran so long that we are already past the next grid point, skip it
                while next_run <= datetime.now():
                    next_run += timedelta(minutes=int(CHECK_INTERVAL_HOURS * 60))
                    
                print(f"  Next check at: {next_run.strftime('%H:%M:%S')}")

            time.sleep(30)  # Check every 30 seconds for better responsiveness after wake
    except KeyboardInterrupt:
        print("\nStopped by user.")
        set_status(False, duration=None)
