/**
 * StatusFooter — persistent status bar fixed to the bottom of every page.
 * Displays API/WS/ML connection status, app version/mode, and last-refresh time.
 */

import { useState, useEffect, useCallback } from 'react';
import { RefreshCw } from 'lucide-react';

function StatusDot({ color, pulse }) {
  const colorMap = {
    green: 'bg-emerald-400',
    amber: 'bg-amber-400',
    red:   'bg-red-500',
  };
  return (
    <span
      className={`w-2 h-2 rounded-full inline-block ${colorMap[color] ?? colorMap.green} ${pulse ? 'pulse-live' : ''}`}
    />
  );
}

function pad(n) {
  return String(n).padStart(2, '0');
}

function formatTime(date) {
  return `${pad(date.getHours())}:${pad(date.getMinutes())}:${pad(date.getSeconds())}`;
}

export default function StatusFooter({
  apiStatus  = 'red',
  wsStatus   = 'red',
  mlStatus   = 'red',
}) {
  const [lastRefresh, setLastRefresh] = useState(formatTime(new Date()));

  // Auto-tick the clock every second
  useEffect(() => {
    const id = setInterval(() => setLastRefresh(formatTime(new Date())), 1000);
    return () => clearInterval(id);
  }, []);

  const handleRefresh = useCallback(() => {
    setLastRefresh(formatTime(new Date()));
    window.dispatchEvent(new CustomEvent('embodier:refresh'));
  }, []);

  return (
    <footer className="fixed bottom-0 left-0 right-0 z-50 bg-[#0B0E14] border-t border-[#1e293b] px-4 py-1.5 flex items-center justify-between text-[10px] select-none">
      {/* Left — status indicators */}
      <div className="flex items-center gap-3">
        <span className="flex items-center gap-1.5 text-slate-400">
          <StatusDot color={apiStatus} pulse={apiStatus === 'green'} />
          API Connected
        </span>
        <span className="flex items-center gap-1.5 text-slate-400">
          <StatusDot color={wsStatus} pulse={wsStatus === 'green'} />
          WS Active
        </span>
        <span className="flex items-center gap-1.5 text-slate-400">
          <StatusDot color={mlStatus} pulse={mlStatus === 'green'} />
          ML Engine
        </span>
      </div>

      {/* Center — version / mode */}
      <div className="font-mono text-slate-500 tracking-wider absolute left-1/2 -translate-x-1/2">
        EMBODIER TRADER v2.4.1 — PAPER MODE
      </div>

      {/* Right — last refresh */}
      <div className="flex items-center gap-1.5 text-slate-500 font-mono">
        Last refresh: {lastRefresh}
        <button
          type="button"
          onClick={handleRefresh}
          className="ml-1 text-slate-600 hover:text-slate-300 transition-colors"
          aria-label="Refresh"
        >
          <RefreshCw size={11} />
        </button>
      </div>
    </footer>
  );
}
