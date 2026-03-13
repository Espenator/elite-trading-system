import React from 'react';

// ─── COLOR PALETTE ────────────────────────────────────────────────────────────
// #0B0E14  background
// #111827  surface
// #10B981  emerald / green
// #EF4444  red
// #06B6D4  cyan
// #F59E0B  amber
// #8B5CF6  purple

// ─────────────────────────────────────────────────────────────────────────────
// 1. TradingGradeHero
//    Large circular badge with animated draw-on SVG ring showing the grade.
// ─────────────────────────────────────────────────────────────────────────────

export function TradingGradeHero({ grade = '—', score = 0, size = 120 }) {
  const gradeColors = {
    A: '#10B981',
    B: '#06B6D4',
    C: '#F59E0B',
    D: '#F97316',
    F: '#EF4444',
  };

  const color = gradeColors[grade] || '#4b5563';
  const strokeWidth = 7;
  const r = (size - strokeWidth * 2) / 2;
  const circ = 2 * Math.PI * r;
  const pct = Math.max(0, Math.min(score / 100, 1));
  const offset = circ * (1 - pct);

  // Glow color for box-shadow equivalent via filter
  const glowId = `glow-${grade}`;

  return (
    <div className="flex flex-col items-center gap-1">
      {/* SVG ring + centered letter */}
      <div className="relative flex items-center justify-center" style={{ width: size, height: size }}>
        <svg
          width={size}
          height={size}
          viewBox={`0 0 ${size} ${size}`}
          style={{ transform: 'rotate(-90deg)' }}
          aria-label={`Trading grade ${grade}, score ${score} out of 100`}
        >
          <defs>
            <filter id={glowId} x="-50%" y="-50%" width="200%" height="200%">
              <feGaussianBlur stdDeviation="3" result="blur" />
              <feMerge>
                <feMergeNode in="blur" />
                <feMergeNode in="SourceGraphic" />
              </feMerge>
            </filter>
          </defs>

          {/* Background track */}
          <circle
            cx={size / 2}
            cy={size / 2}
            r={r}
            fill="none"
            stroke="#1f2937"
            strokeWidth={strokeWidth}
          />

          {/* Colored progress arc */}
          <circle
            cx={size / 2}
            cy={size / 2}
            r={r}
            fill="none"
            stroke={color}
            strokeWidth={strokeWidth}
            strokeDasharray={circ}
            strokeDashoffset={offset}
            strokeLinecap="round"
            filter={`url(#${glowId})`}
            style={{
              transition: 'stroke-dashoffset 1.2s cubic-bezier(0.4, 0, 0.2, 1)',
            }}
          />
        </svg>

        {/* Grade letter — absolutely centered over the SVG */}
        <span
          className="absolute font-bold text-white font-mono select-none"
          style={{
            fontSize: size * 0.28,
            lineHeight: 1,
            textShadow: `0 0 20px ${color}60`,
          }}
        >
          {grade}
        </span>
      </div>

      {/* Labels */}
      <div
        className="text-[10px] uppercase tracking-widest font-semibold"
        style={{ color: '#6b7280', letterSpacing: '0.12em' }}
      >
        Trading Grade
      </div>
      <div className="text-[10px] font-mono" style={{ color: color }}>
        Score:&nbsp;{score}/100
      </div>
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// 2. ReturnsHeatmapCalendar
//    Multi-year monthly returns heatmap grid.
// ─────────────────────────────────────────────────────────────────────────────

const MONTH_ABBRS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];

function heatmapCellStyle(value) {
  if (value === null || value === undefined) {
    return { bg: '#111827', text: '#374151', label: '—' };
  }
  if (value >= 5)  return { bg: 'rgba(16,185,129,0.45)', text: '#6ee7b7', label: `+${value.toFixed(1)}%` };
  if (value >= 0)  return { bg: 'rgba(16,185,129,0.18)', text: '#34d399', label: `+${value.toFixed(1)}%` };
  if (value >= -5) return { bg: 'rgba(239,68,68,0.18)',  text: '#fca5a5', label: `${value.toFixed(1)}%` };
  return             { bg: 'rgba(239,68,68,0.42)',  text: '#f87171', label: `${value.toFixed(1)}%` };
}

export function ReturnsHeatmapCalendar({ data = [], className = '', onCellClick }) {
  // Build lookup: { year: { month: return_pct } }
  const lookup = {};
  const yearsSet = new Set();
  for (const row of data) {
    yearsSet.add(row.year);
    if (!lookup[row.year]) lookup[row.year] = {};
    lookup[row.year][row.month] = row.return_pct;
  }

  // When no data, show current year as an empty placeholder row
  if (yearsSet.size === 0) {
    yearsSet.add(new Date().getFullYear());
  }

  const years = Array.from(yearsSet).sort((a, b) => a - b);

  return (
    <div className={`w-full font-mono ${className}`}>
      {/* Column headers */}
      <div className="grid gap-px mb-1" style={{ gridTemplateColumns: '36px repeat(12, 1fr)' }}>
        <div />
        {MONTH_ABBRS.map((m) => (
          <div
            key={m}
            className="text-center text-[8px] uppercase tracking-wider"
            style={{ color: '#4b5563' }}
          >
            {m}
          </div>
        ))}
      </div>

      {/* Year rows */}
      <div className="flex flex-col gap-px">
        {years.map((year) => (
          <div
            key={year}
            className="grid gap-px"
            style={{ gridTemplateColumns: '36px repeat(12, 1fr)' }}
          >
            {/* Year label */}
            <div
              className="flex items-center text-[9px] font-semibold pr-1"
              style={{ color: '#6b7280' }}
            >
              {year}
            </div>

            {/* Month cells */}
            {MONTH_ABBRS.map((_, mIdx) => {
              const month = mIdx + 1;
              const val = lookup[year]?.[month] ?? null;
              const { bg, text, label } = heatmapCellStyle(val);
              return (
                <div
                  key={month}
                  role={onCellClick ? 'button' : undefined}
                  tabIndex={onCellClick ? 0 : undefined}
                  onClick={onCellClick ? () => onCellClick(year, month) : undefined}
                  onKeyDown={onCellClick ? (e) => { if (e.key === 'Enter' || e.key === ' ') onCellClick(year, month); } : undefined}
                  className={`flex items-center justify-center rounded-sm ${onCellClick ? 'cursor-pointer hover:ring-1 hover:ring-cyan-500/50' : ''}`}
                  style={{
                    backgroundColor: bg,
                    color: text,
                    fontSize: '8px',
                    height: 22,
                    lineHeight: 1,
                    transition: 'background-color 0.2s ease',
                  }}
                  title={`${year} ${MONTH_ABBRS[mIdx]}: ${val !== null ? `${val > 0 ? '+' : ''}${val.toFixed(2)}%` : 'No data'}${onCellClick ? ' — Click for day\'s trades' : ''}`}
                >
                  {label}
                </div>
              );
            })}
          </div>
        ))}
      </div>

      {/* Legend */}
      <div className="flex items-center gap-3 mt-2 justify-end">
        {[
          { bg: 'rgba(239,68,68,0.42)',  text: '#f87171', label: '< -5%' },
          { bg: 'rgba(239,68,68,0.18)',  text: '#fca5a5', label: '-5–0%' },
          { bg: 'rgba(16,185,129,0.18)', text: '#34d399', label: '0–5%' },
          { bg: 'rgba(16,185,129,0.45)', text: '#6ee7b7', label: '> 5%' },
          { bg: '#111827',               text: '#374151', label: 'N/A' },
        ].map(({ bg, text, label }) => (
          <div key={label} className="flex items-center gap-1">
            <div
              className="rounded-sm"
              style={{ width: 10, height: 10, backgroundColor: bg, border: '1px solid rgba(255,255,255,0.05)' }}
            />
            <span style={{ fontSize: '8px', color: '#6b7280' }}>{label}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// 3. ConcentricAIDial
//    Apple-fitness-style concentric rings for AI model metrics.
// ─────────────────────────────────────────────────────────────────────────────

function ConcentricRing({ cx, cy, r, trackColor, fillColor, value, strokeWidth, index }) {
  const circ = 2 * Math.PI * r;
  const dashoffset = circ * (1 - Math.max(0, Math.min(value / 100, 1)));
  const delay = index * 0.15;

  return (
    <g>
      {/* Background track */}
      <circle
        cx={cx}
        cy={cy}
        r={r}
        fill="none"
        stroke={trackColor}
        strokeWidth={strokeWidth}
        opacity={0.25}
      />
      {/* Value fill */}
      <circle
        cx={cx}
        cy={cy}
        r={r}
        fill="none"
        stroke={fillColor}
        strokeWidth={strokeWidth}
        strokeDasharray={circ}
        strokeDashoffset={dashoffset}
        strokeLinecap="round"
        style={{
          transition: `stroke-dashoffset 1.1s cubic-bezier(0.4, 0, 0.2, 1) ${delay}s`,
          filter: `drop-shadow(0 0 4px ${fillColor}80)`,
        }}
      />
    </g>
  );
}

export function ConcentricAIDial({ metrics = [], centerLabel }) {
  const svgSize = 180;
  const cx = svgSize / 2;
  const cy = svgSize / 2;
  const ringGap = 14;        // gap between rings
  const strokeWidth = 10;
  const outerR = (svgSize / 2) - strokeWidth / 2 - 4;

  // Overall AI score = weighted average of metric values; 0 when no metrics
  const overallScore = metrics.length > 0
    ? Math.round(metrics.reduce((sum, m) => sum + m.value, 0) / metrics.length)
    : 0;

  // Grade label for the overall score
  const overallGrade = metrics.length === 0
    ? 'N/A'
    : overallScore >= 90 ? 'A+'
    : overallScore >= 80 ? 'A'
    : overallScore >= 70 ? 'B'
    : overallScore >= 60 ? 'C'
    : 'D';

  // Rings from outside in: index 0 = outermost.
  // When no metrics, render 4 empty placeholder tracks so the dial structure is visible.
  const PLACEHOLDER_RING_COUNT = 4;
  const rings = metrics.length > 0
    ? metrics.map((m, i) => ({ ...m, r: outerR - i * (strokeWidth + ringGap) }))
    : Array.from({ length: PLACEHOLDER_RING_COUNT }, (_, i) => ({
        name: `ring-${i}`,
        value: 0,
        color: '#374151',
        r: outerR - i * (strokeWidth + ringGap),
      }));

  return (
    <div className="flex flex-col items-center gap-3">
      {/* Dial SVG */}
      <div className="relative flex items-center justify-center">
        <svg
          width={svgSize}
          height={svgSize}
          viewBox={`0 0 ${svgSize} ${svgSize}`}
          style={{ transform: 'rotate(-90deg)' }}
          aria-label={`AI performance dial, overall score ${overallScore}`}
        >
          {rings.map((ring, i) => (
            <ConcentricRing
              key={ring.name}
              cx={cx}
              cy={cy}
              r={ring.r}
              trackColor="#374151"
              fillColor={ring.color}
              value={ring.value}
              strokeWidth={strokeWidth}
              index={i}
            />
          ))}
        </svg>

        {/* Center score overlay — NOT rotated */}
        <div
          className="absolute flex flex-col items-center justify-center"
          style={{ pointerEvents: 'none' }}
        >
          {centerLabel ? (
            <>
              <span
                className="font-bold font-mono leading-none"
                style={{ fontSize: 22, color: '#f1f5f9' }}
              >
                {centerLabel}
              </span>
            </>
          ) : (
            <>
              <span
                className="font-bold font-mono leading-none"
                style={{ fontSize: 28, color: '#f1f5f9' }}
              >
                {overallScore}
              </span>
              <span
                className="font-mono text-[9px] uppercase tracking-widest mt-0.5"
                style={{ color: '#6b7280' }}
              >
                AI Score
              </span>
              <span
                className="font-mono text-xs font-bold mt-0.5"
                style={{
                  color:
                    metrics.length === 0 ? '#6b7280'
                    : overallScore >= 80 ? '#10B981'
                    : overallScore >= 60 ? '#F59E0B'
                    : '#EF4444',
                }}
              >
                {overallGrade}
              </span>
            </>
          )}
        </div>
      </div>

      {/* Legend */}
      <div className="w-full grid grid-cols-2 gap-x-4 gap-y-1.5">
        {metrics.map((m) => (
          <div key={m.name} className="flex items-center gap-2">
            {/* Color swatch */}
            <div
              className="rounded-full shrink-0"
              style={{
                width: 8,
                height: 8,
                backgroundColor: m.color,
                boxShadow: `0 0 6px ${m.color}80`,
              }}
            />
            <div className="flex flex-col min-w-0">
              <span
                className="text-[9px] leading-tight truncate"
                style={{ color: '#9ca3af' }}
              >
                {m.name}
              </span>
              <span
                className="text-[11px] font-bold font-mono leading-tight"
                style={{ color: m.color }}
              >
                {m.value}%
              </span>
            </div>
          </div>
        ))}
      </div>

      {/* Mini progress bars beneath legend for extra clarity */}
      <div className="w-full space-y-1.5">
        {metrics.map((m) => (
          <div key={m.name} className="flex items-center gap-2">
            <span
              className="text-[8px] font-mono shrink-0"
              style={{ color: '#6b7280', width: 90 }}
            >
              {m.name.length > 14 ? m.name.slice(0, 14) + '…' : m.name}
            </span>
            <div
              className="flex-1 rounded-full overflow-hidden"
              style={{ height: 4, backgroundColor: '#1f2937' }}
            >
              <div
                className="h-full rounded-full"
                style={{
                  width: `${m.value}%`,
                  backgroundColor: m.color,
                  boxShadow: `0 0 6px ${m.color}60`,
                  transition: 'width 1.1s cubic-bezier(0.4, 0, 0.2, 1)',
                }}
              />
            </div>
            <span
              className="text-[9px] font-mono font-bold shrink-0"
              style={{ color: m.color, width: 28, textAlign: 'right' }}
            >
              {m.value}%
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}
