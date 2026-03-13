import React, { useState, useEffect, useRef, useCallback } from "react";
import { useSettings } from "../hooks/useSettings";
import { useApi } from "../hooks/useApi";
import { toast } from "react-toastify";
import {
  User, Key, Activity, Bell, Cpu, Database,
  ShieldAlert, Save, RefreshCw, CheckCircle2,
  AlertTriangle, Settings, Sliders, Wifi,
  Loader2, RotateCcw, Download, Upload,
  Bot, TrendingUp, BarChart2, Globe, Zap,
  Shield, Brain, Palette, FileText, Eye,
  EyeOff, Monitor, Lock, Clock, ChevronDown, Star,
  Copy,
} from "lucide-react";

// -- Toast config --
const TOAST_CFG = { position: "bottom-right", theme: "dark" };

// -- Section nav: id, label, category (or categories) for save/reset --
const SECTION_NAV = [
  { group: "PLATFORM", items: [
    { id: "identity", label: "Identity & Locale", categories: ["user", "appearance"] },
    { id: "trading-mode", label: "Trading Mode", categories: ["dataSources", "trading"] },
    { id: "appearance", label: "Display & Appearance", categories: ["appearance", "system"] },
  ]},
  { group: "INTELLIGENCE", items: [
    { id: "data-sources", label: "Data Source Priority", categories: ["dataSources"] },
    { id: "ollama", label: "Ollama Local LLM", categories: ["ollama"] },
    { id: "ai-inference", label: "AI Inference Models", categories: ["ollama"] },
    { id: "ml-models", label: "ML Models & Flywheel", categories: ["ml"] },
    { id: "agents", label: "OpenClaw & Agents", categories: ["agents"] },
  ]},
  { group: "EXECUTION", items: [
    { id: "position-risk", label: "Position & Risk", categories: ["trading", "risk", "kelly"] },
    { id: "trade-mgmt", label: "Trade Management", categories: ["risk", "trading"] },
    { id: "order-exec", label: "Order Execution", categories: ["trading"] },
  ]},
  { group: "SYSTEM", items: [
    { id: "brokerage", label: "Brokerage & API Keys", categories: ["dataSources"] },
    { id: "notifications", label: "Notifications", categories: ["notifications"] },
    { id: "security", label: "Security & Auth", categories: ["system"] },
    { id: "backup", label: "Backup & Import/Export", categories: ["system"] },
    { id: "audit", label: "Audit Log", categories: [] },
    { id: "strategy", label: "Strategy", categories: ["strategy"] },
  ]},
];
const REVEAL_DURATION_MS = 10000;
const KELLY_MIN = 0.05;
const KELLY_MAX = 0.50;
const KELLY_TICKS = [0.10, 0.25, 0.40];
const RISK_PRESETS = {
  conservative: { kellyMaxAllocation: 0.10, maxPortfolioHeat: 0.15, maxPortfolioRisk: 0.04 },
  moderate: { kellyMaxAllocation: 0.25, maxPortfolioHeat: 0.25, maxPortfolioRisk: 0.06 },
  aggressive: { kellyMaxAllocation: 0.40, maxPortfolioHeat: 0.35, maxPortfolioRisk: 0.10 },
};

// -- Tiny reusable components --

function StatusDot({ ok, testing }) {
  if (testing) return <Loader2 className="w-3 h-3 animate-spin text-[#00D9FF]" />;
  if (ok === true) return <CheckCircle2 className="w-3 h-3 text-[#10b981]" />;
  if (ok === false) return <AlertTriangle className="w-3 h-3 text-red-400" />;
  return <div className="w-2 h-2 rounded-full bg-gray-600" />;
}

function SectionCard({ title, children, className = "", star = false, categories = [], onSave, onReset, saving }) {
  return (
    <div className={`bg-[#111827] border border-[rgba(42,52,68,0.5)] rounded-lg p-2 shadow-sm ${className}`}>
      <div className="flex items-center gap-1.5 mb-1.5 pb-1 border-b border-gray-800/50">
        {star && <Star className="w-3 h-3 text-amber-400 fill-amber-400 flex-shrink-0" />}
        <span className="text-xs font-bold uppercase tracking-wider text-slate-400 font-mono">{title}</span>
      </div>
      <div className="space-y-0.5">{children}</div>
      {categories.length > 0 && onSave && onReset && (
        <div className="flex items-center gap-2 mt-2 pt-2 border-t border-gray-800/50">
          <button
            onClick={async () => {
              try {
                for (const c of categories) await onSave(c);
                toast.success(`${title} saved`, TOAST_CFG);
              } catch {
                toast.error(`Failed to save ${title}`, TOAST_CFG);
              }
            }}
            disabled={saving}
            className="text-[10px] font-bold px-2 py-1 rounded bg-[#00D9FF]/20 text-[#00D9FF] hover:bg-[#00D9FF]/30 disabled:opacity-50 flex items-center gap-1"
          >
            <Save className="w-3 h-3" /> Save
          </button>
          <button
            onClick={async () => {
              const msg = `Reset ${title} to defaults? This will revert: ${categories.join(", ")}.`;
              if (!window.confirm(msg)) return;
              try {
                for (const c of categories) await onReset(c);
                toast.success(`${title} reset to defaults`, TOAST_CFG);
              } catch {
                toast.error(`Failed to reset ${title}`, TOAST_CFG);
              }
            }}
            className="text-[10px] text-gray-400 hover:text-white px-2 py-1 rounded border border-gray-600/50 hover:border-gray-500"
          >
            <RotateCcw className="w-3 h-3" /> Reset to Defaults
          </button>
        </div>
      )}
    </div>
  );
}

function MiniField({ label, value, onChange, type = "text", suffix, className = "", ...props }) {
  return (
    <div className="flex items-center justify-between gap-2 py-[1px]">
      <span className="text-[10px] text-gray-400 whitespace-nowrap">{label}</span>
      <div className="flex items-center gap-1">
        <input
          type={type}
          value={value}
          onChange={onChange}
          className={`w-20 bg-[#0B0E14] border border-gray-700/50 rounded px-1.5 py-0.5 text-[10px] text-white outline-none focus:border-[#00D9FF]/50 ${className}`}
          {...props}
        />
        {suffix && <span className="text-[9px] text-gray-600">{suffix}</span>}
      </div>
    </div>
  );
}

function MiniSelect({ label, value, options, onChange }) {
  return (
    <div className="flex items-center justify-between gap-2 py-[1px]">
      <span className="text-[10px] text-gray-400 whitespace-nowrap">{label}</span>
      <select
        value={value}
        onChange={onChange}
        className="bg-[#0B0E14] border border-gray-700/50 rounded px-1 py-0.5 text-[10px] text-white outline-none focus:border-[#00D9FF]/50 appearance-none cursor-pointer pr-4"
      >
        {options.map((o) => (
          <option key={typeof o === "string" ? o : o.value} value={typeof o === "string" ? o : o.value}>
            {typeof o === "string" ? o : o.label}
          </option>
        ))}
      </select>
    </div>
  );
}

