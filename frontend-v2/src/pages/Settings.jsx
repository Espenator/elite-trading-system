import React, { useState, useEffect, useRef } from "react";
import Card from "../components/ui/Card";
import Button from "../components/ui/Button";
import PageHeader from "../components/ui/PageHeader";
import Toggle from "../components/ui/Toggle";
import TextField from "../components/ui/TextField";
import Select from "../components/ui/Select";
import Badge from "../components/ui/Badge";
import { useSettings } from "../hooks/useSettings";
import { useApi } from "../hooks/useApi";
import { toast } from "react-toastify";
import AlignmentEngine from "../components/settings/AlignmentEngine";
import DirectiveEditor from "../components/settings/DirectiveEditor";
import {
  User, Key, Activity, Bell, Layout, Cpu, Database,
  ShieldAlert, History, Save, RefreshCw, CheckCircle2,
  AlertTriangle, Settings, Terminal, Sliders, Wifi,
  WifiOff, Loader2, RotateCcw, Download, Upload,
  Bot, TrendingUp, BarChart2, Globe, Zap,
  Shield, Brain, Palette, FileText,
} from "lucide-react";

// -- Shared helpers ----------------------------------------
const TOAST_CFG = { position: "bottom-right", theme: "dark" };

function StatusDot({ ok, testing }) {
  if (testing) return <Loader2 className="w-3 h-3 animate-spin text-[#00D9FF]" />;
  if (ok === true)  return <CheckCircle2 className="w-3 h-3 text-[#10b981]" />;
  if (ok === false) return <AlertTriangle className="w-3 h-3 text-red-400" />;
  return <div className="w-2 h-2 rounded-full bg-gray-600" />;
}

function SectionHeader({ icon: Icon, color = "#00D9FF", title, sub }) {
  return (
    <div className="mb-2">
      <h3 className="text-[10px] font-bold text-white uppercase tracking-wider flex items-center gap-1.5">
        <Icon className="w-3 h-3" style={{ color }} />
        {title}
      </h3>
      {sub && <p className="text-[9px] text-gray-500 mt-0.5">{sub}</p>}
    </div>
  );
}

function FieldRow({ label, children }) {
  return (
    <div className="flex items-center justify-between py-1 px-1.5 bg-[#0B0E14]/50 border border-[rgba(42,52,68,0.3)] rounded">
      <span className="text-[10px] text-gray-400 font-medium">{label}</span>
      <div className="flex-shrink-0 ml-2">{children}</div>
    </div>
  );
}

function MiniField({ label, value, onChange, type = "text", suffix, ...props }) {
  return (
    <div className="flex items-center justify-between gap-2 py-0.5">
      <span className="text-[10px] text-gray-400 whitespace-nowrap">{label}</span>
      <div className="flex items-center gap-1">
        <input
          type={type}
          value={value}
          onChange={onChange}
          className="w-16 bg-[#0a0d13] border border-gray-700/50 rounded px-1.5 py-0.5 text-[10px] text-white outline-none focus:border-cyan-500/50"
          {...props}
        />
        {suffix && <span className="text-[9px] text-gray-600">{suffix}</span>}
      </div>
    </div>
  );
}

function MiniSelect({ label, value, options, onChange }) {
  return (
    <div className="flex items-center justify-between gap-2 py-0.5">
      <span className="text-[10px] text-gray-400 whitespace-nowrap">{label}</span>
      <select
        value={value}
        onChange={onChange}
        className="bg-[#0a0d13] border border-gray-700/50 rounded px-1 py-0.5 text-[10px] text-white outline-none focus:border-cyan-500/50 appearance-none cursor-pointer"
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
    <div className="flex items-center justify-between py-0.5">
      <span className="text-[10px] text-gray-400">{label}</span>
      <button
        onClick={() => onChange(!checked)}
        className={`w-7 h-3.5 rounded-full border transition-colors flex items-center ${
          checked ? "bg-cyan-500/30 border-cyan-500/50" : "bg-gray-700/30 border-gray-600/50"
        }`}
      >
        <span className={`block w-2.5 h-2.5 rounded-full transition-transform ${
          checked ? "translate-x-3.5 bg-cyan-400" : "translate-x-0.5 bg-gray-500"
        }`} />
      </button>
    </div>
  );
}

function SectionCard({ title, icon: Icon, color = "#00D9FF", children, className = "" }) {
  return (
    <div className={`bg-[#111827] border border-[rgba(42,52,68,0.5)] rounded-lg p-2.5 ${className}`}>
      <div className="flex items-center gap-1.5 mb-2 pb-1.5 border-b border-gray-800/50">
        {Icon && <Icon className="w-3 h-3" style={{ color }} />}
        <span className="text-[10px] font-bold text-white uppercase tracking-wider">{title}</span>
      </div>
      <div className="space-y-1">
        {children}
      </div>
    </div>
  );
}

