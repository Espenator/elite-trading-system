import React, { useState, useEffect, useRef } from "react";
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
  Monitor, Lock, Clock, ChevronDown,
} from "lucide-react";

// -- Toast config --
const TOAST_CFG = { position: "bottom-right", theme: "dark" };

// -- Tiny reusable components --

function StatusDot({ ok, testing }) {
  if (testing) return <Loader2 className="w-3 h-3 animate-spin text-[#00D9FF]" />;
  if (ok === true) return <CheckCircle2 className="w-3 h-3 text-[#10b981]" />;
  if (ok === false) return <AlertTriangle className="w-3 h-3 text-red-400" />;
  return <div className="w-2 h-2 rounded-full bg-gray-600" />;
}

function SectionCard({ title, children, className = "" }) {
  return (
    <div className={`bg-[#111827] border border-[rgba(42,52,68,0.5)] rounded-lg p-2 ${className}`}>
      <div className="flex items-center gap-1.5 mb-1.5 pb-1 border-b border-gray-800/50">
        <span className="text-xs font-bold uppercase tracking-wider text-slate-400 font-mono">{title}</span>
      </div>
      <div className="space-y-0.5">{children}</div>
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
          className={`w-20 bg-[#0B0E14] border border-gray-700/50 rounded px-1.5 py-0.5 text-[10px] text-white outline-none focus:border-[#00D9FF]/50/50 ${className}`}
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
        className="bg-[#0B0E14] border border-gray-700/50 rounded px-1 py-0.5 text-[10px] text-white outline-none focus:border-[#00D9FF]/50/50 appearance-none cursor-pointer pr-4"
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
          checked ? "bg-cyan-500/30 border-[#00D9FF]/50/50" : "bg-gray-700/30 border-gray-600/50"
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
            ? "bg-cyan-500/30 border-[#00D9FF]/50/50 text-[#00D9FF]"
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

  const get = (cat, key, fallback = "") => S[cat]?.[key] ?? fallback;

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

  if (loading) {
    return (
      <div className="min-h-screen bg-[#0B0E14] flex items-center justify-center">
        <Loader2 className="w-6 h-6 animate-spin text-[#00D9FF]" />
        <span className="ml-2 text-gray-400 text-sm">Loading settings...</span>
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
    <div className="min-h-screen bg-[#0B0E14] text-gray-100 p-3">
      {/* Hidden import input */}
      <input ref={importRef} type="file" accept=".json" className="hidden" onChange={onImport} />

      {/* HEADER */}
      <div className="flex items-center justify-between mb-3 pb-2 border-b border-[rgba(42,52,68,0.5)]">
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
          onClick={saveAllSettings}
          disabled={saving}
          className="bg-[#00D9FF] hover:bg-[#00D9FF]/80 text-black font-bold text-[11px] px-5 py-1.5 rounded uppercase tracking-wider disabled:opacity-50 flex items-center gap-1.5 transition-all hover:shadow-[0_0_12px_rgba(0,217,255,0.4)]"
        >
          <Save className="w-3.5 h-3.5" />
          {saving ? "Saving..." : "SAVE ALL"}
        </button>
      </div>

      {/* ROW 1: Identity & Locale, Trading Mode, Position Rules, Risk Limits, Circuit Breakers */}
      <div className="grid grid-cols-5 gap-2 mb-2">

        {/* 1. IDENTITY & LOCALE */}
        <SectionCard title="Identity & Locale">
          <MiniField label="Display Name" value={get("user", "displayName", "Espen Schiefloe")} onChange={(e) => updateField("user", "displayName", e.target.value)} />
          <MiniSelect label="Timezone" value={get("user", "timezone", "America/New_York")} options={[
            { value: "America/New_York", label: "EST" },
            { value: "America/Chicago", label: "CT" },
            { value: "America/Los_Angeles", label: "PT" },
            { value: "UTC", label: "UTC" },
            { value: "Europe/Oslo", label: "CET" },
          ]} onChange={(e) => updateField("user", "timezone", e.target.value)} />
          <MiniSelect label="Language" value={get("user", "language", "en")} options={[
            { value: "en", label: "English" },
            { value: "no", label: "Norwegian" },
          ]} onChange={(e) => updateField("user", "language", e.target.value)} />
          <MiniField label="Timeframe" value={get("appearance", "chartTimeframe", "15")} onChange={(e) => updateField("appearance", "chartTimeframe", e.target.value)} />
          <MiniField label="# Stocks" value={get("scanning", "maxStocks", 15)} type="number" onChange={(e) => updateField("scanning", "maxStocks", Number(e.target.value))} />
          <MiniToggle label="Show FII" checked={!!get("appearance", "showFill", true)} onChange={(v) => updateField("appearance", "showFill", v)} />
        </SectionCard>

        {/* 2. TRADING MODE */}
        <SectionCard title="Trading Mode">
          <div className="flex items-center gap-4 mb-1">
            <span className={`text-sm font-bold ${get("dataSources", "alpacaBaseUrl", "paper") === "paper" ? "text-[#00D9FF]" : "text-gray-500"}`}>PAPER</span>
            <button
              onClick={() => updateField("dataSources", "alpacaBaseUrl", get("dataSources", "alpacaBaseUrl", "paper") === "paper" ? "live" : "paper")}
              className={`relative w-14 h-7 rounded-full transition-colors ${get("dataSources", "alpacaBaseUrl", "paper") === "live" ? "bg-red-500" : "bg-cyan-500"}`}
            >
              <div className={`absolute top-0.5 w-6 h-6 bg-white rounded-full transition-transform ${get("dataSources", "alpacaBaseUrl", "paper") === "live" ? "translate-x-7" : "translate-x-0.5"}`} />
            </button>
            <span className={`text-sm font-bold ${get("dataSources", "alpacaBaseUrl", "paper") === "live" ? "text-red-400" : "text-gray-500"}`}>LIVE</span>
          </div>
          {get("dataSources", "alpacaBaseUrl", "paper") === "live" && (
            <p className="text-[10px] text-amber-400 mt-1">⚠ Live mode = real money</p>
          )}
          <MiniSelect label="Broker" value={get("trading", "broker", "alpaca")} options={[
            { value: "alpaca", label: "Alpaca Markets" },
            { value: "ibkr", label: "Interactive Brokers" },
          ]} onChange={(e) => updateField("trading", "broker", e.target.value)} />
          <MiniField label="Account" value={get("trading", "accountType", "Paper Trading")} onChange={(e) => updateField("trading", "accountType", e.target.value)} />
          <div className="flex items-center justify-between py-[1px]">
            <span className="text-[10px] text-gray-400">Paper Trading</span>
            <span className="text-[9px] text-green-400">Active</span>
          </div>
        </SectionCard>

        {/* 3. POSITION RULES */}
        <SectionCard title="Position Rules">
          <MiniField label="Base Size" value={get("trading", "maxPositionSize", "$15,000")} onChange={(e) => updateField("trading", "maxPositionSize", e.target.value)} />
          <MiniField label="Max Daily Risk" value={get("risk", "maxDailyRiskPct", 2.5)} type="number" step="0.1" suffix="%" onChange={(e) => updateField("risk", "maxDailyRiskPct", parseFloat(e.target.value))} />
          <MiniField label="Max Open" value={get("risk", "maxPositions", 15)} type="number" onChange={(e) => updateField("risk", "maxPositions", Number(e.target.value))} />
          <MiniField label="Max Sector" value={get("risk", "maxSectorExposure", 30)} type="number" suffix="%" onChange={(e) => updateField("risk", "maxSectorExposure", Number(e.target.value))} />
          <MiniToggle label="Auto-Scale" checked={!!get("trading", "autoScale", true)} onChange={(v) => updateField("trading", "autoScale", v)} />
          <MiniField label="Correlation" value={get("risk", "correlationLimit", 0.71)} type="number" step="0.01" onChange={(e) => updateField("risk", "correlationLimit", parseFloat(e.target.value))} />
        </SectionCard>

        {/* 4. RISK LIMITS */}
        <SectionCard title="Risk Limits">
          <MiniField label="Max Daily Risk" value={get("risk", "maxDailyRisk", 2.5)} type="number" step="0.1" suffix="%" onChange={(e) => updateField("risk", "maxDailyRisk", parseFloat(e.target.value))} />
          <MiniField label="Master Killswitch" value={get("risk", "masterKillswitch", "$2,500")} onChange={(e) => updateField("risk", "masterKillswitch", e.target.value)} />
          <MiniField label="Flash Crash" value={get("risk", "flashCrashLimit", "$1,000")} onChange={(e) => updateField("risk", "flashCrashLimit", e.target.value)} />
          <MiniField label="Max Drawdown" value={get("risk", "maxDrawdownPct", 5)} type="number" suffix="%" onChange={(e) => updateField("risk", "maxDrawdownPct", Number(e.target.value))} />
          <MiniField label="VaR Limit" value={get("risk", "varLimit", 1.5)} type="number" step="0.1" suffix="%" onChange={(e) => updateField("risk", "varLimit", parseFloat(e.target.value))} />
          <MiniToggle label="Auto-Pause" checked={!!get("risk", "autoPause", true)} onChange={(v) => updateField("risk", "autoPause", v)} />
        </SectionCard>

        {/* 5. CIRCUIT BREAKERS */}
        <SectionCard title="Circuit Breakers">
          <MiniField label="Daily Loss Limit" value={get("risk", "dailyLossLimit", "$2,500")} onChange={(e) => updateField("risk", "dailyLossLimit", e.target.value)} />
          <MiniField label="Market Killswitch" value={get("risk", "marketKillswitch", "$2,500")} onChange={(e) => updateField("risk", "marketKillswitch", e.target.value)} />
          <MiniField label="Flash Crash" value={get("risk", "flashCrash", "$1,000")} onChange={(e) => updateField("risk", "flashCrash", e.target.value)} />
          <MiniField label="Consecutive Loss" value={get("risk", "consecutiveLossLimit", 5)} type="number" onChange={(e) => updateField("risk", "consecutiveLossLimit", Number(e.target.value))} />
          <MiniToggle label="Circuit Breaker" checked={!!get("risk", "circuitBreaker", true)} onChange={(v) => updateField("risk", "circuitBreaker", v)} />
          <MiniToggle label="Auto-Pause Trading" checked={!!get("risk", "autoPauseTrading", true)} onChange={(v) => updateField("risk", "autoPauseTrading", v)} />
        </SectionCard>
      </div>

      {/* ROW 2: Brokerage Connections, Data Feed API Keys, Data Source Priority, Global Local LLM, Inference Models */}
      <div className="grid grid-cols-5 gap-2 mb-2">

        {/* 6. BROKERAGE CONNECTIONS */}
        <SectionCard title="Brokerage Connections">
          <div className="flex items-center justify-between py-0.5">
            <span className="text-[10px] text-gray-400">Alpaca Markets<span className="text-amber-500 text-[10px] ml-1">★</span></span>
            <div className="flex items-center gap-1">
              <ConnBadge status="connected" label="Connected" />
              <span className="text-[8px] text-gray-600">[Test][Edit]</span>
            </div>
          </div>
          <div className="flex items-center justify-between py-0.5">
            <span className="text-[10px] text-gray-400">Interactive Brokers<span className="text-amber-500 text-[10px] ml-1">★</span></span>
            <ConnBadge status="not_configured" label="Not Connected" />
          </div>
          <div className="flex items-center justify-between py-0.5">
            <span className="text-[10px] text-gray-400">TD Ameritrade<span className="text-amber-500 text-[10px] ml-1">★</span></span>
            <ConnBadge status="not_configured" label="Not Connected" />
          </div>
          <div className="mt-1.5 pt-1 border-t border-gray-800/50">
            <button className="text-[9px] text-[#00D9FF] hover:text-cyan-300 flex items-center gap-1">
              + Add Broker
            </button>
          </div>
        </SectionCard>

        {/* 7. DATA FEED API KEYS */}
        <SectionCard title="Data Feed API Keys">
          <div className="flex items-center justify-between py-0.5">
            <span className="text-[10px] text-gray-400">Unusual Whales<span className="text-amber-500 text-[10px] ml-1">★</span></span>
            <div className="flex items-center gap-1">
              <ConnBadge status="connected" label="Connected" />
              <span className="text-[8px] text-gray-600">[Test][Edit]</span>
            </div>
          </div>
          <div className="flex items-center justify-between py-0.5">
            <span className="text-[10px] text-gray-400">Polygon.io<span className="text-amber-500 text-[10px] ml-1">★</span></span>
            <div className="flex items-center gap-1">
              <ConnBadge status="aggregated" label="Aggregated" />
            </div>
          </div>
          <div className="flex items-center justify-between py-0.5">
            <span className="text-[10px] text-gray-400">FinViz</span>
            <span className="text-[9px] text-gray-500">N/A</span>
          </div>
          <div className="flex items-center justify-between py-0.5">
            <span className="text-[10px] text-gray-400">FRED<span className="text-amber-500 text-[10px] ml-1">★</span></span>
            <span className="text-[9px] text-gray-500">Not set</span>
          </div>
          <div className="flex items-center justify-between py-0.5">
            <span className="text-[10px] text-gray-400">SEC EDGAR</span>
            <span className="text-[9px] text-gray-500">N/A</span>
          </div>
        </SectionCard>

        {/* 8. DATA SOURCE PRIORITY */}
        <SectionCard title="Data Source Priority">
          <MiniSelect label="Polygon v3 (SPX)" value={get("dataSources", "endpointPriority", "polygon")} options={["polygon", "alpaca", "benzinga"]} onChange={(e) => updateField("dataSources", "endpointPriority", e.target.value)} />
          <MiniSelect label="Options Flow" value={get("dataSources", "optionsFlowPriority", "unusual_whales")} options={[
            { value: "unusual_whales", label: "Unusual Whales" },
            { value: "polygon", label: "Polygon" },
          ]} onChange={(e) => updateField("dataSources", "optionsFlowPriority", e.target.value)} />
          <MiniSelect label="SEC EDGAR" value={get("dataSources", "secEdgarPriority", "sec_edgar")} options={["sec_edgar", "polygon"]} onChange={(e) => updateField("dataSources", "secEdgarPriority", e.target.value)} />
          <MiniSelect label="Rate Limit" value={get("dataSources", "rateLimitMode", "conservative")} options={["conservative", "moderate", "aggressive"]} onChange={(e) => updateField("dataSources", "rateLimitMode", e.target.value)} />
        </SectionCard>

        {/* 9. GLOBAL LOCAL LLM */}
        <SectionCard title="Global Local LLM">
          <div className="flex items-center justify-between gap-2 py-[1px]">
            <span className="text-[10px] text-gray-400 whitespace-nowrap">Endpoint<span className="text-amber-500 text-[10px] ml-1">★</span></span>
            <input type="text" value={get("ollama", "ollamaHostUrl", "http://localhost:11434")} onChange={(e) => updateField("ollama", "ollamaHostUrl", e.target.value)} className="w-28 bg-[#0B0E14] border border-gray-700/50 rounded px-1.5 py-0.5 text-[10px] text-white outline-none focus:border-[#00D9FF]/50/50" />
          </div>
          <div className="flex items-center justify-between gap-2 py-[1px]">
            <span className="text-[10px] text-gray-400 whitespace-nowrap">Model<span className="text-amber-500 text-[10px] ml-1">★</span></span>
            <input type="text" value={get("ollama", "ollamaDefaultModel", "llama3")} onChange={(e) => updateField("ollama", "ollamaDefaultModel", e.target.value)} className="w-20 bg-[#0B0E14] border border-gray-700/50 rounded px-1.5 py-0.5 text-[10px] text-white outline-none focus:border-[#00D9FF]/50/50" />
          </div>
          <MiniField label="GPT-4" value={get("ollama", "gpt4oStatus", "disabled")} onChange={(e) => updateField("ollama", "gpt4oStatus", e.target.value)} />
          <MiniField label="Context" value={get("ollama", "ollamaContextLength", 8192)} type="number" suffix="tok" onChange={(e) => updateField("ollama", "ollamaContextLength", Number(e.target.value))} />
          <MiniToggle label="CUDA" checked={!!get("ollama", "ollamaCudaEnabled", false)} onChange={(v) => updateField("ollama", "ollamaCudaEnabled", v)} />
          <div className="flex items-center justify-between pt-0.5">
            <button onClick={() => onTestConn("ollama")} className="text-[9px] text-purple-400 hover:text-purple-300 flex items-center gap-1">
              <Wifi className="w-2.5 h-2.5" /> {ollamaCr.testing ? "Testing..." : "Test"}
            </button>
            <StatusDot ok={ollamaCr.valid} testing={ollamaCr.testing} />
          </div>
        </SectionCard>

        {/* 10. INFERENCE MODELS */}
        <SectionCard title="Inference Models">
          <div className="flex items-center justify-between gap-2 py-[1px]">
            <span className="text-[10px] text-gray-400 whitespace-nowrap">GPT-4o<span className="text-amber-500 text-[10px] ml-1">★</span></span>
            <input type="text" value={get("ollama", "gpt4Status", "disabled")} onChange={(e) => updateField("ollama", "gpt4Status", e.target.value)} className="w-20 bg-[#0B0E14] border border-gray-700/50 rounded px-1.5 py-0.5 text-[10px] text-white outline-none focus:border-[#00D9FF]/50/50" />
          </div>
          <div className="flex items-center justify-between py-[1px]">
            <span className="text-[10px] text-gray-400">GPU/CPU</span>
            <span className="text-[9px] text-[#00D9FF]">auto</span>
          </div>
          <div className="flex items-center justify-between gap-2 py-[1px]">
            <span className="text-[10px] text-gray-400 whitespace-nowrap">Signal Model<span className="text-amber-500 text-[10px] ml-1">★</span></span>
            <input type="text" value={get("ollama", "signalAnalysisModel", "Signal Analysis")} onChange={(e) => updateField("ollama", "signalAnalysisModel", e.target.value)} className="w-20 bg-[#0B0E14] border border-gray-700/50 rounded px-1.5 py-0.5 text-[10px] text-white outline-none focus:border-[#00D9FF]/50/50" />
          </div>
          <div className="flex items-center justify-between gap-2 py-[1px]">
            <span className="text-[10px] text-gray-400 whitespace-nowrap">Pattern Model<span className="text-amber-500 text-[10px] ml-1">★</span></span>
            <input type="text" value={get("ollama", "patternAnalysisModel", "Pattern Analysis")} onChange={(e) => updateField("ollama", "patternAnalysisModel", e.target.value)} className="w-20 bg-[#0B0E14] border border-gray-700/50 rounded px-1.5 py-0.5 text-[10px] text-white outline-none focus:border-[#00D9FF]/50/50" />
          </div>
          <div className="flex items-center justify-between gap-2 py-[1px]">
            <span className="text-[10px] text-gray-400 whitespace-nowrap">Gen Model<span className="text-amber-500 text-[10px] ml-1">★</span></span>
            <input type="text" value={get("ollama", "signalGenerationModel", "Signal Generation")} onChange={(e) => updateField("ollama", "signalGenerationModel", e.target.value)} className="w-20 bg-[#0B0E14] border border-gray-700/50 rounded px-1.5 py-0.5 text-[10px] text-white outline-none focus:border-[#00D9FF]/50/50" />
          </div>
          <div className="flex items-center justify-between gap-2 py-[1px]">
            <span className="text-[10px] text-gray-400 whitespace-nowrap">Fallback<span className="text-amber-500 text-[10px] ml-1">★</span></span>
            <input type="text" value={get("ollama", "fallbackModel", "llama3")} onChange={(e) => updateField("ollama", "fallbackModel", e.target.value)} className="w-20 bg-[#0B0E14] border border-gray-700/50 rounded px-1.5 py-0.5 text-[10px] text-white outline-none focus:border-[#00D9FF]/50/50" />
          </div>
          <MiniField label="Max Tokens" value={get("ollama", "maxTokens", "500K+")} onChange={(e) => updateField("ollama", "maxTokens", e.target.value)} />
        </SectionCard>
      </div>

      {/* ROW 3: ML Models, Learning Log, OpenClaw Agents, Agent Thresholds, Signal Thresholds */}
      <div className="grid grid-cols-5 gap-2 mb-2">

        {/* 11. ML MODELS */}
        <SectionCard title="ML Models">
          <div className="flex gap-1 mb-1">
            <span className="text-[9px] font-bold px-1.5 py-0.5 rounded bg-[#10b981]/20 text-[#10b981] border border-[#10b981]/30">XGBoost</span>
            <span className="text-[9px] font-bold px-1.5 py-0.5 rounded bg-[#10b981]/20 text-[#10b981] border border-[#10b981]/30">HMM</span>
          </div>
          <div className="flex items-center gap-1.5 mb-0.5">
            <div className="w-2 h-2 rounded-full bg-green-500" />
            <span className="text-[9px] text-green-400">Active</span>
            <div className="w-2 h-2 rounded-full bg-green-500 ml-2" />
            <span className="text-[9px] text-green-400">Active</span>
          </div>
          <MiniSelect label="Lookback" value={get("ml", "lookback", "90d")} options={["30d", "60d", "90d", "180d"]} onChange={(e) => updateField("ml", "lookback", e.target.value)} />
          <MiniSelect label="Lookback" value={get("ml", "retrainFrequency", "weekly")} options={["daily", "weekly", "monthly"]} onChange={(e) => updateField("ml", "retrainFrequency", e.target.value)} />
          <MiniField label="Retrain" value={get("ml", "retrainInterval", 7)} type="number" suffix="days" onChange={(e) => updateField("ml", "retrainInterval", Number(e.target.value))} />
          <MiniField label="Metrics" value={get("ml", "metricsInterval", 14)} type="number" suffix="days" onChange={(e) => updateField("ml", "metricsInterval", Number(e.target.value))} />
          <MiniToggle label="Momentum Tracking" checked={!!get("ml", "momentumTracking", true)} onChange={(v) => updateField("ml", "momentumTracking", v)} />
        </SectionCard>

        {/* 12. LEARNING LOG */}
        <SectionCard title="Learning Log">
          <MiniSelect label="Auto" value={get("ml", "autoMode", "auto")} options={["auto", "manual", "hybrid"]} onChange={(e) => updateField("ml", "autoMode", e.target.value)} />
          <MiniSelect label="Soft" value={get("ml", "softMode", "soft")} options={["soft", "hard", "adaptive"]} onChange={(e) => updateField("ml", "softMode", e.target.value)} />
          <MiniSelect label="Direction" value={get("ml", "direction", "both")} options={["long", "short", "both"]} onChange={(e) => updateField("ml", "direction", e.target.value)} />
          <MiniField label="Walk-Forward" value={get("ml", "walkForwardWindow", 90)} type="number" suffix="days" onChange={(e) => updateField("ml", "walkForwardWindow", Number(e.target.value))} />
          <MiniToggle label="Model Training" checked={!!get("ml", "modelTraining", true)} onChange={(v) => updateField("ml", "modelTraining", v)} />
          <MiniToggle label="Minimum Tracking" checked={!!get("ml", "minimumTracking", true)} onChange={(v) => updateField("ml", "minimumTracking", v)} />
          <MiniField label="Confidence" value={get("ml", "confidenceThreshold", 0.7)} type="number" step="0.01" onChange={(e) => updateField("ml", "confidenceThreshold", parseFloat(e.target.value))} />
        </SectionCard>

        {/* 13. OPENCLAW AGENTS */}
        <SectionCard title="OpenClaw Agents">
          <div className="space-y-0.5">
            {[
              { key: "priorityScanner", label: "Priority Scanner" },
              { key: "marketScanner", label: "Market Scanner" },
              { key: "momentumAgent", label: "Momentum Agent" },
              { key: "marketRegime", label: "Market Regime" },
              { key: "optionsScanner", label: "Options Scanner" },
              { key: "riskAgent", label: "Risk Agent" },
            ].map((agent) => (
              <div key={agent.key} className="flex items-center justify-between py-[1px]">
                <div className="flex items-center gap-1">
                  <MiniToggle
                    label=""
                    checked={!!get("agents", agent.key, true)}
                    onChange={(v) => updateField("agents", agent.key, v)}
                  />
                  <span className="text-[10px] text-gray-400">{agent.label}</span>
                </div>
                <input
                  type="range"
                  min={0}
                  max={10}
                  value={get("agents", `${agent.key}Priority`, 5)}
                  onChange={(e) => updateField("agents", `${agent.key}Priority`, Number(e.target.value))}
                  className="w-12 h-1 accent-cyan-500 cursor-pointer"
                />
              </div>
            ))}
          </div>
          <MiniSelect label="Regime" value={get("agents", "regimeMode", "adaptive")} options={["adaptive", "fixed", "ml-driven"]} onChange={(e) => updateField("agents", "regimeMode", e.target.value)} />
        </SectionCard>

        {/* 14. AGENT THRESHOLDS */}
        <SectionCard title="Agent Thresholds">
          <MiniField label="Vol Threshold" value={get("agents", "volumeThreshold", "500K+")} onChange={(e) => updateField("agents", "volumeThreshold", e.target.value)} />
          <MiniField label="Flow Threshold" value={get("agents", "flowThreshold", "100K")} onChange={(e) => updateField("agents", "flowThreshold", e.target.value)} />
          <MiniField label="Min Price" value={get("agents", "minPrice", "140")} onChange={(e) => updateField("agents", "minPrice", e.target.value)} />
          <MiniField label="Max Price" value={get("agents", "maxPrice", "155")} onChange={(e) => updateField("agents", "maxPrice", e.target.value)} />
          <MiniField label="Max Concurrent" value={get("agents", "maxConcurrentAgents", 8)} type="number" onChange={(e) => updateField("agents", "maxConcurrentAgents", Number(e.target.value))} />
          <MiniField label="Timeout" value={get("agents", "agentTimeout", 30)} type="number" suffix="sec" onChange={(e) => updateField("agents", "agentTimeout", Number(e.target.value))} />
          <MiniToggle label="Auto Restart" checked={!!get("agents", "autoRestart", true)} onChange={(v) => updateField("agents", "autoRestart", v)} />
        </SectionCard>

        {/* 15. SIGNAL THRESHOLDS */}
        <SectionCard title="Signal Thresholds">
          <MiniField label="Min Composite" value={get("ml", "minCompositeScore", 60)} type="number" suffix="pts" onChange={(e) => updateField("ml", "minCompositeScore", Number(e.target.value))} />
          <MiniField label="Buy Threshold" value={get("ml", "buyThreshold", 0.60)} type="number" step="0.01" onChange={(e) => updateField("ml", "buyThreshold", parseFloat(e.target.value))} />
          <MiniField label="Strong Buy" value={get("ml", "strongBuyThreshold", 0.75)} type="number" step="0.01" onChange={(e) => updateField("ml", "strongBuyThreshold", parseFloat(e.target.value))} />
          <MiniField label="Min Kelly Edge" value={get("ml", "minKellyEdge", 0.05)} type="number" step="0.01" onChange={(e) => updateField("ml", "minKellyEdge", parseFloat(e.target.value))} />
          <MiniField label="Signal Weight" value={get("ml", "signalWeight", 1.0)} type="number" step="0.1" onChange={(e) => updateField("ml", "signalWeight", parseFloat(e.target.value))} />
          <MiniField label="ML Weight" value={get("ml", "mlWeight", 1.0)} type="number" step="0.1" onChange={(e) => updateField("ml", "mlWeight", parseFloat(e.target.value))} />
        </SectionCard>
      </div>

      {/* ROW 4: Trade Management, Order Execution, Notifications, Security & Auth, Backup & System */}
      <div className="grid grid-cols-5 gap-2 mb-2">

        {/* 16. TRADE MANAGEMENT */}
        <SectionCard title="Trade Management">
          <MiniField label="TP1" value={get("risk", "takeProfit1", 1.5)} type="number" step="0.1" suffix="R" onChange={(e) => updateField("risk", "takeProfit1", parseFloat(e.target.value))} />
          <MiniField label="TP2" value={get("risk", "takeProfit2", 1.4)} type="number" step="0.1" suffix="R" onChange={(e) => updateField("risk", "takeProfit2", parseFloat(e.target.value))} />
          <MiniField label="TP3" value={get("risk", "takeProfit3", 2.0)} type="number" step="0.1" suffix="R" onChange={(e) => updateField("risk", "takeProfit3", parseFloat(e.target.value))} />
          <MiniField label="Trailing" value={get("risk", "trailingStop", 1.5)} type="number" step="0.1" suffix="R" onChange={(e) => updateField("risk", "trailingStop", parseFloat(e.target.value))} />
          <MiniField label="Time Exit" value={get("trading", "marketClose", "16:00")} onChange={(e) => updateField("trading", "marketClose", e.target.value)} />
          <MiniToggle label="Post-Trade Confirm" checked={!!get("trading", "confirmBeforeOrder", true)} onChange={(v) => updateField("trading", "confirmBeforeOrder", v)} />
        </SectionCard>

        {/* 17. ORDER EXECUTION */}
        <SectionCard title="Order Execution">
          <MiniField label="Slippage" value={get("trading", "slippageTolerance", 0.075)} type="number" step="0.001" suffix="%" onChange={(e) => updateField("trading", "slippageTolerance", parseFloat(e.target.value))} />
          <MiniToggle label="Trade Execution" checked={!!get("trading", "tradeExecution", true)} onChange={(v) => updateField("trading", "tradeExecution", v)} />
          <MiniToggle label="EOD Summary" checked={!!get("trading", "eodSummary", true)} onChange={(v) => updateField("trading", "eodSummary", v)} />
          <MiniField label="Partial Fill" value={get("trading", "partialFillPct", 75)} type="number" suffix="%" onChange={(e) => updateField("trading", "partialFillPct", Number(e.target.value))} />
          <MiniToggle label="Retry Failed" checked={!!get("trading", "retryFailed", true)} onChange={(v) => updateField("trading", "retryFailed", v)} />
          <MiniField label="Timeout" value={get("trading", "riskCheckMs", 50)} type="number" suffix="ms" onChange={(e) => updateField("trading", "riskCheckMs", Number(e.target.value))} />
        </SectionCard>

        {/* 18. NOTIFICATIONS */}
        <SectionCard title="Notifications">
          <div className="mb-0.5">
            <span className="text-[9px] text-gray-500 uppercase font-bold">PMS / Email / Push</span>
          </div>
          <MiniToggle label="Trade Execution" checked={!!get("notifications", "tradeAlerts", false)} onChange={(v) => updateField("notifications", "tradeAlerts", v)} />
          <MiniToggle label="EOD Summary" checked={!!get("notifications", "dailySummary", false)} onChange={(v) => updateField("notifications", "dailySummary", v)} />
          <MiniToggle label="Risk Warnings" checked={!!get("notifications", "riskAlerts", false)} onChange={(v) => updateField("notifications", "riskAlerts", v)} />
          <MiniToggle label="Signal Alerts" checked={!!get("notifications", "signalAlerts", false)} onChange={(v) => updateField("notifications", "signalAlerts", v)} />
          <MiniToggle label="System Anomalies" checked={!!get("notifications", "agentStatusAlerts", false)} onChange={(v) => updateField("notifications", "agentStatusAlerts", v)} />
          <MiniToggle label="Daily PnL" checked={!!get("notifications", "dailyPnl", false)} onChange={(v) => updateField("notifications", "dailyPnl", v)} />
        </SectionCard>

        {/* 19. SECURITY & AUTH */}
        <SectionCard title="Security & Auth">
          <MiniToggle label="2FA Enabled" checked={!!get("user", "twoFactorEnabled", false)} onChange={(v) => updateField("user", "twoFactorEnabled", v)} />
          <MiniField label="Session Timeout" value={get("user", "sessionTimeoutMinutes", 30)} type="number" suffix="min" onChange={(e) => updateField("user", "sessionTimeoutMinutes", Number(e.target.value))} />
          <MiniField label="API Key Rotation" value={get("user", "apiKeyRotationDays", 90)} type="number" suffix="days" onChange={(e) => updateField("user", "apiKeyRotationDays", Number(e.target.value))} />
          <MiniToggle label="SSL/TLS" checked={!!get("user", "sslEnabled", true)} onChange={(v) => updateField("user", "sslEnabled", v)} />
          <MiniToggle label="IP Whitelisting" checked={!!get("user", "ipWhitelisting", false)} onChange={(v) => updateField("user", "ipWhitelisting", v)} />
          <div className="text-[9px] text-gray-600 mt-0.5 pt-0.5 border-t border-gray-800/50">
            <div>AES-256 on disk</div>
            <div>Keys hashed (bcrypt)</div>
          </div>
        </SectionCard>

        {/* 20. BACKUP & SYSTEM */}
        <SectionCard title="Backup & System">
          <div className="space-y-1">
            <div className="text-[9px] text-gray-500 font-mono">
              system.json (primary)
            </div>
            <MiniToggle label="Auto-Save" checked={!!get("system", "autoSave", true)} onChange={(v) => updateField("system", "autoSave", v)} />
            <div className="text-[9px] text-gray-500 font-mono">
              {new Date().toISOString().replace("T", " ").slice(0, 19)} (latest)
            </div>
            <div className="text-[9px] text-gray-600">
              <div>AES-256 on disk</div>
              <div>Auto-backup: daily</div>
            </div>
          </div>
        </SectionCard>
      </div>

      {/* ROW 5: Appearance, Market Data, Notification Channels, Logging & Audit, Strategy Config */}
      <div className="grid grid-cols-5 gap-2 mb-2">

        {/* 21. APPEARANCE */}
        <SectionCard title="Appearance">
          {/* Theme thumbnails */}
          <div className="mb-1.5">
            <div className="grid grid-cols-3 gap-3 mb-1">
              {[
                { name: 'Midnight Bloomberg', bg: '#0B0E14', surface: '#111827', accent: '#00D9FF' },
                { name: 'Classic Dark', bg: '#1a1a2e', surface: '#16213e', accent: '#0f3460' },
                { name: 'OLED Black', bg: '#000000', surface: '#0a0a0a', accent: '#00D9FF' },
              ].map(theme => (
                <button key={theme.name} className="flex flex-col items-center gap-1.5 p-2 border border-gray-700 rounded-md hover:border-[#00D9FF]/50 group">
                  <div className="w-full h-12 rounded-sm flex gap-0.5" style={{ background: theme.bg }}>
                    <div className="w-1/4 h-full rounded-sm" style={{ background: theme.surface }} />
                    <div className="flex-1 h-full rounded-sm" style={{ background: theme.surface }}>
                      <div className="w-3/4 h-1 mt-2 mx-auto rounded" style={{ background: theme.accent }} />
                    </div>
                  </div>
                  <span className="text-[9px] text-gray-500 group-hover:text-[#00D9FF]">{theme.name}</span>
                </button>
              ))}
            </div>
            {/* Color swatches */}
            <div className="flex gap-1 mb-1">
              {[
                { key: "midnight", color: "#1a1a2e", label: "Midnight Illuminator" },
                { key: "ocean", color: "#0a2e4a", label: "Ocean Dark" },
                { key: "emerald", color: "#0a2e1a", label: "Emerald" },
                { key: "crimson", color: "#2e0a0a", label: "Crimson" },
                { key: "amber", color: "#2e1a0a", label: "Amber" },
              ].map((t) => (
                <button
                  key={t.key}
                  onClick={() => updateField("appearance", "theme", t.key)}
                  title={t.label}
                  className={`w-5 h-5 rounded border-2 transition-all ${
                    get("appearance", "theme", "midnight") === t.key
                      ? "border-[#00D9FF] ring-1 ring-cyan-400/50"
                      : "border-gray-700 hover:border-gray-500"
                  }`}
                  style={{ background: t.color }}
                />
              ))}
            </div>
            <span className="text-[9px] text-gray-500">
              {get("appearance", "theme", "midnight") === "midnight" ? "Midnight Illuminator" :
               get("appearance", "theme") === "ocean" ? "Ocean Dark" :
               get("appearance", "theme") === "emerald" ? "Emerald" :
               get("appearance", "theme") === "crimson" ? "Crimson" :
               get("appearance", "theme") === "amber" ? "Amber" : "Midnight Illuminator"}
            </span>
          </div>
          <MiniSelect label="Dark/Ultra" value={get("appearance", "darkMode", "dark")} options={[
            { value: "dark", label: "Dark" },
            { value: "ultra_dark", label: "Ultra Dark" },
          ]} onChange={(e) => updateField("appearance", "darkMode", e.target.value)} />
          <MiniSelect label="Density" value={get("appearance", "density", "ultra_dense")} options={[
            { value: "ultra_dense", label: "Ultra Dense" },
            { value: "compact", label: "Compact" },
            { value: "comfortable", label: "Comfortable" },
          ]} onChange={(e) => updateField("appearance", "density", e.target.value)} />
          <MiniSelect label="Font" value={get("appearance", "font", "monospace")} options={["monospace", "sans-serif", "serif"]} onChange={(e) => updateField("appearance", "font", e.target.value)} />
          <MiniToggle label="Animations" checked={!!get("appearance", "animations", true)} onChange={(v) => updateField("appearance", "animations", v)} />
        </SectionCard>

        {/* 22. MARKET DATA */}
        <SectionCard title="Market Data">
          <MiniSelect label="Timeframe" value={get("appearance", "chartTimeframe", "5m")} options={["1m", "5m", "15m", "1h", "4h", "1d"]} onChange={(e) => updateField("appearance", "chartTimeframe", e.target.value)} />
          <MiniSelect label="Update" value={get("dataSources", "updateFrequency", "5s")} options={["1s", "5s", "15s", "30s", "60s"]} onChange={(e) => updateField("dataSources", "updateFrequency", e.target.value)} />
          <MiniField label="SSD Rate" value={get("dataSources", "ssdRate", "fast")} onChange={(e) => updateField("dataSources", "ssdRate", e.target.value)} />
          <MiniToggle label="After-hours" checked={!!get("trading", "afterHoursEnabled", false)} onChange={(v) => updateField("trading", "afterHoursEnabled", v)} />
          <MiniField label="Volume" value={get("scanning", "volumeMin", "YTD, 1M, All")} onChange={(e) => updateField("scanning", "volumeMin", e.target.value)} />
          <MiniField label="Gap filter" value={get("scanning", "gapFilter", 2)} type="number" suffix="%" onChange={(e) => updateField("scanning", "gapFilter", Number(e.target.value))} />
          <MiniSelect label="Export" value={get("dataSources", "exportFormat", "json")} options={["json", "csv"]} onChange={(e) => updateField("dataSources", "exportFormat", e.target.value)} />
        </SectionCard>

        {/* 23. NOTIFICATION CHANNELS */}
        <SectionCard title="Notification Channels">
          <div className="space-y-0.5">
            {[
              { label: "Track PnL", key: "trackPnl" },
              { label: "Metrics", key: "metrics" },
              { label: "Sharpe, Sortino", key: "sharpeSortino" },
              { label: "Max DD", key: "maxDrawdown" },
            ].map((item) => (
              <MiniToggle
                key={item.key}
                label={item.label}
                checked={!!get("notifications", item.key, false)}
                onChange={(v) => updateField("notifications", item.key, v)}
              />
            ))}
            <div className="flex items-center justify-between py-0.5">
              <span className="text-[10px] text-gray-400">Discord</span>
              <ConnBadge status={get("notifications", "discordWebhookUrl") ? "connected" : "not_set"} label={get("notifications", "discordWebhookUrl") ? "Active" : "Setup"} />
            </div>
            <div className="flex items-center justify-between py-0.5">
              <span className="text-[10px] text-gray-400">Slack</span>
              <ConnBadge status={get("notifications", "slackWebhookUrl") ? "connected" : "not_set"} label={get("notifications", "slackWebhookUrl") ? "Active" : "Setup"} />
            </div>
            <div className="flex items-center justify-between py-0.5">
              <span className="text-[10px] text-gray-400">Telegram</span>
              <ConnBadge status={get("notifications", "telegramBotToken") ? "connected" : "not_set"} label={get("notifications", "telegramBotToken") ? "Active" : "Setup"} />
            </div>
          </div>
        </SectionCard>

        {/* 24. LOGGING & AUDIT */}
        <SectionCard title="Logging & Audit">
          <MiniSelect label="Log Level" value={get("system", "logLevel", "INFO")} options={["DEBUG", "INFO", "WARNING", "ERROR"]} onChange={(e) => updateField("system", "logLevel", e.target.value)} />
          <MiniField label="Log Retention" value={get("system", "logRetentionDays", 30)} type="number" suffix="days" onChange={(e) => updateField("system", "logRetentionDays", Number(e.target.value))} />
          <MiniField label="Audit Retention" value={get("system", "auditRetentionDays", 90)} type="number" suffix="days" onChange={(e) => updateField("system", "auditRetentionDays", Number(e.target.value))} />
          <MiniToggle label="Trade Audit Log" checked={!!get("system", "tradeAuditLog", true)} onChange={(v) => updateField("system", "tradeAuditLog", v)} />
          <MiniToggle label="Performance Metrics" checked={!!get("system", "perfMetricsLog", true)} onChange={(v) => updateField("system", "perfMetricsLog", v)} />
          <MiniToggle label="Agent Decision Log" checked={!!get("system", "agentDecisionLog", true)} onChange={(v) => updateField("system", "agentDecisionLog", v)} />
          <button
            onClick={() => setShowFullLog(!showFullLog)}
            className="mt-1 w-full text-[9px] bg-cyan-500/10 border border-[#00D9FF]/50/20 rounded px-2 py-1 text-[#00D9FF] hover:bg-cyan-500/20 flex items-center gap-1 justify-center"
          >
            <FileText className="w-2.5 h-2.5" /> {showFullLog ? "Hide" : "View"} Full Log
          </button>
        </SectionCard>

        {/* 25. STRATEGY CONFIG */}
        <SectionCard title="Strategy Config">
          <MiniSelect label="Order Type" value={get("trading", "orderType", "market")} options={["market", "limit", "stop", "stop_limit"]} onChange={(e) => updateField("trading", "orderType", e.target.value)} />
          <MiniSelect label="Entry Method" value={get("trading", "entryMethod", "signal")} options={[
            { value: "signal", label: "Signal-driven" },
            { value: "manual", label: "Manual Only" },
            { value: "hybrid", label: "Hybrid" },
          ]} onChange={(e) => updateField("trading", "entryMethod", e.target.value)} />
          <MiniToggle label="Auto Execute" checked={!!get("trading", "autoExecute", false)} onChange={(v) => updateField("trading", "autoExecute", v)} />
          <MiniToggle label="Paper Trade First" checked={!!get("trading", "paperTradeFirst", true)} onChange={(v) => updateField("trading", "paperTradeFirst", v)} />
          <MiniField label="Min Sharpe" value={get("trading", "minSharpe", 1.2)} type="number" step="0.1" onChange={(e) => updateField("trading", "minSharpe", parseFloat(e.target.value))} />
          <MiniField label="Min Win Rate" value={get("trading", "minWinRate", 52)} type="number" suffix="%" onChange={(e) => updateField("trading", "minWinRate", Number(e.target.value))} />
        </SectionCard>
      </div>

      {/* FOOTER BAR */}
      <div className="flex items-center justify-between mt-2 pt-2 border-t border-gray-800/50">
        <div className="flex gap-2">
          <button
            onClick={onExport}
            className="text-[10px] text-gray-500 hover:text-[#00D9FF] flex items-center gap-1 px-3 py-1 border border-gray-800/50 rounded"
          >
            Export Settings
          </button>
          <button
            onClick={() => importRef.current?.click()}
            className="text-[10px] text-gray-500 hover:text-[#00D9FF] flex items-center gap-1 px-3 py-1 border border-gray-800/50 rounded"
          >
            Import Settings
          </button>
          <button
            onClick={() => { onReset("trading"); onReset("risk"); onReset("ml"); onReset("agents"); }}
            className="text-[10px] text-gray-500 hover:text-red-400 flex items-center gap-1 px-3 py-1 border border-gray-800/50 rounded"
          >
            Reset Defaults
          </button>
        </div>
        <button
          onClick={saveAllSettings}
          disabled={saving}
          className="bg-cyan-500 hover:bg-cyan-600 text-black font-bold text-[10px] px-5 py-1.5 rounded uppercase tracking-wider disabled:opacity-50 flex items-center gap-1.5"
        >
          <Save className="w-3 h-3" />
          {saving ? "Saving..." : "SAVE ALL CHANGES"}
        </button>
      </div>

      {/* FULL AUDIT LOG (expanded) */}
      {showFullLog && (
        <div className="mt-3">
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
