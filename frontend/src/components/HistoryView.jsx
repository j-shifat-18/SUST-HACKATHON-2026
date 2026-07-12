"use client";

import React, { useState, useEffect } from "react";
import {
  ArrowDownLeft,
  ArrowUpRight,
  Search,
  Clock,
  Filter,
  RefreshCw,
} from "lucide-react";
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from "recharts";
import { useDashboard } from "../context/DashboardContext";

const PROVIDER_COLORS = {
  bkash: "#E2136E",
  nagad: "#F04923",
  rocket: "#8C3494",
  physical: "#2CD4BF",
};

export default function HistoryView() {
  const { fetchWithAuth } = useDashboard();
  const [transactions, setTransactions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState("all");
  const [searchTerm, setSearchTerm] = useState("");

  useEffect(() => {
    loadTransactions();
  }, []);

  const loadTransactions = async () => {
    setLoading(true);
    try {
      const data = await fetchWithAuth("/api/v1/transactions?limit=50");
      setTransactions(data || []);
    } catch (err) {
      console.error("Failed to load transactions:", err);
    }
    setLoading(false);
  };

  const filteredTransactions = transactions.filter((tx) => {
    if (filter !== "all" && tx.provider !== filter) return false;
    if (searchTerm && !tx.account_ref.includes(searchTerm) && !tx.id.includes(searchTerm)) return false;
    return true;
  });

  // Build hourly flow data from real transactions
  const hourlyFlow = buildHourlyFlow(transactions);

  return (
    <div className="space-y-5">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-heading">Transaction History</h1>
          <p className="text-sm text-muted-custom mt-0.5">Real-time transaction monitoring</p>
        </div>
        <button
          onClick={loadTransactions}
          className="flex items-center gap-1.5 px-3 py-1.5 bg-surface-elevated border border-border-light rounded-lg text-xs text-muted-custom hover:text-heading transition-all cursor-pointer"
        >
          <RefreshCw size={13} className={loading ? "animate-spin" : ""} />
          Refresh
        </button>
      </div>

      {/* Flow Chart */}
      {hourlyFlow.length > 0 && (
        <div className="bg-surface border border-border-custom rounded-xl p-5">
          <h3 className="text-sm font-semibold text-heading mb-4">Hourly Cash Flow (Last 12h)</h3>
          <ResponsiveContainer width="100%" height={200}>
            <AreaChart data={hourlyFlow}>
              <CartesianGrid strokeDasharray="3 3" stroke="#1F2937" />
              <XAxis dataKey="hour" tick={{ fill: "#6B7280", fontSize: 10 }} />
              <YAxis tick={{ fill: "#6B7280", fontSize: 10 }} tickFormatter={(v) => `${(v / 1000).toFixed(0)}k`} />
              <Tooltip
                contentStyle={{
                  backgroundColor: "#1F2937",
                  border: "1px solid #374151",
                  borderRadius: "8px",
                  color: "#F9FAFB",
                  fontSize: "11px",
                }}
                formatter={(value) => [`৳${value.toLocaleString()}`, ""]}
              />
              <Area
                type="monotone"
                dataKey="cash_in"
                stroke="#2CD4BF"
                fill="#2CD4BF"
                fillOpacity={0.2}
                name="Cash In"
              />
              <Area
                type="monotone"
                dataKey="cash_out"
                stroke="#EF4444"
                fill="#EF4444"
                fillOpacity={0.15}
                name="Cash Out"
              />
            </AreaChart>
          </ResponsiveContainer>
          <div className="flex justify-center gap-4 mt-2">
            <div className="flex items-center gap-1.5">
              <div className="w-2.5 h-2.5 rounded-full bg-primary" />
              <span className="text-[10px] text-muted-custom">Cash In</span>
            </div>
            <div className="flex items-center gap-1.5">
              <div className="w-2.5 h-2.5 rounded-full bg-error-custom" />
              <span className="text-[10px] text-muted-custom">Cash Out</span>
            </div>
          </div>
        </div>
      )}

      {/* Filters */}
      <div className="flex items-center gap-3 flex-wrap">
        <div className="relative flex-1 max-w-xs">
          <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-muted-custom" />
          <input
            type="text"
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            placeholder="Search by ID or account..."
            className="w-full bg-surface-elevated border border-border-light text-heading rounded-lg pl-9 pr-3 py-2 text-xs focus:outline-none focus:border-primary transition-all"
          />
        </div>
        <div className="flex items-center gap-1.5">
          <Filter size={13} className="text-muted-custom" />
          {["all", "bkash", "nagad", "rocket", "physical"].map((p) => (
            <button
              key={p}
              onClick={() => setFilter(p)}
              className={`px-2.5 py-1 rounded-full text-[10px] font-medium transition-all cursor-pointer capitalize ${
                filter === p
                  ? "bg-primary/15 text-primary border border-primary/30"
                  : "bg-surface-elevated text-muted-custom hover:text-heading border border-border-light"
              }`}
            >
              {p}
            </button>
          ))}
        </div>
      </div>

      {/* Transaction List */}
      {loading ? (
        <div className="bg-surface border border-border-custom rounded-xl p-10 text-center">
          <RefreshCw size={24} className="text-primary mx-auto mb-2 animate-spin" />
          <p className="text-sm text-muted-custom">Loading transactions...</p>
        </div>
      ) : (
        <div className="bg-surface border border-border-custom rounded-xl overflow-hidden">
          <div className="grid grid-cols-[1fr_80px_90px_100px_100px_140px] gap-2 px-4 py-2.5 border-b border-border-custom text-[10px] font-semibold text-muted-custom uppercase tracking-wider">
            <span>Transaction</span>
            <span>Provider</span>
            <span>Type</span>
            <span>Amount</span>
            <span>Account</span>
            <span>Time</span>
          </div>
          <div className="divide-y divide-border-custom">
            {filteredTransactions.length === 0 ? (
              <div className="p-6 text-center text-sm text-muted-custom">No transactions found</div>
            ) : (
              filteredTransactions.map((tx) => (
                <div key={tx.id} className="grid grid-cols-[1fr_80px_90px_100px_100px_140px] gap-2 px-4 py-3 items-center hover:bg-surface-elevated/50 transition-colors">
                  <span className="text-xs font-mono text-heading truncate">{tx.id.slice(0, 12)}...</span>
                  <span>
                    <span
                      className="inline-block px-1.5 py-0.5 rounded text-[9px] font-bold text-white"
                      style={{ backgroundColor: PROVIDER_COLORS[tx.provider] || "#6B7280" }}
                    >
                      {tx.provider}
                    </span>
                  </span>
                  <span className="flex items-center gap-1 text-xs">
                    {tx.transaction_type.includes("in") ? (
                      <ArrowDownLeft size={11} className="text-primary" />
                    ) : (
                      <ArrowUpRight size={11} className="text-error-custom" />
                    )}
                    <span className="text-muted-custom capitalize text-[10px]">{tx.transaction_type.replace(/_/g, " ")}</span>
                  </span>
                  <span className="text-xs font-semibold text-heading">৳{tx.amount.toLocaleString()}</span>
                  <span className="text-xs font-mono text-muted-custom">{tx.account_ref}</span>
                  <span className="text-[10px] text-muted-custom flex items-center gap-1">
                    <Clock size={9} />
                    {formatTime(tx.timestamp)}
                  </span>
                </div>
              ))
            )}
          </div>
        </div>
      )}
    </div>
  );
}

function formatTime(isoString) {
  const d = new Date(isoString);
  return d.toLocaleString("en-GB", {
    day: "2-digit",
    month: "short",
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  });
}

function buildHourlyFlow(transactions) {
  if (!transactions.length) return [];

  const now = new Date();
  const buckets = [];

  for (let i = 11; i >= 0; i--) {
    const hourStart = new Date(now);
    hourStart.setHours(now.getHours() - i, 0, 0, 0);
    const hourEnd = new Date(hourStart);
    hourEnd.setHours(hourStart.getHours() + 1);

    let cash_in = 0;
    let cash_out = 0;

    for (const tx of transactions) {
      const txTime = new Date(tx.timestamp);
      if (txTime >= hourStart && txTime < hourEnd) {
        if (tx.transaction_type === "cash_in") {
          cash_in += tx.amount;
        } else if (tx.transaction_type === "cash_out") {
          cash_out += tx.amount;
        }
      }
    }

    buckets.push({
      hour: hourStart.toLocaleTimeString("en-GB", { hour: "2-digit", minute: "2-digit" }),
      cash_in,
      cash_out,
    });
  }

  return buckets;
}
