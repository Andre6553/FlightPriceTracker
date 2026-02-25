import os
from dotenv import load_dotenv
from supabase import create_client

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "tools", ".env"))
url = os.environ.get("SUPABASE_URL")
# Use ANON KEY to simulate browser fetch
key = os.environ.get("SUPABASE_ANON_KEY")

print(f"Connecting to {url} with anon key...")
supabase = create_client(url, key)

try:
    print("Fetching from flight_prices...")
    response = supabase.table("flight_prices").select("*").limit(1).execute()
    print("Success! Data:", response.data)
except Exception as e:
    print(f"Error: {e}")
