/**
 * Command palette — Ctrl+K / Cmd+K to open.
 * Search + quick nav to sidebar pages.
 */
import { useState, useEffect, useCallback } from "react";
import { useNavigate } from "react-router-dom";
import { Search } from "lucide-react";

const SIDEBAR_ROUTES = [
  { path: "/dashboard", label: "Intelligence Dashboard" },
  { path: "/agents", label: "Agent Command Center" },
  { path: "/sentiment", label: "Sentiment Intelligence" },
  { path: "/data-sources", label: "Data Sources Manager" },
  { path: "/signal-intelligence-v3", label: "Signal Intelligence" },
  { path: "/ml-brain", label: "ML Brain & Flywheel" },
  { path: "/patterns", label: "Screener & Patterns" },
  { path: "/backtest", label: "Backtesting Lab" },
  { path: "/performance", label: "Performance Analytics" },
  { path: "/market-regime", label: "Market Regime" },
  { path: "/trades", label: "Active Trades" },
  { path: "/risk", label: "Risk Intelligence" },
  { path: "/trade-execution", label: "Trade Execution" },
  { path: "/settings", label: "Settings" },
];

export default function CommandPalette({ open, onClose }) {
  const [query, setQuery] = useState("");
  const [selected, setSelected] = useState(0);
  const navigate = useNavigate();

  const filtered = query.trim()
    ? SIDEBAR_ROUTES.filter(
        (r) =>
          r.label.toLowerCase().includes(query.toLowerCase()) ||
          r.path.toLowerCase().includes(query.toLowerCase())
      )
    : SIDEBAR_ROUTES;

  const select = useCallback(
    (item) => {
      navigate(item.path);
      onClose();
      setQuery("");
      setSelected(0);
    },
    [navigate, onClose]
  );

  useEffect(() => {
    setSelected(0);
  }, [query]);

  useEffect(() => {
    const onKeyDown = (e) => {
      if (!open) return;
      if (e.key === "Escape") {
        onClose();
        return;
      }
      if (e.key === "ArrowDown") {
        e.preventDefault();
        setSelected((i) => Math.min(i + 1, filtered.length - 1));
        return;
      }
      if (e.key === "ArrowUp") {
        e.preventDefault();
        setSelected((i) => Math.max(i - 1, 0));
        return;
      }
      if (e.key === "Enter" && filtered[selected]) {
        e.preventDefault();
        select(filtered[selected]);
      }
    };
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [open, filtered, selected, select, onClose]);

  if (!open) return null;

  return (
    <div
      className="fixed inset-0 z-[100] flex items-start justify-center pt-[15vh] bg-black/60 backdrop-blur-sm"
      onClick={onClose}
      role="dialog"
      aria-modal="true"
      aria-label="Command palette"
    >
      <div
        className="w-full max-w-lg rounded-lg border border-[rgba(42,52,68,0.6)] bg-[#111827] shadow-xl"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center gap-2 px-3 py-2 border-b border-[rgba(42,52,68,0.5)]">
          <Search className="w-4 h-4 text-[#6B7280]" />
          <input
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Search pages…"
            className="flex-1 bg-transparent text-sm text-white placeholder-[#6B7280] outline-none"
            autoFocus
          />
          <kbd className="text-[10px] text-[#6B7280]">Esc</kbd>
        </div>
        <ul className="max-h-72 overflow-y-auto py-1">
          {filtered.length === 0 ? (
            <li className="px-3 py-4 text-sm text-[#6B7280]">No matches</li>
          ) : (
            filtered.map((item, i) => (
              <li key={item.path}>
                <button
                  type="button"
                  onClick={() => select(item)}
                  className={`w-full flex items-center gap-3 px-3 py-2.5 text-left text-sm transition-colors ${
                    i === selected
                      ? "bg-[rgba(0,217,255,0.12)] text-[#00D9FF]"
                      : "text-gray-300 hover:bg-white/5"
                  }`}
                >
                  <span className="font-medium">{item.label}</span>
                  <span className="ml-auto font-mono text-[10px] text-[#6B7280]">
                    {item.path}
                  </span>
                </button>
              </li>
            ))
          )}
        </ul>
      </div>
    </div>
  );
}

export { SIDEBAR_ROUTES };