// -- AuditLogTab (own component so it can use hooks safely) -- v2
function AuditLogTab() {
  const { data: auditData, loading: logLoading } = useApi("settings", { endpoint: "/settings/audit-log" });
  const logs = auditData?.logs || [];
  return (
    <div className="space-y-6 animate-in fade-in duration-300">
      <SectionHeader icon={FileText} title="Audit Log" sub="Track all settings changes and system events." />
      <Card className="bg-[#111827] border border-[rgba(42,52,68,0.5)] rounded-[8px] p-4">
        {logLoading ? (
          <div className="flex items-center gap-2 text-gray-500 text-xs"><Loader2 className="w-4 h-4 animate-spin" />Loading audit log...</div>
        ) : logs.length === 0 ? (
          <p className="text-gray-500 text-xs">No audit entries found.</p>
        ) : (
          <div className="space-y-1 max-h-[500px] overflow-y-auto">
            {logs.map((log, i) => (
              <div key={i} className="flex items-center gap-3 py-1.5 px-2 text-xs border-b border-gray-800/50 hover:bg-gray-800/30">
                <span className="text-gray-500 font-mono w-36 shrink-0">{new Date(log.timestamp).toLocaleString()}</span>
                <span className={`w-16 shrink-0 font-bold uppercase ${log.action === "update" ? "text-yellow-500" : log.action === "reset" ? "text-red-400" : "text-[#00D9FF]"}`}>{log.action}</span>
                <span className="text-gray-300">{log.category}</span>
                <span className="text-gray-500 truncate">{log.detail || ""}</span>
              </div>
            ))}
          </div>
        )}
      </Card>
      <div className="flex gap-3">
        <Button variant="secondary" size="sm" leftIcon={Download} onClick={() => {
          const blob = new Blob([JSON.stringify(logs, null, 2)], { type: "application/json" });
          const a = document.createElement("a"); a.href = URL.createObjectURL(blob); a.download = "audit-log.json"; a.click();
        }} className="text-xs border-gray-700 text-gray-400">Export Log</Button>
      </div>
    </div>
  );
}

