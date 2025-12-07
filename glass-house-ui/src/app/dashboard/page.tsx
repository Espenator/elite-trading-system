"use client";
import { useEffect, useState } from "react";
import { useMarketStore } from "@/lib/store";

export default function GlassHouseDashboard() {
  const { fetchSignals, connectWebSocket, disconnectWebSocket, systemHealth } = useMarketStore();
  const [selectedSignal, setSelectedSignal] = useState<any>(null);

  useEffect(() => {
    // Fetch initial data
    fetchSignals();

    // Connect WebSocket
    connectWebSocket();

    // Fetch signals every 30 seconds
    const interval = setInterval(() => fetchSignals(), 30000);

    // Cleanup
    return () => {
      clearInterval(interval);
      disconnectWebSocket();
    };
  }, [fetchSignals, connectWebSocket, disconnectWebSocket]);

  return (
    <div className="h-screen bg-gradient-to-br from-slate-950 via-slate-900 to-slate-950 flex flex-col">
      {/* Header */}
      <div className="glass-panel m-4 p-4 border border-slate-700/50">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold text-slate-100">
              Elite Trading Glass House
            </h1>
            <p className="text-sm text-slate-400">
              Real-time signals with live backend data
            </p>
          </div>
          <div className="flex items-center gap-4">
            <div className="flex items-center gap-2">
              <div
                className={`w-2 h-2 rounded-full ${
                  systemHealth.apiConnected ? "bg-green-500" : "bg-red-500"
                } animate-pulse`}
              />
              <span className="text-xs text-slate-400">
                API: {systemHealth.apiConnected ? "Connected" : "Offline"}
              </span>
            </div>
            <div className="flex items-center gap-2">
              <div
                className={`w-2 h-2 rounded-full ${
                  systemHealth.wsConnected ? "bg-blue-500" : "bg-gray-500"
                } animate-pulse`}
              />
              <span className="text-xs text-slate-400">
                WS: {systemHealth.wsConnected ? "Live" : "Offline"}
              </span>
            </div>
            <span className="text-xs text-slate-400">
              Signals: {systemHealth.signalCount}
            </span>
          </div>
        </div>
      </div>

      {/* Main Content */}
      <div className="flex-1 flex gap-0 mx-4 mb-4 overflow-hidden">
        <LeftSidebar
          selectedSignal={selectedSignal}
          onSelectSignal={setSelectedSignal}
        />
        <CenterStage signal={selectedSignal} />
        <RightPanel />
      </div>
    </div>
  );
}

// Component implementations (LeftSidebar, CenterStage, RightPanel) remain the same
// but with data structure fixes...

function LeftSidebar({ selectedSignal, onSelectSignal }: any) {
  const { coreSignals, hotSignals, liquidSignals } = useMarketStore();
  const [activeTab, setActiveTab] = useState<"CORE" | "HOT" | "LIQUID">("HOT");
  const signals = { CORE: coreSignals, HOT: hotSignals, LIQUID: liquidSignals };

  return (
    <div className="w-80 h-full flex flex-col glass-panel border-r border-slate-700/50">
      <div className="flex border-b border-slate-700/50">
        {(["CORE", "HOT", "LIQUID"] as const).map((tier) => (
          <button
            key={tier}
            onClick={() => setActiveTab(tier)}
            className={`flex-1 py-3 text-sm font-semibold transition-all ${
              activeTab === tier
                ? "border-b-2 border-blue-500 text-slate-100"
                : "text-slate-400 hover:text-slate-200"
            }`}
          >
            {tier}
            <span className="ml-2 text-xs opacity-70">
              ({signals[tier].length})
            </span>
          </button>
        ))}
      </div>
      <div className="flex-1 overflow-y-auto p-3">
        {signals[activeTab].length === 0 ? (
          <div className="text-center text-slate-400 py-8">
            <p className="text-sm">No {activeTab} signals</p>
          </div>
        ) : (
          signals[activeTab].map((signal: any) => (
            <SignalCard
              key={signal.id}
              signal={signal}
              isSelected={selectedSignal?.id === signal.id}
              onClick={onSelectSignal}
            />
          ))
        )}
      </div>
    </div>
  );
}

function SignalCard({ signal, isSelected, onClick }: any) {
  const changeColor =
    signal.percentChange >= 0 ? "text-green-400" : "text-red-400";
  
  return (
    <div
      onClick={() => onClick(signal)}
      className={`p-3 mb-2 cursor-pointer rounded-lg border transition-all ${
        isSelected
          ? "border-blue-500 bg-blue-500/10"
          : "border-slate-700/50 bg-slate-800/50 hover:border-slate-600"
      }`}
    >
      <div className="flex items-start justify-between mb-2">
        <div className="flex items-center gap-2">
          <h3 className="text-lg font-bold text-slate-100">{signal.ticker}</h3>
          <span className="text-xs px-2 py-0.5 rounded bg-slate-700/50 text-slate-300">
            {signal.tier}
          </span>
        </div>
        <span className={`text-sm font-semibold ${changeColor}`}>
          {signal.percentChange >= 0 ? "+" : ""}
          {signal.percentChange.toFixed(2)}%
        </span>
      </div>
      <div className="flex items-center justify-between text-xs text-slate-400">
        <span>Conf: {signal.globalConfidence}%</span>
        <span
          className={
            signal.direction === "long" ? "text-green-400" : "text-red-400"
          }
        >
          {signal.direction.toUpperCase()}
        </span>
      </div>
    </div>
  );
}

