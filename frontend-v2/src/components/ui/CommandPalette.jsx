/**
 * Command palette — Ctrl+K (or Cmd+K) to open.
 * Lists sidebar pages and navigates on selection.
 * Escape to close.
 */
import { useEffect, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  LayoutDashboard,
  Bot,
  MessageCircle,
  Link2,
  Radar,
  Brain,
  Search,
  RotateCcw,
  TrendingUp,
  BarChart3,
  LineChart,
  Shield,
  Crosshair,
  Settings,
} from 'lucide-react';

const PALETTE_ROUTES = [
  { to: '/dashboard', label: 'Intelligence Dashboard', icon: LayoutDashboard },
  { to: '/agents', label: 'Agent Command Center', icon: Bot },
  { to: '/sentiment', label: 'Sentiment Intelligence', icon: MessageCircle },
  { to: '/data-sources', label: 'Data Sources Manager', icon: Link2 },
  { to: '/signal-intelligence-v3', label: 'Signal Intelligence', icon: Radar },
  { to: '/ml-brain', label: 'ML Brain & Flywheel', icon: Brain },
  { to: '/patterns', label: 'Screener & Patterns', icon: Search },
  { to: '/backtest', label: 'Backtesting Lab', icon: RotateCcw },
  { to: '/performance', label: 'Performance Analytics', icon: TrendingUp },
  { to: '/market-regime', label: 'Market Regime', icon: BarChart3 },
  { to: '/trades', label: 'Active Trades', icon: LineChart },
  { to: '/risk', label: 'Risk Intelligence', icon: Shield },
  { to: '/trade-execution', label: 'Trade Execution', icon: Crosshair },
  { to: '/settings', label: 'Settings', icon: Settings },
];

export default function CommandPalette({ open, onClose }) {
  const [filter, setFilter] = useState('');
  const [selected, setSelected] = useState(0);
  const inputRef = useRef(null);
  const listRef = useRef(null);
  const navigate = useNavigate();

  const filtered = filter.trim()
    ? PALETTE_ROUTES.filter((r) =>
        r.label.toLowerCase().includes(filter.toLowerCase())
      )
    : PALETTE_ROUTES;

  useEffect(() => {
    if (!open) return;
    setFilter('');
    setSelected(0);
    setTimeout(() => inputRef.current?.focus(), 50);
  }, [open]);

  useEffect(() => {
    setSelected((s) => Math.min(s, Math.max(0, filtered.length - 1)));
  }, [filtered.length]);

  useEffect(() => {
    const el = listRef.current;
    if (!el) return;
    const item = el.children[selected];
    item?.scrollIntoView({ block: 'nearest', behavior: 'smooth' });
  }, [selected]);

  const handleKeyDown = (e) => {
    if (e.key === 'Escape') {
      onClose();
      return;
    }
    if (e.key === 'ArrowDown') {
      e.preventDefault();
      setSelected((s) => Math.min(s + 1, filtered.length - 1));
      return;
    }
    if (e.key === 'ArrowUp') {
      e.preventDefault();
      setSelected((s) => Math.max(s - 1, 0));
      return;
    }
    if (e.key === 'Enter' && filtered[selected]) {
      e.preventDefault();
      navigate(filtered[selected].to);
      onClose();
    }
  };

  if (!open) return null;

  return (
    <div
      className="fixed inset-0 z-[100] flex items-start justify-center pt-[15vh] bg-black/50 backdrop-blur-sm"
      onClick={onClose}
      role="dialog"
      aria-label="Command palette"
    >
      <div
        className="w-full max-w-lg rounded-lg overflow-hidden shadow-xl border border-[rgba(42,52,68,0.6)]"
        style={{ background: '#111827' }}
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center gap-2 px-3 py-2 border-b border-[rgba(42,52,68,0.5)]">
          <span className="text-[#6B7280] text-sm">⌘K</span>
          <input
            ref={inputRef}
            type="text"
            value={filter}
            onChange={(e) => setFilter(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Search pages…"
            className="flex-1 bg-transparent text-white text-sm outline-none placeholder-[#6B7280]"
          />
        </div>
        <ul
          ref={listRef}
          className="max-h-72 overflow-y-auto custom-scrollbar py-1"
        >
          {filtered.length === 0 ? (
            <li className="px-4 py-3 text-sm text-[#6B7280]">No matches</li>
          ) : (
            filtered.map((r, i) => {
              const Icon = r.icon;
              return (
                <li key={r.to}>
                  <button
                    type="button"
                    onClick={() => {
                      navigate(r.to);
                      onClose();
                    }}
                    className={`w-full flex items-center gap-3 px-4 py-2.5 text-left text-sm transition-colors ${
                      i === selected
                        ? 'bg-[rgba(0,217,255,0.12)] text-[#00D9FF]'
                        : 'text-[#E5E7EB] hover:bg-white/5'
                    }`}
                  >
                    <Icon className="w-4 h-4 shrink-0" style={{ color: i === selected ? '#00D9FF' : '#9CA3AF' }} />
                    {r.label}
                  </button>
                </li>
              );
            })
          )}
        </ul>
        <div className="px-4 py-2 border-t border-[rgba(42,52,68,0.5)] text-[10px] text-[#6B7280] font-mono">
          ↑↓ navigate · Enter select · Esc close
        </div>
      </div>
    </div>
  );
}
