"use client";

import React, { useState, useEffect } from "react";
import {
  AlertTriangle,
  CheckCircle,
  ArrowUpRight,
  Clock,
  Filter,
  RefreshCw,
  Eye,
  X,
  Zap,
  MessageSquare,
  ShieldAlert,
  Lightbulb,
} from "lucide-react";
import { useDashboard } from "../context/DashboardContext";

const SEVERITY_STYLES = {
  critical: "bg-error-custom/10 text-error-custom border-error-custom/20",
  high: "bg-warning-custom/10 text-warning-custom border-warning-custom/20",
  medium: "bg-info-custom/10 text-info-custom border-info-custom/20",
  low: "bg-muted-custom/10 text-muted-custom border-muted-custom/20",
};

const STATUS_STYLES = {
  open: "bg-error-custom/10 text-error-custom",
  acknowledged: "bg-info-custom/10 text-info-custom",
  in_progress: "bg-warning-custom/10 text-warning-custom",
  escalated: "bg-secondary/10 text-secondary",
  resolved: "bg-primary/10 text-primary",
};

export default function AlertView() {
  const { alerts, fetchAlerts, acknowledgeAlert, escalateAlert, resolveAlert, fetchWithAuth } = useDashboard();
  const [statusFilter, setStatusFilter] = useState("open");
  const [loading, setLoading] = useState(false);
  const [actionNote, setActionNote] = useState("");
  const [selectedAlert, setSelectedAlert] = useState(null);
  const [showActionModal, setShowActionModal] = useState(null);

  // Detail panel state
  const [detailAlert, setDetailAlert] = useState(null);
  const [advisory, setAdvisory] = useState(null);
  const [advisoryLoading, setAdvisoryLoading] = useState(false);

  useEffect(() => {
    loadAlerts();
  }, [statusFilter]);

  const loadAlerts = async () => {
    setLoading(true);
    await fetchAlerts(statusFilter);
    setLoading(false);
  };

  const handleAction = async (action) => {
    if (!selectedAlert) return;
    setLoading(true);
    try {
      if (action === "acknowledge") await acknowledgeAlert(selectedAlert.id, actionNote);
      else if (action === "escalate") await escalateAlert(selectedAlert.id, actionNote);
      else if (action === "resolve") await resolveAlert(selectedAlert.id, actionNote);
      setShowActionModal(null);
      setActionNote("");
      setSelectedAlert(null);
      setDetailAlert(null);
      // Switch to resolved tab after acknowledge/resolve so user can see it
      if (action === "acknowledge" || action === "resolve") {
        setStatusFilter("resolved");
      } else {
        await loadAlerts();
      }
    } catch (err) {
      console.error("Alert action failed:", err);
    }
    setLoading(false);
  };

  const handleViewDetails = async (alert) => {
    setDetailAlert(alert);
    setAdvisory(null);
    setAdvisoryLoading(true);
    try {
      const data = await fetchWithAuth(`/api/v1/alerts/${alert.id}/advisory`, { method: "POST" });
      setAdvisory(data);
    } catch (err) {
      console.error("Advisory fetch failed:", err);
      setAdvisory({
        advisory: "Unable to generate advisory at this time.",
        recommendations: ["Please review the alert evidence manually."],
        confidence_note: "Advisory system unavailable.",
        severity_context: `Alert severity: ${alert.severity}`,
      });
    }
    setAdvisoryLoading(false);
  };

  const closeDetailPanel = () => {
    setDetailAlert(null);
    setAdvisory(null);
  };

  const statuses = ["open", "acknowledged", "in_progress", "escalated", "resolved"];

  return (
    <div className="space-y-5">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-heading">Alerts</h1>
          <p className="text-sm text-muted-custom mt-0.5">Monitor and manage liquidity alerts</p>
        </div>
        <button
          onClick={loadAlerts}
          className="flex items-center gap-1.5 px-3 py-1.5 bg-surface-elevated border border-border-light rounded-lg text-xs text-muted-custom hover:text-heading transition-all cursor-pointer"
        >
          <RefreshCw size={13} className={loading ? "animate-spin" : ""} />
          Refresh
        </button>
      </div>

      {/* Status Filters */}
      <div className="flex items-center gap-2 flex-wrap">
        <Filter size={14} className="text-muted-custom" />
        {statuses.map((s) => (
          <button
            key={s}
            onClick={() => setStatusFilter(s)}
            className={`px-3 py-1 rounded-full text-xs font-medium transition-all cursor-pointer capitalize ${
              statusFilter === s
                ? "bg-primary/15 text-primary border border-primary/30"
                : "bg-surface-elevated text-muted-custom hover:text-heading border border-border-light"
            }`}
          >
            {s.replace(/_/g, " ")}
          </button>
        ))}
      </div>

      {/* Alert List */}
      <div className="space-y-3">
        {alerts.length === 0 && !loading && (
          <div className="bg-surface border border-border-custom rounded-xl p-10 text-center">
            <CheckCircle size={32} className="text-primary mx-auto mb-2 opacity-50" />
            <p className="text-sm text-muted-custom">No alerts with status &ldquo;{statusFilter.replace(/_/g, " ")}&rdquo;</p>
          </div>
        )}

        {alerts.map((alert) => (
          <div
            key={alert.id}
            className="bg-surface border border-border-custom rounded-xl p-4 hover:border-border-light transition-all"
          >
            <div className="flex items-start justify-between">
              <div className="flex-1">
                <div className="flex items-center gap-2 mb-1.5">
                  <span className={`inline-flex items-center px-2 py-0.5 rounded text-[10px] font-bold uppercase border ${SEVERITY_STYLES[alert.severity]}`}>
                    {alert.severity}
                  </span>
                  <span className={`inline-flex items-center px-2 py-0.5 rounded text-[10px] font-medium capitalize ${STATUS_STYLES[alert.status]}`}>
                    {alert.status.replace(/_/g, " ")}
                  </span>
                  <span className="text-[10px] text-muted-custom">
                    {(alert.confidence * 100).toFixed(0)}% confidence
                  </span>
                </div>
                <h3 className="text-sm font-semibold text-heading capitalize">
                  {alert.alert_type.replace(/_/g, " ")}
                </h3>
                <p className="text-xs text-muted-custom mt-1">
                  Agent: <span className="font-mono text-text-main">{alert.agent_id.slice(0, 8)}...</span>
                </p>
                <div className="flex items-center gap-3 mt-2 text-[10px] text-muted-custom">
                  <span className="flex items-center gap-1">
                    <Clock size={10} />
                    {new Date(alert.created_at).toLocaleString()}
                  </span>
                  {alert.assigned_to_user_id && (
                    <span>Assigned: {alert.assigned_to_user_id.slice(0, 8)}...</span>
                  )}
                </div>
              </div>

              {/* Actions */}
              <div className="flex flex-col gap-1.5 ml-3">
                {/* View Details Button */}
                <button
                  onClick={() => handleViewDetails(alert)}
                  className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg text-[10px] font-semibold bg-primary/10 text-primary hover:bg-primary/20 border border-primary/20 transition-all cursor-pointer whitespace-nowrap"
                >
                  <Eye size={11} />
                  View Details
                </button>

                {alert.status === "open" && (
                  <ActionButton
                    label="Acknowledge"
                    onClick={() => { setSelectedAlert(alert); setShowActionModal("acknowledge"); }}
                  />
                )}
                {["acknowledged", "in_progress"].includes(alert.status) && (
                  <ActionButton
                    label="Escalate"
                    onClick={() => { setSelectedAlert(alert); setShowActionModal("escalate"); }}
                  />
                )}
                {["acknowledged", "in_progress", "escalated"].includes(alert.status) && (
                  <ActionButton
                    label="Resolve"
                    variant="success"
                    onClick={() => { setSelectedAlert(alert); setShowActionModal("resolve"); }}
                  />
                )}
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* Detail Panel (Slide-over) */}
      {detailAlert && (
        <div className="fixed inset-0 bg-black/60 z-50 flex justify-end">
          <div className="w-full max-w-lg bg-surface border-l border-border-custom h-full overflow-y-auto animate-in slide-in-from-right">
            {/* Panel Header */}
            <div className="sticky top-0 bg-surface border-b border-border-custom px-5 py-4 flex items-center justify-between z-10">
              <div className="flex items-center gap-2">
                <ShieldAlert size={18} className="text-primary" />
                <h2 className="text-sm font-bold text-heading">Alert Details</h2>
              </div>
              <button
                onClick={closeDetailPanel}
                className="w-7 h-7 rounded-lg bg-surface-elevated flex items-center justify-center text-muted-custom hover:text-heading transition-colors cursor-pointer"
              >
                <X size={14} />
              </button>
            </div>

            <div className="p-5 space-y-5">
              {/* Alert Info */}
              <div className="space-y-3">
                <div className="flex items-center gap-2">
                  <span className={`inline-flex items-center px-2.5 py-1 rounded text-[11px] font-bold uppercase border ${SEVERITY_STYLES[detailAlert.severity]}`}>
                    {detailAlert.severity}
                  </span>
                  <span className={`inline-flex items-center px-2.5 py-1 rounded text-[11px] font-medium capitalize ${STATUS_STYLES[detailAlert.status]}`}>
                    {detailAlert.status.replace(/_/g, " ")}
                  </span>
                </div>

                <h3 className="text-base font-bold text-heading capitalize">
                  {detailAlert.alert_type.replace(/_/g, " ")}
                </h3>

                <div className="grid grid-cols-2 gap-3">
                  <InfoItem label="Confidence" value={`${(detailAlert.confidence * 100).toFixed(0)}%`} />
                  <InfoItem label="Created" value={new Date(detailAlert.created_at).toLocaleString()} />
                  <InfoItem label="Agent" value={detailAlert.agent_id.slice(0, 12) + "..."} mono />
                  <InfoItem label="Status" value={detailAlert.status.replace(/_/g, " ")} />
                </div>

                {/* Evidence */}
                {detailAlert.evidence && Object.keys(detailAlert.evidence).length > 0 && (
                  <div className="bg-surface-elevated border border-border-light rounded-lg p-3">
                    <p className="text-[10px] font-semibold text-muted-custom uppercase tracking-wider mb-2">Evidence</p>
                    <div className="space-y-1.5">
                      {Object.entries(detailAlert.evidence).map(([key, value]) => (
                        <div key={key} className="flex items-center justify-between">
                          <span className="text-xs text-muted-custom capitalize">{key.replace(/_/g, " ")}</span>
                          <span className="text-xs font-medium text-heading font-mono">
                            {typeof value === "boolean" ? (value ? "Yes" : "No") : String(value)}
                          </span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>

              {/* AI Advisory Section */}
              <div className="border-t border-border-custom pt-5">
                <div className="flex items-center gap-2 mb-4">
                  <div className="w-7 h-7 rounded-lg bg-primary/10 flex items-center justify-center">
                    <Zap size={14} className="text-primary" />
                  </div>
                  <div>
                    <h4 className="text-sm font-bold text-heading">AI Advisory</h4>
                    <p className="text-[10px] text-muted-custom">Intelligent analysis and recommendations</p>
                  </div>
                </div>

                {advisoryLoading ? (
                  <div className="bg-surface-elevated rounded-xl p-6 text-center">
                    <div className="w-8 h-8 rounded-full border-2 border-primary/30 border-t-primary animate-spin mx-auto mb-3" />
                    <p className="text-xs text-muted-custom">Generating advisory...</p>
                  </div>
                ) : advisory ? (
                  <div className="space-y-3">
                    {/* Main Advisory */}
                    <div className="bg-surface-elevated border border-primary/20 rounded-xl p-4">
                      <div className="flex items-start gap-2.5">
                        <MessageSquare size={16} className="text-primary mt-0.5 shrink-0" />
                        <p className="text-sm text-heading leading-relaxed">{advisory.advisory}</p>
                      </div>
                    </div>

                    {/* Severity Context */}
                    {advisory.severity_context && (
                      <div className="bg-warning-custom/5 border border-warning-custom/15 rounded-lg p-3">
                        <div className="flex items-start gap-2">
                          <AlertTriangle size={13} className="text-warning-custom mt-0.5 shrink-0" />
                          <p className="text-xs text-warning-custom">{advisory.severity_context}</p>
                        </div>
                      </div>
                    )}

                    {/* Confidence Note */}
                    {advisory.confidence_note && (
                      <div className="flex items-start gap-2 px-1">
                        <ShieldAlert size={12} className="text-muted-custom mt-0.5 shrink-0" />
                        <p className="text-[11px] text-muted-custom italic">{advisory.confidence_note}</p>
                      </div>
                    )}

                    {/* Recommendations */}
                    {advisory.recommendations?.length > 0 && (
                      <div className="bg-surface-elevated rounded-xl p-4">
                        <div className="flex items-center gap-2 mb-2.5">
                          <Lightbulb size={14} className="text-primary" />
                          <p className="text-xs font-semibold text-heading">Recommendations</p>
                        </div>
                        <ul className="space-y-2">
                          {advisory.recommendations.map((rec, i) => (
                            <li key={i} className="flex items-start gap-2.5">
                              <span className="w-4 h-4 rounded-full bg-primary/15 text-primary text-[9px] font-bold flex items-center justify-center shrink-0 mt-0.5">
                                {i + 1}
                              </span>
                              <span className="text-xs text-text-main leading-relaxed">{rec}</span>
                            </li>
                          ))}
                        </ul>
                      </div>
                    )}

                    {/* Language badge */}
                    {advisory.language && (
                      <div className="flex items-center gap-1.5 pt-1">
                        <span className="text-[9px] text-muted-custom bg-surface-elevated px-2 py-0.5 rounded-full">
                          Language: {advisory.language === "bn" || advisory.language === "Bengali" ? "বাংলা" : advisory.language === "banglish" || advisory.language === "Banglish" ? "Banglish" : "English"}
                        </span>
                      </div>
                    )}
                  </div>
                ) : null}
              </div>

              {/* Actions in detail panel */}
              <div className="border-t border-border-custom pt-4 space-y-2">
                <p className="text-[10px] font-semibold text-muted-custom uppercase tracking-wider mb-2">Actions</p>
                <div className="flex flex-wrap gap-2">
                  {detailAlert.status === "open" && (
                    <button
                      onClick={() => { setSelectedAlert(detailAlert); setShowActionModal("acknowledge"); }}
                      className="px-3 py-1.5 rounded-lg text-xs font-medium bg-info-custom/10 text-info-custom border border-info-custom/20 hover:bg-info-custom/20 transition-all cursor-pointer"
                    >
                      Acknowledge
                    </button>
                  )}
                  {["acknowledged", "in_progress"].includes(detailAlert.status) && (
                    <button
                      onClick={() => { setSelectedAlert(detailAlert); setShowActionModal("escalate"); }}
                      className="px-3 py-1.5 rounded-lg text-xs font-medium bg-secondary/10 text-secondary border border-secondary/20 hover:bg-secondary/20 transition-all cursor-pointer"
                    >
                      Escalate
                    </button>
                  )}
                  {["acknowledged", "in_progress", "escalated"].includes(detailAlert.status) && (
                    <button
                      onClick={() => { setSelectedAlert(detailAlert); setShowActionModal("resolve"); }}
                      className="px-3 py-1.5 rounded-lg text-xs font-medium bg-primary/10 text-primary border border-primary/20 hover:bg-primary/20 transition-all cursor-pointer"
                    >
                      Resolve
                    </button>
                  )}
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Action Modal */}
      {showActionModal && (
        <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-[60] p-4">
          <div className="bg-surface border border-border-custom rounded-xl p-5 w-full max-w-sm">
            <h3 className="text-sm font-bold text-heading capitalize mb-3">
              {showActionModal} Alert
            </h3>
            <textarea
              value={actionNote}
              onChange={(e) => setActionNote(e.target.value)}
              placeholder="Add a note (optional)..."
              className="w-full bg-surface-elevated border border-border-light text-text-main rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-primary resize-none h-20"
            />
            <div className="flex gap-2 mt-3">
              <button
                onClick={() => { setShowActionModal(null); setActionNote(""); }}
                className="flex-1 px-3 py-2 bg-surface-elevated border border-border-light text-muted-custom rounded-lg text-xs font-medium hover:text-heading transition-all cursor-pointer"
              >
                Cancel
              </button>
              <button
                onClick={() => handleAction(showActionModal)}
                disabled={loading}
                className="flex-1 px-3 py-2 bg-primary text-white rounded-lg text-xs font-semibold hover:bg-primary-light transition-all cursor-pointer disabled:opacity-50"
              >
                Confirm
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

function ActionButton({ label, onClick, variant = "default" }) {
  const base = "px-2.5 py-1 rounded-lg text-[10px] font-medium transition-all cursor-pointer whitespace-nowrap";
  const styles = variant === "success"
    ? `${base} bg-primary/10 text-primary hover:bg-primary/20 border border-primary/20`
    : `${base} bg-surface-elevated text-muted-custom hover:text-heading border border-border-light`;
  return (
    <button onClick={onClick} className={styles}>
      {label}
    </button>
  );
}

function InfoItem({ label, value, mono = false }) {
  return (
    <div className="bg-surface-elevated rounded-lg p-2.5">
      <p className="text-[9px] text-muted-custom uppercase tracking-wider mb-0.5">{label}</p>
      <p className={`text-xs font-medium text-heading ${mono ? "font-mono" : ""}`}>{value}</p>
    </div>
  );
}