function CenterStage({ signal }: any) {
  if (!signal)
    return (
      <div className="flex-1 flex items-center justify-center glass-panel mx-4">
        <div className="text-center text-slate-400">
          <div className="mb-4 text-6xl">📊</div>
          <p className="text-lg mb-2">Select a signal to view details</p>
          <p className="text-sm opacity-70">
            Choose from CORE, HOT, or LIQUID tiers
          </p>
        </div>
      </div>
    );

  const changeColor =
    signal.percentChange >= 0 ? "text-green-400" : "text-red-400";

  return (
    <div className="flex-1 glass-panel mx-4 p-6 overflow-y-auto">
      <div className="flex items-start justify-between mb-6">
        <div>
          <h1 className="text-4xl font-bold text-slate-100 mb-2">
            {signal.ticker}
          </h1>
          <p className="text-xl text-slate-300">
            Current Price:{" "}
            <span className="text-slate-100 font-semibold">
              ${signal.currentPrice.toFixed(2)}
            </span>
          </p>
        </div>
        <div className="text-right">
          <p className={`text-3xl font-bold ${changeColor}`}>
            {signal.percentChange >= 0 ? "+" : ""}
            {signal.percentChange.toFixed(2)}%
          </p>
        </div>
      </div>

      <div className="grid grid-cols-4 gap-4">
        <div className="p-4 rounded-lg bg-slate-800/50 border border-slate-700/50">
          <p className="text-sm text-slate-400 mb-1">Confidence</p>
          <p className="text-2xl font-bold text-slate-100">
            {signal.globalConfidence}%
          </p>
        </div>
        <div className="p-4 rounded-lg bg-slate-800/50 border border-slate-700/50">
          <p className="text-sm text-slate-400 mb-1">RVol</p>
          <p className="text-2xl font-bold text-slate-100">
            {signal.rvol.toFixed(2)}x
          </p>
        </div>
        <div className="p-4 rounded-lg bg-slate-800/50 border border-slate-700/50">
          <p className="text-sm text-slate-400 mb-1">Model Agreement</p>
          <p className="text-2xl font-bold text-slate-100">
            {(signal.modelAgreement * 100).toFixed(0)}%
          </p>
        </div>
        <div className="p-4 rounded-lg bg-slate-800/50 border border-slate-700/50">
          <p className="text-sm text-slate-400 mb-1">Direction</p>
          <p
            className={`text-2xl font-bold ${
              signal.direction === "long" ? "text-green-400" : "text-red-400"
            }`}
          >
            {signal.direction.toUpperCase()}
          </p>
        </div>
      </div>
    </div>
  );
}

function RightPanel() {
  const { systemHealth, mlConfig, updateMLConfig } = useMarketStore();

  return (
    <div className="w-96 h-full flex flex-col glass-panel border-l border-slate-700/50">
      <div className="p-4 border-b border-slate-700/50">
        <h3 className="text-lg font-semibold text-slate-100 mb-3">
          ⚡ System Health
        </h3>
        <div className="space-y-3 text-sm">
          <div className="flex justify-between">
            <span className="text-slate-400">Last Update</span>
            <span className="text-slate-200">
              {new Date(systemHealth.lastUpdate).toLocaleTimeString()}
            </span>
          </div>
          <div className="flex justify-between">
            <span className="text-slate-400">Signal Count</span>
            <span className="text-slate-200">{systemHealth.signalCount}</span>
          </div>
        </div>
      </div>

      <div className="flex-1 p-4 overflow-y-auto">
        <h3 className="text-lg font-semibold text-slate-100 mb-4">
          🎛️ ML Controls
        </h3>
        <div className="space-y-4">
          <div>
            <div className="flex justify-between mb-2">
              <label className="text-sm text-slate-400">
                Confidence Threshold
              </label>
              <span className="text-sm font-semibold text-blue-400">
                {mlConfig.confidenceThreshold}%
              </span>
            </div>
            <input
              type="range"
              min="0"
              max="100"
              value={mlConfig.confidenceThreshold}
              onChange={(e) =>
                updateMLConfig({
                  confidenceThreshold: parseInt(e.target.value),
                })
              }
              className="w-full"
            />
          </div>
        </div>
      </div>
    </div>
  );
}
