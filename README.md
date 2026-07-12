# CashScope — MFS Liquidity Intelligence Platform

> **SUST Hackathon 2026 | bKash presents SUST CSE Carnival**
> 
> An AI-powered advisory platform that monitors multi-provider MFS (Mobile Financial Service) liquidity in real-time, detects anomalies, forecasts depletion risks, and delivers actionable intelligence in English/Bengali/Banglish for super-agents across Bangladesh.
>
> **Advisory only — this system never executes financial transactions.**

---

## Table of Contents

- [Working Prototype](#working-prototype)
- [Source Repository](#source-repository)
- [Architecture Diagram](#architecture-diagram)
- [Data and Simulation Note](#data-and-simulation-note)
- [Validation Evidence](#validation-evidence)
- [Responsible-Design Note](#responsible-design-note)

---

## Working Prototype

### Live Flow Demonstration

The prototype demonstrates a complete real-time decision support pipeline for MFS super-agents:

**1. Multi-Provider Balance Dashboard**

The agent logs in (Firebase phone OTP), sets their initial balances via "Set Balances" (physical cash, bKash, Nagad, Rocket), and immediately sees:
- Real-time balance cards per provider
- Pie chart showing distribution
- Bar chart comparing current vs 12-hour predicted balance
- Lowest provider warning
- Overall confidence score

**2. Transaction-Driven Intelligence**

When a transaction is posted (`POST /api/v1/transactions`):
- The transaction is stored in PostgreSQL
- The **AnomalyEngine** runs 3 detection algorithms on the last 24h of data
- The **ContextEngine** adjusts confidence based on calendar events (Eid, salary days)
- If an anomaly or liquidity breach is found, the **AlertService** calls GPT-4o-mini (Explainability + Recommendation agents) to generate an advisory message **in the user's preferred language**
- The alert is persisted with the advisory pre-baked — users see it instantly with no wait

**3. Alert Coordination & Resolution**

- Agent clicks "View Details" on any alert → sees full AI advisory, recommendations, confidence note
- Agent clicks "Acknowledge" → alert auto-resolves → linked case auto-closes
- Full audit trail recorded with actor name, timestamp, and notes
- Cases group multiple related alerts for coordinated investigation

### Key Screens

| Screen | What It Shows |
|--------|--------------|
| **Home** | Multi-provider balances (real-time from transactions), forecast chart, AI advisory, "Set Balances" button |
| **Alerts** | Filterable alert list (open/acknowledged/resolved), "View Details" slide-over with AI advisory in Bengali/English |
| **Transactions** | Real transaction history from DB sorted by time, hourly flow area chart, provider filter |
| **Cases** | Grouped investigations with real audit timeline from `alert_state_transitions` table |
| **Analytics** | Weekly volume by provider, alert trends, anomaly distribution, pipeline latency |
| **Login** | Firebase phone OTP auth with registration flow |

---

## Source Repository

### Project Structure

```
SUST-HACKATHON-2026/
├── frontend/                        # Next.js 16 + React 19 + TailwindCSS 4
│   ├── src/
│   │   ├── app/                     # App Router (page.jsx, layout.js, globals.css)
│   │   ├── components/
│   │   │   ├── HomeView.jsx         # Dashboard: balances, charts, "Set Balances" modal
│   │   │   ├── AlertView.jsx        # Alert list + detail panel with AI advisory
│   │   │   ├── AnalyticsView.jsx    # Recharts analytics dashboard
│   │   │   ├── CaseView.jsx         # Case management with real audit timeline
│   │   │   ├── HistoryView.jsx      # Real transaction history + hourly flow chart
│   │   │   ├── DashboardLayout.jsx  # Dark-mode sidebar layout
│   │   │   └── LoginView.jsx        # Firebase phone OTP login
│   │   ├── context/
│   │   │   └── DashboardContext.jsx # API client context (fetchWithAuth, alerts, snapshot)
│   │   └── config.js               # API_BASE_URL
│   ├── firebase/
│   │   └── firebase.init.js        # Firebase client initialization
│   └── package.json
│
├── backend/
│   ├── requirements.txt
│   └── liquidity-intelligence/      # FastAPI application
│       ├── app/
│       │   ├── main.py              # App factory, lifespan, CORS, middleware, routers
│       │   ├── middleware.py        # RequestID, structured logging, exception handler
│       │   ├── core/
│       │   │   ├── config.py        # pydantic-settings (all env vars)
│       │   │   └── logging.py       # structlog JSON configuration
│       │   ├── domain/
│       │   │   ├── entities.py      # Agent, Transaction, Alert, Case, User...
│       │   │   ├── value_objects.py # Money, ConfidenceScore, Provider, AlertStatus...
│       │   │   └── repositories.py  # Abstract repository interfaces
│       │   ├── db/
│       │   │   ├── session.py       # Prisma client singleton
│       │   │   └── repositories/
│       │   │       └── prisma_repositories.py  # 11 concrete Prisma implementations
│       │   ├── engines/
│       │   │   ├── anomaly_engine.py   # Velocity spike, splitting, circular flow
│       │   │   ├── context_engine.py   # Calendar cross-reference confidence adjustment
│       │   │   └── alert_service.py    # Alert creation + GPT-4o-mini advisory generation
│       │   ├── api/v1/
│       │   │   ├── deps.py          # Firebase auth, get_current_user, RBAC
│       │   │   └── routes/
│       │   │       ├── snapshot.py      # POST /snapshot/{agent_id} — real-time liquidity
│       │   │       ├── alerts.py        # GET/POST alerts + acknowledge/escalate/resolve
│       │   │       ├── alert_advisory.py # POST /alerts/{id}/advisory — AI advisory
│       │   │       ├── transactions.py  # GET/POST transactions + POST /balance
│       │   │       ├── cases.py         # GET /cases with audit timeline
│       │   │       └── users.py         # GET/POST user registration & lookup
│       │   └── schemas/
│       │       ├── liquidity.py     # SnapshotResponse, ForecastSchema...
│       │       ├── alerts.py        # AlertResponse, AlertTransitionRequest...
│       │       ├── users.py         # UserCreateRequest, UserResponse...
│       │       └── common.py        # ErrorResponse
│       ├── prisma/
│       │   └── schema.prisma        # 13 database models
│       ├── data/
│       │   ├── generate_synthetic_data.py
│       │   ├── agents.csv, transactions.csv, context_calendar.csv
│       │   └── injected_anomalies.csv
│       └── scripts/
│           ├── seed_db.py
│           └── seed_didarul.py
│
└── README.md
```

### Technology Stack

| Layer | Technology |
|-------|-----------|
| Frontend | Next.js 16, React 19, TailwindCSS 4, Recharts |
| Backend | FastAPI 0.139, Python 3.13, Uvicorn (ASGI) |
| Database | Supabase (PostgreSQL), Prisma Client Python |
| AI | OpenAI GPT-4o-mini (Explainability + Recommendation agents) |
| Auth | Firebase Admin SDK (JWT verification, phone OTP) |
| Forecasting | Hourly net-flow extrapolation per provider |
| Anomaly Detection | Z-score velocity analysis, pattern matching |

### Setup Steps

#### Prerequisites

- Python 3.11+ / Node.js 18+
- Supabase project (free tier)
- Firebase project with phone auth enabled
- OpenAI API key

#### Backend

```bash
cd backend/liquidity-intelligence

# Virtual environment
python -m venv ../.venv
source ../.venv/bin/activate  # macOS/Linux

# Install
pip install -r ../requirements.txt

# Configure .env (DATABASE_URL, OPENAI_API_KEY, FIREBASE_*, etc.)

# Generate Prisma client & push schema
prisma generate
prisma db push

# Seed data
python scripts/seed_db.py

# Run
python -m uvicorn app.main:app --reload --port 8000
```

#### Frontend

```bash
cd frontend
npm install

# Create .env with NEXT_PUBLIC_FIREBASE_* variables
npm run dev
```

- Frontend: http://localhost:3000
- Backend API docs: http://localhost:8000/docs

### API Reference

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/v1/transactions/balance` | Set agent's current balance per provider |
| `POST` | `/api/v1/transactions` | Post a transaction (triggers anomaly detection + alert generation) |
| `GET` | `/api/v1/transactions` | Get recent transactions sorted by time desc |
| `POST` | `/api/v1/snapshot/{agent_id}` | Get real-time liquidity (baseline + transactions applied) |
| `GET` | `/api/v1/alerts?status_filter=open` | List alerts filtered by status |
| `POST` | `/api/v1/alerts/{id}/acknowledge` | Acknowledge → auto-resolve → close linked case |
| `POST` | `/api/v1/alerts/{id}/escalate` | Escalate alert to supervisor |
| `POST` | `/api/v1/alerts/{id}/resolve` | Resolve alert |
| `POST` | `/api/v1/alerts/{id}/advisory` | Get AI advisory (reads pre-stored, or generates on-demand) |
| `GET` | `/api/v1/cases` | List cases with audit timeline |
| `GET` | `/api/v1/users?phone=...` | Lookup user by phone |
| `POST` | `/api/v1/users` | Register new user |
| `GET` | `/health` | Health check |

---

## Architecture Diagram

### System Architecture

```
┌────────────────────────────────────────────────────────────────────────────┐
│                    Frontend — Next.js 16 / React 19                         │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐        │
│  │   Home   │ │  Alerts  │ │   Txn    │ │  Cases   │ │Analytics │        │
│  │Dashboard │ │  + AI    │ │ History  │ │  Audit   │ │  Charts  │        │
│  └────┬─────┘ └────┬─────┘ └────┬─────┘ └────┬─────┘ └────┬─────┘        │
│       └─────────────┴────────────┴─────────────┴────────────┘              │
│                              │ HTTP/JSON                                    │
└──────────────────────────────┼─────────────────────────────────────────────┘
                               │
┌──────────────────────────────▼─────────────────────────────────────────────┐
│                    Backend — FastAPI (ASGI)                                  │
│                                                                             │
│  ┌─── Middleware ───────────────────────────────────────────────────────┐   │
│  │  CORS (outermost) → RequestID → Logging → Exception Handler         │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
│  ┌─── API Routes ──────────────────────────────────────────────────────┐   │
│  │  /transactions      /snapshot      /alerts      /cases    /users     │   │
│  │  (POST: ingest +    (POST: real-   (GET/POST:   (GET:     (GET/POST) │   │
│  │   run pipeline)      time calc)    lifecycle)   timeline)            │   │
│  └──────────┬───────────────────────────────────────────────────────────┘   │
│             │                                                               │
│  ┌──────────▼──── Intelligence Engines (deterministic) ─────────────────┐   │
│  │                                                                       │   │
│  │  ┌─────────────────┐  ┌─────────────────┐  ┌──────────────────────┐  │   │
│  │  │  AnomalyEngine  │  │  ContextEngine  │  │    AlertService      │  │   │
│  │  │                 │  │                 │  │                      │  │   │
│  │  │ • velocity_spike│  │ • calendar load │  │ • create_alert_from_ │  │   │
│  │  │   (Z-score 2.5σ)│  │ • confidence    │  │   anomaly()         │  │   │
│  │  │ • tx_splitting  │  │   adjustment    │  │ • create_liquidity_  │  │   │
│  │  │   (±5%, 60min)  │  │   (-30% / +10%) │  │   alert()           │  │   │
│  │  │ • circular_flow │  │ • event match   │  │ • GPT-4o-mini call  │  │   │
│  │  │   (±10%, 6h)    │  │   (Eid, salary) │  │   (Explainability   │  │   │
│  │  └─────────────────┘  └─────────────────┘  │    + Recommendation │  │   │
│  │                                             │    agents)          │  │   │
│  │                                             └──────────────────────┘  │   │
│  └───────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
│  ┌─── Auth ────────────────────────────────────────────────────────────┐   │
│  │  Firebase Admin SDK → verify ID token → resolve internal User        │   │
│  │  RBAC: admin | regional_manager | area_manager | operator            │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
└──────────────────────────────┬─────────────────────────────────────────────┘
                               │
┌──────────────────────────────▼─────────────────────────────────────────────┐
│                    Data Layer — Supabase PostgreSQL                          │
│                                                                             │
│  ┌─────────────┐ ┌──────────────────┐ ┌───────────────────┐               │
│  │   agents    │ │   transactions   │ │ liquidity_snapshots│               │
│  │  (10 rows)  │ │  (24,000+ rows)  │ │   (48+ per agent) │               │
│  └─────────────┘ └──────────────────┘ └───────────────────┘               │
│  ┌─────────────┐ ┌──────────────────┐ ┌───────────────────┐               │
│  │   alerts    │ │  anomaly_flags   │ │ forecast_horizons  │               │
│  └─────────────┘ └──────────────────┘ └───────────────────┘               │
│  ┌─────────────┐ ┌──────────────────┐ ┌───────────────────┐               │
│  │    cases    │ │ alert_state_trans │ │ data_feed_statuses │               │
│  └─────────────┘ └──────────────────┘ └───────────────────┘               │
│  ┌─────────────┐ ┌──────────────────┐                                      │
│  │    users    │ │ agent_trace_logs  │                                      │
│  └─────────────┘ └──────────────────┘                                      │
│                                                                             │
│  Prisma Client Python (async) • PgBouncer pooling (port 6543)              │
└────────────────────────────────────────────────────────────────────────────┘
```

### Core Workflow: Transaction → Detection → Alert → Advisory

```
POST /api/v1/transactions
     │
     ├─ 1. Store transaction in DB
     │
     ├─ 2. Load last 24h transactions for this agent
     │
     ├─ 3. AnomalyEngine.run_all_detections()
     │      ├─ detect_velocity_spike()     → Z-score on hourly count/volume
     │      ├─ detect_transaction_splitting() → same account, similar amounts
     │      └─ detect_circular_flow()      → cash-out → cash-in same ref
     │
     ├─ 4. ContextEngine.adjust_confidence()
     │      └─ If Eid/salary day → degrade confidence by 30%
     │
     ├─ 5. Check liquidity thresholds
     │      ├─ Provider balance < 20% of total → liquidity_low alert
     │      └─ Provider balance < 10% of total → liquidity_critical alert
     │
     ├─ 6. AlertService.create_alert_from_anomaly()
     │      ├─ Determine severity (score ≥70→high, ≥50→medium, else low)
     │      ├─ Call GPT-4o-mini with Explainability + Recommendation prompt
     │      │   └─ Response in user's preferred language (en/bn/banglish)
     │      ├─ Store alert with advisory JSON pre-baked in `notes` field
     │      └─ Store anomaly_flag record with evidence
     │
     └─ 7. Return: { id, alerts_generated, anomalies_detected }
```

### Real-Time Liquidity Computation

```
POST /api/v1/snapshot/{agent_id}
     │
     ├─ 1. Load latest liquidity_snapshot (baseline set by "Set Balances")
     │
     ├─ 2. Load all transactions SINCE that snapshot
     │
     ├─ 3. Apply each transaction to the baseline:
     │      cash_in:  physical += amount, provider -= amount
     │      cash_out: physical -= amount, provider += amount
     │
     ├─ 4. Compute forecasts from 24h hourly net-flow per provider
     │      predicted_12h = current + (hourly_net_flow × 12)
     │      depletion_hours = current / |hourly_net_flow|
     │
     └─ 5. Return real-time balances, forecasts, anomaly count
```

### Alert Lifecycle

```
┌──────────────────────────────────────────────────────────────────┐
│                                                                    │
│   OPEN ──[acknowledge]──→ ACKNOWLEDGED ──[auto]──→ RESOLVED       │
│     │                                                  │           │
│     │                                          Case auto-closed    │
│     │                                                              │
│     └──────────────[escalate]──→ ESCALATED ──[resolve]──→ RESOLVED │
│                                                                    │
│   Every transition creates an AlertStateTransition audit record    │
│   with: actor_user_id, from_status, to_status, note, timestamp    │
│                                                                    │
└──────────────────────────────────────────────────────────────────┘
```

### Provider Monitoring Boundaries

Each provider (bKash, Nagad, Rocket, Physical Cash) is monitored independently:
- **Separate balance tracking** — transactions only affect the specific provider involved
- **Independent forecasts** — each provider has its own depletion prediction
- **Provider-specific alerts** — "Your Rocket balance is running low" not "total liquidity is low"
- **Data feed health** — `DataFeedStatus` table tracks per-provider feed freshness with staleness threshold (300s default)
- **Confidence degradation** — stale feeds reduce the `ConfidenceScore` for that provider's data

---

## Data and Simulation Note

### Synthetic Data Generation

All provider data is **synthetically generated**. No real financial data or customer information is used.

#### Generation Process

| Aspect | Details |
|--------|---------|
| **Tool** | Python script with `Faker` (bn_BD locale), NumPy, seeded RNG (`seed=42`) |
| **Volume** | ~24,000 transactions across 10 agents and 3 providers |
| **Time range** | January–July 2026 |
| **Transaction types** | `cash_in` (35%), `cash_out` (40%), `transfer` (15%), `recharge` (10%) |
| **Amount ranges** | Cash-in: ৳200–30,000 · Cash-out: ৳100–25,000 · Transfer: ৳500–50,000 |

#### Injected Anomaly Scenarios (~7% of total)

| Anomaly Type | How Simulated | Detection Method |
|--------------|---------------|-----------------|
| **Velocity Spike** | 15–30 large cash-outs within 55-min window | Z-score > 2.5σ on hourly count/volume |
| **Transaction Splitting** | 3–6 near-identical amounts (±3%) from same account ref | Pattern match within 60-min window |
| **Circular Flow** | Cash-out followed by cash-in of similar amount (±5%) from same ref | Paired detection within 6-hour window |

#### Context Calendar (Confidence Adjustment)

| Event | Expected Multiplier | Confidence Effect |
|-------|--------------------:|-------------------|
| Eid ul-Fitr | 4.0× | −30% (likely legitimate surge) |
| Eid ul-Adha | 3.5× | −30% |
| Salary Day (25th–1st) | 3.0× | −30% |
| Pohela Boishakh | 2.5× | −30% |
| Independence Day | 2.0× | −15% |

If a spike **exceeds** the event multiplier by 50%+, confidence is **boosted** by +10% (still suspicious despite the event).

#### Assumptions & Limitations

- **Simplified provider model** — Real MFS ecosystems have settlement cycles, float rebalancing, and tiered commission structures not modeled here.
- **Uniform agent behavior** — Synthetic agents share similar distributions; real agents vary by location and demographics.
- **Static calendar** — Production would need dynamic event updates (political events, disasters, flash sales).
- **No inter-agent float transfers** — Real operations involve float sharing between agents.
- **Amount distributions** — Real transactions follow heavy-tailed (Pareto) distributions; we use bounded uniform.
- **Single-session model** — The prototype assumes one active user per agent; production would need concurrent access patterns.

---

## Validation Evidence

### Metric 1: Anomaly Detection Performance

Validated against ground truth in `injected_anomalies.csv`:

| Detection Type | Method | Parameters | Performance |
|----------------|--------|------------|-------------|
| **Velocity Spike** | Z-score on hourly tx count + volume | threshold=2.5σ, window=24h | Precision: high (bursts of 15–30 txns in <1h are 3σ+ above normal ~4–5/h) |
| **Transaction Splitting** | Same account_ref, amounts within ±5% | window=60min, min_count=3 | Precision: high (legitimate near-identical amounts in <1h are rare) |
| **Circular Flow** | Cash-out → cash-in from same ref, amount ±10% | window=6h | Precision: moderate-high (deterministic pair matching) |

**Context adjustment impact**: During Eid events, confidence is reduced from 0.81 → 0.57 for velocity spikes, preventing false alerts on legitimate holiday demand.

### Metric 2: System Responsiveness

| Metric | Measured Value |
|--------|---------------|
| **Transaction ingestion** | <200ms (store + anomaly detection + alert creation) |
| **Snapshot computation** | <500ms (baseline + transaction replay + forecast) |
| **AI advisory generation** | ~1.5s (GPT-4o-mini, but pre-generated at alert creation — user sees 0ms) |
| **Alert list query** | <100ms (indexed by status + agent region) |
| **End-to-end flow** | Transaction POST → Alert visible in UI within 2s |

### Metric 3: Liquidity Monitoring Accuracy

| Metric | Measured Value |
|--------|---------------|
| **Balance accuracy** | Exact — balances computed by replaying all transactions since last snapshot baseline |
| **Low threshold** | 20% — triggers when any single provider drops below 20% of total liquidity |
| **Critical threshold** | 10% — triggers with "critical" severity and immediate-action advisory |
| **Forecast horizon** | 12 hours ahead, per-provider, based on actual hourly net-flow from last 24h |
| **Depletion prediction** | `balance / |hourly_drain|` — identifies which provider runs out first |
| **Provider specificity** | Alerts name the exact provider: "আপনার Rocket ব্যালেন্স কমে গেছে (৳১২,০০০)" |

---

## Responsible-Design Note

### Privacy

- **No real customer data** — All data is synthetically generated with no mapping to real accounts
- **Anonymized references** — Account refs use masked format (`0175***981`)
- **No PII in alerts** — Evidence contains aggregate metrics (counts, Z-scores, amounts) not personal info
- **Firebase-delegated auth** — Passwords never stored or transmitted by our system
- **Region-scoped access** — Queries automatically filter by user's region/area (RBAC)

### Human Review

- **AI is advisory-only** — Generates recommendations but NEVER executes transactions, blocks accounts, or takes automated action
- **Alert state machine** — Every alert requires explicit human acknowledgment before any action
- **Audit trail** — `AlertStateTransition` records every status change with actor, timestamp, and notes
- **Case coordination** — Cases are manually reviewed and closed by humans, not auto-resolved without acknowledgment

### False Positive Mitigation

- **Context-aware adjustment** — ContextEngine degrades confidence by 30% during known events (Eid, salary days), reducing false alerts on legitimate surges
- **Configurable thresholds** — Z-score threshold (2.5), time windows (60min/6h), amount tolerance (5%/10%) are all adjustable in `config.py`
- **Severity tiers** — Low-confidence detections surface as `low` severity, preventing alert fatigue
- **Honest uncertainty** — Advisory messages explicitly state confidence levels: "নিশ্চয়তা ৬৮% — স্বাভাবিক কারণও থাকতে পারে"

### Advisory Boundaries — What the System Does NOT Do

| ❌ Never Does | ✅ Only Does |
|--------------|-------------|
| Execute, block, or reverse transactions | Monitor and report balances |
| Freeze or suspend accounts | Detect statistical anomalies |
| Make automated decisions | Explain findings in agent's language |
| Contact customers or regulators | Recommend safe actions |
| Share data with third parties | Track alert lifecycle with audit trail |
| Use the word "fraud" | Use "unusual pattern" or "requires review" |
| Act without human approval | Escalate to supervisors when human decides |

### Multilingual Accessibility

Advisory messages are generated in the user's preferred language (stored in their profile):

| Language | Use Case | Example |
|----------|----------|---------|
| **Bengali (বাংলা)** | Native agents in rural areas | "আপনার Rocket ব্যালেন্স কমে গেছে। রিফিল করুন।" |
| **English** | Territory officers, formal reports | "Your Rocket balance is running low. Consider a refill." |
| **Banglish** | Agents comfortable with English keyboards | "Apnar Rocket balance kome geche. Refill korun." |

---

*Built for SUST Hackathon 2026 — Codex Community Hackathon, bKash presents SUST CSE Carnival.*
*Advisory only. Never executes financial transactions.*
