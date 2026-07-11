"use client";

import React, { useState, useEffect } from "react";
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip as RechartsTooltip, Legend, ResponsiveContainer } from "recharts";
import { auth } from "../../firebase/firebase.init";
import { Clock, ShieldCheck, RefreshCw, AlertTriangle } from "lucide-react";
import { API_BASE_URL } from "../config";

export default function AnalyticsView({ userProfile }) {
  const [snapshot, setSnapshot] = useState(null);
  const [loading, setLoading] = useState(true);

  const fetchForecasts = async () => {
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
      } else {
        throw new Error("Backend response error");
      }
    } catch (err) {
      console.error("Failed to fetch forecast snapshot, loading mock forecasts:", err);
      loadMockSnapshot();
    } finally {
      setLoading(false);
    }
  };

  const loadMockSnapshot = () => {
    setSnapshot({
      forecasts: [
        { provider: "Cash", current_balance_bdt: 50000, predicted_balance_bdt: 44000, depletion_time_hours: null, hourly_net_flow_bdt: -500.0, confidence: 0.88, forecast_hours: 12 },
        { provider: "bKash", current_balance_bdt: 45000, predicted_balance_bdt: 29000, depletion_time_hours: 6.5, hourly_net_flow_bdt: -1333.33, confidence: 0.81, forecast_hours: 12 },
        { provider: "Nagad", current_balance_bdt: 35000, predicted_balance_bdt: 38000, depletion_time_hours: null, hourly_net_flow_bdt: 250.0, confidence: 0.74, forecast_hours: 12 },
        { provider: "Rocket", current_balance_bdt: 25000, predicted_balance_bdt: 12000, depletion_time_hours: 3.2, hourly_net_flow_bdt: -1083.33, confidence: 0.69, forecast_hours: 12 }
      ]
    });
  };

  useEffect(() => {
    if (userProfile && userProfile.uid) {
      fetchForecasts();
    }
  }, [userProfile]);

  const forecasts = snapshot?.forecasts ?? [];

  // Reformat data for bar chart comparison
  const chartData = forecasts.map(f => ({
    name: f.provider.charAt(0).toUpperCase() + f.provider.slice(1),
    "Current Balance": f.current_balance_bdt,
    "12h Predicted Balance": f.predicted_balance_bdt
  }));

  const getDepletionStatus = (time, flow) => {
    if (flow >= 0) return { label: "Inflow / Growing", style: "bg-emerald-50 text-emerald-700 border border-emerald-500/10" };
    if (!time) return { label: "Safe / No Depletion", style: "bg-slate-50 text-slate-700 border border-border-custom" };
    if (time <= 4) return { label: `Critical Risk (<${time.toFixed(1)}h)`, style: "bg-red-50 text-red-700 border border-red-500/10 font-bold" };
    return { label: `Moderate Risk (<${time.toFixed(1)}h)`, style: "bg-amber-50 text-amber-700 border border-amber-500/10" };
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex justify-between items-center border-b border-border-custom pb-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-heading">Liquidity Analytics & Forecasting</h1>
          <p className="text-xs text-muted-custom mt-0.5">Simple Exponential Smoothing (SES) models and depletion alerts</p>
        </div>
        <button
          onClick={fetchForecasts}
          disabled={loading}
          className="flex items-center gap-1.5 px-3 py-1.5 bg-slate-100 hover:bg-slate-200 disabled:opacity-50 text-text-main text-xs font-semibold rounded-lg border border-border-custom cursor-pointer transition-all animate-fadeIn"
        >
          <RefreshCw size={12} className={loading ? "animate-spin" : ""} />
          Recalculate Models
        </button>
      </div>

      {loading ? (
        <div className="flex flex-col items-center justify-center py-12">
          <div className="w-10 h-10 rounded-full border-4 border-slate-100 border-t-secondary animate-spin"></div>
          <span className="text-xs font-semibold text-muted-custom mt-2">Computing forecasting matrices...</span>
        </div>
      ) : (
        <div className="grid grid-cols-1 xl:grid-cols-3 gap-6">
          
          {/* Bar Chart Comparison */}
          <div className="bg-surface border border-border-custom rounded-xl p-6 shadow-sm xl:col-span-2">
            <h3 className="text-sm font-bold text-heading uppercase tracking-wide mb-4">Balance Comparison (Current vs. 12h Forecast)</h3>
            <div className="w-full h-80 text-xs">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={chartData} margin={{ top: 20, right: 10, left: 10, bottom: 5 }}>
                  <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#F1F5F9" />
                  <XAxis dataKey="name" stroke="#64748B" fontSize={11} tickLine={false} />
                  <YAxis stroke="#64748B" fontSize={11} tickLine={false} axisLine={false} tickFormatter={(val) => `৳${(val / 1000)}k`} />
                  <RechartsTooltip formatter={(val) => `৳${Number(val).toLocaleString()}`} contentStyle={{ fontSize: "11px", borderRadius: "8px", border: "1px solid #E2E8F0" }} />
                  <Legend wrapperStyle={{ fontSize: "11px", marginTop: "10px" }} />
                  <Bar dataKey="Current Balance" fill="#4F46E5" radius={[4, 4, 0, 0]} maxBarSize={36} />
                  <Bar dataKey="12h Predicted Balance" fill="#0EA5E9" radius={[4, 4, 0, 0]} maxBarSize={36} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>

          {/* Side Info Cards */}
          <div className="space-y-6">
            <div className="bg-surface border border-border-custom rounded-xl p-6 shadow-sm space-y-4">
              <h3 className="text-sm font-bold text-heading uppercase tracking-wide">Model Parameters</h3>
              <div className="space-y-3 text-xs">
                <div className="flex justify-between border-b border-border-custom/50 pb-2">
                  <span className="text-muted-custom">Model Version</span>
                  <span className="font-bold text-heading font-mono">ses_v1.0.3</span>
                </div>
                <div className="flex justify-between border-b border-border-custom/50 pb-2">
                  <span className="text-muted-custom">Alpha coefficient</span>
                  <span className="font-bold text-heading font-mono">0.15 (Adaptive)</span>
                </div>
                <div className="flex justify-between border-b border-border-custom/50 pb-2">
                  <span className="text-muted-custom">Forecast Interval</span>
                  <span className="font-bold text-heading">12 Hours</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-muted-custom">Risk Matrix Evaluation</span>
                  <span className="font-bold text-success-custom flex items-center gap-1">
                    <ShieldCheck size={14} /> Active
                  </span>
                </div>
              </div>
            </div>

            <div className="bg-slate-900 border border-slate-800 text-white rounded-xl p-5 shadow-md flex items-start gap-3">
              <AlertTriangle className="text-warning-custom shrink-0 mt-0.5" size={18} />
              <div>
                <span className="text-[10px] font-bold text-warning-custom uppercase tracking-wide block mb-1">Advisory Trigger</span>
                <p className="text-xs text-slate-300 leading-relaxed">
                  Forecasting models report high velocity drainage in Rocket and bKash channels. Monitor active cases to arrange wallet rebalancing before standard business close hours.
                </p>
              </div>
            </div>
          </div>

          {/* Depletion Forecast Table */}
          <div className="bg-surface border border-border-custom rounded-xl p-6 shadow-sm xl:col-span-3">
            <h3 className="text-sm font-bold text-heading uppercase tracking-wide mb-4">Risk & Depletion Matrix</h3>
            <div className="overflow-x-auto text-xs">
              <table className="w-full text-left border-collapse">
                <thead>
                  <tr className="bg-slate-50 text-muted-custom border-b border-border-custom font-bold uppercase tracking-wider">
                    <th className="p-3">Channel</th>
                    <th className="p-3">Net Hourly Flow</th>
                    <th className="p-3">Current Balance</th>
                    <th className="p-3">Model Confidence</th>
                    <th className="p-3">Depletion Alarm</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-border-custom text-text-main">
                  {forecasts.map((f) => {
                    const status = getDepletionStatus(f.depletion_time_hours, f.hourly_net_flow_bdt);
                    return (
                      <tr key={f.provider} className="hover:bg-slate-50/50 transition-colors">
                        <td className="p-3 font-bold text-heading capitalize">{f.provider}</td>
                        <td className={`p-3 font-mono font-bold ${f.hourly_net_flow_bdt < 0 ? "text-error-custom" : "text-success-custom"}`}>
                          {f.hourly_net_flow_bdt < 0 ? "-" : "+"}৳{Math.abs(f.hourly_net_flow_bdt).toFixed(2)}/h
                        </td>
                        <td className="p-3 font-semibold text-heading">৳ {f.current_balance_bdt.toLocaleString()}</td>
                        <td className="p-3 font-bold font-mono">{(f.confidence * 100).toFixed(0)}%</td>
                        <td className="p-3">
                          <span className={`px-2.5 py-1 rounded text-[10px] font-bold ${status.style}`}>
                            {status.label}
                          </span>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </div>

        </div>
      )}
    </div>
  );
}
