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

// ── Toast config ──────────────────────────────────────────────
const TOAST_CFG = { position: "bottom-right", theme: "dark" };

// ── Tiny reusable components ──────────────────────────────────

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
        <span className="text-[10px] font-bold text-white uppercase tracking-wider">{title}</span>
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
          className={`w-20 bg-[#0a0d13] border border-gray-700/50 rounded px-1.5 py-0.5 text-[10px] text-white outline-none focus:border-cyan-500/50 ${className}`}
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
        className="bg-[#0a0d13] border border-gray-700/50 rounded px-1 py-0.5 text-[10px] text-white outline-none focus:border-cyan-500/50 appearance-none cursor-pointer pr-4"
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
          checked ? "bg-cyan-500/30 border-cyan-500/50" : "bg-gray-700/30 border-gray-600/50"
        }`}
      >
        <span
          className={`block w-2.5 h-2.5 rounded-full transition-transform ${
            checked ? "translate-x-3.5 bg-cyan-400" : "translate-x-0.5 bg-gray-500"
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
            ? "bg-cyan-500/30 border-cyan-500/50 text-cyan-400"
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
          ? "bg-cyan-500/15 text-cyan-400 border border-cyan-500/30"
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
        <span className="text-[9px] text-cyan-400 w-4 text-right">{value}</span>
      </div>
    </div>
  );
}

