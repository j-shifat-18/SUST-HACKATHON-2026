"use client";

import React, { createContext, useContext, useState, useEffect, useCallback } from "react";
import { API_BASE_URL } from "../config";
import { auth } from "../../firebase/firebase.init";

const DashboardContext = createContext();

export function DashboardProvider({ children, userProfile }) {
  const [snapshot, setSnapshot] = useState(null);
  const [alerts, setAlerts] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const getToken = async () => {
    if (auth?.currentUser) {
      return await auth.currentUser.getIdToken();
    }
    return null;
  };

  const fetchWithAuth = useCallback(async (url, options = {}) => {
    const token = await getToken();
    const headers = {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...options.headers,
    };
    const response = await fetch(`${API_BASE_URL}${url}`, { ...options, headers });
    if (!response.ok) {
      const errData = await response.json().catch(() => ({}));
      throw new Error(errData.detail || errData.error?.message || `Request failed: ${response.status}`);
    }
    return response.json();
  }, []);

  // Fetch snapshot for an agent
  const fetchSnapshot = useCallback(async (agentId) => {
    setLoading(true);
    setError(null);
    try {
      const data = await fetchWithAuth(`/api/v1/snapshot/${agentId}`, { method: "POST" });
      setSnapshot(data);
      return data;
    } catch (err) {
      setError(err.message);
      return null;
    } finally {
      setLoading(false);
    }
  }, [fetchWithAuth]);

  // Fetch alerts
  const fetchAlerts = useCallback(async (statusFilter = "open", agentId = null) => {
    try {
      let url = `/api/v1/alerts?status_filter=${statusFilter}`;
      if (agentId) url += `&agent_id=${agentId}`;
      const data = await fetchWithAuth(url);
      setAlerts(data.alerts || []);
      return data;
    } catch (err) {
      setError(err.message);
      return { alerts: [], total: 0 };
    }
  }, [fetchWithAuth]);

  // Alert transitions
  const acknowledgeAlert = useCallback(async (alertId, note = "") => {
    return fetchWithAuth(`/api/v1/alerts/${alertId}/acknowledge`, {
      method: "POST",
      body: JSON.stringify({ note }),
    });
  }, [fetchWithAuth]);

  const escalateAlert = useCallback(async (alertId, note = "") => {
    return fetchWithAuth(`/api/v1/alerts/${alertId}/escalate`, {
      method: "POST",
      body: JSON.stringify({ note }),
    });
  }, [fetchWithAuth]);

  const resolveAlert = useCallback(async (alertId, note = "") => {
    return fetchWithAuth(`/api/v1/alerts/${alertId}/resolve`, {
      method: "POST",
      body: JSON.stringify({ note }),
    });
  }, [fetchWithAuth]);

  return (
    <DashboardContext.Provider
      value={{
        snapshot,
        alerts,
        loading,
        error,
        userProfile,
        fetchSnapshot,
        fetchAlerts,
        acknowledgeAlert,
        escalateAlert,
        resolveAlert,
        fetchWithAuth,
      }}
    >
      {children}
    </DashboardContext.Provider>
  );
}

export function useDashboard() {
  const context = useContext(DashboardContext);
  if (!context) {
    throw new Error("useDashboard must be used within a DashboardProvider");
  }
  return context;
}
