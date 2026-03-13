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
  Monitor, Lock, Clock, ChevronDown, Star,
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

function SectionCard({ title, children, className = "", star = false }) {
  return (
    <div className={`bg-[#111827] border border-[rgba(42,52,68,0.5)] rounded-lg p-2 shadow-sm ${className}`}>
      <div className="flex items-center gap-1.5 mb-1.5 pb-1 border-b border-gray-800/50">
        {star && <Star className="w-3 h-3 text-amber-400 fill-amber-400 flex-shrink-0" />}
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
          onClick={async () => { try { await saveAllSettings(); toast.success("All settings saved", TOAST_CFG); } catch { toast.error("Failed to save settings", TOAST_CFG); } }}
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
          <MiniField label="Email" value={get("user", "email", "espen@embodier.ai")} onChange={(e) => updateField("user", "email", e.target.value)} />
          <MiniSelect label="Timezone" value={get("user", "timezone", "America/New_York")} options={[
            { value: "America/New_York", label: "EST" },
            { value: "America/Chicago", label: "CT" },
            { value: "America/Los_Angeles", label: "PT" },
            { value: "UTC", label: "UTC" },
            { value: "Europe/Oslo", label: "CET" },
          ]} onChange={(e) => updateField("user", "timezone", e.target.value)} />
          <MiniSelect label="Currency" value={get("user", "currency", "USD")} options={[
            { value: "USD", label: "USD" },
            { value: "EUR", label: "EUR" },
            { value: "GBP", label: "GBP" },
          ]} onChange={(e) => updateField("user", "currency", e.target.value)} />
          <MiniSelect label="Timeframe" value={get("appearance", "chartTimeframe", "1D")} options={[
            { value: "1m", label: "1M" },
            { value: "5m", label: "5M" },
            { value: "15m", label: "15M" },
            { value: "1D", label: "1D" },
            { value: "1W", label: "1W" },
          ]} onChange={(e) => updateField("appearance", "chartTimeframe", e.target.value)} />
          <div className="flex items-center justify-between py-[1px] pt-1">
            <span className="text-[10px] text-gray-400">Avatar</span>
            <button className="text-[9px] text-[#00D9FF] hover:text-cyan-300 px-2 py-1 border border-gray-700/50 rounded">Choose File</button>
          </div>
        </SectionCard>

        {/* 2. TRADING MODE */}
        <SectionCard title="Trading Mode">
          <div className="flex items-center gap-4 mb-1">
            <span className={`text-sm font-bold ${get("dataSources", "alpacaBaseUrl", "paper") === "paper" ? "text-emerald-500" : "text-gray-500"}`}>PAPER</span>
            <button
              onClick={() => updateField("dataSources", "alpacaBaseUrl", get("dataSources", "alpacaBaseUrl", "paper") === "paper" ? "live" : "paper")}
              className={`relative w-14 h-7 rounded-full transition-colors ${get("dataSources", "alpacaBaseUrl", "paper") === "live" ? "bg-red-500" : "bg-emerald-500"}`}
            >
              <div className={`absolute top-0.5 w-6 h-6 bg-white rounded-full transition-transform ${get("dataSources", "alpacaBaseUrl", "paper") === "live" ? "translate-x-7" : "translate-x-0.5"}`} />
            </button>
            <span className={`text-sm font-bold ${get("dataSources", "alpacaBaseUrl", "paper") === "live" ? "text-red-400" : "text-gray-500"}`}>LIVE</span>
          </div>
          {get("dataSources", "alpacaBaseUrl", "paper") === "live" && (
            <p className="text-[10px] text-emerald-400 mt-1">▲ Live mode = real money</p>
          )}
          <MiniSelect label="Broker" value={get("trading", "broker", "alpaca")} options={[
            { value: "alpaca", label: "Alpaca Markets" },
            { value: "ibkr", label: "Interactive Brokers" },
          ]} onChange={(e) => updateField("trading", "broker", e.target.value)} />
          <div className="flex items-center justify-between py-[1px]">
            <span className="text-[10px] text-gray-400">Status</span>
            <span className="text-[9px] text-emerald-400 flex items-center gap-1"><span className="w-1.5 h-1.5 rounded-full bg-emerald-500" /> Connected</span>
          </div>
          <MiniField label="Account" value={get("trading", "accountType", "Paper Trading")} onChange={(e) => updateField("trading", "accountType", e.target.value)} />
          <MiniField label="Sync" value={get("trading", "lastSync", "2026-03-01 06:50")} onChange={(e) => updateField("trading", "lastSync", e.target.value)} />
        </SectionCard>

        {/* 3. POSITION SIZING */}
        <SectionCard title="Position Sizing">
          <MiniField label="Base Size" value={get("trading", "baseSize", "$25,000")} onChange={(e) => updateField("trading", "baseSize", e.target.value)} />
          <MiniField label="Max Size" value={get("trading", "maxPositionSize", "$100,000")} onChange={(e) => updateField("trading", "maxPositionSize", e.target.value)} />
          <MiniField label="Max Positions" value={get("risk", "maxPositions", 5)} type="number" onChange={(e) => updateField("risk", "maxPositions", Number(e.target.value))} />
          <MiniSelect label="Size Mode" value={get("trading", "sizeMode", "Fixed")} options={["Fixed", "Percent", "Kelly"]} onChange={(e) => updateField("trading", "sizeMode", e.target.value)} />
          <MiniToggle label="Auto-Scale" checked={!!get("trading", "autoScale", true)} onChange={(v) => updateField("trading", "autoScale", v)} />
        </SectionCard>

        {/* 4. RISK LIMITS */}
        <SectionCard title="Risk Limits" star>
          <MiniField label="Max Daily Risk" value={get("risk", "maxDailyRiskPct", 2.0)} type="number" step="0.1" suffix="%" onChange={(e) => updateField("risk", "maxDailyRiskPct", parseFloat(e.target.value))} />
          <MiniField label="Max Per Trade" value={get("risk", "maxPerTradePct", 0.5)} type="number" step="0.1" suffix="%" onChange={(e) => updateField("risk", "maxPerTradePct", parseFloat(e.target.value))} />
          <MiniField label="Max Daily Loss" value={get("risk", "maxDailyLoss", "$2,500")} onChange={(e) => updateField("risk", "maxDailyLoss", e.target.value)} />
          <MiniField label="Portfolio Heat" value={get("risk", "portfolioHeat", 8.0)} type="number" step="0.1" suffix="%" onChange={(e) => updateField("risk", "portfolioHeat", parseFloat(e.target.value))} />
          <MiniField label="Correlation" value={get("risk", "correlationLimit", 0.75)} type="number" step="0.01" onChange={(e) => updateField("risk", "correlationLimit", parseFloat(e.target.value))} />
        </SectionCard>

        {/* 5. CIRCUIT BREAKERS */}
        <SectionCard title="Circuit Breakers" star>
          <MiniToggle label="Master Killswitch" checked={!!get("risk", "masterKillswitch", false)} onChange={(v) => updateField("risk", "masterKillswitch", v)} />
          <MiniToggle label="VIX Halt (>15%)" checked={!!get("risk", "vixHalt", true)} onChange={(v) => updateField("risk", "vixHalt", v)} />
          <MiniToggle label="Flash Crash" checked={!!get("risk", "flashCrash", true)} onChange={(v) => updateField("risk", "flashCrash", v)} />
          <MiniToggle label="Daily Loss" checked={!!get("risk", "dailyLossBreaker", true)} onChange={(v) => updateField("risk", "dailyLossBreaker", v)} />
          <MiniToggle label="Consecutive Loss (5)" checked={!!get("risk", "consecutiveLossBreaker", true)} onChange={(v) => updateField("risk", "consecutiveLossBreaker", v)} />
        </SectionCard>
      </div>

      {/* ROW 2: Brokerage Connections, Data Feed API Keys, Data Source Priority, Global Local LLM, Inference Models */}
      <div className="grid grid-cols-5 gap-2 mb-2">

        {/* 6. BROKERAGE CONNECTIONS */}
        <SectionCard title="Brokerage Connections">
          <div className="flex items-center justify-between py-0.5">
            <span className="text-[10px] text-gray-400">Alpaca Markets</span>
            <div className="flex items-center gap-1">
              <span className="text-[9px] text-emerald-400 flex items-center gap-1"><span className="w-1.5 h-1.5 rounded-full bg-emerald-500" /> Connected</span>
              <span className="text-[9px] text-gray-500 font-mono">PK8V2****</span>
              <button onClick={() => onTestConn("alpaca")} className="text-[9px] text-[#00D9FF] hover:text-cyan-300">[Test]</button>
              <button className="text-[9px] text-[#00D9FF] hover:text-cyan-300">[Edit]</button>
            </div>
          </div>
          <div className="flex items-center justify-between py-0.5">
            <span className="text-[10px] text-gray-400">Interactive Brokers</span>
            <div className="flex items-center gap-1">
              <span className="text-[9px] text-gray-500">Not Configured</span>
              <button className="text-[9px] text-[#00D9FF] hover:text-cyan-300">[Add]</button>
            </div>
          </div>
          <div className="flex items-center justify-between py-0.5">
            <span className="text-[10px] text-gray-400">Tradier</span>
            <div className="flex items-center gap-1">
              <span className="text-[9px] text-gray-500">Not Configured</span>
              <button className="text-[9px] text-[#00D9FF] hover:text-cyan-300">[Add]</button>
            </div>
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
            <span className="text-[10px] text-gray-400">Unusual Whales</span>
            <div className="flex items-center gap-1">
              <span className="text-[9px] text-emerald-400 flex items-center gap-1"><span className="w-1.5 h-1.5 rounded-full bg-emerald-500" /> Connected</span>
              <span className="text-[9px] text-gray-500 font-mono">UW_882****</span>
              <button className="text-[9px] text-[#00D9FF] hover:text-cyan-300">[Test]</button>
              <button className="text-[9px] text-[#00D9FF] hover:text-cyan-300">[Edit]</button>
            </div>
          </div>
          <div className="flex items-center justify-between py-0.5">
            <span className="text-[10px] text-gray-400">Polygon.io</span>
            <div className="flex items-center gap-1">
              <span className="text-[9px] text-amber-400 flex items-center gap-1">▲ Degraded</span>
              <span className="text-[9px] text-gray-500 font-mono">sk-proj-****</span>
              <button className="text-[9px] text-[#00D9FF] hover:text-cyan-300">[Test]</button>
              <button className="text-[9px] text-[#00D9FF] hover:text-cyan-300">[Edit]</button>
            </div>
          </div>
          <div className="flex items-center justify-between py-0.5">
            <span className="text-[10px] text-gray-400">OpenAI</span>
            <div className="flex items-center gap-1">
              <span className="text-[9px] text-emerald-400 flex items-center gap-1"><span className="w-1.5 h-1.5 rounded-full bg-emerald-500" /> Connected</span>
              <button className="text-[9px] text-[#00D9FF] hover:text-cyan-300">[Test]</button>
              <button className="text-[9px] text-[#00D9FF] hover:text-cyan-300">[Edit]</button>
            </div>
          </div>
          <div className="flex items-center justify-between py-0.5">
            <span className="text-[10px] text-gray-400">FRED</span>
            <div className="flex items-center gap-1">
              <span className="text-[9px] text-gray-500">Not Set</span>
              <button className="text-[9px] text-[#00D9FF] hover:text-cyan-300">[Add]</button>
            </div>
          </div>
          <div className="flex items-center justify-between py-0.5">
            <span className="text-[10px] text-gray-400">SEC EDGAR</span>
            <div className="flex items-center gap-1">
              <span className="text-[9px] text-gray-500">Not Set</span>
              <button className="text-[9px] text-[#00D9FF] hover:text-cyan-300">[Add]</button>
            </div>
          </div>
        </SectionCard>

        {/* 8. DATA SOURCE PRIORITY */}
        <SectionCard title="Data Source Priority">
          <MiniSelect label="Primary Pricing" value={get("dataSources", "primaryPricing", "polygon_sip")} options={[
            { value: "polygon_sip", label: "Polygon.io (SIP)" },
            { value: "alpaca", label: "Alpaca" },
          ]} onChange={(e) => updateField("dataSources", "primaryPricing", e.target.value)} />
          <MiniSelect label="Fallback" value={get("dataSources", "fallbackPricing", "alpaca_v2")} options={[
            { value: "alpaca_v2", label: "Alpaca Data V2" },
            { value: "polygon", label: "Polygon" },
          ]} onChange={(e) => updateField("dataSources", "fallbackPricing", e.target.value)} />
          <MiniSelect label="Options Flow" value={get("dataSources", "optionsFlowPriority", "unusual_whales")} options={[
            { value: "unusual_whales", label: "Unusual Whales" },
            { value: "polygon", label: "Polygon" },
          ]} onChange={(e) => updateField("dataSources", "optionsFlowPriority", e.target.value)} />
          <MiniSelect label="Economic" value={get("dataSources", "economicPriority", "fred")} options={[
            { value: "fred", label: "FRED" },
            { value: "none", label: "None" },
          ]} onChange={(e) => updateField("dataSources", "economicPriority", e.target.value)} />
          <MiniSelect label="Filings" value={get("dataSources", "secEdgarPriority", "sec_edgar")} options={[
            { value: "sec_edgar", label: "SEC EDGAR" },
            { value: "polygon", label: "Polygon" },
          ]} onChange={(e) => updateField("dataSources", "secEdgarPriority", e.target.value)} />
          <MiniSelect label="Rate Limit" value={get("dataSources", "rateLimitMode", "conservative")} options={[
            { value: "conservative", label: "Conservative" },
            { value: "moderate", label: "Moderate" },
            { value: "aggressive", label: "Aggressive" },
          ]} onChange={(e) => updateField("dataSources", "rateLimitMode", e.target.value)} />
        </SectionCard>

        {/* 9. OLLAMA LOCAL LLM */}
        <SectionCard title="Ollama Local LLM" star>
          <div className="flex items-center justify-between gap-2 py-[1px]">
            <span className="text-[10px] text-gray-400 whitespace-nowrap">Endpoint</span>
            <input type="text" value={get("ollama", "ollamaHostUrl", "http://localhost:11434")} onChange={(e) => updateField("ollama", "ollamaHostUrl", e.target.value)} className="w-28 bg-[#0B0E14] border border-gray-700/50 rounded px-1.5 py-0.5 text-[10px] text-white outline-none focus:border-[#00D9FF]/50/50" />
          </div>
          <div className="flex items-center justify-between pt-0.5">
            <span className="text-[10px] text-gray-400">Status</span>
            <div className="flex items-center gap-1">
              <span className={`text-[9px] flex items-center gap-1 ${ollamaCr.valid ? "text-emerald-400" : "text-red-400"}`}>
                <span className={`w-1.5 h-1.5 rounded-full ${ollamaCr.valid ? "bg-emerald-500" : "bg-red-500"}`} />
                {ollamaCr.valid ? "Connected" : "Not Connected"}
              </span>
              <button onClick={() => onTestConn("ollama")} className="text-[9px] text-[#00D9FF] hover:text-cyan-300">{ollamaCr.testing ? "..." : "[Test]"}</button>
            </div>
          </div>
          <div className="pt-0.5 space-y-0.5">
            <span className="text-[9px] text-gray-500 block mb-0.5">Models</span>
            {["llama3:70b", "mistral:7b", "mixtral:7b", "mixtral:8x7b", "codellama:34b"].map((m) => {
              const models = (get("ollama", "models", "") || "").split(",").filter(Boolean);
              const checked = models.includes(m) || get("ollama", "ollamaDefaultModel", "").startsWith(m.split(":")[0]);
              return (
                <MiniCheckbox
                  key={m}
                  label={m}
                  checked={!!checked}
                  onChange={(v) => {
                    const next = v ? [...models, m] : models.filter((x) => x !== m);
                    updateField("ollama", "models", next.join(","));
                  }}
                />
              );
            })}
          </div>
          <button className="text-[9px] text-[#00D9FF] hover:text-cyan-300 mt-0.5">[Pull Models]</button>
          <div className="flex items-center justify-between gap-2 py-[1px] pt-0.5">
            <span className="text-[10px] text-gray-400">Use for</span>
            <input type="text" value={get("ollama", "useFor", "Pattern Analysis")} onChange={(e) => updateField("ollama", "useFor", e.target.value)} placeholder="Pattern Analysis" className="w-24 bg-[#0B0E14] border border-gray-700/50 rounded px-1.5 py-0.5 text-[10px] text-white outline-none focus:border-[#00D9FF]/50/50" />
          </div>
        </SectionCard>

        {/* 10. AI INFERENCE MODELS */}
        <SectionCard title="AI Inference Models">
          <MiniSelect label="Primary" value={get("ollama", "primaryModel", "gpt-4o")} options={[
            { value: "gpt-4o", label: "GPT-4o" },
            { value: "claude-3.5", label: "Claude 3.5" },
          ]} onChange={(e) => updateField("ollama", "primaryModel", e.target.value)} />
          <MiniSelect label="Fallback" value={get("ollama", "fallbackModel", "claude-3.5")} options={[
            { value: "claude-3.5", label: "Claude 3.5" },
            { value: "gpt-4o", label: "GPT-4o" },
          ]} onChange={(e) => updateField("ollama", "fallbackModel", e.target.value)} />
          <MiniSelect label="Local" value={get("ollama", "localModel", "Ollama")} options={[
            { value: "Ollama", label: "Ollama" },
            { value: "none", label: "None" },
          ]} onChange={(e) => updateField("ollama", "localModel", e.target.value)} />
          <MiniField label="Timeout" value={get("ollama", "timeout", 10)} type="number" suffix="s" onChange={(e) => updateField("ollama", "timeout", Number(e.target.value))} />
          <MiniField label="Max Tokens" value={get("ollama", "maxTokens", 2048)} type="number" onChange={(e) => updateField("ollama", "maxTokens", Number(e.target.value))} />
          <MiniField label="Temperature" value={get("ollama", "temperature", 0.3)} type="number" step="0.1" onChange={(e) => updateField("ollama", "temperature", parseFloat(e.target.value))} />
          <div className="flex items-center justify-between gap-2 py-[1px] pt-0.5">
            <span className="text-[10px] text-gray-400">Use for</span>
            <input type="text" value={get("ollama", "inferenceUseFor", "Signal reasoning")} onChange={(e) => updateField("ollama", "inferenceUseFor", e.target.value)} placeholder="Signal reasoning" className="w-24 bg-[#0B0E14] border border-gray-700/50 rounded px-1.5 py-0.5 text-[10px] text-white outline-none focus:border-[#00D9FF]/50/50" />
          </div>
        </SectionCard>
      </div>

      {/* ROW 3: ML Models, Learning Log, OpenClaw Agents, Agent Thresholds, Signal Thresholds */}
      <div className="grid grid-cols-5 gap-2 mb-2">

        {/* 11. ML MODELS */}
        <SectionCard title="ML Models">
          <div className="grid grid-cols-3 gap-2 mb-1">
            {["LSTM", "XGBoost", "HMM"].map((name) => (
              <div key={name} className="space-y-0.5">
                <div className="flex items-center gap-1">
                  <span className="w-1.5 h-1.5 rounded-full bg-emerald-500" />
                  <span className="text-[9px] font-bold text-emerald-400">Active</span>
                </div>
                <MiniField label="Min Conf" value={get("ml", "minConf", 0.6)} type="number" step="0.01" onChange={(e) => updateField("ml", "minConf", parseFloat(e.target.value))} />
                <MiniField label="Lookback" value={get("ml", "lookback", 60)} type="number" onChange={(e) => updateField("ml", "lookback", Number(e.target.value))} />
                <MiniSelect label="Retrain" value={get("ml", "retrainFrequency", "Weekly")} options={["Daily", "Weekly", "Monthly"]} onChange={(e) => updateField("ml", "retrainFrequency", e.target.value)} />
              </div>
            ))}
          </div>
        </SectionCard>

        {/* 12. ML FLYWHEEL */}
        <SectionCard title="ML Flywheel" star>
          <MiniSelect label="Learning Loop" value={get("ml", "learningLoop", "auto")} options={["auto", "manual", "hybrid"]} onChange={(e) => updateField("ml", "learningLoop", e.target.value)} />
          <MiniToggle label="Auto-Retrain" checked={!!get("ml", "autoRetrain", true)} onChange={(v) => updateField("ml", "autoRetrain", v)} />
          <MiniToggle label="Drift Detection" checked={!!get("ml", "driftDetection", true)} onChange={(v) => updateField("ml", "driftDetection", v)} />
          <MiniSelect label="Schedule" value={get("ml", "schedule", "Medium")} options={["Light", "Medium", "Heavy"]} onChange={(e) => updateField("ml", "schedule", e.target.value)} />
          <MiniField label="Walk-Forward" value={get("ml", "walkForward", "Sunday 02:00")} onChange={(e) => updateField("ml", "walkForward", e.target.value)} />
          <MiniField label="Validation" value={get("ml", "validationDays", 30)} type="number" suffix="days" onChange={(e) => updateField("ml", "validationDays", Number(e.target.value))} />
          <MiniField label="Min Samples" value={get("ml", "minSamples", 500)} type="number" onChange={(e) => updateField("ml", "minSamples", Number(e.target.value))} />
          <MiniToggle label="Feature Tracking" checked={!!get("ml", "featureTracking", true)} onChange={(v) => updateField("ml", "featureTracking", v)} />
        </SectionCard>

        {/* 13. OPENCLAW AGENTS */}
        <SectionCard title="OpenClaw Agents" star>
          <MiniSelect label="Swarm Mode" value={get("agents", "swarmMode", "Parallel")} options={["Parallel", "Sequential", "Hybrid"]} onChange={(e) => updateField("agents", "swarmMode", e.target.value)} />
          <div className="flex items-center justify-between py-[1px]">
            <span className="text-[10px] text-gray-400">Voting</span>
            <span className="text-[9px] text-gray-300">Enabled (min 3)</span>
          </div>
          <div className="flex items-center justify-between py-[1px]">
            <span className="text-[10px] text-gray-400">Queue</span>
            <span className="text-[9px] text-gray-300">Priority-based</span>
          </div>
          <MiniToggle label="Blackboard" checked={!!get("agents", "blackboard", true)} onChange={(v) => updateField("agents", "blackboard", v)} />
          <div className="border-t border-gray-800/50 pt-1 mt-0.5 space-y-0.5">
            {[
              { key: "marketScanner", label: "Market Scanner" },
              { key: "patternRecognition", label: "Pattern Recognition" },
              { key: "riskAssessment", label: "Risk Assessment" },
              { key: "sentiment", label: "Sentiment" },
              { key: "youtube", label: "YouTube" },
              { key: "macroRegime", label: "Macro Regime" },
              { key: "optionsFlow", label: "Options Flow" },
              { key: "earnings", label: "Earnings" },
              { key: "backtesting", label: "Backtesting" },
              { key: "tradeExecution", label: "Trade Execution" },
            ].map((agent) => (
              <MiniToggle key={agent.key} label={agent.label} checked={!!get("agents", agent.key, agent.key === "backtesting" ? false : true)} onChange={(v) => updateField("agents", agent.key, v)} />
            ))}
          </div>
        </SectionCard>

        {/* 14. AGENT THRESHOLDS */}
        <SectionCard title="Agent Thresholds">
          <MiniField label="Market Scanner" value={get("agents", "marketScannerThreshold", "500K vol")} onChange={(e) => updateField("agents", "marketScannerThreshold", e.target.value)} />
          <MiniField label="Pattern" value={get("agents", "patternConfidence", "75% conf")} onChange={(e) => updateField("agents", "patternConfidence", e.target.value)} />
          <MiniField label="Risk" value={get("agents", "riskHeat", "10% heat")} onChange={(e) => updateField("agents", "riskHeat", e.target.value)} />
          <MiniField label="Sentiment" value={get("agents", "sentimentScore", "60 score")} onChange={(e) => updateField("agents", "sentimentScore", e.target.value)} />
          <MiniField label="YouTube" value={get("agents", "youtubeViews", "10K views")} onChange={(e) => updateField("agents", "youtubeViews", e.target.value)} />
          <MiniField label="Regime" value={get("agents", "regimeProb", "0.65 prob")} onChange={(e) => updateField("agents", "regimeProb", e.target.value)} />
          <MiniField label="Options" value={get("agents", "optionsPremium", "$100K premium")} onChange={(e) => updateField("agents", "optionsPremium", e.target.value)} />
          <MiniField label="Earnings" value={get("agents", "earningsDays", "3 days")} onChange={(e) => updateField("agents", "earningsDays", e.target.value)} />
        </SectionCard>

        {/* 15. AGENT COORDINATION */}
        <SectionCard title="Agent Coordination">
          <MiniSelect label="Task Assignment" value={get("agents", "taskAssignment", "Auto")} options={["Auto", "Manual", "Hybrid"]} onChange={(e) => updateField("agents", "taskAssignment", e.target.value)} />
          <MiniField label="Timeout" value={get("agents", "taskTimeout", 30)} type="number" suffix="s" onChange={(e) => updateField("agents", "taskTimeout", Number(e.target.value))} />
          <MiniField label="Max Tasks" value={get("agents", "maxTasks", 3)} type="number" onChange={(e) => updateField("agents", "maxTasks", Number(e.target.value))} />
          <MiniField label="Health Check" value={get("agents", "healthCheck", 60)} type="number" suffix="s" onChange={(e) => updateField("agents", "healthCheck", Number(e.target.value))} />
          <MiniField label="Retry" value={get("agents", "retryAttempts", 2)} type="number" suffix="attempts" onChange={(e) => updateField("agents", "retryAttempts", Number(e.target.value))} />
          <MiniSelect label="Log Level" value={get("system", "logLevel", "INFO")} options={["DEBUG", "INFO", "WARNING", "ERROR"]} onChange={(e) => updateField("system", "logLevel", e.target.value)} />
          <MiniToggle label="Telemetry" checked={!!get("agents", "telemetry", true)} onChange={(v) => updateField("agents", "telemetry", v)} />
        </SectionCard>
      </div>

      {/* ROW 4: Trade Management, Order Execution, Notifications, Security & Auth, Backup & System */}
      <div className="grid grid-cols-5 gap-2 mb-2">

        {/* 16. TRADE MANAGEMENT */}
        <SectionCard title="Trade Management">
          <MiniField label="Default SL" value={get("risk", "defaultSL", "1.0 ATR")} onChange={(e) => updateField("risk", "defaultSL", e.target.value)} />
          <MiniField label="TP1" value={get("risk", "takeProfit1", 1.5)} type="number" step="0.1" suffix="R" onChange={(e) => updateField("risk", "takeProfit1", parseFloat(e.target.value))} />
          <MiniField label="TP2" value={get("risk", "takeProfit2", 3.0)} type="number" step="0.1" suffix="R" onChange={(e) => updateField("risk", "takeProfit2", parseFloat(e.target.value))} />
          <MiniField label="Trailing" value={get("risk", "trailingStop", 1.5)} type="number" step="0.1" suffix="R" onChange={(e) => updateField("risk", "trailingStop", parseFloat(e.target.value))} />
          <MiniField label="Partial Exit" value={get("risk", "partialExit", "50%")} onChange={(e) => updateField("risk", "partialExit", e.target.value)} />
          <MiniField label="Time Exit" value={get("trading", "timeExit", "EOD")} onChange={(e) => updateField("trading", "timeExit", e.target.value)} />
          <MiniToggle label="Extended Hours" checked={!!get("trading", "extendedHours", false)} onChange={(v) => updateField("trading", "extendedHours", v)} />
          <MiniToggle label="Dry Run" checked={!!get("trading", "dryRun", true)} onChange={(v) => updateField("trading", "dryRun", v)} />
        </SectionCard>

        {/* 17. ORDER EXECUTION */}
        <SectionCard title="Order Execution">
          <MiniSelect label="Order Type" value={get("trading", "orderType", "Limit")} options={["Market", "Limit", "Stop", "Stop Limit"]} onChange={(e) => updateField("trading", "orderType", e.target.value)} />
          <MiniField label="Offset" value={get("trading", "offset", "0.01%")} onChange={(e) => updateField("trading", "offset", e.target.value)} />
          <MiniField label="Slippage" value={get("trading", "slippageTolerance", 0.05)} type="number" step="0.01" suffix="%" onChange={(e) => updateField("trading", "slippageTolerance", parseFloat(e.target.value))} />
          <MiniField label="Timeout" value={get("trading", "orderTimeout", 60)} type="number" suffix="s" onChange={(e) => updateField("trading", "orderTimeout", Number(e.target.value))} />
          <MiniToggle label="Pre-Trade Check" checked={!!get("trading", "preTradeCheck", true)} onChange={(v) => updateField("trading", "preTradeCheck", v)} />
          <MiniToggle label="Post-Trade Confirm" checked={!!get("trading", "confirmBeforeOrder", true)} onChange={(v) => updateField("trading", "confirmBeforeOrder", v)} />
        </SectionCard>

        {/* 18. NOTIFICATIONS */}
        <SectionCard title="Notifications" star>
          <div className="mb-0.5">
            <span className="text-[9px] text-gray-500 uppercase font-bold">Channels</span>
          </div>
          <div className="flex flex-wrap gap-x-3 gap-y-0.5 mb-1">
            {["Discord", "SMS", "Email", "Slack"].map((ch) => (
              <MiniCheckbox key={ch} label={ch} checked={!!get("notifications", ch.toLowerCase(), true)} onChange={(v) => updateField("notifications", ch.toLowerCase(), v)} />
            ))}
          </div>
          <div className="border-t border-gray-800/50 pt-1 space-y-0.5">
            <MiniToggle label="Trade Executions" checked={!!get("notifications", "tradeAlerts", true)} onChange={(v) => updateField("notifications", "tradeAlerts", v)} />
            <MiniToggle label="Pattern Alerts" checked={!!get("notifications", "patternAlerts", true)} onChange={(v) => updateField("notifications", "patternAlerts", v)} />
            <MiniToggle label="Risk Warnings" checked={!!get("notifications", "riskAlerts", true)} onChange={(v) => updateField("notifications", "riskAlerts", v)} />
            <MiniToggle label="API Disconnects" checked={!!get("notifications", "apiDisconnects", true)} onChange={(v) => updateField("notifications", "apiDisconnects", v)} />
            <MiniToggle label="Options Anomalies" checked={!!get("notifications", "optionsAnomalies", false)} onChange={(v) => updateField("notifications", "optionsAnomalies", v)} />
            <MiniToggle label="EOD Summary" checked={!!get("notifications", "dailySummary", true)} onChange={(v) => updateField("notifications", "dailySummary", v)} />
            <MiniToggle label="Agent Tasks" checked={!!get("notifications", "agentTasks", true)} onChange={(v) => updateField("notifications", "agentTasks", v)} />
            <MiniToggle label="ML Drift" checked={!!get("notifications", "mlDrift", true)} onChange={(v) => updateField("notifications", "mlDrift", v)} />
            <MiniToggle label="Circuit Breaker" checked={!!get("notifications", "circuitBreaker", true)} onChange={(v) => updateField("notifications", "circuitBreaker", v)} />
            <MiniToggle label="Earnings (3d)" checked={!!get("notifications", "earnings3d", true)} onChange={(v) => updateField("notifications", "earnings3d", v)} />
            <MiniToggle label="Daily PnL" checked={!!get("notifications", "dailyPnl", true)} onChange={(v) => updateField("notifications", "dailyPnl", v)} />
            <MiniToggle label="YouTube Research" checked={!!get("notifications", "youtubeResearch", false)} onChange={(v) => updateField("notifications", "youtubeResearch", v)} />
          </div>
        </SectionCard>

        {/* 19. SECURITY & AUTH */}
        <SectionCard title="Security & Auth" star>
          <div className="space-y-0.5 mb-1">
            <span className="text-[9px] text-gray-500 block">Change Password</span>
            <div className="flex gap-1 flex-wrap">
              <input type="password" placeholder="Current" className="w-16 bg-[#0B0E14] border border-gray-700/50 rounded px-1.5 py-0.5 text-[10px] text-white outline-none" />
              <input type="password" placeholder="New" className="w-16 bg-[#0B0E14] border border-gray-700/50 rounded px-1.5 py-0.5 text-[10px] text-white outline-none" />
              <input type="password" placeholder="Confirm" className="w-16 bg-[#0B0E14] border border-gray-700/50 rounded px-1.5 py-0.5 text-[10px] text-white outline-none" />
              <button className="text-[9px] text-[#00D9FF] hover:text-cyan-300">[Update]</button>
            </div>
          </div>
          <div className="flex gap-2 mb-1">
            <button className="text-[9px] text-[#00D9FF] hover:text-cyan-300">[Enable TOTP]</button>
            <button className="text-[9px] text-[#00D9FF] hover:text-cyan-300">[Enable SMS]</button>
          </div>
          <div className="flex items-center justify-between py-[1px]">
            <span className="text-[10px] text-gray-400">Encryption</span>
            <span className="text-[9px] text-emerald-400 flex items-center gap-1"><span className="w-1.5 h-1.5 rounded-full bg-emerald-500" /> AES-256 Active</span>
          </div>
          <div className="flex items-center justify-between py-[1px]">
            <span className="text-[10px] text-gray-400">Session</span>
            <span className="text-[9px] text-gray-300">24h timeout, 1 session</span>
          </div>
          <div className="flex items-center justify-between py-[1px]">
            <span className="text-[10px] text-gray-400">Last Login</span>
            <span className="text-[9px] text-gray-500">2026-03-01 06:30</span>
          </div>
          <button className="text-[9px] text-[#00D9FF] hover:text-cyan-300 mt-0.5">[Revoke All]</button>
        </SectionCard>

        {/* 20. BACKUP & SYSTEM */}
        <SectionCard title="Backup & System">
          <div className="flex gap-2 mb-1">
            <button onClick={onExport} className="text-[9px] text-[#00D9FF] hover:text-cyan-300">[Export JSON]</button>
            <button onClick={() => importRef.current?.click()} className="text-[9px] text-[#00D9FF] hover:text-cyan-300">[Import JSON]</button>
          </div>
          <MiniField label="Last Backup" value={get("system", "lastBackup", "2026-02-28 18:30")} onChange={(e) => updateField("system", "lastBackup", e.target.value)} />
          <MiniSelect label="Auto-Backup" value={get("system", "autoBackup", "Daily")} options={["Daily", "Weekly", "Manual"]} onChange={(e) => updateField("system", "autoBackup", e.target.value)} />
          <MiniField label="Location" value={get("system", "backupLocation", "/backups/")} onChange={(e) => updateField("system", "backupLocation", e.target.value)} />
          <div className="border-t border-gray-800/50 pt-1 mt-0.5 space-y-0.5 text-[9px] text-gray-500">
            <div>System Info: v0.9.2-alpha</div>
            <div>DB: DuckDB 0.9.x</div>
            <div>CPU: 12 cores</div>
            <div>RAM: 32GB</div>
            <div>GPU: RTX 4090 (Detected)</div>
          </div>
        </SectionCard>
      </div>

      {/* ROW 5: Appearance, Market Data, Performance, Audit Log, Strategy */}
      <div className="grid grid-cols-5 gap-2 mb-2">

        {/* 21. APPEARANCE */}
        <SectionCard title="Appearance">
          <div className="grid grid-cols-3 gap-2 mb-1">
            {[
              { key: "midnight", name: "Midnight Bloomberg", bg: "#0B0E14", surface: "#111827", accent: "#00D9FF" },
              { key: "classic", name: "Classic Dark", bg: "#1a1a2e", surface: "#16213e", accent: "#0f3460" },
              { key: "oled", name: "OLED Black", bg: "#000000", surface: "#0a0a0a", accent: "#00D9FF" },
            ].map((theme) => (
              <button
                key={theme.key}
                onClick={() => updateField("appearance", "theme", theme.key)}
                className={`flex flex-col items-center gap-1 p-2 border-2 rounded-md hover:border-[#00D9FF]/50 transition-all ${
                  get("appearance", "theme", "oled") === theme.key ? "border-emerald-500 ring-1 ring-emerald-500/30" : "border-gray-700"
                }`}
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
          <MiniSelect label="Density" value={get("appearance", "density", "Ultra Dense")} options={["Ultra Dense", "Compact", "Comfortable"]} onChange={(e) => updateField("appearance", "density", e.target.value)} />
          <MiniSelect label="Charts" value={get("appearance", "charts", "Lightweight")} options={["Lightweight", "Standard", "Heavy"]} onChange={(e) => updateField("appearance", "charts", e.target.value)} />
          <MiniSelect label="Font" value={get("appearance", "fontSize", "10px")} options={["9px", "10px", "12px", "14px"]} onChange={(e) => updateField("appearance", "fontSize", e.target.value)} />
        </SectionCard>

        {/* 22. MARKET DATA */}
        <SectionCard title="Market Data">
          <MiniField label="Timeframe" value={get("dataSources", "timeframe", 10)} type="number" onChange={(e) => updateField("dataSources", "timeframe", Number(e.target.value))} />
          <MiniField label="Bars" value={get("dataSources", "bars", 200)} type="number" onChange={(e) => updateField("dataSources", "bars", Number(e.target.value))} />
          <MiniField label="Update" value={get("dataSources", "updateFrequency", "1s")} onChange={(e) => updateField("dataSources", "updateFrequency", e.target.value)} />
          <MiniToggle label="Pre-market" checked={!!get("trading", "preMarket", true)} onChange={(v) => updateField("trading", "preMarket", v)} />
          <MiniToggle label="After-hours" checked={!!get("trading", "afterHoursEnabled", true)} onChange={(v) => updateField("trading", "afterHoursEnabled", v)} />
          <MiniSelect label="Volume" value={get("dataSources", "volumeDisplay", "Bars + MA")} options={["Bars", "Bars + MA", "None"]} onChange={(e) => updateField("dataSources", "volumeDisplay", e.target.value)} />
        </SectionCard>

        {/* 23. PERFORMANCE */}
        <SectionCard title="Performance">
          <MiniToggle label="Track P&L" checked={!!get("performance", "trackPnl", true)} onChange={(v) => updateField("performance", "trackPnl", v)} />
          <MiniToggle label="Daily Stats" checked={!!get("performance", "dailyStats", true)} onChange={(v) => updateField("performance", "dailyStats", v)} />
          <MiniSelect label="Metrics" value={get("performance", "metrics", "Sharpe, Sortino")} options={["Sharpe, Sortino", "Max DD", "Win Rate"]} onChange={(e) => updateField("performance", "metrics", e.target.value)} />
          <MiniField label="Benchmark" value={get("performance", "benchmark", "SPY")} onChange={(e) => updateField("performance", "benchmark", e.target.value)} />
          <MiniSelect label="Tax" value={get("performance", "taxMethod", "FIFO")} options={["FIFO", "LIFO", "Specific ID"]} onChange={(e) => updateField("performance", "taxMethod", e.target.value)} />
          <MiniSelect label="Window" value={get("performance", "window", "YTD, 1M, 3M")} options={["YTD", "1M", "3M", "YTD, 1M, 3M"]} onChange={(e) => updateField("performance", "window", e.target.value)} />
          <MiniSelect label="Export" value={get("performance", "exportFormat", "CSV, JSON")} options={["CSV", "JSON", "CSV, JSON"]} onChange={(e) => updateField("performance", "exportFormat", e.target.value)} />
        </SectionCard>

        {/* 24. AUDIT LOG */}
        <SectionCard title="Audit Log">
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
                {[
                  { time: "03-01 06:50", cat: "CFG", actor: "Espen", event: "Paper Mode" },
                  { time: "02-28 18:30", cat: "SEC", actor: "Espen", event: "Login 104.x" },
                  { time: "02-28 15:05", cat: "RSK", actor: "Auto", event: "VIX Halt" },
                  { time: "02-27 11:20", cat: "CFG", actor: "Espen", event: "API Keys" },
                  { time: "02-27 09:15", cat: "SYS", actor: "OClaw", event: "WebSocket" },
                ].map((row, i) => (
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
          <button
            onClick={() => setShowFullLog(!showFullLog)}
            className="mt-1 text-[9px] text-[#00D9FF] hover:text-cyan-300"
          >
            [View Full Log]
          </button>
        </SectionCard>

        {/* 25. STRATEGY */}
        <SectionCard title="Strategy">
          <MiniToggle label="Adaptive" checked={!!get("strategy", "adaptive", true)} onChange={(v) => updateField("strategy", "adaptive", v)} />
          <div className="flex items-center justify-between py-[1px]">
            <span className="text-[10px] text-gray-400">Regime Switch</span>
            <span className="text-[9px] text-gray-300">Bull, Bear, Neutral</span>
          </div>
          <MiniField label="Min Prob" value={get("strategy", "minProb", 0.65)} type="number" step="0.01" onChange={(e) => updateField("strategy", "minProb", parseFloat(e.target.value))} />
          <MiniSelect label="Override" value={get("strategy", "override", "None")} options={["None", "Bull", "Bear", "Neutral"]} onChange={(e) => updateField("strategy", "override", e.target.value)} />
          <MiniToggle label="Momentum" checked={!!get("strategy", "momentum", true)} onChange={(v) => updateField("strategy", "momentum", v)} />
          <MiniToggle label="Mean Reversion" checked={!!get("strategy", "meanReversion", true)} onChange={(v) => updateField("strategy", "meanReversion", v)} />
          <MiniToggle label="Range" checked={!!get("strategy", "range", true)} onChange={(v) => updateField("strategy", "range", v)} />
        </SectionCard>
      </div>

      {/* FOOTER BAR */}
      <div className="flex items-center justify-between mt-2 pt-2 border-t border-gray-800/50">
        <div className="flex gap-3">
          <button onClick={onExport} className="text-[10px] text-[#00D9FF] hover:text-cyan-300">
            [Export Settings]
          </button>
          <button onClick={() => importRef.current?.click()} className="text-[10px] text-[#00D9FF] hover:text-cyan-300">
            [Import Settings]
          </button>
          <button
            onClick={() => { onReset("trading"); onReset("risk"); onReset("ml"); onReset("agents"); }}
            className="text-[10px] text-[#00D9FF] hover:text-cyan-300"
          >
            [Reset Defaults]
          </button>
        </div>
        <button
          onClick={async () => { try { await saveAllSettings(); toast.success("All settings saved", TOAST_CFG); } catch { toast.error("Failed to save settings", TOAST_CFG); } }}
          disabled={saving}
          className="bg-[#00D9FF] hover:bg-[#00D9FF]/80 text-black font-bold text-[10px] px-5 py-1.5 rounded uppercase tracking-wider disabled:opacity-50 flex items-center gap-1.5"
        >
          <Star className="w-3 h-3 text-amber-500 fill-amber-500" />
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
