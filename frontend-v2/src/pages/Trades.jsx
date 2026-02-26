"use client";

import React, { useState } from "react";
import {
  Briefcase,
  Activity,
  TrendingUp,
  TrendingDown,
  AlertTriangle,
  CheckCircle,
  Crosshair,
  Clock,
  Shield,
  XCircle,
} from "lucide-react";
import PageHeader from "../components/ui/PageHeader";

export default function Trades() {
  const [activeTab, setActiveTab] = useState("OPEN"); // 'OPEN' or 'CLOSED'
  const [totalRisk] = useState(2.8); // 2.8% of account currently at risk

  // Simulated open positions based on Bible v6.0 rules
  const [openPositions, setOpenPositions] = useState([
    {
      id: "POS-01",
      ticker: "RBRK",
      direction: "LONG",
      entryPrice: 75.5,
      currentPrice: 83.2,
      stopLoss: 75.5, // Moved to breakeven
      target1: 89.0,
      target2: 102.5,
      shares: 1185,
      rMultiple: 0.57, // (83.20 - 75.50) / 13.50 initial risk
      unrealizedPnL: 9124.5,
      structure4H: "HOLDING", // HOLDING or BROKEN
      volumeProfile: "ACCUMULATION",
      timeOpen: "1h 45m",
      status: "PROFIT_TRAIL", // Stop moved to BE
    },
    {
      id: "POS-02",
      ticker: "SNOW",
      direction: "SHORT",
      entryPrice: 185.0,
      currentPrice: 182.1,
      stopLoss: 191.5,
      target1: 172.0,
      target2: 155.0,
      shares: 400,
      rMultiple: 0.44, // (185 - 182.10) / 6.50
      unrealizedPnL: 1160.0,
      structure4H: "HOLDING",
      volumeProfile: "NEUTRAL",
      timeOpen: "45m",
      status: "ACTIVE",
    },
    {
      id: "POS-03",
      ticker: "PLTR",
      direction: "LONG",
      entryPrice: 24.1,
      currentPrice: 23.5,
      stopLoss: 22.8,
      target1: 26.5,
      target2: 30.0,
      shares: 3500,
      rMultiple: -0.46, // (23.50 - 24.10) / 1.30
      unrealizedPnL: -2100.0,
      structure4H: "MARGINAL",
      volumeProfile: "DISTRIBUTION",
      timeOpen: "3h 10m",
      status: "AT_RISK",
    },
  ]);

  const closedPositions = [
    {
      id: "TRD-99",
      ticker: "CRWD",
      direction: "LONG",
      entryPrice: 280.0,
      exitPrice: 305.5,
      shares: 500,
      pnl: 12750.0,
      rMultiple: 2.1,
      exitReason: "TARGET_2_HIT",
      duration: "2 Days",
    },
    {
      id: "TRD-98",
      ticker: "TSLA",
      direction: "SHORT",
      entryPrice: 190.0,
      exitPrice: 195.0,
      shares: 600,
      pnl: -3000.0,
      rMultiple: -1.0,
      exitReason: "STOP_HIT",
      duration: "4 Hours",
    },
  ];

  const getStatusColor = (status) => {
    switch (status) {
      case "PROFIT_TRAIL":
        return "text-green-400 bg-green-400/10 border-green-500/30";
      case "ACTIVE":
        return "text-blue-400 bg-blue-400/10 border-blue-500/30";
      case "AT_RISK":
        return "text-yellow-400 bg-yellow-400/10 border-yellow-500/30";
      default:
        return "text-slate-400 bg-slate-400/10 border-slate-500/30";
    }
  };

  const getStructureIcon = (structure) => {
    switch (structure) {
      case "HOLDING":
        return <CheckCircle className="w-4 h-4 text-green-400" />;
      case "MARGINAL":
        return <AlertTriangle className="w-4 h-4 text-yellow-400" />;
      case "BROKEN":
        return <XCircle className="w-4 h-4 text-red-500" />;
      default:
        return null;
    }
  };

  const handleClosePosition = (id) => {
    setOpenPositions(openPositions.filter((pos) => pos.id !== id));
    // In production, this fires API to execution/ordermanager.py
  };

  return (
    <div className="space-y-6">
      <PageHeader
        icon={Briefcase}
        title="Position Management"
        description="Live Structural Tracking & Trailing Stops"
      >
        <div className="flex gap-4">
          <div className="bg-slate-800/40 border border-slate-700/50 rounded-xl p-4 backdrop-blur-md min-w-[150px]">
            <div className="text-xs text-slate-500 mb-1">Open Risk</div>
            <div
              className={`text-2xl font-mono font-bold ${totalRisk > 5 ? "text-red-400" : "text-yellow-400"}`}
            >
              {totalRisk}%
            </div>
          </div>
          <div className="bg-slate-800/40 border border-slate-700/50 rounded-xl p-4 backdrop-blur-md min-w-[150px]">
            <div className="text-xs text-slate-500 mb-1">Unrealized PnL</div>
            <div className="text-2xl font-mono font-bold text-green-400">
              +$
              {openPositions
                .reduce((sum, pos) => sum + pos.unrealizedPnL, 0)
                .toLocaleString(undefined, { minimumFractionDigits: 2 })}
            </div>
          </div>
        </div>
      </PageHeader>

      {/* Tabs */}
      <div className="flex gap-4 mb-6 border-b border-slate-800 pb-2">
        <button
          onClick={() => setActiveTab("OPEN")}
          className={`pb-2 px-4 font-bold text-sm tracking-wider transition-colors relative ${activeTab === "OPEN" ? "text-blue-400" : "text-slate-500 hover:text-slate-300"}`}
        >
          OPEN POSITIONS ({openPositions.length})
          {activeTab === "OPEN" && (
            <span className="absolute bottom-0 left-0 w-full h-0.5 bg-blue-500 shadow-[0_0_10px_rgba(59,130,246,0.8)]"></span>
          )}
        </button>
        <button
          onClick={() => setActiveTab("CLOSED")}
          className={`pb-2 px-4 font-bold text-sm tracking-wider transition-colors relative ${activeTab === "CLOSED" ? "text-blue-400" : "text-slate-500 hover:text-slate-300"}`}
        >
          TODAY'S CLOSED
          {activeTab === "CLOSED" && (
            <span className="absolute bottom-0 left-0 w-full h-0.5 bg-blue-500 shadow-[0_0_10px_rgba(59,130,246,0.8)]"></span>
          )}
        </button>
      </div>

      {/* Open Positions View */}
      {activeTab === "OPEN" && (
        <div className="space-y-4">
          {openPositions.map((pos) => (
            <div
              key={pos.id}
              className="bg-slate-800/40 border border-slate-700/50 rounded-xl p-5 backdrop-blur-sm shadow-lg relative overflow-hidden group"
            >
              {/* Left Color Bar */}
              <div
                className={`absolute top-0 left-0 w-1 h-full ${pos.direction === "LONG" ? "bg-green-500" : "bg-red-500"}`}
              ></div>

              <div className="flex flex-col lg:flex-row items-center justify-between gap-6">
                {/* Ticker & Status */}
                <div className="w-full lg:w-1/5">
                  <div className="flex items-center gap-3 mb-2">
                    <span className="text-3xl font-black text-white tracking-widest">
                      {pos.ticker}
                    </span>
                    <span
                      className={`px-2 py-0.5 rounded text-[10px] font-black tracking-widest border ${pos.direction === "LONG" ? "bg-green-500/20 text-green-400 border-green-500/50" : "bg-red-500/20 text-red-400 border-red-500/50"}`}
                    >
                      {pos.direction}
                    </span>
                  </div>
                  <span
                    className={`px-2 py-1 rounded text-xs font-bold border ${getStatusColor(pos.status)}`}
                  >
                    {pos.status.replace("_", " ")}
                  </span>
                </div>

                {/* Core Math */}
                <div className="w-full lg:w-1/3 grid grid-cols-2 gap-4 bg-slate-900/50 p-3 rounded-lg border border-slate-700/30 font-mono">
                  <div>
                    <div className="text-xs text-slate-500">Entry</div>
                    <div className="text-slate-300">
                      ${pos.entryPrice.toFixed(2)}
                    </div>
                  </div>
                  <div>
                    <div className="text-xs text-slate-500">Current</div>
                    <div
                      className={`font-bold ${pos.direction === "LONG" ? (pos.currentPrice > pos.entryPrice ? "text-green-400" : "text-red-400") : pos.currentPrice < pos.entryPrice ? "text-green-400" : "text-red-400"}`}
                    >
                      ${pos.currentPrice.toFixed(2)}
                    </div>
                  </div>
                  <div>
                    <div className="text-xs text-slate-500 flex items-center gap-1">
                      <Shield className="w-3 h-3 text-red-400" /> Stop Loss
                    </div>
                    <div
                      className={`${pos.stopLoss === pos.entryPrice ? "text-blue-400 font-bold" : "text-red-400"}`}
                    >
                      ${pos.stopLoss.toFixed(2)}{" "}
                      {pos.stopLoss === pos.entryPrice && "(BE)"}
                    </div>
                  </div>
                  <div>
                    <div className="text-xs text-slate-500 flex items-center gap-1">
                      <Crosshair className="w-3 h-3 text-green-400" /> T1 (1R)
                    </div>
                    <div className="text-green-400">
                      ${pos.target1.toFixed(2)}
                    </div>
                  </div>
                </div>

                {/* Systemic Analysis */}
                <div className="w-full lg:w-1/4 space-y-2 text-sm">
                  <div className="flex justify-between items-center">
                    <span className="text-slate-400">4H Structure</span>
                    <span className="flex items-center gap-1 font-bold text-white">
                      {pos.structure4H} {getStructureIcon(pos.structure4H)}
                    </span>
                  </div>
                  <div className="flex justify-between items-center">
                    <span className="text-slate-400">Volume Profile</span>
                    <span
                      className={`font-bold ${pos.volumeProfile === "ACCUMULATION" ? "text-green-400" : pos.volumeProfile === "DISTRIBUTION" ? "text-red-400" : "text-slate-300"}`}
                    >
                      {pos.volumeProfile}
                    </span>
                  </div>
                  <div className="flex justify-between items-center">
                    <span className="text-slate-400">
                      <Clock className="inline w-3 h-3 mb-0.5" /> Time Open
                    </span>
                    <span className="text-slate-300">{pos.timeOpen}</span>
                  </div>
                </div>

                {/* Performance & Actions */}
                <div className="w-full lg:w-[15%] flex flex-col items-end gap-3">
                  <div className="text-right">
                    <div
                      className={`text-2xl font-black font-mono ${pos.unrealizedPnL >= 0 ? "text-green-400" : "text-red-500"}`}
                    >
                      {pos.unrealizedPnL >= 0 ? "+" : ""}$
                      {pos.unrealizedPnL.toLocaleString(undefined, {
                        minimumFractionDigits: 2,
                      })}
                    </div>
                    <div className="text-sm font-bold text-slate-400">
                      {pos.rMultiple.toFixed(2)}R
                    </div>
                  </div>

                  <button
                    onClick={() => handleClosePosition(pos.id)}
                    className="w-full py-2 bg-red-600/20 hover:bg-red-600 text-red-400 hover:text-white border border-red-500/30 hover:border-red-500 rounded font-bold transition-all text-xs tracking-wider"
                  >
                    CLOSE MARKET
                  </button>
                </div>
              </div>
            </div>
          ))}

          {openPositions.length === 0 && (
            <div className="text-center py-20 bg-slate-800/20 border border-slate-700/30 rounded-xl">
              <Shield className="w-12 h-12 text-slate-600 mx-auto mb-3" />
              <h3 className="text-xl font-bold text-slate-400">FLAT MARKET</h3>
              <p className="text-slate-500 mt-1">
                No active positions. Scanning for structure...
              </p>
            </div>
          )}
        </div>
      )}

      {/* Closed Positions View */}
      {activeTab === "CLOSED" && (
        <div className="bg-slate-800/40 border border-slate-700/50 rounded-xl overflow-hidden backdrop-blur-md shadow-lg">
          <table className="w-full text-left border-collapse">
            <thead>
              <tr className="bg-slate-900/60 border-b border-slate-700/50 text-xs uppercase tracking-wider text-slate-400">
                <th className="p-4 font-semibold">Asset</th>
                <th className="p-4 font-semibold">Direction</th>
                <th className="p-4 font-semibold">Entry / Exit</th>
                <th className="p-4 font-semibold">Duration</th>
                <th className="p-4 font-semibold">Exit Reason</th>
                <th className="p-4 font-semibold text-right">R-Multiple</th>
                <th className="p-4 font-semibold text-right">Realized PnL</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-700/30">
              {closedPositions.map((trade) => (
                <tr
                  key={trade.id}
                  className="hover:bg-slate-800/40 transition-colors"
                >
                  <td className="p-4 font-bold text-white">{trade.ticker}</td>
                  <td className="p-4">
                    <span
                      className={`px-2 py-0.5 rounded text-[10px] font-black tracking-widest ${trade.direction === "LONG" ? "text-green-400 bg-green-400/10" : "text-red-400 bg-red-400/10"}`}
                    >
                      {trade.direction}
                    </span>
                  </td>
                  <td className="p-4 font-mono text-sm text-slate-300">
                    ${trade.entryPrice.toFixed(2)} → $
                    {trade.exitPrice.toFixed(2)}
                  </td>
                  <td className="p-4 text-sm text-slate-400">
                    {trade.duration}
                  </td>
                  <td className="p-4 text-sm font-semibold text-slate-300">
                    {trade.exitReason.replace(/_/g, " ")}
                  </td>
                  <td
                    className={`p-4 font-mono text-sm text-right font-bold ${trade.rMultiple > 0 ? "text-green-400" : "text-red-400"}`}
                  >
                    {trade.rMultiple > 0 ? "+" : ""}
                    {trade.rMultiple.toFixed(2)}R
                  </td>
                  <td
                    className={`p-4 font-mono font-bold text-right ${trade.pnl > 0 ? "text-green-400" : "text-red-400"}`}
                  >
                    {trade.pnl > 0 ? "+" : ""}$
                    {trade.pnl.toLocaleString(undefined, {
                      minimumFractionDigits: 2,
                    })}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
