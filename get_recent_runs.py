import sqlite3
import datetime

conn = sqlite3.connect('flights.db')
cursor = conn.cursor()

# Get all distinct scrape_datetimes
query = "SELECT DISTINCT scrape_datetime FROM flight_prices ORDER BY scrape_datetime DESC"
cursor.execute(query)
runs = cursor.fetchall()

now = datetime.datetime.fromisoformat('2026-02-25T07:59:37')
twenty_four_hours_ago = now - datetime.timedelta(hours=24)

count = 0
for run in runs:
    try:
        # handle time strings
        dt_str = run[0].replace(' ', 'T')
        dt = datetime.datetime.fromisoformat(dt_str)
            
        if dt >= twenty_four_hours_ago:
            count += 1
            print(f"- {run[0]}")
    except Exception as e:
        print(f"Failed to parse or error: {run[0]} -> {e}")

print(f"Total successful runs in the last 24 hours: {count}")
conn.close()
