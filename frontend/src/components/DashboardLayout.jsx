"use client";

import React, { useState } from "react";
import { Home, AlertTriangle, ClipboardList, Briefcase, BarChart3, LogOut, Activity, Shield } from "lucide-react";
import { signOut } from "firebase/auth";
import { auth } from "../../firebase/firebase.init";
import HomeView from "./HomeView";
import AlertView from "./AlertView";
import HistoryView from "./HistoryView";
import CaseView from "./CaseView";
import AnalyticsView from "./AnalyticsView";
import { DashboardProvider } from "../context/DashboardContext";

export default function DashboardLayout({ userProfile }) {
  const [activeTab, setActiveTab] = useState("Home");

  const handleLogout = () => {
    signOut(auth).catch((err) => console.error("Sign out error", err));
  };

  const navigationItems = [
    { name: "Home", icon: Home },
    { name: "Alerts", icon: AlertTriangle },
    { name: "Transactions", icon: ClipboardList },
    { name: "Cases", icon: Briefcase },
    { name: "Analytics", icon: BarChart3 },
  ];

  const renderContent = () => {
    switch (activeTab) {
      case "Home":
        return <HomeView userProfile={userProfile} />;
      case "Alerts":
        return <AlertView userProfile={userProfile} />;
      case "Transactions":
        return <HistoryView userProfile={userProfile} />;
      case "Cases":
        return <CaseView userProfile={userProfile} />;
      case "Analytics":
        return <AnalyticsView userProfile={userProfile} />;
      default:
        return <HomeView userProfile={userProfile} />;
    }
  };

  return (
    <DashboardProvider userProfile={userProfile}>
      <div className="flex h-screen bg-background text-text-main overflow-hidden font-sans">
        {/* Sidebar */}
        <aside className="w-60 bg-surface border-r border-border-custom flex flex-col justify-between shrink-0">
          <div>
            <div className="h-16 flex items-center px-5 border-b border-border-custom gap-2">
              <Shield className="w-6 h-6 text-primary" />
              <span className="text-lg font-bold tracking-wide text-heading">CashScope</span>
            </div>

            <nav className="p-3 space-y-0.5 mt-2">
              {navigationItems.map((item) => {
                const Icon = item.icon;
                const isActive = activeTab === item.name;
                return (
                  <button
                    key={item.name}
                    onClick={() => setActiveTab(item.name)}
                    className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-all cursor-pointer ${
                      isActive
                        ? "bg-primary/10 text-primary border-l-2 border-primary"
                        : "text-muted-custom hover:bg-surface-elevated hover:text-heading"
                    }`}
                  >
                    <Icon size={18} />
                    <span>{item.name}</span>
                  </button>
                );
              })}
            </nav>
          </div>

          <div className="p-4 border-t border-border-custom">
            <div className="flex items-center gap-2 px-2 mb-3">
              <Activity size={12} className="text-primary" />
              <span className="text-[10px] text-muted-custom font-medium">System Active</span>
            </div>
            <p className="text-[10px] text-muted-custom text-center">© 2026 CashScope</p>
          </div>
        </aside>

        {/* Main */}
        <main className="flex-1 flex flex-col min-w-0 overflow-hidden">
          {/* Top bar */}
          <header className="h-14 border-b border-border-custom flex items-center justify-between px-6 bg-surface/80 backdrop-blur-md shrink-0">
            <div className="flex items-center gap-2">
              <span className="text-xs text-muted-custom">Dashboard</span>
              <span className="text-xs text-muted-custom">/</span>
              <span className="text-sm font-semibold text-heading">{activeTab}</span>
            </div>
            <div className="flex items-center gap-3">
              <div className="flex items-center gap-2">
                <div className="w-8 h-8 rounded-full bg-primary/15 flex items-center justify-center font-bold text-xs text-primary">
                  {userProfile.name.charAt(0).toUpperCase()}
                </div>
                <div className="flex flex-col">
                  <span className="text-xs font-semibold text-heading">{userProfile.name}</span>
                  <span className="text-[10px] text-muted-custom">
                    {userProfile.district}, {userProfile.division}
                  </span>
                </div>
              </div>
              <button
                onClick={handleLogout}
                className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg text-xs font-medium text-error-custom bg-error-custom/10 hover:bg-error-custom/20 transition-all border border-error-custom/20 cursor-pointer"
              >
                <LogOut size={13} />
                Logout
              </button>
            </div>
          </header>

          {/* Content */}
          <div className="flex-1 overflow-y-auto p-6">
            {renderContent()}
          </div>
        </main>
      </div>
    </DashboardProvider>
  );
}
