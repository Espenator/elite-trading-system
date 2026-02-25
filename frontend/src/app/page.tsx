// frontend/src/app/page.tsx
'use client';

import React, { useEffect, useState } from 'react';
import { useTradingStore } from '@/lib/store';
import TacticalChart from '@/components/charts/TacticalChart';
import { 
  PriceTick, 
  ActivePosition, 
  TradingSignal, 
  AgentActivityLog, 
  SystemHealth 
} from '@/lib/types';

// ─── KPI Card Component ───────────────────────────────────────
function KPICard({ 
  label, value, change, icon 
}: { 
  label: string; value: string; change?: number; icon: string 
}) {
  const isPositive = (change ?? 0) >= 0;
  return (
    <div className="bg-slate-800/60 border border-slate-700/50 rounded-lg p-4 
                    hover:border-cyan-500/30 transition-all duration-200">
      <div className="flex items-center justify-between mb-2">
        <span className="text-slate-400 text-xs font-medium uppercase tracking-wider">
          {label}
        </span>
        <span className="text-lg">{icon}</span>
      </div>
      <p className="text-2xl font-bold text-white font-mono">{value}</p>
      {change !== undefined && (
        <p className={`text-xs font-semibold mt-1 ${isPositive ? 'text-emerald-400' : 'text-red-400'}`}>
          {isPositive ? '▲' : '▼'} {Math.abs(change).toFixed(2)}%
        </p>
      )}
    </div>
  );
}

// ─── Watchlist Row Component ──────────────────────────────────
function WatchlistRow({ tick }: { tick: PriceTick }) {
  const isPositive = tick.change24h >= 0;
  return (
    <div className="flex items-center justify-between py-2 px-3 hover:bg-slate-700/30 
                    transition-colors border-b border-slate-800/50 cursor-pointer">
      <div className="flex items-center gap-2">
        <span className={`w-2 h-2 rounded-full ${isPositive ? 'bg-emerald-400' : 'bg-red-400'}`} />
        <span className="text-white text-sm font-semibold font-mono">{tick.symbol}</span>
      </div>
      <div className="text-right">
        <p className="text-white text-sm font-mono">${tick.price.toLocaleString()}</p>
        <p className={`text-xs font-mono ${isPositive ? 'text-emerald-400' : 'text-red-400'}`}>
          {isPositive ? '+' : ''}{tick.change24h.toFixed(2)}%
        </p>
      </div>
    </div>
  );
}

