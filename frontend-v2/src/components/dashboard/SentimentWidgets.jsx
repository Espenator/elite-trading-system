// SentimentWidgets.jsx
// Pure SVG/CSS visualization components for the Sentiment Intelligence page.
// No external chart libraries — all rendering is native SVG and inline CSS.
// Palette: #0B0E14 bg | #111827 surface | #10B981 green | #EF4444 red
//          #06B6D4 cyan | #F59E0B amber | #8B5CF6 purple

import React, { useMemo } from 'react';

// ─────────────────────────────────────────────
// 1. SectorTreemap
// Finviz-style sector/stock heatmap.
// ─────────────────────────────────────────────

/** Returns a CSS rgba color based on % change, matching the page's getHeatmapCellBg */
function treemapCellColor(pct) {
  if (pct == null) return 'rgba(30,41,59,0.5)';
  if (pct >  3)   return 'rgba(16,185,129,0.80)';  // strong green
  if (pct >  1.5) return 'rgba(16,185,129,0.60)';
  if (pct >  0)   return 'rgba(16,185,129,0.38)';
  if (pct > -1.5) return 'rgba(239,68,68,0.38)';
  if (pct > -3)   return 'rgba(239,68,68,0.60)';
  return 'rgba(239,68,68,0.80)';                    // strong red
}

export function SectorTreemap({ data = [], width = '100%', height = 300 }) {
  // Group stocks by sector
  const sectors = useMemo(() => {
    const map = {};
    data.forEach((item) => {
      if (!map[item.sector]) map[item.sector] = [];
      map[item.sector].push(item);
    });
    return Object.entries(map); // [ [sectorName, stocks[]] ]
  }, [data]);

  // Empty state
  if (data.length === 0) {
    return (
      <div
        style={{
          width,
          minHeight: height,
          backgroundColor: '#0B0E14',
          borderRadius: '8px',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
        }}
      >
        <span
          style={{
            color: '#374151',
            fontSize: '12px',
            fontFamily: 'monospace',
            letterSpacing: '0.05em',
          }}
        >
          No sector data
        </span>
      </div>
    );
  }

  // Build grid-template-columns proportional to sector stock count
  const totalStocks = data.length;
  const templateColumns = sectors
    .map(([, stocks]) => `${(stocks.length / totalStocks) * 100}fr`)
    .join(' ');

  return (
    <div
      style={{
        width,
        minHeight: height,
        display: 'grid',
        gridTemplateColumns: templateColumns,
        gap: '2px',
        backgroundColor: '#0B0E14',
        borderRadius: '8px',
        overflow: 'hidden',
        padding: '2px',
      }}
    >
      {sectors.map(([sectorName, stocks]) => (
        <div key={sectorName} style={{ display: 'flex', flexDirection: 'column', gap: '2px' }}>
          {/* Sector header */}
          <div
            style={{
              padding: '4px 6px 2px',
              backgroundColor: 'rgba(255,255,255,0.04)',
              borderBottom: '1px solid rgba(255,255,255,0.06)',
            }}
          >
            <span
              style={{
                color: '#94a3b8',
                fontSize: '8px',
                fontWeight: 700,
                letterSpacing: '0.05em',
                textTransform: 'uppercase',
                fontFamily: 'monospace',
              }}
            >
              {sectorName}
            </span>
          </div>

          {/* Stock cells */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: '2px', flex: 1 }}>
            {stocks.map((stock) => {
              const isPositive = stock.change_pct >= 0;
              return (
                <div
                  key={stock.symbol}
                  style={{
                    minHeight: '40px',
                    flex: 1,
                    backgroundColor: treemapCellColor(stock.change_pct),
                    display: 'flex',
                    flexDirection: 'column',
                    alignItems: 'center',
                    justifyContent: 'center',
                    cursor: 'pointer',
                    borderRadius: '3px',
                    transition: 'filter 0.15s',
                    userSelect: 'none',
                    padding: '2px',
                  }}
                  onMouseEnter={(e) => (e.currentTarget.style.filter = 'brightness(1.25)')}
                  onMouseLeave={(e) => (e.currentTarget.style.filter = 'none')}
                >
                  <span
                    style={{
                      color: '#ffffff',
                      fontSize: '9px',
                      fontWeight: 700,
                      letterSpacing: '0.04em',
                      lineHeight: 1.1,
                    }}
                  >
                    {stock.symbol}
                  </span>
                  <span
                    style={{
                      fontSize: '7px',
                      fontWeight: 600,
                      fontFamily: 'monospace',
                      color: isPositive ? '#86efac' : '#fca5a5',
                      lineHeight: 1.2,
                    }}
                  >
                    {isPositive ? '+' : ''}
                    {stock.change_pct.toFixed(1)}%
                  </span>
                </div>
              );
            })}
          </div>
        </div>
      ))}
    </div>
  );
}

