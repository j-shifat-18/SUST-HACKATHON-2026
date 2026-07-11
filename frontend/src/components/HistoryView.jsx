"use client";

import React from "react";

export default function HistoryView() {
  const dummyTransactions = [
    { id: 1, provider: "bKash", type: "Cash-out", amount: 12000, timestamp: "2026-07-11 13:12:45" },
    { id: 2, provider: "Nagad", type: "Cash-in", amount: 5000, timestamp: "2026-07-11 13:08:20"},
    { id: 3, provider: "Rocket", type: "Cash-out", amount: 8000, timestamp: "2026-07-11 12:55:10"},
    { id: 4, provider: "bKash", type: "Cash-in", amount: 15000, timestamp: "2026-07-11 12:42:01"},
    { id: 5, provider: "Nagad", type: "Cash-out", amount: 3000, timestamp: "2026-07-11 12:30:15"},
    { id: 6, provider: "bKash", type: "Cash-out", amount: 10000, timestamp: "2026-07-11 12:15:00"}
  ];

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="border-b border-border-custom pb-4">
        <h1 className="text-2xl font-bold tracking-tight text-heading">Transaction History</h1>
      </div>

      {/* Transaction Table */}
      <div className="bg-surface border border-border-custom rounded-xl overflow-hidden shadow-sm text-xs">
        <table className="w-full text-left border-collapse">
          <thead>
            <tr className="bg-slate-50 text-muted-custom border-b border-border-custom font-bold uppercase tracking-wider">
              <th className="p-4">Provider</th>
              <th className="p-4">Transaction Type</th>
              <th className="p-4">Amount</th>
              <th className="p-4">Time</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-border-custom text-text-main">
            {dummyTransactions.map((tx) => (
              <tr key={tx.id} className="hover:bg-slate-50/50 transition-colors">
                {/* Provider with matching signature color */}
                <td className="p-4 font-bold">
                  <span className={tx.color}>{tx.provider}</span>
                </td>
                
                {/* Type Badge */}
                <td className="p-4">
                  <span className={`px-2 py-0.5 rounded-full text-[10px] font-bold ${
                    tx.type === "Cash-in" ? "bg-success-custom/10 text-success-custom" : "bg-info-custom/10 text-red-400"
                  }`}>
                    {tx.type}
                  </span>
                </td>
                
                {/* Amount */}
                <td className="p-4 font-bold text-heading">
                  ৳ {tx.amount.toLocaleString()}
                </td>
                
                {/* Timestamp */}
                <td className="p-4 text-muted-custom font-mono">
                  {tx.timestamp}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
