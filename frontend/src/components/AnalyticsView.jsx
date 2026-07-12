"use client";

import React from "react";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  LineChart,
  Line,
  PieChart,
  Pie,
  Cell,
  RadialBarChart,
  RadialBar,
  Legend,
} from "recharts";
import { TrendingUp, Clock, Shield, Zap, Target, Activity } from "lucide-react";

// Mock analytics data
const DAILY_VOLUME = [
  { day: "Mon", bkash: 320000, nagad: 180000, rocket: 95000 },
  { day: "Tue", bkash: 280000, nagad: 220000, rocket: 110000 },
  { day: "Wed", bkash: 350000, nagad: 190000, rocket: 85000 },
  { day: "Thu", bkash: 410000, nagad: 250000, rocket: 120000 },
  { day: "Fri", bkash: 520000, nagad: 340000, rocket: 180000 },
  { day: "Sat", bkash: 380000, nagad: 210000, rocket: 105000 },
  { day: "Sun", bkash: 290000, nagad: 170000, rocket: 78000 },
];

const ALERT_TREND = [
  { day: "Jul 5", alerts: 3, resolved: 2 },
  { day: "Jul 6", alerts: 5, resolved: 4 },
  { day: "Jul 7", alerts: 2, resolved: 3 },
  { day: "Jul 8", alerts: 7, resolved: 5 },
  { day: "Jul 9", alerts: 4, resolved: 4 },
  { day: "Jul 10", alerts: 6, resolved: 5 },
  { day: "Jul 11", alerts: 3, resolved: 2 },
];

const ANOMALY_DISTRIBUTION = [
  { name: "Velocity Spike", value: 45, fill: "#F59E0B" },
  { name: "Tx Splitting", value: 30, fill: "#EF4444" },
  { name: "Circular Flow", value: 25, fill: "#8C3494" },
];

const CONFIDENCE_DATA = [
  { name: "bKash", confidence: 92, fill: "#E2136E" },
  { name: "Nagad", confidence: 88, fill: "#F04923" },
  { name: "Rocket", confidence: 75, fill: "#8C3494" },
  { name: "Physical", confidence: 95, fill: "#2CD4BF" },
];

const KPI_METRICS = [
  { label: "Avg Lead Time", value: "35 min", icon: Clock, desc: "Alert → Resolution", trend: "-12%" },
  { label: "Detection Precision", value: "92%", icon: Target, desc: "Anomaly accuracy", trend: "+3%" },
  { label: "False Positive Rate", value: "4.5%", icon: Shield, desc: "Below 5% threshold", trend: "-1.2%" },
  { label: "Pipeline Latency", value: "1.2s", icon: Zap, desc: "End-to-end P95", trend: "-200ms" },
];

