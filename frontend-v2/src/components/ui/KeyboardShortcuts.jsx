/**
 * Keyboard Shortcuts Help Overlay — press "?" to toggle.
 * Shows all available shortcuts across the app.
 */
import { useEffect, useState } from "react";

const SHORTCUT_GROUPS = [
  {
    title: "Navigation",
    shortcuts: [
      { keys: ["Ctrl", "K"], description: "Open command palette" },
      { keys: ["?"], description: "Show keyboard shortcuts" },
      { keys: ["Esc"], description: "Close overlay / dialog" },
    ],
  },
  {
    title: "Dashboard",
    shortcuts: [
      { keys: ["F5"], description: "Run scan" },
      { keys: ["F7"], description: "Export CSV" },
      { keys: ["N"], description: "Spawn agent (go to Agent Command Center)" },
    ],
  },
  {
    title: "System",
    shortcuts: [
      { keys: ["Alt", "T"], description: "Toggle notifications panel" },
    ],
  },
];

function Kbd({ children }) {
  return (
    <kbd className="inline-flex items-center justify-center min-w-[24px] px-1.5 py-0.5 rounded bg-[#1e293b] border border-[#374151] text-[11px] font-mono text-gray-300 shadow-sm">
      {children}
    </kbd>
  );
}

export default function KeyboardShortcuts() {
  const [open, setOpen] = useState(false);

  useEffect(() => {
    const handler = (e) => {
      if (
        e.key === "?" &&
        !e.ctrlKey &&
        !e.metaKey &&
        document.activeElement?.tagName !== "INPUT" &&
        document.activeElement?.tagName !== "TEXTAREA"
      ) {
        e.preventDefault();
        setOpen((v) => !v);
      }
      if (e.key === "Escape" && open) {
        setOpen(false);
      }
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [open]);

  if (!open) return null;

  return (
    <div
      className="fixed inset-0 z-[110] flex items-center justify-center bg-black/60 backdrop-blur-sm"
      onClick={() => setOpen(false)}
      role="dialog"
      aria-label="Keyboard shortcuts"
    >
      <div
        className="w-full max-w-md rounded-lg overflow-hidden shadow-2xl border border-[rgba(42,52,68,0.6)] bg-[#111827]"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between px-4 py-3 border-b border-[rgba(42,52,68,0.5)]">
          <h2 className="text-sm font-bold text-white">Keyboard Shortcuts</h2>
          <button
            type="button"
            onClick={() => setOpen(false)}
            className="text-gray-400 hover:text-white text-lg leading-none"
            aria-label="Close"
          >
            &times;
          </button>
        </div>
        <div className="p-4 space-y-4 max-h-[60vh] overflow-y-auto">
          {SHORTCUT_GROUPS.map((group) => (
            <div key={group.title}>
              <h3 className="text-[10px] font-bold uppercase tracking-wider text-[#00D9FF]/60 mb-2">
                {group.title}
              </h3>
              <div className="space-y-1.5">
                {group.shortcuts.map((s) => (
                  <div
                    key={s.description}
                    className="flex items-center justify-between py-1"
                  >
                    <span className="text-xs text-gray-400">
                      {s.description}
                    </span>
                    <span className="flex items-center gap-1">
                      {s.keys.map((k, i) => (
                        <span key={k} className="flex items-center gap-1">
                          {i > 0 && (
                            <span className="text-[10px] text-gray-600">+</span>
                          )}
                          <Kbd>{k}</Kbd>
                        </span>
                      ))}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          ))}
        </div>
        <div className="px-4 py-2 border-t border-[rgba(42,52,68,0.5)] text-[10px] text-[#6B7280] font-mono text-center">
          Press <Kbd>?</Kbd> to toggle this overlay
        </div>
      </div>
    </div>
  );
}
