"use client";

import React, { useState, useEffect } from "react";
import {
  Briefcase,
  Clock,
  User,
  ChevronDown,
  ChevronRight,
  AlertTriangle,
  CheckCircle2,
  RefreshCw,
} from "lucide-react";
import { useDashboard } from "../context/DashboardContext";

export default function CaseView() {
  const { fetchWithAuth } = useDashboard();
  const [cases, setCases] = useState([]);
  const [loading, setLoading] = useState(true);
  const [expandedCase, setExpandedCase] = useState(null);
  const [statusFilter, setStatusFilter] = useState("all");

  useEffect(() => {
    loadCases();
  }, [statusFilter]);

  const loadCases = async () => {
    setLoading(true);
    try {
      const url = statusFilter === "all" ? "/api/v1/cases" : `/api/v1/cases?status_filter=${statusFilter}`;
      const data = await fetchWithAuth(url);
      setCases(data.cases || []);
    } catch (err) {
      console.error("Failed to load cases:", err);
    }
    setLoading(false);
  };

  const openCases = cases.filter((c) => c.status === "open");
  const closedCases = cases.filter((c) => c.status === "closed");

  return (
    <div className="space-y-5">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-heading">Case Management</h1>
          <p className="text-sm text-muted-custom mt-0.5">Track and manage grouped alert investigations</p>
        </div>
        <button
          onClick={loadCases}
          className="flex items-center gap-1.5 px-3 py-1.5 bg-surface-elevated border border-border-light rounded-lg text-xs text-muted-custom hover:text-heading transition-all cursor-pointer"
        >
          <RefreshCw size={13} className={loading ? "animate-spin" : ""} />
          Refresh
        </button>
      </div>

      {/* Summary Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <SummaryCard
          label="Open Cases"
          value={openCases.length}
          icon={Briefcase}
          color="warning"
        />
        <SummaryCard
          label="Resolved"
          value={closedCases.length}
          icon={CheckCircle2}
          color="primary"
        />
        <SummaryCard
          label="Total Alerts Linked"
          value={cases.reduce((acc, c) => acc + (c.alert_ids?.length || 0), 0)}
          icon={AlertTriangle}
          color="info"
        />
      </div>

      {/* Filters */}
      <div className="flex items-center gap-2">
        {["all", "open", "closed"].map((s) => (
          <button
            key={s}
            onClick={() => setStatusFilter(s)}
            className={`px-3 py-1 rounded-full text-xs font-medium transition-all cursor-pointer capitalize ${
              statusFilter === s
                ? "bg-primary/15 text-primary border border-primary/30"
                : "bg-surface-elevated text-muted-custom hover:text-heading border border-border-light"
            }`}
          >
            {s}
          </button>
        ))}
      </div>

      {/* Cases */}
      {loading ? (
        <div className="bg-surface border border-border-custom rounded-xl p-10 text-center">
          <RefreshCw size={24} className="text-primary mx-auto mb-2 animate-spin" />
          <p className="text-sm text-muted-custom">Loading cases...</p>
        </div>
      ) : cases.length === 0 ? (
        <div className="bg-surface border border-border-custom rounded-xl p-10 text-center">
          <Briefcase size={32} className="text-muted-custom mx-auto mb-2 opacity-40" />
          <p className="text-sm text-muted-custom">No cases found</p>
        </div>
      ) : (
        <div className="space-y-3">
          {cases.map((caseItem) => {
            const isExpanded = expandedCase === caseItem.id;
            return (
              <div key={caseItem.id} className="bg-surface border border-border-custom rounded-xl overflow-hidden">
                {/* Header */}
                <button
                  onClick={() => setExpandedCase(isExpanded ? null : caseItem.id)}
                  className="w-full flex items-center justify-between p-4 hover:bg-surface-elevated/50 transition-colors cursor-pointer"
                >
                  <div className="flex items-start gap-3">
                    <div className={`w-8 h-8 rounded-lg flex items-center justify-center ${
                      caseItem.status === "open" ? "bg-warning-custom/10 text-warning-custom" : "bg-primary/10 text-primary"
                    }`}>
                      <Briefcase size={16} />
                    </div>
                    <div className="text-left">
                      <h3 className="text-sm font-semibold text-heading">{caseItem.title}</h3>
                      <div className="flex items-center gap-3 mt-1">
                        <span className="text-[10px] font-mono text-muted-custom">{caseItem.id.slice(0, 8)}...</span>
                        <span className={`inline-flex items-center px-1.5 py-0.5 rounded text-[9px] font-bold uppercase ${
                          caseItem.status === "open" ? "bg-warning-custom/10 text-warning-custom" : "bg-primary/10 text-primary"
                        }`}>
                          {caseItem.status}
                        </span>
                        <span className="text-[10px] text-muted-custom flex items-center gap-1">
                          <AlertTriangle size={9} />
                          {caseItem.alert_ids?.length || 0} alerts
                        </span>
                        <span className="text-[10px] text-muted-custom flex items-center gap-1">
                          <Clock size={9} />
                          {new Date(caseItem.created_at).toLocaleDateString()}
                        </span>
                      </div>
                    </div>
                  </div>
                  {isExpanded ? <ChevronDown size={16} className="text-muted-custom" /> : <ChevronRight size={16} className="text-muted-custom" />}
                </button>

                {/* Expanded Timeline */}
                {isExpanded && (
                  <div className="border-t border-border-custom px-4 py-4 bg-surface-elevated/30">
                    {caseItem.resolution_note && (
                      <div className="mb-3 bg-primary/5 border border-primary/20 rounded-lg p-2.5">
                        <p className="text-xs text-primary font-medium">Resolution: {caseItem.resolution_note}</p>
                      </div>
                    )}

                    <h4 className="text-xs font-semibold text-heading mb-3">Audit Timeline</h4>
                    <div className="relative pl-4 border-l border-border-light space-y-3">
                      {(caseItem.timeline || []).map((entry, i) => (
                        <div key={i} className="relative">
                          <div className={`absolute -left-[21px] top-1 w-2.5 h-2.5 rounded-full border-2 ${
                            entry.action.includes("Created") ? "bg-info-custom/20 border-info-custom" :
                            entry.action.includes("Closed") || entry.action.includes("resolved") ? "bg-primary/20 border-primary" :
                            "bg-surface-elevated border-primary"
                          }`} />
                          <div className="flex items-center gap-2 mb-0.5">
                            <span className="text-[10px] font-mono text-muted-custom">{entry.time}</span>
                            <span className="text-[10px] font-semibold text-heading">{entry.action}</span>
                            <span className="text-[10px] text-muted-custom flex items-center gap-0.5">
                              <User size={8} /> {entry.actor}
                            </span>
                          </div>
                          <p className="text-xs text-text-main">{entry.notes}</p>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}

function SummaryCard({ label, value, icon: Icon, color }) {
  const colorClasses = {
    primary: "text-primary bg-primary/10",
    warning: "text-warning-custom bg-warning-custom/10",
    info: "text-info-custom bg-info-custom/10",
  };

  return (
    <div className="bg-surface border border-border-custom rounded-xl p-4 flex items-center gap-3">
      <div className={`w-10 h-10 rounded-lg flex items-center justify-center ${colorClasses[color]}`}>
        <Icon size={18} />
      </div>
      <div>
        <p className="text-2xl font-bold text-heading">{value}</p>
        <p className="text-[11px] text-muted-custom">{label}</p>
      </div>
    </div>
  );
}
