"use client";

import React, { createContext, useContext, useState, useEffect, useRef } from "react";

const DashboardContext = createContext();

// Initial seed data
const initialProviders = {
  bkash: { id: "bkash", name: "bKash", balance: 45000, logoColor: "#E2125B", limit: 100000, demandRate: 1 },
  nagad: { id: "nagad", name: "Nagad", balance: 35000, logoColor: "#F04923", limit: 100000, demandRate: 1 },
  rocket: { id: "rocket", name: "Rocket", balance: 25000, logoColor: "#8C3494", limit: 100000, demandRate: 1 }
};

const initialCashDrawer = {
  physicalCash: 50000,
  safeThreshold: 15000,
  confidence: 1.0, // 0.0 to 1.0 (drops on data inconsistency)
  status: "Normal" // Normal, Warning, Critical, Inconsistent
};

const initialTransactions = [
  { id: "TX1001", time: "13:15:02", provider: "bkash", type: "Cash-in", amount: 5000, account: "0175***981", status: "Success", confidence: 1.0 },
  { id: "TX1002", time: "13:12:45", provider: "nagad", type: "Cash-out", amount: 12000, account: "0191***432", status: "Success", confidence: 1.0 },
  { id: "TX1003", time: "13:10:10", provider: "rocket", type: "Cash-out", amount: 8000, account: "0152***119", status: "Success", confidence: 1.0 },
  { id: "TX1004", time: "13:05:00", provider: "bkash", type: "Cash-out", amount: 15000, account: "0183***872", status: "Success", confidence: 1.0 },
  { id: "TX1005", time: "13:00:23", provider: "nagad", type: "Cash-in", amount: 2000, account: "0171***555", status: "Success", confidence: 1.0 }
];

const initialAlerts = [
  {
    id: "ALT-001",
    time: "13:12:45",
    type: "Liquidity Warning",
    provider: "nagad",
    title: "Upcoming Nagad E-Money Shortage",
    titleBn: "নগদ ই-মানি ঘাটতি সতর্কতা",
    severity: "Warning",
    description: "Nagad balance is projected to run out in 45 minutes due to high Cash-out volume.",
    descriptionBn: "চলতি ক্যাশ-আউটের চাপ বজায় থাকলে আগামী ৪৫ মিনিটের মধ্যে আপনার নগদ ই-মানি শেষ হয়ে যেতে পারে।",
    evidence: "Average transaction rate increased by 230% in last 30 minutes.",
    uncertainty: "Low (85% confidence)",
    owner: "Agent",
    status: "Active"
  }
];

const initialCases = [
  {
    id: "CASE-001",
    alertId: "ALT-001",
    title: "Nagad Liquidity Shortage Support",
    provider: "nagad",
    status: "New",
    owner: "Central Operations",
    assignee: "Unassigned",
    escalationPath: "Agent -> Territory Officer -> Central Ops",
    timeline: [
      { time: "13:12:45", action: "Case Created", actor: "System", notes: "Case auto-generated from Liquidity Warning alert." }
    ]
  }
];