// ── Main Settings Page ────────────────────────────────────────
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
        <button onClick={refetch} className="text-xs text-cyan-400 hover:text-cyan-300 flex items-center gap-1">
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

      {/* ═══════ HEADER ═══════ */}
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <Settings className="w-4 h-4 text-cyan-400" />
          <h1 className="text-sm font-bold text-white uppercase tracking-wider">System Configuration</h1>
        </div>
        <button
          onClick={saveAllSettings}
          disabled={saving}
          className="bg-cyan-500 hover:bg-cyan-600 text-black font-bold text-[10px] px-4 py-1.5 rounded uppercase tracking-wider disabled:opacity-50"
        >
          {saving ? "Saving..." : "SAVE ALL"}
        </button>
      </div>

      {/* ═══════ ROW 1: Identity, Trading Mode, Position & Limits, Circuit Breakers ═══════ */}
      <div className="grid grid-cols-4 gap-2 mb-2">

        {/* IDENTITY & LOCALE */}
        <SectionCard title="Identity & Locale">
          <MiniField label="Display Name" value={get("user", "displayName", "Espen Schafferr")} onChange={(e) => updateField("user", "displayName", e.target.value)} />
          <MiniSelect label="Timezone" value={get("user", "timezone", "America/Chicago")} options={[
            { value: "America/Chicago", label: "CT" },
            { value: "America/New_York", label: "ET" },
            { value: "America/Los_Angeles", label: "PT" },
            { value: "UTC", label: "UTC" },
            { value: "Europe/Oslo", label: "CET" },
          ]} onChange={(e) => updateField("user", "timezone", e.target.value)} />
          <MiniField label="Email" value={get("user", "email", "")} onChange={(e) => updateField("user", "email", e.target.value)} className="w-28" />
          <MiniSelect label="Currency" value={get("user", "currency", "USD")} options={["USD", "EUR", "GBP", "NOK", "CHF"]} onChange={(e) => updateField("user", "currency", e.target.value)} />
          <div className="flex items-center justify-between py-[1px]">
            <span className="text-[10px] text-gray-400">Avatar</span>
            <button className="text-[9px] bg-[#0a0d13] border border-gray-700/50 rounded px-2 py-0.5 text-gray-400 hover:text-cyan-400 transition-colors">
              Choose File
            </button>
          </div>
          <MiniCheckbox label="Show Fill" checked={!!get("appearance", "showFill", true)} onChange={(v) => updateField("appearance", "showFill", v)} />
        </SectionCard>

        {/* TRADING MODE */}
        <SectionCard title="Trading Mode">
          <div className="flex gap-1 mb-1">
            {["PAPER", "LIVE"].map((env) => (
              <button
                key={env}
                onClick={() => updateField("dataSources", "alpacaBaseUrl", env.toLowerCase())}
                className={`flex-1 px-2 py-1 rounded text-[10px] font-bold uppercase tracking-wider border transition-all ${
                  get("dataSources", "alpacaBaseUrl", "paper") === env.toLowerCase()
                    ? "bg-[rgba(0,217,255,0.15)] border-[rgba(0,217,255,0.3)] text-[#00D9FF]"
                    : "bg-[#0B0E14] border-gray-700 text-gray-500 hover:border-gray-600"
                }`}
              >
                {env}
              </button>
            ))}
          </div>
          <div className="flex items-center gap-1.5 mb-1">
            <div className={`w-2 h-2 rounded-full ${get("dataSources", "alpacaBaseUrl") === "live" ? "bg-red-500 animate-pulse" : "bg-green-500"}`} />
            <span className="text-[9px] text-yellow-400">
              {get("dataSources", "alpacaBaseUrl") === "live" ? "Live mode + real money" : "Live mode + real money"}
            </span>
          </div>
          <MiniSelect label="Account" value={get("trading", "accountType", "paper_trading")} options={[
            { value: "paper_trading", label: "Paper Trading" },
            { value: "live", label: "Live Trading" },
          ]} onChange={(e) => updateField("trading", "accountType", e.target.value)} />
          <MiniField label="Portfolio Size" value={get("trading", "portfolioSize", "")} onChange={(e) => updateField("trading", "portfolioSize", e.target.value)} />
          <div className="mt-1 pt-1 border-t border-gray-800/50 space-y-0.5">
            <div className="flex items-center justify-between py-[1px]">
              <span className="text-[9px] text-gray-500">Broker</span>
              <span className="text-[9px] text-white font-mono">Alpaca Markets</span>
            </div>
            <div className="flex items-center justify-between py-[1px]">
              <span className="text-[9px] text-gray-500">Status</span>
              <span className="text-[9px] text-green-400 font-mono">Connected</span>
            </div>
            <div className="flex items-center justify-between py-[1px]">
              <span className="text-[9px] text-gray-500">Sync</span>
              <span className="text-[9px] text-gray-400 font-mono">2026-03-01 06:50</span>
            </div>
          </div>
        </SectionCard>

        {/* POSITION & LIMITS */}
        <SectionCard title="Position & Limits">
          <MiniField label="Base Size" value={get("trading", "maxPositionSize", 5000)} type="number" suffix="$" onChange={(e) => updateField("trading", "maxPositionSize", Number(e.target.value))} />
          <MiniField label="Max Daily Risk" value={get("risk", "maxDailyRiskPct", 2.5)} type="number" step="0.1" suffix="%" onChange={(e) => updateField("risk", "maxDailyRiskPct", parseFloat(e.target.value))} />
          <MiniField label="Max Open Positions" value={get("risk", "maxPositions", 10)} type="number" onChange={(e) => updateField("risk", "maxPositions", Number(e.target.value))} />
          <MiniField label="Max Sector" value={get("risk", "maxSectorExposure", 30)} type="number" suffix="%" onChange={(e) => updateField("risk", "maxSectorExposure", Number(e.target.value))} />
          <MiniToggle label="Auto-Scale" checked={!!get("trading", "autoScale", true)} onChange={(v) => updateField("trading", "autoScale", v)} />
          <MiniField label="Correlation" value={get("risk", "correlationLimit", 0.71)} type="number" step="0.01" onChange={(e) => updateField("risk", "correlationLimit", parseFloat(e.target.value))} />
        </SectionCard>

        {/* CIRCUIT BREAKERS */}
        <SectionCard title="Circuit Breakers">
          <MiniField label="Daily Loss Limit" value={get("risk", "dailyLossLimit", 2500)} type="number" suffix="$" onChange={(e) => updateField("risk", "dailyLossLimit", Number(e.target.value))} />
          <MiniField label="Market Killswitch" value={get("risk", "marketKillswitch", 2500)} type="number" suffix="$" onChange={(e) => updateField("risk", "marketKillswitch", Number(e.target.value))} />
          <MiniField label="Flash Crash" value={get("risk", "flashCrashLimit", 1000)} type="number" suffix="$" onChange={(e) => updateField("risk", "flashCrashLimit", Number(e.target.value))} />
          <MiniField label="Consecutive Loss" value={get("risk", "consecutiveLossLimit", 5)} type="number" onChange={(e) => updateField("risk", "consecutiveLossLimit", Number(e.target.value))} />
        </SectionCard>
      </div>

      {/* ═══════ ROW 2: Brokerage, Data Feed, Data Source Priority, Ollama, Ollama Models ═══════ */}
      <div className="grid grid-cols-5 gap-2 mb-2">

        {/* BROKERAGE CONNECTIONS */}
        <SectionCard title="Brokerage Connections">
          <div className="flex items-center justify-between py-0.5">
            <span className="text-[10px] text-gray-400">Alpaca Markets</span>
            <div className="flex items-center gap-1">
              <ConnBadge status="connected" label="Connected" />
              <span className="text-[8px] text-gray-600">[Test][Edit]</span>
            </div>
          </div>
          <div className="flex items-center justify-between py-0.5">
            <span className="text-[10px] text-gray-400">Interactive Brokers</span>
            <ConnBadge status="not_configured" label="Not Configured" />
          </div>
          <div className="mt-1.5 pt-1 border-t border-gray-800/50">
            <button className="text-[9px] text-cyan-400 hover:text-cyan-300 flex items-center gap-1">
              + Add Broker
            </button>
          </div>
        </SectionCard>

        {/* DATA FEED API KEYS */}
        <SectionCard title="Data Feed API Keys">
          <div className="flex items-center justify-between py-0.5">
            <span className="text-[10px] text-gray-400">Unusual Whales</span>
            <div className="flex items-center gap-1">
              <ConnBadge status="connected" label="Connected" />
              <span className="text-[8px] text-gray-600">[Test][Edit]</span>
            </div>
          </div>
          <div className="flex items-center justify-between py-0.5">
            <span className="text-[10px] text-gray-400">Polygon.io</span>
            <div className="flex items-center gap-1">
              <ConnBadge status="aggregated" label="Aggregated" />
            </div>
          </div>
          <div className="flex items-center justify-between py-0.5">
            <span className="text-[10px] text-gray-400">FRED</span>
            <span className="text-[9px] text-gray-500">Not set</span>
          </div>
          <div className="flex items-center justify-between py-0.5">
            <span className="text-[10px] text-gray-400">SEC EDGAR</span>
            <span className="text-[9px] text-gray-500">N/A</span>
          </div>
        </SectionCard>

        {/* DATA SOURCE PRIORITY */}
        <SectionCard title="Data Source Priority">
          <MiniSelect label="Polygon v3 (SPX)" value={get("dataSources", "endpointPriority", "polygon")} options={["polygon", "alpaca", "benzinga"]} onChange={(e) => updateField("dataSources", "endpointPriority", e.target.value)} />
          <MiniSelect label="Options Flow" value={get("dataSources", "optionsFlowPriority", "unusual_whales")} options={[
            { value: "unusual_whales", label: "Unusual Whales" },
            { value: "polygon", label: "Polygon" },
          ]} onChange={(e) => updateField("dataSources", "optionsFlowPriority", e.target.value)} />
          <MiniSelect label="SEC EDGAR" value={get("dataSources", "secEdgarPriority", "sec_edgar")} options={["sec_edgar", "polygon"]} onChange={(e) => updateField("dataSources", "secEdgarPriority", e.target.value)} />
          <MiniSelect label="Rate Limit" value={get("dataSources", "rateLimitMode", "conservative")} options={["conservative", "moderate", "aggressive"]} onChange={(e) => updateField("dataSources", "rateLimitMode", e.target.value)} />
        </SectionCard>

        {/* OLLAMA LOCAL LLM */}
        <SectionCard title="Ollama Local LLM">
          <MiniField label="Endpoint" value={get("ollama", "ollamaHostUrl", "http://localhost:11434")} onChange={(e) => updateField("ollama", "ollamaHostUrl", e.target.value)} className="w-28" />
          <MiniField label="Model" value={get("ollama", "ollamaDefaultModel", "llama3")} onChange={(e) => updateField("ollama", "ollamaDefaultModel", e.target.value)} />
          <MiniField label="GPT-4o" value={get("ollama", "gpt4oStatus", "disabled")} onChange={(e) => updateField("ollama", "gpt4oStatus", e.target.value)} />
          <MiniField label="Context" value={get("ollama", "ollamaContextLength", 8192)} type="number" suffix="tok" onChange={(e) => updateField("ollama", "ollamaContextLength", Number(e.target.value))} />
          <MiniToggle label="CUDA" checked={!!get("ollama", "ollamaCudaEnabled", false)} onChange={(v) => updateField("ollama", "ollamaCudaEnabled", v)} />
          <div className="flex items-center justify-between pt-0.5">
            <button onClick={() => onTestConn("ollama")} className="text-[9px] text-purple-400 hover:text-purple-300 flex items-center gap-1">
              <Wifi className="w-2.5 h-2.5" /> {ollamaCr.testing ? "Testing..." : "Test"}
            </button>
            <StatusDot ok={ollamaCr.valid} testing={ollamaCr.testing} />
          </div>
        </SectionCard>

        {/* OLLAMA MODELS */}
        <SectionCard title="Ollama Models">
          <MiniField label="GPT-4o" value={get("ollama", "gpt4Status", "disabled")} onChange={(e) => updateField("ollama", "gpt4Status", e.target.value)} />
          <MiniField label="Use for" value={get("ollama", "signalAnalysisModel", "Signal Analysis")} onChange={(e) => updateField("ollama", "signalAnalysisModel", e.target.value)} />
          <MiniField label="Use for" value={get("ollama", "patternAnalysisModel", "Pattern Analysis")} onChange={(e) => updateField("ollama", "patternAnalysisModel", e.target.value)} />
          <MiniField label="Use for" value={get("ollama", "signalGenerationModel", "Signal Generation")} onChange={(e) => updateField("ollama", "signalGenerationModel", e.target.value)} />
          <MiniField label="Fallback" value={get("ollama", "fallbackModel", "llama3")} onChange={(e) => updateField("ollama", "fallbackModel", e.target.value)} />
        </SectionCard>
      </div>

      {/* ═══════ ROW 3: ML Models, Learning Loop, Pipeline Guard Agents, Agent Thresholds ═══════ */}
      <div className="grid grid-cols-4 gap-2 mb-2">

        {/* ML MODELS */}
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
          <MiniField label="Walk-Forward" value={get("ml", "walkForwardWindow", 90)} type="number" suffix="days" onChange={(e) => updateField("ml", "walkForwardWindow", Number(e.target.value))} />
          <MiniToggle label="Momentum Tracking" checked={!!get("ml", "momentumTracking", true)} onChange={(v) => updateField("ml", "momentumTracking", v)} />
        </SectionCard>

        {/* LEARNING LOOP */}
        <SectionCard title="Learning Loop">
          <MiniToggle label="Auto-Retrain" checked={!!get("ml", "autoRetrain", true)} onChange={(v) => updateField("ml", "autoRetrain", v)} />
          <MiniToggle label="Drift Detection" checked={!!get("ml", "driftDetection", true)} onChange={(v) => updateField("ml", "driftDetection", v)} />
          <MiniSelect label="Schedule" value={get("ml", "retrainSchedule", "weekly")} options={["daily", "weekly", "monthly", "on-drift"]} onChange={(e) => updateField("ml", "retrainSchedule", e.target.value)} />
          <MiniToggle label="Walk-Forward" checked={!!get("ml", "walkForwardEnabled", true)} onChange={(v) => updateField("ml", "walkForwardEnabled", v)} />
          <MiniSelect label="Validation" value={get("ml", "validationMethod", "time_series")} options={[
            { value: "time_series", label: "Time Series CV" },
            { value: "expanding", label: "Expanding Window" },
            { value: "kfold", label: "K-Fold" },
          ]} onChange={(e) => updateField("ml", "validationMethod", e.target.value)} />
          <MiniField label="Min Samples" value={get("ml", "minSamples", 500)} type="number" onChange={(e) => updateField("ml", "minSamples", Number(e.target.value))} />
          <MiniToggle label="Feature Tracking" checked={!!get("ml", "featureTracking", true)} onChange={(v) => updateField("ml", "featureTracking", v)} />
        </SectionCard>

        {/* OPENCLAW AGENTS */}
        <SectionCard title="OpenClaw Agents">
          <div className="space-y-0.5 mb-1.5">
            <MiniToggle label="Swarm Mode" checked={!!get("agents", "swarmMode", true)} onChange={(v) => updateField("agents", "swarmMode", v)} />
            <MiniToggle label="Voting" checked={!!get("agents", "votingEnabled", true)} onChange={(v) => updateField("agents", "votingEnabled", v)} />
            <MiniToggle label="Closure" checked={!!get("agents", "closureEnabled", true)} onChange={(v) => updateField("agents", "closureEnabled", v)} />
            <MiniToggle label="Blackboard" checked={!!get("agents", "blackboardEnabled", true)} onChange={(v) => updateField("agents", "blackboardEnabled", v)} />
          </div>
          <div className="pt-1 border-t border-gray-800/50 space-y-0.5">
            <MiniCheckbox label="Market Scanner" checked={!!get("agents", "marketScanner", true)} onChange={(v) => updateField("agents", "marketScanner", v)} />
            <MiniCheckbox label="Risk Assessment" checked={!!get("agents", "riskAssessment", true)} onChange={(v) => updateField("agents", "riskAssessment", v)} />
            <MiniCheckbox label="Sentiment" checked={!!get("agents", "sentimentAgent", true)} onChange={(v) => updateField("agents", "sentimentAgent", v)} />
            <MiniCheckbox label="YouTube" checked={!!get("agents", "youtubeAgent", false)} onChange={(v) => updateField("agents", "youtubeAgent", v)} />
          </div>
        </SectionCard>

        {/* AGENT THRESHOLDS */}
        <SectionCard title="Agent Thresholds">
          <MiniField label="Vol Threshold" value={get("agents", "volumeThreshold", "500K")} onChange={(e) => updateField("agents", "volumeThreshold", e.target.value)} />
          <MiniField label="Flow Threshold" value={get("agents", "flowThreshold", "100K")} onChange={(e) => updateField("agents", "flowThreshold", e.target.value)} />
          <MiniField label="Min Price" value={get("agents", "minPrice", "1K")} onChange={(e) => updateField("agents", "minPrice", e.target.value)} />
          <MiniField label="Max Concurrent" value={get("agents", "maxConcurrentAgents", 8)} type="number" onChange={(e) => updateField("agents", "maxConcurrentAgents", Number(e.target.value))} />
          <MiniField label="Timeout" value={get("agents", "agentTimeout", 30)} type="number" suffix="sec" onChange={(e) => updateField("agents", "agentTimeout", Number(e.target.value))} />
          <MiniToggle label="Auto Restart" checked={!!get("agents", "autoRestart", true)} onChange={(v) => updateField("agents", "autoRestart", v)} />
        </SectionCard>
      </div>

      {/* ═══════ ROW 4: Trade Management, Order Execution, Notifications, Security & Safety ═══════ */}
      <div className="grid grid-cols-4 gap-2 mb-2">

        {/* TRADE MANAGEMENT */}
        <SectionCard title="Trade Management">
          <MiniField label="TP1" value={get("risk", "takeProfit1", 1.0)} type="number" step="0.1" suffix="R" onChange={(e) => updateField("risk", "takeProfit1", parseFloat(e.target.value))} />
          <MiniField label="TP2" value={get("risk", "takeProfit2", 1.5)} type="number" step="0.1" suffix="R" onChange={(e) => updateField("risk", "takeProfit2", parseFloat(e.target.value))} />
          <MiniField label="TP3" value={get("risk", "takeProfit3", 2.0)} type="number" step="0.1" suffix="R" onChange={(e) => updateField("risk", "takeProfit3", parseFloat(e.target.value))} />
          <MiniField label="Trailing" value={get("risk", "trailingStop", 1.5)} type="number" step="0.1" suffix="R" onChange={(e) => updateField("risk", "trailingStop", parseFloat(e.target.value))} />
          <MiniField label="Time Exit" value={get("trading", "marketClose", "16:00")} onChange={(e) => updateField("trading", "marketClose", e.target.value)} />
          <MiniToggle label="Post-Trade Confirm" checked={!!get("trading", "confirmBeforeOrder", true)} onChange={(v) => updateField("trading", "confirmBeforeOrder", v)} />
        </SectionCard>

        {/* ORDER EXECUTION */}
        <SectionCard title="Order Execution">
          <MiniField label="Slippage" value={get("trading", "slippageTolerance", 0.075)} type="number" step="0.001" suffix="%" onChange={(e) => updateField("trading", "slippageTolerance", parseFloat(e.target.value))} />
          <MiniField label="Partial Fill" value={get("trading", "partialFillPct", 75)} type="number" suffix="%" onChange={(e) => updateField("trading", "partialFillPct", Number(e.target.value))} />
          <MiniToggle label="Retry Failed" checked={!!get("trading", "retryFailed", true)} onChange={(v) => updateField("trading", "retryFailed", v)} />
          <MiniField label="Max Retries" value={get("trading", "maxRetries", 3)} type="number" onChange={(e) => updateField("trading", "maxRetries", Number(e.target.value))} />
          <MiniSelect label="Routing" value={get("trading", "orderRouting", "smart")} options={["smart", "direct", "iex"]} onChange={(e) => updateField("trading", "orderRouting", e.target.value)} />
          <MiniField label="Risk Check" value={get("trading", "riskCheckMs", 50)} type="number" suffix="ms" onChange={(e) => updateField("trading", "riskCheckMs", Number(e.target.value))} />
        </SectionCard>

        {/* NOTIFICATIONS */}
        <SectionCard title="Notifications">
          <div className="mb-1">
            <span className="text-[9px] text-gray-500 uppercase font-bold">Channels</span>
            <div className="flex gap-2 mt-0.5">
              <MiniCheckbox label="Discord" checked={!!get("notifications", "discordEnabled", true)} onChange={(v) => updateField("notifications", "discordEnabled", v)} />
              <MiniCheckbox label="SMS" checked={!!get("notifications", "smsEnabled", true)} onChange={(v) => updateField("notifications", "smsEnabled", v)} />
              <MiniCheckbox label="Email" checked={!!get("notifications", "emailEnabled", true)} onChange={(v) => updateField("notifications", "emailEnabled", v)} />
              <MiniCheckbox label="Slack" checked={!!get("notifications", "slackEnabled", false)} onChange={(v) => updateField("notifications", "slackEnabled", v)} />
            </div>
          </div>
          <div className="pt-0.5 border-t border-gray-800/50">
            <span className="text-[9px] text-gray-500 uppercase font-bold mb-0.5 block">PMS / Email / Push</span>
          </div>
          <MiniToggle label="Trade Execution" checked={!!get("notifications", "tradeAlerts", false)} onChange={(v) => updateField("notifications", "tradeAlerts", v)} />
          <MiniToggle label="EOD Summary" checked={!!get("notifications", "dailySummary", false)} onChange={(v) => updateField("notifications", "dailySummary", v)} />
          <MiniToggle label="Risk Warnings" checked={!!get("notifications", "riskAlerts", false)} onChange={(v) => updateField("notifications", "riskAlerts", v)} />
          <MiniToggle label="Signal Alerts" checked={!!get("notifications", "signalAlerts", false)} onChange={(v) => updateField("notifications", "signalAlerts", v)} />
          <MiniToggle label="System Anomalies" checked={!!get("notifications", "agentStatusAlerts", false)} onChange={(v) => updateField("notifications", "agentStatusAlerts", v)} />
          <MiniToggle label="Daily PnL" checked={!!get("notifications", "dailyPnl", false)} onChange={(v) => updateField("notifications", "dailyPnl", v)} />
        </SectionCard>

        {/* SECURITY & AUTH */}
        <SectionCard title="Security & Auth">
          <MiniToggle label="2FA Enabled" checked={!!get("user", "twoFactorEnabled", false)} onChange={(v) => updateField("user", "twoFactorEnabled", v)} />
          <MiniToggle label="SSL/TLS" checked={!!get("user", "sslEnabled", true)} onChange={(v) => updateField("user", "sslEnabled", v)} />
          <MiniToggle label="IP Whitelisting" checked={!!get("user", "ipWhitelisting", false)} onChange={(v) => updateField("user", "ipWhitelisting", v)} />
          <div className="mt-1 pt-1 border-t border-gray-800/50 space-y-0.5">
            <MiniField label="New Password" value="" type="password" onChange={() => {}} className="w-24" />
            <MiniField label="Confirm" value="" type="password" onChange={() => {}} className="w-24" />
          </div>
          <div className="mt-1 pt-1 border-t border-gray-800/50 text-[9px] text-gray-600 space-y-0.5">
            <div>Encryption: <span className="text-gray-400">AES-256</span></div>
            <div>Session: <span className="text-gray-400">{get("user", "sessionTimeoutMinutes", 24)}h timeout</span></div>
            <div>Last Login: <span className="text-gray-400">{new Date().toISOString().slice(0, 10)}</span></div>
          </div>
          <button className="mt-1 w-full text-[9px] bg-red-900/20 border border-red-800/30 rounded px-2 py-0.5 text-red-400 hover:bg-red-900/30">
            Revoke All Sessions
          </button>
        </SectionCard>
      </div>

      {/* ═══════ ROW 5: Appearance, Market Data, Backup & System ═══════ */}
      <div className="grid grid-cols-4 gap-2 mb-2">

        {/* APPEARANCE */}
        <SectionCard title="Appearance">
          {/* Theme preview thumbnails */}
          <div className="mb-1.5">
            <div className="flex gap-1.5 mb-1">
              {[
                { key: "midnight_bloomberg", gradient: "linear-gradient(135deg, #0a0a1a 0%, #1a1a2e 50%, #0d1117 100%)", label: "Midnight Bloomberg" },
                { key: "classic_dark", gradient: "linear-gradient(135deg, #111827 0%, #1f2937 50%, #0f172a 100%)", label: "Classic Dark" },
                { key: "oled_black", gradient: "linear-gradient(135deg, #000000 0%, #0a0a0a 50%, #050505 100%)", label: "OLED Black" },
              ].map((t) => (
                <button
                  key={t.key}
                  onClick={() => updateField("appearance", "theme", t.key)}
                  className={`relative flex-1 h-10 rounded border-2 transition-all overflow-hidden ${
                    get("appearance", "theme", "midnight_bloomberg") === t.key
                      ? "border-cyan-400 ring-1 ring-cyan-400/50"
                      : "border-gray-700 hover:border-gray-500"
                  }`}
                  style={{ background: t.gradient }}
                >
                  {/* Mini preview lines */}
                  <div className="absolute inset-1 flex flex-col gap-0.5 opacity-40">
                    <div className="h-1 w-3/4 rounded-full bg-cyan-500/50" />
                    <div className="h-0.5 w-full rounded-full bg-gray-500/30" />
                    <div className="h-0.5 w-2/3 rounded-full bg-gray-500/20" />
                  </div>
                  {/* Radio dot */}
                  <div className={`absolute bottom-0.5 left-1/2 -translate-x-1/2 w-2 h-2 rounded-full border ${
                    get("appearance", "theme", "midnight_bloomberg") === t.key
                      ? "border-cyan-400 bg-cyan-400"
                      : "border-gray-600 bg-transparent"
                  }`} />
                </button>
              ))}
            </div>
            <span className="text-[9px] text-gray-500">
              {get("appearance", "theme", "midnight_bloomberg") === "midnight_bloomberg" ? "Midnight Bloomberg" :
               get("appearance", "theme") === "classic_dark" ? "Classic Dark" :
               get("appearance", "theme") === "oled_black" ? "OLED Black" : "Midnight Bloomberg"}
            </span>
          </div>
          <MiniSelect label="Density" value={get("appearance", "density", "ultra_dense")} options={[
            { value: "ultra_dense", label: "Ultra Dense" },
            { value: "compact", label: "Compact" },
            { value: "comfortable", label: "Comfortable" },
          ]} onChange={(e) => updateField("appearance", "density", e.target.value)} />
          <MiniSelect label="Font" value={get("appearance", "font", "monospace")} options={["monospace", "sans-serif", "serif"]} onChange={(e) => updateField("appearance", "font", e.target.value)} />
          <MiniToggle label="Animations" checked={!!get("appearance", "animations", true)} onChange={(v) => updateField("appearance", "animations", v)} />
          <MiniToggle label="Sound Alerts" checked={!!get("appearance", "soundAlerts", false)} onChange={(v) => updateField("appearance", "soundAlerts", v)} />
        </SectionCard>

        {/* MARKET DATA */}
        <SectionCard title="Market Data">
          <MiniSelect label="Timeframe" value={get("appearance", "chartTimeframe", "5m")} options={["1m", "5m", "15m", "1h", "4h", "1d"]} onChange={(e) => updateField("appearance", "chartTimeframe", e.target.value)} />
          <MiniSelect label="Update" value={get("dataSources", "updateFrequency", "5s")} options={["1s", "5s", "15s", "30s", "60s"]} onChange={(e) => updateField("dataSources", "updateFrequency", e.target.value)} />
          <MiniToggle label="After-hours" checked={!!get("trading", "afterHoursEnabled", false)} onChange={(v) => updateField("trading", "afterHoursEnabled", v)} />
          <MiniField label="Gap filter" value={get("scanning", "gapFilter", 2)} type="number" suffix="%" onChange={(e) => updateField("scanning", "gapFilter", Number(e.target.value))} />
          <MiniToggle label="Pre-Market" checked={!!get("trading", "preMarketEnabled", false)} onChange={(v) => updateField("trading", "preMarketEnabled", v)} />
          <MiniField label="Volume Min" value={get("scanning", "volumeMin", "YTD, 1M, All")} onChange={(e) => updateField("scanning", "volumeMin", e.target.value)} />
          <MiniSelect label="Export" value={get("dataSources", "exportFormat", "json")} options={["json", "csv"]} onChange={(e) => updateField("dataSources", "exportFormat", e.target.value)} />
        </SectionCard>

        {/* STRATEGY */}
        <SectionCard title="Strategy">
          <MiniToggle label="Adaptive" checked={!!get("trading", "adaptiveStrategy", true)} onChange={(v) => updateField("trading", "adaptiveStrategy", v)} />
          <MiniToggle label="Regime Switch" checked={!!get("trading", "regimeSwitch", true)} onChange={(v) => updateField("trading", "regimeSwitch", v)} />
          <div className="mt-1 pt-1 border-t border-gray-800/50 space-y-0.5">
            <MiniSelect label="Bull" value={get("trading", "bullStrategy", "momentum")} options={["momentum", "breakout", "mean_reversion"]} onChange={(e) => updateField("trading", "bullStrategy", e.target.value)} />
            <MiniSelect label="Bear" value={get("trading", "bearStrategy", "defensive")} options={["defensive", "short_bias", "hedge"]} onChange={(e) => updateField("trading", "bearStrategy", e.target.value)} />
            <MiniSelect label="Neutral" value={get("trading", "neutralStrategy", "range_bound")} options={["range_bound", "pairs", "stat_arb"]} onChange={(e) => updateField("trading", "neutralStrategy", e.target.value)} />
            <MiniSelect label="Range" value={get("trading", "rangeStrategy", "mean_reversion")} options={["mean_reversion", "scalping", "grid"]} onChange={(e) => updateField("trading", "rangeStrategy", e.target.value)} />
          </div>
          <div className="mt-1 pt-1 border-t border-gray-800/50 space-y-0.5">
            <MiniField label="Min Prob" value={get("trading", "minProbability", 0.65)} type="number" step="0.01" onChange={(e) => updateField("trading", "minProbability", parseFloat(e.target.value))} />
            <MiniToggle label="Override" checked={!!get("trading", "manualOverride", false)} onChange={(v) => updateField("trading", "manualOverride", v)} />
          </div>
        </SectionCard>

        {/* BACKUP & SYSTEM */}
        <SectionCard title="Backup & System">
          <div className="space-y-1">
            <div className="text-[9px] text-gray-500 font-mono">
              {new Date().toISOString().replace("T", " ").slice(0, 19)} (Jmesca)
            </div>
            <div className="text-[9px] text-gray-600 space-y-0.5">
              <div>System: <span className="text-gray-400">v0.3-alpha</span></div>
              <div>DB: <span className="text-gray-400">DuckDB 0.9.x</span></div>
              <div>CPU: <span className="text-gray-400">12 cores</span></div>
              <div>RAM: <span className="text-gray-400">32 GB</span></div>
              <div>GPU: <span className="text-green-400">RTX 4090 ✓ Detected</span></div>
              <div>AES-256 on disk &middot; Auto-backup: daily</div>
            </div>
            <div className="flex gap-1">
              <button onClick={onExport} className="flex-1 text-[9px] bg-[#0B0E14] border border-gray-700/50 rounded px-2 py-1 text-cyan-400 hover:bg-gray-800 flex items-center gap-1 justify-center">
                <Download className="w-2.5 h-2.5" /> Export
              </button>
              <button onClick={() => importRef.current?.click()} className="flex-1 text-[9px] bg-[#0B0E14] border border-gray-700/50 rounded px-2 py-1 text-cyan-400 hover:bg-gray-800 flex items-center gap-1 justify-center">
                <Upload className="w-2.5 h-2.5" /> Import
              </button>
            </div>
            <button
              onClick={() => { onReset("trading"); onReset("risk"); onReset("ml"); onReset("agents"); }}
              className="w-full text-[9px] bg-red-900/20 border border-red-800/30 rounded px-2 py-1 text-red-400 hover:bg-red-900/30 flex items-center gap-1 justify-center"
            >
              <RotateCcw className="w-2.5 h-2.5" /> Reset All Defaults
            </button>
          </div>
          <button
            onClick={() => setShowFullLog(!showFullLog)}
            className="mt-1 w-full text-[9px] bg-cyan-500/10 border border-cyan-500/20 rounded px-2 py-1 text-cyan-400 hover:bg-cyan-500/20 flex items-center gap-1 justify-center"
          >
            <FileText className="w-2.5 h-2.5" /> {showFullLog ? "Hide" : "View"} Full Log
          </button>
        </SectionCard>
      </div>

      {/* ═══════ FOOTER BAR ═══════ */}
      <div className="flex items-center justify-between mt-2 pt-2 border-t border-gray-800/50">
        <div className="flex gap-2">
          <button
            onClick={onExport}
            className="text-[10px] text-gray-500 hover:text-cyan-400 flex items-center gap-1 px-3 py-1 border border-gray-800/50 rounded"
          >
            Export Settings
          </button>
          <button
            onClick={() => importRef.current?.click()}
            className="text-[10px] text-gray-500 hover:text-cyan-400 flex items-center gap-1 px-3 py-1 border border-gray-800/50 rounded"
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
          className="bg-green-600 hover:bg-green-700 text-white font-bold text-[10px] px-5 py-1.5 rounded uppercase tracking-wider disabled:opacity-50 flex items-center gap-1.5"
        >
          <Save className="w-3 h-3" />
          {saving ? "Saving..." : "SAVE ALL CHANGES"}
        </button>
      </div>

      {/* ═══════ FULL AUDIT LOG (expanded) ═══════ */}
      {showFullLog && (
        <div className="mt-3">
          <AuditLogPanel />
        </div>
      )}
    </div>
  );
}

// ── Audit Log Panel ──────────────────────────────────────────
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
          className="text-[9px] text-cyan-400 hover:text-cyan-300 flex items-center gap-1"
        >
          <Download className="w-2.5 h-2.5" /> Export Log
        </button>
      </div>
    </SectionCard>
  );
}
