"""
Unit tests for Aviation Delay Economics calculations and matrices.
"""

import os
import sqlite3
import pytest
from src.delay_economics import (
    get_connection,
    compute_carrier_benchmarks,
    compute_tail_rotation_cascades,
    calculate_hold_economics,
    generate_decision_matrix
)

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, "data", "flights.db")


@pytest.fixture(scope="module")
def conn():
    conn = get_connection(DB_PATH)
    yield conn
    conn.close()


def test_carrier_benchmarks(conn):
    df = compute_carrier_benchmarks(conn)
    assert not df.empty, "Carrier benchmarks should not be empty"
    carriers = set(df["carrier"].tolist())
    assert {"UA", "DL", "WN", "AA"}.issubset(carriers)
    
    # Verify expected metrics exist
    for col in ["total_flights", "mean_dep_delay", "mean_arr_delay", "a14_dep_rate", "mean_airborne_recovery"]:
        assert col in df.columns
        assert not df[col].isnull().any()


def test_tail_rotation_cascades(conn):
    df = compute_tail_rotation_cascades(conn)
    assert not df.empty, "Cascade DataFrame should not be empty"
    assert "cascade_probability_pct" in df.columns
    assert "buffer_absorption_pct" in df.columns


def test_calculate_hold_economics_breakeven():
    # 15 minutes hold, 10 passengers connecting
    res = calculate_hold_economics(
        hold_minutes=15,
        connecting_pax=10,
        cost_per_block_minute=85.0,
        cost_per_misconnected_pax=350.0,
        cascade_factor=0.40,
        remaining_downstream_legs=3
    )
    # Direct cost = 15 * 85 = 1275
    # Cascading cost = 15 * 0.40 * 3 * 85 = 1530
    # Total cost = 1275 + 1530 = 2805
    # Pax protection value = 10 * 350 = 3500
    # Net value = 3500 - 2805 = +695
    assert res["direct_cost"] == 1275.0
    assert res["cascading_cost"] == 1530.0
    assert res["total_cost"] == 2805.0
    assert res["pax_protection_value"] == 3500.0
    assert res["net_value"] == 695.0
    assert res["recommended_action"] == "HOLD FLIGHT"
    # Breakeven pax = 2805 / 350 = 8.01 -> 8.0
    assert res["breakeven_pax"] == 8.0


def test_calculate_hold_economics_pushback():
    # 15 minutes hold, only 2 passengers connecting
    res = calculate_hold_economics(
        hold_minutes=15,
        connecting_pax=2,
        cost_per_block_minute=85.0,
        cost_per_misconnected_pax=350.0,
        cascade_factor=0.40,
        remaining_downstream_legs=3
    )
    # Total cost = 2805
    # Pax value = 2 * 350 = 700
    # Net value = 700 - 2805 = -2105
    assert res["net_value"] == -2105.0
    assert res["recommended_action"] == "PUSHBACK ON TIME"


def test_generate_decision_matrix():
    matrix = generate_decision_matrix(
        hold_times=[5, 10, 15],
        pax_ranges=[1, 5, 10]
    )
    assert len(matrix) == 3
    assert "breakeven_pax" in matrix.columns
    assert "pax_1" in matrix.columns
    assert "pax_5" in matrix.columns
    assert "pax_10" in matrix.columns
