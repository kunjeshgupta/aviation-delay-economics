# Aviation Flight Delay & Connection Economics Analyzer
### *The 15-Minute Hold Decision: Unit Economics, Turnaround Cascades, and Network Resilience*

**Author:** Kunjesh Gupta | MSBA, USC Marshall School of Business  
**Domain:** Airline Revenue Management & Network Operations Analytics  
**Tech Stack:** Python 3.9+, SQLite (`data/flights.db`), SQL (Postgres-compatible window functions), Pandas, Seaborn, Matplotlib, Pytest  
**Dataset:** Bureau of Transportation Statistics (`nycflights13` - 336,776 departure records across JFK, EWR, LGA)

---

## 1. Executive Summary & Business Problem

In commercial airline operations, an on-time departure is more than an FAA A14 operational metric—it represents an economic trade-off between **passenger lifetime value / connection protection** and **compounding network operating costs**.

When an inbound connecting flight is delayed by 10–15 minutes, the Operations Control Center (OCC) faces a high-stakes decision:
* **The Case for Holding Outbound (15 mins)**: Protects connecting passengers from missing high-yield transcontinental/international banks, avoiding DOT-mandated hotel vouchers, meal stipends, and rebooking costs (~$350 per disrupted passenger).
* **The Case for On-Time Pushback**: FAA direct block delay costs run at **~$85/minute** (gate fees, taxi fuel burn, crew duty limits). On high-utilization fleets, a 15-minute gate hold cascades across sequential flight legs of that aircraft, compounding network penalties.

This project analyzes 336k flights to benchmark **Hub-and-Spoke Legacy Carriers (United [UA], Delta [DL], American [AA])** against a **Point-to-Point Low-Cost Carrier (Southwest [WN])** and produces an optimal decision boundary for gate holds.

---

## 2. Key Analytical Findings

### 2.1. Carrier Delay Benchmarks & In-Flight Buffer Absorption
| Carrier | Carrier Name | Total Flights | Mean Dep Delay | Mean Arr Delay | Airborne Recovery | A14 Dep On-Time % | A14 Arr On-Time % | Late Dep Recovery Rate |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **UA** | United Air Lines Inc. | 57,782 | 12.02 min | 3.56 min | **+8.46 min** | 79.04% | 78.21% | **38.78%** |
| **DL** | Delta Air Lines Inc. | 47,658 | 9.22 min | 1.64 min | **+7.58 min** | 83.72% | 81.77% | 33.32% |
| **AA** | American Airlines Inc. | 31,947 | 8.57 min | 0.36 min | **+8.20 min** | 84.11% | 81.21% | 34.01% |
| **WN** | Southwest Airlines Co. | 12,044 | **17.66 min** | 9.65 min | **+8.01 min** | 73.13% | 75.14% | 34.31% |

* **Airborne Delay Absorption**: All carriers systematically pad flight schedules by **7.5 to 8.5 minutes**, enabling pilots to absorb departure delays en-route. For flights departing late, carriers recover to an on-time arrival 33%–39% of the time.

---

### 2.2. Turnaround Buffer Depletion & Delay Cascades (Sequential Tail Rotations)
Tracking sequential flight legs for identical aircraft (`tailnum`) on the same calendar day reveals contrasting operational resilience:

| Carrier | Multi-Leg Turns Analyzed | Avg Leg 1 Delay | Avg Leg 2 Delay | Cascade Probability (Leg 1 > 15m → Leg 2 > 15m) | Gate Buffer Absorption |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **AA** | 5,167 | -0.39 min | 13.25 min | 55.30% | **44.70%** |
| **DL** | 8,753 | 1.30 min | 15.90 min | 58.83% | **41.17%** |
| **UA** | 6,359 | 3.75 min | 21.49 min | 61.27% | **38.73%** |
| **WN** | 550 | 7.27 min | **34.97 min** | **69.62%** | **30.38%** |

* **The Southwest Cascade Vulnerability**: In Southwest's aggressive 25-minute turn model, when Leg 1 departs > 15 minutes late, **69.62%** of subsequent leg departures are also delayed, and downstream delay explodes to an average of **34.97 minutes**.
* **Legacy Resilience**: Legacy carriers with scheduled hub turnaround buffers absorb between **38.7% and 44.7%** of upstream delays at the gate.

