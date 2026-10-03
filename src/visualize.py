"""
Visualization module for Aviation Delay Economics.
Generates publication-quality charts for the Jupyter Notebook and Executive Report:
1. Carrier On-Time Performance & Airborne Absorption
2. Sequential Leg Delay Cascades (WN vs UA vs DL vs AA)
3. The Hold-vs-Pushback Economic Decision Heatmap
"""

import os
import sqlite3
import matplotlib.pyplot as plt
import seaborn as sns
import pandas as pd
import numpy as np

from src.delay_economics import (
    get_connection,
    compute_carrier_benchmarks,
    compute_tail_rotation_cascades,
    generate_decision_matrix
)

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FIGURES_DIR = os.path.join(BASE_DIR, "reports", "figures")


def set_plot_style():
    """Sets a clean, modern aesthetic with high contrast and executive polish."""
    sns.set_theme(style="whitegrid", font="sans-serif")
    plt.rcParams["font.sans-serif"] = ["Helvetica", "Arial", "DejaVu Sans"]
    plt.rcParams["axes.edgecolor"] = "#cccccc"
    plt.rcParams["axes.linewidth"] = 0.8


def plot_carrier_benchmarks(conn: sqlite3.Connection, save_path: str = None):
    """Figure 1: Carrier Departure Delay vs In-Flight Buffer Absorption."""
    df = compute_carrier_benchmarks(conn)
    set_plot_style()

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5))

    # Barplot 1: Average Delays
    carrier_colors = {"AA": "#0078D7", "DL": "#003366", "UA": "#002244", "WN": "#FFBF00"}
    palette = [carrier_colors.get(c, "#666666") for c in df["carrier"]]

    bars = ax1.bar(df["carrier"], df["mean_dep_delay"], color=palette, width=0.55, edgecolor="#222222", linewidth=0.5)
    ax1.set_title("Average Departure Delay by Carrier (NYC Hubs)", fontsize=13, fontweight="bold", pad=12)
    ax1.set_ylabel("Mean Departure Delay (Minutes)", fontsize=11)
    ax1.set_xlabel("Carrier Code", fontsize=11)
    ax1.axhline(15, color="#D9534F", linestyle="--", linewidth=1.2, label="FAA A14 Threshold (15 min)")
    ax1.legend(loc="upper left")

    # Add data labels
    for bar in bars:
        yval = bar.get_height()
        ax1.text(bar.get_x() + bar.get_width()/2.0, yval + 0.4, f"{yval:.1f}m", ha="center", va="bottom", fontweight="bold", fontsize=10)

    # Barplot 2: On-Time Rates (A14)
    x = np.arange(len(df))
    width = 0.35
    ax2.bar(x - width/2, df["a14_dep_rate"], width, label="A14 Departure On-Time %", color="#2ECC71", edgecolor="#222222", linewidth=0.5)
    ax2.bar(x + width/2, df["a14_arr_rate"], width, label="A14 Arrival On-Time %", color="#3498DB", edgecolor="#222222", linewidth=0.5)
    ax2.set_xticks(x)
    ax2.set_xticklabels(df["carrier"])
    ax2.set_title("On-Time Performance (A14 Arrival vs Departure)", fontsize=13, fontweight="bold", pad=12)
    ax2.set_ylabel("Flights Arriving/Departing <= 15m (%)", fontsize=11)
    ax2.set_ylim(60, 95)
    ax2.legend(loc="lower right")

    plt.tight_layout()
    if save_path:
        os.makedirs(os.path.dirname(save_path), exist_ok=True)
        plt.savefig(save_path, dpi=300)
        print(f"📊 Saved Figure 1 to: {save_path}")
    plt.close()


