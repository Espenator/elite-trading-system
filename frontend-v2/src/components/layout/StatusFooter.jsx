/**
 * StatusFooter — persistent status bar fixed to the bottom of every page.
 *
 * Visual spec (matches mockups):
 *   - bg: #0B0E14, border-top: rgba(42,52,68,0.5), height: ~28px
 *   - Left:   scrolling stock ticker strip (SPY, QQQ, DIA, VIX, IWM, REGIME)
 *   - Center: system health indicators (WS · API · agents · LLM Flow · Conference · Load)
 *   - Right:  Uptime · Last Refresh (monospace clock) · refresh button
 *
 * Mockup text verbatim examples:
 *   "WebSocket Connected • API Healthy • 42 agents • LLM Flow 847 • Conference 8/12 • Last Refresh 09:41:23 • Load 2.4/4.0 • Uptime 47d 12h"
 *   "SPY 598.42 +0.34% | QQQ 518.73 +0.52% | DIA 441.20 +0.18% | VIX 14.20 -2.31% | IWM 226.84 +0.67% | REGIME: GREEN"
 */

import { useState, useEffect, useCallback, useRef } from "react";
import { RefreshCw } from "lucide-react";

// ── Colour helpers ────────────────────────────────────────────────────────────
function statusColor(s) {
  if (s === "green")  return "#10B981";
  if (s === "amber")  return "#F59E0B";
  if (s === "red")    return "#EF4444";
  return "#6B7280";
}

function statusGlow(s) {
  if (s === "green") return "0 0 6px rgba(16,185,129,0.5)";
  if (s === "amber") return "0 0 6px rgba(245,158,11,0.5)";
  if (s === "red")   return "0 0 6px rgba(239,68,68,0.5)";
  return "none";
}

function StatusDot({ status, pulse }) {
  const color = statusColor(status);
  return (
    <span
      className={pulse ? "pulse-live" : ""}
      style={{
        display:      "inline-block",
        width:        7,
        height:       7,
        borderRadius: "50%",
        background:   color,
        boxShadow:    statusGlow(status),
        flexShrink:   0,
      }}
    />
  );
}

// ── Regime colour ────────────────────────────────────────────────────────────
const REGIME_TEXT = {
  GREEN:  "#10B981",
  YELLOW: "#F59E0B",
  RED:    "#EF4444",
};

// ── Ticker item ──────────────────────────────────────────────────────────────
function TickerItem({ symbol, price, change, changeColor }) {
  const col =
    changeColor === "green"
      ? "#10B981"
      : changeColor === "red"
      ? "#EF4444"
      : "#9CA3AF";
  const arrow = change?.startsWith("+") ? "▲" : change?.startsWith("-") ? "▼" : "";
  return (
    <span className="flex items-center gap-1 mx-3 font-mono text-[10px] shrink-0">
      <span className="text-[#9CA3AF] font-bold tracking-wider">{symbol}</span>
      <span className="text-white">{price}</span>
      {change && (
        <span style={{ color: col }}>
          {arrow} {change}
        </span>
      )}
    </span>
  );
}

// ── Separator ────────────────────────────────────────────────────────────────
const Pipe = () => (
  <span className="text-[#374151] mx-1 font-mono text-[10px] shrink-0">|</span>
);

const Dot = () => (
  <span className="text-[#374151] mx-2 shrink-0">•</span>
);

// ── Time utils ────────────────────────────────────────────────────────────────
function pad(n) { return String(n).padStart(2, "0"); }
function fmtTime(d) {
  return `${pad(d.getHours())}:${pad(d.getMinutes())}:${pad(d.getSeconds())}`;
}

