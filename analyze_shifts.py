import sqlite3
import pandas as pd

conn = sqlite3.connect('flights.db')
query = """
SELECT route, flight_date, departure_time, scrape_datetime, price
FROM flight_prices
WHERE departure_time != 'calendar'
ORDER BY route, flight_date, departure_time, scrape_datetime ASC
"""
df = pd.read_sql_query(query, conn)
conn.close()

results = []
for name, group in df.groupby(['route', 'flight_date', 'departure_time']):
    prices = group['price'].values
    if len(prices) <= 1:
        continue
    
    history = [prices[0]]
    shifts = 0
    for i in range(1, len(prices)):
        if prices[i] != prices[i-1]:
            shifts += 1
            history.append(prices[i])
            
    if shifts > 0:
         results.append({
             'route': name[0],
             'flight_date': name[1],
             'departure_time': name[2],
             'shifts': shifts,
             'min_price': min(prices),
             'max_price': max(prices),
             'history': " -> ".join([f"R{int(p)}" for p in history])
         })

if not results:
    print("No price shifts detected in the database.")
else:
    res_df = pd.DataFrame(results)
    # Sort by number of shifts first, then price variation
    res_df['variation'] = res_df['max_price'] - res_df['min_price']
    res_df = res_df.sort_values(by=['shifts', 'variation'], ascending=[False, False])
    
    print("--- Flights with the most price changes ---")
    for _, row in res_df.head(15).iterrows():
        print(f"Route: {row['route']} | Date: {row['flight_date']} | Time: {row['departure_time']}")
        print(f"  Changes:   {row['shifts']}")
        print(f"  Prices:    R{int(row['min_price'])} to R{int(row['max_price'])} (Variation: R{int(row['max_price'] - row['min_price'])})")
        print(f"  Sequence:  {row['history']}")
        print()
