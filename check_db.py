import sqlite3
import pandas as pd
conn = sqlite3.connect('flights.db')
df = pd.read_sql_query("SELECT * FROM flight_prices WHERE route='GRJ-JNB' AND flight_date='2026-05-15' AND departure_time != 'calendar' ORDER BY scrape_datetime DESC", conn)
print(df.to_string())
