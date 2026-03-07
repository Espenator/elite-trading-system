/**
 * KPICard — metric card for mega-strips at the top of every page.
 *
 * Visual spec (matches mockups):
 *   - Aurora card surface (gradient, border, glow on hover)
 *   - Value: JetBrains Mono, 18px bold, white — the dominant element
 *   - Label: 10px uppercase tracking, #6B7280
 *   - Change: 10px mono, coloured per direction (▲ green / ▼ red / amber)
 *   - Icon: top-right, 14px, coloured per changeColor (not grey)
 *   - Hover: cyan glow (via aurora-card class)
 *
 * Props:
 *   label        string             — metric name (e.g. "WIN RATE")
 *   value        string | number    — primary display value (e.g. "62.4%")
 *   change       string (optional)  — e.g. "+2.3%" or "-0.8%"
 *   changeColor  "green"|"red"|"amber"|"neutral" (optional, default "neutral")
 *   icon         Lucide component   (optional) — accent icon top-right
 *   className    string             (optional)
 */

const changeColorMap = {
  green:   { text: 'text-emerald-400', icon: 'text-emerald-400' },
  red:     { text: 'text-red-400',     icon: 'text-red-400'     },
  amber:   { text: 'text-amber-400',   icon: 'text-amber-400'   },
  neutral: { text: 'text-slate-400',   icon: 'text-slate-500'   },
};

function arrow(change) {
  if (!change) return '';
  const t = change.trim();
  if (t.startsWith('+')) return '▲ ';
  if (t.startsWith('-')) return '▼ ';
  return '';
}

export default function KPICard({
  label,
  value,
  change,
  changeColor = 'neutral',
  icon: Icon,
  className = '',
}) {
  const colors = changeColorMap[changeColor] ?? changeColorMap.neutral;

  return (
    <div
      className={`relative overflow-hidden rounded-[8px] px-3 py-2.5 border transition-all duration-300 ${className}`}
      style={{
        background:           'linear-gradient(145deg, #111827, #1F2937)',
        borderColor:          'rgba(42,52,68,0.5)',
        backdropFilter:       'blur(16px)',
        WebkitBackdropFilter: 'blur(16px)',
        boxShadow:            '0 8px 32px rgba(0,0,0,0.3)',
      }}
      onMouseEnter={(e) => {
        e.currentTarget.style.boxShadow   = '0 0 20px rgba(0,217,255,0.3)';
        e.currentTarget.style.borderColor = 'rgba(0,217,255,0.2)';
      }}
      onMouseLeave={(e) => {
        e.currentTarget.style.boxShadow   = '0 8px 32px rgba(0,0,0,0.3)';
        e.currentTarget.style.borderColor = 'rgba(42,52,68,0.5)';
      }}
    >
      {/* Icon — top-right, coloured to match change direction */}
      {Icon && (
        <div className={`absolute top-2 right-2 ${colors.icon}`}>
          <Icon size={14} strokeWidth={2} />
        </div>
      )}

      {/* Primary value — dominant element */}
      <div
        className="font-mono font-bold text-white leading-tight"
        style={{
          fontSize:           '1.125rem',
          fontVariantNumeric: 'tabular-nums',
        }}
      >
        {value}
      </div>

      {/* Label */}
      <div
        className="uppercase tracking-wider text-[#6B7280] font-medium"
        style={{ fontSize: '0.625rem', marginTop: '0.125rem' }}
      >
        {label}
      </div>

      {/* Change indicator */}
      {change && (
        <div
          className={`font-mono ${colors.text}`}
          style={{ fontSize: '0.625rem', marginTop: '0.125rem' }}
        >
          {arrow(change)}{change}
        </div>
      )}
    </div>
  );
}
