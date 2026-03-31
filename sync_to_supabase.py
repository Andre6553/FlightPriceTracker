import os
import sqlite3
from dotenv import load_dotenv
from supabase import create_client, Client
from datetime import datetime

# Load env vars from tools/.env
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "tools", ".env"))

def sync_table(table_name):
    print(f"Syncing {table_name} to Supabase...")
    
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
    if not url or not key:
        print("Missing SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY in tools/.env")
        return

    supabase: Client = create_client(url, key)
    
    # Get max ID currently in Supabase to only sync new rows
    try:
        # Latest Supabase-py 2.x uses .order("id", desc=True)
        response = supabase.table(table_name).select("id").order("id", desc=True).limit(1).execute()
        max_id = response.data[0]['id'] if response.data else 0
    except Exception as e:
        print(f"Error fetching max id from Supabase {table_name}: {e}")
        max_id = 0

    conn = sqlite3.connect(os.path.expanduser("~/flysafair-scraper/flights.db"))
    cur = conn.cursor()
    
    # SMART SYNC: Only sync TODAY'S records that are also NEWER than max_id
    today = datetime.now().strftime("%Y-%m-%d")
    cur.execute(f"SELECT * FROM {table_name} WHERE id > ? AND scrape_datetime LIKE ?", (max_id, f"{today}%"))
    rows = cur.fetchall()
    
    if not rows:
        print(f"No new rows to sync for {table_name}.")
        conn.close()
        return

    print(f"Local sync starting from {table_name} ID > {max_id}. Found {len(rows)} new rows.")
    
    # Get column names
    cur.execute(f"PRAGMA table_info({table_name})")
    cols = [c[1] for c in cur.fetchall()]
    
    batch_size = 100
    for i in range(0, len(rows), batch_size):
        batch = rows[i:i+batch_size]
        payload = []
        for r in batch:
            row_dict = dict(zip(cols, r))
            payload.append(row_dict)
            
        try:
            supabase.table(table_name).insert(payload).execute()
            print(f"  Inserted batch {i//batch_size + 1}/{(len(rows)-1)//batch_size + 1}")
        except Exception as e:
            print(f"Error inserting batch into {table_name}: {e}")
            break

    print(f"Sync complete for {table_name}.")
    conn.close()

def manage_storage():
    """Monitor database size and trim oldest past-flight data when approaching limits.
    
    Strategy:
    - Safe limit: 1,600,000 total rows (~400MB, 80% of 500MB free tier)
    - When exceeded: delete oldest scrapes for past flight dates
    - Always keeps the LATEST scrape for each past date (for reference)
    - Never touches future flight data
    """
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
    if not url or not key:
        return
    
    supabase: Client = create_client(url, key)
    SAFE_LIMIT = 1_600_000  # ~400MB
    
    # Count total rows across both tables
    try:
        r1 = supabase.table("flight_prices").select("id", count="exact").limit(1).execute()
        r2 = supabase.table("flight_details").select("id", count="exact").limit(1).execute()
        total = (r1.count or 0) + (r2.count or 0)
        pct = (total / SAFE_LIMIT) * 100
        print(f"\n--- Storage Monitor ---")
        print(f"  Total rows: {total:,} / {SAFE_LIMIT:,} ({pct:.1f}%)")
    except Exception as e:
        print(f"  Storage check failed: {e}")
        return
    
    if total < SAFE_LIMIT:
        print(f"  Status: OK - plenty of room")
        return
    
    # We need to trim! Delete oldest past-flight scrapes
    today = datetime.now().strftime("%Y-%m-%d")
    rows_to_delete = total - int(SAFE_LIMIT * 0.7)  # Trim down to 70% to avoid frequent cleanups
    print(f"  Status: CLEANUP NEEDED - trimming ~{rows_to_delete:,} oldest past-flight rows")
    
    for table_name in ["flight_details", "flight_prices"]:
        if rows_to_delete <= 0:
            break
        try:
            # Find the oldest scrape dates for past flights
            oldest = supabase.table(table_name)\
                .select("id")\
                .lt("flight_date", today)\
                .order("scrape_datetime", desc=False)\
                .limit(min(rows_to_delete, 5000))\
                .execute()
            
            if not oldest.data:
                continue
            
            ids_to_delete = [r["id"] for r in oldest.data]
            
            # Delete in batches
            batch_size = 500
            deleted = 0
            for i in range(0, len(ids_to_delete), batch_size):
                batch_ids = ids_to_delete[i:i+batch_size]
                supabase.table(table_name).delete().in_("id", batch_ids).execute()
                deleted += len(batch_ids)
            
            rows_to_delete -= deleted
            print(f"  Trimmed {deleted:,} old rows from {table_name}")
            
        except Exception as e:
            print(f"  Trim error on {table_name}: {e}")
    
    print(f"  Cleanup complete.")

if __name__ == "__main__":
    print(f"============================================")
    print(f"  Starting Supabase Sync - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"============================================")
    try:
        sync_table("flight_prices")
        sync_table("flight_details")
        print("Master Sync complete.")
        manage_storage()
    except Exception as e:
        print(f"Sync script failed: {e}")
