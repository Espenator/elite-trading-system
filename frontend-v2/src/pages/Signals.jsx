"use client";

import React, { useState, useEffect } from "react";
import {
  Zap,
  Activity,
  TrendingUp,
  TrendingDown,
  Target,
  Filter,
  Layers,
  BarChart2,
  ShieldAlert,
  Clock,
} from "lucide-react";
import PageHeader from "../components/ui/PageHeader";

export default function Signals() {
  const [activeFilter, setActiveFilter] = useState("ALL");
  const [lastScan, setLastScan] = useState(new Date());

  // Simulated WebSocket feed of real-time signals from backendrunner.py
  const mockSignals = [
    {
      id: "SIG-001",
      ticker: "RBRK",
      action: "LONG",
      type: "MOMENTUM_BREAKOUT",
      confidence: 92,
      tier: "SLAM DUNK",
      entry: 75.5,
      target: 81.2,
      stop: 62.0,
      factors: {
        velez: 94,
        williamsR: -82,
        volume: "300%",
        flow: "2.5M Calls (Ask)",
      },
      time: "Just now",
    },
    {
      id: "SIG-002",
      ticker: "PLTR",
      action: "LONG",
      type: "COILING_BASE",
      confidence: 88,
      tier: "SLAM DUNK",
      entry: 24.1,
      target: 26.5,
      stop: 22.8,
      factors: {
        velez: 87,
        williamsR: -78,
        volume: "180%",
        flow: "800k Calls",
      },
      time: "2 mins ago",
    },
    {
      id: "SIG-003",
      ticker: "SNOW",
      action: "SHORT",
      type: "MEAN_REVERSION",
      confidence: 76,
      tier: "STRONG GO",
      entry: 185.0,
      target: 172.0,
      stop: 191.5,
      factors: {
        velez: 72,
        williamsR: -15,
        volume: "120%",
        flow: "1.2M Puts",
      },
      time: "4 mins ago",
    },
    {
      id: "SIG-004",
      ticker: "CRWD",
      action: "LONG",
      type: "FRACTAL_BOUNCE",
      confidence: 65,
      tier: "WATCH",
      entry: null,
      target: null,
      stop: null,
      factors: {
        velez: 61,
        williamsR: -55,
        volume: "90%",
        flow: "Mixed",
      },
      time: "5 mins ago",
    },
  ];

  // Helper for Tier Colors
  const getTierColor = (tier) => {
    switch (tier) {
      case "SLAM DUNK":
        return "text-green-400 bg-green-400/10 border-green-500/50";
      case "STRONG GO":
        return "text-blue-400 bg-blue-400/10 border-blue-500/50";
      case "WATCH":
        return "text-yellow-400 bg-yellow-400/10 border-yellow-500/50";
      default:
        return "text-slate-400 bg-slate-400/10 border-slate-500/50";
    }
  };

  const filteredSignals =
    activeFilter === "ALL"
      ? mockSignals
      : mockSignals.filter((s) => s.action === activeFilter);

  return (
    <div className="space-y-6">
      <PageHeader
        icon={Zap}
        title="Live Signal Feed"
        description="Real-time Velez Momentum & Dark Pool Breakout Scanner"
      >
        <div className="text-right flex flex-col items-end gap-2">
          <div className="flex items-center gap-2 px-4 py-2 bg-slate-800/50 border border-slate-700/50 rounded-lg">
            <Activity className="w-4 h-4 text-blue-400 animate-pulse" />
            <span className="text-sm font-semibold text-white">
              Scanner Active (5m Interval)
            </span>
          </div>
          <p className="text-xs text-slate-500 flex items-center gap-1">
            <Clock className="w-3 h-3" /> Last Scan:{" "}
            {lastScan.toLocaleTimeString()}
          </p>
        </div>
      </PageHeader>

      {/* Control Panel */}
      <div className="flex flex-wrap items-center justify-between mb-6 p-4 bg-slate-800/40 border border-slate-700/50 rounded-xl backdrop-blur-md">
        <div className="flex gap-2">
          {["ALL", "LONG", "SHORT"].map((filter) => (
            <button
              key={filter}
              onClick={() => setActiveFilter(filter)}
              className={`px-4 py-2 rounded-lg text-sm font-bold transition-all ${
                activeFilter === filter
                  ? "bg-blue-600 text-white shadow-[0_0_15px_rgba(37,99,235,0.5)]"
                  : "bg-slate-800 text-slate-400 hover:bg-slate-700"
              }`}
            >
              {filter}
            </button>
          ))}
        </div>
        <div className="flex gap-4 text-sm">
          <span className="flex items-center gap-2 text-slate-300">
            <Filter className="w-4 h-4 text-slate-500" /> Velez Score &gt; 60
          </span>
          <span className="flex items-center gap-2 text-slate-300">
            <Layers className="w-4 h-4 text-slate-500" /> Volume Surge &gt; 150%
          </span>
        </div>
      </div>

      {/* Signal Feed Array */}
      <div className="space-y-4">
        {filteredSignals.map((signal) => (
          <div
            key={signal.id}
            className="group relative bg-slate-800/40 border border-slate-700/50 rounded-xl p-5 backdrop-blur-sm hover:border-blue-500/50 hover:bg-slate-800/60 transition-all duration-300 shadow-lg"
          >
            <div className="flex flex-col lg:flex-row items-center justify-between gap-6">
              {/* Left Column: Ticker & Main Action */}
              <div className="flex items-center gap-6 min-w-[250px]">
                <div
                  className={`p-4 rounded-xl flex items-center justify-center border ${
                    signal.action === "LONG"
                      ? "bg-green-900/20 border-green-500/30 text-green-400"
                      : "bg-red-900/20 border-red-500/30 text-red-400"
                  }`}
                >
                  {signal.action === "LONG" ? (
                    <TrendingUp className="w-8 h-8" />
                  ) : (
                    <TrendingDown className="w-8 h-8" />
                  )}
                </div>
                <div>
                  <h2 className="text-3xl font-bold text-white tracking-wider">
                    {signal.ticker}
                  </h2>
                  <div className="flex items-center gap-2 mt-1">
                    <span
                      className={`px-2 py-0.5 text-xs font-bold rounded border ${getTierColor(signal.tier)}`}
                    >
                      {signal.tier}
                    </span>
                    <span className="text-xs text-slate-400">
                      {signal.time}
                    </span>
                  </div>
                </div>
              </div>

              {/* Middle Column: Execution Data */}
              <div className="flex-1 grid grid-cols-3 gap-4 bg-slate-900/50 rounded-lg p-3 border border-slate-700/30 w-full lg:w-auto">
                <div className="flex flex-col">
                  <span className="text-xs text-slate-500 mb-1">Entry</span>
                  <span className="text-lg text-white">
                    {signal.entry ? `$${signal.entry.toFixed(2)}` : "Wait"}
                  </span>
                </div>
                <div className="flex flex-col border-l border-slate-700/50 pl-4">
                  <span className="text-xs text-slate-500 mb-1">
                    Target (1R)
                  </span>
                  <span className="text-lg text-green-400">
                    {signal.target ? `$${signal.target.toFixed(2)}` : "--"}
                  </span>
                </div>
                <div className="flex flex-col border-l border-slate-700/50 pl-4">
                  <span className="text-xs text-slate-500 mb-1">
                    Stop (2.5 ATR)
                  </span>
                  <span className="text-lg text-red-400">
                    {signal.stop ? `$${signal.stop.toFixed(2)}` : "--"}
                  </span>
                </div>
              </div>

              {/* Right Column: Factor Breakdown & Confidence */}
              <div className="flex items-center gap-6 min-w-[300px] w-full lg:w-auto">
                <div className="grid grid-cols-2 gap-x-6 gap-y-2 text-sm w-full">
                  <div className="flex justify-between items-center">
                    <span className="text-slate-500 text-xs">Velez v2.0</span>
                    <span
                      className={`font-bold ${signal.factors.velez >= 80 ? "text-green-400" : "text-yellow-400"}`}
                    >
                      {signal.factors.velez}/100
                    </span>
                  </div>
                  <div className="flex justify-between items-center">
                    <span className="text-slate-500 text-xs">Will %R</span>
                    <span className="font-bold text-white">
                      {signal.factors.williamsR}
                    </span>
                  </div>
                  <div className="flex justify-between items-center">
                    <span className="text-slate-500 text-xs">Vol Surge</span>
                    <span className="font-bold text-blue-400">
                      {signal.factors.volume}
                    </span>
                  </div>
                  <div className="flex justify-between items-center">
                    <span className="text-slate-500 text-xs">Whale Flow</span>
                    <span
                      className="font-bold text-purple-400 truncate max-w-[80px]"
                      title={signal.factors.flow}
                    >
                      {signal.factors.flow}
                    </span>
                  </div>
                </div>

                {/* Circular Confidence Gauge */}
                <div className="flex flex-col items-center justify-center relative w-16 h-16 shrink-0">
                  <svg className="w-16 h-16 transform -rotate-90">
                    <circle
                      cx="32"
                      cy="32"
                      r="28"
                      stroke="currentColor"
                      strokeWidth="4"
                      fill="transparent"
                      className="text-slate-700"
                    />
                    <circle
                      cx="32"
                      cy="32"
                      r="28"
                      stroke="currentColor"
                      strokeWidth="4"
                      fill="transparent"
                      strokeDasharray="175.9"
                      strokeDashoffset={
                        175.9 - (175.9 * signal.confidence) / 100
                      }
                      className={
                        signal.confidence >= 80
                          ? "text-green-500"
                          : signal.confidence >= 60
                            ? "text-yellow-500"
                            : "text-red-500"
                      }
                    />
                  </svg>
                  <div className="absolute flex flex-col items-center justify-center">
                    <span className="text-sm font-bold text-white">
                      {signal.confidence}%
                    </span>
                  </div>
                </div>
              </div>

              {/* Action Button */}
              <div className="shrink-0">
                <button
                  disabled={signal.tier === "WATCH"}
                  className={`px-6 py-3 rounded-lg font-bold transition-all flex items-center gap-2 ${
                    signal.tier === "WATCH"
                      ? "bg-slate-800 text-slate-500 cursor-not-allowed border border-slate-700"
                      : "bg-blue-600 text-white hover:bg-blue-500 hover:shadow-[0_0_20px_rgba(37,99,235,0.4)]"
                  }`}
                >
                  <Target className="w-4 h-4" />
                  EXECUTE
                </button>
              </div>
            </div>

            {/* Hidden Expanding Factor Strip (Glass Box feature) */}
            <div className="absolute top-0 left-0 w-1 h-full rounded-l-xl bg-gradient-to-b from-blue-500 to-purple-600 opacity-0 group-hover:opacity-100 transition-opacity"></div>
          </div>
        ))}
      </div>
    </div>
  );
}
