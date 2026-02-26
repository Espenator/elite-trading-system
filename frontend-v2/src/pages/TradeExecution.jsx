"use client";

import React, { useState } from "react";
import {
  ShieldAlert,
  Target,
  CheckCircle2,
  XCircle,
  Lock,
  Activity,
  Send,
} from "lucide-react";
import PageHeader from "../components/ui/PageHeader";

export default function TradeExecution() {
  const [accountSize] = useState(800000); // From Trader Profile memory
  const [regimeRisk] = useState(0.02); // 2.0% Risk (GREEN Regime)

  // Simulated selected signal from Signals.jsx
  const [activeSignal] = useState({
    ticker: "RBRK",
    action: "LONG",
    entry: 75.5,
    stop: 62.0, // Structural Invalidation
    target1: 89.0, // 1R (1:1)
    target2: 102.5, // 2R (2:1)
    confidence: 92,
    factors: ["Velez Daily 88", "4H HHHL", "Whale Ask Flow 80%"],
  });

  // 6-Question Zone Checklist State
  const [checklist, setChecklist] = useState({
    edgeConfirmed: false,
    riskPredefined: false,
    riskAccepted: false,
    noHesitation: false,
    profitPlan: false,
    journalReady: false,
  });

  const allChecksPassed = Object.values(checklist).every((val) => val === true);

  // Position Sizing Math (Van Tharp)
  const riskAmount = accountSize * regimeRisk; // $16,000
  const riskPerShare = activeSignal.entry - activeSignal.stop; // $13.50
  const totalShares = Math.floor(riskAmount / riskPerShare); // ~1,185 shares
  const totalCapitalRequired = totalShares * activeSignal.entry;

  // 33-33-34 Scale-in Math
  const entry1 = Math.floor(totalShares * 0.33);
  const entry2 = Math.floor(totalShares * 0.33);
  const entry3 = totalShares - entry1 - entry2;

  const [orderStatus, setOrderStatus] = useState("IDLE");

  const handleExecute = () => {
    setOrderStatus("ROUTING");
    setTimeout(() => setOrderStatus("FILLED"), 1500);
  };

  const toggleCheck = (key) => {
    setChecklist((prev) => ({ ...prev, [key]: !prev[key] }));
  };

  return (
    <div className="space-y-6">
      <PageHeader
        icon={Send}
        title="Trade Execution"
        description="6-Question Zone Checklist & position sizing"
      />

      <div className="flex flex-col xl:flex-row gap-6 flex-1">
        {/* Left Column: Signal Data & Risk Parameters */}
        <div className="w-full xl:w-1/4 space-y-6">
          <div className="bg-slate-800/40 border border-slate-700/50 rounded-xl p-6 backdrop-blur-md shadow-lg">
            <div className="flex items-center justify-between mb-6 border-b border-slate-700/50 pb-4">
              <h2 className="text-2xl font-bold text-white flex items-center gap-2">
                <Target className="text-blue-500" /> ACTIVE SETUP
              </h2>
              <span className="px-3 py-1 bg-green-500/20 text-green-400 border border-green-500/50 rounded text-xs font-bold tracking-wider">
                {activeSignal.action}
              </span>
            </div>

            <div className="text-5xl font-black text-white mb-2 tracking-widest">
              {activeSignal.ticker}
            </div>
            <div className="text-sm text-slate-400 mb-6">
              Confidence Score:{" "}
              <span className="text-green-400 font-bold">
                {activeSignal.confidence}%
              </span>
            </div>

            <div className="space-y-4 text-sm">
              <div className="flex justify-between p-3 bg-slate-900/50 rounded border border-slate-700/30">
                <span className="text-slate-500">Entry Zone</span>
                <span className="text-white font-bold">
                  ${activeSignal.entry.toFixed(2)}
                </span>
              </div>
              <div className="flex justify-between p-3 bg-red-950/20 rounded border border-red-900/30">
                <span className="text-red-400/70">Structural Stop</span>
                <span className="text-red-400 font-bold">
                  ${activeSignal.stop.toFixed(2)}
                </span>
              </div>
              <div className="flex justify-between p-3 bg-green-950/20 rounded border border-green-900/30">
                <span className="text-green-400/70">Target 1 (1R)</span>
                <span className="text-green-400 font-bold">
                  ${activeSignal.target1.toFixed(2)}
                </span>
              </div>
            </div>
          </div>

          <div className="bg-slate-800/40 border border-slate-700/50 rounded-xl p-6 backdrop-blur-md shadow-lg">
            <h3 className="text-lg font-bold text-white mb-4 flex items-center gap-2">
              <ShieldAlert className="w-5 h-5 text-yellow-500" /> Van Tharp
              Sizing
            </h3>
            <div className="space-y-3 text-sm">
              <div className="flex justify-between">
                <span className="text-slate-400">Account Size</span>
                <span className="text-white">
                  ${accountSize.toLocaleString()}
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-400">Regime Risk Cap</span>
                <span className="text-yellow-400">
                  {(regimeRisk * 100).toFixed(1)}%
                </span>
              </div>
              <div className="flex justify-between border-t border-slate-700/50 pt-3">
                <span className="text-slate-400">Capital at Risk (1R)</span>
                <span className="text-red-400 font-bold">
                  -${riskAmount.toLocaleString()}
                </span>
              </div>
            </div>
          </div>
        </div>

        {/* Center Column: 6-Question Zone Checklist */}
        <div className="w-full xl:w-2/5 bg-slate-800/40 border border-slate-700/50 rounded-xl p-6 backdrop-blur-md shadow-lg">
          <h2 className="text-2xl font-bold text-white mb-2 flex items-center gap-2">
            <Lock className="text-purple-500" /> ZONE CHECKLIST
          </h2>
          <p className="text-slate-400 text-sm mb-6">
            All 6 questions must be answered YES to unlock execution.
          </p>

          <div className="space-y-3">
            {[
              {
                id: "edgeConfirmed",
                title: "1. Edge Confirmed?",
                desc: "Scanner score > 70? Weekly/Daily/4H aligned? Flow confirms?",
              },
              {
                id: "riskPredefined",
                title: "2. Risk Predefined?",
                desc: "Stop placed below structural invalidation level?",
              },
              {
                id: "riskAccepted",
                title: "3. Risk Accepted?",
                desc: `Accepting a total loss of $${riskAmount.toLocaleString()} if thesis fails?`,
              },
              {
                id: "noHesitation",
                title: "4. No Hesitation?",
                desc: "Ready to execute mechanically without fear or greed?",
              },
              {
                id: "profitPlan",
                title: "5. Profit Plan?",
                desc: "T1 set at 1R for 50% scale-out? Trailing stop ready?",
              },
              {
                id: "journalReady",
                title: "6. Journal Ready?",
                desc: "Hypothesis documented in Google Sheets?",
              },
            ].map((item) => (
              <div
                key={item.id}
                onClick={() => toggleCheck(item.id)}
                className={`p-4 rounded-lg border cursor-pointer transition-all duration-300 flex gap-4 items-start ${
                  checklist[item.id]
                    ? "bg-blue-900/20 border-blue-500/50 shadow-[0_0_15px_rgba(37,99,235,0.15)]"
                    : "bg-slate-900/50 border-slate-700/50 hover:bg-slate-800"
                }`}
              >
                <div className="mt-0.5">
                  {checklist[item.id] ? (
                    <CheckCircle2 className="text-blue-500" />
                  ) : (
                    <XCircle className="text-slate-600" />
                  )}
                </div>
                <div>
                  <h4
                    className={`font-bold ${checklist[item.id] ? "text-white" : "text-slate-300"}`}
                  >
                    {item.title}
                  </h4>
                  <p className="text-xs text-slate-500 mt-1">{item.desc}</p>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Right Column: 33-33-34 Scale-In Execution Deck */}
        <div className="w-full xl:w-[35%] bg-slate-800/40 border border-slate-700/50 rounded-xl p-6 backdrop-blur-md shadow-lg flex flex-col justify-between">
          <div>
            <h2 className="text-2xl font-bold text-white mb-6 flex items-center gap-2">
              <Activity className="text-green-500" /> EXECUTION DECK
            </h2>

            <div className="bg-slate-900/50 p-4 rounded-lg border border-slate-700/50 mb-6">
              <div className="flex justify-between items-end mb-2">
                <span className="text-slate-400 text-sm">Total Position</span>
                <span className="text-2xl font-bold text-white">
                  {totalShares.toLocaleString()}{" "}
                  <span className="text-sm text-slate-500">shares</span>
                </span>
              </div>
              <div className="flex justify-between items-end">
                <span className="text-slate-400 text-sm">Capital Required</span>
                <span className="text-lg text-slate-300">
                  $
                  {totalCapitalRequired.toLocaleString(undefined, {
                    minimumFractionDigits: 2,
                  })}
                </span>
              </div>
            </div>

            <h4 className="text-sm font-bold text-slate-300 mb-3 uppercase tracking-wider">
              33-33-34 Scale-In Protocol
            </h4>
            <div className="space-y-2 text-sm mb-8">
              <div className="grid grid-cols-12 gap-2 bg-slate-900/40 p-3 rounded border border-slate-700/30 items-center">
                <div className="col-span-2 text-slate-500">33%</div>
                <div className="col-span-3 text-blue-400 font-bold">
                  {entry1} sh
                </div>
                <div className="col-span-4 text-white">
                  @ ${activeSignal.entry.toFixed(2)}
                </div>
                <div className="col-span-3 text-right text-xs text-slate-500">
                  Market Open
                </div>
              </div>
              <div className="grid grid-cols-12 gap-2 bg-slate-900/40 p-3 rounded border border-slate-700/30 items-center">
                <div className="col-span-2 text-slate-500">33%</div>
                <div className="col-span-3 text-blue-400 font-bold">
                  {entry2} sh
                </div>
                <div className="col-span-4 text-white">@ Retest</div>
                <div className="col-span-3 text-right text-xs text-slate-500">
                  Limit Ord
                </div>
              </div>
              <div className="grid grid-cols-12 gap-2 bg-slate-900/40 p-3 rounded border border-slate-700/30 items-center">
                <div className="col-span-2 text-slate-500">34%</div>
                <div className="col-span-3 text-blue-400 font-bold">
                  {entry3} sh
                </div>
                <div className="col-span-4 text-white">@ Breakout</div>
                <div className="col-span-3 text-right text-xs text-slate-500">
                  Stop Lmt
                </div>
              </div>
            </div>
          </div>

          {/* Big Confident Execute Button */}
          <div>
            {orderStatus === "IDLE" ? (
              <button
                disabled={!allChecksPassed}
                onClick={handleExecute}
                className={`w-full py-5 rounded-xl font-black text-xl tracking-widest transition-all duration-300 flex justify-center items-center gap-3 ${
                  allChecksPassed
                    ? "bg-blue-600 text-white hover:bg-blue-500 hover:shadow-[0_0_30px_rgba(37,99,235,0.6)] cursor-pointer"
                    : "bg-slate-800 text-slate-600 border border-slate-700 cursor-not-allowed"
                }`}
              >
                {allChecksPassed ? (
                  <>
                    <Send className="w-6 h-6" /> FIRE ENTRY 1
                  </>
                ) : (
                  <>
                    <Lock className="w-6 h-6" /> COMPLETE CHECKLIST
                  </>
                )}
              </button>
            ) : orderStatus === "ROUTING" ? (
              <div className="w-full py-5 rounded-xl bg-yellow-600/20 border border-yellow-500/50 text-yellow-500 font-black text-xl tracking-widest flex justify-center items-center gap-3 animate-pulse">
                <Activity className="w-6 h-6 animate-spin" /> ROUTING TO
                BROKER...
              </div>
            ) : (
              <div className="w-full py-5 rounded-xl bg-green-600/20 border border-green-500/50 text-green-400 font-black text-xl tracking-widest flex justify-center items-center gap-3 shadow-[0_0_30px_rgba(34,197,94,0.3)]">
                <CheckCircle2 className="w-6 h-6" /> ENTRY 1 FILLED
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
