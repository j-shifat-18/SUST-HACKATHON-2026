"use client";

import React from "react";
import { useDashboard } from "../context/DashboardContext";

export default function SidebarSimulator() {
  const {
    activeScenario,
    simulationSpeed,
    setSimulationSpeed,
    triggerScenario,
    resetSimulation
  } = useDashboard();

  return (
    <div className="bg-zinc-900 border-l border-zinc-800 w-80 p-6 flex flex-col justify-between overflow-y-auto">
      <div>
        <div className="flex items-center gap-2 mb-6">
          <span className="w-2.5 h-2.5 rounded-full bg-emerald-500 animate-pulse"></span>
          <h3 className="text-sm font-semibold tracking-wider text-zinc-400 uppercase">Simulation Control</h3>
        </div>

        {/* Active Scenario Indicator */}
        <div className="mb-6 p-4 rounded-xl bg-zinc-800/40 border border-zinc-800">
          <p className="text-xs text-zinc-500 mb-1">Active Scenario</p>
          <p className="text-sm font-medium text-white">
            {activeScenario === "A" && "Scenario A: bKash E-Money Expiry"}
            {activeScenario === "B" && "Scenario B: Split Transactions Anomaly"}
            {activeScenario === "C" && "Scenario C: Rocket Feed Delay"}
            {activeScenario === "D" && "Scenario D: Coordinated Escalation"}
            {!activeScenario && "Default Stable Flow"}
          </p>
        </div>

        {/* Preset Triggers */}
        <div className="space-y-3 mb-6">
          <p className="text-xs font-semibold text-zinc-400">Trigger Demonstration Scenarios</p>
          
          <button
            onClick={() => triggerScenario("A")}
            className={`w-full text-left p-3 rounded-lg border text-xs transition-all ${
              activeScenario === "A"
                ? "bg-rose-950/40 border-rose-500 text-rose-200"
                : "bg-zinc-800/30 border-zinc-700/50 hover:bg-zinc-800 text-zinc-300 hover:text-white"
            }`}
          >
            <div className="font-semibold mb-1">Scenario A: Hidden Shortage</div>
            <div className="text-[10px] text-zinc-500">
              bKash balance drops rapidly, triggering Bangla liquidity alerts.
            </div>
          </button>

          <button
            onClick={() => triggerScenario("B")}
            className={`w-full text-left p-3 rounded-lg border text-xs transition-all ${
              activeScenario === "B"
                ? "bg-amber-950/40 border-amber-500 text-amber-200"
                : "bg-zinc-800/30 border-zinc-700/50 hover:bg-zinc-800 text-zinc-300 hover:text-white"
            }`}
          >
            <div className="font-semibold mb-1">Scenario B: Anomaly + Cash Drop</div>
            <div className="text-[10px] text-zinc-500">
              Split transaction pattern flagged. Physical cash reserve falls under safe limit.
            </div>
          </button>

          <button
            onClick={() => triggerScenario("C")}
            className={`w-full text-left p-3 rounded-lg border text-xs transition-all ${
              activeScenario === "C"
                ? "bg-sky-950/40 border-sky-500 text-sky-200"
                : "bg-zinc-800/30 border-zinc-700/50 hover:bg-zinc-800 text-zinc-300 hover:text-white"
            }`}
          >
            <div className="font-semibold mb-1">Scenario C: Rocket Feed Delay</div>
            <div className="text-[10px] text-zinc-500">
              Simulates Rocket API delay. Reduces data confidence indicator.
            </div>
          </button>

          <button
            onClick={() => triggerScenario("D")}
            className={`w-full text-left p-3 rounded-lg border text-xs transition-all ${
              activeScenario === "D"
                ? "bg-indigo-950/40 border-indigo-500 text-indigo-200"
                : "bg-zinc-800/30 border-zinc-700/50 hover:bg-zinc-800 text-zinc-300 hover:text-white"
            }`}
          >
            <div className="font-semibold mb-1">Scenario D: Coordinated Support</div>
            <div className="text-[10px] text-zinc-500">
              Triggers a case routed to Field Officer for rebalancing.
            </div>
          </button>
        </div>

        {/* Speed Adjustment */}
        <div className="mb-6 space-y-2">
          <p className="text-xs font-semibold text-zinc-400">Simulation Speed</p>
          <div className="grid grid-cols-3 gap-2">
            {[
              { label: "Paused", value: 0 },
              { label: "1x", value: 1 },
              { label: "4x", value: 4 }
            ].map(speed => (
              <button
                key={speed.value}
                onClick={() => setSimulationSpeed(speed.value)}
                className={`py-1.5 rounded text-xs transition-colors ${
                  simulationSpeed === speed.value
                    ? "bg-white text-black font-semibold"
                    : "bg-zinc-850 hover:bg-zinc-800 text-zinc-400 hover:text-white"
                }`}
              >
                {speed.label}
              </button>
            ))}
          </div>
        </div>
      </div>

      <button
        onClick={resetSimulation}
        className="w-full bg-zinc-800 hover:bg-zinc-700 text-white font-medium py-2.5 rounded-lg text-xs transition-colors border border-zinc-750"
      >
        Reset Simulation
      </button>
    </div>
  );
}
