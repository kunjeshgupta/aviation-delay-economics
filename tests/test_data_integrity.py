"""
TDD verification suite for Aviation Delay Economics data pipeline.
Validates table creation, row counts, key carrier presence (UA, DL, WN, AA),
and relational join integrity for DBeaver & SQL analytics.
"""

import os
import sqlite3
import pytest

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, "data", "flights.db")


@pytest.fixture(scope="module")
def db_conn():
    assert os.path.exists(DB_PATH), f"Database file not found at {DB_PATH}. Run src/ingest.py first."
    conn = sqlite3.connect(DB_PATH)
    yield conn
    conn.close()


def test_required_tables_exist(db_conn):
    cursor = db_conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = {row[0] for row in cursor.fetchall()}
    expected_tables = {"flights", "airlines", "airports", "planes", "weather"}
    assert expected_tables.issubset(tables), f"Missing tables: {expected_tables - tables}"


def test_flight_row_count(db_conn):
    cursor = db_conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM flights")
    count = cursor.fetchone()[0]
    assert count == 336776, f"Expected 336,776 flights, but got {count:,}"


def test_target_carriers_present(db_conn):
    cursor = db_conn.cursor()
    cursor.execute("SELECT DISTINCT carrier FROM flights")
    carriers = {row[0] for row in cursor.fetchall()}
    target_carriers = {"UA", "DL", "WN", "AA"}
    assert target_carriers.issubset(carriers), f"Missing target carriers: {target_carriers - carriers}"


def test_carrier_flight_volumes(db_conn):
    cursor = db_conn.cursor()
    cursor.execute("""
        SELECT carrier, COUNT(*) 
        FROM flights 
        WHERE carrier IN ('UA', 'DL', 'WN', 'AA')
        GROUP BY carrier
    """)
    volumes = dict(cursor.fetchall())
    # UA, DL, AA, WN should all have significant flight counts in NYC 2013
    assert volumes["UA"] > 50000, f"UA volume unexpectedly low: {volumes.get('UA')}"
    assert volumes["DL"] > 40000, f"DL volume unexpectedly low: {volumes.get('DL')}"
    assert volumes["AA"] > 30000, f"AA volume unexpectedly low: {volumes.get('AA')}"
    assert volumes["WN"] > 10000, f"WN volume unexpectedly low: {volumes.get('WN')}"


def test_relational_join_integrity(db_conn):
    cursor = db_conn.cursor()
    # Test joining flights with airlines and planes
    cursor.execute("""
        SELECT f.carrier, a.name, COUNT(f.flight_id) as flight_count, AVG(p.seats) as avg_seats
        FROM flights f
        JOIN airlines a ON f.carrier = a.carrier
        LEFT JOIN planes p ON f.tailnum = p.tailnum
        WHERE f.carrier IN ('UA', 'DL', 'WN')
        GROUP BY f.carrier, a.name
    """)
    rows = cursor.fetchall()
    assert len(rows) == 3, f"Expected 3 carrier join rows, got {len(rows)}"
    for carrier, name, cnt, avg_seats in rows:
        assert cnt > 0
        assert avg_seats is not None and avg_seats > 50, f"Unexpected seat average for {carrier}: {avg_seats}"