// ── Main ─────────────────────────────────────────────────────────────────────
export default function StatusFooter({
  // Connection status
  apiStatus    = "red",
  wsStatus     = "red",
  mlStatus     = "red",

  // System info
  agentCount   = null,
  llmFlow      = null,
  conferenceCur = null,
  conferenceMax = null,
  loadCur      = null,
  loadMax      = null,
  uptimeDays   = null,
  uptimeHours  = null,

  // Market / regime
  regime       = null,

  // Ticker data — array of { symbol, price, change, changeColor }
  tickerItems,
}) {
  const [lastRefresh, setLastRefresh] = useState(fmtTime(new Date()));
  const [tick, setTick]               = useState(0); // force clock re-render

  // Tick every second for the clock
  useEffect(() => {
    const id = setInterval(() => {
      setLastRefresh(fmtTime(new Date()));
      setTick((t) => t + 1);
    }, 1000);
    return () => clearInterval(id);
  }, []);

  const handleRefresh = useCallback(() => {
    setLastRefresh(fmtTime(new Date()));
    window.dispatchEvent(new CustomEvent("embodier:refresh"));
  }, []);

  // Default ticker items (fallback while real data loads)
  const tickers = Array.isArray(tickerItems) ? tickerItems : [];

  // Duplicate the ticker array so the loop-scroll looks seamless
  const doubled = [...tickers, ...tickers];

  return (
    <footer
      className="fixed bottom-0 left-0 right-0 z-50 select-none overflow-hidden"
      style={{
        background:    "#0B0E14",
        borderTop:     "1px solid rgba(42,52,68,0.5)",
        height:        "28px",
        display:       "flex",
        alignItems:    "center",
      }}
    >
      {/* ── Left: Scrolling ticker ──────────────────────────────────── */}
      <div
        className="relative overflow-hidden"
        style={{
          width:       "360px",
          minWidth:    "260px",
          flexShrink:  0,
          borderRight: "1px solid rgba(42,52,68,0.4)",
          height:      "100%",
        }}
      >
        {tickers.length === 0 ? (
          <div className="flex items-center h-full px-3 font-mono text-[10px] text-[#6B7280]">
            No live market snapshot
          </div>
        ) : (
          <>
            {/* Left fade mask */}
            <div
              className="absolute left-0 top-0 bottom-0 w-6 z-10 pointer-events-none"
              style={{ background: "linear-gradient(to right, #0B0E14, transparent)" }}
            />
            {/* Right fade mask */}
            <div
              className="absolute right-0 top-0 bottom-0 w-6 z-10 pointer-events-none"
              style={{ background: "linear-gradient(to left, #0B0E14, transparent)" }}
            />

            <div
              className="ticker-strip flex items-center h-full px-2"
              style={{ width: "max-content" }}
            >
              {doubled.map((item, i) => (
                <span key={`${item.symbol}-${i}`} className="flex items-center">
                  <TickerItem {...item} />
                  {i < doubled.length - 1 && <Pipe />}
                </span>
              ))}
              {regime && (
                <span className="flex items-center gap-1.5 mx-3 font-mono text-[10px] shrink-0">
                  <span className="text-[#9CA3AF] font-bold tracking-wider">REGIME:</span>
                  <span
                    className="font-bold tracking-wider"
                    style={{ color: REGIME_TEXT[regime] ?? "#10B981" }}
                  >
                    {regime}
                  </span>
                </span>
              )}
            </div>
          </>
        )}
      </div>

      {/* ── Center: System status ───────────────────────────────────── */}
      <div
        className="flex-1 flex items-center justify-center gap-0 font-mono text-[10px] tracking-wide overflow-hidden px-2"
        style={{ color: "#6B7280" }}
      >
        <span className="flex items-center gap-1.5 shrink-0">
          <StatusDot status={wsStatus} pulse={wsStatus === "green"} />
          <span style={{ color: wsStatus === "green" ? "#10B981" : wsStatus === "red" ? "#EF4444" : "#F59E0B" }}>
            WebSocket {wsStatus === "green" ? "Connected" : wsStatus === "red" ? "Disconnected" : "Unstable"}
          </span>
        </span>

        <Dot />

        <span className="flex items-center gap-1.5 shrink-0">
          <StatusDot status={apiStatus} pulse={apiStatus === "green"} />
          <span style={{ color: apiStatus === "green" ? "#10B981" : apiStatus === "red" ? "#EF4444" : "#F59E0B" }}>
            API {apiStatus === "green" ? "Healthy" : apiStatus === "red" ? "Down" : "Degraded"}
          </span>
        </span>

        <Dot />

        {agentCount != null && (
          <>
            <span className="shrink-0 text-[#9CA3AF]">
              <span style={{ color: "#00D9FF" }}>{agentCount}</span> agents
            </span>
            <Dot />
          </>
        )}

        {llmFlow != null && (
          <>
            <span className="shrink-0 text-[#9CA3AF]">
              LLM Flow <span style={{ color: "#F9FAFB" }}>{llmFlow}</span>
            </span>
            <Dot />
          </>
        )}

        {conferenceCur != null && conferenceMax != null && (
          <>
            <span className="shrink-0 text-[#9CA3AF]">
              Conference{" "}
              <span style={{ color: conferenceCur >= conferenceMax ? "#EF4444" : "#F9FAFB" }}>
                {conferenceCur}/{conferenceMax}
              </span>
            </span>
            <Dot />
          </>
        )}

        {loadCur != null && loadMax != null && (
          <span className="shrink-0 text-[#9CA3AF]">
            Load{" "}
            <span
              style={{
                color:
                  loadCur / loadMax > 0.85
                    ? "#EF4444"
                    : loadCur / loadMax > 0.65
                    ? "#F59E0B"
                    : "#F9FAFB",
              }}
            >
              {typeof loadCur === "number" ? loadCur.toFixed(1) : loadCur}/
              {typeof loadMax === "number" ? loadMax.toFixed(1) : loadMax}
            </span>
          </span>
        )}
      </div>

      {/* ── Right: Uptime + Clock ───────────────────────────────────── */}
      <div
        className="flex items-center gap-2 font-mono text-[10px] shrink-0 px-3"
        style={{
          color:       "#6B7280",
          borderLeft:  "1px solid rgba(42,52,68,0.4)",
          height:      "100%",
        }}
      >
        {uptimeDays != null && uptimeHours != null && (
          <>
            <span className="shrink-0">
              Uptime{" "}
              <span className="text-[#9CA3AF]">
                {uptimeDays}d {pad(uptimeHours)}h
              </span>
            </span>
            <span className="text-[#374151]">·</span>
          </>
        )}

        <span className="shrink-0">
          Refresh{" "}
          <span className="text-[#9CA3AF]">{lastRefresh}</span>
        </span>

        <button
          type="button"
          onClick={handleRefresh}
          className="transition-colors"
          style={{ color: "#4B5563" }}
          aria-label="Refresh"
          onMouseEnter={(e) => { e.currentTarget.style.color = "#9CA3AF"; }}
          onMouseLeave={(e) => { e.currentTarget.style.color = "#4B5563"; }}
        >
          <RefreshCw size={10} />
        </button>
      </div>
    </footer>
  );
}