// ─── Active Positions Table ───────────────────────────────────
function PositionsTable({ positions }: { positions: ActivePosition[] }) {
  return (
    <div className="bg-slate-800/40 border border-slate-700/50 rounded-lg overflow-hidden">
      <div className="px-4 py-3 border-b border-slate-700/50">
        <h3 className="text-white font-semibold text-sm">Active Positions</h3>
      </div>
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead className="bg-slate-900/60">
            <tr>
              {['Symbol','Side','Size','Entry','Current','P&L','P&L %','Duration'].map(h => (
                <th key={h} className="px-3 py-2 text-left text-xs font-semibold text-slate-400 
                                       uppercase tracking-wider">{h}</th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-800/50">
            {positions.map((pos) => (
              <tr key={pos.id} className="hover:bg-slate-700/20 transition-colors">
                <td className="px-3 py-2 text-white font-mono font-semibold">{pos.symbol}</td>
                <td className="px-3 py-2">
                  <span className={`px-2 py-0.5 rounded text-xs font-bold 
                    ${pos.side === 'long' 
                      ? 'bg-emerald-500/20 text-emerald-400' 
                      : 'bg-red-500/20 text-red-400'}`}>
                    {pos.side.toUpperCase()}
                  </span>
                </td>
                <td className="px-3 py-2 text-slate-300 font-mono">{pos.size}</td>
                <td className="px-3 py-2 text-slate-300 font-mono">${pos.entryPrice.toFixed(2)}</td>
                <td className="px-3 py-2 text-white font-mono">${pos.currentPrice.toFixed(2)}</td>
                <td className={`px-3 py-2 font-mono font-semibold 
                  ${pos.unrealizedPnL >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>
                  {pos.unrealizedPnL >= 0 ? '+' : ''}${pos.unrealizedPnL.toFixed(2)}
                </td>
                <td className={`px-3 py-2 font-mono text-xs 
                  ${pos.unrealizedPnLPercent >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>
                  {pos.unrealizedPnLPercent >= 0 ? '+' : ''}{pos.unrealizedPnLPercent.toFixed(2)}%
                </td>
                <td className="px-3 py-2 text-slate-400 text-xs">{pos.duration}</td>
              </tr>
            ))}
            {positions.length === 0 && (
              <tr>
                <td colSpan={8} className="px-3 py-8 text-center text-slate-500">
                  Awaiting backend connection...
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}

// ─── Signal Feed ──────────────────────────────────────────────
function SignalFeed({ signals }: { signals: TradingSignal[] }) {
  return (
    <div className="bg-slate-800/40 border border-slate-700/50 rounded-lg">
      <div className="px-4 py-3 border-b border-slate-700/50 flex items-center justify-between">
        <h3 className="text-white font-semibold text-sm">Live Signals</h3>
        <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
      </div>
      <div className="max-h-64 overflow-y-auto divide-y divide-slate-800/50">
        {signals.map((sig) => (
          <div key={sig.id} className="px-4 py-3 hover:bg-slate-700/20 transition-colors">
            <div className="flex items-center justify-between mb-1">
              <div className="flex items-center gap-2">
                <span className="text-white font-mono font-bold text-sm">{sig.symbol}</span>
                <span className={`px-1.5 py-0.5 rounded text-[10px] font-bold uppercase
                  ${sig.direction === 'long' 
                    ? 'bg-emerald-500/20 text-emerald-400' 
                    : 'bg-red-500/20 text-red-400'}`}>
                  {sig.direction}
                </span>
                <span className="px-1.5 py-0.5 rounded text-[10px] font-medium 
                  bg-blue-500/20 text-blue-300">
                  {sig.type.replace('_', ' ')}
                </span>
              </div>
              <span className="text-cyan-400 font-mono text-sm font-bold">
                {sig.confidence}%
              </span>
            </div>
            <div className="flex gap-4 text-xs text-slate-400 font-mono">
              <span>Entry: ${sig.entryPrice.toFixed(2)}</span>
              <span className="text-red-400">SL: ${sig.stopLoss.toFixed(2)}</span>
              <span className="text-emerald-400">TP: ${sig.takeProfit.toFixed(2)}</span>
            </div>
          </div>
        ))}
        {signals.length === 0 && (
          <div className="px-4 py-8 text-center text-slate-500 text-sm">
            No active signals — scanner initializing...
          </div>
        )}
      </div>
    </div>
  );
}

// ─── Agent Activity Log ───────────────────────────────────────
function AgentLog({ logs }: { logs: AgentActivityLog[] }) {
  const statusColor = (s: string) => 
    s === 'success' ? 'text-emerald-400' : s === 'processing' ? 'text-yellow-400' : 'text-red-400';
  
  return (
    <div className="bg-slate-800/40 border border-slate-700/50 rounded-lg">
      <div className="px-4 py-3 border-b border-slate-700/50">
        <h3 className="text-white font-semibold text-sm">Agent Activity</h3>
      </div>
      <div className="max-h-48 overflow-y-auto divide-y divide-slate-800/50">
        {logs.map((log) => (
          <div key={log.id} className="px-4 py-2 flex items-start gap-3">
            <span className={`mt-1 w-1.5 h-1.5 rounded-full flex-shrink-0 ${
              log.status === 'success' ? 'bg-emerald-400' 
              : log.status === 'processing' ? 'bg-yellow-400 animate-pulse' 
              : 'bg-red-400'
            }`} />
            <div className="flex-1 min-w-0">
              <p className="text-xs text-white truncate">
                <span className="text-cyan-400 font-semibold">{log.agentId}</span>
                {' — '}{log.action}
              </p>
              <p className="text-[10px] text-slate-500 font-mono">{log.details}</p>
            </div>
            <span className="text-[10px] text-slate-500 font-mono flex-shrink-0">
              {new Date(log.timestamp).toLocaleTimeString()}
            </span>
          </div>
        ))}
        {logs.length === 0 && (
          <div className="px-4 py-6 text-center text-slate-500 text-xs">
            Agents idle — awaiting WebSocket connection
          </div>
        )}
      </div>
    </div>
  );
}

// ─── System Health Bar ────────────────────────────────────────
function SystemHealthBar({ health }: { health: SystemHealth }) {
  const color = health.status === 'online' ? 'bg-emerald-400' 
    : health.status === 'degraded' ? 'bg-yellow-400' : 'bg-red-400';
  
  return (
    <div className="flex items-center gap-4 px-6 py-2 bg-slate-900/80 border-b border-slate-800">
      <div className="flex items-center gap-2">
        <span className={`w-2 h-2 rounded-full ${color} ${
          health.status === 'online' ? 'animate-pulse' : ''}`} />
        <span className="text-xs text-slate-300 font-medium uppercase">
          {health.status}
        </span>
      </div>
      <span className="text-xs text-slate-500">|</span>
      <span className="text-xs text-slate-400 font-mono">
        Latency: {health.latencyMs}ms
      </span>
      <span className="text-xs text-slate-500">|</span>
      <span className="text-xs text-slate-400 font-mono">
        Agents: {health.activeAgents}
      </span>
      <span className="text-xs text-slate-500">|</span>
      <span className="text-xs text-slate-400 font-mono">
        Last Tick: {new Date(health.lastTick).toLocaleTimeString()}
      </span>
      <div className="ml-auto">
        <span className="text-xs text-cyan-400 font-bold tracking-wider">
          ELITE TRADER COMMAND CENTER
        </span>
      </div>
    </div>
  );
}

// ═════════════════════════════════════════════════════════════════
// ─── MAIN DASHBOARD PAGE ────────────────────────────────────────
// ═════════════════════════════════════════════════════════════════
export default function DashboardPage() {
  const { 
    prices, 
    activePositions, 
    latestSignals, 
    agentLogs, 
    systemHealth, 
    selectedSymbol, 
    setSelectedSymbol,
    connect, 
    isConnected 
  } = useTradingStore();

  // Connect to WebSocket on mount
  useEffect(() => {
    connect();
  }, [connect]);

  // Derive KPI values from store
  const totalPnL = activePositions.reduce((sum, p) => sum + p.unrealizedPnL, 0);
  const winningPositions = activePositions.filter(p => p.unrealizedPnL > 0).length;
  const winRate = activePositions.length > 0 
    ? ((winningPositions / activePositions.length) * 100) 
    : 0;
  const totalMargin = activePositions.reduce((sum, p) => sum + p.marginUsed, 0);
  const symbolCount = Object.keys(prices).length;

  // Convert prices map to sorted array for watchlist
  const watchlistTicks = Object.values(prices)
    .sort((a, b) => Math.abs(b.change24h) - Math.abs(a.change24h));

  return (
    <div className="min-h-screen bg-gradient-to-b from-slate-950 via-slate-900 to-slate-950 text-white">
      {/* ─── Top Health Bar ─── */}
      <SystemHealthBar health={systemHealth} />

      <div className="px-4 py-4">
        {/* ─── KPI Cards Row (10 Cards) ─── */}
        <div className="grid grid-cols-2 md:grid-cols-5 xl:grid-cols-10 gap-3 mb-4">
          <KPICard label="Portfolio P&L" value={`$${totalPnL.toFixed(2)}`} 
                   change={totalPnL / 10000} icon="💰" />
          <KPICard label="Active Positions" value={`${activePositions.length}`} icon="📊" />
          <KPICard label="Win Rate" value={`${winRate.toFixed(1)}%`} icon="🎯" />
          <KPICard label="Margin Used" value={`$${totalMargin.toFixed(0)}`} icon="🏦" />
          <KPICard label="Live Signals" value={`${latestSignals.length}`} icon="⚡" />
          <KPICard label="Symbols Tracked" value={`${symbolCount}`} icon="👁️" />
          <KPICard label="Agents Online" value={`${systemHealth.activeAgents}`} icon="🤖" />
          <KPICard label="WS Latency" value={`${systemHealth.latencyMs}ms`} icon="📡" />
          <KPICard label="Connection" value={isConnected ? 'LIVE' : 'OFFLINE'} icon="🔌" />
          <KPICard label="System" value={systemHealth.status.toUpperCase()} icon="⚙️" />
        </div>

        {/* ─── Main 3-Column Grid ─── */}
        <div className="grid grid-cols-12 gap-4">
          
          {/* LEFT: Watchlist Sidebar (2 cols) */}
          <div className="col-span-12 xl:col-span-2">
            <div className="bg-slate-800/40 border border-slate-700/50 rounded-lg">
              <div className="px-4 py-3 border-b border-slate-700/50 flex items-center justify-between">
                <h3 className="text-white font-semibold text-sm">Watchlist</h3>
                <span className="text-xs text-slate-400 font-mono">{symbolCount}</span>
              </div>
              <div className="max-h-[calc(100vh-280px)] overflow-y-auto">
                {watchlistTicks.map((tick) => (
                  <div key={tick.symbol} onClick={() => setSelectedSymbol(tick.symbol)}>
                    <WatchlistRow tick={tick} />
                  </div>
                ))}
                {watchlistTicks.length === 0 && (
                  <div className="px-4 py-8 text-center text-slate-500 text-xs">
                    Connecting to price feed...
                  </div>
                )}
              </div>
            </div>
          </div>

          {/* CENTER: Main Content (7 cols) */}
          <div className="col-span-12 xl:col-span-7 space-y-4">
            {/* Massive Equity Curve — TradingView Lightweight Charts */}
            <div className="bg-slate-800/40 border border-slate-700/50 rounded-lg p-4">
              <div className="flex items-center justify-between mb-3">
                <h2 className="text-white font-bold text-lg">
                  {selectedSymbol || 'BTC'} — Tactical View
                </h2>
                <div className="flex gap-1">
                  {['1H', '4H', '1D', '1W'].map((tf) => (
                    <button key={tf} className="px-3 py-1 text-xs font-semibold rounded 
                      bg-slate-700 text-slate-300 hover:bg-slate-600 transition-colors">
                      {tf}
                    </button>
                  ))}
                </div>
              </div>
              <TacticalChart symbol={selectedSymbol || 'BTC'} theme="dark" />
            </div>

            {/* Active Positions Table (15+ rows) */}
            <PositionsTable positions={activePositions} />
          </div>

          {/* RIGHT: Signals + Agent Log (3 cols) */}
          <div className="col-span-12 xl:col-span-3 space-y-4">
            <SignalFeed signals={latestSignals} />
            <AgentLog logs={agentLogs} />
          </div>
        </div>
      </div>
    </div>
  );
}
