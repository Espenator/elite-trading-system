/**
 * KPICard — shared metric card for mega-strips at top of pages.
 * Props:
 *   label       string             — metric name
 *   value       string | number    — primary display value
 *   change      string (optional)  — e.g. "+2.3%" or "-0.8%"
 *   changeColor "green"|"red"|"amber"|"neutral" (optional)
 *   icon        Lucide component   (optional)
 *   className   string             (optional)
 */

const changeColorMap = {
  green:   'text-emerald-400',
  red:     'text-red-400',
  amber:   'text-amber-400',
  neutral: 'text-slate-400',
};

function changePrefix(change) {
  if (!change) return '';
  const trimmed = change.trim();
  if (trimmed.startsWith('+')) return '▲';
  if (trimmed.startsWith('-')) return '▼';
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
  const colorClass = changeColorMap[changeColor] ?? changeColorMap.neutral;
  const prefix = changePrefix(change);

  return (
    <div className={`bg-[#111827] border border-[#1e293b] rounded-md px-3 py-2 relative ${className}`}>
      {/* Optional icon — top-right corner */}
      {Icon && (
        <div className="absolute top-2 right-2 text-slate-600">
          <Icon size={14} />
        </div>
      )}

      {/* Primary value */}
      <div className="text-lg font-bold font-mono text-white leading-tight">{value}</div>

      {/* Label */}
      <div className="text-[10px] uppercase tracking-wider text-slate-500 mt-0.5">{label}</div>

      {/* Change indicator */}
      {change && (
        <div className={`text-[10px] font-mono mt-0.5 ${colorClass}`}>
          {prefix}{change}
        </div>
      )}
    </div>
  );
}
