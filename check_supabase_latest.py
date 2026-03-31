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

def get_latest(table_name):
    print(f"\n--- Latest from {table_name} ---")
    try:
        response = supabase.table(table_name).select("*").order("scrape_datetime", desc=True).limit(1).execute()
        if response.data:
            data = response.data[0]
            print(f"  Route: {data.get('route')}")
            print(f"  Flight Date: {data.get('flight_date')}")
            print(f"  Price: R{data.get('price')}")
            print(f"  Scrape Time: {data.get('scrape_datetime')}")
        else:
            print("  No data found in table.")
    except Exception as e:
        print(f"  Error fetching from {table_name}: {e}")

if __name__ == "__main__":
    get_latest("flight_prices")
    get_latest("flight_details")