function MiniToggle({ label, checked, onChange }) {
  return (
    <div className="flex items-center justify-between py-[1px]">
      <span className="text-[10px] text-gray-400">{label}</span>
      <button
        onClick={() => onChange(!checked)}
        className={`w-7 h-3.5 rounded-full border transition-colors flex items-center ${
          checked ? "bg-cyan-500/30 border-[#00D9FF]/50" : "bg-gray-700/30 border-gray-600/50"
        }`}
      >
        <span
          className={`block w-2.5 h-2.5 rounded-full transition-transform ${
            checked ? "translate-x-3.5 bg-[#00D9FF]" : "translate-x-0.5 bg-gray-500"
          }`}
        />
      </button>
    </div>
  );
}

function MiniCheckbox({ label, checked, onChange }) {
  return (
    <div className="flex items-center gap-1.5 py-[1px]">
      <button
        onClick={() => onChange(!checked)}
        className={`w-3 h-3 rounded-sm border flex items-center justify-center text-[8px] ${
          checked
            ? "bg-cyan-500/30 border-[#00D9FF]/50 text-[#00D9FF]"
            : "bg-transparent border-gray-600/50"
        }`}
      >
        {checked && "\u2713"}
      </button>
      <span className="text-[10px] text-gray-400">{label}</span>
    </div>
  );
}

function ConnBadge({ status, label }) {
  const isConnected = status === "connected";
  const isAggregated = status === "aggregated";
  return (
    <span
      className={`text-[8px] font-bold px-1.5 py-0.5 rounded uppercase tracking-wider ${
        isConnected
          ? "bg-[#10b981]/20 text-[#10b981] border border-[#10b981]/30"
          : isAggregated
          ? "bg-cyan-500/15 text-[#00D9FF] border border-[#00D9FF]/50/30"
          : "bg-gray-700/30 text-gray-500 border border-gray-600/30"
      }`}
    >
      {label || status}
    </span>
  );
}

function PrioritySlider({ label, value, onChange, max = 10 }) {
  return (
    <div className="flex items-center justify-between gap-2 py-[1px]">
      <span className="text-[10px] text-gray-400 whitespace-nowrap flex-shrink-0">{label}</span>
      <div className="flex items-center gap-1.5 flex-1 justify-end">
        <input
          type="range"
          min={0}
          max={max}
          value={value}
          onChange={onChange}
          className="w-14 h-1 accent-cyan-500 cursor-pointer"
        />
        <span className="text-[9px] text-[#00D9FF] w-4 text-right">{value}</span>
      </div>
    </div>
  );
}

function SkeletonLine({ className = "" }) {
  return (
    <div className={`h-4 bg-gray-700/50 rounded animate-pulse ${className}`} />
  );
}

function ApiKeyRow({ source, label, value, maskedValue, connectionResult, onReveal, onCopy, onTest, revealed, revealExpiry }) {
  const isRevealed = revealed && (typeof revealExpiry !== "number" || Date.now() < revealExpiry);
  const displayValue = (value != null && value !== "" && isRevealed) ? value : (maskedValue || "••••••••");
  const canCopy = isRevealed && value;
  const cr = connectionResult || {};
  return (
    <div className="flex items-center justify-between py-0.5 gap-2 flex-wrap">
      <span className="text-[10px] text-gray-400">{label}</span>
      <div className="flex items-center gap-1 flex-wrap">
        <StatusDot ok={cr.valid} testing={cr.testing} />
        <span className="text-[9px] text-gray-500 font-mono max-w-[80px] truncate">{displayValue}</span>
        <button type="button" onClick={onReveal} className="text-[9px] text-[#00D9FF] hover:text-cyan-300 flex items-center gap-0.5" title={isRevealed ? "Hide" : "Reveal 10s"}>
          {isRevealed ? <EyeOff className="w-3 h-3" /> : <Eye className="w-3 h-3" />}
        </button>
        <button type="button" onClick={() => canCopy && navigator.clipboard.writeText(value).then(() => toast.success("Copied", TOAST_CFG))} disabled={!canCopy} className="text-[9px] text-[#00D9FF] hover:text-cyan-300 disabled:opacity-40 disabled:cursor-not-allowed flex items-center gap-0.5" title="Copy (when revealed)">
          <Copy className="w-3 h-3" />
        </button>
        <button type="button" onClick={() => onTest(source)} className="text-[9px] text-[#00D9FF] hover:text-cyan-300">[Test]</button>
      </div>
    </div>
  );
}

function KellySliderWithPresets({ value, onChange, onPreset, kellyCategoryKey, riskCategoryKeys }) {
  const num = typeof value === "number" ? value : parseFloat(value) || KELLY_MIN;
  return (
    <div className="space-y-1">
      <div className="flex items-center justify-between gap-2">
        <span className="text-[10px] text-gray-400">Kelly Fraction: {KELLY_MIN} – {KELLY_MAX} (current: {num.toFixed(2)})</span>
      </div>
      <div className="relative flex items-center gap-1">
        <input
          type="range"
          min={KELLY_MIN}
          max={KELLY_MAX}
          step={0.01}
          value={num}
          onChange={(e) => onChange(parseFloat(e.target.value))}
          className="flex-1 h-2 accent-[#00D9FF] cursor-pointer"
        />
        <span className="text-[9px] text-[#00D9FF] w-8 text-right">{num.toFixed(2)}</span>
      </div>
      <div className="flex justify-between text-[9px] text-gray-500 px-0.5">
        <span>0.10</span>
        <span>0.25</span>
        <span>0.40</span>
      </div>
      <div className="flex gap-2 pt-0.5">
        {(["conservative", "moderate", "aggressive"]).map((preset) => (
          <button
            key={preset}
            type="button"
            onClick={() => onPreset(preset)}
            className="text-[9px] px-2 py-0.5 rounded border border-gray-600/50 text-gray-400 hover:border-[#00D9FF]/50 hover:text-[#00D9FF] capitalize"
          >
            {preset}
          </button>
        ))}
      </div>
    </div>
  );
}

function NotificationToggleWithDot({ label, checked, onChange, status }) {
  return (
    <div className="flex items-center justify-between py-[1px] gap-2">
      <span className="text-[10px] text-gray-400">{label}</span>
      <div className="flex items-center gap-1.5">
        <StatusDot ok={status === "ok"} testing={status === "testing"} />
        <button
          onClick={() => onChange(!checked)}
          className={`w-7 h-3.5 rounded-full border transition-colors flex items-center ${checked ? "bg-cyan-500/30 border-[#00D9FF]/50" : "bg-gray-700/30 border-gray-600/50"}`}
        >
          <span className={`block w-2.5 h-2.5 rounded-full transition-transform ${checked ? "translate-x-3.5 bg-[#00D9FF]" : "translate-x-0.5 bg-gray-500"}`} />
        </button>
      </div>
    </div>
  );
}

