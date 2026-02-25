"""
FlySafair Dashboard Server
Opens the dashboard in your browser via a local HTTP server.
Includes API endpoints for manual scraping and flight date advice.
"""
import http.server
import webbrowser
import threading
import os
import subprocess
import json
import sqlite3
from urllib.parse import urlparse, parse_qs
from datetime import datetime

PORT = 8888
DIRECTORY = os.path.dirname(os.path.abspath(__file__))
VENV_PYTHON = os.path.join(DIRECTORY, "venv", "Scripts", "python.exe")
DB_PATH = os.path.join(DIRECTORY, "flights.db")

scrape_lock = threading.Lock()
scrape_running = False


def run_scrape_job():
    global scrape_running
    try:
        subprocess.run([VENV_PYTHON, os.path.join(DIRECTORY, "scraper.py")],
                       cwd=DIRECTORY, timeout=600)
        subprocess.run([VENV_PYTHON, os.path.join(DIRECTORY, "analyzer.py")],
                       cwd=DIRECTORY, timeout=60)
    except Exception as e:
        print(f"Scrape error: {e}")
    finally:
        with scrape_lock:
            scrape_running = False
        print("Manual check complete!")


def get_flight_advice(flight_date_str):
    """Analyze collected data to give booking advice for a specific flight date."""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        # Get all price records for this flight date
        cursor.execute("""
            SELECT route, price, scrape_datetime, days_before_flight
            FROM flight_prices
            WHERE flight_date = ?
            ORDER BY scrape_datetime
        """, (flight_date_str,))
        rows = cursor.fetchall()

        if not rows:
            # No exact data — use pattern-based advice from similar days
            flight_date = datetime.strptime(flight_date_str, "%Y-%m-%d")
            day_of_week = flight_date.strftime("%A")
            days_until = (flight_date - datetime.now()).days

            # Get average price for similar days_before_flight range
            cursor.execute("""
                SELECT route, AVG(price), MIN(price), COUNT(*)
                FROM flight_prices
                WHERE days_before_flight BETWEEN ? AND ?
                GROUP BY route
            """, (max(0, days_until - 3), days_until + 3))
            similar = cursor.fetchall()

            conn.close()
            return {
                "date": flight_date_str,
                "day_of_week": day_of_week,
                "days_until": days_until,
                "has_data": False,
                "similar_prices": [
                    {"route": r[0], "avg_price": round(r[1], 2),
                     "min_price": round(r[2], 2), "samples": r[3]}
                    for r in similar
                ],
                "advice": get_booking_advice(days_until, conn=None)
            }

        # We have data for this exact date
        flight_date = datetime.strptime(flight_date_str, "%Y-%m-%d")
        day_of_week = flight_date.strftime("%A")
        days_until = (flight_date - datetime.now()).days

        # Current prices per route (latest scrape)
        route_prices = {}
        price_history = {}
        for route, price, scrape_dt, days_before in rows:
            if route not in route_prices:
                route_prices[route] = []
                price_history[route] = []
            route_prices[route].append({"price": price, "scrape": scrape_dt, "days_before": days_before})
            price_history[route].append({"price": price, "scrape": scrape_dt})

        # Build route summary
        routes = []
        for route, entries in route_prices.items():
            prices = [e["price"] for e in entries]
            latest = entries[-1]
            first = entries[0]
            trend = "stable"
            if len(prices) > 1:
                if latest["price"] < first["price"]:
                    trend = "dropping"
                elif latest["price"] > first["price"]:
                    trend = "rising"

            routes.append({
                "route": route,
                "current_price": latest["price"],
                "lowest_seen": min(prices),
                "highest_seen": max(prices),
                "avg_price": round(sum(prices) / len(prices), 2),
                "checks": len(prices),
                "trend": trend,
                "history": price_history[route]
            })

        # Get overall booking window pattern
        cursor.execute("""
            SELECT days_before_flight, AVG(price)
            FROM flight_prices
            WHERE days_before_flight > 0
            GROUP BY days_before_flight
            ORDER BY AVG(price)
            LIMIT 5
        """)
        best_windows = cursor.fetchall()

        # Count unique scrape days (to know if day/hour data is meaningful)
        cursor.execute("SELECT COUNT(DISTINCT DATE(scrape_datetime)) FROM flight_prices")
        unique_scrape_days = cursor.fetchone()[0]

        # Best day of week to book PER ROUTE
        cursor.execute("""
            SELECT route,
                CASE CAST(strftime('%w', scrape_datetime) AS INTEGER)
                    WHEN 0 THEN 'Sunday' WHEN 1 THEN 'Monday' WHEN 2 THEN 'Tuesday'
                    WHEN 3 THEN 'Wednesday' WHEN 4 THEN 'Thursday'
                    WHEN 5 THEN 'Friday' WHEN 6 THEN 'Saturday'
                END as book_day,
                AVG(price) as avg_price
            FROM flight_prices
            WHERE days_before_flight > 0
            GROUP BY route, book_day
            ORDER BY route, avg_price
        """)
        route_book_days = {}
        for r in cursor.fetchall():
            if r[0] not in route_book_days:
                route_book_days[r[0]] = []
            route_book_days[r[0]].append({"day": r[1], "avg_price": round(r[2], 2)})

        # Best hour of day to book PER ROUTE
        cursor.execute("""
            SELECT route,
                CAST(strftime('%H', scrape_datetime) AS INTEGER) as book_hour,
                AVG(price) as avg_price
            FROM flight_prices
            WHERE days_before_flight > 0
            GROUP BY route, book_hour
            ORDER BY route, avg_price
        """)
        route_book_hours = {}
        for r in cursor.fetchall():
            if r[0] not in route_book_hours:
                route_book_hours[r[0]] = []
            route_book_hours[r[0]].append({"hour": f"{r[1]:02d}:00", "avg_price": round(r[2], 2)})

        conn.close()

        return {
            "date": flight_date_str,
            "day_of_week": day_of_week,
            "days_until": days_until,
            "has_data": True,
            "routes": routes,
            "best_windows": [{"days": int(w[0]), "avg_price": round(w[1], 2)} for w in best_windows],
            "route_book_days": route_book_days,
            "route_book_hours": route_book_hours,
            "unique_scrape_days": unique_scrape_days,
            "advice": get_booking_advice(days_until, routes)
        }

    except Exception as e:
        return {"error": str(e)}


