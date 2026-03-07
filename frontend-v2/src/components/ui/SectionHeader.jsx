export default function SectionHeader({ title, action, className = '' }) {
  return (
    <div className={`flex items-center justify-between mb-2 ${className}`}>
      <h3 className="text-xs font-bold uppercase tracking-wider text-slate-400 font-mono">{title}</h3>
      {action && <div className="shrink-0">{action}</div>}
    </div>
  );
}
