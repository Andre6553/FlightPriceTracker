import asyncio
from datetime import datetime

# Mock prices for February 2026
prices = [
    {"day": 23, "price": 2369.83}, # Monday
    {"day": 24, "price": 1369.82}, # Tuesday
    {"day": 25, "price": 1069.82}, # Wednesday (Cheapest)
    {"day": 26, "price": 1369.82}, # Thursday
    {"day": 27, "price": 1169.82}, # Friday (Weekend)
    {"day": 28, "price": 1169.82}, # Saturday
    {"day": 1, "price": 1369.82},  # Sunday (Weekend) - Note: In a real month, Feb 1st would be Sunday
]

month_num = 2
year_num = 2026

if prices and month_num and year_num:
    min_price = min(p["price"] for p in prices)
    
    target_days = []
    for p in prices:
        is_min = p["price"] == min_price
        
        try:
            p_date = datetime(year_num, month_num, p["day"])
            day_of_week = p_date.weekday()
            is_weekend = day_of_week == 4 or day_of_week == 6 # Friday = 4, Sunday = 6
            print(f"Day {p['day']}: Day of week = {day_of_week}, is_min = {is_min}, is_weekend = {is_weekend}")
        except ValueError:
            is_weekend = False
            
        if is_min or is_weekend:
            target_days.append(p["day"])
            
    # Deduplicate days
    target_days = list(set(target_days))
    target_days.sort()

    print(f"\nTarget days selected: {target_days}")