def get_booking_advice(days_until, routes=None):
    """Generate human-readable booking advice."""
    if days_until < 0:
        return "This date has already passed."
    if days_until == 0:
        return "This flight is today! Book immediately if seats are available."
    if days_until <= 2:
        return "Very short notice — prices are likely at their highest. Book only if you must travel."

    # Check if prices are dropping
    if routes:
        dropping = [r for r in routes if r.get("trend") == "dropping"]
        rising = [r for r in routes if r.get("trend") == "rising"]
        if dropping and not rising:
            return f"Prices are DROPPING — consider waiting a bit longer for a better deal. You have {days_until} days."
        if rising and not dropping:
            return f"Prices are RISING — book NOW before they go higher! {days_until} days until flight."

    if days_until > 90:
        return f"You have {days_until} days — plenty of time. Prices tend to be lowest 2-3 months before. Monitor and book when you see a dip."
    if days_until > 30:
        return f"You have {days_until} days — good window. Watch for price drops and book within the next few weeks."
    if days_until > 14:
        return f"{days_until} days left — prices may start rising soon. Consider booking this week."
    if days_until > 7:
        return f"Only {days_until} days left — book soon! Prices typically increase in the last week."
    return f"Only {days_until} days away — book NOW for the best remaining price."


def get_price_detail(route, price_type="min"):
    """Get details of when a route's min or max price was recorded."""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        # Find the target price
        agg = "MIN" if price_type == "min" else "MAX"
        cursor.execute(f"SELECT {agg}(price) FROM flight_prices WHERE route = ?", (route,))
        target_price = cursor.fetchone()[0]
        if target_price is None:
            conn.close()
            return {"error": "No data for this route"}

        # Get all records matching this price
        cursor.execute("""
            SELECT flight_date, scrape_datetime, price, days_before_flight
            FROM flight_prices
            WHERE route = ? AND price = ?
            ORDER BY scrape_datetime DESC
        """, (route, target_price))
        rows = cursor.fetchall()
        conn.close()

        day_names = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
        records = []
        for r in rows:
            flight_dt = datetime.strptime(r[0], "%Y-%m-%d")
            scrape_dt = datetime.strptime(r[1], "%Y-%m-%d %H:%M:%S") if " " in r[1] else datetime.strptime(r[1], "%Y-%m-%dT%H:%M:%S")
            records.append({
                "flight_date": r[0],
                "flight_day": day_names[flight_dt.weekday()],
                "scrape_time": scrape_dt.strftime("%Y-%m-%d %H:%M"),
                "price": r[2],
                "days_before": r[3]
            })

        return {
            "route": route,
            "type": price_type,
            "price": target_price,
            "occurrences": len(records),
            "records": records[:20]  # limit to 20 most recent
        }
    except Exception as e:
        return {"error": str(e)}


