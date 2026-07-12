"use client";

import React, { useState, useEffect } from "react";
import {
  Wallet,
  TrendingDown,
  AlertTriangle,
  Activity,
  RefreshCw,
  Zap,
  Users,
  ShieldCheck,
  Settings,
  X,
  Save,
} from "lucide-react";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell,
} from "recharts";
import { useDashboard } from "../context/DashboardContext";

const PROVIDER_COLORS = {
  bkash: "#E2136E",
  nagad: "#F04923",
  rocket: "#8C3494",
  physical: "#2CD4BF",
};

export default function HomeView({ userProfile }) {
  const { snapshot, loading, error, fetchSnapshot, fetchAlerts, alerts, fetchWithAuth } = useDashboard();
  const [snapshotData, setSnapshotData] = useState(null);
  const [autoLoading, setAutoLoading] = useState(true);
  const [showBalanceModal, setShowBalanceModal] = useState(false);
  const [balanceForm, setBalanceForm] = useState({
    physical_cash: "",
    bkash_balance: "",
    nagad_balance: "",
    rocket_balance: "",
  });
  const [savingBalance, setSavingBalance] = useState(false);

  useEffect(() => {
    loadUserData();
  }, []);

  const loadUserData = async () => {
    setAutoLoading(true);
    await fetchAlerts("open");
    if (userProfile?.id) {
      const data = await fetchSnapshot(userProfile.id);
      if (data) setSnapshotData(data);
    }
    setAutoLoading(false);
  };

  const handleRefresh = () => {
    loadUserData();
  };

  const openBalanceModal = () => {
    // Pre-fill with current values if available
    if (liquidity) {
      setBalanceForm({
        physical_cash: Math.round(liquidity.physical_cash_bdt).toString(),
        bkash_balance: Math.round(liquidity.bkash_balance_bdt).toString(),
        nagad_balance: Math.round(liquidity.nagad_balance_bdt).toString(),
        rocket_balance: Math.round(liquidity.rocket_balance_bdt).toString(),
      });
    }
    setShowBalanceModal(true);
  };

  const handleSaveBalance = async () => {
    setSavingBalance(true);
    try {
      const body = { agent_id: userProfile.id };
      if (balanceForm.physical_cash) body.physical_cash = parseFloat(balanceForm.physical_cash);
      if (balanceForm.bkash_balance) body.bkash_balance = parseFloat(balanceForm.bkash_balance);
      if (balanceForm.nagad_balance) body.nagad_balance = parseFloat(balanceForm.nagad_balance);
      if (balanceForm.rocket_balance) body.rocket_balance = parseFloat(balanceForm.rocket_balance);

      await fetchWithAuth("/api/v1/transactions/balance", {
        method: "POST",
        body: JSON.stringify(body),
      });

      setShowBalanceModal(false);
      // Reload data
      await loadUserData();
    } catch (err) {
      console.error("Failed to save balance:", err);
    }
    setSavingBalance(false);
  };

  const liquidity = snapshotData?.liquidity;
  const forecasts = snapshotData?.forecasts || [];
  const anomalies = snapshotData?.anomalies || [];

  const balanceChartData = liquidity
    ? [
        { name: "Physical", value: liquidity.physical_cash_bdt, fill: PROVIDER_COLORS.physical },
        { name: "bKash", value: liquidity.bkash_balance_bdt, fill: PROVIDER_COLORS.bkash },
        { name: "Nagad", value: liquidity.nagad_balance_bdt, fill: PROVIDER_COLORS.nagad },
        { name: "Rocket", value: liquidity.rocket_balance_bdt, fill: PROVIDER_COLORS.rocket },
      ]
    : [];

  const forecastChartData = forecasts.map((f) => ({
    provider: f.provider.charAt(0).toUpperCase() + f.provider.slice(1),
    current: f.current_balance_bdt,
    predicted: f.predicted_balance_bdt,
  }));

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-heading">
            Welcome back, {userProfile?.name?.split(" ")[0] || "Officer"}
          </h1>
          <p className="text-sm text-muted-custom mt-0.5">
            {userProfile?.district}, {userProfile?.division} — Real-time liquidity overview
          </p>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={openBalanceModal}
            className="flex items-center gap-1.5 px-3 py-2 bg-primary/10 border border-primary/20 rounded-lg text-xs font-medium text-primary hover:bg-primary/20 transition-all cursor-pointer"
          >
            <Settings size={14} />
            Set Balances
          </button>
          <button
            onClick={handleRefresh}
            disabled={loading || autoLoading}
            className="flex items-center gap-2 px-3 py-2 bg-surface-elevated border border-border-light rounded-lg text-xs text-muted-custom hover:text-heading transition-all cursor-pointer disabled:opacity-50"
          >
            <RefreshCw size={14} className={(loading || autoLoading) ? "animate-spin" : ""} />
            Refresh
          </button>
        </div>
      </div>

      {/* User Info Card */}
      <div className="bg-surface border border-border-custom rounded-xl p-4">
        <div className="flex items-center gap-4">
          <div className="w-12 h-12 rounded-xl bg-primary/15 flex items-center justify-center">
            <Users size={22} className="text-primary" />
          </div>
          <div className="flex-1">
            <h3 className="text-sm font-semibold text-heading">{userProfile?.name}</h3>
            <p className="text-xs text-muted-custom mt-0.5">
              {userProfile?.phone} • {userProfile?.role || "Operator"} • {userProfile?.district}, {userProfile?.division}
            </p>
          </div>
          <div className="flex items-center gap-1.5 px-2.5 py-1 bg-primary/10 rounded-lg">
            <ShieldCheck size={12} className="text-primary" />
            <span className="text-[10px] font-medium text-primary">Active Session</span>
          </div>
        </div>
      </div>

      {/* Quick Stats */}
      {liquidity ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          <StatCard
            icon={Wallet}
            label="Total Liquidity"
            value={`৳${formatNumber(liquidity.total_liquidity_bdt)}`}
            sub={`${liquidity.utilization_pct}% utilization`}
            color="primary"
          />
          <StatCard
            icon={liquidity.is_critical ? AlertTriangle : TrendingDown}
            label="Lowest Provider"
            value={liquidity.lowest_provider.charAt(0).toUpperCase() + liquidity.lowest_provider.slice(1)}
            sub={liquidity.is_critical ? "CRITICAL" : liquidity.is_low ? "LOW" : "Normal"}
            color={liquidity.is_critical ? "error" : liquidity.is_low ? "warning" : "primary"}
          />
          <StatCard
            icon={Activity}
            label="Confidence"
            value={`${(liquidity.overall_confidence * 100).toFixed(0)}%`}
            sub={liquidity.degraded_providers.length > 0 ? `${liquidity.degraded_providers.length} degraded` : "All feeds healthy"}
            color={liquidity.overall_confidence > 0.7 ? "primary" : "warning"}
          />
          <StatCard
            icon={AlertTriangle}
            label="Active Alerts"
            value={alerts.length}
            sub={`${snapshotData?.anomaly_count || 0} anomalies detected`}
            color={alerts.length > 0 ? "warning" : "primary"}
          />
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          <StatCard icon={AlertTriangle} label="Active Alerts" value={alerts.length} sub="In your region" color={alerts.length > 0 ? "warning" : "primary"} />
          <StatCard icon={Activity} label="Region" value={userProfile?.division || "—"} sub={userProfile?.district || ""} color="primary" />
          <StatCard icon={Users} label="Role" value={userProfile?.role || "operator"} sub="Access level" color="primary" />
          <StatCard icon={ShieldCheck} label="Status" value="Online" sub="Session active" color="primary" />
        </div>
      )}

      {/* Charts Row */}
      {liquidity && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          {/* Balance Distribution */}
          <div className="bg-surface border border-border-custom rounded-xl p-5">
            <h3 className="text-sm font-semibold text-heading mb-4">Balance Distribution</h3>
            <ResponsiveContainer width="100%" height={220}>
              <PieChart>
                <Pie
                  data={balanceChartData}
                  cx="50%"
                  cy="50%"
                  innerRadius={55}
                  outerRadius={85}
                  paddingAngle={3}
                  dataKey="value"
                >
                  {balanceChartData.map((entry, index) => (
                    <Cell key={index} fill={entry.fill} />
                  ))}
                </Pie>
                <Tooltip
                  contentStyle={{ backgroundColor: "#1F2937", border: "1px solid #374151", borderRadius: "8px", color: "#F9FAFB", fontSize: "12px" }}
                  formatter={(value) => [`৳${formatNumber(value)}`, ""]}
                />
              </PieChart>
            </ResponsiveContainer>
            <div className="flex flex-wrap justify-center gap-3 mt-2">
              {balanceChartData.map((item) => (
                <div key={item.name} className="flex items-center gap-1.5">
                  <div className="w-2.5 h-2.5 rounded-full" style={{ backgroundColor: item.fill }} />
                  <span className="text-xs text-muted-custom">{item.name}: ৳{formatNumber(item.value)}</span>
                </div>
              ))}
            </div>
          </div>

          {/* Forecast Comparison */}
          <div className="bg-surface border border-border-custom rounded-xl p-5">
            <h3 className="text-sm font-semibold text-heading mb-4">Current vs Predicted (12h)</h3>
            <ResponsiveContainer width="100%" height={220}>
              <BarChart data={forecastChartData} barGap={4}>
                <CartesianGrid strokeDasharray="3 3" stroke="#1F2937" />
                <XAxis dataKey="provider" tick={{ fill: "#6B7280", fontSize: 11 }} />
                <YAxis tick={{ fill: "#6B7280", fontSize: 11 }} tickFormatter={(v) => `৳${(v / 1000).toFixed(0)}k`} />
                <Tooltip
                  contentStyle={{ backgroundColor: "#1F2937", border: "1px solid #374151", borderRadius: "8px", color: "#F9FAFB", fontSize: "12px" }}
                  formatter={(value) => [`৳${formatNumber(value)}`, ""]}
                />
                <Bar dataKey="current" fill="#2CD4BF" radius={[4, 4, 0, 0]} name="Current" />
                <Bar dataKey="predicted" fill="#6366F1" radius={[4, 4, 0, 0]} name="Predicted" />
              </BarChart>
            </ResponsiveContainer>
            <div className="flex justify-center gap-4 mt-2">
              <div className="flex items-center gap-1.5">
                <div className="w-2.5 h-2.5 rounded-full bg-primary" />
                <span className="text-[10px] text-muted-custom">Current</span>
              </div>
              <div className="flex items-center gap-1.5">
                <div className="w-2.5 h-2.5 rounded-full bg-secondary" />
                <span className="text-[10px] text-muted-custom">Predicted (12h)</span>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Advisory */}
      {snapshotData?.agent_advisory && (
        <div className="bg-surface border border-border-custom rounded-xl p-5">
          <h3 className="text-sm font-semibold text-heading mb-3 flex items-center gap-2">
            <Zap size={14} className="text-primary" />
            AI Advisory
          </h3>
          <div className="space-y-3">
            <div className="flex items-start gap-3">
              <span className={`inline-block px-2 py-0.5 rounded text-[10px] font-bold uppercase ${
                snapshotData.agent_advisory.operational_status === "NORMAL"
                  ? "bg-primary/10 text-primary"
                  : "bg-warning-custom/10 text-warning-custom"
              }`}>
                {snapshotData.agent_advisory.operational_status}
              </span>
              <p className="text-sm text-text-main flex-1">{snapshotData.agent_advisory.summary}</p>
            </div>
            {snapshotData.agent_advisory.recommendations?.length > 0 && (
              <div className="bg-surface-elevated rounded-lg p-3 mt-2">
                <p className="text-xs font-semibold text-heading mb-1.5">Recommendations</p>
                <ul className="space-y-1">
                  {snapshotData.agent_advisory.recommendations.map((rec, i) => (
                    <li key={i} className="text-xs text-muted-custom flex items-start gap-2">
                      <span className="text-primary mt-0.5">•</span>
                      {rec}
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Anomalies */}
      {anomalies.length > 0 && (
        <div className="bg-surface border border-border-custom rounded-xl p-5">
          <h3 className="text-sm font-semibold text-heading mb-3">Detected Patterns</h3>
          <div className="space-y-2">
            {anomalies.map((anomaly, i) => (
              <div key={i} className="bg-surface-elevated border border-border-light rounded-lg p-3">
                <div className="flex items-center justify-between mb-1">
                  <span className="text-xs font-semibold text-heading capitalize">{anomaly.flag_type.replace(/_/g, " ")}</span>
                  <div className="flex items-center gap-2">
                    <span className="text-[10px] text-muted-custom">Severity: {anomaly.severity_score}/100</span>
                    <span className="text-[10px] text-muted-custom">Confidence: {(anomaly.confidence * 100).toFixed(0)}%</span>
                  </div>
                </div>
                <p className="text-xs text-text-main">{anomaly.explanation_en}</p>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Recent Alerts Preview */}
      {alerts.length > 0 && !liquidity && (
        <div className="bg-surface border border-border-custom rounded-xl p-5">
          <h3 className="text-sm font-semibold text-heading mb-3 flex items-center gap-2">
            <AlertTriangle size={14} className="text-warning-custom" />
            Recent Alerts in Your Region
          </h3>
          <div className="space-y-2">
            {alerts.slice(0, 5).map((alert) => (
              <div key={alert.id} className="bg-surface-elevated border border-border-light rounded-lg p-3 flex items-center justify-between">
                <div>
                  <p className="text-xs font-semibold text-heading capitalize">{alert.alert_type.replace(/_/g, " ")}</p>
                  <p className="text-[10px] text-muted-custom mt-0.5">{new Date(alert.created_at).toLocaleString()}</p>
                </div>
                <span className={`px-1.5 py-0.5 rounded text-[9px] font-bold uppercase ${
                  alert.severity === "critical" ? "bg-error-custom/10 text-error-custom" :
                  alert.severity === "high" ? "bg-warning-custom/10 text-warning-custom" :
                  "bg-info-custom/10 text-info-custom"
                }`}>
                  {alert.severity}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Loading state */}
      {(loading || autoLoading) && !snapshotData && (
        <div className="bg-surface border border-border-custom rounded-xl p-10 text-center">
          <RefreshCw size={28} className="text-primary mx-auto mb-3 animate-spin" />
          <p className="text-sm text-muted-custom">Loading your liquidity data...</p>
        </div>
      )}

      {/* Empty state */}
      {!snapshotData && !loading && !autoLoading && alerts.length === 0 && (
        <div className="bg-surface border border-border-custom rounded-xl p-12 text-center">
          <Activity size={40} className="text-muted-custom mx-auto mb-3 opacity-40" />
          <p className="text-sm text-muted-custom">No liquidity data available yet</p>
          <p className="text-xs text-muted-custom mt-1">Click "Set Balances" above to enter your current cash and provider balances</p>
        </div>
      )}

      {/* Balance Modal */}
      {showBalanceModal && (
        <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50 p-4">
          <div className="bg-surface border border-border-custom rounded-xl p-6 w-full max-w-md">
            <div className="flex items-center justify-between mb-5">
              <div className="flex items-center gap-2">
                <Wallet size={18} className="text-primary" />
                <h3 className="text-sm font-bold text-heading">Update Balances</h3>
              </div>
              <button
                onClick={() => setShowBalanceModal(false)}
                className="w-7 h-7 rounded-lg bg-surface-elevated flex items-center justify-center text-muted-custom hover:text-heading cursor-pointer"
              >
                <X size={14} />
              </button>
            </div>

            <p className="text-xs text-muted-custom mb-4">
              Enter your current cash and provider e-money balances. This sets the baseline — all future transactions will adjust these values automatically.
            </p>

            <div className="space-y-3">
              <BalanceInput
                label="Physical Cash (৳)"
                value={balanceForm.physical_cash}
                onChange={(v) => setBalanceForm((p) => ({ ...p, physical_cash: v }))}
                color="#2CD4BF"
              />
              <BalanceInput
                label="bKash Balance (৳)"
                value={balanceForm.bkash_balance}
                onChange={(v) => setBalanceForm((p) => ({ ...p, bkash_balance: v }))}
                color="#E2136E"
              />
              <BalanceInput
                label="Nagad Balance (৳)"
                value={balanceForm.nagad_balance}
                onChange={(v) => setBalanceForm((p) => ({ ...p, nagad_balance: v }))}
                color="#F04923"
              />
              <BalanceInput
                label="Rocket Balance (৳)"
                value={balanceForm.rocket_balance}
                onChange={(v) => setBalanceForm((p) => ({ ...p, rocket_balance: v }))}
                color="#8C3494"
              />
            </div>

            {/* Total */}
            <div className="mt-4 pt-3 border-t border-border-light flex items-center justify-between">
              <span className="text-xs font-medium text-muted-custom">Total</span>
              <span className="text-sm font-bold text-heading">
                ৳{formatNumber(
                  (parseFloat(balanceForm.physical_cash) || 0) +
                  (parseFloat(balanceForm.bkash_balance) || 0) +
                  (parseFloat(balanceForm.nagad_balance) || 0) +
                  (parseFloat(balanceForm.rocket_balance) || 0)
                )}
              </span>
            </div>

            <div className="flex gap-2 mt-5">
              <button
                onClick={() => setShowBalanceModal(false)}
                className="flex-1 px-3 py-2.5 bg-surface-elevated border border-border-light text-muted-custom rounded-lg text-xs font-medium hover:text-heading transition-all cursor-pointer"
              >
                Cancel
              </button>
              <button
                onClick={handleSaveBalance}
                disabled={savingBalance}
                className="flex-1 px-3 py-2.5 bg-primary text-white rounded-lg text-xs font-semibold hover:bg-primary-light transition-all cursor-pointer disabled:opacity-50 flex items-center justify-center gap-1.5"
              >
                {savingBalance ? (
                  <RefreshCw size={13} className="animate-spin" />
                ) : (
                  <Save size={13} />
                )}
                Save Balances
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

function BalanceInput({ label, value, onChange, color }) {
  return (
    <div>
      <label className="flex items-center gap-2 text-xs font-medium text-muted-custom mb-1.5">
        <div className="w-2.5 h-2.5 rounded-full" style={{ backgroundColor: color }} />
        {label}
      </label>
      <input
        type="number"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder="0"
        min="0"
        className="w-full bg-surface-elevated border border-border-light text-heading rounded-lg px-3 py-2.5 text-sm font-mono focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary/30 transition-all"
      />
    </div>
  );
}

function StatCard({ icon: Icon, label, value, sub, color }) {
  const colorClasses = {
    primary: "text-primary bg-primary/10",
    warning: "text-warning-custom bg-warning-custom/10",
    error: "text-error-custom bg-error-custom/10",
  };

  return (
    <div className="bg-surface border border-border-custom rounded-xl p-4">
      <div className="flex items-center gap-3">
        <div className={`w-9 h-9 rounded-lg flex items-center justify-center ${colorClasses[color]}`}>
          <Icon size={18} />
        </div>
        <div>
          <p className="text-[11px] text-muted-custom font-medium">{label}</p>
          <p className="text-lg font-bold text-heading">{value}</p>
          <p className="text-[10px] text-muted-custom">{sub}</p>
        </div>
      </div>
    </div>
  );
}

function formatNumber(num) {
  if (num >= 100000) return (num / 100000).toFixed(1) + "L";
  if (num >= 1000) return (num / 1000).toFixed(1) + "K";
  return num?.toFixed(0) || "0";
}
