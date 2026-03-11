// =============================================================================
// RiskWidgets.jsx — Embodier Trader | Risk Intelligence Visualization Components
// Exports: CorrelationMatrixHeatmap, ParameterSweepsPanel
// =============================================================================
import React, { useState, useCallback, useRef } from 'react';

// ─── COLOR PALETTE (mirrors RiskIntelligence.jsx) ───────────────────────────
const C = {
  bg:      '#0B0E14',
  surface: '#111827',
  card:    '#1A1F2E',
  border:  '#1E293B',
  cyan:    '#00D9FF',
  green:   '#10B981',
  red:     '#EF4444',
  amber:   '#F59E0B',
  purple:  '#A855F7',
  teal:    '#14B8A6',
  text:    '#f8fafc',
  muted:   '#64748B',
  dimText: '#94A3B8',
};

// =============================================================================
// CORRELATION MATRIX HEATMAP
// =============================================================================

const DEFAULT_ASSETS = ['SPY', 'QQQ', 'AAPL', 'MSFT', 'GOOGL', 'TSLA', 'NVDA', 'AMD'];
const ZERO_CORR = Array.from({ length: 8 }, (_, i) =>
  Array.from({ length: 8 }, (_, j) => i === j ? 1.00 : 0)
);

/**
 * Map a correlation value → background color string.
 * Uses RGBA so cells layer naturally over the dark card background.
 */
function getCorrBg(val, isDiag) {
  if (isDiag) return 'rgba(0,217,255,0.10)';
  const abs = Math.abs(val);
  if (abs >= 0.85) return 'rgba(239,68,68,0.55)';
  if (abs >= 0.70) return 'rgba(239,68,68,0.30)';
  if (abs >= 0.55) return 'rgba(245,158,11,0.45)';
  if (abs >= 0.40) return 'rgba(245,158,11,0.25)';
  if (abs >= 0.20) return 'rgba(16,185,129,0.30)';
  return 'rgba(20,184,166,0.20)';
}

/**
 * Map a correlation value → text color class.
 */
function getCorrColor(val) {
  const abs = Math.abs(val);
  if (abs >= 0.8) return { bg: 'bg-red-500/80',   text: 'text-white' };
  if (abs >= 0.6) return { bg: 'bg-amber-500/60', text: 'text-white' };
  if (abs >= 0.4) return { bg: 'bg-amber-500/30', text: 'text-amber-100' };
  return            { bg: 'bg-emerald-500/30', text: 'text-emerald-100' };
}

/**
 * CorrelationMatrixHeatmap
 *
 * Props:
 *   assets      – string[]          (default: 8 tech symbols)
 *   correlations – number[][]        (default: zero matrix, diagonal = 1)
 *   className   – string
 */
