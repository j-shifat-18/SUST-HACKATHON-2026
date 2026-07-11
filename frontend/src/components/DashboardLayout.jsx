"use client";

import React, { useState } from "react";
import { Home, AlertTriangle, ClipboardList, Briefcase, BarChart3 } from "lucide-react";
import HomeView from "./HomeView";
import AlertView from "./AlertView";
import HistoryView from "./HistoryView";
import CaseView from "./CaseView";
import AnalyticsView from "./AnalyticsView";

export default function DashboardLayout() {
  const [activeTab, setActiveTab] = useState("Home");

  // Navigation tabs
  const navigationItems = [
    { name: "Home", icon: <Home size={18} /> },
    { name: "Alerts", icon: <AlertTriangle size={18} /> },
    { name: "Transaction History", icon: <ClipboardList size={18} /> },
    { name: "Case Management", icon: <Briefcase size={18} /> },
    { name: "Analytics", icon: <BarChart3 size={18} /> }
  ];


  // Render active component
  const renderContent = () => {
    switch (activeTab) {
      case "Home":
        return <HomeView />;
      case "Alerts":
        return <AlertView />;
      case "Transaction History":
        return <HistoryView />;
      case "Case Management":
        return <CaseView />;
      case "Analytics":
        return <AnalyticsView />;
      default:
        return <HomeView />;
    }
  };

  return (
    <div className="flex h-screen bg-background text-text-main overflow-hidden font-sans">
      {/* Left Sidebar */}
      <aside className="w-64 bg-surface border-r border-border-custom flex flex-col justify-between shrink-0">
        <div>
          {/* Header Branding */}
          <div className="h-16 flex items-center px-6 border-b border-border-custom">
            <span className="text-xl font-bold tracking-wider text-black bg-clip-text">
              CashScope
            </span>
          </div>

          {/* Navigation Links */}
          <nav className="p-4 space-y-1">
            {navigationItems.map((item) => (
              <button
                key={item.name}
                onClick={() => setActiveTab(item.name)}
                className={`w-full flex items-center gap-3 px-4 py-3 rounded-lg text-sm font-medium transition-all ${
                  activeTab === item.name
                    ? "bg-slate-100 text-secondary font-semibold border-l-2 border-secondary"
                    : "text-muted-custom hover:bg-slate-50 hover:text-heading"
                }`}
              >
                <span className="text-lg">{item.icon}</span>
                <span>{item.name}</span>
              </button>
            ))}
          </nav>
        </div>

        {/* Sidebar Footer */}
        <div className="p-4 border-t border-border-custom text-center text-xs text-muted-custom">
          © 2026 CashScope System
        </div>
      </aside>

      {/* Main Content Area */}
      <main className="flex-1 flex flex-col min-w-0 overflow-hidden">
        {/* Top Navbar */}
        <header className="h-16 border-b border-border-custom flex items-center justify-between px-8 bg-surface/80 backdrop-blur-md shrink-0">
          <div>
            <h2 className="text-sm font-semibold text-muted-custom">
              Dashboard / <span className="text-heading font-bold">{activeTab}</span>
            </h2>
          </div>
          <div className="flex items-center gap-4">
            <div className="w-8 h-8 rounded-full bg-secondary/10 flex items-center justify-center font-bold text-xs text-secondary">
              FO
            </div>
            <span className="text-xs font-semibold text-muted-custom">Field Officer Dashboard</span>
          </div>
        </header>

        {/* Viewport content */}
        <div className="flex-1 overflow-y-auto p-8">
          {renderContent()}
        </div>
      </main>
    </div>
  );
}
