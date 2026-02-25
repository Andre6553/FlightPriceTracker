"""
FlySafair Price Tracker - Database Manager
Handles all SQLite database operations for storing and retrieving flight prices.
"""
import sqlite3
import pandas as pd
from datetime import datetime
import os

DB_PATH = 'flights.db'


def _get_db_path():
    """Get absolute path to the database file."""
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), DB_PATH)


def init_db():
    """Initialize the SQLite database and create tables."""
    conn = sqlite3.connect(_get_db_path())
    cursor = conn.cursor()

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS flight_prices (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            route TEXT NOT NULL,
            flight_date DATE NOT NULL,
            departure_time TEXT NOT NULL,
            scrape_datetime DATETIME NOT NULL,
            days_before_flight INTEGER NOT NULL,
            price REAL NOT NULL
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS flight_details (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            route TEXT NOT NULL,
            flight_date DATE NOT NULL,
            flight_number TEXT NOT NULL,
            departure_time TEXT NOT NULL,
            arrival_time TEXT NOT NULL,
            price REAL NOT NULL,
            is_cheapest INTEGER DEFAULT 0,
            is_special INTEGER DEFAULT 0,
            scrape_datetime DATETIME NOT NULL,
            days_before_flight INTEGER NOT NULL
        )
    ''')

    conn.commit()
    conn.close()


def save_flight_price(route, flight_date, departure_time, scrape_datetime, days_before_flight, price):
    """Save a single scraped flight price to the database."""
    conn = sqlite3.connect(_get_db_path())
    cursor = conn.cursor()

    cursor.execute('''
        INSERT INTO flight_prices (route, flight_date, departure_time, scrape_datetime, days_before_flight, price)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (route, flight_date, departure_time, scrape_datetime, days_before_flight, price))

    conn.commit()
    conn.close()


def get_all_data():
    """Return all flight data as a pandas DataFrame for analysis."""
    conn = sqlite3.connect(_get_db_path())
    df = pd.read_sql_query("SELECT * FROM flight_prices", conn)
    conn.close()
    return df


def save_flight_detail(route, flight_date, flight_number, departure_time, arrival_time,
                       price, is_cheapest, is_special, scrape_datetime, days_before_flight):
    """Save a single flight detail (from the flight selection page) to the database."""
    conn = sqlite3.connect(_get_db_path())
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO flight_details
        (route, flight_date, flight_number, departure_time, arrival_time,
         price, is_cheapest, is_special, scrape_datetime, days_before_flight)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (route, flight_date, flight_number, departure_time, arrival_time,
          price, is_cheapest, is_special, scrape_datetime, days_before_flight))
    conn.commit()
    conn.close()


def get_flight_details_data():
    """Return all flight details as a pandas DataFrame."""
    conn = sqlite3.connect(_get_db_path())
    try:
        df = pd.read_sql_query("SELECT * FROM flight_details", conn)
    except Exception:
        df = pd.DataFrame()
    conn.close()
    return df


if __name__ == "__main__":
    init_db()
    print("Database initialized successfully.")