// ─────────────────────────────────────────────
// 2. MultiFactorRadar
// Pure SVG spider/radar chart.
// ─────────────────────────────────────────────

/** Convert polar (angle in radians, radius) to Cartesian coords relative to a centre */
function polarToCartesian(cx, cy, r, angleRad) {
  return {
    x: cx + r * Math.cos(angleRad),
    y: cy + r * Math.sin(angleRad),
  };
}

/** Build an SVG polygon points string from an array of {x,y} */
function pointsString(pts) {
  return pts.map((p) => `${p.x.toFixed(2)},${p.y.toFixed(2)}`).join(' ');
}

// Default axis structure shown when no data is provided
const DEFAULT_RADAR_AXES = [
  'Technical',
  'Fundamental',
  'Sentiment',
  'Momentum',
  'Volume',
  'Options Flow',
];

export function MultiFactorRadar({ data = [], fillColor = '#06B6D4' }) {
  const cx = 150;
  const cy = 150;
  const maxR = 95; // outer radius in SVG units

  // Determine axes: use data axes if available, otherwise fall back to default axis labels at value 0
  const hasData = data.length > 0;
  const axisLabels = hasData ? data.map((d) => d.axis) : DEFAULT_RADAR_AXES;
  const n = axisLabels.length;

  // Start at top (-π/2) and go clockwise
  const angles = axisLabels.map((_, i) => (2 * Math.PI * i) / n - Math.PI / 2);

  // Grid rings at 25%, 50%, 75%, 100%
  const gridLevels = [0.25, 0.5, 0.75, 1.0];

  // Data polygon vertices — zero radius when no data
  const dataPoints = axisLabels.map((_, i) => {
    const value = hasData ? data[i].value : 0;
    const r = (value / 100) * maxR;
    return polarToCartesian(cx, cy, r, angles[i]);
  });

  // Axis endpoints (at 100% radius)
  const axisEndpoints = angles.map((a) => polarToCartesian(cx, cy, maxR, a));

  // Label positions — slightly beyond the axis endpoint
  const labelOffset = 18;
  const labelPositions = angles.map((a, i) => {
    const pt = polarToCartesian(cx, cy, maxR + labelOffset, a);
    // Horizontal text-anchor based on position
    const cos = Math.cos(a);
    let anchor = 'middle';
    if (cos < -0.3) anchor = 'end';
    else if (cos > 0.3) anchor = 'start';
    return { ...pt, label: axisLabels[i], anchor };
  });

  // Fill color with opacity
  const fillHex = fillColor; // e.g. '#06B6D4'
  // Convert hex -> rgba for polygon fill
  const fillRgba = `${fillHex}4D`; // 30% opacity hex suffix

  return (
    <svg
      viewBox="0 0 300 300"
      width="100%"
      style={{ display: 'block', overflow: 'visible' }}
      aria-label="Multi-factor radar chart"
    >
      {/* ── Grid rings ── */}
      {gridLevels.map((level) => {
        const ringPts = angles.map((a) => polarToCartesian(cx, cy, maxR * level, a));
        return (
          <polygon
            key={level}
            points={pointsString(ringPts)}
            fill="none"
            stroke="#1f2937"
            strokeWidth="1"
          />
        );
      })}

      {/* ── Grid level labels (25/50/75/100) on first axis ── */}
      {gridLevels.map((level) => {
        const pt = polarToCartesian(cx, cy, maxR * level, angles[0]);
        return (
          <text
            key={`lbl-${level}`}
            x={pt.x + 3}
            y={pt.y - 2}
            fontSize="6"
            fill="#374151"
            textAnchor="start"
          >
            {level * 100}
          </text>
        );
      })}

      {/* ── Axis lines ── */}
      {axisEndpoints.map((ep, i) => (
        <line
          key={`axis-${i}`}
          x1={cx}
          y1={cy}
          x2={ep.x}
          y2={ep.y}
          stroke="#1f2937"
          strokeWidth="1"
        />
      ))}

      {/* ── Filled data polygon (only when data is present) ── */}
      {hasData && (
        <polygon
          points={pointsString(dataPoints)}
          fill={fillRgba}
          stroke={fillColor}
          strokeWidth="1.5"
          strokeLinejoin="round"
        />
      )}

      {/* ── Data point circles (only when data is present) ── */}
      {hasData && dataPoints.map((pt, i) => (
        <circle key={`dot-${i}`} cx={pt.x} cy={pt.y} r="3.5" fill={fillColor} />
      ))}

      {/* ── Axis labels ── */}
      {labelPositions.map((lp, i) => (
        <text
          key={`label-${i}`}
          x={lp.x}
          y={lp.y}
          fontSize="9"
          fill="#94a3b8"
          textAnchor={lp.anchor}
          dominantBaseline="middle"
        >
          {lp.label}
        </text>
      ))}

      {/* ── Value badges at data points (only when data is present) ── */}
      {hasData && dataPoints.map((pt, i) => (
        <text
          key={`val-${i}`}
          x={pt.x}
          y={pt.y - 6}
          fontSize="7"
          fill={fillColor}
          textAnchor="middle"
          fontFamily="monospace"
        >
          {data[i].value}
        </text>
      ))}
    </svg>
  );
}

