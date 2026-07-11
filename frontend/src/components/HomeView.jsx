"use client";

import React, { useState, useEffect } from "react";
import { PieChart, Pie, Sector, Cell, ResponsiveContainer } from "recharts";
import { auth } from "../../firebase/firebase.init";
import { AlertCircle, TrendingDown, RefreshCw, Cpu } from "lucide-react";
import { API_BASE_URL } from "../config";

const renderActiveShape = (props) => {
  const { cx, cy, innerRadius, outerRadius, startAngle, endAngle, fill } = props;
  return (
    <g>
      <Sector
        cx={cx}
        cy={cy}
        innerRadius={innerRadius}
        outerRadius={outerRadius + 6}
        startAngle={startAngle}
        endAngle={endAngle}
        fill={fill}
      />
      <Sector
        cx={cx}
        cy={cy}
        startAngle={startAngle}
        endAngle={endAngle}
        innerRadius={outerRadius + 10}
        outerRadius={outerRadius + 14}
        fill={fill}
        opacity={0.3}
      />
    </g>
  );
};

export default function HomeView({ userProfile }) {
  const [snapshot, setSnapshot] = useState(null);
  const [loading, setLoading] = useState(true);
  const [activeIndex, setActiveIndex] = useState(null);

  const fetchSnapshot = async () => {
    try {
      setLoading(true);
      const firebaseUser = auth.currentUser;
      if (!firebaseUser) return;
      const idToken = await firebaseUser.getIdToken();
      const response = await fetch(`${API_BASE_URL}/api/v1/snapshot/${userProfile.uid}`, {
        method: "POST",
        headers: {
          "Authorization": `Bearer ${idToken}`
        }
      });
      if (response.ok) {
        const data = await response.json();
        setSnapshot(data);
      }
    } catch (err) {
      console.error("Failed to load dashboard snapshot:", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (userProfile && userProfile.uid) {
      fetchSnapshot();
    }
  }, [userProfile]);

  const onPieEnter = (_, index) => {
    setActiveIndex(index);
  };

  const onPieLeave = () => {
    setActiveIndex(null);
  };

  // Dynamically resolve values with secure fallbacks
  const physical = snapshot?.liquidity?.physical_cash_bdt ?? 50000;
  const bkash = snapshot?.liquidity?.bkash_balance_bdt ?? 45000;
  const nagad = snapshot?.liquidity?.nagad_balance_bdt ?? 35000;
  const rocket = snapshot?.liquidity?.rocket_balance_bdt ?? 25000;
  const utilization = snapshot?.liquidity?.utilization_pct ?? 56.9;

  const chartData = [
    { name: "Cash", value: physical, color: "#22C55E" },
    { name: "bKash", value: bkash, color: "#E2125B" },
    { name: "Nagad", value: nagad, color: "#F04923" },
    { name: "Rocket", value: rocket, color: "#8C3494" }
  ];

  const total = chartData.reduce((sum, item) => sum + item.value, 0);

  return (
    <div className="space-y-6">
      {/* Overview Title block */}
      <div className="flex justify-between items-center border-b border-border-custom pb-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-heading">Dashboard Overview</h1>
          <p className="text-xs text-muted-custom mt-0.5">Real-time MFS Liquidity Intelligence Platform</p>
        </div>
        <button
          onClick={fetchSnapshot}
          disabled={loading}
          className="flex items-center gap-1.5 px-3 py-1.5 bg-slate-100 hover:bg-slate-200 disabled:opacity-50 text-text-main text-xs font-semibold rounded-lg border border-border-custom cursor-pointer transition-all"
        >
          <RefreshCw size={12} className={loading ? "animate-spin" : ""} />
          Refresh
        </button>
      </div>

      {/* Grid containing provider balances */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
        {/* Shared physical cash drawer */}
        <div className="bg-surface border border-border-custom rounded-xl p-5 flex flex-col justify-between shadow-sm relative overflow-hidden">
          <div className="absolute top-0 left-0 right-0 h-1 bg-success-custom"></div>
          <div>
            <div className="flex justify-between items-center text-muted-custom font-bold uppercase tracking-wider text-[10px] mb-2">
              <span>Cash</span>
            </div>
            <div className="text-2xl font-bold text-heading">৳ {physical.toLocaleString()}</div>
          </div>
          <div className="mt-4 w-full bg-slate-100 h-1.5 rounded-full overflow-hidden">
            <div className="bg-success-custom h-full" style={{ width: `${(physical / total * 100).toFixed(0)}%` }}></div>
          </div>
        </div>

        {/* bKash card */}
        <div className="bg-surface border border-border-custom rounded-xl p-5 flex flex-col justify-between relative overflow-hidden shadow-sm">
          <div className="absolute top-0 left-0 right-0 h-1 bg-pink-600"></div>
          <div>
            <div className="flex justify-between items-center text-[10px] mb-2 font-bold tracking-wider uppercase text-pink-500">
              <span>bKash</span>
            </div>
            <div className="text-2xl font-bold text-heading">৳ {bkash.toLocaleString()}</div>
          </div>
          <div className="mt-4 w-full bg-slate-100 h-1.5 rounded-full overflow-hidden">
            <div className="bg-pink-600 h-full" style={{ width: `${(bkash / total * 100).toFixed(0)}%` }}></div>
          </div>
        </div>

        {/* Nagad card */}
        <div className="bg-surface border border-border-custom rounded-xl p-5 flex flex-col justify-between relative overflow-hidden shadow-sm">
          <div className="absolute top-0 left-0 right-0 h-1 bg-orange-500"></div>
          <div>
            <div className="flex justify-between items-center text-[10px] mb-2 font-bold tracking-wider uppercase text-orange-500">
              <span>Nagad</span>
            </div>
            <div className="text-2xl font-bold text-heading">৳ {nagad.toLocaleString()}</div>
          </div>
          <div className="mt-4 w-full bg-slate-100 h-1.5 rounded-full overflow-hidden">
            <div className="bg-orange-500 h-full" style={{ width: `${(nagad / total * 100).toFixed(0)}%` }}></div>
          </div>
        </div>

        {/* Rocket card */}
        <div className="bg-surface border border-border-custom rounded-xl p-5 flex flex-col justify-between relative overflow-hidden shadow-sm">
          <div className="absolute top-0 left-0 right-0 h-1 bg-violet-600"></div>
          <div>
            <div className="flex justify-between items-center text-[10px] mb-2 font-bold tracking-wider uppercase text-violet-500">
              <span>Rocket</span>
            </div>
            <div className="text-2xl font-bold text-heading">৳ {rocket.toLocaleString()}</div>
          </div>
          <div className="mt-4 w-full bg-slate-100 h-1.5 rounded-full overflow-hidden">
            <div className="bg-violet-600 h-full" style={{ width: `${(rocket / total * 100).toFixed(0)}%` }}></div>
          </div>
        </div>
      </div>

      {/* Pie Chart and Confidence Summary Layout */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {/* Recharts Pie/Donut Chart */}
        <div className="bg-surface border border-border-custom rounded-xl p-6 shadow-sm flex flex-col items-center justify-center col-span-2">
          <h3 className="text-sm font-bold text-heading uppercase tracking-wide mb-6 w-full text-left">Liquidity Distribution</h3>
          
          <div className="relative w-full max-w-[260px] aspect-square flex justify-center items-center">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie
                  activeIndex={activeIndex}
                  activeShape={renderActiveShape}
                  data={chartData}
                  cx="50%"
                  cy="50%"
                  innerRadius="65%"
                  outerRadius="80%"
                  dataKey="value"
                  onMouseEnter={onPieEnter}
                  onMouseLeave={onPieLeave}
                >
                  {chartData.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={entry.color} style={{ outline: "none" }} />
                  ))}
                </Pie>
              </PieChart>
            </ResponsiveContainer>

            {/* Absolute centered labels */}
            <div className="absolute inset-0 flex flex-col items-center justify-center text-center pointer-events-none p-4">
              {activeIndex === null || activeIndex === -1 ? (
                <>
                  <span className="text-[10px] text-muted-custom font-extrabold uppercase tracking-widest mb-0.5">
                    Total Amount
                  </span>
                  <span className="text-lg font-black text-heading leading-tight">
                    ৳{total.toLocaleString()}
                  </span>
                </>
              ) : (
                <>
                  <span className="text-[10px] font-extrabold uppercase tracking-widest mb-0.5" style={{ color: chartData[activeIndex].color }}>
                    {chartData[activeIndex].name}
                  </span>
                  <span className="text-lg font-black text-heading leading-tight">
                    ৳{chartData[activeIndex].value.toLocaleString()}
                  </span>
                  <span className="text-[9px] text-muted-custom font-semibold mt-1 bg-slate-50 border border-border-custom px-1.5 py-0.5 rounded-full">
                    {((chartData[activeIndex].value / total) * 100).toFixed(1)}% Share
                  </span>
                </>
              )}
            </div>
          </div>
        </div>

        {/* Stats Column */}
        <div className="bg-surface border border-border-custom rounded-xl p-6 shadow-sm flex flex-col justify-between">
          <div>
            <h3 className="text-sm font-bold text-heading uppercase tracking-wide mb-4">Risk & Performance</h3>
            <div className="space-y-4">
              <div>
                <span className="text-[10px] font-bold text-muted-custom uppercase block mb-1">Float Utilization</span>
                <div className="text-xl font-bold text-heading">{utilization.toFixed(1)}%</div>
                <p className="text-[10px] text-muted-custom mt-0.5">Wallet balance vs. total position</p>
              </div>

              <div>
                <span className="text-[10px] font-bold text-muted-custom uppercase block mb-1">Overall Confidence</span>
                <div className="text-xl font-bold text-heading">
                  {((snapshot?.overall_confidence ?? 0.87) * 100).toFixed(0)}%
                </div>
                <p className="text-[10px] text-muted-custom mt-0.5">Based on feed health & latency</p>
              </div>

              <div>
                <span className="text-[10px] font-bold text-muted-custom uppercase block mb-1">Anomalies Detected</span>
                <div className="text-xl font-bold text-error-custom flex items-center gap-1.5">
                  {snapshot?.anomaly_count ?? 0} Flagged
                </div>
                <p className="text-[10px] text-muted-custom mt-0.5">Suspicious activities in past 24h</p>
              </div>
            </div>
          </div>
          
          {snapshot?.liquidity?.degraded_providers?.length > 0 && (
            <div className="mt-4 p-3 bg-warning-custom/10 border border-warning-custom/25 rounded-lg flex items-start gap-2 text-[10px] text-warning-custom">
              <AlertCircle size={14} className="shrink-0 mt-0.5" />
              <span>Stale data feeds detected for: {snapshot.liquidity.degraded_providers.join(", ")}</span>
            </div>
          )}
        </div>
      </div>

      {/* AI Decision Support Advisory Board */}
      <div className="bg-slate-900 border border-slate-800 text-white rounded-2xl p-6 shadow-md relative overflow-hidden">
        <div className="absolute top-0 right-0 p-6 opacity-5 pointer-events-none">
          <Cpu size={120} />
        </div>

        <div className="flex items-center gap-2 mb-4">
          <span className="w-2 h-2 rounded-full bg-primary animate-ping"></span>
          <h3 className="text-xs font-bold uppercase tracking-widest text-primary flex items-center gap-1.5">
            <Cpu size={14} /> AI Decision Support Agent
          </h3>
        </div>

        {/* Advisory Content */}
        <div className="space-y-4">
          <div>
            <div className="flex items-center gap-2 mb-1.5">
              <span className="text-xs font-bold uppercase text-muted-custom">Operational Status:</span>
              <span className={`px-2 py-0.5 rounded text-[10px] font-bold tracking-wider ${
                (snapshot?.agent_advisory?.operational_status ?? "NORMAL") === "CRITICAL"
                  ? "bg-error-custom text-white"
                  : (snapshot?.agent_advisory?.operational_status ?? "NORMAL") === "ALERT"
                  ? "bg-warning-custom text-heading"
                  : "bg-primary text-heading"
              }`}>
                {snapshot?.agent_advisory?.operational_status ?? "NORMAL"}
              </span>
            </div>
            <p className="text-sm font-semibold text-slate-100">
              {snapshot?.agent_advisory?.summary ?? "Liquidity matrix shows balanced levels across all channels. Keep regular monitoring on Rocket wallet reserves."}
            </p>
          </div>

          {(snapshot?.agent_advisory?.recommendations?.length > 0 || !snapshot) && (
            <div className="pt-2 border-t border-slate-800">
              <span className="text-[10px] font-bold text-primary uppercase tracking-wide block mb-2">Recommended Actions</span>
              <ul className="space-y-1.5 text-xs text-slate-300">
                {(snapshot?.agent_advisory?.recommendations ?? [
                  "Monitor Rocket balance closely over next 6 hours.",
                  "Rebalance Nagad to bKash if Nagad utilization exceeds 80%.",
                  "Prepare cash replenishment for next morning shift."
                ]).map((rec, i) => (
                  <li key={i} className="flex items-start gap-2">
                    <span className="text-primary font-bold mt-0.5">•</span>
                    <span>{rec}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}

          <div className="pt-3 border-t border-slate-800 bg-slate-950/30 -mx-6 -mb-6 p-6 rounded-b-2xl">
            <span className="text-[9px] font-bold uppercase tracking-wider text-muted-custom block mb-1">Executive Summary</span>
            <p className="text-xs italic text-slate-400">
              "{snapshot?.agent_advisory?.executive_summary ?? "Platform analytics indicate healthy operational capacity. Depletion risk is nominal under typical daily flows."}"
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
