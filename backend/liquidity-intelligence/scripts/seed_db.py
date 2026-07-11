"""
Seed script — loads synthetic CSV data into the database via Prisma.
Uses create_many with skip_duplicates for fast bulk inserts.

Usage:
  python scripts/seed_db.py
"""
from __future__ import annotations

import asyncio
import csv
import random
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from prisma import Prisma

DATA_DIR = Path(__file__).parent.parent / "data"
BATCH_SIZE = 1000  # rows per create_many call


def _now() -> datetime:
    return datetime.now(timezone.utc)


async def seed() -> None:
    db = Prisma()
    await db.connect()

    try:
        # ------------------------------------------------------------------ #
        # 1. Agents                                                            #
        # ------------------------------------------------------------------ #
        agents_file = DATA_DIR / "agents.csv"
        agent_ids: list[str] = []

        if agents_file.exists():
            rows = []
            with open(agents_file, encoding="utf-8") as f:
                for row in csv.DictReader(f):
                    agent_ids.append(row["id"])
                    rows.append({
                        "id": row["id"],
                        "name": row["name"],
                        "phone": row["phone"],
                        "area": row["area"],
                        "region": row["region"],
                        "isActive": True,
                        "createdAt": _now(),
                    })
            result = await db.agent.create_many(data=rows, skip_duplicates=True)
            print(f"✓ Agents seeded: {result}")

        # ------------------------------------------------------------------ #
        # 2. Transactions (bulk in batches)                                   #
        # ------------------------------------------------------------------ #
        tx_file = DATA_DIR / "transactions.csv"
        if tx_file.exists():
            total = 0
            batch: list[dict] = []

            with open(tx_file, encoding="utf-8") as f:
                for row in csv.DictReader(f):
                    batch.append({
                        "id": row["id"],
                        "agentId": row["agent_id"],
                        "provider": row["provider"],
                        "transactionType": row["transaction_type"],
                        "amount": float(row["amount"]),
                        "timestamp": datetime.fromisoformat(row["timestamp"]),
                        "area": row["area"],
                        "accountRef": row["account_ref"],
                        # metadata uses Prisma Json default from schema
                    })
                    if len(batch) >= BATCH_SIZE:
                        count = await db.transaction.create_many(
                            data=batch, skip_duplicates=True
                        )
                        total += count
                        print(f"  … {total:,} transactions inserted")
                        batch = []

            if batch:
                count = await db.transaction.create_many(
                    data=batch, skip_duplicates=True
                )
                total += count

            print(f"✓ Transactions seeded: {total:,}")

        # ------------------------------------------------------------------ #
        # 3. Liquidity snapshots — one per agent                              #
        # ------------------------------------------------------------------ #
        rng = random.Random(99)
        snapshots = [
            {
                "id": str(uuid.uuid4()),
                "agentId": agent_id,
                "physicalCash": round(rng.uniform(10_000, 100_000), 2),
                "bkashBalance": round(rng.uniform(5_000, 80_000), 2),
                "nagadBalance": round(rng.uniform(3_000, 60_000), 2),
                "rocketBalance": round(rng.uniform(2_000, 40_000), 2),
                "overallConfidence": round(rng.uniform(0.7, 1.0), 4),
                "capturedAt": _now(),
            }
            for agent_id in agent_ids
        ]
        if snapshots:
            count = await db.liquiditysnapshot.create_many(
                data=snapshots, skip_duplicates=True
            )
            print(f"✓ Liquidity snapshots seeded: {count}")

        # ------------------------------------------------------------------ #
        # 4. Data feed statuses                                               #
        # ------------------------------------------------------------------ #
        feeds = [
            {
                "id": str(uuid.uuid4()),
                "provider": provider,
                "lastReceivedAt": _now(),
                "isHealthy": True,
                "stalenessThresholdSeconds": 300,
            }
            for provider in ["bkash", "nagad", "rocket", "physical"]
        ]
        count = await db.datafeedstatus.create_many(data=feeds, skip_duplicates=True)
        print(f"✓ Data feed statuses seeded: {count}")

    finally:
        await db.disconnect()

    print("\nSeeding complete.")


if __name__ == "__main__":
    asyncio.run(seed())
