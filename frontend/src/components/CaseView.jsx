"use client";

import React, { useState, useEffect } from "react";
import { Folder, FolderOpen, CheckSquare, Clock, FileText, AlertCircle } from "lucide-react";
import { API_BASE_URL } from "../config";

export default function CaseView({ userProfile }) {
  const [cases, setCases] = useState([]);
  const [loading, setLoading] = useState(true);
  const [statusFilter, setStatusFilter] = useState("open");
  const [closingCaseId, setClosingCaseId] = useState(null);
  const [resolutionNote, setResolutionNote] = useState("");
  const [submitting, setSubmitting] = useState(false);

  const fetchCases = async () => {
    try {
      setLoading(true);
      // Backend GET /api/v1/cases might be available. If not, default to mocks
      const response = await fetch(`${API_BASE_URL}/api/v1/cases?status=${statusFilter}`);
      if (response.ok) {
        const data = await response.json();
        setCases(data.cases || []);
      } else {
        throw new Error("API not implemented");
      }
    } catch (err) {
      console.error("Failed to fetch cases, loading mock data:", err);
      loadMockCases();
    } finally {
      setLoading(false);
    }
  };

  const loadMockCases = () => {
    const mocks = [
      {
        id: "case-1",
        title: "Nagad & bKash liquidity imbalance alert at Sylhet Station #3",
        alert_ids: ["alert-uuid-1", "alert-uuid-2"],
        status: "open",
        resolution_note: "",
        created_at: "2026-07-11T09:12:00Z"
      },
      {
        id: "case-2",
        title: "Velocity Anomaly flag: multiple micro-deposits within 5 mins",
        alert_ids: ["alert-uuid-3"],
        status: "open",
        resolution_note: "",
        created_at: "2026-07-11T07:45:00Z"
      },
      {
        id: "case-3",
        title: "Forecast breach risk: Rocket wallet estimated depletion < 2h",
        alert_ids: ["alert-uuid-4"],
        status: "closed",
        resolution_note: "Resolved: Operator successfully transferred 20,000 BDT from cash reserves to Rocket wallet.",
        created_at: "2026-07-10T14:30:00Z"
      }
    ];

    const filtered = mocks.filter(c => c.status === statusFilter);
    setCases(filtered);
  };

  useEffect(() => {
    fetchCases();
  }, [statusFilter, userProfile]);

  const handleCloseCase = async (caseId) => {
    if (!resolutionNote.trim()) {
      alert("Resolution note is required to close a case.");
      return;
    }

    try {
      setSubmitting(true);
      const response = await fetch(`${API_BASE_URL}/api/v1/cases/${caseId}/close`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ resolution_note: resolutionNote })
      });

      if (response.ok) {
        setResolutionNote("");
        setClosingCaseId(null);
        fetchCases();
      } else {
        alert("Server error when closing case.");
      }
    } catch (err) {
      console.error("Failed to close case:", err);
      // Simulate state transition locally
      setCases(prev => prev.filter(c => c.id !== caseId));
      setClosingCaseId(null);
      setResolutionNote("");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex justify-between items-center border-b border-border-custom pb-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-heading">Case Management</h1>
          <p className="text-xs text-muted-custom mt-0.5">Escalated incidents and rebalancing resolution logs</p>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex gap-2 border-b border-border-custom pb-3">
        <button
          onClick={() => {
            setStatusFilter("open");
            setClosingCaseId(null);
          }}
          className={`px-4 py-2 rounded-lg text-xs font-bold uppercase tracking-wider transition-all cursor-pointer flex items-center gap-2 ${
            statusFilter === "open"
              ? "bg-secondary text-white shadow-sm"
              : "bg-surface border border-border-custom text-text-main hover:bg-slate-50"
          }`}
        >
          <FolderOpen size={14} /> Open Cases
        </button>
        <button
          onClick={() => {
            setStatusFilter("closed");
            setClosingCaseId(null);
          }}
          className={`px-4 py-2 rounded-lg text-xs font-bold uppercase tracking-wider transition-all cursor-pointer flex items-center gap-2 ${
            statusFilter === "closed"
              ? "bg-secondary text-white shadow-sm"
              : "bg-surface border border-border-custom text-text-main hover:bg-slate-50"
          }`}
        >
          <Folder size={14} /> Closed Archive
        </button>
      </div>

      {/* Cases list */}
      {loading ? (
        <div className="flex flex-col items-center justify-center py-12">
          <div className="w-10 h-10 rounded-full border-4 border-slate-100 border-t-secondary animate-spin"></div>
          <span className="text-xs font-semibold text-muted-custom mt-2">Loading cases...</span>
        </div>
      ) : cases.length === 0 ? (
        <div className="bg-surface border border-border-custom rounded-xl p-12 text-center shadow-sm">
          <CheckSquare className="text-success-custom mx-auto mb-3" size={32} />
          <h3 className="font-bold text-heading text-sm">No Active Cases</h3>
          <p className="text-xs text-muted-custom mt-1">All escalated incidents have been investigated and closed.</p>
        </div>
      ) : (
        <div className="space-y-4">
          {cases.map((c) => {
            const isClosing = closingCaseId === c.id;
            return (
              <div 
                key={c.id} 
                className="bg-surface border border-border-custom rounded-xl p-5 shadow-sm space-y-4"
              >
                <div className="flex items-start justify-between gap-4">
                  <div className="space-y-1">
                    <h3 className="font-bold text-heading text-sm text-left">{c.title}</h3>
                    <div className="flex flex-wrap items-center gap-3 text-[10px] text-muted-custom font-semibold">
                      <span className="flex items-center gap-1">
                        <Clock size={12} /> Created: {new Date(c.created_at).toLocaleString()}
                      </span>
                      <span className="bg-slate-100 px-2 py-0.5 rounded border border-border-custom">
                        {c.alert_ids.length} Linked Alerts
                      </span>
                    </div>
                  </div>

                  {c.status === "open" && !isClosing && (
                    <button
                      onClick={() => setClosingCaseId(c.id)}
                      className="px-3 py-1.5 bg-emerald-600 hover:bg-emerald-700 text-white text-xs font-bold rounded-lg cursor-pointer transition-all shadow-sm shrink-0"
                    >
                      Close Incident
                    </button>
                  )}
                </div>

                {/* Resolution note display for closed archive */}
                {c.status === "closed" && c.resolution_note && (
                  <div className="bg-slate-50 border border-border-custom p-4 rounded-lg flex items-start gap-2.5 text-xs">
                    <FileText size={16} className="text-muted-custom shrink-0 mt-0.5" />
                    <div>
                      <span className="font-bold text-heading uppercase text-[10px] block mb-1">Resolution Audit Note</span>
                      <p className="text-text-main leading-relaxed">{c.resolution_note}</p>
                    </div>
                  </div>
                )}

                {/* Close Case action form */}
                {isClosing && (
                  <div className="space-y-3 p-4 bg-slate-50 border border-border-custom rounded-lg border-l-4 border-l-emerald-600 animate-fadeIn">
                    <div>
                      <h4 className="text-xs font-bold text-heading mb-1">Resolve and Close Case</h4>
                      <p className="text-[10px] text-muted-custom">Please supply diagnostic resolution notes to log audit transparency.</p>
                    </div>
                    <textarea
                      value={resolutionNote}
                      onChange={(e) => setResolutionNote(e.target.value)}
                      placeholder="Detailing balance rebalancing, physical checks, or fake anomaly reports..."
                      className="w-full bg-white border border-border-custom text-text-main text-xs p-3 rounded-lg h-20 focus:outline-none focus:border-secondary"
                    />
                    <div className="flex gap-2 justify-end">
                      <button
                        onClick={() => {
                          setClosingCaseId(null);
                          setResolutionNote("");
                        }}
                        className="px-3 py-1.5 bg-slate-100 hover:bg-slate-200 text-text-main text-xs font-semibold rounded-lg cursor-pointer"
                      >
                        Cancel
                      </button>
                      <button
                        onClick={() => handleCloseCase(c.id)}
                        disabled={submitting}
                        className="px-4 py-1.5 bg-emerald-600 hover:bg-emerald-700 disabled:opacity-50 text-white text-xs font-bold rounded-lg cursor-pointer flex items-center gap-1.5"
                      >
                        {submitting && (
                          <span className="w-3 h-3 rounded-full border-2 border-white/30 border-t-white animate-spin"></span>
                        )}
                        Confirm Closure
                      </button>
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
