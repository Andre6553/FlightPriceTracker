import os
import sqlite3
from dotenv import load_dotenv
from supabase import create_client, Client
from datetime import datetime

# Load env vars from tools/.env
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "tools", ".env"))

url = os.environ.get("SUPABASE_URL")
key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")

if not url or not key:
    print("Error: Supabase URL or Key not found in tools/.env")
    exit(1)

# create supabase client
supabase: Client = create_client(url, key)

DB_PATH = os.path.join(os.path.dirname(__file__), "flights.db")

def sync_table(table_name):
    print(f"Syncing {table_name} to Supabase...")
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # We fetch the max ID currently in Supabase to know where to resume
    try:
        response = supabase.table(table_name).select("id").order("id", desc=True).limit(1).execute()
        max_id = response.data[0]['id'] if response.data else 0
    except Exception as e:
        print(f"Error fetching max id from Supabase {table_name}: {e}")
        max_id = 0

    print(f"Local sync starting from {table_name} ID > {max_id}")
    
    cursor.execute(f"SELECT * FROM {table_name} WHERE id > ?", (max_id,))
    rows = cursor.fetchall()
    
    if not rows:
        print(f"No new rows to sync for {table_name}.")
        conn.close()
        return

    batch_size = 1000
    for i in range(0, len(rows), batch_size):
        batch = [dict(r) for r in rows[i:i+batch_size]]
        try:
            supabase.table(table_name).insert(batch).execute()
            print(f"  Inserted {len(batch)} rows into {table_name} (up to id {batch[-1]['id']})")
        except Exception as e:
            print(f"Error inserting batch into {table_name}: {e}")
            break
            
    conn.close()

if __name__ == "__main__":
    print(f"============================================")
    print(f"  Starting Supabase Sync - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"============================================")
    try:
        sync_table("flight_prices")
        sync_table("flight_details")
        print("Sync complete.")
    except Exception as e:
        print(f"Sync script failed: {e}")
