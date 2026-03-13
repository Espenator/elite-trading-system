/**
 * TradeExecutionWidgets.jsx
 * Visualization components for the Trade Execution page.
 *
 * Exports:
 *   - VisualPriceLadder   — SVG price ladder with entry/stop/target levels
 *   - CouncilDecisionPanel — AI council verdict with agent vote breakdown
 */

import React, { useEffect, useState } from 'react';
import clsx from 'clsx';
import { getApiUrl } from '../../config/api';

/* ─────────────────────────────────────────────────────────────────
   Palette tokens (mirrors TradeExecution.jsx design language)
   ───────────────────────────────────────────────────────────────── */
const C = {
  bg0:      '#070d18',
  bg1:      '#0a1020',
  bg2:      '#111b2e',
  border:   '#1a2744',
  borderSub:'rgba(26,39,68,0.4)',
  textPrimary: '#e8f0fe',
  textMuted:   '#5a6f8a',
  textSub:     '#c8d6e5',
  cyan:     '#00d4e8',
  green:    '#00e676',
  red:      '#ff3860',
  amber:    '#ffab00',
  yellow:   '#ffe57f',
};

/* ─────────────────────────────────────────────────────────────────
   Shared micro-components
   ───────────────────────────────────────────────────────────────── */
const PanelHead = ({ children, right }) => (
  <div
    className="px-3 py-[7px] border-b flex items-center justify-between shrink-0"
    style={{ background: C.bg0, borderColor: C.border }}
  >
    <span
      className="font-mono text-[9px] font-semibold uppercase tracking-[0.5px]"
      style={{ color: C.textMuted }}
    >
      {children}
    </span>
    <div className="flex items-center gap-2">
      {right}
      <div className="flex gap-[3px]">
        <span className="w-[3px] h-[3px] rounded-full" style={{ background: C.textMuted }} />
        <span className="w-[3px] h-[3px] rounded-full" style={{ background: C.textMuted }} />
        <span className="w-[3px] h-[3px] rounded-full" style={{ background: C.textMuted }} />
      </div>
    </div>
  </div>
);

const DirectionBadge = ({ direction, size = 'sm' }) => {
  const color =
    direction === 'BUY'  ? C.green :
    direction === 'SELL' ? C.red   :
    C.amber;
  const bg =
    direction === 'BUY'  ? 'rgba(0,230,118,0.12)' :
    direction === 'SELL' ? 'rgba(255,56,96,0.12)'  :
    'rgba(255,171,0,0.12)';
  const px = size === 'lg' ? '10px' : '5px';
  const py = size === 'lg' ? '3px'  : '1px';
  const fs = size === 'lg' ? '11px' : '8px';
  return (
    <span
      className="font-mono font-bold rounded-[2px] uppercase"
      style={{ color, background: bg, padding: `${py} ${px}`, fontSize: fs, letterSpacing: '0.5px' }}
    >
      {direction}
    </span>
  );
};

/* ═════════════════════════════════════════════════════════════════
   1. VisualPriceLadder
   ═════════════════════════════════════════════════════════════════ */

/**
 * VisualPriceLadder
 *
 * A vertical SVG price ladder showing entry, stop, and target levels
 * with a current-price line and risk/reward annotation.
 *
 * Props:
 *   entry        {number}  Entry price
 *   stop         {number}  Stop-loss price
 *   target       {number}  Target price
 *   currentPrice {number}  Live price
 *   symbol       {string}  Ticker symbol
 */