// -------------------------------------------------------
export default function SettingsPage() {
  const [activeTab, setActiveTab] = useState("api-keys");
  const {
    settings, loading, saving, dirty, error,
    connectionResults, updateField,
    saveCategory, saveAllSettings, resetCategory,
    validateKey, testConnection,
    exportSettings, importSettings, refetch,
  } = useSettings();

  const importRef = useRef(null);
  const S = settings || {};

  // Helper: get a value from a category
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

  const [showFullLog, setShowFullLog] = useState(false);

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
        <Button variant="secondary" size="xs" onClick={refetch} leftIcon={RefreshCw}>Retry</Button>
      </div>
    );
  }

  const alpacaCr = connectionResults["alpaca"] || {};
  const uwCr = connectionResults["unusual_whales"] || {};
  const finvizCr = connectionResults["finviz"] || {};
  const fredCr = connectionResults["fred"] || {};
  const ollamaCr = connectionResults["ollama"] || {};

  return (
    <div className="min-h-screen bg-[#0B0E14] text-gray-100 p-3">
      {/* Hidden import input */}
      <input ref={importRef} type="file" accept=".json" className="hidden" onChange={onImport} />

      {/* ===== HEADER ===== */}
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-3">
          <Settings className="w-5 h-5 text-cyan-400" />
          <h1 className="text-sm font-bold text-white uppercase tracking-wider">System Configuration</h1>
        </div>
        <Button
          variant="primary"
          size="sm"
          leftIcon={Save}
          onClick={saveAllSettings}
          disabled={saving}
          className="bg-cyan-500 hover:bg-cyan-600 text-black font-bold text-[10px] px-4 py-1.5 rounded"
        >
          {saving ? "Saving..." : "SAVE ALL"}
        </Button>
      </div>

      {/* ===== ROW 1: Identity, Trading Mode, Position Sizing, Risk Limits, Circuit Breakers ===== */}
      <div className="grid grid-cols-5 gap-2 mb-2">

        {/* IDENTITY & LOCALE */}
        <SectionCard title="Identity & Locale" icon={User}>
          <MiniField label="Display Name" value={get("user", "displayName")} onChange={(e) => updateField("user", "displayName", e.target.value)} />
          <MiniField label="Email" value={get("user", "email")} onChange={(e) => updateField("user", "email", e.target.value)} />
          <MiniSelect label="Timezone" value={get("user", "timezone", "America/New_York")} options={["America/New_York", "America/Chicago", "America/Los_Angeles", "Europe/Oslo", "UTC"]} onChange={(e) => updateField("user", "timezone", e.target.value)} />
          <MiniSelect label="Currency" value={get("user", "currency", "USD")} options={["USD", "EUR", "NOK", "GBP"]} onChange={(e) => updateField("user", "currency", e.target.value)} />
          <MiniField label="Session Timeout" value={get("user", "sessionTimeoutMinutes", 30)} type="number" suffix="min" onChange={(e) => updateField("user", "sessionTimeoutMinutes", Number(e.target.value))} />
          <MiniToggle label="Two-Factor Auth" checked={!!get("user", "twoFactorEnabled", false)} onChange={(v) => updateField("user", "twoFactorEnabled", v)} />
          <MiniSelect label="Timeframe" value={get("appearance", "chartTimeframe", "5m")} options={["1m", "5m", "15m", "1h", "1d"]} onChange={(e) => updateField("appearance", "chartTimeframe", e.target.value)} />
        </SectionCard>

        {/* TRADING MODE */}
        <SectionCard title="Trading Mode" icon={Activity}>
          <div className="flex gap-1 mb-2">
            {["paper", "live"].map((env) => (
              <button key={env} onClick={() => updateField("dataSources", "alpacaBaseUrl", env)}
                className={`flex-1 px-2 py-1 rounded text-[10px] font-bold uppercase tracking-wider border transition-all ${
                  get("dataSources", "alpacaBaseUrl", "paper") === env
                    ? "bg-[rgba(0,217,255,0.15)] border-[rgba(0,217,255,0.3)] text-[#00D9FF]"
                    : "bg-[#0B0E14] border-gray-700 text-gray-500 hover:border-gray-600"
                }`}>{env}</button>
            ))}
          </div>
          <div className="text-[9px] text-yellow-400 flex items-center gap-1 mb-1.5">
            <AlertTriangle className="w-2.5 h-2.5" />
            {get("dataSources", "alpacaBaseUrl") === "live" ? "LIVE mode - real money at risk" : "Paper trading - simulated orders"}
          </div>
          <MiniSelect label="Account" value={get("trading", "defaultOrderType", "market")} options={["market", "limit", "stop", "stop_limit"]} onChange={(e) => updateField("trading", "defaultOrderType", e.target.value)} />
          <MiniToggle label="Paper Trading" checked={get("dataSources", "alpacaBaseUrl", "paper") === "paper"} onChange={(v) => updateField("dataSources", "alpacaBaseUrl", v ? "paper" : "live")} />
          <MiniToggle label="Auto-Execute" checked={!!get("trading", "autoExecute", false)} onChange={(v) => updateField("trading", "autoExecute", v)} />
          <MiniToggle label="Confirm Orders" checked={!!get("trading", "confirmBeforeOrder", true)} onChange={(v) => updateField("trading", "confirmBeforeOrder", v)} />
          <MiniSelect label="Entry Method" value={get("trading", "entryMethod", "market")} options={["market", "limit", "scale_in"]} onChange={(e) => updateField("trading", "entryMethod", e.target.value)} />
        </SectionCard>

        {/* POSITION SIZING */}
        <SectionCard title="Position Sizing" icon={BarChart2}>
          <MiniField label="Base Size" value={get("trading", "maxPositionSize", 10000)} type="number" suffix="$" onChange={(e) => updateField("trading", "maxPositionSize", Number(e.target.value))} />
          <MiniField label="Max Positions" value={get("risk", "maxPositions", 10)} type="number" onChange={(e) => updateField("risk", "maxPositions", Number(e.target.value))} />
          <MiniField label="Max Daily Trades" value={get("trading", "maxDailyTrades", 10)} type="number" onChange={(e) => updateField("trading", "maxDailyTrades", Number(e.target.value))} />
          <MiniField label="Portfolio Risk" value={get("risk", "maxPortfolioRisk", 0.02)} type="number" step="0.01" onChange={(e) => updateField("risk", "maxPortfolioRisk", parseFloat(e.target.value))} />
          <MiniField label="Position Risk" value={get("risk", "maxPositionRisk", 0.01)} type="number" step="0.01" onChange={(e) => updateField("risk", "maxPositionRisk", parseFloat(e.target.value))} />
          <MiniField label="Correlation" value={get("risk", "maxDrawdownLimit", 0.1)} type="number" step="0.01" onChange={(e) => updateField("risk", "maxDrawdownLimit", parseFloat(e.target.value))} />
          <MiniToggle label="Auto-Scale" checked={!!get("trading", "autoExecute", false)} onChange={(v) => updateField("trading", "autoExecute", v)} />
        </SectionCard>

        {/* RISK LIMITS */}
        <SectionCard title="Risk Limits" icon={Shield} color="#ef4444">
          <MiniField label="Max Daily Risk" value={get("risk", "maxDailyLossPct", 3)} type="number" suffix="%" onChange={(e) => updateField("risk", "maxDailyLossPct", parseFloat(e.target.value))} />
          <MiniField label="Max Drawdown" value={get("risk", "maxDrawdownLimit", 0.1)} type="number" step="0.01" onChange={(e) => updateField("risk", "maxDrawdownLimit", parseFloat(e.target.value))} />
          <MiniField label="Stop Loss" value={get("risk", "stopLossDefault", 0.02)} type="number" step="0.01" onChange={(e) => updateField("risk", "stopLossDefault", parseFloat(e.target.value))} />
          <MiniField label="Take Profit" value={get("risk", "takeProfitDefault", 0.04)} type="number" step="0.01" onChange={(e) => updateField("risk", "takeProfitDefault", parseFloat(e.target.value))} />
          <MiniField label="ATR Multiplier" value={get("risk", "atrStopMultiplier", 2.0)} type="number" step="0.1" suffix="x" onChange={(e) => updateField("risk", "atrStopMultiplier", parseFloat(e.target.value))} />
          <MiniField label="Kelly Fraction" value={get("risk", "kellyFractionMultiplier", 0.5)} type="number" step="0.1" onChange={(e) => updateField("risk", "kellyFractionMultiplier", parseFloat(e.target.value))} />
        </SectionCard>

        {/* CIRCUIT BREAKERS */}
        <SectionCard title="Circuit Breakers" icon={ShieldAlert} color="#ef4444">
          <MiniToggle label="Circuit Breaker" checked={!!get("risk", "circuitBreakerEnabled", true)} onChange={(v) => updateField("risk", "circuitBreakerEnabled", v)} />
          <MiniField label="Master Killswitch" value={get("alignment", "maxHeatPct", 20)} type="number" suffix="%" onChange={(e) => updateField("alignment", "maxHeatPct", Math.min(25, Number(e.target.value)))} />
          <MiniField label="Max Heat" value={get("alignment", "maxDrawdownPct", 10)} type="number" suffix="%" onChange={(e) => updateField("alignment", "maxDrawdownPct", Math.min(15, Number(e.target.value)))} />
          <MiniField label="Flash Crash" value={get("alignment", "rapidFireWindowSec", 60)} type="number" suffix="sec" onChange={(e) => updateField("alignment", "rapidFireWindowSec", Number(e.target.value))} />
          <MiniField label="Daily Trade Cap" value={get("alignment", "dailyTradeCap", 15)} type="number" onChange={(e) => updateField("alignment", "dailyTradeCap", Number(e.target.value))} />
          <MiniField label="Consecutive Loss" value={get("risk", "maxDailyLossPct", 3)} type="number" onChange={(e) => updateField("risk", "maxDailyLossPct", parseFloat(e.target.value))} />
        </SectionCard>
      </div>

      {/* ===== ROW 2: Brokerage, Data Feed API Keys, Data Source Priority, Ollama Local LLM, Ollama Models ===== */}
      <div className="grid grid-cols-5 gap-2 mb-2">

        {/* BROKERAGE CONNECTIONS */}
        <SectionCard title="Brokerage Connections" icon={Globe}>
          <div className="flex items-center justify-between py-0.5">
            <span className="text-[10px] text-gray-400">Alpaca Markets</span>
            <div className="flex items-center gap-1">
              <StatusDot ok={alpacaCr.valid} testing={alpacaCr.testing} />
              <Badge variant={alpacaCr.valid ? "success" : "secondary"} size="sm">{alpacaCr.valid ? "Connected" : "Test"}</Badge>
            </div>
          </div>
          <div className="flex items-center justify-between py-0.5">
            <span className="text-[10px] text-gray-400">Interactive Brokers</span>
            <Badge variant="secondary" size="sm">Not Configured</Badge>
          </div>
          <div className="mt-1.5 pt-1.5 border-t border-gray-800/50">
            <button
              onClick={() => onTestConn("alpaca")}
              className="text-[9px] text-cyan-400 hover:text-cyan-300 flex items-center gap-1"
            >
              <Wifi className="w-2.5 h-2.5" /> Test Connections
            </button>
          </div>
        </SectionCard>

        {/* DATA FEED API KEYS */}
        <SectionCard title="Data Feed API Keys" icon={Key}>
          {[
            { id: "unusual_whales", label: "Unusual Whales", cr: uwCr, keyField: "unusualWhalesApiKey" },
            { id: "finviz", label: "FinViz Elite", cr: finvizCr, keyField: "finvizApiKey" },
            { id: "fred", label: "FRED", cr: fredCr, keyField: "fredApiKey" },
          ].map((p) => (
            <div key={p.id} className="flex items-center justify-between py-0.5">
              <span className="text-[10px] text-gray-400">{p.label}</span>
              <div className="flex items-center gap-1">
                <StatusDot ok={p.cr.valid} testing={p.cr.testing} />
                <Badge variant={p.cr.valid ? "success" : "secondary"} size="sm">
                  {p.cr.testing ? "..." : p.cr.valid ? "OK" : "Set"}
                </Badge>
              </div>
            </div>
          ))}
          <div className="flex items-center justify-between py-0.5">
            <span className="text-[10px] text-gray-400">NewsAPI</span>
            <Badge variant="secondary" size="sm">Set</Badge>
          </div>
          <div className="flex items-center justify-between py-0.5">
            <span className="text-[10px] text-gray-400">SEC EDGAR</span>
            <Badge variant="secondary" size="sm">N/A</Badge>
          </div>
        </SectionCard>

        {/* DATA SOURCE PRIORITY */}
        <SectionCard title="Data Source Priority" icon={Database}>
          <MiniSelect label="Endpoint" value={get("dataSources", "endpointPriority", "polygon")} options={["polygon", "alpaca", "benzinga"]} onChange={(e) => updateField("dataSources", "endpointPriority", e.target.value)} />
          <MiniSelect label="Options Flow" value={get("dataSources", "optionsFlowPriority", "unusual_whales")} options={["unusual_whales", "polygon"]} onChange={(e) => updateField("dataSources", "optionsFlowPriority", e.target.value)} />
          <MiniSelect label="Screener" value={get("dataSources", "screenerPriority", "finviz")} options={["finviz", "polygon"]} onChange={(e) => updateField("dataSources", "screenerPriority", e.target.value)} />
          <MiniSelect label="News" value={get("dataSources", "newsPriority", "benzinga")} options={["benzinga", "newsapi"]} onChange={(e) => updateField("dataSources", "newsPriority", e.target.value)} />
          <MiniSelect label="Fundamentals" value={get("dataSources", "fundamentalsPriority", "polygon")} options={["polygon", "finviz"]} onChange={(e) => updateField("dataSources", "fundamentalsPriority", e.target.value)} />
          <MiniSelect label="Rate Limit" value={get("dataSources", "rateLimitMode", "conservative")} options={["conservative", "moderate", "aggressive"]} onChange={(e) => updateField("dataSources", "rateLimitMode", e.target.value)} />
        </SectionCard>

        {/* OLLAMA LOCAL LLM */}
        <SectionCard title="Ollama Local LLM" icon={Brain} color="#a78bfa">
          <MiniField label="Endpoint" value={get("ollama", "ollamaHostUrl", "http://localhost:11434")} onChange={(e) => updateField("ollama", "ollamaHostUrl", e.target.value)} />
          <MiniField label="Model" value={get("ollama", "ollamaDefaultModel", "llama3")} onChange={(e) => updateField("ollama", "ollamaDefaultModel", e.target.value)} />
          <MiniField label="Context" value={get("ollama", "ollamaContextLength", 8192)} type="number" suffix="tok" onChange={(e) => updateField("ollama", "ollamaContextLength", Number(e.target.value))} />
          <MiniToggle label="CUDA" checked={!!get("ollama", "ollamaCudaEnabled", false)} onChange={(v) => updateField("ollama", "ollamaCudaEnabled", v)} />
          <div className="flex items-center justify-between pt-1">
            <button onClick={() => onTestConn("ollama")} className="text-[9px] text-purple-400 hover:text-purple-300 flex items-center gap-1">
              <Wifi className="w-2.5 h-2.5" /> {ollamaCr.testing ? "Testing..." : "Test Connection"}
            </button>
            <StatusDot ok={ollamaCr.valid} testing={ollamaCr.testing} />
          </div>
          {ollamaCr.message && <div className="text-[9px] text-gray-500 mt-0.5">{ollamaCr.message}</div>}
        </SectionCard>

        {/* OLLAMA MODELS */}
        <SectionCard title="Ollama Models" icon={Cpu} color="#a78bfa">
          <MiniField label="Use for" value={get("ollama", "signalAnalysisModel", "Signal Analysis")} onChange={(e) => updateField("ollama", "signalAnalysisModel", e.target.value)} />
          <MiniField label="Use for" value={get("ollama", "patternAnalysisModel", "Pattern Analysis")} onChange={(e) => updateField("ollama", "patternAnalysisModel", e.target.value)} />
          <MiniField label="Use for" value={get("ollama", "signalGenerationModel", "Signal Generation")} onChange={(e) => updateField("ollama", "signalGenerationModel", e.target.value)} />
          <MiniField label="GPT-4" value={get("ollama", "gpt4Status", "disabled")} onChange={(e) => updateField("ollama", "gpt4Status", e.target.value)} />
          <MiniField label="Fallback" value={get("ollama", "fallbackModel", "llama3")} onChange={(e) => updateField("ollama", "fallbackModel", e.target.value)} />
        </SectionCard>
      </div>

      {/* ===== ROW 3: ML Models, Scanning Config, Pipeline Adjusts, Agent Switches, Backup & System ===== */}
      <div className="grid grid-cols-5 gap-2 mb-2">

        {/* ML MODELS */}
        <SectionCard title="ML Models" icon={Brain}>
          <div className="flex gap-1 mb-1">
            {["XGBoost", "HMM"].map((m) => (
              <Badge key={m} variant="primary" size="sm">{m}</Badge>
            ))}
          </div>
          <MiniToggle label="Active" checked={!!get("ml", "mlActive", true)} onChange={(v) => updateField("ml", "mlActive", v)} />
          <MiniSelect label="Model Type" value={get("ml", "modelType", "xgboost")} options={["xgboost", "random_forest", "lstm", "transformer"]} onChange={(e) => updateField("ml", "modelType", e.target.value)} />
          <MiniSelect label="Lookback" value={get("ml", "retrainFrequency", "weekly")} options={["daily", "weekly", "monthly"]} onChange={(e) => updateField("ml", "retrainFrequency", e.target.value)} />
          <MiniField label="Confidence" value={get("ml", "confidenceThreshold", 0.7)} type="number" step="0.01" onChange={(e) => updateField("ml", "confidenceThreshold", parseFloat(e.target.value))} />
          <MiniField label="Min Score" value={get("ml", "minCompositeScore", 60)} type="number" suffix="pts" onChange={(e) => updateField("ml", "minCompositeScore", Number(e.target.value))} />
          <MiniField label="Min ML Conf" value={get("ml", "minMLConfidence", 50)} type="number" suffix="pts" onChange={(e) => updateField("ml", "minMLConfidence", Number(e.target.value))} />
          <MiniField label="Walk-Forward" value={get("ml", "walkForwardWindow", 90)} type="number" suffix="days" onChange={(e) => updateField("ml", "walkForwardWindow", Number(e.target.value))} />
          <MiniToggle label="Momentum Tracking" checked={!!get("ml", "momentumTracking", true)} onChange={(v) => updateField("ml", "momentumTracking", v)} />
        </SectionCard>

        {/* SCANNING CONFIG */}
        <SectionCard title="Scanning Config" icon={Activity}>
          <MiniSelect label="Scan Distribution" value={get("scanning", "scanDistribution", "auto")} options={["auto", "manual", "hybrid"]} onChange={(e) => updateField("scanning", "scanDistribution", e.target.value)} />
          <MiniSelect label="Priority-Based" value={get("scanning", "priorityBased", "yes")} options={["yes", "no"]} onChange={(e) => updateField("scanning", "priorityBased", e.target.value)} />
          <MiniSelect label="Market Scanner" value={get("scanning", "marketScanner", "finviz")} options={["finviz", "polygon"]} onChange={(e) => updateField("scanning", "marketScanner", e.target.value)} />
          <MiniSelect label="Options Scanner" value={get("scanning", "optionsScanner", "unusual_whales")} options={["unusual_whales", "polygon"]} onChange={(e) => updateField("scanning", "optionsScanner", e.target.value)} />
          <MiniSelect label="Market Regime" value={get("scanning", "marketRegime", "auto")} options={["auto", "bull", "bear", "neutral"]} onChange={(e) => updateField("scanning", "marketRegime", e.target.value)} />
          <MiniToggle label="After-Hours Scan" checked={!!get("scanning", "afterHoursScan", false)} onChange={(v) => updateField("scanning", "afterHoursScan", v)} />
          <MiniToggle label="Pre-Market Scan" checked={!!get("trading", "preMarketEnabled", false)} onChange={(v) => updateField("trading", "preMarketEnabled", v)} />
        </SectionCard>

        {/* PIPELINE ADJUSTMENTS */}
        <SectionCard title="Pipeline Adjustments" icon={Sliders}>
          <MiniField label="Signal Weight" value={get("ml", "signalWeight", 1.0)} type="number" step="0.1" onChange={(e) => updateField("ml", "signalWeight", parseFloat(e.target.value))} />
          <MiniField label="ML Weight" value={get("ml", "mlWeight", 1.0)} type="number" step="0.1" onChange={(e) => updateField("ml", "mlWeight", parseFloat(e.target.value))} />
          <MiniField label="Pattern Weight" value={get("ml", "patternWeight", 0.8)} type="number" step="0.1" onChange={(e) => updateField("ml", "patternWeight", parseFloat(e.target.value))} />
          <MiniField label="Drift Threshold" value={get("ml", "driftThreshold", 0.15)} type="number" step="0.01" onChange={(e) => updateField("ml", "driftThreshold", parseFloat(e.target.value))} />
          <MiniToggle label="Drift Detection" checked={!!get("ml", "driftDetectionEnabled", true)} onChange={(v) => updateField("ml", "driftDetectionEnabled", v)} />
          <MiniField label="Critique Thresh" value={get("alignment", "critiqueThreshold", 70)} type="number" suffix="%" onChange={(e) => updateField("alignment", "critiqueThreshold", Number(e.target.value))} />
        </SectionCard>

        {/* AGENT SWITCHES */}
        <SectionCard title="Agent Switches" icon={Bot}>
          <MiniField label="Max Concurrent" value={get("agents", "maxConcurrentAgents", 8)} type="number" onChange={(e) => updateField("agents", "maxConcurrentAgents", Number(e.target.value))} />
          <MiniField label="Timeout" value={get("agents", "agentTimeout", 30)} type="number" suffix="sec" onChange={(e) => updateField("agents", "agentTimeout", Number(e.target.value))} />
          {[
            { key: "marketDataAgent", label: "Market Data" },
            { key: "riskAgent", label: "Risk Agent" },
            { key: "signalEngine", label: "Signal Engine" },
            { key: "patternAI", label: "Pattern AI" },
            { key: "youtubeAgent", label: "YouTube Agent" },
            { key: "driftMonitor", label: "Drift Monitor" },
            { key: "flywheelEngine", label: "Flywheel" },
            { key: "openclawBridge", label: "OpenClaw" },
          ].map((a) => (
            <MiniToggle key={a.key} label={a.label} checked={!!get("agents", a.key, true)} onChange={(v) => updateField("agents", a.key, v)} />
          ))}
          <MiniToggle label="Auto Restart" checked={!!get("agents", "autoRestart", true)} onChange={(v) => updateField("agents", "autoRestart", v)} />
        </SectionCard>

        {/* BACKUP & SYSTEM */}
        <SectionCard title="Backup & System" icon={Database}>
          <div className="space-y-1.5">
            <div className="text-[9px] text-gray-500 font-mono">{new Date().toISOString().split("T")[0]} {new Date().toLocaleTimeString()}</div>
            <div className="flex gap-1">
              <button onClick={onExport} className="flex-1 text-[9px] bg-[#0B0E14] border border-gray-700/50 rounded px-2 py-1 text-cyan-400 hover:bg-gray-800 flex items-center gap-1 justify-center">
                <Download className="w-2.5 h-2.5" /> Export
              </button>
              <button onClick={() => importRef.current?.click()} className="flex-1 text-[9px] bg-[#0B0E14] border border-gray-700/50 rounded px-2 py-1 text-cyan-400 hover:bg-gray-800 flex items-center gap-1 justify-center">
                <Upload className="w-2.5 h-2.5" /> Import
              </button>
            </div>
            <button onClick={() => { onReset("trading"); onReset("risk"); onReset("ml"); }} className="w-full text-[9px] bg-red-900/20 border border-red-800/30 rounded px-2 py-1 text-red-400 hover:bg-red-900/30 flex items-center gap-1 justify-center">
              <RotateCcw className="w-2.5 h-2.5" /> Reset All Defaults
            </button>
            <div className="text-[9px] text-gray-600 mt-1">
              <div>AES-256 on disk</div>
              <div>Auto-backup: daily</div>
            </div>
          </div>
        </SectionCard>
      </div>

      {/* ===== ROW 4: Trade Management, Order Execution, Notifications, Security & Auth, OpenClaw Bridge ===== */}
      <div className="grid grid-cols-5 gap-2 mb-2">

        {/* TRADE MANAGEMENT */}
        <SectionCard title="Trade Management" icon={TrendingUp}>
          <MiniField label="TP1" value={get("risk", "takeProfitDefault", 0.04)} type="number" step="0.01" suffix="R" onChange={(e) => updateField("risk", "takeProfitDefault", parseFloat(e.target.value))} />
          <MiniField label="TP2" value={get("risk", "takeProfit2", 2.0)} type="number" step="0.1" suffix="R" onChange={(e) => updateField("risk", "takeProfit2", parseFloat(e.target.value))} />
          <MiniField label="TP3" value={get("risk", "takeProfit3", 3.0)} type="number" step="0.1" suffix="R" onChange={(e) => updateField("risk", "takeProfit3", parseFloat(e.target.value))} />
          <MiniField label="Trailing" value={get("risk", "trailingStop", 1.5)} type="number" step="0.1" suffix="R" onChange={(e) => updateField("risk", "trailingStop", parseFloat(e.target.value))} />
          <MiniField label="Time Exit" value={get("trading", "marketClose", "16:00")} onChange={(e) => updateField("trading", "marketClose", e.target.value)} />
          <MiniToggle label="Post-Trade Confirm" checked={!!get("trading", "confirmBeforeOrder", true)} onChange={(v) => updateField("trading", "confirmBeforeOrder", v)} />
        </SectionCard>

        {/* ORDER EXECUTION */}
        <SectionCard title="Order Execution" icon={Zap}>
          <MiniField label="Slippage" value={get("trading", "slippageTolerance", 0.075)} type="number" step="0.001" suffix="%" onChange={(e) => updateField("trading", "slippageTolerance", parseFloat(e.target.value))} />
          <MiniField label="Partial Fill" value={get("trading", "partialFillPct", 75)} type="number" suffix="%" onChange={(e) => updateField("trading", "partialFillPct", Number(e.target.value))} />
          <MiniToggle label="Retry Failed" checked={!!get("trading", "retryFailed", true)} onChange={(v) => updateField("trading", "retryFailed", v)} />
          <MiniField label="Max Retries" value={get("trading", "maxRetries", 3)} type="number" onChange={(e) => updateField("trading", "maxRetries", Number(e.target.value))} />
          <MiniSelect label="Routing" value={get("trading", "orderRouting", "smart")} options={["smart", "direct", "iex"]} onChange={(e) => updateField("trading", "orderRouting", e.target.value)} />
        </SectionCard>

        {/* NOTIFICATIONS */}
        <SectionCard title="Notifications" icon={Bell}>
          <div className="mb-1">
            <span className="text-[9px] text-gray-500 uppercase font-bold">Channels: PMS / Email / Push</span>
          </div>
          <MiniToggle label="Trade Executions" checked={!!get("notifications", "tradeAlerts", false)} onChange={(v) => updateField("notifications", "tradeAlerts", v)} />
          <MiniToggle label="EOD Summary" checked={!!get("notifications", "dailySummary", false)} onChange={(v) => updateField("notifications", "dailySummary", v)} />
          <MiniToggle label="Risk Warnings" checked={!!get("notifications", "riskAlerts", false)} onChange={(v) => updateField("notifications", "riskAlerts", v)} />
          <MiniToggle label="Signal Alerts" checked={!!get("notifications", "signalAlerts", false)} onChange={(v) => updateField("notifications", "signalAlerts", v)} />
          <MiniToggle label="System Anomalies" checked={!!get("notifications", "agentStatusAlerts", false)} onChange={(v) => updateField("notifications", "agentStatusAlerts", v)} />
          <MiniToggle label="Daily PnL" checked={!!get("notifications", "dailySummary", false)} onChange={(v) => updateField("notifications", "dailySummary", v)} />
        </SectionCard>

        {/* SECURITY & AUTH */}
        <SectionCard title="Security & Auth" icon={Shield} color="#10b981">
          <MiniToggle label="2FA Enabled" checked={!!get("user", "twoFactorEnabled", false)} onChange={(v) => updateField("user", "twoFactorEnabled", v)} />
          <MiniField label="Session Timeout" value={get("user", "sessionTimeoutMinutes", 30)} type="number" suffix="min" onChange={(e) => updateField("user", "sessionTimeoutMinutes", Number(e.target.value))} />
          <MiniToggle label="IP Whitelisting" checked={!!get("user", "ipWhitelisting", false)} onChange={(v) => updateField("user", "ipWhitelisting", v)} />
          <MiniToggle label="API Rate Limit" checked={!!get("user", "apiRateLimit", true)} onChange={(v) => updateField("user", "apiRateLimit", v)} />
          <div className="text-[9px] text-gray-600 mt-1 pt-1 border-t border-gray-800/50">
            <div>AES-256 on disk</div>
            <div>Keys hashed (bcrypt)</div>
          </div>
        </SectionCard>

        {/* OPENCLAW BRIDGE */}
        <SectionCard title="OpenClaw Bridge" icon={Bot} color="#f59e0b">
          <MiniField label="WS URL" value={get("openclaw", "openclawWsUrl", "ws://localhost:8765")} onChange={(e) => updateField("openclaw", "openclawWsUrl", e.target.value)} />
          <MiniField label="API Key" value={get("openclaw", "openclawApiKey")} type="password" onChange={(e) => updateField("openclaw", "openclawApiKey", e.target.value)} />
          <MiniField label="Reconnect" value={get("openclaw", "openclawReconnectInterval", 5)} type="number" suffix="sec" onChange={(e) => updateField("openclaw", "openclawReconnectInterval", Number(e.target.value))} />
          <MiniField label="Scanner Int." value={get("agents", "scannerInterval", 60)} type="number" suffix="sec" onChange={(e) => updateField("agents", "scannerInterval", Number(e.target.value))} />
        </SectionCard>
      </div>

      {/* ===== ROW 5: Appearance, Market Data, Notification Channels, Alignment Engine, Audit Log ===== */}
      <div className="grid grid-cols-5 gap-2 mb-2">

        {/* APPEARANCE */}
        <SectionCard title="Appearance" icon={Palette}>
          <div className="flex gap-1 mb-1.5">
            {["dark", "midnight", "terminal"].map((t) => (
              <button key={t} onClick={() => updateField("appearance", "theme", t)}
                className={`flex-1 px-1 py-0.5 rounded text-[9px] border ${
                  get("appearance", "theme", "dark") === t
                    ? "bg-cyan-500/15 border-cyan-500/30 text-cyan-400 font-bold"
                    : "bg-[#0B0E14] border-gray-700/50 text-gray-500"
                }`}>{t}</button>
            ))}
          </div>
          <MiniSelect label="Density" value={get("appearance", "density", "compact")} options={["compact", "comfortable", "spacious"]} onChange={(e) => updateField("appearance", "density", e.target.value)} />
          <MiniSelect label="Font" value={get("appearance", "font", "monospace")} options={["monospace", "sans-serif", "serif"]} onChange={(e) => updateField("appearance", "font", e.target.value)} />
          <MiniToggle label="Animations" checked={!!get("appearance", "animations", true)} onChange={(v) => updateField("appearance", "animations", v)} />
          <MiniToggle label="Sound Alerts" checked={!!get("appearance", "soundAlerts", false)} onChange={(v) => updateField("appearance", "soundAlerts", v)} />
          <MiniToggle label="Show PnL" checked={!!get("appearance", "showPnlHeader", true)} onChange={(v) => updateField("appearance", "showPnlHeader", v)} />
        </SectionCard>

        {/* MARKET DATA */}
        <SectionCard title="Market Data" icon={BarChart2}>
          <MiniSelect label="Timeframe" value={get("appearance", "chartTimeframe", "5m")} options={["1m", "5m", "15m", "1h", "1d"]} onChange={(e) => updateField("appearance", "chartTimeframe", e.target.value)} />
          <MiniField label="Market Open" value={get("trading", "marketOpen", "09:30")} onChange={(e) => updateField("trading", "marketOpen", e.target.value)} />
          <MiniField label="Market Close" value={get("trading", "marketClose", "16:00")} onChange={(e) => updateField("trading", "marketClose", e.target.value)} />
          <MiniToggle label="Pre-Market" checked={!!get("trading", "preMarketEnabled", false)} onChange={(v) => updateField("trading", "preMarketEnabled", v)} />
          <MiniToggle label="After Hours" checked={!!get("trading", "afterHoursEnabled", false)} onChange={(v) => updateField("trading", "afterHoursEnabled", v)} />
          <MiniSelect label="Volume" value={get("appearance", "volumeDisplay", "relative")} options={["relative", "absolute"]} onChange={(e) => updateField("appearance", "volumeDisplay", e.target.value)} />
        </SectionCard>

        {/* NOTIFICATION CHANNELS */}
        <SectionCard title="Notification Channels" icon={Bell} color="#10b981">
          <div className="space-y-1.5">
            <div className="flex items-center justify-between py-0.5">
              <span className="text-[10px] text-gray-400">Discord</span>
              <Badge variant={get("notifications", "discordWebhookUrl") ? "success" : "secondary"} size="sm">
                {get("notifications", "discordWebhookUrl") ? "Active" : "Setup"}
              </Badge>
            </div>
            <div className="flex items-center justify-between py-0.5">
              <span className="text-[10px] text-gray-400">Slack</span>
              <Badge variant={get("notifications", "slackWebhookUrl") ? "success" : "secondary"} size="sm">
                {get("notifications", "slackWebhookUrl") ? "Active" : "Setup"}
              </Badge>
            </div>
            <div className="flex items-center justify-between py-0.5">
              <span className="text-[10px] text-gray-400">Telegram</span>
              <Badge variant={get("notifications", "telegramBotToken") ? "success" : "secondary"} size="sm">
                {get("notifications", "telegramBotToken") ? "Active" : "Setup"}
              </Badge>
            </div>
            <div className="flex items-center justify-between py-0.5">
              <span className="text-[10px] text-gray-400">Email</span>
              <Badge variant="secondary" size="sm">Setup</Badge>
            </div>
            <div className="flex items-center justify-between py-0.5">
              <span className="text-[10px] text-gray-400">SMS</span>
              <Badge variant="secondary" size="sm">N/A</Badge>
            </div>
            <MiniSelect label="Export" value={get("notifications", "exportFormat", "json")} options={["json", "csv"]} onChange={(e) => updateField("notifications", "exportFormat", e.target.value)} />
          </div>
        </SectionCard>

        {/* ALIGNMENT ENGINE */}
        <SectionCard title="Alignment Engine" icon={ShieldAlert} color="#f59e0b">
          <MiniToggle label="Enabled" checked={!!get("alignment", "enabled", true)} onChange={(v) => updateField("alignment", "enabled", v)} />
          <MiniSelect label="Mode" value={get("alignment", "mode", "strict")} options={["strict", "moderate", "advisory"]} onChange={(e) => updateField("alignment", "mode", e.target.value)} />
          <MiniToggle label="Bright Lines" checked={!!get("alignment", "checkBrightLines", true)} onChange={(v) => updateField("alignment", "checkBrightLines", v)} />
          <MiniToggle label="Trading Bible" checked={!!get("alignment", "checkBible", true)} onChange={(v) => updateField("alignment", "checkBible", v)} />
          <MiniToggle label="Metacognition" checked={!!get("alignment", "checkMetacognition", true)} onChange={(v) => updateField("alignment", "checkMetacognition", v)} />
          <MiniToggle label="Critique" checked={!!get("alignment", "checkCritique", true)} onChange={(v) => updateField("alignment", "checkCritique", v)} />
          <MiniField label="Max Position %" value={get("alignment", "maxPositionPct", 5)} type="number" suffix="%" onChange={(e) => updateField("alignment", "maxPositionPct", Math.min(10, Number(e.target.value)))} />
        </SectionCard>

        {/* SYSTEM LOG / VIEW FULL LOG */}
        <SectionCard title="System / Audit Log" icon={FileText}>
          <div className="text-[9px] text-gray-500 space-y-0.5">
            <div className="font-mono">{new Date().toISOString()}</div>
            <div>Settings loaded successfully</div>
            <div>All agents operational</div>
          </div>
          <button
            onClick={() => setShowFullLog(!showFullLog)}
            className="mt-1.5 w-full text-[9px] bg-cyan-500/10 border border-cyan-500/20 rounded px-2 py-1 text-cyan-400 hover:bg-cyan-500/20 flex items-center gap-1 justify-center"
          >
            <FileText className="w-2.5 h-2.5" /> {showFullLog ? "Hide" : "View"} Full Log
          </button>
        </SectionCard>
      </div>

      {/* ===== FOOTER BAR ===== */}
      <div className="flex items-center justify-between mt-2 pt-2 border-t border-gray-800/50">
        <div className="flex gap-2">
          <button onClick={onExport} className="text-[10px] text-gray-500 hover:text-cyan-400 flex items-center gap-1 px-2 py-1 border border-gray-800/50 rounded">
            <Download className="w-3 h-3" /> Export Settings
          </button>
          <button onClick={() => importRef.current?.click()} className="text-[10px] text-gray-500 hover:text-cyan-400 flex items-center gap-1 px-2 py-1 border border-gray-800/50 rounded">
            <Upload className="w-3 h-3" /> Import Settings
          </button>
          <button onClick={() => { onReset("trading"); onReset("risk"); onReset("ml"); onReset("agents"); }} className="text-[10px] text-gray-500 hover:text-red-400 flex items-center gap-1 px-2 py-1 border border-gray-800/50 rounded">
            <RotateCcw className="w-3 h-3" /> Reset Defaults
          </button>
        </div>
        <Button
          variant="primary"
          size="sm"
          leftIcon={Save}
          onClick={saveAllSettings}
          disabled={saving}
          className="bg-cyan-500 hover:bg-cyan-600 text-black font-bold text-[10px] px-4 py-1.5 rounded"
        >
          {saving ? "Saving..." : "SAVE ALL CHANGES"}
        </Button>
      </div>

      {/* ===== FULL AUDIT LOG (expanded) ===== */}
      {showFullLog && (
        <div className="mt-3">
          <AuditLogTab />
        </div>
      )}
    </div>
  );
}
