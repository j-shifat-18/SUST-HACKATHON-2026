"""
Synthetic Data Generator — Phase 1
Produces:
  - transactions.csv      (5,000-20,000 rows)
  - agents.csv
  - providers.csv
  - context_calendar.csv
  - injected_anomalies.csv  (ground truth for precision/recall)

Run: python data/generate_synthetic_data.py
"""
from __future__ import annotations

import csv
import random
import uuid
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np
from faker import Faker

fake = Faker("bn_BD")
rng = random.Random(42)
np.random.seed(42)

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
N_AGENTS = 10
N_TRANSACTIONS = 15_000
START_DATE = datetime(2026, 1, 1)
END_DATE = datetime(2026, 6, 30)
PROVIDERS = ["bkash", "nagad", "rocket"]
ANOMALY_RATE = 0.07  # 7% injected anomalies
OUTPUT_DIR = Path(__file__).parent

# ---------------------------------------------------------------------------
# Calendar events
# ---------------------------------------------------------------------------
CALENDAR_EVENTS = [
    {"date": "2026-01-01", "event_name": "New Year", "volume_multiplier": 1.8, "description": "New Year transactions spike"},
    {"date": "2026-03-26", "event_name": "Independence Day", "volume_multiplier": 2.0, "description": "Independence Day remittances"},
    {"date": "2026-04-14", "event_name": "Pohela Boishakh", "volume_multiplier": 2.5, "description": "Bengali New Year — highest cash-in day"},
    {"date": "2026-05-01", "event_name": "Salary Day", "volume_multiplier": 3.0, "description": "Monthly salary disbursement"},
    {"date": "2026-05-25", "event_name": "Eid ul-Fitr", "volume_multiplier": 4.0, "description": "Eid — peak MFS usage"},
    {"date": "2026-05-26", "event_name": "Eid ul-Fitr +1", "volume_multiplier": 3.5, "description": "Post-Eid gifting"},
    {"date": "2026-06-01", "event_name": "Salary Day", "volume_multiplier": 3.0, "description": "Monthly salary disbursement"},
]

TX_TYPES = ["cash_in", "cash_out", "transfer", "recharge"]
TX_TYPE_WEIGHTS = [0.35, 0.40, 0.15, 0.10]

# Normal transaction amount ranges (BDT)
AMOUNT_RANGES = {
    "cash_in":   (200, 30_000),
    "cash_out":  (100, 25_000),
    "transfer":  (500, 50_000),
    "recharge":  (50, 2_000),
}

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def random_date(start: datetime, end: datetime) -> datetime:
    delta = end - start
    return start + timedelta(seconds=rng.randint(0, int(delta.total_seconds())))


def event_multiplier(dt: datetime) -> float:
    date_str = dt.strftime("%Y-%m-%d")
    for ev in CALENDAR_EVENTS:
        if ev["date"] == date_str:
            return ev["volume_multiplier"]
    # Weekend bump
    if dt.weekday() >= 4:
        return 1.3
    return 1.0


def random_amount(tx_type: str) -> float:
    lo, hi = AMOUNT_RANGES[tx_type]
    return round(rng.uniform(lo, hi), 2)


def anonymise_account() -> str:
    return f"ACC{rng.randint(10000, 99999)}"


# ---------------------------------------------------------------------------
# Generate agents
# ---------------------------------------------------------------------------

def generate_agents() -> list[dict]:
    areas = ["Dhaka-North", "Dhaka-South", "Chittagong", "Sylhet", "Rajshahi"]
    regions = {"Dhaka-North": "Dhaka", "Dhaka-South": "Dhaka",
               "Chittagong": "Chittagong", "Sylhet": "Sylhet", "Rajshahi": "Rajshahi"}
    agents = []
    for i in range(N_AGENTS):
        area = rng.choice(areas)
        agents.append({
            "id": str(uuid.uuid4()),
            "name": f"Agent {i+1:02d}",
            "phone": f"+8801{rng.randint(700000000, 999999999)}",
            "area": area,
            "region": regions[area],
        })
    return agents


# ---------------------------------------------------------------------------
# Generate transactions (normal + injected anomalies)
# ---------------------------------------------------------------------------