export function CorrelationMatrixHeatmap({
  assets = DEFAULT_ASSETS,
  correlations = ZERO_CORR,
  className = '',
}) {
  // hoveredCell tracks {row, col} so we can highlight entire row + col
  const [hoveredCell, setHoveredCell] = useState(null);
  const [tooltip, setTooltip]         = useState(null);
  const containerRef                  = useRef(null);

  const n = assets.length;
  // Keep cells square at 40px minimum
  const CELL = 40;
  const LABEL_W = 44; // row label column width

  const handleMouseEnter = useCallback((ri, ci, val) => {
    setHoveredCell({ row: ri, col: ci });
    setTooltip({ row: ri, col: ci, val });
  }, []);

  const handleMouseLeave = useCallback(() => {
    setHoveredCell(null);
    setTooltip(null);
  }, []);

  // Legend data
  const legendStops = [
    { label: '-1.0', color: 'rgba(20,184,166,0.60)' },
    { label: '-0.5', color: 'rgba(16,185,129,0.55)' },
    { label:  '0.0', color: 'rgba(245,158,11,0.30)' },
    { label: '+0.5', color: 'rgba(239,68,68,0.35)' },
    { label: '+1.0', color: 'rgba(239,68,68,0.75)' },
  ];

  return (
    <div className={`select-none ${className}`} ref={containerRef}>
      {/* ── Tooltip ─────────────────────────────────────────────────────── */}
      {tooltip && (
        <div
          className="absolute z-50 pointer-events-none px-2 py-1 rounded text-[10px] font-mono font-bold border"
          style={{
            backgroundColor: C.card,
            borderColor: C.border,
            color: C.cyan,
            top: 0,
            right: 0,
          }}
        >
          {assets[tooltip.row]} vs {assets[tooltip.col]}:{' '}
          <span style={{ color: tooltip.row === tooltip.col ? C.dimText : (Math.abs(tooltip.val) >= 0.7 ? C.red : Math.abs(tooltip.val) >= 0.45 ? C.amber : C.green) }}>
            {tooltip.val.toFixed(2)}
          </span>
        </div>
      )}

      <div className="overflow-auto" style={{ position: 'relative' }}>
        {/* ── Grid using CSS Grid ───────────────────────────────────────── */}
        <div
          style={{
            display: 'grid',
            gridTemplateColumns: `${LABEL_W}px repeat(${n}, minmax(${CELL}px, 1fr))`,
            gridTemplateRows:    `auto repeat(${n}, minmax(${CELL}px, auto))`,
            gap: 1,
          }}
        >
          {/* Corner cell (empty) */}
          <div style={{ gridColumn: 1, gridRow: 1 }} />

          {/* Column headers (rotated 45°) */}
          {assets.map((sym, ci) => (
            <div
              key={`col-${ci}`}
              style={{
                gridColumn: ci + 2,
                gridRow: 1,
                display: 'flex',
                alignItems: 'flex-end',
                justifyContent: 'center',
                paddingBottom: 4,
                height: 48,
                opacity: hoveredCell && hoveredCell.col !== ci ? 0.45 : 1,
                transition: 'opacity 150ms',
              }}
            >
              <span
                style={{
                  display: 'inline-block',
                  transform: 'rotate(-45deg)',
                  transformOrigin: 'bottom center',
                  fontSize: 9,
                  fontFamily: 'ui-monospace,monospace',
                  fontWeight: 700,
                  color: hoveredCell?.col === ci ? C.cyan : C.dimText,
                  whiteSpace: 'nowrap',
                  transition: 'color 150ms',
                }}
              >
                {sym}
              </span>
            </div>
          ))}

          {/* Data rows */}
          {assets.map((rowSym, ri) => (
            <React.Fragment key={`row-${ri}`}>
              {/* Row header */}
              <div
                style={{
                  gridColumn: 1,
                  gridRow: ri + 2,
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'flex-end',
                  paddingRight: 6,
                  fontSize: 9,
                  fontFamily: 'ui-monospace,monospace',
                  fontWeight: 700,
                  color: hoveredCell?.row === ri ? C.cyan : C.dimText,
                  opacity: hoveredCell && hoveredCell.row !== ri ? 0.45 : 1,
                  transition: 'color 150ms, opacity 150ms',
                  whiteSpace: 'nowrap',
                }}
              >
                {rowSym}
              </div>

              {/* Data cells */}
              {(correlations[ri] ?? []).map((val, ci) => {
                const isDiag    = ri === ci;
                const safeVal   = val ?? 0;
                const isHovRow  = hoveredCell?.row === ri;
                const isHovCol  = hoveredCell?.col === ci;
                const isHovCell = isHovRow && isHovCol;
                const isHighlit = isHovRow || isHovCol;

                return (
                  <div
                    key={`cell-${ri}-${ci}`}
                    onMouseEnter={() => handleMouseEnter(ri, ci, safeVal)}
                    onMouseLeave={handleMouseLeave}
                    style={{
                      gridColumn: ci + 2,
                      gridRow: ri + 2,
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      minWidth:  CELL,
                      minHeight: CELL,
                      backgroundColor: getCorrBg(safeVal, isDiag),
                      border: isHovCell
                        ? `1.5px solid ${C.cyan}`
                        : isHighlit
                          ? `1px solid rgba(0,217,255,0.35)`
                          : '1px solid rgba(30,41,59,0.40)',
                      cursor: 'default',
                      opacity: hoveredCell && !isHighlit ? 0.55 : 1,
                      transition: 'opacity 120ms, border-color 120ms, background-color 120ms',
                      borderRadius: 2,
                      boxShadow: isHovCell ? `0 0 8px rgba(0,217,255,0.25)` : 'none',
                    }}
                  >
                    <span
                      style={{
                        fontSize: 8,
                        fontFamily: 'ui-monospace,monospace',
                        fontWeight: isDiag ? 400 : 700,
                        color: isDiag
                          ? C.dimText
                          : isHovCell
                            ? '#ffffff'
                            : '#e2e8f0',
                        letterSpacing: '-0.3px',
                        lineHeight: 1,
                      }}
                    >
                      {safeVal.toFixed(2)}
                    </span>
                  </div>
                );
              })}
            </React.Fragment>
          ))}
        </div>
      </div>

      {/* ── Color Legend ──────────────────────────────────────────────────── */}
      <div className="mt-3 pt-2" style={{ borderTop: `1px solid ${C.border}` }}>
        <div className="flex items-center gap-2">
          <span style={{ fontSize: 8, fontFamily: 'ui-monospace,monospace', color: C.muted, whiteSpace: 'nowrap' }}>
            CORR SCALE
          </span>

          {/* Gradient bar */}
          <div className="flex-1 relative" style={{ height: 10 }}>
            <div
              style={{
                position: 'absolute',
                inset: 0,
                borderRadius: 3,
                background:
                  'linear-gradient(to right, rgba(20,184,166,0.65), rgba(16,185,129,0.50), rgba(245,158,11,0.40), rgba(239,68,68,0.45), rgba(239,68,68,0.80))',
              }}
            />
          </div>

          {/* Tick labels */}
          <div className="flex items-center justify-between" style={{ width: '100%', position: 'absolute', pointerEvents: 'none' }}>
            {/* rendered as overlay, use a separate row instead */}
          </div>
        </div>

        {/* Tick labels row */}
        <div className="flex justify-between mt-0.5" style={{ paddingLeft: 52 }}>
          {['-1.0', '-0.5', '0.0', '+0.5', '+1.0'].map((tick) => (
            <span
              key={tick}
              style={{ fontSize: 7, fontFamily: 'ui-monospace,monospace', color: C.muted }}
            >
              {tick}
            </span>
          ))}
        </div>

        {/* Legend swatches */}
        <div className="flex items-center gap-3 mt-1.5 flex-wrap">
          {[
            { label: 'High (≥0.8)',   bg: 'rgba(239,68,68,0.55)',    text: '#EF4444' },
            { label: 'Med (0.5–0.8)', bg: 'rgba(245,158,11,0.40)',   text: '#F59E0B' },
            { label: 'Low (<0.5)',    bg: 'rgba(16,185,129,0.30)',   text: '#10B981' },
            { label: 'Diagonal',      bg: 'rgba(0,217,255,0.10)',    text: C.dimText },
          ].map(({ label, bg, text }) => (
            <div key={label} className="flex items-center gap-1">
              <div style={{ width: 10, height: 10, borderRadius: 2, backgroundColor: bg, border: `1px solid ${C.border}` }} />
              <span style={{ fontSize: 8, fontFamily: 'ui-monospace,monospace', color: C.muted }}>{label}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

// =============================================================================
// PARAMETER SWEEPS PANEL
// =============================================================================

const DEFAULT_PARAMETERS = [
  {
    id:      'maxPosition',
    label:   'Max Position Size',
    unit:    '%',
    min:     1,
    max:     10,
    step:    0.5,
    default: 5,
  },
  {
    id:      'sectorExposure',
    label:   'Sector Exposure',
    unit:    '%',
    min:     10,
    max:     50,
    step:    1,
    default: 30,
  },
  {
    id:      'corrThreshold',
    label:   'Correlation Threshold',
    unit:    '',
    min:     0.3,
    max:     0.9,
    step:    0.05,
    default: 0.7,
  },
  {
    id:      'atrMultiplier',
    label:   'ATR Multiplier',
    unit:    'x',
    min:     1.0,
    max:     5.0,
    step:    0.1,
    default: 2.5,
  },
  {
    id:      'stopLoss',
    label:   'Stop Loss',
    unit:    '%',
    min:     1,
    max:     10,
    step:    0.5,
    default: 3,
  },
];

const SWEEP_STYLES = `
  .risk-sweep-slider {
    -webkit-appearance: none;
    appearance: none;
    width: 100%;
    height: 4px;
    border-radius: 2px;
    outline: none;
    cursor: pointer;
    background: transparent;
  }
  .risk-sweep-slider::-webkit-slider-runnable-track {
    height: 4px;
    border-radius: 2px;
    background: transparent;
  }
  .risk-sweep-slider::-webkit-slider-thumb {
    -webkit-appearance: none;
    appearance: none;
    width: 14px;
    height: 14px;
    border-radius: 50%;
    background: #00D9FF;
    border: 2px solid #0B0E14;
    box-shadow: 0 0 6px rgba(0,217,255,0.55);
    cursor: pointer;
    margin-top: -5px;
    transition: transform 150ms, box-shadow 150ms;
  }
  .risk-sweep-slider::-webkit-slider-thumb:hover {
    transform: scale(1.2);
    box-shadow: 0 0 10px rgba(0,217,255,0.80);
  }
  .risk-sweep-slider::-moz-range-thumb {
    width: 14px;
    height: 14px;
    border-radius: 50%;
    background: #00D9FF;
    border: 2px solid #0B0E14;
    box-shadow: 0 0 6px rgba(0,217,255,0.55);
    cursor: pointer;
  }
  .risk-sweep-slider::-moz-range-track {
    height: 4px;
    border-radius: 2px;
    background: transparent;
  }
  .risk-sweep-slider:focus::-webkit-slider-thumb {
    box-shadow: 0 0 0 3px rgba(0,217,255,0.25), 0 0 8px rgba(0,217,255,0.60);
  }
`;

/**
 * A single styled range slider with track fill via CSS gradient.
 */
function SweepSlider({ param, value, onChange }) {
  const pct = ((value - param.min) / (param.max - param.min)) * 100;
  const trackBg = `linear-gradient(to right, rgba(0,217,255,0.80) 0%, rgba(0,217,255,0.80) ${pct}%, rgba(30,41,59,0.70) ${pct}%, rgba(30,41,59,0.70) 100%)`;

  const fmt = (v) => {
    const decimals = param.step < 0.1 ? 2 : param.step < 1 ? 1 : 0;
    return Number(v).toFixed(decimals);
  };

  return (
    <div className="space-y-1">
      <div className="flex items-center justify-between">
        <label
          htmlFor={`sweep-${param.id}`}
          style={{ fontSize: 10, fontFamily: 'ui-monospace,monospace', color: C.dimText, userSelect: 'none' }}
        >
          {param.label}
        </label>
        <span
          style={{
            fontSize: 11,
            fontFamily: 'ui-monospace,monospace',
            fontWeight: 700,
            color: C.cyan,
            minWidth: 44,
            textAlign: 'right',
          }}
        >
          {fmt(value)}{param.unit}
        </span>
      </div>

      <div className="relative flex items-center" style={{ height: 18 }}>
        {/* Track (visual only — rendered behind the native input) */}
        <div
          style={{
            position: 'absolute',
            left: 0,
            right: 0,
            height: 4,
            borderRadius: 2,
            background: trackBg,
            pointerEvents: 'none',
          }}
        />
        <input
          id={`sweep-${param.id}`}
          type="range"
          className="risk-sweep-slider"
          min={param.min}
          max={param.max}
          step={param.step}
          value={value}
          onChange={(e) => onChange(param.id, Number(e.target.value))}
          style={{ position: 'relative', zIndex: 1 }}
        />
      </div>

      {/* Min / Max ticks */}
      <div className="flex justify-between" style={{ marginTop: -1 }}>
        <span style={{ fontSize: 7, fontFamily: 'ui-monospace,monospace', color: C.muted }}>
          {fmt(param.min)}{param.unit}
        </span>
        <span style={{ fontSize: 7, fontFamily: 'ui-monospace,monospace', color: C.muted }}>
          {fmt(param.max)}{param.unit}
        </span>
      </div>
    </div>
  );
}

/**
 * ParameterSweepsPanel
 *
 * Props:
 *   onRun        – () => void
 *   onStop       – () => void
 *   parameters   – array of param config objects (optional override)
 *   className    – string
 */
export function ParameterSweepsPanel({
  onRun,
  onStop,
  parameters = DEFAULT_PARAMETERS,
  className = '',
}) {
  // Build initial values from defaults
  const initValues = Object.fromEntries(parameters.map((p) => [p.id, p.default]));
  const [values, setValues]       = useState(initValues);
  const [isRunning, setIsRunning] = useState(false);
  const [lastResult, setLastResult] = useState(null);

  const handleChange = useCallback((id, val) => {
    setValues((prev) => ({ ...prev, [id]: val }));
  }, []);

  const handleRun = useCallback(() => {
    setIsRunning(true);
    onRun?.(values);
  }, [onRun, values]);

  const handleStop = useCallback(() => {
    setIsRunning(false);
    onStop?.();
  }, [onStop]);

  const handleReset = useCallback(() => {
    setValues(initValues);
  }, [initValues]);

  const deltaPositive = lastResult ? parseFloat(lastResult.delta) >= 0 : false;

  return (
    <div className={`space-y-4 ${className}`}>
      {/* Inject slider styles */}
      <style>{SWEEP_STYLES}</style>

      {/* ── Parameter Sliders ───────────────────────────────────────────── */}
      <div className="space-y-3.5">
        {parameters.map((param) => (
          <SweepSlider
            key={param.id}
            param={param}
            value={values[param.id] ?? param.default}
            onChange={handleChange}
          />
        ))}
      </div>

      {/* ── Action Buttons ──────────────────────────────────────────────── */}
      <div
        className="pt-3"
        style={{ borderTop: `1px solid ${C.border}` }}
      >
        <div className="flex items-center gap-2">
          {/* Run Sweep */}
          <button
            onClick={handleRun}
            disabled={isRunning}
            style={{
              flex: 2,
              paddingTop: 8,
              paddingBottom: 8,
              borderRadius: 8,
              fontSize: 11,
              fontFamily: 'ui-monospace,monospace',
              fontWeight: 700,
              textTransform: 'uppercase',
              letterSpacing: '0.05em',
              cursor: isRunning ? 'not-allowed' : 'pointer',
              backgroundColor: isRunning ? 'rgba(0,217,255,0.12)' : 'rgba(0,217,255,0.18)',
              color: isRunning ? 'rgba(0,217,255,0.50)' : C.cyan,
              border: `1px solid ${isRunning ? 'rgba(0,217,255,0.15)' : 'rgba(0,217,255,0.45)'}`,
              boxShadow: isRunning ? 'none' : '0 0 10px rgba(0,217,255,0.15)',
              transition: 'all 150ms',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              gap: 6,
            }}
          >
            {isRunning ? (
              <>
                {/* Spinner */}
                <svg
                  width="12" height="12" viewBox="0 0 12 12"
                  style={{ animation: 'spin 0.8s linear infinite' }}
                >
                  <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
                  <circle cx="6" cy="6" r="4.5" stroke="currentColor" strokeWidth="1.5"
                    fill="none" strokeDasharray="20" strokeDashoffset="8"
                    strokeLinecap="round" />
                </svg>
                RUNNING…
              </>
            ) : (
              <>
                {/* Play icon */}
                <svg width="10" height="10" viewBox="0 0 10 10" fill="currentColor">
                  <path d="M2 1.5L9 5L2 8.5V1.5Z" />
                </svg>
                RUN SWEEP
              </>
            )}
          </button>

          {/* Stop */}
          <button
            onClick={handleStop}
            disabled={!isRunning}
            style={{
              flex: 1,
              paddingTop: 8,
              paddingBottom: 8,
              borderRadius: 8,
              fontSize: 11,
              fontFamily: 'ui-monospace,monospace',
              fontWeight: 700,
              textTransform: 'uppercase',
              letterSpacing: '0.05em',
              cursor: isRunning ? 'pointer' : 'not-allowed',
              backgroundColor: isRunning ? 'rgba(239,68,68,0.20)' : 'rgba(239,68,68,0.07)',
              color: isRunning ? '#EF4444' : 'rgba(239,68,68,0.35)',
              border: `1px solid ${isRunning ? 'rgba(239,68,68,0.45)' : 'rgba(239,68,68,0.15)'}`,
              transition: 'all 150ms',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              gap: 5,
            }}
          >
            {/* Stop icon */}
            <svg width="8" height="8" viewBox="0 0 8 8" fill="currentColor">
              <rect x="1" y="1" width="6" height="6" rx="1" />
            </svg>
            STOP
          </button>
        </div>

        {/* Reset Defaults */}
        <button
          onClick={handleReset}
          disabled={isRunning}
          style={{
            width: '100%',
            marginTop: 6,
            paddingTop: 5,
            paddingBottom: 5,
            borderRadius: 6,
            fontSize: 10,
            fontFamily: 'ui-monospace,monospace',
            fontWeight: 600,
            textTransform: 'uppercase',
            letterSpacing: '0.05em',
            cursor: isRunning ? 'not-allowed' : 'pointer',
            backgroundColor: 'rgba(100,116,139,0.10)',
            color: isRunning ? 'rgba(100,116,139,0.30)' : C.muted,
            border: `1px solid rgba(100,116,139,0.20)`,
            transition: 'all 150ms',
          }}
          onMouseEnter={(e) => { if (!isRunning) e.currentTarget.style.backgroundColor = 'rgba(100,116,139,0.18)'; }}
          onMouseLeave={(e) => { e.currentTarget.style.backgroundColor = 'rgba(100,116,139,0.10)'; }}
        >
          Reset Defaults
        </button>
      </div>

      {/* ── Last Sweep Results ──────────────────────────────────────────── */}
      <div
        className="rounded-lg p-3 space-y-1"
        style={{
          backgroundColor: lastResult
            ? (deltaPositive ? 'rgba(16,185,129,0.07)' : 'rgba(239,68,68,0.07)')
            : 'rgba(100,116,139,0.07)',
          border: `1px solid ${lastResult
            ? (deltaPositive ? 'rgba(16,185,129,0.25)' : 'rgba(239,68,68,0.25)')
            : 'rgba(100,116,139,0.20)'}`,
        }}
      >
        <div className="flex items-center justify-between">
          <span style={{ fontSize: 9, fontFamily: 'ui-monospace,monospace', color: C.muted, textTransform: 'uppercase', letterSpacing: '0.06em' }}>
            Last Sweep
          </span>
          {lastResult && (
            <span
              style={{
                fontSize: 9,
                fontFamily: 'ui-monospace,monospace',
                fontWeight: 700,
                color: deltaPositive ? C.green : C.red,
                backgroundColor: deltaPositive ? 'rgba(16,185,129,0.15)' : 'rgba(239,68,68,0.15)',
                padding: '1px 6px',
                borderRadius: 4,
              }}
            >
              {lastResult.delta}
            </span>
          )}
        </div>

        {lastResult ? (
          <div
            style={{
              fontSize: 12,
              fontFamily: 'ui-monospace,monospace',
              fontWeight: 700,
              color: C.text,
              display: 'flex',
              alignItems: 'center',
              gap: 6,
            }}
          >
            <span style={{ color: C.muted }}>Sharpe</span>
            <span style={{ color: C.dimText }}>{lastResult.sharpeFrom.toFixed(2)}</span>
            <svg width="14" height="10" viewBox="0 0 14 10" fill="none" style={{ flexShrink: 0 }}>
              <path d="M1 5H13M9 1L13 5L9 9" stroke={deltaPositive ? C.green : C.red} strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
            </svg>
            <span style={{ color: deltaPositive ? C.green : C.red }}>
              {lastResult.sharpeTo.toFixed(2)}
            </span>
          </div>
        ) : (
          <div
            style={{
              fontSize: 12,
              fontFamily: 'ui-monospace,monospace',
              fontWeight: 700,
              color: C.muted,
            }}
          >
            No results yet
          </div>
        )}

        <div style={{ fontSize: 8, fontFamily: 'ui-monospace,monospace', color: C.muted, marginTop: 2 }}>
          {isRunning
            ? 'Sweep in progress — parameters locked…'
            : 'Click "Run Sweep" to optimize with current parameters'}
        </div>
      </div>
    </div>
  );
}

// =============================================================================
// DEFAULT EXPORT — convenience re-export of both
// =============================================================================
export default { CorrelationMatrixHeatmap, ParameterSweepsPanel };