export function VisualPriceLadder({
  entry        = 0,
  stop         = 0,
  target       = 0,
  currentPrice = 0,
  symbol       = '',
}) {
  const livePrice = currentPrice;

  /* ── Pulse animation for current price line ── */
  const [pulse, setPulse] = useState(true);
  useEffect(() => {
    const id = setInterval(() => setPulse(p => !p), 600);
    return () => clearInterval(id);
  }, []);

  /* ── Geometry ── */
  const SVG_W   = 220;   // wider to accommodate labels on right
  const SVG_H   = 300;
  const AXIS_X  = 52;    // x position of the price axis line
  const LABEL_X = AXIS_X + 6;
  const PAD_TOP    = 18;
  const PAD_BOTTOM = 18;

  /* ── Zero-state: show empty ladder when no prices set ── */
  const isEmpty = entry === 0 && stop === 0 && target === 0;

  const minP = stop   - 5;
  const maxP = target + 5;
  const range = maxP - minP;

  /* Map price → SVG Y (inverted: higher price = lower Y value) */
  const toY = (p) => PAD_TOP + ((maxP - p) / range) * (SVG_H - PAD_TOP - PAD_BOTTOM);

  /* Calculate tick interval (aim for ~$1 or auto-scale) */
  const rawInterval = range / 8;
  const magnitude   = Math.pow(10, Math.floor(Math.log10(rawInterval)));
  const tickInterval = Math.ceil(rawInterval / magnitude) * magnitude;
  const firstTick   = Math.ceil(minP / tickInterval) * tickInterval;
  const ticks = [];
  for (let t = firstTick; t <= maxP + 0.001; t = parseFloat((t + tickInterval).toFixed(10))) {
    ticks.push(parseFloat(t.toFixed(2)));
  }

  /* R:R ratio */
  const reward = target - entry;
  const risk   = entry  - stop;
  const rr     = risk > 0 ? (reward / risk).toFixed(1) : '—';

  /* Y positions */
  const yTarget = toY(target);
  const yEntry  = toY(entry);
  const yStop   = toY(stop);
  const yLive   = toY(Math.max(minP, Math.min(maxP, livePrice)));

  /* ── Badge rendering helper ── */
  const renderBadge = (x, y, text, color, bg) => {
    const chars  = text.length;
    const bW     = chars * 5.5 + 8;
    const bH     = 12;
    return (
      <g>
        <rect x={x} y={y - bH / 2} width={bW} height={bH} rx="2" fill={bg} />
        <text
          x={x + bW / 2} y={y + 4}
          textAnchor="middle"
          fontFamily="'JetBrains Mono', monospace"
          fontSize="7"
          fontWeight="700"
          fill={color}
          letterSpacing="0.3"
        >
          {text}
        </text>
      </g>
    );
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'stretch', background: C.bg1, border: `1px solid ${C.border}`, borderRadius: '4px', overflow: 'hidden', width: '100%', minWidth: 180 }}>
      <PanelHead right={
        <span className="font-mono text-[9px] font-semibold" style={{ color: C.cyan }}>{symbol}</span>
      }>
        Visual Price Ladder
      </PanelHead>

      {isEmpty ? (
        <div style={{
          flex: 1,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          padding: '40px 16px',
          color: C.textMuted,
          fontFamily: "'JetBrains Mono', monospace",
          fontSize: 10,
          textAlign: 'center',
          letterSpacing: '0.4px',
        }}>
          Set entry / stop / target to visualize
        </div>
      ) : (
      <div style={{ display: 'flex', gap: 0, flex: 1 }}>
        {/* SVG price strip */}
        <div style={{ flex: 1, display: 'flex', justifyContent: 'center', padding: '4px 0' }}>
          <svg
            viewBox={`0 0 ${SVG_W} ${SVG_H}`}
            width={SVG_W}
            height={SVG_H}
            style={{ display: 'block', maxWidth: '100%' }}
          >
            {/* ── Dark gradient background ── */}
            <defs>
              <linearGradient id="ladderBg" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%"   stopColor="#0a1428" />
                <stop offset="100%" stopColor="#050c1a" />
              </linearGradient>
              <linearGradient id="greenZone" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%"   stopColor="rgba(0,230,118,0.07)" />
                <stop offset="100%" stopColor="rgba(0,230,118,0.03)" />
              </linearGradient>
              <linearGradient id="redZone" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%"   stopColor="rgba(255,56,96,0.05)" />
                <stop offset="100%" stopColor="rgba(255,56,96,0.09)" />
              </linearGradient>
              <filter id="glow-green" x="-50%" y="-50%" width="200%" height="200%">
                <feGaussianBlur in="SourceGraphic" stdDeviation="1.5" result="blur" />
                <feMerge><feMergeNode in="blur" /><feMergeNode in="SourceGraphic" /></feMerge>
              </filter>
              <filter id="glow-cyan" x="-50%" y="-50%" width="200%" height="200%">
                <feGaussianBlur in="SourceGraphic" stdDeviation="1.5" result="blur" />
                <feMerge><feMergeNode in="blur" /><feMergeNode in="SourceGraphic" /></feMerge>
              </filter>
              <filter id="glow-red" x="-50%" y="-50%" width="200%" height="200%">
                <feGaussianBlur in="SourceGraphic" stdDeviation="1.5" result="blur" />
                <feMerge><feMergeNode in="blur" /><feMergeNode in="SourceGraphic" /></feMerge>
              </filter>
              <filter id="glow-yellow" x="-50%" y="-50%" width="200%" height="200%">
                <feGaussianBlur in="SourceGraphic" stdDeviation="2" result="blur" />
                <feMerge><feMergeNode in="blur" /><feMergeNode in="SourceGraphic" /></feMerge>
              </filter>
            </defs>

            <rect x="0" y="0" width={SVG_W} height={SVG_H} fill="url(#ladderBg)" />

            {/* ── Zone: entry → target (green tint) ── */}
            <rect
              x={AXIS_X - 40}
              y={yTarget}
              width={40}
              height={yEntry - yTarget}
              fill="url(#greenZone)"
            />

            {/* ── Zone: stop → entry (red tint) ── */}
            <rect
              x={AXIS_X - 40}
              y={yEntry}
              width={40}
              height={yStop - yEntry}
              fill="url(#redZone)"
            />

            {/* ── Axis line ── */}
            <line
              x1={AXIS_X} y1={PAD_TOP - 8}
              x2={AXIS_X} y2={SVG_H - PAD_BOTTOM + 8}
              stroke={C.border} strokeWidth="1"
            />

            {/* ── Tick marks & price labels ── */}
            {ticks.map((t) => {
              const ty = toY(t);
              const isKey = [entry, stop, target].some(p => Math.abs(p - t) < tickInterval * 0.05);
              return (
                <g key={t}>
                  <line
                    x1={AXIS_X - 4} y1={ty}
                    x2={AXIS_X}     y2={ty}
                    stroke={isKey ? '#2a3d60' : C.borderSub}
                    strokeWidth="1"
                  />
                  <text
                    x={AXIS_X + 4} y={ty + 3}
                    fontFamily="'JetBrains Mono', monospace"
                    fontSize="7"
                    fill={C.textMuted}
                    letterSpacing="0"
                  >
                    {t.toFixed(2)}
                  </text>
                </g>
              );
            })}

            {/* ── Horizontal grid lines (subtle) ── */}
            {ticks.map((t) => {
              const ty = toY(t);
              return (
                <line
                  key={`g-${t}`}
                  x1={AXIS_X - 40} y1={ty}
                  x2={AXIS_X}      y2={ty}
                  stroke={C.borderSub}
                  strokeWidth="0.5"
                  strokeDasharray="2,3"
                />
              );
            })}

            {/* ── TARGET line (green) ── */}
            <line
              x1={AXIS_X - 40} y1={yTarget}
              x2={AXIS_X + 2}  y2={yTarget}
              stroke={C.green} strokeWidth="1.5"
              filter="url(#glow-green)"
            />
            <line
              x1={0} y1={yTarget}
              x2={AXIS_X - 40} y2={yTarget}
              stroke="rgba(0,230,118,0.08)" strokeWidth="1"
            />
            {/* Target badge */}
            {renderBadge(LABEL_X, yTarget, `TARGET $${target.toFixed(2)}`, C.green, 'rgba(0,230,118,0.14)')}
            {/* Triangle marker on axis */}
            <polygon
              points={`${AXIS_X - 2},${yTarget} ${AXIS_X - 8},${yTarget - 4} ${AXIS_X - 8},${yTarget + 4}`}
              fill={C.green}
            />

            {/* ── ENTRY line (cyan) ── */}
            <line
              x1={AXIS_X - 40} y1={yEntry}
              x2={AXIS_X + 2}  y2={yEntry}
              stroke={C.cyan} strokeWidth="1.5"
              filter="url(#glow-cyan)"
            />
            <line
              x1={0} y1={yEntry}
              x2={AXIS_X - 40} y2={yEntry}
              stroke="rgba(0,212,232,0.08)" strokeWidth="1"
            />
            {renderBadge(LABEL_X, yEntry, `ENTRY $${entry.toFixed(2)}`, C.cyan, 'rgba(0,212,232,0.14)')}
            <polygon
              points={`${AXIS_X - 2},${yEntry} ${AXIS_X - 8},${yEntry - 4} ${AXIS_X - 8},${yEntry + 4}`}
              fill={C.cyan}
            />

            {/* ── STOP line (red) ── */}
            <line
              x1={AXIS_X - 40} y1={yStop}
              x2={AXIS_X + 2}  y2={yStop}
              stroke={C.red} strokeWidth="1.5"
              filter="url(#glow-red)"
            />
            <line
              x1={0} y1={yStop}
              x2={AXIS_X - 40} y2={yStop}
              stroke="rgba(255,56,96,0.08)" strokeWidth="1"
            />
            {renderBadge(LABEL_X, yStop, `STOP $${stop.toFixed(2)}`, C.red, 'rgba(255,56,96,0.14)')}
            <polygon
              points={`${AXIS_X - 2},${yStop} ${AXIS_X - 8},${yStop - 4} ${AXIS_X - 8},${yStop + 4}`}
              fill={C.red}
            />

            {/* ── LIVE PRICE line (pulsing yellow/white) ── */}
            <line
              x1={0}      y1={yLive}
              x2={AXIS_X} y2={yLive}
              stroke={pulse ? C.yellow : 'rgba(255,255,255,0.9)'}
              strokeWidth={pulse ? '1.5' : '1'}
              filter="url(#glow-yellow)"
              style={{ transition: 'stroke 0.3s, stroke-width 0.3s, y1 0.4s, y2 0.4s' }}
            />
            {/* Live price dot */}
            <circle
              cx={AXIS_X - 2} cy={yLive} r={pulse ? 3 : 2.5}
              fill={pulse ? C.yellow : 'rgba(255,255,255,0.9)'}
              filter="url(#glow-yellow)"
              style={{ transition: 'r 0.3s, fill 0.3s' }}
            />
            {/* Live price label (compact, left of axis) */}
            <rect
              x={0} y={yLive - 6}
              width={AXIS_X - 6} height={12}
              rx="2"
              fill="rgba(255,229,127,0.13)"
            />
            <text
              x={(AXIS_X - 6) / 2} y={yLive + 3.5}
              textAnchor="middle"
              fontFamily="'JetBrains Mono', monospace"
              fontSize="7.5"
              fontWeight="700"
              fill={C.yellow}
            >
              {livePrice.toFixed(2)}
            </text>

            {/* ── R:R annotation ── */}
            <text
              x={AXIS_X + 4} y={SVG_H - PAD_BOTTOM + 12}
              fontFamily="'JetBrains Mono', monospace"
              fontSize="8"
              fontWeight="700"
              fill={C.amber}
              letterSpacing="0.3"
            >
              R:R {rr}:1
            </text>

            {/* ── Symbol watermark ── */}
            <text
              x={AXIS_X - 40} y={PAD_TOP - 4}
              fontFamily="'JetBrains Mono', monospace"
              fontSize="7"
              fill="rgba(90,111,138,0.4)"
              letterSpacing="0.5"
            >
              {symbol}
            </text>
          </svg>
        </div>
      </div>
      )}
    </div>
  );
}