// -- Main Settings Page --
export default function SettingsPage() {
  const {
    settings, loading, saving, dirty, error,
    connectionResults, updateField,
    saveCategory, saveAllSettings, resetCategory,
    validateKey, testConnection,
    exportSettings, importSettings, refetch,
  } = useSettings();

  const importRef = useRef(null);
  const S = settings || {};
  const [showFullLog, setShowFullLog] = useState(false);
  const [activeSection, setActiveSection] = useState("identity");
  const [revealedKeys, setRevealedKeys] = useState({});
  const revealTimersRef = useRef({});

  const get = (cat, key) => S[cat]?.[key];
  const getStr = (cat, key) => get(cat, key) ?? "";
  const getNum = (cat, key) => {
    const v = get(cat, key);
    return typeof v === "number" ? v : (parseFloat(v) != null && !Number.isNaN(parseFloat(v)) ? parseFloat(v) : 0);
  };
  const getBool = (cat, key) => !!get(cat, key);

  const revealKey = useCallback((id) => {
    if (revealTimersRef.current[id]) clearTimeout(revealTimersRef.current[id]);
    setRevealedKeys((prev) => ({ ...prev, [id]: Date.now() + REVEAL_DURATION_MS }));
    revealTimersRef.current[id] = setTimeout(() => {
      setRevealedKeys((prev) => ({ ...prev, [id]: 0 }));
      delete revealTimersRef.current[id];
    }, REVEAL_DURATION_MS);
  }, []);
  const isKeyRevealed = useCallback((id) => {
    const exp = revealedKeys[id];
    return exp && typeof exp === "number" && Date.now() < exp;
  }, [revealedKeys]);

  const onSave = async (cat) => {
    try {
      await saveCategory(cat);
      toast.success(`${cat} settings saved`, TOAST_CFG);
    } catch {
      toast.error(`Failed to save ${cat} settings`, TOAST_CFG);
    }
  };

  const onReset = async (cat) => {
    if (!window.confirm(`Reset all ${cat} settings to defaults?`)) return;
    try {
      await resetCategory(cat);
      toast.success(`${cat} reset to defaults`, TOAST_CFG);
    } catch {
      toast.error(`Failed to reset ${cat}`, TOAST_CFG);
    }
  };

  const onTestConn = async (source) => {
    const r = await testConnection(source);
    if (r.valid) toast.success(`${source}: ${r.message}`, TOAST_CFG);
    else toast.error(`${source}: ${r.message}`, TOAST_CFG);
  };

  const onExport = async () => {
    try {
      const data = await exportSettings();
      const blob = new Blob([JSON.stringify(data, null, 2)], { type: "application/json" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = "elite-settings-export.json";
      a.click();
      URL.revokeObjectURL(url);
      toast.success("Settings exported", TOAST_CFG);
    } catch {
      toast.error("Export failed", TOAST_CFG);
    }
  };

  const onImport = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    try {
      const text = await file.text();
      const data = JSON.parse(text);
      await importSettings(data);
      toast.success("Settings imported successfully", TOAST_CFG);
    } catch {
      toast.error("Import failed - invalid JSON", TOAST_CFG);
    }
  };

  // Warn on unsaved changes
  useEffect(() => {
    if (!dirty) return;
    const handler = (e) => { e.preventDefault(); e.returnValue = ""; };
    window.addEventListener("beforeunload", handler);
    return () => window.removeEventListener("beforeunload", handler);
  }, [dirty]);

  if (loading && !settings) {
    return (
      <div className="min-h-screen bg-[#0a0e1a] flex">
        <div className="w-[40%] max-w-[280px] p-3 border-r border-gray-800/50 space-y-4">
          {SECTION_NAV.map((g) => (
            <div key={g.group}>
              <div className="text-[10px] font-bold uppercase text-gray-500 mb-1">{g.group}</div>
              <div className="space-y-0.5">
                {g.items.map(() => (
                  <SkeletonLine key={Math.random()} className="h-6 w-full" />
                ))}
              </div>
            </div>
          ))}
        </div>
        <div className="flex-1 p-4 space-y-3">
          <SkeletonLine className="w-48 h-6" />
          {[1, 2, 3, 4, 5].map((i) => (
            <SkeletonLine key={i} className="w-full h-8" />
          ))}
        </div>
      </div>
    );
  }

  if (error && !settings) {
    return (
      <div className="min-h-screen bg-[#0B0E14] flex flex-col items-center justify-center gap-3">
        <AlertTriangle className="w-6 h-6 text-red-400" />
        <span className="text-gray-400 text-sm">Failed to load settings: {error.message}</span>
        <button onClick={refetch} className="text-xs text-[#00D9FF] hover:text-cyan-300 flex items-center gap-1">
          <RefreshCw className="w-3 h-3" /> Retry
        </button>
      </div>
    );
  }

  const alpacaCr = connectionResults["alpaca"] || {};
  const uwCr = connectionResults["unusual_whales"] || {};
  const ollamaCr = connectionResults["ollama"] || {};

  return (
    <div className="min-h-screen bg-[#0a0e1a] text-[#e2e8f0]">
      <input ref={importRef} type="file" accept=".json" className="hidden" onChange={onImport} />

      {/* HEADER */}
      <div className="flex items-center justify-between p-3 pb-2 border-b border-[rgba(30,41,59,0.5)] bg-[#111827]">
        <div className="flex items-center gap-3">
          <Settings className="w-5 h-5 text-[#00D9FF]" />
          <h1 className="text-base font-bold text-white uppercase tracking-widest font-mono">SYSTEM CONFIGURATION</h1>
          {dirty && (
            <span className="px-2 py-0.5 text-[9px] font-bold bg-amber-500/20 text-amber-400 border border-amber-500/30 rounded uppercase animate-pulse">
              UNSAVED CHANGES
            </span>
          )}
        </div>
        <button
          onClick={async () => { try { await saveAllSettings(); toast.success("All settings saved", TOAST_CFG); } catch { toast.error("Save failed", TOAST_CFG); } }}
          disabled={saving}
          className="bg-[#00D9FF] hover:bg-[#00D9FF]/80 text-black font-bold text-[11px] px-5 py-1.5 rounded uppercase tracking-wider disabled:opacity-50 flex items-center gap-1.5"
        >
          <Save className="w-3.5 h-3.5" />
          {saving ? "Saving..." : "SAVE ALL"}
        </button>
      </div>

      <div className="flex min-h-[calc(100vh-56px)]">
        {/* LEFT: Sticky section nav (40%) */}
        <aside className="w-[40%] max-w-[280px] flex-shrink-0 border-r border-[rgba(30,41,59,0.5)] bg-[#111827] sticky top-0 self-start max-h-[calc(100vh-56px)] overflow-y-auto">
          <nav className="p-3 space-y-4">
            {SECTION_NAV.map((g) => (
              <div key={g.group}>
                <div className="text-[10px] font-bold uppercase text-[#94a3b8] mb-1.5">{g.group}</div>
                <div className="space-y-0.5">
                  {g.items.map((item) => (
                    <button
                      key={item.id}
                      type="button"
                      onClick={() => setActiveSection(item.id)}
                      className={`w-full text-left px-2 py-1.5 rounded text-xs font-mono transition-colors ${
                        activeSection === item.id ? "bg-[#00D9FF]/20 text-[#00D9FF]" : "text-gray-400 hover:bg-gray-800/50 hover:text-white"
                      }`}
                    >
                      {item.label}
                    </button>
                  ))}
                </div>
              </div>
            ))}
          </nav>
        </aside>

        {/* RIGHT: Detail panel (60%) */}
        <main className="flex-1 p-4 overflow-y-auto bg-[#0a0e1a]">
          {activeSection === "identity" && (
            <SectionCard title="Identity & Locale" categories={["user", "appearance"]} onSave={saveCategory} onReset={resetCategory} saving={saving}>
              <MiniField label="Display Name" value={getStr("user", "displayName")} onChange={(e) => updateField("user", "displayName", e.target.value)} />
              <MiniField label="Email" value={getStr("user", "email")} onChange={(e) => updateField("user", "email", e.target.value)} />
              <MiniSelect label="Timezone" value={getStr("user", "timezone") || "America/New_York"} options={[
            { value: "America/New_York", label: "EST" },
            { value: "America/Chicago", label: "CT" },
            { value: "America/Los_Angeles", label: "PT" },
            { value: "UTC", label: "UTC" },
            { value: "Europe/Oslo", label: "CET" },
          ]} onChange={(e) => updateField("user", "timezone", e.target.value)} />
          <MiniSelect label="Currency" value={getStr("user", "currency") || "USD"} options={[
            { value: "USD", label: "USD" },
            { value: "EUR", label: "EUR" },
            { value: "GBP", label: "GBP" },
          ]} onChange={(e) => updateField("user", "currency", e.target.value)} />
          <MiniSelect label="Timeframe" value={getStr("appearance", "chartTimeframe") || "1D"} options={[
            { value: "1m", label: "1M" },
            { value: "5m", label: "5M" },
            { value: "15m", label: "15M" },
            { value: "1D", label: "1D" },
            { value: "1W", label: "1W" },
          ]} onChange={(e) => updateField("appearance", "chartTimeframe", e.target.value)} />
          <div className="flex items-center justify-between py-[1px] pt-1">
            <span className="text-[10px] text-gray-400">Avatar</span>
            <button type="button" className="text-[9px] text-[#00D9FF] hover:text-cyan-300 px-2 py-1 border border-gray-700/50 rounded">Choose File</button>
          </div>
            </SectionCard>
          )}

          {activeSection === "trading-mode" && (
            <SectionCard title="Trading Mode" categories={["dataSources", "trading"]} onSave={saveCategory} onReset={resetCategory} saving={saving}>
              <div className="flex items-center gap-4 mb-1">
                <span className={`text-sm font-bold ${(get("dataSources", "alpacaBaseUrl") || "paper") === "paper" ? "text-emerald-500" : "text-gray-500"}`}>PAPER</span>
                <button type="button"
                  onClick={() => updateField("dataSources", "alpacaBaseUrl", (get("dataSources", "alpacaBaseUrl") || "paper") === "paper" ? "live" : "paper")}
                  className={`relative w-14 h-7 rounded-full transition-colors ${(get("dataSources", "alpacaBaseUrl") || "paper") === "live" ? "bg-red-500" : "bg-emerald-500"}`}
                >
                  <div className={`absolute top-0.5 w-6 h-6 bg-white rounded-full transition-transform ${(get("dataSources", "alpacaBaseUrl") || "paper") === "live" ? "translate-x-7" : "translate-x-0.5"}`} />
                </button>
                <span className={`text-sm font-bold ${(get("dataSources", "alpacaBaseUrl") || "paper") === "live" ? "text-red-400" : "text-gray-500"}`}>LIVE</span>
              </div>
              {(get("dataSources", "alpacaBaseUrl") || "paper") === "live" && (
                <p className="text-[10px] text-emerald-400 mt-1">▲ Live mode = real money</p>
              )}
              <MiniSelect label="Broker" value={getStr("trading", "broker") || "alpaca"} options={[
                { value: "alpaca", label: "Alpaca Markets" },
                { value: "ibkr", label: "Interactive Brokers" },
              ]} onChange={(e) => updateField("trading", "broker", e.target.value)} />
              <div className="flex items-center justify-between py-[1px]">
                <span className="text-[10px] text-gray-400">Status</span>
                <StatusDot ok={alpacaCr.valid} testing={alpacaCr.testing} />
                <span className="text-[9px] text-emerald-400 flex items-center gap-1"><span className="w-1.5 h-1.5 rounded-full bg-emerald-500" /> Connected</span>
              </div>
              <MiniField label="Account" value={getStr("trading", "accountType")} onChange={(e) => updateField("trading", "accountType", e.target.value)} />
              <MiniField label="Sync" value={getStr("trading", "lastSync")} onChange={(e) => updateField("trading", "lastSync", e.target.value)} />
            </SectionCard>
          )}

          {activeSection === "position-risk" && (
            <>
              <SectionCard title="Position Sizing" categories={["trading", "risk"]} onSave={saveCategory} onReset={resetCategory} saving={saving}>
                <MiniField label="Base Size" value={getStr("trading", "baseSize")} onChange={(e) => updateField("trading", "baseSize", e.target.value)} />
                <MiniField label="Max Size" value={String(get("trading", "maxPositionSize") ?? "")} onChange={(e) => updateField("trading", "maxPositionSize", e.target.value)} />
                <MiniField label="Max Positions" value={getNum("risk", "maxPositions")} type="number" onChange={(e) => updateField("risk", "maxPositions", Number(e.target.value))} />
                <MiniSelect label="Size Mode" value={getStr("trading", "sizeMode") || "Fixed"} options={[{ value: "Fixed", label: "Fixed" }, { value: "Percent", label: "Percent" }, { value: "Kelly", label: "Kelly" }]} onChange={(e) => updateField("trading", "sizeMode", e.target.value)} />
                <MiniToggle label="Auto-Scale" checked={getBool("trading", "autoScale")} onChange={(v) => updateField("trading", "autoScale", v)} />
              </SectionCard>
              <SectionCard title="Risk Limits" star categories={["risk", "kelly"]} onSave={saveCategory} onReset={resetCategory} saving={saving} className="mt-3">
                <KellySliderWithPresets
                  value={get("kelly", "kellyMaxAllocation") ?? get("risk", "kellyFractionMultiplier") ?? 0.25}
                  onChange={(v) => { updateField("kelly", "kellyMaxAllocation", v); updateField("risk", "kellyFractionMultiplier", v); }}
                  onPreset={(preset) => {
                    const p = RISK_PRESETS[preset];
                    if (p) { updateField("kelly", "kellyMaxAllocation", p.kellyMaxAllocation); updateField("kelly", "maxPortfolioHeat", p.maxPortfolioHeat); updateField("risk", "maxPortfolioRisk", p.maxPortfolioRisk); }
                  }}
                />
                <MiniField label="Max Daily Risk" value={getNum("risk", "maxDailyRiskPct")} type="number" step="0.1" suffix="%" onChange={(e) => updateField("risk", "maxDailyRiskPct", parseFloat(e.target.value))} />
                <MiniField label="Max Per Trade" value={getNum("risk", "maxPerTradePct")} type="number" step="0.1" suffix="%" onChange={(e) => updateField("risk", "maxPerTradePct", parseFloat(e.target.value))} />
                <MiniField label="Portfolio Heat" value={getNum("kelly", "maxPortfolioHeat")} type="number" step="0.01" suffix="" onChange={(e) => updateField("kelly", "maxPortfolioHeat", parseFloat(e.target.value))} />
                <MiniField label="Correlation" value={getNum("risk", "correlationLimit")} type="number" step="0.01" onChange={(e) => updateField("risk", "correlationLimit", parseFloat(e.target.value))} />
              </SectionCard>
              <SectionCard title="Circuit Breakers" star categories={["risk"]} onSave={saveCategory} onReset={resetCategory} saving={saving} className="mt-3">
                <MiniToggle label="Master Killswitch" checked={getBool("risk", "masterKillswitch")} onChange={(v) => updateField("risk", "masterKillswitch", v)} />
                <MiniToggle label="VIX Halt (>15%)" checked={getBool("risk", "vixHalt")} onChange={(v) => updateField("risk", "vixHalt", v)} />
                <MiniToggle label="Flash Crash" checked={getBool("risk", "flashCrash")} onChange={(v) => updateField("risk", "flashCrash", v)} />
                <MiniToggle label="Daily Loss" checked={getBool("risk", "dailyLossBreaker")} onChange={(v) => updateField("risk", "dailyLossBreaker", v)} />
                <MiniToggle label="Consecutive Loss (5)" checked={getBool("risk", "consecutiveLossBreaker")} onChange={(v) => updateField("risk", "consecutiveLossBreaker", v)} />
              </SectionCard>
            </>
          )}

          {activeSection === "brokerage" && (
            <SectionCard title="Brokerage & API Keys" categories={["dataSources"]} onSave={saveCategory} onReset={resetCategory} saving={saving}>
              <ApiKeyRow source="alpaca" label="Alpaca" value={get("dataSources", "alpacaApiKey")} maskedValue={(getStr("dataSources", "alpacaApiKey") || "").slice(0, 4) + "****" || "••••"} connectionResult={connectionResults["alpaca"]} onReveal={() => revealKey("alpaca")} onCopy={() => {}} onTest={onTestConn} revealed={isKeyRevealed("alpaca")} revealExpiry={revealedKeys["alpaca"]} />
              <ApiKeyRow source="unusual_whales" label="Unusual Whales" value={get("dataSources", "unusualWhalesApiKey")} maskedValue={(getStr("dataSources", "unusualWhalesApiKey") || "").slice(0, 6) + "****" || "••••"} connectionResult={connectionResults["unusual_whales"]} onReveal={() => revealKey("unusual_whales")} onCopy={() => {}} onTest={onTestConn} revealed={isKeyRevealed("unusual_whales")} revealExpiry={revealedKeys["unusual_whales"]} />
              <ApiKeyRow source="finviz" label="Finviz" value={get("dataSources", "finvizApiKey")} maskedValue={(getStr("dataSources", "finvizApiKey") || "").slice(0, 4) + "****" || "••••"} connectionResult={connectionResults["finviz"]} onReveal={() => revealKey("finviz")} onCopy={() => {}} onTest={onTestConn} revealed={isKeyRevealed("finviz")} revealExpiry={revealedKeys["finviz"]} />
              <ApiKeyRow source="fred" label="FRED" value={get("dataSources", "fredApiKey")} maskedValue={(getStr("dataSources", "fredApiKey") || "").slice(0, 4) + "****" || "••••"} connectionResult={connectionResults["fred"]} onReveal={() => revealKey("fred")} onCopy={() => {}} onTest={onTestConn} revealed={isKeyRevealed("fred")} revealExpiry={revealedKeys["fred"]} />
            </SectionCard>
          )}

          {activeSection === "data-sources" && (
            <SectionCard title="Data Source Priority" categories={["dataSources"]} onSave={saveCategory} onReset={resetCategory} saving={saving}>
          <MiniSelect label="Primary Pricing" value={getStr("dataSources", "primaryPricing") || "polygon_sip"} options={[
            { value: "polygon_sip", label: "Polygon.io (SIP)" },
            { value: "alpaca", label: "Alpaca" },
          ]} onChange={(e) => updateField("dataSources", "primaryPricing", e.target.value)} />
          <MiniSelect label="Fallback" value={getStr("dataSources", "fallbackPricing") || "alpaca_v2"} options={[
            { value: "alpaca_v2", label: "Alpaca Data V2" },
            { value: "polygon", label: "Polygon" },
          ]} onChange={(e) => updateField("dataSources", "fallbackPricing", e.target.value)} />
          <MiniSelect label="Options Flow" value={getStr("dataSources", "optionsFlowPriority") || "unusual_whales"} options={[
            { value: "unusual_whales", label: "Unusual Whales" },
            { value: "polygon", label: "Polygon" },
          ]} onChange={(e) => updateField("dataSources", "optionsFlowPriority", e.target.value)} />
          <MiniSelect label="Economic" value={getStr("dataSources", "economicPriority") || "fred"} options={[
            { value: "fred", label: "FRED" },
            { value: "none", label: "None" },
          ]} onChange={(e) => updateField("dataSources", "economicPriority", e.target.value)} />
          <MiniSelect label="Filings" value={getStr("dataSources", "secEdgarPriority") || "sec_edgar"} options={[
            { value: "sec_edgar", label: "SEC EDGAR" },
            { value: "polygon", label: "Polygon" },
          ]} onChange={(e) => updateField("dataSources", "secEdgarPriority", e.target.value)} />
          <MiniSelect label="Rate Limit" value={getStr("dataSources", "rateLimitMode") || "conservative"} options={[
            { value: "conservative", label: "Conservative" },
            { value: "moderate", label: "Moderate" },
            { value: "aggressive", label: "Aggressive" },
          ]} onChange={(e) => updateField("dataSources", "rateLimitMode", e.target.value)} />
            </SectionCard>
          )}

          {activeSection === "ollama" && (
            <SectionCard title="Ollama Local LLM" star categories={["ollama"]} onSave={saveCategory} onReset={resetCategory} saving={saving}>
              <div className="flex items-center justify-between gap-2 py-[1px]">
                <span className="text-[10px] text-gray-400 whitespace-nowrap">Endpoint</span>
                <input type="text" value={getStr("ollama", "ollamaHostUrl") || "http://localhost:11434"} onChange={(e) => updateField("ollama", "ollamaHostUrl", e.target.value)} className="w-28 bg-[#0B0E14] border border-gray-700/50 rounded px-1.5 py-0.5 text-[10px] text-white outline-none focus:border-[#00D9FF]/50" />
              </div>
              <div className="flex items-center justify-between pt-0.5">
                <span className="text-[10px] text-gray-400">Status</span>
                <div className="flex items-center gap-1">
                  <StatusDot ok={ollamaCr.valid} testing={ollamaCr.testing} />
                  <span className="text-[9px] text-gray-400">{ollamaCr.testing ? "Testing..." : ollamaCr.valid ? "Connected" : "Not connected"}</span>
                  <button type="button" onClick={() => onTestConn("ollama")} className="text-[9px] text-[#00D9FF] hover:text-cyan-300">[Test]</button>
                </div>
              </div>
              <div className="pt-0.5 space-y-0.5">
                <span className="text-[9px] text-gray-500 block mb-0.5">Models</span>
                {((get("ollama", "activeModels") || getStr("ollama", "models") || "").split(",").filter(Boolean).length ? (get("ollama", "activeModels") || getStr("ollama", "models") || "").split(",").filter(Boolean) : ["llama3.2", "mistral", "deepseek-r1"]).map((m) => {
                  const models = (getStr("ollama", "models") || getStr("ollama", "activeModels") || "").split(",").filter(Boolean);
                  const checked = models.includes(m) || (getStr("ollama", "ollamaDefaultModel") || "").startsWith(String(m).split(":")[0]);
                  return (
                    <MiniCheckbox
                      key={m}
                      label={String(m)}
                      checked={!!checked}
                      onChange={(v) => {
                        const list = (getStr("ollama", "activeModels") || getStr("ollama", "models") || "").split(",").filter(Boolean);
                        const next = v ? [...list, m].filter((x, i, a) => a.indexOf(x) === i) : list.filter((x) => x !== m);
                        updateField("ollama", "activeModels", next.join(","));
                      }}
                    />
                  );
                })}
              </div>
              <div className="flex items-center justify-between gap-2 py-[1px] pt-0.5">
                <span className="text-[10px] text-gray-400">Use for</span>
                <input type="text" value={getStr("ollama", "useFor")} onChange={(e) => updateField("ollama", "useFor", e.target.value)} placeholder="Pattern Analysis" className="w-24 bg-[#0B0E14] border border-gray-700/50 rounded px-1.5 py-0.5 text-[10px] text-white outline-none focus:border-[#00D9FF]/50" />
              </div>
            </SectionCard>
          )}

          {activeSection === "ai-inference" && (
            <SectionCard title="AI Inference Models" categories={["ollama"]} onSave={saveCategory} onReset={resetCategory} saving={saving}>
              <div className="text-[9px] text-gray-500 mb-1">Tier 1: Ollama (local). Tier 2: Perplexity (search). Tier 3: Claude — Deep reasoning only: strategy_critic, overnight_analysis.</div>
              <MiniSelect label="Primary" value={getStr("ollama", "primaryModel") || "gpt-4o"} options={[
                { value: "gpt-4o", label: "GPT-4o" },
                { value: "claude-3.5", label: "Claude 3.5 (Tier 3)" },
              ]} onChange={(e) => updateField("ollama", "primaryModel", e.target.value)} />
              <MiniSelect label="Fallback" value={getStr("ollama", "fallbackModel") || "claude-3.5"} options={[
                { value: "claude-3.5", label: "Claude 3.5" },
                { value: "gpt-4o", label: "GPT-4o" },
              ]} onChange={(e) => updateField("ollama", "fallbackModel", e.target.value)} />
              <MiniSelect label="Local" value={getStr("ollama", "localModel") || "Ollama"} options={[
                { value: "Ollama", label: "Ollama (Tier 1)" },
                { value: "none", label: "None" },
              ]} onChange={(e) => updateField("ollama", "localModel", e.target.value)} />
              <MiniField label="Timeout" value={getNum("ollama", "timeout") || 10} type="number" suffix="s" onChange={(e) => updateField("ollama", "timeout", Number(e.target.value))} />
              <MiniField label="Max Tokens" value={getNum("ollama", "maxTokens") || 2048} type="number" onChange={(e) => updateField("ollama", "maxTokens", Number(e.target.value))} />
              <MiniField label="Temperature" value={getNum("ollama", "temperature")} type="number" step="0.1" onChange={(e) => updateField("ollama", "temperature", parseFloat(e.target.value))} />
              <div className="flex items-center justify-between gap-2 py-[1px] pt-0.5">
                <span className="text-[10px] text-gray-400">Use for</span>
                <input type="text" value={getStr("ollama", "inferenceUseFor")} onChange={(e) => updateField("ollama", "inferenceUseFor", e.target.value)} placeholder="Signal reasoning" className="w-24 bg-[#0B0E14] border border-gray-700/50 rounded px-1.5 py-0.5 text-[10px] text-white outline-none focus:border-[#00D9FF]/50" />
              </div>
            </SectionCard>
          )}

          {activeSection === "ml-models" && (
            <>
              <SectionCard title="ML Models" categories={["ml"]} onSave={saveCategory} onReset={resetCategory} saving={saving}>
                <MiniField label="Min Conf" value={getNum("ml", "minConf") || get("ml", "confidenceThreshold")} type="number" step="0.01" onChange={(e) => updateField("ml", "confidenceThreshold", parseFloat(e.target.value))} />
                <MiniField label="Lookback" value={getNum("ml", "walkForwardWindow") || getNum("ml", "lookback")} type="number" onChange={(e) => updateField("ml", "walkForwardWindow", Number(e.target.value))} />
                <MiniSelect label="Retrain" value={getStr("ml", "retrainFrequency") || "weekly"} options={[{ value: "daily", label: "Daily" }, { value: "weekly", label: "Weekly" }, { value: "monthly", label: "Monthly" }]} onChange={(e) => updateField("ml", "retrainFrequency", e.target.value)} />
              </SectionCard>
              <SectionCard title="ML Flywheel" star categories={["ml"]} onSave={saveCategory} onReset={resetCategory} saving={saving} className="mt-3">
                <MiniSelect label="Learning Loop" value={getStr("ml", "learningLoop") || "auto"} options={[{ value: "auto", label: "Auto" }, { value: "manual", label: "Manual" }, { value: "hybrid", label: "Hybrid" }]} onChange={(e) => updateField("ml", "learningLoop", e.target.value)} />
                <MiniToggle label="Auto-Retrain" checked={getBool("ml", "autoRetrain")} onChange={(v) => updateField("ml", "autoRetrain", v)} />
                <MiniToggle label="Drift Detection" checked={getBool("ml", "driftDetectionEnabled")} onChange={(v) => updateField("ml", "driftDetectionEnabled", v)} />
                <MiniField label="Walk-Forward" value={getStr("ml", "walkForward")} onChange={(e) => updateField("ml", "walkForward", e.target.value)} />
                <MiniField label="Validation" value={getNum("ml", "validationDays")} type="number" suffix="days" onChange={(e) => updateField("ml", "validationDays", Number(e.target.value))} />
                <MiniField label="Min Samples" value={getNum("ml", "minSamples")} type="number" onChange={(e) => updateField("ml", "minSamples", Number(e.target.value))} />
              </SectionCard>
            </>
          )}

          {activeSection === "agents" && (
            <>
              <SectionCard title="OpenClaw Agents" star categories={["agents"]} onSave={saveCategory} onReset={resetCategory} saving={saving}>
                <MiniSelect label="Swarm Mode" value={getStr("agents", "swarmMode") || "Parallel"} options={[{ value: "Parallel", label: "Parallel" }, { value: "Sequential", label: "Sequential" }, { value: "Hybrid", label: "Hybrid" }]} onChange={(e) => updateField("agents", "swarmMode", e.target.value)} />
                <MiniToggle label="Blackboard" checked={getBool("agents", "blackboard")} onChange={(v) => updateField("agents", "blackboard", v)} />
                {["marketDataAgent", "riskAgent", "signalEngine", "patternAI", "youtubeAgent", "driftMonitor", "flywheelEngine", "openclawBridge"].map((key) => (
                  <MiniToggle key={key} label={key.replace(/([A-Z])/g, " $1").trim()} checked={getBool("agents", key)} onChange={(v) => updateField("agents", key, v)} />
                ))}
              </SectionCard>
              <SectionCard title="Agent Coordination" categories={["agents", "logging"]} onSave={saveCategory} onReset={resetCategory} saving={saving} className="mt-3">
                <MiniField label="Timeout" value={getNum("agents", "agentTimeout")} type="number" suffix="s" onChange={(e) => updateField("agents", "agentTimeout", Number(e.target.value))} />
                <MiniField label="Max Concurrent" value={getNum("agents", "maxConcurrentAgents")} type="number" onChange={(e) => updateField("agents", "maxConcurrentAgents", Number(e.target.value))} />
                <MiniSelect label="Log Level" value={getStr("logging", "logLevel") || "INFO"} options={[{ value: "DEBUG", label: "DEBUG" }, { value: "INFO", label: "INFO" }, { value: "WARNING", label: "WARNING" }, { value: "ERROR", label: "ERROR" }]} onChange={(e) => updateField("logging", "logLevel", e.target.value)} />
              </SectionCard>
            </>
          )}

          {activeSection === "trade-mgmt" && (
            <SectionCard title="Trade Management" categories={["risk", "trading"]} onSave={saveCategory} onReset={resetCategory} saving={saving}>
              <MiniField label="Default SL" value={getStr("risk", "stopLossDefault")} type="number" step="0.01" onChange={(e) => updateField("risk", "stopLossDefault", parseFloat(e.target.value))} />
              <MiniField label="TP1" value={getNum("risk", "takeProfit1")} type="number" step="0.1" suffix="R" onChange={(e) => updateField("risk", "takeProfit1", parseFloat(e.target.value))} />
              <MiniField label="TP2" value={getNum("risk", "takeProfit2")} type="number" step="0.1" suffix="R" onChange={(e) => updateField("risk", "takeProfit2", parseFloat(e.target.value))} />
              <MiniField label="Trailing" value={getNum("risk", "trailingStop")} type="number" step="0.1" suffix="R" onChange={(e) => updateField("risk", "trailingStop", parseFloat(e.target.value))} />
              <MiniToggle label="Extended Hours" checked={getBool("trading", "afterHoursEnabled")} onChange={(v) => updateField("trading", "afterHoursEnabled", v)} />
              <MiniToggle label="Dry Run" checked={getBool("trading", "dryRun")} onChange={(v) => updateField("trading", "dryRun", v)} />
            </SectionCard>
          )}

          {activeSection === "order-exec" && (
            <SectionCard title="Order Execution" categories={["trading"]} onSave={saveCategory} onReset={resetCategory} saving={saving}>
              <MiniSelect label="Order Type" value={getStr("trading", "defaultOrderType") || "market"} options={[{ value: "market", label: "Market" }, { value: "limit", label: "Limit" }, { value: "stop", label: "Stop" }, { value: "stop_limit", label: "Stop Limit" }]} onChange={(e) => updateField("trading", "defaultOrderType", e.target.value)} />
              <MiniField label="Slippage" value={getNum("trading", "slippageTolerance")} type="number" step="0.01" suffix="%" onChange={(e) => updateField("trading", "slippageTolerance", parseFloat(e.target.value))} />
              <MiniToggle label="Pre-Trade Check" checked={getBool("trading", "preTradeCheck")} onChange={(v) => updateField("trading", "preTradeCheck", v)} />
              <MiniToggle label="Confirm Before Order" checked={getBool("trading", "confirmBeforeOrder")} onChange={(v) => updateField("trading", "confirmBeforeOrder", v)} />
            </SectionCard>
          )}

          {activeSection === "notifications" && (
            <SectionCard title="Notifications" star categories={["notifications"]} onSave={saveCategory} onReset={resetCategory} saving={saving}>
              <div className="mb-0.5 text-[9px] text-gray-500 uppercase font-bold">Channels (dot: green=OK, red=fail, gray=not configured)</div>
              <NotificationToggleWithDot label="Email (Resend)" checked={getBool("notifications", "tradeAlerts")} onChange={(v) => updateField("notifications", "tradeAlerts", v)} status={connectionResults["resend"]?.valid === true ? "ok" : connectionResults["resend"]?.valid === false ? "fail" : null} />
              <div className="flex items-center justify-between py-[1px] gap-2">
                <span className="text-[10px] text-gray-400">Slack</span>
                <StatusDot ok={null} />
                <span className="text-[9px] text-gray-500">{getStr("notifications", "slackWebhookUrl") ? "Configured" : "Not set"}</span>
              </div>
              <div className="flex items-center justify-between py-[1px] gap-2">
                <span className="text-[10px] text-gray-400">Telegram</span>
                <StatusDot ok={null} />
                <span className="text-[9px] text-gray-500">{getStr("notifications", "telegramBotToken") ? "Configured" : "Not set"}</span>
              </div>
              <MiniToggle label="Trade Alerts" checked={getBool("notifications", "tradeAlerts")} onChange={(v) => updateField("notifications", "tradeAlerts", v)} />
              <MiniToggle label="Risk Alerts" checked={getBool("notifications", "riskAlerts")} onChange={(v) => updateField("notifications", "riskAlerts", v)} />
              <MiniToggle label="Daily Summary" checked={getBool("notifications", "dailySummary")} onChange={(v) => updateField("notifications", "dailySummary", v)} />
              <MiniToggle label="Signal Alerts" checked={getBool("notifications", "signalAlerts")} onChange={(v) => updateField("notifications", "signalAlerts", v)} />
            </SectionCard>
          )}

          {activeSection === "security" && (
            <SectionCard title="Security & Auth" star categories={["system"]} onSave={saveCategory} onReset={resetCategory} saving={saving}>
              <div className="flex items-center justify-between py-[1px]">
                <span className="text-[10px] text-gray-400">Encryption</span>
                <span className="text-[9px] text-emerald-400 flex items-center gap-1"><span className="w-1.5 h-1.5 rounded-full bg-emerald-500" /> AES-256 Active</span>
              </div>
              <div className="flex items-center justify-between py-[1px]">
                <span className="text-[10px] text-gray-400">Session</span>
                <span className="text-[9px] text-gray-300">24h timeout</span>
              </div>
            </SectionCard>
          )}

          {activeSection === "backup" && (
            <SectionCard title="Backup & Import/Export" categories={["system"]} onSave={saveCategory} onReset={resetCategory} saving={saving}>
              <div className="flex gap-2 mb-1">
                <button type="button" onClick={onExport} className="text-[9px] text-[#00D9FF] hover:text-cyan-300">[Export JSON]</button>
                <button type="button" onClick={() => importRef.current?.click()} className="text-[9px] text-[#00D9FF] hover:text-cyan-300">[Import JSON]</button>
              </div>
              <MiniField label="Last Backup" value={getStr("system", "lastBackup")} onChange={(e) => updateField("system", "lastBackup", e.target.value)} />
              <MiniSelect label="Auto-Backup" value={getStr("system", "autoBackup") || "Daily"} options={[{ value: "Daily", label: "Daily" }, { value: "Weekly", label: "Weekly" }, { value: "Manual", label: "Manual" }]} onChange={(e) => updateField("system", "autoBackup", e.target.value)} />
              <MiniField label="Location" value={getStr("system", "backupLocation")} onChange={(e) => updateField("system", "backupLocation", e.target.value)} />
            </SectionCard>
          )}

          {activeSection === "appearance" && (
            <SectionCard title="Display & Appearance" categories={["appearance", "system"]} onSave={saveCategory} onReset={resetCategory} saving={saving}>
              <div className="grid grid-cols-3 gap-2 mb-1">
                {[
                  { key: "midnight", name: "Midnight Bloomberg", bg: "#0B0E14", surface: "#111827", accent: "#00D9FF" },
                  { key: "classic", name: "Classic Dark", bg: "#1a1a2e", surface: "#16213e", accent: "#0f3460" },
                  { key: "dark", name: "Aurora Dark", bg: "#0a0e1a", surface: "#111827", accent: "#00D9FF" },
                ].map((theme) => (
                  <button
                    key={theme.key}
                    type="button"
                    onClick={() => updateField("appearance", "theme", theme.key)}
                    className={`flex flex-col items-center gap-1 p-2 border-2 rounded-md hover:border-[#00D9FF]/50 transition-all ${(get("appearance", "theme") || get("system", "theme") || "dark") === theme.key ? "border-[#00D9FF] ring-1 ring-[#00D9FF]/30" : "border-gray-700"}`}
                  >
                    <div className="w-full h-10 rounded-sm flex gap-0.5" style={{ background: theme.bg }}>
                      <div className="w-1/4 h-full rounded-sm" style={{ background: theme.surface }} />
                      <div className="flex-1 h-full rounded-sm" style={{ background: theme.surface }}>
                        <div className="w-3/4 h-1 mt-2 mx-auto rounded" style={{ background: theme.accent }} />
                      </div>
                    </div>
                    <span className="text-[9px] text-gray-500">{theme.name}</span>
                  </button>
                ))}
              </div>
              <MiniSelect label="Density" value={getStr("appearance", "density") || "compact"} options={[{ value: "Ultra Dense", label: "Ultra Dense" }, { value: "compact", label: "Compact" }, { value: "Comfortable", label: "Comfortable" }]} onChange={(e) => updateField("appearance", "density", e.target.value)} />
            </SectionCard>
          )}

          {activeSection === "strategy" && (
            <SectionCard title="Strategy" categories={["strategy"]} onSave={saveCategory} onReset={resetCategory} saving={saving}>
              <MiniToggle label="Adaptive" checked={getBool("strategy", "adaptive")} onChange={(v) => updateField("strategy", "adaptive", v)} />
              <MiniField label="Min Prob" value={getNum("strategy", "minProb")} type="number" step="0.01" onChange={(e) => updateField("strategy", "minProb", parseFloat(e.target.value))} />
              <MiniSelect label="Override" value={getStr("strategy", "override") || "None"} options={[{ value: "None", label: "None" }, { value: "Bull", label: "Bull" }, { value: "Bear", label: "Bear" }, { value: "Neutral", label: "Neutral" }]} onChange={(e) => updateField("strategy", "override", e.target.value)} />
              <MiniSelect label="Entry" value={getStr("strategy", "entryMethod") || "signal"} options={[{ value: "signal", label: "Signal" }, { value: "manual", label: "Manual" }]} onChange={(e) => updateField("strategy", "entryMethod", e.target.value)} />
            </SectionCard>
          )}

          {activeSection === "audit" && (
            <SectionCard title="Audit Log" categories={[]}>
              <div className="overflow-x-auto">
                <table className="w-full text-[9px]">
                  <thead>
                    <tr className="text-gray-500 border-b border-gray-800/50">
                      <th className="text-left py-1 font-bold">Time</th>
                      <th className="text-left py-1 font-bold">Cat</th>
                      <th className="text-left py-1 font-bold">Actor</th>
                      <th className="text-left py-1 font-bold">Event</th>
                    </tr>
                  </thead>
                  <tbody className="text-gray-400">
                    {[].map((row, i) => (
                      <tr key={i} className="border-b border-gray-800/30">
                        <td className="py-0.5">{row.time}</td>
                        <td className="py-0.5">{row.cat}</td>
                        <td className="py-0.5">{row.actor}</td>
                        <td className="py-0.5">{row.event}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              <button type="button" onClick={() => setShowFullLog(!showFullLog)} className="mt-1 text-[9px] text-[#00D9FF] hover:text-cyan-300">[View Full Log]</button>
            </SectionCard>
          )}
        </main>
      </div>

      {/* FOOTER BAR */}
      <div className="flex items-center justify-between p-3 border-t border-[rgba(30,41,59,0.5)] bg-[#111827]">
        <div className="flex gap-3">
          <button type="button" onClick={onExport} className="text-[10px] text-[#00D9FF] hover:text-cyan-300">[Export Settings]</button>
          <button type="button" onClick={() => importRef.current?.click()} className="text-[10px] text-[#00D9FF] hover:text-cyan-300">[Import Settings]</button>
          <button
            type="button"
            onClick={async () => {
              if (!window.confirm("Reset Trading, Risk, ML, and Agents to defaults?")) return;
              try {
                for (const c of ["trading", "risk", "ml", "agents"]) await resetCategory(c);
                toast.success("Defaults reset", TOAST_CFG);
              } catch { toast.error("Reset failed", TOAST_CFG); }
            }}
            className="text-[10px] text-[#00D9FF] hover:text-cyan-300"
          >
            [Reset Defaults]
          </button>
        </div>
        <button type="button" onClick={async () => { try { await saveAllSettings(); toast.success("All settings saved", TOAST_CFG); } catch { toast.error("Save failed", TOAST_CFG); } }} disabled={saving} className="bg-[#00D9FF] hover:bg-[#00D9FF]/80 text-black font-bold text-[10px] px-5 py-1.5 rounded uppercase tracking-wider disabled:opacity-50 flex items-center gap-1.5">
          <Save className="w-3 h-3" />
          {saving ? "Saving..." : "SAVE ALL CHANGES"}
        </button>
      </div>

      {showFullLog && (
        <div className="p-4">
          <AuditLogPanel />
        </div>
      )}
    </div>
  );
}

// -- Audit Log Panel --
function AuditLogPanel() {
  const { data: auditData, loading: logLoading } = useApi("settings", { endpoint: "/settings/audit-log" });
  const logs = auditData?.logs || [];

  return (
    <SectionCard title="System / Audit Log" className="w-full">
      {logLoading ? (
        <div className="flex items-center gap-2 text-gray-500 text-xs p-2">
          <Loader2 className="w-4 h-4 animate-spin" /> Loading audit log...
        </div>
      ) : logs.length === 0 ? (
        <p className="text-gray-500 text-xs p-2">No audit entries found.</p>
      ) : (
        <div className="space-y-0.5 max-h-[400px] overflow-y-auto">
          {logs.map((log, i) => (
            <div key={i} className="flex items-center gap-3 py-1 px-2 text-xs border-b border-gray-800/50 hover:bg-gray-800/30">
              <span className="text-gray-500 font-mono w-36 shrink-0 text-[10px]">{new Date(log.timestamp).toLocaleString()}</span>
              <span className={`w-14 shrink-0 font-bold uppercase text-[10px] ${
                log.action === "update" ? "text-yellow-500" : log.action === "reset" ? "text-red-400" : "text-[#00D9FF]"
              }`}>{log.action}</span>
              <span className="text-gray-300 text-[10px]">{log.category}</span>
              <span className="text-gray-500 truncate text-[10px]">{log.detail || ""}</span>
            </div>
          ))}
        </div>
      )}
      <div className="mt-1.5 pt-1 border-t border-gray-800/50">
        <button
          onClick={() => {
            const blob = new Blob([JSON.stringify(logs, null, 2)], { type: "application/json" });
            const a = document.createElement("a");
            a.href = URL.createObjectURL(blob);
            a.download = "audit-log.json";
            a.click();
          }}
          className="text-[9px] text-[#00D9FF] hover:text-cyan-300 flex items-center gap-1"
        >
          <Download className="w-2.5 h-2.5" /> Export Log
        </button>
      </div>
    </SectionCard>
  );
}
