"use client";

import React, { useState, useEffect } from "react";
import { auth } from "../../firebase/firebase.init";
import { AlertCircle, AlertTriangle, CheckCircle, ShieldAlert, Clock, ArrowRight, MessageSquare } from "lucide-react";
import { API_BASE_URL } from "../config";

export default function AlertView({ userProfile }) {
  const [alerts, setAlerts] = useState([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [statusFilter, setStatusFilter] = useState("open");
  const [transitionNote, setTransitionNote] = useState("");
  const [activeAlertId, setActiveAlertId] = useState(null);
  const [actioningAlertId, setActioningAlertId] = useState(null);
  const [actionType, setActionType] = useState(null); // "acknowledge" | "escalate" | "resolve"

  const fetchAlerts = async () => {
    try {
      setLoading(true);
      const firebaseUser = auth.currentUser;
      if (!firebaseUser) return;
      const idToken = await firebaseUser.getIdToken();
      
      const filterParam = statusFilter === "all" ? "" : `status_filter=${statusFilter}`;
      const url = `${API_BASE_URL}/api/v1/alerts?${filterParam}`;
      
      const response = await fetch(url, {
        headers: {
          "Authorization": `Bearer ${idToken}`
        }
      });
      if (response.ok) {
        const data = await response.json();
        setAlerts(data.alerts || []);
        setTotal(data.total || 0);
      } else {
        throw new Error("Backend response error");
      }
    } catch (err) {
      console.error("Failed to fetch alerts from backend, loading mock data:", err);
      loadMockAlerts();
    } finally {
      setLoading(false);
    }
  };

  const loadMockAlerts = () => {
    const mocks = [
      {
        id: "alert-1",
        alert_type: "liquidity_low",
        severity: "high",
        confidence: 0.94,
        evidence: {
          lowest_provider: "rocket",
          total_liquidity_bdt: 104500.0,
          rocket_bdt: 9500.0
        },
        status: "open",
        assigned_to_user_id: null,
        notes: "",
        created_at: "2026-07-11T08:30:00Z"
      },
      {
        id: "alert-2",
        alert_type: "anomaly_detected",
        severity: "critical",
        confidence: 0.85,
        evidence: {
          flag_type: "circular_flow",
          explanation: "Circular cash flow patterns detected between user nodes."
        },
        status: "acknowledged",
        assigned_to_user_id: "user-123",
        notes: "Acknowledge Note: Assigned to field team review.",
        created_at: "2026-07-11T07:15:00Z"
      },
      {
        id: "alert-3",
        alert_type: "forecast_breach",
        severity: "medium",
        confidence: 0.76,
        evidence: {
          provider: "bkash",
          predicted_breach_hours: 6
        },
        status: "resolved",
        assigned_to_user_id: "user-123",
        notes: "Resolved Note: Wallet rebalanced successfully.",
        created_at: "2026-07-11T06:02:00Z"
      }
    ];

    const filtered = statusFilter === "all" 
      ? mocks 
      : mocks.filter(a => a.status === statusFilter);
    setAlerts(filtered);
    setTotal(filtered.length);
  };

  useEffect(() => {
    fetchAlerts();
  }, [statusFilter, userProfile]);

  const handleTransition = async (alertId) => {
    if (!actionType) return;
    try {
      setActioningAlertId(alertId);
      const firebaseUser = auth.currentUser;
      const idToken = firebaseUser ? await firebaseUser.getIdToken() : "";
      
      const response = await fetch(`${API_BASE_URL}/api/v1/alerts/${alertId}/${actionType}`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "Authorization": `Bearer ${idToken}`
        },
        body: JSON.stringify({ note: transitionNote })
      });

      if (response.ok) {
        setTransitionNote("");
        setActionType(null);
        setActiveAlertId(null);
        fetchAlerts();
      } else {
        alert("Failed to submit transition. Backend returned an error.");
      }
    } catch (err) {
      console.error(`Alert transition ${actionType} error:`, err);
      // Simulate state transition locally on mock data
      setAlerts(prev => prev.map(a => {
        if (a.id === alertId) {
          const nextStatus = actionType === "acknowledge" 
            ? "acknowledged" 
            : actionType === "escalate" 
            ? "escalated" 
            : "resolved";
          return {
            ...a,
            status: nextStatus,
            notes: a.notes + `\n[${actionType.toUpperCase()}] ${transitionNote}`
          };
        }
        return a;
      }));
      setTransitionNote("");
      setActionType(null);
      setActiveAlertId(null);
    } finally {
      setActioningAlertId(null);
    }
  };

  const getAlertIcon = (type) => {
    switch (type) {
      case "liquidity_low":
      case "liquidity_critical":
        return <TrendingDown className="text-warning-custom" size={18} />;
      case "anomaly_detected":
        return <ShieldAlert className="text-error-custom" size={18} />;
      default:
        return <AlertTriangle className="text-info-custom" size={18} />;
    }
  };

  const getSeverityStyle = (sev) => {
    switch (sev) {
      case "critical":
        return "bg-red-500/10 text-red-500 border border-red-500/20";
      case "high":
        return "bg-orange-500/10 text-orange-500 border border-orange-500/20";
      case "medium":
        return "bg-yellow-500/10 text-yellow-500 border border-yellow-500/20";
      default:
        return "bg-blue-500/10 text-blue-500 border border-blue-500/20";
    }
  };

  const getStatusStyle = (status) => {
    switch (status) {
      case "open":
        return "bg-rose-100 text-rose-700";
      case "acknowledged":
        return "bg-amber-100 text-amber-700";
      case "escalated":
        return "bg-purple-100 text-purple-700";
      default:
        return "bg-emerald-100 text-emerald-700";
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex justify-between items-center border-b border-border-custom pb-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-heading">Security & Liquidity Alerts</h1>
          <p className="text-xs text-muted-custom mt-0.5">Manage and resolve depletion and anomaly triggers</p>
        </div>
        <div className="text-xs font-bold text-heading bg-slate-100 border border-border-custom px-3 py-1.5 rounded-lg shadow-sm">
          Total alerts: {total}
        </div>
      </div>

      {/* Tabs / Filter bar */}
      <div className="flex gap-2 border-b border-border-custom pb-3">
        {["open", "acknowledged", "escalated", "resolved", "all"].map((tab) => (
          <button
            key={tab}
            onClick={() => {
              setStatusFilter(tab);
              setActionType(null);
            }}
            className={`px-4 py-2 rounded-lg text-xs font-bold uppercase tracking-wider transition-all cursor-pointer ${
              statusFilter === tab
                ? "bg-secondary text-white shadow-sm"
                : "bg-surface border border-border-custom text-text-main hover:bg-slate-50"
            }`}
          >
            {tab}
          </button>
        ))}
      </div>

      {/* Loading overlay */}
      {loading ? (
        <div className="flex flex-col items-center justify-center py-12">
          <div className="w-10 h-10 rounded-full border-4 border-slate-100 border-t-secondary animate-spin"></div>
          <span className="text-xs font-semibold text-muted-custom mt-2">Loading latest alerts...</span>
        </div>
      ) : alerts.length === 0 ? (
        <div className="bg-surface border border-border-custom rounded-xl p-12 text-center shadow-sm">
          <CheckCircle className="text-success-custom mx-auto mb-3" size={32} />
          <h3 className="font-bold text-heading text-sm">All Clear</h3>
          <p className="text-xs text-muted-custom mt-1">No alerts found matching this status filter.</p>
        </div>
      ) : (
        <div className="space-y-4">
          {alerts.map((alertItem) => {
            const isExpanded = activeAlertId === alertItem.id;
            return (
              <div 
                key={alertItem.id}
                className="bg-surface border border-border-custom rounded-xl p-5 shadow-sm transition-all hover:border-border-custom/80"
              >
                <div className="flex items-start justify-between gap-4">
                  <div className="flex items-start gap-3">
                    <div className="p-2 bg-slate-50 border border-border-custom rounded-lg mt-0.5">
                      {getAlertIcon(alertItem.alert_type)}
                    </div>
                    <div>
                      <h4 className="font-bold text-heading text-sm capitalize">
                        {alertItem.alert_type.replace("_", " ")}
                      </h4>
                      <div className="flex items-center gap-2 mt-1">
                        <span className={`px-2 py-0.5 rounded text-[10px] font-bold uppercase tracking-wider ${getSeverityStyle(alertItem.severity)}`}>
                          {alertItem.severity}
                        </span>
                        <span className={`px-2 py-0.5 rounded text-[10px] font-bold uppercase tracking-wider ${getStatusStyle(alertItem.status)}`}>
                          {alertItem.status}
                        </span>
                        <span className="text-[10px] text-muted-custom font-medium flex items-center gap-1">
                          <Clock size={10} /> {new Date(alertItem.created_at).toLocaleString()}
                        </span>
                      </div>
                    </div>
                  </div>
                  
                  <button
                    onClick={() => {
                      setActiveAlertId(isExpanded ? null : alertItem.id);
                      setActionType(null);
                    }}
                    className="text-xs font-semibold text-secondary hover:underline cursor-pointer focus:outline-none"
                  >
                    {isExpanded ? "Collapse Details" : "View Diagnostics"}
                  </button>
                </div>

                {/* Details Section */}
                {isExpanded && (
                  <div className="mt-4 pt-4 border-t border-border-custom/50 space-y-4 animate-fadeIn">
                    {/* Evidence Parameters */}
                    <div className="bg-slate-50 p-4 border border-border-custom rounded-lg space-y-2">
                      <span className="text-[10px] font-bold text-heading uppercase tracking-wide block">Evidence Data</span>
                      <pre className="text-[10px] font-mono text-text-main overflow-x-auto whitespace-pre-wrap">
                        {JSON.stringify(alertItem.evidence, null, 2)}
                      </pre>
                    </div>

                    {/* notes audit history */}
                    {alertItem.notes && (
                      <div className="space-y-1 bg-amber-50/20 border border-amber-500/10 p-3 rounded-lg text-xs">
                        <span className="font-bold text-heading flex items-center gap-1.5 text-[10px] uppercase text-amber-700">
                          <MessageSquare size={12} /> Resolution Notes & transitions
                        </span>
                        <p className="text-text-main font-medium whitespace-pre-line text-[11px]">{alertItem.notes}</p>
                      </div>
                    )}

                    {/* Transition Actions Form */}
                    {alertItem.status !== "resolved" && (
                      <div className="pt-2">
                        {actionType ? (
                          <div className="space-y-3 p-4 bg-slate-50 border border-border-custom rounded-lg">
                            <h5 className="text-xs font-bold text-heading capitalize">
                              Add notes for: {actionType}
                            </h5>
                            <textarea
                              value={transitionNote}
                              onChange={(e) => setTransitionNote(e.target.value)}
                              placeholder="Describe actions taken, escalations, or rebalancing details..."
                              className="w-full bg-white border border-border-custom text-text-main text-xs p-3 rounded-lg h-20 focus:outline-none focus:border-secondary"
                            />
                            <div className="flex gap-2 justify-end">
                              <button
                                onClick={() => setActionType(null)}
                                className="px-3 py-1.5 bg-slate-100 hover:bg-slate-200 text-text-main text-xs font-semibold rounded-lg cursor-pointer"
                              >
                                Cancel
                              </button>
                              <button
                                onClick={() => handleTransition(alertItem.id)}
                                disabled={actioningAlertId === alertItem.id}
                                className="px-4 py-1.5 bg-secondary hover:bg-secondary/90 disabled:opacity-50 text-white text-xs font-bold rounded-lg cursor-pointer flex items-center gap-1.5"
                              >
                                {actioningAlertId === alertItem.id && (
                                  <span className="w-3 h-3 rounded-full border-2 border-white/30 border-t-white animate-spin"></span>
                                )}
                                Submit Transition
                              </button>
                            </div>
                          </div>
                        ) : (
                          <div className="flex gap-2">
                            {alertItem.status === "open" && (
                              <button
                                onClick={() => setActionType("acknowledge")}
                                className="px-3.5 py-2 bg-amber-500 hover:bg-amber-600 text-white text-xs font-bold rounded-lg cursor-pointer shadow-sm transition-all"
                              >
                                Acknowledge Alert
                              </button>
                            )}
                            {(alertItem.status === "acknowledged" || alertItem.status === "escalated") && (
                              <>
                                <button
                                  onClick={() => setActionType("escalate")}
                                  className="px-3.5 py-2 bg-purple-600 hover:bg-purple-700 text-white text-xs font-bold rounded-lg cursor-pointer shadow-sm transition-all"
                                >
                                  Escalate Case
                                </button>
                                <button
                                  onClick={() => setActionType("resolve")}
                                  className="px-3.5 py-2 bg-emerald-600 hover:bg-emerald-700 text-white text-xs font-bold rounded-lg cursor-pointer shadow-sm transition-all"
                                >
                                  Resolve Issue
                                </button>
                              </>
                            )}
                          </div>
                        )}
                      </div>
                    )}
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