/* ═════════════════════════════════════════════════════════════════
   2. CouncilDecisionPanel
   ═════════════════════════════════════════════════════════════════ */

/* Circular confidence ring (SVG donut) */
function ConfidenceRing({ value = 87, size = 72 }) {
  const r      = (size - 10) / 2;
  const cx     = size / 2;
  const cy     = size / 2;
  const circ   = 2 * Math.PI * r;
  const filled = circ * (value / 100);
  const color  = value >= 75 ? C.green : value >= 50 ? C.amber : C.red;

  return (
    <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`}>
      {/* Track */}
      <circle
        cx={cx} cy={cy} r={r}
        fill="none"
        stroke={C.border}
        strokeWidth="5"
      />
      {/* Fill arc — start from top (−90°) */}
      <circle
        cx={cx} cy={cy} r={r}
        fill="none"
        stroke={color}
        strokeWidth="5"
        strokeDasharray={`${filled} ${circ - filled}`}
        strokeDashoffset={circ / 4}
        strokeLinecap="round"
        style={{ filter: `drop-shadow(0 0 4px ${color}44)`, transition: 'stroke-dasharray 0.6s ease' }}
      />
      {/* Percentage text */}
      <text
        x={cx} y={cy + 4}
        textAnchor="middle"
        fontFamily="'JetBrains Mono', monospace"
        fontSize="14"
        fontWeight="700"
        fill={color}
      >
        {value}%
      </text>
    </svg>
  );
}

/* Confidence bar for vote table */
function ConfBar({ value }) {
  const color = value >= 75 ? C.green : value >= 50 ? C.amber : C.red;
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 4, minWidth: 80 }}>
      <div style={{
        flex: 1,
        height: 4,
        background: C.bg2,
        borderRadius: 2,
        overflow: 'hidden',
      }}>
        <div style={{
          width: `${value}%`,
          height: '100%',
          background: color,
          borderRadius: 2,
          boxShadow: `0 0 4px ${color}55`,
          transition: 'width 0.5s ease',
        }} />
      </div>
      <span
        className="font-mono"
        style={{ fontSize: 8, color, minWidth: 24, textAlign: 'right' }}
      >
        {value}%
      </span>
    </div>
  );
}

/**
 * CouncilDecisionPanel
 *
 * Displays the latest AI council verdict with agent vote breakdown.
 *
 * Props:
 *   councilData  {object}   Council response
 *   onExecute    {function} Called when "Execute Trade" is clicked
 *   onOverride   {function} Called when "Override" is clicked
 *   onDismiss    {function} Called when "Dismiss" is clicked
 */
export function CouncilDecisionPanel({
  councilData,
  onExecute = () => {},
  onOverride = () => {},
  onDismiss  = () => {},
}) {
  const [data, setData] = useState(councilData || null);
  const [fetching, setFetching] = useState(false);
  const [fetchError, setFetchError] = useState(null);

  /* Fetch from real API if no councilData prop provided */
  useEffect(() => {
    if (councilData) {
      setData(councilData);
      return;
    }
    let cancelled = false;
    const fetchCouncil = async () => {
      setFetching(true);
      try {
        const res = await fetch(getApiUrl('councilLatest'));
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const json = await res.json();
        if (!cancelled) setData(json);
      } catch (err) {
        if (!cancelled) {
          setFetchError(err.message);
          setData(null);
        }
      } finally {
        if (!cancelled) setFetching(false);
      }
    };
    fetchCouncil();
    return () => { cancelled = true; };
  }, [councilData]);

  const d = data;

  /* Format timestamp — guard against undefined/null/invalid */
  const fmtTs = (ts) => {
    if (!ts) return '—';
    try {
      const d = new Date(ts);
      if (isNaN(d.getTime())) return '—';
      return d.toLocaleTimeString('en-US', {
        hour: '2-digit', minute: '2-digit', second: '2-digit', hour12: false,
      });
    } catch { return '—'; }
  };

  const dirColor =
    d?.direction === 'BUY'  ? C.green :
    d?.direction === 'SELL' ? C.red   :
    C.amber;

  const dirBg =
    d?.direction === 'BUY'  ? 'rgba(0,230,118,0.08)'  :
    d?.direction === 'SELL' ? 'rgba(255,56,96,0.08)'   :
    'rgba(255,171,0,0.08)';

  return (
    <div
      style={{
        background: C.bg1,
        border: `1px solid ${C.border}`,
        borderRadius: 4,
        overflow: 'hidden',
        display: 'flex',
        flexDirection: 'column',
        width: '100%',
      }}
    >
      {/* ── Header ── */}
      <PanelHead right={
        <span className="font-mono text-[8px]" style={{ color: C.textMuted }}>
          {fetching ? 'fetching...' : fetchError ? '⚠ no data' : d ? fmtTs(d.timestamp) : '—'}
        </span>
      }>
        Council Decision
      </PanelHead>

      {/* ── Verdict area ── */}
      {!d ? (
        <div
          style={{
            borderBottom: `1px solid ${C.border}`,
            padding: '24px 16px',
            display: 'flex',
            alignItems: 'center',
            gap: 16,
          }}
        >
          <ConfidenceRing value={0} size={68} />
          <div style={{ flex: 1 }}>
            <div
              className="font-mono font-black"
              style={{ fontSize: 36, lineHeight: 1, color: C.textMuted, letterSpacing: '-1px' }}
            >
              —
            </div>
            <div
              className="font-mono"
              style={{ fontSize: 10, color: C.textMuted, marginTop: 6 }}
            >
              No council decision available
            </div>
            <div
              className="font-mono"
              style={{ fontSize: 9, color: C.textMuted, marginTop: 2 }}
            >
              0% Confidence
            </div>
          </div>
        </div>
      ) : (
        <div
          style={{
            background: dirBg,
            borderBottom: `1px solid ${C.border}`,
            padding: '12px 16px',
            display: 'flex',
            alignItems: 'center',
            gap: 16,
          }}
        >
          {/* Confidence ring */}
          <ConfidenceRing value={d.confidence} size={68} />

          {/* Direction + symbol */}
          <div style={{ flex: 1 }}>
            <div
              className="font-mono font-black"
              style={{
                fontSize: 36,
                lineHeight: 1,
                color: dirColor,
                letterSpacing: '-1px',
                textShadow: `0 0 24px ${dirColor}55`,
              }}
            >
              {d.direction}
            </div>
            <div
              className="font-mono font-semibold"
              style={{ fontSize: 11, color: C.textSub, marginTop: 4, letterSpacing: '0.3px' }}
            >
              {d.symbol} — <span style={{ color: dirColor }}>{d.confidence}% Confidence</span>
            </div>
          </div>
        </div>
      )}

      {/* ── Vote breakdown table ── */}
      <div style={{ overflowX: 'auto' }}>
        <table style={{ width: '100%', borderCollapse: 'collapse' }}>
          <thead>
            <tr>
              {['Agent', 'Direction', 'Confidence', 'Weight', 'Reasoning'].map(h => (
                <th
                  key={h}
                  className="font-mono font-semibold uppercase"
                  style={{
                    padding: '5px 8px',
                    fontSize: 7.5,
                    color: C.textMuted,
                    textAlign: 'left',
                    letterSpacing: '0.5px',
                    borderBottom: `1px solid ${C.border}`,
                    background: C.bg0,
                    whiteSpace: 'nowrap',
                  }}
                >
                  {h}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {d ? (d.votes || []).map((v, i) => (
              <tr
                key={v.agent}
                style={{ background: i % 2 === 0 ? 'transparent' : 'rgba(255,255,255,0.015)' }}
                onMouseEnter={e => e.currentTarget.style.background = 'rgba(0,212,232,0.04)'}
                onMouseLeave={e => e.currentTarget.style.background = i % 2 === 0 ? 'transparent' : 'rgba(255,255,255,0.015)'}
              >
                {/* Agent name */}
                <td
                  className="font-mono font-semibold"
                  style={{
                    padding: '5px 8px',
                    fontSize: 9,
                    color: C.cyan,
                    borderBottom: `1px solid ${C.borderSub}`,
                    whiteSpace: 'nowrap',
                  }}
                >
                  {v.agent}
                </td>
                {/* Direction badge */}
                <td
                  style={{
                    padding: '5px 8px',
                    borderBottom: `1px solid ${C.borderSub}`,
                  }}
                >
                  <DirectionBadge direction={v.direction} />
                </td>
                {/* Confidence bar */}
                <td
                  style={{
                    padding: '5px 8px',
                    borderBottom: `1px solid ${C.borderSub}`,
                  }}
                >
                  <ConfBar value={v.confidence} />
                </td>
                {/* Weight */}
                <td
                  className="font-mono"
                  style={{
                    padding: '5px 8px',
                    fontSize: 9,
                    color: C.textSub,
                    borderBottom: `1px solid ${C.borderSub}`,
                    whiteSpace: 'nowrap',
                  }}
                >
                  {Math.round(v.weight * 100)}%
                </td>
                {/* Reasoning */}
                <td
                  className="font-mono"
                  style={{
                    padding: '5px 8px',
                    fontSize: 8.5,
                    color: C.textMuted,
                    borderBottom: `1px solid ${C.borderSub}`,
                    maxWidth: 180,
                    overflow: 'hidden',
                    textOverflow: 'ellipsis',
                    whiteSpace: 'nowrap',
                  }}
                  title={v.reasoning}
                >
                  {v.reasoning}
                </td>
              </tr>
            )) : (
              <tr>
                <td
                  colSpan={5}
                  className="font-mono"
                  style={{
                    padding: '14px 8px',
                    fontSize: 9,
                    color: C.textMuted,
                    textAlign: 'center',
                    borderBottom: `1px solid ${C.borderSub}`,
                  }}
                >
                  No votes available
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      {/* ── Reasoning summary ── */}
      <div
        style={{
          padding: '10px 14px',
          borderTop: `1px solid ${C.border}`,
          background: 'rgba(0,212,232,0.025)',
        }}
      >
        <div
          className="font-mono uppercase"
          style={{ fontSize: 7.5, color: C.textMuted, marginBottom: 4, letterSpacing: '0.5px' }}
        >
          Council Reasoning
        </div>
        <p
          className="font-mono"
          style={{ fontSize: 9, color: C.textSub, lineHeight: 1.55, margin: 0 }}
        >
          {d ? d.reasoning : '—'}
        </p>
      </div>

      {/* ── Action buttons ── */}
      <div
        style={{
          padding: '10px 14px',
          borderTop: `1px solid ${C.border}`,
          display: 'flex',
          gap: 8,
          background: C.bg0,
        }}
      >
        {/* Execute Trade — pass verdict data so parent can submit order */}
        <button
          onClick={d ? () => onExecute(d) : undefined}
          disabled={!d}
          className="flex-1 font-mono font-bold uppercase transition-all"
          style={{
            padding: '7px 12px',
            fontSize: 10,
            letterSpacing: '0.6px',
            background: d ? `linear-gradient(135deg, #006b40, ${C.green})` : C.bg2,
            color: d ? '#000' : C.textMuted,
            border: 'none',
            borderRadius: 3,
            cursor: d ? 'pointer' : 'not-allowed',
            boxShadow: d ? `0 2px 12px rgba(0,230,118,0.2)` : 'none',
            opacity: d ? 1 : 0.45,
          }}
          onMouseEnter={e => { if (d) { e.currentTarget.style.filter = 'brightness(1.2)'; e.currentTarget.style.transform = 'translateY(-1px)'; } }}
          onMouseLeave={e => { e.currentTarget.style.filter = 'brightness(1)'; e.currentTarget.style.transform = 'translateY(0)'; }}
        >
          Execute Trade
        </button>

        {/* Override — pass verdict data */}
        <button
          onClick={d ? () => onOverride(d) : undefined}
          disabled={!d}
          className="font-mono font-semibold uppercase transition-all"
          style={{
            padding: '7px 14px',
            fontSize: 10,
            letterSpacing: '0.6px',
            background: 'transparent',
            color: d ? C.amber : C.textMuted,
            border: `1px solid ${d ? C.amber : C.border}`,
            borderRadius: 3,
            cursor: d ? 'pointer' : 'not-allowed',
            opacity: d ? 1 : 0.45,
          }}
          onMouseEnter={e => { if (d) { e.currentTarget.style.background = 'rgba(255,171,0,0.1)'; e.currentTarget.style.transform = 'translateY(-1px)'; } }}
          onMouseLeave={e => { e.currentTarget.style.background = 'transparent'; e.currentTarget.style.transform = 'translateY(0)'; }}
        >
          Override
        </button>

        {/* Dismiss */}
        <button
          onClick={onDismiss}
          className="font-mono font-semibold uppercase transition-all"
          style={{
            padding: '7px 14px',
            fontSize: 10,
            letterSpacing: '0.6px',
            background: 'transparent',
            color: C.textMuted,
            border: `1px solid ${C.border}`,
            borderRadius: 3,
            cursor: 'pointer',
          }}
          onMouseEnter={e => { e.currentTarget.style.borderColor = C.textMuted; e.currentTarget.style.color = C.textSub; e.currentTarget.style.transform = 'translateY(-1px)'; }}
          onMouseLeave={e => { e.currentTarget.style.borderColor = C.border;    e.currentTarget.style.color = C.textMuted; e.currentTarget.style.transform = 'translateY(0)'; }}
        >
          Dismiss
        </button>
      </div>
    </div>
  );
}
