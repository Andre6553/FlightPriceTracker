import os
import sqlite3
from datetime import datetime

DB_PATH = os.path.expanduser("~/flysafair-scraper/flights.db")

def query_prices():
    if not os.path.exists(DB_PATH):
        print(f"Error: Database not found at {DB_PATH}")
        return

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Query for JNB-CPT or CPT-JNB for 1 April 2026
    query = """
    SELECT route, flight_date, departure_time, price, scrape_datetime 
    FROM flight_prices 
    WHERE (route='JNB-CPT' OR route='CPT-JNB') 
      AND flight_date='2026-04-01' 
    ORDER BY scrape_datetime DESC 
    LIMIT 3;
    """
    
    cursor.execute(query)
    rows = cursor.fetchall()
    
    if not rows:
        print("No matches found for JNB-CPT on 1 April.")
    else:
        for row in rows:
            print(f"Route: {row[0]} | Date: {row[1]} | Time: {row[2]} | Price: R{row[3]} | Scraped: {row[4]}")
            
    conn.close()

if __name__ == "__main__":
    query_prices()
