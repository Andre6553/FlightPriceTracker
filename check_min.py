from db_manager import get_all_data

df = get_all_data()
df['price'] = df['price'].astype(float)
row = df.loc[df['price'].idxmin()]

route = row['route']
fdate = row['flight_date']
price = row['price']
sdt = row['scrape_datetime']
dbf = row['days_before_flight']

print(f"Route: {route}")
print(f"Flight Date: {fdate}")
print(f"Price: R{price:.2f}")
print(f"Scraped at: {sdt}")
print(f"Days before: {dbf}")