def plot_cascade_dynamics(conn: sqlite3.Connection, save_path: str = None):
    """Figure 2: Turnaround Buffer Depletion & Delay Cascade (Point-to-Point vs Hub-and-Spoke)."""
    df = compute_tail_rotation_cascades(conn)
    set_plot_style()

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5))

    # Cascade Probability
    bars1 = ax1.bar(df["carrier"], df["cascade_probability_pct"], color="#E67E22", width=0.55, edgecolor="#222222", linewidth=0.5)
    ax1.set_title("Delay Cascade Probability (Leg 1 > 15m → Leg 2 > 15m)", fontsize=13, fontweight="bold", pad=12)
    ax1.set_ylabel("Probability Delay Propagates (%)", fontsize=11)
    ax1.set_xlabel("Carrier Code", fontsize=11)
    ax1.set_ylim(40, 80)
    for bar in bars1:
        yval = bar.get_height()
        ax1.text(bar.get_x() + bar.get_width()/2.0, yval + 0.8, f"{yval:.1f}%", ha="center", va="bottom", fontweight="bold", fontsize=10)

    # Average Leg 2 Delay
    bars2 = ax2.bar(df["carrier"], df["avg_leg2_delay"], color="#C0392B", width=0.55, edgecolor="#222222", linewidth=0.5)
    ax2.set_title("Downstream Delay Amplification (Subsequent Leg Delay)", fontsize=13, fontweight="bold", pad=12)
    ax2.set_ylabel("Mean Subsequent Leg Delay (Minutes)", fontsize=11)
    ax2.set_xlabel("Carrier Code", fontsize=11)
    for bar in bars2:
        yval = bar.get_height()
        ax2.text(bar.get_x() + bar.get_width()/2.0, yval + 0.6, f"{yval:.1f}m", ha="center", va="bottom", fontweight="bold", fontsize=10)

    plt.tight_layout()
    if save_path:
        os.makedirs(os.path.dirname(save_path), exist_ok=True)
        plt.savefig(save_path, dpi=300)
        print(f"📊 Saved Figure 2 to: {save_path}")
    plt.close()


def plot_hold_decision_matrix(save_path: str = None):
    """Figure 3: Net Economic Value Heatmap & Break-Even Curve."""
    matrix_df = generate_decision_matrix(
        hold_times=[5, 10, 15, 20, 25, 30],
        pax_ranges=[1, 3, 5, 8, 10, 12, 15, 20]
    )
    set_plot_style()

    pax_cols = [c for c in matrix_df.columns if c.startswith("pax_")]
    heatmap_data = matrix_df[pax_cols].copy()
    heatmap_data.index = [f"{t} min" for t in matrix_df["hold_minutes"]]
    heatmap_data.columns = [c.replace("pax_", "") + " Pax" for c in pax_cols]

    plt.figure(figsize=(10, 6))
    sns.heatmap(
        heatmap_data,
        annot=True,
        fmt=",.0f",
        cmap="vlag",
        center=0,
        cbar_kws={"label": "Net Economic Profit / Loss ($)"},
        linewidths=0.5,
        linecolor="#dddddd"
    )
    plt.title("The 'Hold vs. Pushback' Economic Decision Matrix\n(Net Value = Passenger Protection Value - FAA Delay Costs)", fontsize=13, fontweight="bold", pad=15)
    plt.xlabel("Connecting Passengers Protected (N)", fontsize=11, fontweight="bold")
    plt.ylabel("Gate Hold Duration (Minutes)", fontsize=11, fontweight="bold")

    plt.tight_layout()
    if save_path:
        os.makedirs(os.path.dirname(save_path), exist_ok=True)
        plt.savefig(save_path, dpi=300)
        print(f"📊 Saved Figure 3 to: {save_path}")
    plt.close()


def generate_all_figures():
    """Generates all 3 key figures for the report."""
    conn = get_connection()
    fig1 = os.path.join(FIGURES_DIR, "fig1_carrier_benchmarks.png")
    fig2 = os.path.join(FIGURES_DIR, "fig2_delay_cascades.png")
    fig3 = os.path.join(FIGURES_DIR, "fig3_hold_decision_matrix.png")

    plot_carrier_benchmarks(conn, fig1)
    plot_cascade_dynamics(conn, fig2)
    plot_hold_decision_matrix(fig3)
    conn.close()
    print("✅ All figures generated successfully in reports/figures/")


if __name__ == "__main__":
    generate_all_figures()
