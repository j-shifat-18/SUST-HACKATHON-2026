"use client";

import React, { useState } from "react";
import { PieChart, Pie, Sector, Cell, ResponsiveContainer } from "recharts";

const chartData = [
  { name: "Cash", value: 50000, color: "#22C55E" },
  { name: "bKash", value: 45000, color: "#E2125B" },
  { name: "Nagad", value: 35000, color: "#F04923" },
  { name: "Rocket", value: 25000, color: "#8C3494" }
];

const renderActiveShape = (props) => {
  const { cx, cy, innerRadius, outerRadius, startAngle, endAngle, fill } = props;
  return (
    <g>
      {/* Pop-out segment on hover */}
      <Sector
        cx={cx}
        cy={cy}
        innerRadius={innerRadius}
        outerRadius={outerRadius + 6}
        startAngle={startAngle}
        endAngle={endAngle}
        fill={fill}
      />
      {/* Double ring border */}
      <Sector
        cx={cx}
        cy={cy}
        startAngle={startAngle}
        endAngle={endAngle}
        innerRadius={outerRadius + 10}
        outerRadius={outerRadius + 14}
        fill={fill}
        opacity={0.3}
      />
    </g>
  );
};

export default function HomeView() {
  const [activeIndex, setActiveIndex] = useState(null);

  const onPieEnter = (_, index) => {
    setActiveIndex(index);
  };

  const onPieLeave = () => {
    setActiveIndex(null);
  };

  const total = chartData.reduce((sum, item) => sum + item.value, 0);

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
            <div className="text-2xl font-bold text-heading">৳ 50,000</div>
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

      {/* Dynamic Recharts Pie/Donut Chart */}
      <div className="bg-surface border border-border-custom rounded-xl p-6 shadow-sm flex flex-col items-center justify-center">
        <h3 className="text-sm font-bold text-heading uppercase tracking-wide mb-6 w-full text-left">Liquidity Distribution</h3>
        
        {/* Recharts Container with reduced width */}
        <div className="relative w-full max-w-[280px] aspect-square flex justify-center items-center">
          <ResponsiveContainer width="100%" height="100%">
            <PieChart>
              <Pie
                activeIndex={activeIndex}
                activeShape={renderActiveShape}
                data={chartData}
                cx="50%"
                cy="50%"
                innerRadius="65%"
                outerRadius="80%"
                dataKey="value"
                onMouseEnter={onPieEnter}
                onMouseLeave={onPieLeave}
              >
                {chartData.map((entry, index) => (
                  <Cell key={`cell-${index}`} fill={entry.color} style={{ outline: "none" }} />
                ))}
              </Pie>
            </PieChart>
          </ResponsiveContainer>

          {/* Absolute centered labels */}
          <div className="absolute inset-0 flex flex-col items-center justify-center text-center pointer-events-none p-4">
            {activeIndex === null || activeIndex === -1 ? (
              <>
                <span className="text-[10px] text-muted-custom font-extrabold uppercase tracking-widest mb-0.5">
                  Total Amount
                </span>
                <span className="text-lg font-black text-heading leading-tight">
                  ৳{total.toLocaleString()}
                </span>
              </>
            ) : (
              <>
                <span className="text-[10px] font-extrabold uppercase tracking-widest mb-0.5" style={{ color: chartData[activeIndex].color }}>
                  {chartData[activeIndex].name}
                </span>
                <span className="text-lg font-black text-heading leading-tight">
                  ৳{chartData[activeIndex].value.toLocaleString()}
                </span>
                <span className="text-[9px] text-muted-custom font-semibold mt-1 bg-slate-50 border border-border-custom px-1.5 py-0.5 rounded-full">
                  {((chartData[activeIndex].value / total) * 100).toFixed(1)}% Share
                </span>
              </>
            )}
          </div>
        </div>

      </div>

    </div>
  );
}