---

### 2.3. The 15-Minute Hold Economic Decision Matrix
Using FAA benchmark operating costs ($85/block min) and passenger protection values ($350/misconnected passenger):

| Hold Duration | Break-Even Pax ($N^*$) | Total Delay Cost | Net Value: 1 Pax | Net Value: 3 Pax | Net Value: 5 Pax | Net Value: 8 Pax | Net Value: 12 Pax | Net Value: 15 Pax |
| :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **5 min** | **2.7 pax** | $935 | -$585 | +$115 | +$815 | +$1,865 | +$3,265 | +$4,315 |
| **10 min** | **5.3 pax** | $1,870 | -$1,520 | -$820 | -$120 | +$930 | +$2,330 | +$3,380 |
| **15 min** | **8.0 pax** | **$2,805** | -$2,455 | -$1,755 | -$1,055 | **-$5** | **+$1,395** | **+$2,445** |
| **20 min** | **10.7 pax** | $3,740 | -$3,390 | -$2,690 | -$1,990 | -$940 | +$460 | +$1,510 |
| **25 min** | **13.4 pax** | $4,675 | -$4,325 | -$3,625 | -$2,925 | -$1,875 | -$475 | +$575 |
| **30 min** | **16.0 pax** | $5,610 | -$5,260 | -$4,560 | -$3,860 | -$2,810 | -$1,410 | -$360 |

#### Executive Rule of Thumb:
* **The 8-Passenger Rule**: For a standard 15-minute gate hold, holding for **fewer than 8 connecting passengers is economically irrational**, causing net losses up to -$2,455. Holding for **12+ passengers generates +$1,395+ in positive financial return**.
* **Carrier Asymmetry**: Because Southwest faces a ~70% cascade rate and 35-minute downstream delay amplification, its break-even threshold rises to **12–14 passengers**, whereas United/Delta can afford holds at **7–8 passengers**.

---

## 3. How to Connect & Query with DBeaver

1. Open **DBeaver**.
2. Click **Database -> New Database Connection**.
3. Select **SQLite** and click **Next**.
4. In the **Path** field, click **Browse** and select:
   ```
   projects/aviation-delay-economics/data/flights.db
   ```
5. Click **Finish**. You can now:
   * View the complete ER diagram across `flights`, `airlines`, `planes`, `airports`, and `weather`.
   * Run custom SQL queries directly against the 336k indexed records.

---

## 4. Project Structure

```
projects/aviation-delay-economics/
├── data/
│   └── flights.db              <-- 336k relational SQLite database (view in DBeaver)
├── reports/
│   └── figures/
│       ├── fig1_carrier_benchmarks.png
│       ├── fig2_delay_cascades.png
│       └── fig3_hold_decision_matrix.png
├── src/
│   ├── ingest.py               <-- Ingestion pipeline with indexes & primary keys
│   ├── delay_economics.py      <-- Core analytical calculations & break-even logic
│   ├── visualize.py            <-- High-res chart generator
│   └── build_notebook.py       <-- Generates flight_delay_economics.ipynb
├── tests/
│   ├── test_data_integrity.py  <-- Pytest data verification (5 tests passing)
│   └── test_delay_economics.py <-- Pytest mathematical model verification (5 tests passing)
├── flight_delay_economics.ipynb<-- Publication-grade interactive notebook
├── requirements.txt
└── README.md
```

---

## 5. Resume Bullet Points (Tailored for Product / Strategy Analytics)

* **Aviation Revenue Management & Flight Delay Optimization Pipeline** *(Python, SQL, SQLite, Pandas, Seaborn)*
  * Architected an econometric decision engine analyzing 336k+ BTS flight records across NYC hubs (EWR, JFK, LGA) to model the "Hold vs. Pushback" trade-off between passenger connection protection and cascading network block costs.
  * Formulated an aircraft turnaround cascade model across sequential tail-number rotations; uncovered that point-to-point carriers (Southwest) face a 69.6% delay propagation probability compared to 58.8% for legacy hub-and-spoke carriers (Delta), amplifying downstream leg delays to 35 minutes.
  * Derived an optimal dispatch decision matrix with FAA block-hour cost functions ($85/min) and passenger re-accommodation values ($350/pax), establishing an 8-passenger break-even rule for 15-minute gate holds.
