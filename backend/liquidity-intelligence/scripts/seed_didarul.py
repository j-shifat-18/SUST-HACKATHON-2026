"""
Seed script: Generate realistic data for user Didarul Shahriar.
Creates an agent in his area, plus transactions, snapshots, forecasts, alerts, and anomaly flags.
"""
import asyncio
import json
import random
import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from prisma import Prisma
from prisma import Json


DIDARUL_USER_ID = "58f8d64c-ec88-45ce-a454-339a3d705b24"
DIDARUL_REGION = "Dhaka"
DIDARUL_AREA = "Gazipur"

# Agent for Didarul
AGENT_ID = DIDARUL_USER_ID  # Use same ID so snapshot lookup by user ID works
AGENT_NAME = "Didarul MFS Point - Gazipur"
AGENT_PHONE = "+8801872686000"

PROVIDERS = ["bkash", "nagad", "rocket", "physical"]
TX_TYPES = ["cash_in", "cash_out"]


def random_amount(low=500, high=25000):
    return Decimal(str(random.randint(low, high)))


def random_account():
    prefix = random.choice(["0171", "0175", "0183", "0191", "0152", "0188", "0195"])
    return f"{prefix}***{random.randint(100, 999)}"


async def main():
    db = Prisma()
    await db.connect()

    print("🔧 Creating agent for Didarul...")

    # Upsert agent (use didarul's user id as agent id for seamless lookup)
    await db.agent.upsert(
        where={"id": AGENT_ID},
        data={
            "create": {
                "id": AGENT_ID,
                "name": AGENT_NAME,
                "phone": AGENT_PHONE,
                "area": DIDARUL_AREA,
                "region": DIDARUL_REGION,
                "isActive": True,
            },
            "update": {
                "name": AGENT_NAME,
                "area": DIDARUL_AREA,
                "region": DIDARUL_REGION,
            },
        },
    )
    print(f"  ✓ Agent created: {AGENT_ID}")

    # --- Generate Transactions (last 72 hours, ~500 transactions) ---
    print("📊 Generating transactions...")
    now = datetime.now(timezone.utc)
    transactions = []

    for i in range(500):
        hours_ago = random.uniform(0, 72)
        ts = now - timedelta(hours=hours_ago)
        provider = random.choice(PROVIDERS[:3])  # bkash, nagad, rocket
        tx_type = random.choices(TX_TYPES, weights=[35, 65])[0]  # More cash-out
        amount = random_amount(1000, 20000)

        transactions.append({
            "id": str(uuid.uuid4()),
            "agentId": AGENT_ID,
            "provider": provider,
            "transactionType": tx_type,
            "amount": float(amount),
            "timestamp": ts,
            "area": DIDARUL_AREA,
            "accountRef": random_account(),
            "metadata": Json("{}"),
        })

    # Batch insert
    for i in range(0, len(transactions), 100):
        batch = transactions[i:i+100]
        await db.transaction.create_many(data=batch, skip_duplicates=True)

    print(f"  ✓ {len(transactions)} transactions created")

    # --- Generate Liquidity Snapshots (last 24h, every 30 mins) ---
    print("💰 Generating liquidity snapshots...")
    snapshots = []
    base_physical = 55000
    base_bkash = 42000
    base_nagad = 28000
    base_rocket = 15000

    for i in range(48):  # 48 snapshots = 24 hours of 30-min intervals
        hours_ago = i * 0.5
        ts = now - timedelta(hours=hours_ago)

        # Add some realistic variance
        physical = max(5000, base_physical + random.randint(-15000, 10000))
        bkash = max(3000, base_bkash + random.randint(-12000, 8000))
        nagad = max(2000, base_nagad + random.randint(-8000, 6000))
        rocket = max(1000, base_rocket + random.randint(-5000, 4000))

        # Simulate depletion trend for latest snapshots (more dramatic recently)
        if hours_ago < 4:
            bkash = max(3000, bkash - int(hours_ago * 2000))
            rocket = max(1000, rocket - int(hours_ago * 1500))

        confidence = round(random.uniform(0.78, 0.95), 2)

        snapshots.append({
            "id": str(uuid.uuid4()),
            "agentId": AGENT_ID,
            "physicalCash": float(physical),
            "bkashBalance": float(bkash),
            "nagadBalance": float(nagad),
            "rocketBalance": float(rocket),
            "overallConfidence": confidence,
            "capturedAt": ts,
        })

    await db.liquiditysnapshot.create_many(data=snapshots, skip_duplicates=True)
    print(f"  ✓ {len(snapshots)} liquidity snapshots created")

    # --- Generate Forecast Horizons ---
    print("📈 Generating forecasts...")
    forecasts = []
    current_balances = {
        "bkash": snapshots[0]["bkashBalance"],
        "nagad": snapshots[0]["nagadBalance"],
        "rocket": snapshots[0]["rocketBalance"],
        "physical": snapshots[0]["physicalCash"],
    }

    for provider, balance in current_balances.items():
        hourly_flow = random.uniform(-1500, -500)  # Net outflow
        predicted = max(0, balance + hourly_flow * 12)
        depletion = None
        if hourly_flow < 0 and balance > 0:
            depletion = round(balance / abs(hourly_flow), 1)
            if depletion > 72:
                depletion = None  # No meaningful depletion

        forecasts.append({
            "id": str(uuid.uuid4()),
            "agentId": AGENT_ID,
            "provider": provider,
            "forecastHours": 12,
            "predictedBalance": float(max(0, predicted)),
            "depletionTimeHours": depletion,
            "confidence": round(random.uniform(0.6, 0.85), 2),
            "modelVersion": "ses_v1",
            "generatedAt": now,
        })

    await db.forecasthorizon.create_many(data=forecasts, skip_duplicates=True)
    print(f"  ✓ {len(forecasts)} forecasts created")

    # --- Generate Anomaly Flags ---
    print("🔍 Generating anomaly flags...")
    anomaly_flags = []

    # Velocity spike
    anomaly_flags.append({
        "id": str(uuid.uuid4()),
        "transactionId": transactions[0]["id"],
        "transactionGroupIds": Json(json.dumps([transactions[j]["id"] for j in range(0, min(8, len(transactions)))])),
        "flagType": "velocity_spike",
        "severityScore": 62,
        "confidence": 0.81,
        "evidence": Json(json.dumps({
            "hourly_count": 14,
            "z_score": 3.2,
            "normal_hourly_count": 4.5,
            "spike_timestamp": now.isoformat(),
        })),
        "explanationEn": "Unusual transaction volume detected in the last hour. 14 transactions vs. normal rate of 4-5/hour. This may indicate high seasonal demand.",
        "explanationBn": "গত এক ঘণ্টায় অস্বাভাবিক লেনদেনের পরিমাণ শনাক্ত হয়েছে। স্বাভাবিক ৪-৫টির বিপরীতে ১৪টি লেনদেন হয়েছে।",
        "explanationBanglish": "Last 1 ghontay unusual transaction volume detect hoyeche. Normal 4-5 tar bodole 14 ta transaction hoyeche.",
        "reviewLanguage": "en",
        "isReviewed": False,
        "createdAt": now - timedelta(hours=1),
    })

    # Transaction splitting
    anomaly_flags.append({
        "id": str(uuid.uuid4()),
        "transactionId": transactions[10]["id"] if len(transactions) > 10 else None,
        "transactionGroupIds": Json(json.dumps([transactions[j]["id"] for j in range(10, min(14, len(transactions)))])),
        "flagType": "transaction_splitting",
        "severityScore": 45,
        "confidence": 0.68,
        "evidence": Json(json.dumps({
            "pattern": "3 transactions of ~10,000 BDT from same account within 15 minutes",
            "account_ref": "0175***981",
            "total_amount": 30500,
            "time_window_minutes": 15,
        })),
        "explanationEn": "Possible transaction splitting detected: 3 near-identical amounts (≈10,000 BDT) from the same account within 15 minutes. This may be a legitimate large withdrawal split for convenience.",
        "explanationBn": "সম্ভাব্য লেনদেন বিভাজন শনাক্ত: একই অ্যাকাউন্ট থেকে ১৫ মিনিটের মধ্যে প্রায় সমান ৩টি লেনদেন (≈১০,০০০ টাকা)।",
        "explanationBanglish": "Possible transaction splitting detect hoyeche: same account theke 15 minute er moddhe 3 ta almost equal amount (10,000 BDT) transaction.",
        "reviewLanguage": "en",
        "isReviewed": False,
        "createdAt": now - timedelta(hours=3),
    })

    await db.anomalyflag.create_many(data=anomaly_flags, skip_duplicates=True)
    print(f"  ✓ {len(anomaly_flags)} anomaly flags created")

    # --- Generate Alerts ---
    print("🚨 Generating alerts...")
    alerts = []

    alerts.append({
        "id": str(uuid.uuid4()),
        "agentId": AGENT_ID,
        "alertType": "liquidity_low",
        "severity": "high",
        "confidence": 0.88,
        "evidence": Json(json.dumps({
            "lowest_provider": "rocket",
            "rocket_bdt": current_balances["rocket"],
            "total_liquidity_bdt": sum(current_balances.values()),
            "pct_of_total": round(current_balances["rocket"] / sum(current_balances.values()) * 100, 1),
        })),
        "status": "open",
        "notes": "",
        "createdAt": now - timedelta(hours=2),
        "updatedAt": now - timedelta(hours=2),
    })

    alerts.append({
        "id": str(uuid.uuid4()),
        "agentId": AGENT_ID,
        "alertType": "anomaly_detected",
        "severity": "medium",
        "confidence": 0.81,
        "evidence": Json(json.dumps({
            "flag_type": "velocity_spike",
            "severity_score": 62,
            "hourly_count": 14,
            "z_score": 3.2,
        })),
        "status": "open",
        "anomalyFlagId": anomaly_flags[0]["id"],
        "notes": "",
        "createdAt": now - timedelta(hours=1),
        "updatedAt": now - timedelta(hours=1),
    })

    alerts.append({
        "id": str(uuid.uuid4()),
        "agentId": AGENT_ID,
        "alertType": "forecast_breach",
        "severity": "high",
        "confidence": 0.74,
        "evidence": Json(json.dumps({
            "provider": "rocket",
            "current_balance_bdt": current_balances["rocket"],
            "predicted_depletion_hours": 8.5,
            "forecast_confidence": 0.72,
        })),
        "status": "open",
        "notes": "",
        "createdAt": now - timedelta(minutes=45),
        "updatedAt": now - timedelta(minutes=45),
    })

    alerts.append({
        "id": str(uuid.uuid4()),
        "agentId": AGENT_ID,
        "alertType": "liquidity_critical",
        "severity": "critical",
        "confidence": 0.92,
        "evidence": Json(json.dumps({
            "lowest_provider": "rocket",
            "rocket_bdt": 1200,
            "total_liquidity_bdt": 85000,
            "pct_of_total": 1.4,
            "immediate_action_required": True,
        })),
        "status": "acknowledged",
        "assignedToUserId": DIDARUL_USER_ID,
        "notes": "Acknowledged by Didarul. Monitoring closely.",
        "createdAt": now - timedelta(hours=5),
        "updatedAt": now - timedelta(hours=4),
    })

    alerts.append({
        "id": str(uuid.uuid4()),
        "agentId": AGENT_ID,
        "alertType": "anomaly_detected",
        "severity": "low",
        "confidence": 0.68,
        "evidence": Json(json.dumps({
            "flag_type": "transaction_splitting",
            "severity_score": 45,
            "pattern": "3 near-identical amounts from same account",
        })),
        "status": "open",
        "anomalyFlagId": anomaly_flags[1]["id"],
        "notes": "",
        "createdAt": now - timedelta(hours=3),
        "updatedAt": now - timedelta(hours=3),
    })

    await db.alert.create_many(data=alerts, skip_duplicates=True)
    print(f"  ✓ {len(alerts)} alerts created")

    # --- Generate Cases ---
    print("📋 Generating cases...")
    cases = []

    cases.append({
        "id": str(uuid.uuid4()),
        "agentId": AGENT_ID,
        "title": "Rocket Liquidity Depletion — Urgent Rebalancing Required",
        "alertIds": Json(json.dumps([alerts[0]["id"], alerts[2]["id"]])),
        "status": "open",
        "resolutionNote": "",
        "createdAt": now - timedelta(hours=2),
        "updatedAt": now - timedelta(hours=1),
    })

    cases.append({
        "id": str(uuid.uuid4()),
        "agentId": AGENT_ID,
        "title": "bKash Velocity Spike Investigation",
        "alertIds": Json(json.dumps([alerts[1]["id"]])),
        "status": "open",
        "resolutionNote": "",
        "createdAt": now - timedelta(hours=1),
        "updatedAt": now - timedelta(minutes=30),
    })

    cases.append({
        "id": str(uuid.uuid4()),
        "agentId": AGENT_ID,
        "title": "Previous Rocket Critical Liquidity — Resolved",
        "alertIds": Json(json.dumps([alerts[3]["id"]])),
        "status": "closed",
        "resolutionNote": "Agent topped up Rocket balance via bank transfer. Balance restored to 18,000 BDT.",
        "createdAt": now - timedelta(hours=5),
        "updatedAt": now - timedelta(hours=3),
    })

    await db.case.create_many(data=cases, skip_duplicates=True)
    print(f"  ✓ {len(cases)} cases created")

    # --- Data Feed Statuses ---
    print("📡 Setting data feed statuses...")
    for provider in ["bkash", "nagad", "rocket", "physical"]:
        is_healthy = provider != "rocket"  # rocket slightly stale for realism
        last_received = now - timedelta(seconds=random.randint(5, 60)) if is_healthy else now - timedelta(seconds=320)
        await db.datafeedstatus.upsert(
            where={"provider": provider},
            data={
                "create": {
                    "id": str(uuid.uuid4()),
                    "provider": provider,
                    "lastReceivedAt": last_received,
                    "isHealthy": is_healthy,
                    "stalenessThresholdSeconds": 300,
                },
                "update": {
                    "lastReceivedAt": last_received,
                    "isHealthy": is_healthy,
                },
            },
        )
    print("  ✓ Data feed statuses set")

    # --- Update user area to match agent ---
    print("👤 Ensuring user area matches agent...")
    await db.user.update(
        where={"id": DIDARUL_USER_ID},
        data={"area": DIDARUL_AREA, "region": DIDARUL_REGION},
    )
    print("  ✓ User area confirmed: Gazipur, Dhaka")

    await db.disconnect()
    print("\n✅ All data seeded successfully for Didarul!")
    print(f"   Agent ID: {AGENT_ID}")
    print(f"   Transactions: {len(transactions)}")
    print(f"   Snapshots: {len(snapshots)}")
    print(f"   Forecasts: {len(forecasts)}")
    print(f"   Anomalies: {len(anomaly_flags)}")
    print(f"   Alerts: {len(alerts)}")
    print(f"   Cases: {len(cases)}")


if __name__ == "__main__":
    asyncio.run(main())
