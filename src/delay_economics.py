"""
Analytical engine for Aviation Flight Delay & Connection Economics.
Computes carrier delay benchmarks, in-flight buffer absorption,
turnaround buffers, delay cascade factors, and the optimal Hold-vs-Pushback decision matrix.
"""

import os
import sqlite3
import pandas as pd
import numpy as np

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, "data", "flights.db")


def get_connection(db_path: str = DB_PATH) -> sqlite3.Connection:
    """Returns a connection to the flights SQLite database."""
    return sqlite3.connect(db_path)


def compute_carrier_benchmarks(conn: sqlite3.Connection) -> pd.DataFrame:
    """
    Computes departure delay, arrival delay, and in-flight buffer absorption
    benchmarks for target carriers (UA, DL, WN, AA).
    
    Buffer absorption = dep_delay - arr_delay (minutes made up in the air).
    A14 Departure = % flights departing with <= 15 min delay.
    A14 Arrival = % flights arriving with <= 15 min delay.
    """
    query = """
    SELECT 
        f.carrier,
        a.name AS carrier_name,
        COUNT(*) AS total_flights,
        ROUND(AVG(f.dep_delay), 2) AS mean_dep_delay,
        ROUND(AVG(f.arr_delay), 2) AS mean_arr_delay,
        ROUND(AVG(f.dep_delay - f.arr_delay), 2) AS mean_airborne_recovery,
        ROUND(100.0 * SUM(CASE WHEN f.dep_delay <= 15 THEN 1 ELSE 0 END) / COUNT(*), 2) AS a14_dep_rate,
        ROUND(100.0 * SUM(CASE WHEN f.arr_delay <= 15 THEN 1 ELSE 0 END) / COUNT(*), 2) AS a14_arr_rate,
        ROUND(100.0 * SUM(CASE WHEN f.dep_delay > 0 AND f.arr_delay <= 0 THEN 1 ELSE 0 END) / 
              NULLIF(SUM(CASE WHEN f.dep_delay > 0 THEN 1 ELSE 0 END), 0), 2) AS late_dep_recovery_rate
    FROM flights f
    JOIN airlines a ON f.carrier = a.carrier
    WHERE f.carrier IN ('UA', 'DL', 'WN', 'AA')
      AND f.dep_delay IS NOT NULL
      AND f.arr_delay IS NOT NULL
    GROUP BY f.carrier, a.name
    ORDER BY total_flights DESC;
    """
    return pd.read_sql_query(query, conn)


def compute_tail_rotation_cascades(conn: sqlite3.Connection) -> pd.DataFrame:
    """
    Identifies sequential flight legs for identical aircraft (tailnum) on the same date.
    Measures delay propagation: how initial leg departure delays cascade into subsequent leg departures.
    """
    query = """
    WITH ordered_legs AS (
        SELECT 
            flight_id,
            carrier,
            tailnum,
            year,
            month,
            day,
            sched_dep_time,
            dep_delay,
            arr_delay,
            origin,
            dest,
            ROW_NUMBER() OVER (
                PARTITION BY tailnum, year, month, day 
                ORDER BY sched_dep_time
            ) AS leg_number
        FROM flights
        WHERE tailnum IS NOT NULL 
          AND tailnum != ''
          AND dep_delay IS NOT NULL
          AND carrier IN ('UA', 'DL', 'WN', 'AA')
    ),
    sequential_pairs AS (
        SELECT 
            cur.carrier,
            cur.tailnum,
            cur.year,
            cur.month,
            cur.day,
            cur.leg_number AS first_leg_num,
            cur.dep_delay AS leg1_dep_delay,
            cur.arr_delay AS leg1_arr_delay,
            nxt.dep_delay AS leg2_dep_delay,
            nxt.sched_dep_time - cur.sched_dep_time AS leg_time_delta
        FROM ordered_legs cur
        JOIN ordered_legs nxt 
          ON cur.tailnum = nxt.tailnum
         AND cur.year = nxt.year
         AND cur.month = nxt.month
         AND cur.day = nxt.day
         AND nxt.leg_number = cur.leg_number + 1
        WHERE cur.dep_delay IS NOT NULL 
          AND nxt.dep_delay IS NOT NULL
    )
    SELECT 
        carrier,
        COUNT(*) AS multi_leg_turns,
        ROUND(AVG(leg1_dep_delay), 2) AS avg_leg1_delay,
        ROUND(AVG(leg2_dep_delay), 2) AS avg_leg2_delay,
        ROUND(100.0 * SUM(CASE WHEN leg1_dep_delay > 15 AND leg2_dep_delay > 15 THEN 1 ELSE 0 END) /
              NULLIF(SUM(CASE WHEN leg1_dep_delay > 15 THEN 1 ELSE 0 END), 0), 2) AS cascade_probability_pct,
        ROUND(100.0 * SUM(CASE WHEN leg1_dep_delay > 15 AND leg2_dep_delay <= 15 THEN 1 ELSE 0 END) /
              NULLIF(SUM(CASE WHEN leg1_dep_delay > 15 THEN 1 ELSE 0 END), 0), 2) AS buffer_absorption_pct
    FROM sequential_pairs
    GROUP BY carrier;
    """
    return pd.read_sql_query(query, conn)