def generate_transactions(agents: list[dict]) -> tuple[list[dict], list[dict]]:
    transactions = []
    injected = []

    n_normal = int(N_TRANSACTIONS * (1 - ANOMALY_RATE))
    n_anomaly = N_TRANSACTIONS - n_normal

    # Normal transactions
    for _ in range(n_normal):
        agent = rng.choice(agents)
        provider = rng.choice(PROVIDERS)
        tx_type = rng.choices(TX_TYPES, weights=TX_TYPE_WEIGHTS)[0]
        ts = random_date(START_DATE, END_DATE)
        multiplier = event_multiplier(ts)
        lo, hi = AMOUNT_RANGES[tx_type]
        amount = round(rng.uniform(lo * multiplier, hi * multiplier), 2)

        transactions.append({
            "id": str(uuid.uuid4()),
            "agent_id": agent["id"],
            "provider": provider,
            "transaction_type": tx_type,
            "amount": amount,
            "timestamp": ts.isoformat(),
            "area": agent["area"],
            "account_ref": anonymise_account(),
            "is_anomaly": False,
            "anomaly_type": "",
        })

    # Injected anomalies
    # 1. Velocity spikes — burst of transactions in 1 hour
    n_spikes = n_anomaly // 3
    for _ in range(n_spikes):
        agent = rng.choice(agents)
        provider = rng.choice(PROVIDERS)
        base_ts = random_date(START_DATE, END_DATE)
        burst_size = rng.randint(15, 30)
        group_ids = []
        for j in range(burst_size):
            tx_id = str(uuid.uuid4())
            ts = base_ts + timedelta(minutes=rng.randint(0, 55))
            amount = round(rng.uniform(5_000, 50_000), 2)
            group_ids.append(tx_id)
            transactions.append({
                "id": tx_id,
                "agent_id": agent["id"],
                "provider": provider,
                "transaction_type": "cash_out",
                "amount": amount,
                "timestamp": ts.isoformat(),
                "area": agent["area"],
                "account_ref": anonymise_account(),
                "is_anomaly": True,
                "anomaly_type": "velocity_spike",
            })
        injected.append({
            "anomaly_type": "velocity_spike",
            "agent_id": agent["id"],
            "transaction_ids": ";".join(group_ids),
            "description": f"Burst of {burst_size} large cash-outs in under 1 hour",
        })

    # 2. Splitting — repeated near-identical amounts
    n_splits = n_anomaly // 3
    for _ in range(n_splits):
        agent = rng.choice(agents)
        provider = rng.choice(PROVIDERS)
        base_ts = random_date(START_DATE, END_DATE)
        base_amount = round(rng.uniform(9_000, 9_900), 2)
        ref = anonymise_account()
        split_count = rng.randint(3, 6)
        group_ids = []
        for j in range(split_count):
            tx_id = str(uuid.uuid4())
            ts = base_ts + timedelta(minutes=j * rng.randint(5, 12))
            amount = round(base_amount * rng.uniform(0.97, 1.03), 2)
            group_ids.append(tx_id)
            transactions.append({
                "id": tx_id,
                "agent_id": agent["id"],
                "provider": provider,
                "transaction_type": "cash_out",
                "amount": amount,
                "timestamp": ts.isoformat(),
                "area": agent["area"],
                "account_ref": ref,
                "is_anomaly": True,
                "anomaly_type": "transaction_splitting",
            })
        injected.append({
            "anomaly_type": "transaction_splitting",
            "agent_id": agent["id"],
            "transaction_ids": ";".join(group_ids),
            "description": f"{split_count} near-identical amounts around ৳{base_amount:,.0f}",
        })

    # 3. Circular flows — cash-out followed by cash-in from same ref
    n_circular = n_anomaly - n_spikes - n_splits
    for _ in range(n_circular):
        agent = rng.choice(agents)
        provider = rng.choice(PROVIDERS)
        base_ts = random_date(START_DATE, END_DATE)
        amount = round(rng.uniform(5_000, 30_000), 2)
        ref = anonymise_account()
        out_id = str(uuid.uuid4())
        in_id = str(uuid.uuid4())
        transactions.append({
            "id": out_id,
            "agent_id": agent["id"],
            "provider": provider,
            "transaction_type": "cash_out",
            "amount": amount,
            "timestamp": base_ts.isoformat(),
            "area": agent["area"],
            "account_ref": ref,
            "is_anomaly": True,
            "anomaly_type": "circular_flow",
        })
        transactions.append({
            "id": in_id,
            "agent_id": agent["id"],
            "provider": provider,
            "transaction_type": "cash_in",
            "amount": round(amount * rng.uniform(0.95, 1.05), 2),
            "timestamp": (base_ts + timedelta(minutes=rng.randint(10, 180))).isoformat(),
            "area": agent["area"],
            "account_ref": ref,
            "is_anomaly": True,
            "anomaly_type": "circular_flow",
        })
        injected.append({
            "anomaly_type": "circular_flow",
            "agent_id": agent["id"],
            "transaction_ids": f"{out_id};{in_id}",
            "description": f"Round-trip ৳{amount:,.0f} to/from {ref}",
        })

    return transactions, injected


# ---------------------------------------------------------------------------
# Write CSVs
# ---------------------------------------------------------------------------

def write_csv(path: Path, rows: list[dict]) -> None:
    if not rows:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)
    print(f"  ✓ {path.name}: {len(rows):,} rows")


def main() -> None:
    print("Generating synthetic data…")
    agents = generate_agents()
    transactions, injected = generate_transactions(agents)

    providers = [
        {"id": p, "name": p.capitalize(), "is_active": True}
        for p in PROVIDERS
    ]

    write_csv(OUTPUT_DIR / "agents.csv", agents)
    write_csv(OUTPUT_DIR / "providers.csv", providers)
    write_csv(OUTPUT_DIR / "transactions.csv", transactions)
    write_csv(OUTPUT_DIR / "context_calendar.csv", CALENDAR_EVENTS)
    write_csv(OUTPUT_DIR / "injected_anomalies.csv", injected)

    anomaly_count = sum(1 for t in transactions if t["is_anomaly"])
    print(f"\nSummary:")
    print(f"  Agents:       {len(agents)}")
    print(f"  Transactions: {len(transactions):,} total | {anomaly_count:,} anomalies ({anomaly_count/len(transactions)*100:.1f}%)")
    print(f"  Injected:     {len(injected)} anomaly groups")
    print("\nDone. Files in:", OUTPUT_DIR)


if __name__ == "__main__":
    main()