// ─────────────────────────────────────────────
// 3. ScannerStatusMatrix
// Symbol × data-source dot grid.
// ─────────────────────────────────────────────

const DEFAULT_SYMBOLS = ['AAPL', 'MSFT', 'GOOGL', 'TSLA', 'NVDA', 'META', 'AMZN', 'JPM'];
const DEFAULT_SOURCES = ['Alpaca', 'Finviz', 'EDGAR', 'Whale', 'News', 'Social', 'Options'];

const STATUS_COLORS = {
  ok:    '#10B981',  // green
  warn:  '#F59E0B',  // amber
  error: '#EF4444',  // red
  off:   '#374151',  // gray
};

const STATUS_LABELS = {
  ok:    'Active',
  warn:  'Delayed',
  error: 'Error',
  off:   'Not configured',
};

export function ScannerStatusMatrix({
  symbols = DEFAULT_SYMBOLS,
  sources = DEFAULT_SOURCES,
  statusMap = {},
}) {
  const resolvedMap = useMemo(
    () => statusMap,
    [statusMap],
  );

  return (
    <div
      style={{
        overflowX: 'auto',
        backgroundColor: '#111827',
        borderRadius: '8px',
        padding: '8px',
      }}
    >
      {/* Column headers */}
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: `56px repeat(${sources.length}, 1fr)`,
          gap: '2px',
          marginBottom: '4px',
        }}
      >
        {/* Empty corner */}
        <div />
        {sources.map((src) => (
          <div
            key={src}
            style={{
              textAlign: 'center',
              color: '#64748b',
              fontSize: '8px',
              fontFamily: 'monospace',
              whiteSpace: 'nowrap',
              overflow: 'hidden',
              textOverflow: 'ellipsis',
            }}
            title={src}
          >
            {src.length > 6 ? src.slice(0, 5) + '…' : src}
          </div>
        ))}
      </div>

      {/* Data rows */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: '3px' }}>
        {symbols.map((sym) => (
          <div
            key={sym}
            style={{
              display: 'grid',
              gridTemplateColumns: `56px repeat(${sources.length}, 1fr)`,
              gap: '2px',
              alignItems: 'center',
            }}
          >
            {/* Row label */}
            <span
              style={{
                color: '#e2e8f0',
                fontSize: '8px',
                fontFamily: 'monospace',
                fontWeight: 700,
                overflow: 'hidden',
                textOverflow: 'ellipsis',
                whiteSpace: 'nowrap',
              }}
            >
              {sym}
            </span>

            {/* Status dots */}
            {sources.map((src) => {
              const status = resolvedMap[`${sym}-${src}`] || 'off';
              const color = STATUS_COLORS[status] || STATUS_COLORS.off;
              return (
                <div
                  key={src}
                  title={`${sym} / ${src}: ${STATUS_LABELS[status]}`}
                  style={{
                    display: 'flex',
                    justifyContent: 'center',
                    alignItems: 'center',
                  }}
                >
                  <div
                    style={{
                      width: '8px',
                      height: '8px',
                      borderRadius: '50%',
                      backgroundColor: color,
                      boxShadow:
                        status === 'ok'
                          ? `0 0 5px ${color}80`
                          : status === 'error'
                          ? `0 0 5px ${color}80`
                          : 'none',
                      flexShrink: 0,
                    }}
                  />
                </div>
              );
            })}
          </div>
        ))}
      </div>

      {/* Legend */}
      <div
        style={{
          display: 'flex',
          gap: '10px',
          marginTop: '8px',
          paddingTop: '6px',
          borderTop: '1px solid rgba(255,255,255,0.05)',
          flexWrap: 'wrap',
        }}
      >
        {Object.entries(STATUS_COLORS).map(([status, color]) => (
          <div
            key={status}
            style={{ display: 'flex', alignItems: 'center', gap: '4px' }}
          >
            <div
              style={{
                width: '6px',
                height: '6px',
                borderRadius: '50%',
                backgroundColor: color,
              }}
            />
            <span
              style={{
                color: '#64748b',
                fontSize: '7px',
                fontFamily: 'monospace',
              }}
            >
              {STATUS_LABELS[status]}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}

// ─────────────────────────────────────────────
// 4. PredictionMarketCard
// Individual prediction market card.
// ─────────────────────────────────────────────

/** Small sparkline rendered as a pure SVG polyline */
function Sparkline({ points = [], trend = 'flat', width = 48, height = 20 }) {
  // When no real data is provided, draw a flat line at zero
  const hasPoints = points.length >= 2;

  const strokeColor =
    trend === 'up' ? '#10B981' : trend === 'down' ? '#EF4444' : '#94a3b8';

  if (!hasPoints) {
    // Flat line at the vertical midpoint
    const y = (height / 2).toFixed(1);
    return (
      <svg width={width} height={height} viewBox={`0 0 ${width} ${height}`} style={{ overflow: 'visible' }}>
        <line
          x1="0"
          y1={y}
          x2={width}
          y2={y}
          stroke="#374151"
          strokeWidth="1.5"
          strokeLinecap="round"
        />
      </svg>
    );
  }

  const minV = Math.min(...points);
  const maxV = Math.max(...points);
  const range = Math.max(maxV - minV, 1);

  // Normalise to SVG coords
  const svgPoints = points.map((v, i) => {
    const x = (i / (points.length - 1)) * width;
    const y = height - ((v - minV) / range) * (height - 2) - 1;
    return `${x.toFixed(1)},${y.toFixed(1)}`;
  });

  return (
    <svg width={width} height={height} viewBox={`0 0 ${width} ${height}`} style={{ overflow: 'visible' }}>
      <polyline
        points={svgPoints.join(' ')}
        fill="none"
        stroke={strokeColor}
        strokeWidth="1.5"
        strokeLinejoin="round"
        strokeLinecap="round"
      />
    </svg>
  );
}

/** Trend arrow icon */
function TrendArrow({ trend }) {
  if (trend === 'up')
    return (
      <svg width="12" height="12" viewBox="0 0 12 12">
        <polyline
          points="2,9 6,3 10,9"
          fill="none"
          stroke="#10B981"
          strokeWidth="2"
          strokeLinecap="round"
          strokeLinejoin="round"
        />
      </svg>
    );
  if (trend === 'down')
    return (
      <svg width="12" height="12" viewBox="0 0 12 12">
        <polyline
          points="2,3 6,9 10,3"
          fill="none"
          stroke="#EF4444"
          strokeWidth="2"
          strokeLinecap="round"
          strokeLinejoin="round"
        />
      </svg>
    );
  return (
    <svg width="12" height="12" viewBox="0 0 12 12">
      <line
        x1="2" y1="6" x2="10" y2="6"
        stroke="#94a3b8"
        strokeWidth="2"
        strokeLinecap="round"
      />
    </svg>
  );
}

export function PredictionMarketCard({
  question = '',
  probability = 0,
  volume = '0',
  trend = 'flat',
  sparklinePoints = [],
  className = '',
}) {
  const clamp = Math.max(0, Math.min(100, probability));
  const trendColor =
    trend === 'up' ? '#10B981' : trend === 'down' ? '#EF4444' : '#94a3b8';

  // Progress bar: cyan → green gradient
  const gradId = `pmGrad-${question.slice(0, 8).replace(/\W/g, '')}`;

  return (
    <div
      className={className}
      style={{
        backgroundColor: '#111827',
        border: '1px solid #1e293b',
        borderRadius: '6px',
        padding: '12px',
        display: 'flex',
        flexDirection: 'column',
        gap: '8px',
        minWidth: 0,
      }}
    >
      {/* Question text */}
      <p
        style={{
          color: '#e2e8f0',
          fontSize: '11px',
          fontWeight: 500,
          lineHeight: 1.4,
          margin: 0,
        }}
      >
        {question}
      </p>

      {/* Probability row */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
          {/* Large probability display */}
          <span
            style={{
              fontSize: '24px',
              fontWeight: 800,
              fontFamily: 'monospace',
              color: '#06B6D4',
              lineHeight: 1,
            }}
          >
            {clamp}%
          </span>
          {/* Trend arrow */}
          <TrendArrow trend={trend} />
        </div>

        {/* Sparkline */}
        <Sparkline points={sparklinePoints} trend={trend} width={56} height={22} />
      </div>

      {/* Progress bar (cyan → green gradient) */}
      <div>
        <svg width="100%" height="6" style={{ display: 'block', borderRadius: '3px', overflow: 'hidden' }}>
          <defs>
            <linearGradient id={gradId} x1="0" y1="0" x2="1" y2="0">
              <stop offset="0%" stopColor="#06B6D4" />
              <stop offset="100%" stopColor="#10B981" />
            </linearGradient>
          </defs>
          {/* Background track */}
          <rect x="0" y="0" width="100%" height="6" fill="#1f2937" rx="3" />
          {/* Filled portion — use foreignObject trick via rect with % width via inline style */}
          <rect
            x="0"
            y="0"
            width={`${clamp}%`}
            height="6"
            fill={`url(#${gradId})`}
            rx="3"
          />
        </svg>
      </div>

      {/* Footer: volume + trend label */}
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
        }}
      >
        <span style={{ color: '#64748b', fontSize: '9px', fontFamily: 'monospace' }}>
          Vol: {volume}
        </span>
        <span
          style={{
            fontSize: '9px',
            fontFamily: 'monospace',
            fontWeight: 700,
            color: trendColor,
            textTransform: 'uppercase',
            letterSpacing: '0.05em',
          }}
        >
          {trend === 'up' ? '▲ Bullish' : trend === 'down' ? '▼ Bearish' : '─ Neutral'}
        </span>
      </div>
    </div>
  );
}
