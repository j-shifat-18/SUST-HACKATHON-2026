# MFS Liquidity Intelligence — Backend

> **Advisory only. This system never executes financial transactions.**

An AI-powered decision support platform for Mobile Financial Service (MFS) super-agents in Bangladesh. The system monitors real-time liquidity across bKash, Nagad, Rocket, and physical cash; forecasts depletion risks; detects suspicious transaction patterns; and delivers actionable advisory in English, Bengali, and Banglish through a multi-agent AI pipeline.

---

## Table of Contents

- [System Architecture](#system-architecture)
- [Technology Stack](#technology-stack)
- [Project Structure](#project-structure)
- [Domain Model](#domain-model)
- [Engine Layer](#engine-layer)
- [AI Agent Layer](#ai-agent-layer)
- [Database Schema](#database-schema)
- [API Reference](#api-reference)
- [Request & Response Schemas](#request--response-schemas)
- [Authentication & RBAC](#authentication--rbac)
- [Configuration](#configuration)
- [Local Setup](#local-setup)
- [Data Pipeline](#data-pipeline)

---

## System Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                        Client (HTTP)                                 │
└─────────────────────────────┬───────────────────────────────────────┘
                              │
┌─────────────────────────────▼───────────────────────────────────────┐
│                  FastAPI  (ASGI / uvicorn)                           │
│   RequestIDMiddleware → RequestLoggingMiddleware → CORS              │
│                                                                      │
│   POST /api/v1/snapshot/{agent_id}    ←── Snapshot Router           │
│   GET|POST /api/v1/alerts/...         ←── Alert Router              │
│   GET /health                                                        │
└──────────┬──────────────────────────────────────┬───────────────────┘
           │ Firebase JWT Auth + RBAC              │
┌──────────▼──────────────┐           ┌────────────▼──────────────────┐
│    Engine Layer          │           │     Repository Layer           │
│  (deterministic, sync)  │           │  (Prisma Client — async)       │
│                         │           │                                │
│  LiquidityEngine        │           │  PrismaAgentRepository         │
│  ForecastEngine         │           │  PrismaTransactionRepository   │
│  AnomalyEngine          │           │  PrismaLiquiditySnapshot...    │
│  AlertService           │           │  PrismaAlertRepository         │
│  ContextEngine          │           │  PrismaUserRepository  + more  │
└──────────┬──────────────┘           └────────────┬──────────────────┘
           │                                       │
┌──────────▼──────────────┐           ┌────────────▼──────────────────┐
│    AI Agent Layer        │           │        Supabase (PostgreSQL)   │
│  (OpenAI Agents SDK)    │           │                                │
│                         │           │  11 tables, indexed,           │
│  CoordinatorAgent       │           │  PgBouncer connection pool     │
│    ├─ OperationsAnalyst │           │                                │
│    ├─ Explainability    │           └────────────────────────────────┘
│    ├─ Recommendation    │
│    └─ ExecutiveAsst     │
└─────────────────────────┘
```

### Request Lifecycle — Snapshot Endpoint

```
POST /api/v1/snapshot/{agent_id}
        │
        ├─ 1. Firebase token verification
        ├─ 2. Load latest LiquiditySnapshot + last 72h transactions from DB
        ├─ 3. LiquidityEngine → LiquidityMatrix (thresholds, confidence)
        ├─ 4. ForecastEngine  → ForecastResult × 4 providers (SES model)
        ├─ 5. AnomalyEngine   → AnomalyResult list (velocity/splitting/circular)
        ├─ 6. ContextEngine   → calendar cross-reference → adjust confidence
        ├─ 7. AlertService    → generate Alert entities from engine outputs
        ├─ 8. CoordinatorAgent (GPT-4o) orchestrates sub-agents via tools
        │       ├─ OperationsAnalystAgent   (GPT-4o-mini)
        │       ├─ ExplainabilityAgent      (GPT-4o-mini)
        │       ├─ RecommendationAgent      (GPT-4o-mini)
        │       └─ ExecutiveAssistantAgent  (GPT-4o-mini)
        └─ 9. Return SnapshotResponse (JSON)
```


---

## Technology Stack

| Layer | Technology |
|---|---|
| Web framework | FastAPI 0.139 + Uvicorn (ASGI) |
| Language | Python 3.13 |
| ORM | Prisma Client Python (`prisma-client-py`) v0.15 |
| Database | Supabase (managed PostgreSQL) |
| Connection pooling | Supabase PgBouncer (Transaction mode, port 6543) |
| AI orchestration | OpenAI Agents SDK (`openai-agents`) |
| LLM models | GPT-4o (coordinator), GPT-4o-mini (specialist agents) |
| Forecasting | statsmodels Simple Exponential Smoothing |
| Auth | Firebase Admin SDK (JWT verification) |
| Validation | Pydantic v2 |
| Logging | structlog (JSON output) |
| Settings | pydantic-settings |

---

## Project Structure

```
liquidity-intelligence/
│
├── prisma/
│   └── schema.prisma          # Prisma schema — all 11 DB tables
│
├── app/
│   ├── main.py                # FastAPI app factory + lifespan (Prisma connect/disconnect)
│   ├── middleware.py          # RequestID injection, structured request logging, error handler
│   │
│   ├── core/
│   │   ├── config.py          # pydantic-settings — all env vars
│   │   └── logging.py         # structlog JSON configuration
│   │
│   ├── domain/                # Pure Python — zero framework imports
│   │   ├── entities.py        # AgentEntity, Transaction, LiquiditySnapshot, Alert, ...
│   │   ├── value_objects.py   # Money, ConfidenceScore, Provider, AlertStatus enums, ...
│   │   ├── repositories.py    # Abstract repository interfaces (ABC)
│   │   └── events.py          # Domain events (future use)
│   │
│   ├── db/
│   │   ├── session.py         # Prisma singleton client + connect/disconnect helpers
│   │   └── repositories/
│   │       └── prisma_repositories.py   # 11 concrete Prisma repository implementations
│   │
│   ├── engines/               # Deterministic business logic — no AI, no I/O
│   │   ├── liquidity_engine.py   # Threshold detection, LiquidityMatrix computation
│   │   ├── forecast_engine.py    # Simple Exponential Smoothing balance forecast
│   │   ├── anomaly_engine.py     # Velocity spike, transaction splitting, circular flow
│   │   ├── alert_service.py      # Alert entity creation + state machine transitions
│   │   └── context_engine.py     # Calendar cross-reference for spike context
│   │
│   ├── agents/                # OpenAI Agents SDK layer
│   │   ├── agent_definitions.py  # Build all 5 Agent objects
│   │   ├── pipeline.py           # Orchestrator — runs engines then agents
│   │   ├── prompts.py            # System prompts per agent role
│   │   └── tools.py              # Tool factories wrapping engine outputs
│   │
│   ├── api/v1/
│   │   ├── deps.py            # Firebase auth, get_current_user, require_role, DBClient
│   │   └── routes/
│   │       ├── snapshot.py    # POST /snapshot/{agent_id}
│   │       └── alerts.py      # GET/POST /alerts/...
│   │
│   └── schemas/
│       ├── liquidity.py       # SnapshotResponse, LiquidityMatrixResponse, ForecastSchema, ...
│       ├── alerts.py          # AlertResponse, AlertListResponse, AlertTransitionRequest
│       └── common.py          # ErrorResponse, PaginatedResponse
│
├── data/
│   ├── generate_synthetic_data.py
│   ├── agents.csv
│   ├── transactions.csv
│   └── context_calendar.csv   # Event calendar for ContextEngine
│
└── scripts/
    └── seed_db.py             # Bulk seed via Prisma create_many
```


---

## Domain Model

### Entities

| Entity | Description |
|---|---|
| `AgentEntity` | An MFS super-agent outlet (id, name, phone, area, region) |
| `Transaction` | Single financial transaction (provider, type, amount, timestamp, account_ref) |
| `LiquiditySnapshot` | Point-in-time balance capture across all 4 providers |
| `ForecastHorizon` | Persisted forecast result per provider |
| `AnomalyFlag` | A detected suspicious pattern with tri-lingual explanations |
| `Alert` | Actionable alert with status machine (`open → acknowledged → in_progress → escalated → resolved`) |
| `AlertStateTransition` | Immutable audit record of every alert status change |
| `Case` | A grouped collection of related alerts |
| `DataFeedStatus` | Health status of each provider's data feed |
| `User` | Internal platform user with RBAC role |
| `AgentTraceLog` | AI pipeline execution trace for observability |

### Value Objects

| Value Object | Description |
|---|---|
| `Money` | Immutable BDT amount with `Decimal` precision. Validates non-negative. |
| `ConfidenceScore` | Float `[0.0, 1.0]`. Degrades via `degrade(factor)` when feeds are stale. |
| `Provider` | Enum: `bkash`, `nagad`, `rocket`, `physical` |
| `TransactionType` | Enum: `cash_in`, `cash_out`, `transfer`, `recharge` |
| `AlertType` | Enum: `liquidity_low`, `liquidity_critical`, `anomaly_detected`, `forecast_breach` |
| `AlertSeverity` | Enum: `low`, `medium`, `high`, `critical` |
| `AlertStatus` | Enum: `open`, `acknowledged`, `in_progress`, `escalated`, `resolved` |
| `AnomalyType` | Enum: `velocity_spike`, `transaction_splitting`, `circular_flow` |
| `UserRole` | Enum: `admin`, `regional_manager`, `area_manager`, `operator` |
| `ReviewLanguage` | Enum: `en`, `bn`, `banglish` |

### Alert State Machine

```
OPEN
 │
 ├──[acknowledge]──► ACKNOWLEDGED
 │                        │
 │                   [start_progress]──► IN_PROGRESS ──┐
 │                        │                             │
 │                   [escalate]──────► ESCALATED        │
 │                                         │            │
 └─────────────────────────────────────────┴──[resolve]─┴──► RESOLVED
```

Every transition is validated at the domain level and written to `alert_state_transitions` as an immutable audit record.

---

## Engine Layer

All engines are **deterministic** — pure Python functions with no AI calls, no I/O, no framework dependencies.

### LiquidityEngine

Computes a `LiquidityMatrix` from a `LiquiditySnapshot` and current feed health:

- Aggregates balances across bKash, Nagad, Rocket, and physical cash
- Degrades `ConfidenceScore` by 50% per stale data feed
- Detects `is_low` (< 20% of total) and `is_critical` (< 10% of total) thresholds on the lowest individual provider
- Returns `utilization_pct`, `lowest_provider`, and `degraded_providers` list

### ForecastEngine

Predicts per-provider balance at a configurable horizon (default 12 hours):

- Bins transactions into hourly net-flow buckets
- Fits **Simple Exponential Smoothing** (`statsmodels`) on the flow series
- Extrapolates forward and estimates `depletion_time_hours` via linear drain rate
- `ConfidenceScore` degrades with fewer observations and higher variance
- Falls back to current balance with 0.3 confidence if fewer than 6 observations

### AnomalyEngine

Detects three suspicious patterns. Language is always careful — never uses the word "fraud":

| Pattern | Method | Key Parameters |
|---|---|---|
| **Velocity Spike** | Z-score on hourly tx count and volume | Threshold: 2.5σ, rolling 24h window |
| **Transaction Splitting** | Near-identical amounts from same `account_ref` in short window | 3+ txs within 5% of mean, within 60 min |
| **Circular Flow** | Cash-out followed by cash-in to same ref | Within 6h, amounts within 10% |

All flags include `severity_score` (0–100), `confidence` (0–1), `evidence` dict, and explanations in EN / বাংলা / Banglish.

### ContextEngine

Cross-references spike timestamps against a `context_calendar.csv` event calendar (Eid, salary day, etc.):

- If the spike is within 120% of the expected event multiplier → **downgrade** anomaly confidence by 0.3
- If the spike exceeds the event multiplier by 50%+ → **upgrade** confidence by 0.1

### AlertService

Creates `Alert` entities from engine outputs:

- `create_liquidity_alert()` — from `LiquidityMatrix` threshold breach
- `create_anomaly_alert()` — from `AnomalyFlag`
- `create_forecast_alert()` — from `ForecastHorizon` when depletion < 6 hours
- `transition_alert()` — validates and applies state machine transitions + creates audit record


---

## AI Agent Layer

Built on the **OpenAI Agents SDK**. The pipeline is: engines run first (deterministic), then agents reason over the results via tools.

### Agents

| Agent | Model | Role |
|---|---|---|
| `CoordinatorAgent` | GPT-4o | Orchestrates all sub-agents. Produces final structured JSON advisory. |
| `OperationsAnalystAgent` | GPT-4o-mini | Interprets liquidity matrix and forecast data. |
| `ExplainabilityAgent` | GPT-4o-mini | Translates anomaly evidence into plain-language summaries. |
| `RecommendationAgent` | GPT-4o-mini | Generates actionable operational recommendations. |
| `ExecutiveAssistantAgent` | GPT-4o-mini | Produces concise executive summary. |

### Agent Tools

Each tool wraps pre-computed engine data — agents never run computations themselves:

| Tool | Data Provided |
|---|---|
| `get_liquidity_matrix` | Full `LiquidityMatrix` as JSON |
| `get_forecasts` | All 4 provider `ForecastResult` objects |
| `get_anomalies` | All detected `AnomalyResult` objects with evidence |
| `get_context_assessments` | Calendar context assessments keyed by date |

### AgentTraceLog

Every pipeline execution logs: agent name, input summary, output summary, tool calls, and duration in ms. Stored in the `agent_trace_logs` table for observability.

---

## Database Schema

All tables use UUID primary keys and snake_case column names. Prisma maps them to camelCase fields in the Python client.

### `agents`
| Column | Type | Notes |
|---|---|---|
| `id` | `varchar` PK | UUID |
| `name` | `varchar(200)` | |
| `phone` | `varchar(20)` | UNIQUE |
| `area` | `varchar(100)` | |
| `region` | `varchar(100)` | |
| `is_active` | `boolean` | Default: `true` |
| `created_at` | `timestamp` | Default: `now()` |

### `transactions`
| Column | Type | Notes |
|---|---|---|
| `id` | `varchar` PK | UUID |
| `agent_id` | `varchar` FK → `agents` | Indexed |
| `provider` | `varchar(20)` | `bkash\|nagad\|rocket\|physical` — Indexed |
| `transaction_type` | `varchar(20)` | `cash_in\|cash_out\|transfer\|recharge` |
| `amount` | `decimal(18,2)` | BDT |
| `timestamp` | `timestamp` | Indexed |
| `area` | `varchar(100)` | |
| `account_ref` | `varchar(100)` | Anonymised counterparty |
| `anomaly_flag_id` | `varchar` FK → `anomaly_flags` | Nullable |
| `metadata` | `jsonb` | Default: `{}` |

### `liquidity_snapshots`
| Column | Type | Notes |
|---|---|---|
| `id` | `varchar` PK | |
| `agent_id` | `varchar` FK → `agents` | Indexed |
| `physical_cash` | `decimal(18,2)` | |
| `bkash_balance` | `decimal(18,2)` | |
| `nagad_balance` | `decimal(18,2)` | |
| `rocket_balance` | `decimal(18,2)` | |
| `overall_confidence` | `float` | `[0.0, 1.0]` |
| `captured_at` | `timestamp` | Indexed, Default: `now()` |

### `forecast_horizons`
| Column | Type | Notes |
|---|---|---|
| `id` | `varchar` PK | |
| `agent_id` | `varchar` FK → `agents` | Indexed |
| `provider` | `varchar(20)` | |
| `forecast_hours` | `int` | |
| `predicted_balance` | `decimal(18,2)` | |
| `depletion_time_hours` | `float` | Nullable — `null` means no depletion expected |
| `confidence` | `float` | |
| `model_version` | `varchar(50)` | e.g. `ses_v1` |
| `generated_at` | `timestamp` | |

### `anomaly_flags`
| Column | Type | Notes |
|---|---|---|
| `id` | `varchar` PK | |
| `transaction_id` | `varchar` | Nullable (group-level flags have no single tx) |
| `transaction_group_ids` | `jsonb` | Array of transaction UUIDs |
| `flag_type` | `varchar(50)` | `velocity_spike\|transaction_splitting\|circular_flow` |
| `severity_score` | `int` | `0–100` |
| `confidence` | `float` | |
| `evidence` | `jsonb` | Raw signals |
| `explanation_en` | `text` | |
| `explanation_bn` | `text` | Bengali |
| `explanation_banglish` | `text` | Romanised Bengali |
| `review_language` | `varchar(20)` | Default: `en` |
| `is_reviewed` | `boolean` | Default: `false` |
| `created_at` | `timestamp` | |

### `alerts`
| Column | Type | Notes |
|---|---|---|
| `id` | `varchar` PK | |
| `agent_id` | `varchar` FK → `agents` | Indexed |
| `alert_type` | `varchar(50)` | `liquidity_low\|liquidity_critical\|anomaly_detected\|forecast_breach` |
| `severity` | `varchar(20)` | `low\|medium\|high\|critical` |
| `confidence` | `float` | |
| `evidence` | `jsonb` | |
| `status` | `varchar(20)` | Indexed, Default: `open` |
| `assigned_to_user_id` | `varchar` | Nullable |
| `anomaly_flag_id` | `varchar` | Nullable |
| `forecast_horizon_id` | `varchar` | Nullable |
| `notes` | `text` | |
| `created_at` | `timestamp` | Indexed |
| `updated_at` | `timestamp` | Auto-updated |

### `alert_state_transitions`
| Column | Type | Notes |
|---|---|---|
| `id` | `varchar` PK | |
| `alert_id` | `varchar` FK → `alerts` | Indexed |
| `from_status` | `varchar(20)` | |
| `to_status` | `varchar(20)` | |
| `actor_user_id` | `varchar` | |
| `note` | `text` | |
| `transitioned_at` | `timestamp` | |

### `cases`
| Column | Type | Notes |
|---|---|---|
| `id` | `varchar` PK | |
| `agent_id` | `varchar` FK → `agents` | Indexed |
| `title` | `varchar(500)` | |
| `alert_ids` | `jsonb` | Array of alert UUIDs |
| `status` | `varchar(20)` | `open\|closed` |
| `resolution_note` | `text` | |
| `created_at` | `timestamp` | |
| `updated_at` | `timestamp` | Auto-updated |

### `data_feed_statuses`
| Column | Type | Notes |
|---|---|---|
| `id` | `varchar` PK | |
| `provider` | `varchar(20)` | UNIQUE |
| `last_received_at` | `timestamp` | Nullable |
| `is_healthy` | `boolean` | |
| `staleness_threshold_seconds` | `int` | Default: `300` |

### `users`
| Column | Type | Notes |
|---|---|---|
| `id` | `varchar` PK | |
| `firebase_uid` | `varchar` | UNIQUE, Indexed |
| `phone` | `varchar(20)` | UNIQUE |
| `name` | `varchar(200)` | |
| `language` | `varchar(200)` |
| `region` | `varchar(100)` | Nullable |
| `area` | `varchar(100)` | Nullable |
| `is_active` | `boolean` | Default: `true` |
| `created_at` | `timestamp` | |

### `agent_trace_logs`
| Column | Type | Notes |
|---|---|---|
| `id` | `varchar` PK | |
| `request_id` | `varchar` | Indexed |
| `agent_name` | `varchar(100)` | |
| `input_summary` | `text` | First 500 chars of input |
| `output_summary` | `text` | First 500 chars of output |
| `tool_calls` | `jsonb` | Array of `{agent, tool}` records |
| `duration_ms` | `int` | |
| `created_at` | `timestamp` | |


---

## API Reference

Base URL: `http://localhost:8000`  
All `/api/v1/` routes require a Firebase Bearer token in the `Authorization` header.

### Health Check

#### `GET /health`

No authentication required.

**Response `200`**
```json
{
  "status": "ok",
  "env": "development"
}
```

---

### Snapshot

#### `POST /api/v1/snapshot/{agent_id}`

Runs the full liquidity intelligence pipeline for a given agent. This is the primary endpoint — it executes all engines and the AI agent layer synchronously and returns a complete advisory response.

**Path Parameters**

| Parameter | Type | Description |
|---|---|---|
| `agent_id` | `string` | UUID of the MFS super-agent |

**Headers**

| Header | Required | Description |
|---|---|---|
| `Authorization` | Yes | `Bearer <firebase_id_token>` |

**Response `200`** — `SnapshotResponse`

```json
{
  "request_id": "550e8400-e29b-41d4-a716-446655440000",
  "agent_id": "agent-uuid",
  "overall_confidence": 0.87,
  "generated_at": "2026-07-11T10:00:00Z",
  "liquidity": {
    "agent_id": "agent-uuid",
    "physical_cash_bdt": 45000.00,
    "bkash_balance_bdt": 32000.00,
    "nagad_balance_bdt": 18000.00,
    "rocket_balance_bdt": 9500.00,
    "total_liquidity_bdt": 104500.00,
    "utilization_pct": 56.9,
    "lowest_provider": "rocket",
    "is_low": false,
    "is_critical": false,
    "overall_confidence": 0.87,
    "degraded_providers": [],
    "captured_at": "2026-07-11T09:55:00Z"
  },
  "forecasts": [
    {
      "provider": "bkash",
      "current_balance_bdt": 32000.00,
      "predicted_balance_bdt": 28500.00,
      "depletion_time_hours": null,
      "hourly_net_flow_bdt": -291.67,
      "confidence": 0.74,
      "forecast_hours": 12
    }
  ],
  "anomaly_count": 1,
  "anomalies": [
    {
      "id": "flag_0",
      "flag_type": "velocity_spike",
      "severity_score": 62,
      "confidence": 0.81,
      "explanation_en": "Unusual transaction volume detected at 2026-07-11 08:00...",
      "explanation_bn": "২০২৬-০৭-১১ ০৮:০০ সময়ে অস্বাভাবিক লেনদেনের পরিমাণ...",
      "explanation_banglish": "08:00 te unusual transaction volume...",
      "transaction_count": 14,
      "is_reviewed": false,
      "created_at": "2026-07-11T10:00:00Z"
    }
  ],
  "agent_advisory": {
    "operational_status": "NORMAL",
    "summary": "Agent is operating within normal liquidity parameters...",
    "anomaly_summary": "One velocity spike detected this morning...",
    "recommendations": ["Monitor Rocket balance closely over next 6 hours"],
    "executive_summary": "All systems normal. One pattern flagged for review."
  }
}
```

**Error Responses**

| Code | Condition |
|---|---|
| `401` | Missing or invalid Firebase token |
| `403` | User not registered or account deactivated |
| `404` | Agent not found or no snapshot available |
| `500` | Internal server error |

---

### Alerts

#### `GET /api/v1/alerts`

List alerts. Defaults to open alerts scoped to the authenticated user's region/area.

**Query Parameters**

| Parameter | Type | Default | Description |
|---|---|---|---|
| `status_filter` | `string` | `open` | Filter by status: `open`, `acknowledged`, `in_progress`, `escalated`, `resolved` |
| `agent_id` | `string` | `null` | Filter to a specific agent |

**Response `200`** — `AlertListResponse`

```json
{
  "alerts": [
    {
      "id": "alert-uuid",
      "agent_id": "agent-uuid",
      "alert_type": "liquidity_low",
      "severity": "high",
      "confidence": 0.91,
      "evidence": {
        "lowest_provider": "rocket",
        "total_liquidity_bdt": 104500.0,
        "rocket_bdt": 9500.0
      },
      "status": "open",
      "assigned_to_user_id": null,
      "notes": "",
      "created_at": "2026-07-11T08:30:00Z",
      "updated_at": "2026-07-11T08:30:00Z"
    }
  ],
  "total": 1
}
```

---

#### `GET /api/v1/alerts/{alert_id}`

Retrieve a single alert by ID.

**Path Parameters**

| Parameter | Type | Description |
|---|---|---|
| `alert_id` | `string` | UUID of the alert |

**Response `200`** — `AlertResponse`

**Error Responses**

| Code | Condition |
|---|---|
| `404` | Alert not found |

---

#### `POST /api/v1/alerts/{alert_id}/acknowledge`

Acknowledge an open alert. Assigns it to the requesting user. Transition: `OPEN → ACKNOWLEDGED`.

**Request Body** — `AlertTransitionRequest`

```json
{
  "note": "Reviewed and assigned to field team."
}
```

**Response `200`** — `AlertResponse` with `status: "acknowledged"`

**Error Responses**

| Code | Condition |
|---|---|
| `400` | Invalid state transition (e.g., alert is not OPEN) |
| `404` | Alert not found |

---

#### `POST /api/v1/alerts/{alert_id}/escalate`

Escalate an acknowledged or in-progress alert. Transition: `ACKNOWLEDGED|IN_PROGRESS → ESCALATED`.

**Request Body** — `AlertTransitionRequest`

```json
{
  "note": "Exceeds area manager authority. Escalating to regional."
}
```

**Response `200`** — `AlertResponse` with `status: "escalated"`

---

#### `POST /api/v1/alerts/{alert_id}/resolve`

Resolve an alert. Transition: `ACKNOWLEDGED|IN_PROGRESS|ESCALATED → RESOLVED`.

**Request Body** — `AlertTransitionRequest`

```json
{
  "note": "Agent topped up Rocket balance. Issue resolved."
}
```

**Response `200`** — `AlertResponse` with `status: "resolved"`


---

## Request & Response Schemas

### `SnapshotResponse`

| Field | Type | Description |
|---|---|---|
| `request_id` | `string` | UUID for this request (set via `X-Request-ID` header or auto-generated) |
| `agent_id` | `string` | |
| `liquidity` | `LiquidityMatrixResponse` | Current liquidity state |
| `forecasts` | `ForecastSchema[]` | One forecast per provider |
| `anomaly_count` | `int` | Number of anomalies detected |
| `anomalies` | `AnomalyFlagSchema[]` | Detailed anomaly records |
| `agent_advisory` | `object` | Structured JSON from CoordinatorAgent |
| `overall_confidence` | `float` | Aggregate confidence score `[0.0, 1.0]` |
| `generated_at` | `datetime` | UTC timestamp |

### `LiquidityMatrixResponse`

| Field | Type | Description |
|---|---|---|
| `physical_cash_bdt` | `float` | Physical cash balance in BDT |
| `bkash_balance_bdt` | `float` | bKash wallet balance |
| `nagad_balance_bdt` | `float` | Nagad wallet balance |
| `rocket_balance_bdt` | `float` | Rocket wallet balance |
| `total_liquidity_bdt` | `float` | Sum of all four |
| `utilization_pct` | `float` | % of float deployed in provider wallets |
| `lowest_provider` | `string` | Provider with minimum balance |
| `is_low` | `bool` | True if lowest provider balance < 20% of total |
| `is_critical` | `bool` | True if lowest provider balance < 10% of total |
| `overall_confidence` | `float` | Degraded per stale feed |
| `degraded_providers` | `string[]` | Providers with stale data feeds |
| `captured_at` | `datetime` | Snapshot timestamp |

### `ForecastSchema`

| Field | Type | Description |
|---|---|---|
| `provider` | `string` | `bkash\|nagad\|rocket\|physical` |
| `current_balance_bdt` | `float` | |
| `predicted_balance_bdt` | `float` | Predicted balance at horizon |
| `depletion_time_hours` | `float\|null` | Hours until zero; `null` if no depletion expected |
| `hourly_net_flow_bdt` | `float` | Mean hourly flow; negative = draining |
| `confidence` | `float` | |
| `forecast_hours` | `int` | Horizon window (default 12) |

### `AnomalyFlagSchema`

| Field | Type | Description |
|---|---|---|
| `flag_type` | `string` | `velocity_spike\|transaction_splitting\|circular_flow` |
| `severity_score` | `int` | `0–100` |
| `confidence` | `float` | Adjusted by ContextEngine |
| `explanation_en` | `string` | English explanation |
| `explanation_bn` | `string` | Bengali (বাংলা) explanation |
| `explanation_banglish` | `string` | Romanised Bengali explanation |
| `transaction_count` | `int` | Number of transactions in the group |
| `is_reviewed` | `bool` | |

### `AlertResponse`

| Field | Type | Description |
|---|---|---|
| `id` | `string` | UUID |
| `agent_id` | `string` | |
| `alert_type` | `string` | `liquidity_low\|liquidity_critical\|anomaly_detected\|forecast_breach` |
| `severity` | `string` | `low\|medium\|high\|critical` |
| `confidence` | `float` | |
| `evidence` | `object` | Raw evidence dict (content varies by alert type) |
| `status` | `string` | Current state machine status |
| `assigned_to_user_id` | `string\|null` | Set on acknowledge |
| `notes` | `string` | Accumulated notes from transitions |
| `created_at` | `datetime` | |
| `updated_at` | `datetime` | |

### `AlertTransitionRequest`

| Field | Type | Constraints | Description |
|---|---|---|---|
| `note` | `string` | max 1000 chars, default `""` | Optional note to attach to the transition |

### `AlertListResponse`

| Field | Type | Description |
|---|---|---|
| `alerts` | `AlertResponse[]` | |
| `total` | `int` | Total count returned |

### Error Envelope

All error responses use a consistent envelope:

```json
{
  "error": {
    "code": "INTERNAL_SERVER_ERROR",
    "message": "An unexpected error occurred.",
    "request_id": "550e8400-e29b-41d4-a716-446655440000"
  }
}
```

---

## Authentication & RBAC

### Firebase Authentication

All `/api/v1/` routes verify a Firebase ID token:

```
Authorization: Bearer <firebase_id_token>
```

The token is verified using the Firebase Admin SDK. The decoded `uid` is resolved to an internal `User` entity via the `users` table (`firebase_uid` index). The request is rejected with `401` if the token is invalid or `403` if the user is not registered or deactivated.

### Roles

| Role | Description |
|---|---|
| `admin` | Full platform access |
| `regional_manager` | Access to all agents in their region |
| `area_manager` | Access to all agents in their area |
| `operator` | Limited access, own agent only |

Alert listing is automatically scoped to the authenticated user's `region` and `area` fields unless a specific `agent_id` is provided.

### Middleware

Every request is assigned a `request_id` (from `X-Request-ID` header, or auto-generated UUID). It is:
- Bound to the structlog context for all log lines in that request
- Returned in the `X-Request-ID` response header
- Included in all error envelopes

---

## Configuration

All settings are loaded from the `.env` file at the `liquidity-intelligence/` working directory via `pydantic-settings`.

| Variable | Required | Description |
|---|---|---|
| `DATABASE_URL` | Yes | Supabase pooled connection string (port 6543). Must include `?pgbouncer=true&connection_limit=1` |
| `DIRECT_URL` | Yes | Supabase direct connection string (port 5432). Used by `prisma db push` / `prisma migrate` |
| `SUPABASE_URL` | Yes | Supabase project URL (`https://[ref].supabase.co`) |
| `SUPABASE_KEY` | Yes | Supabase service role or anon key |
| `OPENAI_API_KEY` | Yes | OpenAI API key for GPT-4o / GPT-4o-mini |
| `FIREBASE_PROJECT_ID` | Yes | Firebase project ID |
| `FIREBASE_CLIENT_EMAIL` | Yes | Firebase service account client email |
| `FIREBASE_PRIVATE_KEY` | Yes | Firebase service account private key (newlines as `\n`) |
| `JWT_SECRET` | No | Fallback JWT secret for local dev |
| `APP_ENV` | No | `development` (default) or `production` |
| `LOG_LEVEL` | No | `INFO` (default), `DEBUG`, `WARNING`, `ERROR` |
| `LOW_LIQUIDITY_THRESHOLD_PCT` | No | Default: `20.0` |
| `CRITICAL_LIQUIDITY_THRESHOLD_PCT` | No | Default: `10.0` |
| `ANOMALY_ZSCORE_THRESHOLD` | No | Default: `2.5` |
| `ANOMALY_ROLLING_WINDOW_HOURS` | No | Default: `24` |
| `FORECAST_HORIZON_HOURS` | No | Default: `12` |

### Supabase Connection Strings

```
# Pooled — used at runtime (PgBouncer Transaction mode)
DATABASE_URL=postgresql://postgres.[ref]:[pass]@aws-0-[region].pooler.supabase.com:6543/postgres?pgbouncer=true&connection_limit=1

# Direct — used for schema migrations only
DIRECT_URL=postgresql://postgres.[ref]:[pass]@aws-0-[region].pooler.supabase.com:5432/postgres
```

> The `?pgbouncer=true` flag disables prepared statements, which is required when using PgBouncer in Transaction pooling mode.

---

## Local Setup

### Prerequisites

- Python 3.13+
- A Supabase project (free tier is sufficient)
- A Firebase project with a service account
- An OpenAI API key

### 1. Create and activate virtual environment

```bash
cd "backend"
python3 -m venv .venv
source .venv/bin/activate
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure environment

Copy the template and fill in your values:

```bash
cp .env.example .env   # or edit .env directly
```

### 4. Generate Prisma client

```bash
cd liquidity-intelligence
prisma generate
```

### 5. Push schema to Supabase

```bash
prisma db push
```

For production, use migrations instead:

```bash
prisma migrate dev --name init
```

### 6. Generate synthetic data

```bash
python data/generate_synthetic_data.py
```

### 7. Seed the database

```bash
python scripts/seed_db.py
```

### 8. Run the server

```bash
uvicorn app.main:app --reload --port 8000
```

- API: `http://localhost:8000`
- Interactive docs: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

---

## Data Pipeline

### Synthetic Data Generator

`data/generate_synthetic_data.py` produces:

- `agents.csv` — 10 MFS super-agent outlets across Bangladesh (Dhaka, Chittagong, Sylhet regions)
- `transactions.csv` — ~24,000 transactions over 90 days with realistic volume patterns
- `injected_anomalies.csv` — Ground truth for validation (velocity spikes, splitting patterns, circular flows)

### Context Calendar

`data/context_calendar.csv` contains Bangladeshi financial events with expected volume multipliers:

| Event | Expected Multiplier |
|---|---|
| Eid-ul-Fitr | 3.5× |
| Eid-ul-Adha | 3.0× |
| Salary Day (25th–1st) | 2.5× |
| Pohela Boishakh | 2.0× |

The `ContextEngine` uses this to distinguish legitimate demand surges from suspicious activity and adjusts anomaly confidence accordingly.

### Seed Script

`scripts/seed_db.py` uses `create_many(skip_duplicates=True)` in batches of 1,000 rows for fast bulk insertion:

```
✓ Agents seeded:              10
✓ Transactions seeded:    24,002
✓ Liquidity snapshots:        10
✓ Data feed statuses:          4
```

---

*Built for SUST Hackathon 2026 — Advisory only. Never executes financial transactions.*
