import os
from supabase import create_client, Client
from dotenv import load_dotenv

# Load credentials from tools/.env
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "tools", ".env"))

url = os.environ.get("SUPABASE_URL")
key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")

if not url or not key:
    print("Error: Supabase URL or Key not found.")
    exit(1)

supabase: Client = create_client(url, key)

def get_cheapest():
    print(f"\n--- Cheapest Flight: CPT to JNB on 2026-04-03 ---")
    try:
        # Corrected order syntax for supabase-py
        response = supabase.table("flight_prices")\
            .select("route, flight_date, price, departure_time, scrape_datetime")\
            .eq("route", "CPT-JNB")\
            .eq("flight_date", "2026-04-03")\
            .order("price", desc=False)\
            .limit(1)\
            .execute()
        
        if response.data:
            data = response.data[0]
            print(f"  Route: {data.get('route')}")
            print(f"  Flight Date: {data.get('flight_date')}")
            print(f"  Lowest Price: R{data.get('price')}")
            print(f"  Time: {data.get('departure_time')}")
            print(f"  Scraped At: {data.get('scrape_datetime')}")
        else:
            print("  No data found for this route and date.")
    except Exception as e:
        print(f"  Error fetching data: {e}")

if __name__ == "__main__":
    get_cheapest()