export function DashboardProvider({ children }) {
  const [providers, setProviders] = useState(initialProviders);
  const [cashDrawer, setCashDrawer] = useState(initialCashDrawer);
  const [transactions, setTransactions] = useState(initialTransactions);
  const [alerts, setAlerts] = useState(initialAlerts);
  const [cases, setCases] = useState(initialCases);
  const [activeScenario, setActiveScenario] = useState(null);
  const [simulationSpeed, setSimulationSpeed] = useState(1); // 0 = paused, 1 = normal, 2 = fast
  
  // Custom metrics for evaluation dashboard
  const [metrics, setMetrics] = useState({
    avgLeadTime: "35 mins",
    anomalyPrecision: "92%",
    falsePositiveRate: "4.5%",
    apiLatency: "45ms",
    activeDelay: false
  });

  // Background mock transaction generator
  useEffect(() => {
    if (simulationSpeed === 0) return;

    const interval = setInterval(() => {
      // 1. Generate random normal transaction or follow scenario behavior
      if (activeScenario === "A") {
        // Scenario A: Rapid bKash Cash-out. Shrink bKash balance and physical cash
        setProviders(prev => {
          const newBal = Math.max(0, prev.bkash.balance - 4000);
          return {
            ...prev,
            bkash: { ...prev.bkash, balance: newBal }
          };
        });
        setCashDrawer(prev => {
          const newCash = Math.max(0, prev.physicalCash - 4000);
          return {
            ...prev,
            physicalCash: newCash,
            status: newCash < prev.safeThreshold ? "Critical" : "Warning"
          };
        });
        // Append transaction
        const newTx = {
          id: `TX${Math.floor(1000 + Math.random() * 9000)}`,
          time: new Date().toTimeString().split(" ")[0],
          provider: "bkash",
          type: "Cash-out",
          amount: 4000,
          account: `0171***${Math.floor(100 + Math.random() * 900)}`,
          status: "Success",
          confidence: 1.0
        };
        setTransactions(prev => [newTx, ...prev.slice(0, 19)]);
      } else if (activeScenario === "B") {
        // Scenario B: Repeat transaction anomaly + cash falling rapidly
        setProviders(prev => {
          const newBal = Math.max(0, prev.bkash.balance - 10000);
          return {
            ...prev,
            bkash: { ...prev.bkash, balance: newBal }
          };
        });
        setCashDrawer(prev => {
          const newCash = Math.max(0, prev.physicalCash - 10000);
          return {
            ...prev,
            physicalCash: newCash,
            status: newCash < prev.safeThreshold ? "Critical" : "Warning"
          };
        });
        // Create 2 identical transactions to simulate splitting/anomalies
        const timeStr = new Date().toTimeString().split(" ")[0];
        const newTxs = Array.from({ length: 2 }).map((_, i) => ({
          id: `TX${Math.floor(1000 + Math.random() * 9000) + i}`,
          time: timeStr,
          provider: "bkash",
          type: "Cash-out",
          amount: 10000,
          account: "0172***441", // identical account
          status: "Success",
          confidence: 0.9
        }));
        setTransactions(prev => [...newTxs, ...prev.slice(0, 19)]);
      } else {
        // Default random flow: stable
        const randProvider = ["bkash", "nagad", "rocket"][Math.floor(Math.random() * 3)];
        const randType = Math.random() > 0.4 ? "Cash-out" : "Cash-in";
        const randAmount = Math.floor(1000 + Math.random() * 15000);

        setProviders(prev => {
          const currentProv = prev[randProvider];
          let newBal = currentProv.balance;
          if (randType === "Cash-in") {
            newBal = Math.max(0, currentProv.balance - randAmount);
          } else {
            newBal = Math.min(currentProv.limit, currentProv.balance + randAmount);
          }
          return {
            ...prev,
            [randProvider]: { ...currentProv, balance: newBal }
          };
        });

        setCashDrawer(prev => {
          let newCash = prev.physicalCash;
          if (randType === "Cash-in") {
            newCash += randAmount;
          } else {
            newCash = Math.max(0, prev.physicalCash - randAmount);
          }
          return {
            ...prev,
            physicalCash: newCash,
            status: newCash < prev.safeThreshold ? "Warning" : "Normal"
          };
        });

        const newTx = {
          id: `TX${Math.floor(1000 + Math.random() * 9000)}`,
          time: new Date().toTimeString().split(" ")[0],
          provider: randProvider,
          type: randType,
          amount: randAmount,
          account: `0171***${Math.floor(100 + Math.random() * 900)}`,
          status: "Success",
          confidence: 1.0
        };
        setTransactions(prev => [newTx, ...prev.slice(0, 19)]);
      }
    }, 5000 / simulationSpeed);

    return () => clearInterval(interval);
  }, [activeScenario, simulationSpeed]);

  // Trigger specific scenarios
  const triggerScenario = (scenario) => {
    setActiveScenario(scenario);

    if (scenario === "A") {
      setProviders(prev => ({
        ...prev,
        bkash: { ...prev.bkash, balance: 8000 }
      }));
      const newAlert = {
        id: `ALT-${Date.now()}`,
        time: new Date().toTimeString().split(" ")[0],
        type: "Liquidity Warning",
        provider: "bkash",
        title: "bKash E-Money Expiration Alert",
        titleBn: "বিকাশ ই-মানি ফুরিয়ে যাওয়ার সতর্কতা",
        severity: "Critical",
        description: "bKash e-money balance will run out in approximately 12 minutes due to intense cash-out rate.",
        descriptionBn: "বর্তমান ক্যাশ-আউটের ধারা অনুযায়ী ১২ মিনিটের মধ্যে আপনার বিকাশ ই-মানি শেষ হয়ে যেতে পারে।",
        evidence: "bKash cash-out volume is 5x normal level. Total demand forecast exceeds reserve by 23,000 BDT.",
        uncertainty: "Very Low (95% confidence)",
        owner: "Agent",
        status: "Active"
      };
      setAlerts(prev => [newAlert, ...prev]);

      const newCase = {
        id: `CASE-${Date.now()}`,
        alertId: newAlert.id,
        title: "bKash Impending Liquidity Deficit",
        provider: "bkash",
        status: "New",
        owner: "Territory Officer",
        assignee: "Unassigned",
        escalationPath: "Agent -> Territory Officer -> District Manager",
        timeline: [
          { time: newAlert.time, action: "Case Created", actor: "System", notes: "Liquidity threshold breach on bKash provider." }
        ]
      };
      setCases(prev => [newCase, ...prev]);

    } else if (scenario === "B") {
      setCashDrawer(prev => ({
        ...prev,
        physicalCash: 12000,
        status: "Critical"
      }));
      const newAlert = {
        id: `ALT-${Date.now()}`,
        time: new Date().toTimeString().split(" ")[0],
        type: "Unusual Pattern",
        provider: "bkash",
        title: "Suspected Split Transactions on bKash",
        titleBn: "অস্বাভাবিক লেনদেন প্যাটার্ন সতর্কতা",
        severity: "Critical",
        description: "Velocity spike of identical transactions (10,000 BDT) from a single account within 3 minutes.",
        descriptionBn: "গত ৩ মিনিটে একই অ্যাকাউন্ট থেকে পর পর ১০,০০০ টাকার ক্যাশ-আউট করা হয়েছে। এটি স্বাভাবিক ঈদ ভিড় হতে পারে, তবে যাচাই করা প্রয়োজন।",
        evidence: "2 repetitive high-value cash-out requests. Cash drawer reserve falling at 25,000 BDT/hour.",
        uncertainty: "Medium (70% confidence - potential legitimate Eid spike)",
        owner: "Risk Analyst",
        status: "Active"
      };
      setAlerts(prev => [newAlert, ...prev]);

      const newCase = {
        id: `CASE-${Date.now()}`,
        alertId: newAlert.id,
        title: "bKash Velocity / Split Pattern Review",
        provider: "bkash",
        status: "New",
        owner: "Risk Analyst",
        assignee: "Unassigned",
        escalationPath: "Central Ops -> Risk Analyst -> Compliance",
        timeline: [
          { time: newAlert.time, action: "Escalated to Risk Analyst", actor: "System", notes: "Identified transaction split sequence." }
        ]
      };
      setCases(prev => [newCase, ...prev]);

    } else if (scenario === "C") {
      setCashDrawer(prev => ({
        ...prev,
        confidence: 0.4,
        status: "Inconsistent"
      }));
      setMetrics(prev => ({
        ...prev,
        apiLatency: "4800ms",
        activeDelay: true
      }));

      const newAlert = {
        id: `ALT-${Date.now()}`,
        time: new Date().toTimeString().split(" ")[0],
        type: "Data Inconsistency",
        provider: "rocket",
        title: "Rocket Feed Interrupted / Delayed",
        titleBn: "রকেট ডাটা ফিড বিলম্বজনিত বিভ্রাট",
        severity: "Warning",
        description: "Electronic feed delayed by > 45 seconds. Balance accuracy cannot be guaranteed.",
        descriptionBn: "রকেট ডাটা ফিডে কারিগরি বিলম্ব দেখা দিয়েছে। প্রদর্শিত ব্যালেন্সটি সঠিক নাও হতে পারে।",
        evidence: "API handshake timed out. Displaying cached balance from 13:00:23.",
        uncertainty: "High Uncertainty (Displaying safe fallback data)",
        owner: "Agent",
        status: "Active"
      };
      setAlerts(prev => [newAlert, ...prev]);
    } else if (scenario === "D") {
      const newAlert = {
        id: `ALT-D-01`,
        time: new Date().toTimeString().split(" ")[0],
        type: "Liquidity Warning",
        provider: "rocket",
        title: "Rocket Liquidity Support Needed",
        titleBn: "রকেট লিকুইডিটি সহায়তা প্রয়োজন",
        severity: "Critical",
        description: "Rocket e-money balance depleted. Agent cannot serve cash-out requests.",
        descriptionBn: "রকেট ই-মানি শেষ হয়ে গেছে। গ্রাহকদের সেবা সচল রাখতে দ্রুত রিফিল করা প্রয়োজন।",
        evidence: "Multiple unsuccessful Rocket cash-outs logged due to zero balance.",
        uncertainty: "Zero uncertainty (Actual balance limit reached)",
        owner: "Field Officer",
        status: "Active"
      };
      setAlerts(prev => [newAlert, ...prev]);

      const newCase = {
        id: `CASE-D-01`,
        alertId: newAlert.id,
        title: "Rocket Urgent Rebalancing Support",
        provider: "rocket",
        status: "New",
        owner: "Field Officer",
        assignee: "Territory Officer Didar",
        escalationPath: "Agent -> Territory Officer -> Branch Lead",
        timeline: [
          { time: newAlert.time, action: "Assigned to Didar", actor: "System", notes: "Auto-allocated to nearest field officer based on geolocation." }
        ]
      };
      setCases(prev => [newCase, ...prev]);
    }
  };

  const resetSimulation = () => {
    setActiveScenario(null);
    setProviders(initialProviders);
    setCashDrawer(initialCashDrawer);
    setTransactions(initialTransactions);
    setAlerts(initialAlerts);
    setCases(initialCases);
    setMetrics({
      avgLeadTime: "35 mins",
      anomalyPrecision: "92%",
      falsePositiveRate: "4.5%",
      apiLatency: "45ms",
      activeDelay: false
    });
  };

  const updateCaseStatus = (caseId, status, actor, notes) => {
    setCases(prev => prev.map(c => {
      if (c.id === caseId) {
        return {
          ...c,
          status: status,
          timeline: [...c.timeline, { time: new Date().toTimeString().split(" ")[0], action: `Status changed to ${status}`, actor, notes }]
        };
      }
      return c;
    }));
  };

  const addCaseComment = (caseId, actor, notes) => {
    setCases(prev => prev.map(c => {
      if (c.id === caseId) {
        return {
          ...c,
          timeline: [...c.timeline, { time: new Date().toTimeString().split(" ")[0], action: "Comment Added", actor, notes }]
        };
      }
      return c;
    }));
  };

  const reallocateBalance = (provider, amount) => {
    setProviders(prev => {
      const current = prev[provider];
      return {
        ...prev,
        [provider]: { ...current, balance: current.balance + amount }
      };
    });
  };

  const setManualCash = (amount) => {
    setCashDrawer(prev => ({
      ...prev,
      physicalCash: amount,
      status: amount < prev.safeThreshold ? "Warning" : "Normal"
    }));
  };

  return (
    <DashboardContext.Provider value={{
      providers,
      cashDrawer,
      transactions,
      alerts,
      cases,
      metrics,
      activeScenario,
      simulationSpeed,
      setSimulationSpeed,
      triggerScenario,
      resetSimulation,
      updateCaseStatus,
      addCaseComment,
      reallocateBalance,
      setManualCash
    }}>
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
