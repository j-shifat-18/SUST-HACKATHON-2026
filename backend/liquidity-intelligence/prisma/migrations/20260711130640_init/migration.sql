-- CreateTable
CREATE TABLE "agents" (
    "id" TEXT NOT NULL,
    "name" VARCHAR(200) NOT NULL,
    "phone" VARCHAR(20) NOT NULL,
    "area" VARCHAR(100) NOT NULL,
    "region" VARCHAR(100) NOT NULL,
    "is_active" BOOLEAN NOT NULL DEFAULT true,
    "created_at" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "agents_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "transactions" (
    "id" TEXT NOT NULL,
    "agent_id" TEXT NOT NULL,
    "provider" VARCHAR(20) NOT NULL,
    "transaction_type" VARCHAR(20) NOT NULL,
    "amount" DECIMAL(18,2) NOT NULL,
    "timestamp" TIMESTAMP(3) NOT NULL,
    "area" VARCHAR(100) NOT NULL,
    "account_ref" VARCHAR(100) NOT NULL,
    "anomaly_flag_id" TEXT,
    "metadata" JSONB NOT NULL DEFAULT '{}',

    CONSTRAINT "transactions_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "liquidity_snapshots" (
    "id" TEXT NOT NULL,
    "agent_id" TEXT NOT NULL,
    "physical_cash" DECIMAL(18,2) NOT NULL,
    "bkash_balance" DECIMAL(18,2) NOT NULL,
    "nagad_balance" DECIMAL(18,2) NOT NULL,
    "rocket_balance" DECIMAL(18,2) NOT NULL,
    "overall_confidence" DOUBLE PRECISION NOT NULL,
    "captured_at" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "liquidity_snapshots_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "forecast_horizons" (
    "id" TEXT NOT NULL,
    "agent_id" TEXT NOT NULL,
    "provider" VARCHAR(20) NOT NULL,
    "forecast_hours" INTEGER NOT NULL,
    "predicted_balance" DECIMAL(18,2) NOT NULL,
    "depletion_time_hours" DOUBLE PRECISION,
    "confidence" DOUBLE PRECISION NOT NULL,
    "model_version" VARCHAR(50) NOT NULL,
    "generated_at" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "forecast_horizons_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "anomaly_flags" (
    "id" TEXT NOT NULL,
    "transaction_id" TEXT,
    "transaction_group_ids" JSONB NOT NULL DEFAULT '[]',
    "flag_type" VARCHAR(50) NOT NULL,
    "severity_score" INTEGER NOT NULL,
    "confidence" DOUBLE PRECISION NOT NULL,
    "evidence" JSONB NOT NULL,
    "explanation_en" TEXT NOT NULL,
    "explanation_bn" TEXT NOT NULL,
    "explanation_banglish" TEXT NOT NULL,
    "review_language" VARCHAR(20) NOT NULL DEFAULT 'en',
    "is_reviewed" BOOLEAN NOT NULL DEFAULT false,
    "created_at" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "anomaly_flags_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "alerts" (
    "id" TEXT NOT NULL,
    "agent_id" TEXT NOT NULL,
    "alert_type" VARCHAR(50) NOT NULL,
    "severity" VARCHAR(20) NOT NULL,
    "confidence" DOUBLE PRECISION NOT NULL,
    "evidence" JSONB NOT NULL,
    "status" VARCHAR(20) NOT NULL DEFAULT 'open',
    "assigned_to_user_id" TEXT,
    "anomaly_flag_id" TEXT,
    "forecast_horizon_id" TEXT,
    "notes" TEXT NOT NULL DEFAULT '',
    "created_at" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "alerts_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "alert_state_transitions" (
    "id" TEXT NOT NULL,
    "alert_id" TEXT NOT NULL,
    "from_status" VARCHAR(20) NOT NULL,
    "to_status" VARCHAR(20) NOT NULL,
    "actor_user_id" TEXT NOT NULL,
    "note" TEXT NOT NULL DEFAULT '',
    "transitioned_at" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "alert_state_transitions_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "cases" (
    "id" TEXT NOT NULL,
    "agent_id" TEXT NOT NULL,
    "title" VARCHAR(500) NOT NULL,
    "alert_ids" JSONB NOT NULL DEFAULT '[]',
    "status" VARCHAR(20) NOT NULL DEFAULT 'open',
    "resolution_note" TEXT NOT NULL DEFAULT '',
    "created_at" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "cases_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "data_feed_statuses" (
    "id" TEXT NOT NULL,
    "provider" VARCHAR(20) NOT NULL,
    "last_received_at" TIMESTAMP(3),
    "is_healthy" BOOLEAN NOT NULL DEFAULT true,
    "staleness_threshold_seconds" INTEGER NOT NULL DEFAULT 300,

    CONSTRAINT "data_feed_statuses_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "users" (
    "id" TEXT NOT NULL,
    "firebase_uid" TEXT NOT NULL,
    "phone" VARCHAR(20) NOT NULL,
    "name" VARCHAR(200) NOT NULL,
    "role" VARCHAR(30) NOT NULL,
    "region" VARCHAR(100),
    "area" VARCHAR(100),
    "is_active" BOOLEAN NOT NULL DEFAULT true,
    "created_at" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "users_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "agent_trace_logs" (
    "id" TEXT NOT NULL,
    "request_id" TEXT NOT NULL,
    "agent_name" VARCHAR(100) NOT NULL,
    "input_summary" TEXT NOT NULL,
    "output_summary" TEXT NOT NULL,
    "tool_calls" JSONB NOT NULL DEFAULT '[]',
    "duration_ms" INTEGER NOT NULL,
    "created_at" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "agent_trace_logs_pkey" PRIMARY KEY ("id")
);