export default function AnalyticsView() {
  return (
    <div className="space-y-5">
      <div>
        <h1 className="text-xl font-bold text-heading">Analytics</h1>
        <p className="text-sm text-muted-custom mt-0.5">Performance metrics and operational insights</p>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        {KPI_METRICS.map((kpi) => {
          const Icon = kpi.icon;
          return (
            <div key={kpi.label} className="bg-surface border border-border-custom rounded-xl p-4">
              <div className="flex items-center justify-between mb-2">
                <div className="w-8 h-8 rounded-lg bg-primary/10 flex items-center justify-center">
                  <Icon size={16} className="text-primary" />
                </div>
                <span className="text-[10px] font-medium text-primary bg-primary/10 px-1.5 py-0.5 rounded">
                  {kpi.trend}
                </span>
              </div>
              <p className="text-xl font-bold text-heading">{kpi.value}</p>
              <p className="text-[10px] text-muted-custom">{kpi.label}</p>
              <p className="text-[9px] text-muted-custom mt-0.5">{kpi.desc}</p>
            </div>
          );
        })}
      </div>

      {/* Charts Row 1 */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {/* Daily Volume */}
        <div className="bg-surface border border-border-custom rounded-xl p-5">
          <h3 className="text-sm font-semibold text-heading mb-4 flex items-center gap-2">
            <TrendingUp size={14} className="text-primary" />
            Weekly Transaction Volume (BDT)
          </h3>
          <ResponsiveContainer width="100%" height={220}>
            <BarChart data={DAILY_VOLUME} barGap={2}>
              <CartesianGrid strokeDasharray="3 3" stroke="#1F2937" />
              <XAxis dataKey="day" tick={{ fill: "#6B7280", fontSize: 10 }} />
              <YAxis tick={{ fill: "#6B7280", fontSize: 10 }} tickFormatter={(v) => `${(v / 1000).toFixed(0)}k`} />
              <Tooltip
                contentStyle={{
                  backgroundColor: "#1F2937",
                  border: "1px solid #374151",
                  borderRadius: "8px",
                  color: "#F9FAFB",
                  fontSize: "11px",
                }}
                formatter={(value) => [`৳${(value / 1000).toFixed(0)}k`, ""]}
              />
              <Bar dataKey="bkash" fill="#E2136E" radius={[3, 3, 0, 0]} name="bKash" />
              <Bar dataKey="nagad" fill="#F04923" radius={[3, 3, 0, 0]} name="Nagad" />
              <Bar dataKey="rocket" fill="#8C3494" radius={[3, 3, 0, 0]} name="Rocket" />
            </BarChart>
          </ResponsiveContainer>
          <div className="flex justify-center gap-4 mt-2">
            {[{ name: "bKash", color: "#E2136E" }, { name: "Nagad", color: "#F04923" }, { name: "Rocket", color: "#8C3494" }].map((p) => (
              <div key={p.name} className="flex items-center gap-1.5">
                <div className="w-2 h-2 rounded-full" style={{ backgroundColor: p.color }} />
                <span className="text-[10px] text-muted-custom">{p.name}</span>
              </div>
            ))}
          </div>
        </div>

        {/* Alert Trend */}
        <div className="bg-surface border border-border-custom rounded-xl p-5">
          <h3 className="text-sm font-semibold text-heading mb-4 flex items-center gap-2">
            <Activity size={14} className="text-primary" />
            Alert Trend (Last 7 Days)
          </h3>
          <ResponsiveContainer width="100%" height={220}>
            <LineChart data={ALERT_TREND}>
              <CartesianGrid strokeDasharray="3 3" stroke="#1F2937" />
              <XAxis dataKey="day" tick={{ fill: "#6B7280", fontSize: 10 }} />
              <YAxis tick={{ fill: "#6B7280", fontSize: 10 }} />
              <Tooltip
                contentStyle={{
                  backgroundColor: "#1F2937",
                  border: "1px solid #374151",
                  borderRadius: "8px",
                  color: "#F9FAFB",
                  fontSize: "11px",
                }}
              />
              <Line
                type="monotone"
                dataKey="alerts"
                stroke="#EF4444"
                strokeWidth={2}
                dot={{ fill: "#EF4444", r: 3 }}
                name="New Alerts"
              />
              <Line
                type="monotone"
                dataKey="resolved"
                stroke="#2CD4BF"
                strokeWidth={2}
                dot={{ fill: "#2CD4BF", r: 3 }}
                name="Resolved"
              />
            </LineChart>
          </ResponsiveContainer>
          <div className="flex justify-center gap-4 mt-2">
            <div className="flex items-center gap-1.5">
              <div className="w-2 h-2 rounded-full bg-error-custom" />
              <span className="text-[10px] text-muted-custom">New Alerts</span>
            </div>
            <div className="flex items-center gap-1.5">
              <div className="w-2 h-2 rounded-full bg-primary" />
              <span className="text-[10px] text-muted-custom">Resolved</span>
            </div>
          </div>
        </div>
      </div>

      {/* Charts Row 2 */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {/* Anomaly Distribution */}
        <div className="bg-surface border border-border-custom rounded-xl p-5">
          <h3 className="text-sm font-semibold text-heading mb-4">Anomaly Type Distribution</h3>
          <ResponsiveContainer width="100%" height={200}>
            <PieChart>
              <Pie
                data={ANOMALY_DISTRIBUTION}
                cx="50%"
                cy="50%"
                innerRadius={50}
                outerRadius={75}
                paddingAngle={4}
                dataKey="value"
              >
                {ANOMALY_DISTRIBUTION.map((entry, index) => (
                  <Cell key={index} fill={entry.fill} />
                ))}
              </Pie>
              <Tooltip
                contentStyle={{
                  backgroundColor: "#1F2937",
                  border: "1px solid #374151",
                  borderRadius: "8px",
                  color: "#F9FAFB",
                  fontSize: "11px",
                }}
                formatter={(value) => [`${value}%`, ""]}
              />
            </PieChart>
          </ResponsiveContainer>
          <div className="flex flex-wrap justify-center gap-3 mt-1">
            {ANOMALY_DISTRIBUTION.map((item) => (
              <div key={item.name} className="flex items-center gap-1.5">
                <div className="w-2.5 h-2.5 rounded-full" style={{ backgroundColor: item.fill }} />
                <span className="text-[10px] text-muted-custom">{item.name} ({item.value}%)</span>
              </div>
            ))}
          </div>
        </div>

        {/* Provider Confidence */}
        <div className="bg-surface border border-border-custom rounded-xl p-5">
          <h3 className="text-sm font-semibold text-heading mb-4">Data Feed Confidence by Provider</h3>
          <div className="space-y-4 mt-6">
            {CONFIDENCE_DATA.map((provider) => (
              <div key={provider.name} className="space-y-1">
                <div className="flex items-center justify-between">
                  <span className="text-xs text-text-main font-medium">{provider.name}</span>
                  <span className="text-xs font-bold text-heading">{provider.confidence}%</span>
                </div>
                <div className="w-full h-2 rounded-full bg-surface-elevated overflow-hidden">
                  <div
                    className="h-full rounded-full transition-all duration-500"
                    style={{
                      width: `${provider.confidence}%`,
                      backgroundColor: provider.fill,
                    }}
                  />
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* System Info */}
      <div className="bg-surface border border-border-custom rounded-xl p-5">
        <h3 className="text-sm font-semibold text-heading mb-3">AI Pipeline Performance</h3>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          {[
            { label: "Coordinator (GPT-4o)", latency: "850ms" },
            { label: "Operations Analyst", latency: "320ms" },
            { label: "Explainability Agent", latency: "280ms" },
            { label: "Recommendation Agent", latency: "310ms" },
          ].map((agent) => (
            <div key={agent.label} className="bg-surface-elevated rounded-lg p-3 text-center">
              <p className="text-xs font-medium text-heading mb-1">{agent.label}</p>
              <p className="text-lg font-bold text-primary">{agent.latency}</p>
              <p className="text-[9px] text-muted-custom">Avg response time</p>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