class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=DIRECTORY, **kwargs)

    def log_message(self, format, *args):
        pass

    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path == "/api/check-now":
            self.handle_check_now()
        elif parsed.path == "/api/status":
            self.handle_status()
        elif parsed.path == "/api/last-update":
            self.handle_last_update()
        elif parsed.path == "/api/flight-advice":
            params = parse_qs(parsed.query)
            date = params.get("date", [None])[0]
            if date:
                self.send_json(get_flight_advice(date))
            else:
                self.send_json({"error": "Please provide a ?date=YYYY-MM-DD parameter"})
        elif parsed.path == "/api/price-detail":
            params = parse_qs(parsed.query)
            route = params.get("route", [None])[0]
            price_type = params.get("type", ["min"])[0]  # min or max
            if route:
                self.send_json(get_price_detail(route, price_type))
            else:
                self.send_json({"error": "Please provide ?route=CPT-JNB&type=min"})
        else:
            # Add no-cache headers for dashboard.html
            if parsed.path == "/dashboard.html" or parsed.path == "/":
                self.send_response(200)
                self.send_header("Content-Type", "text/html")
                self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
                self.send_header("Pragma", "no-cache")
                self.send_header("Expires", "0")
                self.end_headers()
                dash_path = os.path.join(DIRECTORY, "dashboard.html")
                if os.path.exists(dash_path):
                    with open(dash_path, "rb") as f:
                        self.wfile.write(f.read())
                return
            super().do_GET()

    def handle_check_now(self):
        global scrape_running
        with scrape_lock:
            if scrape_running:
                self.send_json({"status": "already_running"})
                return
            scrape_running = True
        t = threading.Thread(target=run_scrape_job, daemon=True)
        t.start()
        self.send_json({"status": "started"})

    def handle_status(self):
        self.send_json({"running": scrape_running})

    def handle_last_update(self):
        """Return the last modification time of dashboard.html."""
        dash_path = os.path.join(DIRECTORY, "dashboard.html")
        if os.path.exists(dash_path):
            mtime = os.path.getmtime(dash_path)
            self.send_json({"last_update": mtime})
        else:
            self.send_json({"last_update": 0})

    def send_json(self, data):
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(json.dumps(data).encode())


def open_browser():
    webbrowser.open(f"http://localhost:{PORT}/dashboard.html")


if __name__ == "__main__":
    print(f"Dashboard server running at http://localhost:{PORT}/dashboard.html")
    print("API endpoints:")
    print(f"  GET /api/check-now          - Trigger manual scrape")
    print(f"  GET /api/status             - Check if scrape is running")
    print(f"  GET /api/flight-advice?date= - Get booking advice for a date")
    print("Press Ctrl+C to stop.\n")

    threading.Timer(1.0, open_browser).start()

    try:
        with http.server.HTTPServer(("", PORT), Handler) as httpd:
            httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nServer stopped.")