-- CreateIndex
CREATE UNIQUE INDEX "agents_phone_key" ON "agents"("phone");

-- CreateIndex
CREATE INDEX "transactions_agent_id_idx" ON "transactions"("agent_id");

-- CreateIndex
CREATE INDEX "transactions_provider_idx" ON "transactions"("provider");

-- CreateIndex
CREATE INDEX "transactions_timestamp_idx" ON "transactions"("timestamp");

-- CreateIndex
CREATE INDEX "liquidity_snapshots_agent_id_idx" ON "liquidity_snapshots"("agent_id");

-- CreateIndex
CREATE INDEX "liquidity_snapshots_captured_at_idx" ON "liquidity_snapshots"("captured_at");

-- CreateIndex
CREATE INDEX "forecast_horizons_agent_id_idx" ON "forecast_horizons"("agent_id");

-- CreateIndex
CREATE INDEX "alerts_agent_id_idx" ON "alerts"("agent_id");

-- CreateIndex
CREATE INDEX "alerts_status_idx" ON "alerts"("status");

-- CreateIndex
CREATE INDEX "alerts_created_at_idx" ON "alerts"("created_at");

-- CreateIndex
CREATE INDEX "alert_state_transitions_alert_id_idx" ON "alert_state_transitions"("alert_id");

-- CreateIndex
CREATE INDEX "cases_agent_id_idx" ON "cases"("agent_id");

-- CreateIndex
CREATE UNIQUE INDEX "data_feed_statuses_provider_key" ON "data_feed_statuses"("provider");

-- CreateIndex
CREATE UNIQUE INDEX "users_firebase_uid_key" ON "users"("firebase_uid");

-- CreateIndex
CREATE UNIQUE INDEX "users_phone_key" ON "users"("phone");

-- CreateIndex
CREATE INDEX "users_firebase_uid_idx" ON "users"("firebase_uid");

-- CreateIndex
CREATE INDEX "agent_trace_logs_request_id_idx" ON "agent_trace_logs"("request_id");

-- AddForeignKey
ALTER TABLE "transactions" ADD CONSTRAINT "transactions_agent_id_fkey" FOREIGN KEY ("agent_id") REFERENCES "agents"("id") ON DELETE RESTRICT ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "transactions" ADD CONSTRAINT "transactions_anomaly_flag_id_fkey" FOREIGN KEY ("anomaly_flag_id") REFERENCES "anomaly_flags"("id") ON DELETE SET NULL ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "liquidity_snapshots" ADD CONSTRAINT "liquidity_snapshots_agent_id_fkey" FOREIGN KEY ("agent_id") REFERENCES "agents"("id") ON DELETE RESTRICT ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "forecast_horizons" ADD CONSTRAINT "forecast_horizons_agent_id_fkey" FOREIGN KEY ("agent_id") REFERENCES "agents"("id") ON DELETE RESTRICT ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "alerts" ADD CONSTRAINT "alerts_agent_id_fkey" FOREIGN KEY ("agent_id") REFERENCES "agents"("id") ON DELETE RESTRICT ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "alert_state_transitions" ADD CONSTRAINT "alert_state_transitions_alert_id_fkey" FOREIGN KEY ("alert_id") REFERENCES "alerts"("id") ON DELETE RESTRICT ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "cases" ADD CONSTRAINT "cases_agent_id_fkey" FOREIGN KEY ("agent_id") REFERENCES "agents"("id") ON DELETE RESTRICT ON UPDATE CASCADE;
