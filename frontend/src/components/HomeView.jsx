"use client";

import React from "react";
import { AlertTriangle, CheckCircle } from "lucide-react";

export default function HomeView() {
  return (
    <div className="space-y-6">
      {/* Overview Title block */}
      <div className="border-b border-border-custom pb-4">
        <h1 className="text-2xl font-bold tracking-tight text-heading">Dashboard Overview</h1>
      </div>

      {/* Grid containing balance balances */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
        {/* Shared physical cash drawer */}
        <div className="bg-surface border border-border-custom rounded-xl p-5 flex flex-col justify-between shadow-sm">
          <div>
            <div className="flex justify-between items-center text-muted-custom font-bold uppercase tracking-wider text-[10px] mb-2">
              <span>Cash</span>
            </div>
            <div className="text-2xl font-extrabold text-heading">৳ 50,000</div>
          </div>
          <div className="mt-4 w-full bg-slate-100 h-1.5 rounded-full overflow-hidden">
            <div className="bg-success-custom h-full w-[60%]"></div>
          </div>
        </div>

        {/* bKash card */}
        <div className="bg-surface border border-border-custom rounded-xl p-5 flex flex-col justify-between relative overflow-hidden shadow-sm">
          <div className="absolute top-0 left-0 right-0 h-1 bg-pink-600"></div>
          <div>
            <div className="flex justify-between items-center text-[10px] mb-2 font-bold tracking-wider uppercase text-pink-500">
              <span>bKash</span>
            </div>
            <div className="text-2xl font-bold text-heading">৳ 45,000</div>
          </div>
          <div className="mt-4 w-full bg-slate-100 h-1 rounded-full overflow-hidden">
            <div className="bg-pink-600 h-full w-[45%]"></div>
          </div>
        </div>

        {/* Nagad card */}
        <div className="bg-surface border border-border-custom rounded-xl p-5 flex flex-col justify-between relative overflow-hidden shadow-sm">
          <div className="absolute top-0 left-0 right-0 h-1 bg-orange-500"></div>
          <div>
            <div className="flex justify-between items-center text-[10px] mb-2 font-bold tracking-wider uppercase text-orange-500">
              <span>Nagad</span>
            </div>
            <div className="text-2xl font-bold text-heading">৳ 35,000</div>
          </div>
          <div className="mt-4 w-full bg-slate-100 h-1 rounded-full overflow-hidden">
            <div className="bg-orange-500 h-full w-[35%]"></div>
          </div>
        </div>

        {/* Rocket card */}
        <div className="bg-surface border border-border-custom rounded-xl p-5 flex flex-col justify-between relative overflow-hidden shadow-sm">
          <div className="absolute top-0 left-0 right-0 h-1 bg-violet-600"></div>
          <div>
            <div className="flex justify-between items-center text-[10px] mb-2 font-bold tracking-wider uppercase text-violet-500">
              <span>Rocket</span>
            </div>
            <div className="text-2xl font-bold text-heading">৳ 25,000</div>
          </div>
          <div className="mt-4 w-full bg-slate-100 h-1 rounded-full overflow-hidden">
            <div className="bg-violet-600 h-full w-[25%]"></div>
          </div>
        </div>
      </div>
    </div>
  );
}
