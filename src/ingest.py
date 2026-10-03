"""
Data ingestion pipeline for Aviation Flight Delay & Connection Economics Analyzer.
Loads nycflights13 tables into a relational SQLite database (data/flights.db)
with explicit types, primary keys, and indexes for fast DBeaver & SQL querying.
"""

import os
import sqlite3
import pandas as pd
import nycflights13


BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")
DB_PATH = os.path.join(DATA_DIR, "flights.db")


def create_schema(conn: sqlite3.Connection):
    """Creates the relational schema with indexes."""
    cursor = conn.cursor()

    cursor.executescript("""
    CREATE TABLE IF NOT EXISTS airlines (
        carrier TEXT PRIMARY KEY,
        name TEXT NOT NULL
    );

    CREATE TABLE IF NOT EXISTS airports (
        faa TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        lat REAL,
        lon REAL,
        alt REAL,
        tz REAL,
        dst TEXT,
        tzone TEXT
    );

    CREATE TABLE IF NOT EXISTS planes (
        tailnum TEXT PRIMARY KEY,
        year INTEGER,
        type TEXT,
        manufacturer TEXT,
        model TEXT,
        engines INTEGER,
        seats INTEGER,
        speed REAL,
        engine TEXT
    );

    CREATE TABLE IF NOT EXISTS weather (
        origin TEXT NOT NULL,
        year INTEGER NOT NULL,
        month INTEGER NOT NULL,
        day INTEGER NOT NULL,
        hour INTEGER NOT NULL,
        temp REAL,
        dewp REAL,
        humid REAL,
        wind_dir REAL,
        wind_speed REAL,
        wind_gust REAL,
        precip REAL,
        pressure REAL,
        visib REAL,
        time_hour TEXT NOT NULL
    );

    CREATE TABLE IF NOT EXISTS flights (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        year INTEGER NOT NULL,
        month INTEGER NOT NULL,
        day INTEGER NOT NULL,
        dep_time REAL,
        sched_dep_time INTEGER NOT NULL,
        dep_delay REAL,
        arr_time REAL,
        sched_arr_time INTEGER NOT NULL,
        arr_delay REAL,
        carrier TEXT NOT NULL,
        flight INTEGER NOT NULL,
        tailnum TEXT,
        origin TEXT NOT NULL,
        dest TEXT NOT NULL,
        air_time REAL,
        distance REAL NOT NULL,
        hour INTEGER NOT NULL,
        minute INTEGER NOT NULL,
        time_hour TEXT NOT NULL,
        FOREIGN KEY (carrier) REFERENCES airlines(carrier),
        FOREIGN KEY (tailnum) REFERENCES planes(tailnum),
        FOREIGN KEY (origin) REFERENCES airports(faa)
    );
    """)

    conn.commit()


def create_indexes(conn: sqlite3.Connection):
    """Creates performance indexes for filtering and joins."""
    cursor = conn.cursor()
    cursor.executescript("""
    CREATE INDEX IF NOT EXISTS idx_flights_carrier ON flights(carrier);
    CREATE INDEX IF NOT EXISTS idx_flights_origin ON flights(origin);
    CREATE INDEX IF NOT EXISTS idx_flights_dest ON flights(dest);
    CREATE INDEX IF NOT EXISTS idx_flights_tailnum ON flights(tailnum);
    CREATE INDEX IF NOT EXISTS idx_flights_date ON flights(year, month, day);
    CREATE INDEX IF NOT EXISTS idx_flights_time_hour ON flights(time_hour);
    CREATE INDEX IF NOT EXISTS idx_weather_origin_time ON weather(origin, year, month, day, hour);
    """)
    conn.commit()


def ingest_data(db_path: str = DB_PATH):
    """Extracts tables from nycflights13 package and populates SQLite database."""
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    conn = sqlite3.connect(db_path)

    print("🛠️  Creating database schema...")
    create_schema(conn)

    print("📦 Loading airlines...")
    nycflights13.airlines.to_sql("airlines", conn, if_exists="replace", index=False)

    print("📦 Loading airports...")
    nycflights13.airports.to_sql("airports", conn, if_exists="replace", index=False)

    print("📦 Loading planes...")
    nycflights13.planes.to_sql("planes", conn, if_exists="replace", index=False)

    print("📦 Loading weather (26k+ hourly records)...")
    nycflights13.weather.to_sql("weather", conn, if_exists="replace", index=False)

    print("📦 Loading flights (336k+ departure records)...")
    flights_df = nycflights13.flights.copy()
    flights_df.insert(0, "flight_id", range(1, len(flights_df) + 1))
    flights_df.to_sql("flights", conn, if_exists="replace", index=False)

    print("⚡ Building indexes for high-speed queries...")
    create_indexes(conn)

    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM flights")
    flight_count = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(DISTINCT carrier) FROM flights")
    carrier_count = cursor.fetchone()[0]

    conn.close()

    print(f"\n✅ Ingestion complete! Database stored at: {db_path}")
    print(f"   • Total Flights: {flight_count:,}")
    print(f"   • Active Carriers: {carrier_count}")
    return flight_count


if __name__ == "__main__":
    ingest_data()