def calculate_hold_economics(
    hold_minutes: int,
    connecting_pax: int,
    cost_per_block_minute: float = 85.0,
    cost_per_misconnected_pax: float = 350.0,
    cascade_factor: float = 0.40,
    remaining_downstream_legs: int = 3
) -> dict:
    """
    Evaluates the net financial return of holding an outbound flight for connecting passengers.
    
    Formula:
      Direct Delay Cost = hold_minutes * cost_per_block_minute
      Cascading Network Delay Cost = hold_minutes * cascade_factor * remaining_downstream_legs * cost_per_block_minute
      Total Operational Cost = Direct Cost + Cascading Cost
      Passenger Protection Value = connecting_pax * cost_per_misconnected_pax
      Net Economic Value = Passenger Protection Value - Total Operational Cost
      Break-even Passengers = Total Operational Cost / cost_per_misconnected_pax
    """
    direct_cost = hold_minutes * cost_per_block_minute
    cascading_cost = hold_minutes * cascade_factor * remaining_downstream_legs * cost_per_block_minute
    total_cost = direct_cost + cascading_cost
    pax_protection_value = connecting_pax * cost_per_misconnected_pax
    net_value = pax_protection_value - total_cost
    breakeven_pax = total_cost / cost_per_misconnected_pax

    decision = "HOLD FLIGHT" if net_value >= 0 else "PUSHBACK ON TIME"

    return {
        "hold_minutes": hold_minutes,
        "connecting_pax": connecting_pax,
        "direct_cost": round(direct_cost, 2),
        "cascading_cost": round(cascading_cost, 2),
        "total_cost": round(total_cost, 2),
        "pax_protection_value": round(pax_protection_value, 2),
        "net_value": round(net_value, 2),
        "breakeven_pax": round(breakeven_pax, 1),
        "recommended_action": decision
    }


def generate_decision_matrix(
    hold_times: list = [5, 10, 15, 20, 25, 30],
    pax_ranges: list = [1, 3, 5, 8, 12, 15, 20],
    cascade_factor: float = 0.40,
    remaining_legs: int = 3
) -> pd.DataFrame:
    """Generates a matrix of Net Economic Value ($) across hold durations and connecting passenger counts."""
    matrix = []
    for t in hold_times:
        row = {"hold_minutes": t}
        # compute breakeven
        res_sample = calculate_hold_economics(
            hold_minutes=t,
            connecting_pax=1,
            cascade_factor=cascade_factor,
            remaining_downstream_legs=remaining_legs
        )
        row["breakeven_pax"] = res_sample["breakeven_pax"]
        row["total_delay_cost"] = res_sample["total_cost"]

        for p in pax_ranges:
            eval_res = calculate_hold_economics(
                hold_minutes=t,
                connecting_pax=p,
                cascade_factor=cascade_factor,
                remaining_downstream_legs=remaining_legs
            )
            row[f"pax_{p}"] = eval_res["net_value"]
        matrix.append(row)

    return pd.DataFrame(matrix)
