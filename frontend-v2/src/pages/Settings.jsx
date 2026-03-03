import React, { useState, useEffect } from "react";
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
    <div className="mb-4">
      <h3 className="text-sm font-bold text-white uppercase tracking-wide flex items-center gap-2">
        <Icon className="w-4 h-4" style={{ color }} />
        {title}
      </h3>
      {sub && <p className="text-xs text-gray-500 mt-0.5">{sub}</p>}
    </div>
  );
}

function FieldRow({ label, children }) {
  return (
    <div className="flex items-center justify-between p-3 bg-[#0B0E14] border border-[rgba(42,52,68,0.5)] rounded-[8px]">
      <span className="text-xs text-gray-300 font-medium">{label}</span>
      <div className="flex-shrink-0 ml-4">{children}</div>
    </div>
  );
}

// -------------------------------------------------------
export default function SettingsPage() {
  const [activeTab, setActiveTab] = useState("api-keys");
  const {
    settings, loading, saving, dirty,
    connectionResults, updateField,
    saveCategory, saveAllSettings, resetCategory,
    validateKey, testConnection,
    exportSettings, importSettings, refetch,
  } = useSettings();

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

  // == Tab: User Profile ==
  const renderProfile = () => (
    <div className="space-y-6 animate-in fade-in duration-300">
      <SectionHeader icon={User} title="User Profile" sub="Personal details and session configuration." />
      <Card className="bg-[#111827] border border-[rgba(42,52,68,0.5)] rounded-[8px] p-4 space-y-3 max-w-xl">
        <TextField label="Display Name" value={get("user", "displayName")} onChange={(e) => updateField("user", "displayName", e.target.value)} inputClassName="text-xs py-1.5 rounded-md" />
        <TextField label="Email" value={get("user", "email")} onChange={(e) => updateField("user", "email", e.target.value)} inputClassName="text-xs py-1.5 rounded-md" />
        <Select label="Timezone" value={get("user", "timezone", "America/New_York")} options={["America/New_York", "America/Chicago", "America/Los_Angeles", "Europe/Oslo", "UTC"]} onChange={(v) => updateField("user", "timezone", v)} selectClassName="text-xs py-1.5 rounded-md" />
        <Select label="Currency" value={get("user", "currency", "USD")} options={["USD", "EUR", "NOK", "GBP"]} onChange={(v) => updateField("user", "currency", v)} selectClassName="text-xs py-1.5 rounded-md" />
        <TextField label="Session Timeout" type="number" value={get("user", "sessionTimeoutMinutes", 30)} onChange={(e) => updateField("user", "sessionTimeoutMinutes", Number(e.target.value))} suffix="min" inputClassName="text-xs py-1.5 rounded-md" />
        <FieldRow label="Two-Factor Auth">
          <Toggle checked={!!get("user", "twoFactorEnabled", false)} onChange={(v) => updateField("user", "twoFactorEnabled", v)} />
        </FieldRow>
      </Card>
      <div className="flex gap-3">
        <Button variant="primary" size="sm" leftIcon={Save} onClick={() => onSave("user")} disabled={saving} className="bg-[#00D9FF] hover:bg-[#00b8d9] text-black font-bold text-xs">{saving ? "Saving..." : "Save Profile"}</Button>
        <Button variant="secondary" size="sm" leftIcon={RotateCcw} onClick={() => onReset("user")} className="text-xs border-gray-700 text-gray-400">Reset Defaults</Button>
      </div>
    </div>
  );

  // == Tab: API Keys ==
  const renderApiKeys = () => {
    const providers = [
      { id: "alpaca", label: "Alpaca Trading API", keyField: "alpacaApiKey", secretField: "alpacaSecretKey", source: "alpaca" },
      { id: "unusual_whales", label: "Unusual Whales", keyField: "unusualWhalesApiKey", secretField: null, source: "unusual_whales" },
      { id: "finviz", label: "FinViz Elite", keyField: "finvizApiKey", secretField: null, source: "finviz" },
      { id: "fred", label: "FRED (St. Louis Fed)", keyField: "fredApiKey", secretField: null, source: "fred" },
      { id: "newsapi", label: "NewsAPI", keyField: "newsApiKey", secretField: null, source: null },
    ];
    return (
      <div className="space-y-6 animate-in fade-in duration-300">
        <SectionHeader icon={Key} title="API Keys" sub="Manage broker and data provider credentials." />
        <div className="flex gap-2 mb-4">
          <Button variant="secondary" size="xs" leftIcon={Download} onClick={onExport} className="text-xs text-gray-400">Export</Button>
          <label className="cursor-pointer">
            <input type="file" accept=".json" className="hidden" onChange={onImport} />
            <Button variant="secondary" size="xs" leftIcon={Upload} className="text-xs text-gray-400">Import</Button>
          </label>
        </div>
        {providers.map((p) => {
          const cr = connectionResults[p.id] || {};
          const isOk = cr.valid === true;
          const isFail = cr.valid === false;
          return (
            <Card key={p.id} className="bg-[#111827] border border-[rgba(42,52,68,0.5)] rounded-[8px] p-4 space-y-3">
              <div className="flex items-center justify-between">
                <span className="text-xs font-bold text-white">{p.label}</span>
                <Badge variant={cr.testing ? "info" : isOk ? "success" : isFail ? "error" : "default"}>
                  {cr.testing ? "Testing" : isOk ? "Connected" : isFail ? "Failed" : "Unknown"}
                </Badge>
              </div>
              <TextField label="API Key" type="password" value={get("dataSources", p.keyField)} onChange={(e) => updateField("dataSources", p.keyField, e.target.value)} inputClassName="text-xs py-1.5 bg-[#0a0a0f] border-gray-800/80" />
              {p.secretField && (
                <TextField label="Secret Key" type="password" value={get("dataSources", p.secretField)} onChange={(e) => updateField("dataSources", p.secretField, e.target.value)} inputClassName="text-xs py-1.5 bg-[#0a0a0f] border-gray-800/80" />
              )}
              {cr.message && <div className={`text-[10px] ${isOk ? 'text-emerald-400' : 'text-red-400'}`}>{cr.message}</div>}
              <div className="flex gap-2">
                {p.source && (
                  <Button variant="secondary" size="xs" onClick={() => onTestConn(p.source)} disabled={cr.testing} className="bg-[#00D9FF]/10 hover:bg-[#00D9FF]/20 text-[#00D9FF] border-[#00D9FF]/20 h-auto text-[10px] py-1 px-3">
                    {cr.testing ? <Loader2 className="w-3 h-3 animate-spin" /> : <Wifi className="w-3 h-3" />} Test
                  </Button>
                )}
                <Button variant="secondary" size="xs" onClick={() => onSave("dataSources")} className="bg-gray-800/50 hover:bg-gray-700 text-gray-300 border-gray-700 h-auto text-[10px] py-1 px-3">
                  <Save className="w-3 h-3" /> Save
                </Button>
              </div>
            </Card>
          );
        })}
        <Card className="bg-[#111827] border border-[rgba(42,52,68,0.5)] rounded-[8px] p-4">
          <h4 className="text-xs font-bold text-[#00D9FF] uppercase tracking-wider mb-2">Alpaca Environment</h4>
          <div className="flex gap-2">
            {["paper", "live"].map((env) => (
              <button key={env} onClick={() => updateField("dataSources", "alpacaBaseUrl", env)}
                className={`px-4 py-2 rounded-[8px] text-xs font-bold uppercase tracking-wider border transition-all ${
                  get("dataSources", "alpacaBaseUrl", "paper") === env
                    ? "bg-[rgba(0,217,255,0.15)] border-[rgba(0,217,255,0.3)] text-[#00D9FF]"
                    : "bg-[#111827] border-gray-700 text-[#9CA3AF] hover:border-gray-600"
                }`}>{env}</button>
            ))}
          </div>
          <p className="text-[10px] text-gray-500 mt-2">
            {get("dataSources", "alpacaBaseUrl") === "live" ? "LIVE trading active - real money" : "Paper trading - simulated orders only"}
          </p>
        </Card>
      </div>
    );
  };

  // == Tab: Trading Parameters ==
  const renderTradingParams = () => (
    <div className="space-y-6 animate-in fade-in duration-300">
      <SectionHeader icon={Activity} title="Trading Parameters" sub="Position sizing, order defaults, and session hours." />
      <Card className="bg-[#111827] border border-[rgba(42,52,68,0.5)] rounded-[8px] p-4 space-y-3 max-w-xl">
        <h4 className="text-xs font-bold text-[#00D9FF] uppercase tracking-wider">Position Sizing</h4>
        <TextField label="Max Position Size ($)" type="number" value={get("trading", "maxPositionSize", 10000)} onChange={(e) => updateField("trading", "maxPositionSize", Number(e.target.value))} inputClassName="text-xs py-1.5 rounded-md" />
        <TextField label="Max Daily Trades" type="number" value={get("trading", "maxDailyTrades", 10)} onChange={(e) => updateField("trading", "maxDailyTrades", Number(e.target.value))} inputClassName="text-xs py-1.5 rounded-md" />
        <h4 className="text-xs font-bold text-[#00D9FF] uppercase tracking-wider mt-4">Trade Management</h4>
        <Select label="Default Order Type" value={get("trading", "defaultOrderType", "market")} options={["market", "limit", "stop", "stop_limit"]} onChange={(v) => updateField("trading", "defaultOrderType", v)} selectClassName="text-xs py-1.5" />
        <Select label="Entry Method" value={get("trading", "entryMethod", "market")} options={["market", "limit", "scale_in"]} onChange={(v) => updateField("trading", "entryMethod", v)} selectClassName="text-xs py-1.5" />
        <h4 className="text-xs font-bold text-[#00D9FF] uppercase tracking-wider mt-4">Session Hours</h4>
        <TextField label="Market Open" value={get("trading", "marketOpen", "09:30")} onChange={(e) => updateField("trading", "marketOpen", e.target.value)} inputClassName="text-xs py-1.5 rounded-md" />
        <TextField label="Market Close" value={get("trading", "marketClose", "16:00")} onChange={(e) => updateField("trading", "marketClose", e.target.value)} inputClassName="text-xs py-1.5 rounded-md" />
        <FieldRow label="Auto Execute"><Toggle checked={!!get("trading", "autoExecute", false)} onChange={(v) => updateField("trading", "autoExecute", v)} /></FieldRow>
        <FieldRow label="Confirm Before Order"><Toggle checked={!!get("trading", "confirmBeforeOrder", true)} onChange={(v) => updateField("trading", "confirmBeforeOrder", v)} /></FieldRow>
        <FieldRow label="Pre-Market"><Toggle checked={!!get("trading", "preMarketEnabled", false)} onChange={(v) => updateField("trading", "preMarketEnabled", v)} /></FieldRow>
        <FieldRow label="After Hours"><Toggle checked={!!get("trading", "afterHoursEnabled", false)} onChange={(v) => updateField("trading", "afterHoursEnabled", v)} /></FieldRow>
      </Card>
      <div className="flex gap-3">
        <Button variant="primary" size="sm" leftIcon={Save} onClick={() => onSave("trading")} disabled={saving} className="bg-[#00D9FF] hover:bg-[#00b8d9] text-black font-bold text-xs">{saving ? "Saving..." : "Save Trading Params"}</Button>
        <Button variant="secondary" size="sm" leftIcon={RotateCcw} onClick={() => onReset("trading")} className="text-xs border-gray-700 text-gray-400">Reset</Button>
      </div>
    </div>
  );

  // == Tab: Risk Limits ==
  const renderRiskLimits = () => (
    <div className="space-y-6 animate-in fade-in duration-300">
      <SectionHeader icon={ShieldAlert} color="#ef4444" title="Risk Limits" sub="Portfolio risk constraints and circuit breakers." />
      <Card className="bg-[#111827] border border-[rgba(42,52,68,0.5)] rounded-[8px] p-4 space-y-3 max-w-xl">
        <h4 className="text-xs font-bold text-red-400 uppercase tracking-wider">Portfolio Risk Limits</h4>
        <TextField label="Max Portfolio Risk" type="number" step="0.01" value={get("risk", "maxPortfolioRisk", 0.02)} onChange={(e) => updateField("risk", "maxPortfolioRisk", parseFloat(e.target.value))} suffix="(ratio)" inputClassName="text-xs py-1.5" />
        <TextField label="Max Position Risk" type="number" step="0.01" value={get("risk", "maxPositionRisk", 0.01)} onChange={(e) => updateField("risk", "maxPositionRisk", parseFloat(e.target.value))} suffix="(ratio)" inputClassName="text-xs py-1.5" />
        <TextField label="Max Drawdown Limit" type="number" step="0.01" value={get("risk", "maxDrawdownLimit", 0.1)} onChange={(e) => updateField("risk", "maxDrawdownLimit", parseFloat(e.target.value))} suffix="(ratio)" inputClassName="text-xs py-1.5" />
        <TextField label="Max Daily Loss %" type="number" step="0.1" value={get("risk", "maxDailyLossPct", 3)} onChange={(e) => updateField("risk", "maxDailyLossPct", parseFloat(e.target.value))} suffix="%" inputClassName="text-xs py-1.5" />
        <TextField label="Max Positions" type="number" value={get("risk", "maxPositions", 10)} onChange={(e) => updateField("risk", "maxPositions", Number(e.target.value))} inputClassName="text-xs py-1.5" />
        <h4 className="text-xs font-bold text-red-400 uppercase tracking-wider mt-4">Stop/Target Defaults</h4>
        <TextField label="Stop Loss Default" type="number" step="0.01" value={get("risk", "stopLossDefault", 0.02)} onChange={(e) => updateField("risk", "stopLossDefault", parseFloat(e.target.value))} suffix="(ratio)" inputClassName="text-xs py-1.5" />
        <TextField label="Take Profit Default" type="number" step="0.01" value={get("risk", "takeProfitDefault", 0.04)} onChange={(e) => updateField("risk", "takeProfitDefault", parseFloat(e.target.value))} suffix="(ratio)" inputClassName="text-xs py-1.5" />
        <TextField label="ATR Stop Multiplier" type="number" step="0.1" value={get("risk", "atrStopMultiplier", 2.0)} onChange={(e) => updateField("risk", "atrStopMultiplier", parseFloat(e.target.value))} suffix="x ATR" inputClassName="text-xs py-1.5" />
        <TextField label="Kelly Fraction Multiplier" type="number" step="0.1" value={get("risk", "kellyFractionMultiplier", 0.5)} onChange={(e) => updateField("risk", "kellyFractionMultiplier", parseFloat(e.target.value))} suffix="multiplier" inputClassName="text-xs py-1.5" />
        <h4 className="text-xs font-bold text-red-400 uppercase tracking-wider mt-4">Circuit Breakers</h4>
        <FieldRow label="Circuit Breaker Enabled"><Toggle checked={!!get("risk", "circuitBreakerEnabled", true)} onChange={(v) => updateField("risk", "circuitBreakerEnabled", v)} /></FieldRow>
      </Card>
      <div className="flex gap-3">
        <Button variant="primary" size="sm" leftIcon={Save} onClick={() => onSave("risk")} disabled={saving} className="bg-red-600 hover:bg-red-700 text-white font-bold text-xs">{saving ? "Saving..." : "Save Risk Limits"}</Button>
        <Button variant="secondary" size="sm" leftIcon={RotateCcw} onClick={() => onReset("risk")} className="text-xs border-gray-700 text-gray-400">Reset</Button>
      </div>
    </div>
  );

  // == Tab: AI / ML Config ==
  const renderAiMl = () => (
    <div className="space-y-6 animate-in fade-in duration-300">
      <SectionHeader icon={Cpu} title="AI / ML Configuration" sub="Model settings, Ollama LLM, and drift detection." />
      <Card className="bg-[#111827] border border-[rgba(42,52,68,0.5)] rounded-[8px] p-4 space-y-3 max-w-xl">
        <h4 className="text-xs font-bold text-[#00D9FF] uppercase tracking-wider">Model Config</h4>
        <Select label="Model Type" value={get("ml", "modelType", "xgboost")} options={["xgboost", "random_forest", "lstm", "transformer"]} onChange={(v) => updateField("ml", "modelType", v)} selectClassName="text-xs py-1.5" />
        <Select label="Retrain Frequency" value={get("ml", "retrainFrequency", "weekly")} options={["daily", "weekly", "monthly"]} onChange={(v) => updateField("ml", "retrainFrequency", v)} selectClassName="text-xs py-1.5" />
        <TextField label="Confidence Threshold" type="number" step="0.01" value={get("ml", "confidenceThreshold", 0.7)} onChange={(e) => updateField("ml", "confidenceThreshold", parseFloat(e.target.value))} suffix="ratio" inputClassName="text-xs py-1.5" />
        <TextField label="Min Composite Score" type="number" value={get("ml", "minCompositeScore", 60)} onChange={(e) => updateField("ml", "minCompositeScore", Number(e.target.value))} suffix="pts" inputClassName="text-xs py-1.5" />
        <TextField label="Min ML Confidence" type="number" value={get("ml", "minMLConfidence", 50)} onChange={(e) => updateField("ml", "minMLConfidence", Number(e.target.value))} suffix="pts" inputClassName="text-xs py-1.5" />
        <TextField label="Walk-Forward Window" type="number" value={get("ml", "walkForwardWindow", 90)} onChange={(e) => updateField("ml", "walkForwardWindow", Number(e.target.value))} suffix="days" inputClassName="text-xs py-1.5" />
        <h4 className="text-xs font-bold text-[#a78bfa] uppercase tracking-wider mt-4">Ollama (Local LLM)</h4>
        <TextField label="Host URL" value={get("ollama", "ollamaHostUrl", "http://localhost:11434")} onChange={(e) => updateField("ollama", "ollamaHostUrl", e.target.value)} inputClassName="text-xs py-1.5" />
        <TextField label="Default Model" value={get("ollama", "ollamaDefaultModel", "llama3")} onChange={(e) => updateField("ollama", "ollamaDefaultModel", e.target.value)} inputClassName="text-xs py-1.5" />
        <TextField label="Context Length" type="number" value={get("ollama", "ollamaContextLength", 8192)} onChange={(e) => updateField("ollama", "ollamaContextLength", Number(e.target.value))} suffix="tokens" inputClassName="text-xs py-1.5" />
        <FieldRow label="CUDA Enabled"><Toggle checked={!!get("ollama", "ollamaCudaEnabled", false)} onChange={(v) => updateField("ollama", "ollamaCudaEnabled", v)} /></FieldRow>
        <Button variant="secondary" size="xs" onClick={() => onTestConn("ollama")} className="bg-[#a78bfa]/10 hover:bg-[#a78bfa]/20 text-[#a78bfa] border-[#a78bfa]/20 h-auto text-[10px] py-1 px-3 w-full">
          {connectionResults["ollama"]?.testing ? <Loader2 className="w-3 h-3 animate-spin" /> : <Wifi className="w-3 h-3" />} Test Ollama Connection
        </Button>
        {connectionResults["ollama"]?.message && <div className="text-[10px] text-gray-400">{connectionResults["ollama"].message}</div>}
        <h4 className="text-xs font-bold text-[#00D9FF] uppercase tracking-wider mt-4">Drift Detection</h4>
        <FieldRow label="Drift Detection Enabled"><Toggle checked={!!get("ml", "driftDetectionEnabled", true)} onChange={(v) => updateField("ml", "driftDetectionEnabled", v)} /></FieldRow>
        <TextField label="Drift Threshold" type="number" step="0.01" value={get("ml", "driftThreshold", 0.15)} onChange={(e) => updateField("ml", "driftThreshold", parseFloat(e.target.value))} suffix="ratio" inputClassName="text-xs py-1.5" />
      </Card>
      <div className="flex gap-3">
        <Button variant="primary" size="sm" leftIcon={Save} onClick={() => { onSave("ml"); onSave("ollama"); }} disabled={saving} className="bg-[#00D9FF] hover:bg-[#00b8d9] text-black font-bold text-xs">{saving ? "Saving..." : "Save AI/ML Config"}</Button>
        <Button variant="secondary" size="sm" leftIcon={RotateCcw} onClick={() => { onReset("ml"); onReset("ollama"); }} className="text-xs border-gray-700 text-gray-400">Reset</Button>
      </div>
    </div>
  );

  // == Tab: Agents ==
  const renderAgents = () => {
    const agentToggles = [
      { key: "marketDataAgent", label: "Market Data Agent", desc: "Live feed ingestion and normalization" },
      { key: "riskAgent", label: "Risk Agent", desc: "Real-time position risk monitoring" },
      { key: "signalEngine", label: "Signal Engine", desc: "ML-based signal generation" },
      { key: "patternAI", label: "Pattern AI", desc: "Chart pattern detection (CNN)" },
      { key: "youtubeAgent", label: "YouTube Agent", desc: "Transcript ingestion and knowledge base" },
      { key: "driftMonitor", label: "Drift Monitor", desc: "Model performance drift detection" },
      { key: "flywheelEngine", label: "Flywheel Engine", desc: "Feedback loop for ML self-improvement" },
      { key: "openclawBridge", label: "OpenClaw Bridge", desc: "Multi-agent swarm orchestration" },
    ];
    return (
      <div className="space-y-6 animate-in fade-in duration-300">
        <SectionHeader icon={Bot} title="Agent Configuration" sub="Enable/disable agents and configure operational limits." />
        <Card className="bg-[#111827] border border-[rgba(42,52,68,0.5)] rounded-[8px] p-4 space-y-3 max-w-xl">
          <h4 className="text-xs font-bold text-[#00D9FF] uppercase tracking-wider">Agent Switches</h4>
          {agentToggles.map((a) => (
            <FieldRow key={a.key} label={<div><div className="text-xs text-gray-200">{a.label}</div><div className="text-[10px] text-gray-600">{a.desc}</div></div>}>
              <Toggle checked={!!get("agents", a.key, true)} onChange={(v) => updateField("agents", a.key, v)} />
            </FieldRow>
          ))}
          <h4 className="text-xs font-bold text-[#00D9FF] uppercase tracking-wider mt-4">Operational Limits</h4>
          <TextField label="Max Concurrent Agents" type="number" value={get("agents", "maxConcurrentAgents", 8)} onChange={(e) => updateField("agents", "maxConcurrentAgents", Number(e.target.value))} inputClassName="text-xs py-1.5" />
          <TextField label="Agent Timeout" type="number" value={get("agents", "agentTimeout", 30)} onChange={(e) => updateField("agents", "agentTimeout", Number(e.target.value))} suffix="sec" inputClassName="text-xs py-1.5" />
          <TextField label="Scanner Interval" type="number" value={get("agents", "scannerInterval", 60)} onChange={(e) => updateField("agents", "scannerInterval", Number(e.target.value))} suffix="sec" inputClassName="text-xs py-1.5" />
          <FieldRow label="Auto Restart"><Toggle checked={!!get("agents", "autoRestart", true)} onChange={(v) => updateField("agents", "autoRestart", v)} /></FieldRow>
          <h4 className="text-xs font-bold text-[#00D9FF] uppercase tracking-wider mt-4">OpenClaw Bridge</h4>
          <TextField label="WebSocket URL" value={get("openclaw", "openclawWsUrl", "ws://localhost:8765")} onChange={(e) => updateField("openclaw", "openclawWsUrl", e.target.value)} inputClassName="text-xs py-1.5" />
          <TextField label="API Key" type="password" value={get("openclaw", "openclawApiKey")} onChange={(e) => updateField("openclaw", "openclawApiKey", e.target.value)} inputClassName="text-xs py-1.5 mt-3" />
          <TextField label="Reconnect Interval" type="number" value={get("openclaw", "openclawReconnectInterval", 5)} onChange={(e) => updateField("openclaw", "openclawReconnectInterval", Number(e.target.value))} suffix="sec" inputClassName="text-xs py-1.5 mt-3" />
        </Card>
        <div className="flex gap-3">
          <Button variant="primary" size="sm" leftIcon={Save} onClick={() => { onSave("agents"); onSave("openclaw"); }} disabled={saving} className="bg-[#00D9FF] hover:bg-[#00b8d9] text-black font-bold text-xs">{saving ? "Saving..." : "Save Agent Config"}</Button>
          <Button variant="secondary" size="sm" leftIcon={RotateCcw} onClick={() => { onReset("agents"); onReset("openclaw"); }} className="text-xs border-gray-700 text-gray-400">Reset</Button>
        </div>
      </div>
    );
  };

  // == Tab: Data Sources (FULLY BUILT OUT) ==
  const renderDataSources = () => {
    const sources = [
      { key: "alpacaMarketData", label: "Alpaca Market Data", fields: ["apiUrl", "wsUrl"] },
      { key: "polygon", label: "Polygon.io", fields: ["apiKey", "wsEnabled"] },
      { key: "unusualWhales", label: "Unusual Whales", fields: ["apiKey", "pollInterval"] },
      { key: "benzinga", label: "Benzinga", fields: ["apiKey", "newsEnabled"] },
      { key: "tradingView", label: "TradingView", fields: ["webhookSecret"] },
    ];
    return (
      <div className="space-y-6 animate-in fade-in duration-300">
        <SectionHeader icon={Database} title="Data Source Configuration" sub="Manage market data feeds and external data providers." />
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 max-w-3xl">
          {sources.map((s) => (
            <Card key={s.key} className="bg-[#111827] border border-[rgba(42,52,68,0.5)] rounded-[8px] p-4 space-y-3">
              <div className="flex items-center justify-between">
                <h4 className="text-xs font-bold text-[#00D9FF] uppercase tracking-wider">{s.label}</h4>
                <Toggle checked={!!get("dataSources", `${s.key}.enabled`, false)} onChange={(v) => updateField("dataSources", `${s.key}.enabled`, v)} />
              </div>
              {s.fields.map((f) => (
                <TextField key={f} label={f.replace(/([A-Z])/g, ' $1').trim()} type={f.toLowerCase().includes("key") || f.toLowerCase().includes("secret") ? "password" : "text"}
                  value={get("dataSources", `${s.key}.${f}`, "")} onChange={(e) => updateField("dataSources", `${s.key}.${f}`, e.target.value)} inputClassName="text-xs" />
              ))}
              <Button variant="ghost" size="xs" leftIcon={Zap} onClick={() => testConnection("dataSources", s.key)} className="text-xs text-gray-400 hover:text-[#00D9FF]">Test</Button>
            </Card>
          ))}
        </div>
        <div className="flex gap-3">
          <Button variant="primary" size="sm" leftIcon={Save} onClick={() => onSave("dataSources")} disabled={saving} className="bg-[#00D9FF] hover:bg-[#00b8d9] text-black font-bold">Save</Button>
          <Button variant="secondary" size="sm" leftIcon={RotateCcw} onClick={() => onReset("dataSources")} className="text-xs border-gray-700 text-gray-400">Reset</Button>
        </div>
      </div>
    );
  };

  // == Tab: Notifications ==
  const renderNotifications = () => {
    const alertToggles = [
      { key: "tradeAlerts", label: "Trade Executions", desc: "Alerts for filled orders, partials, and rejections" },
      { key: "signalAlerts", label: "Signal Alerts", desc: "When new high-confidence patterns emerge" },
      { key: "riskAlerts", label: "Risk Threshold Warnings", desc: "When daily drawdown approaches limits" },
      { key: "agentStatusAlerts", label: "Agent Status Alerts", desc: "Critical alerts for agent crashes or disconnects" },
      { key: "dailySummary", label: "End of Day Summary", desc: "Daily PnL and system performance report" },
    ];
    return (
      <div className="space-y-6 animate-in fade-in duration-300">
        <SectionHeader icon={Bell} title="Notification Routing" sub="Configure which events trigger alerts." />
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 max-w-3xl">
          <Card className="bg-[#111827] border border-[rgba(42,52,68,0.5)] rounded-[8px] p-4 space-y-3">
            <h4 className="text-xs font-bold text-[#00D9FF] uppercase tracking-wider mb-2">Alert Types</h4>
            {alertToggles.map((n) => (
              <FieldRow key={n.key} label={<div><div className="text-xs text-gray-200">{n.label}</div><div className="text-[10px] text-gray-600">{n.desc}</div></div>}>
                <Toggle checked={!!get("notifications", n.key, false)} onChange={(v) => updateField("notifications", n.key, v)} />
              </FieldRow>
            ))}
          </Card>
          <Card className="bg-[#111827] border border-[rgba(42,52,68,0.5)] rounded-[8px] p-4 space-y-4">
            <h4 className="text-xs font-bold text-[#10b981] uppercase tracking-wider">Channels</h4>
            <TextField label="Discord Webhook URL" type="password" value={get("notifications", "discordWebhookUrl")} onChange={(e) => updateField("notifications", "discordWebhookUrl", e.target.value)} inputClassName="text-xs py-1.5" />
            <TextField label="Slack Webhook URL" type="password" value={get("notifications", "slackWebhookUrl")} onChange={(e) => updateField("notifications", "slackWebhookUrl", e.target.value)} inputClassName="text-xs py-1.5" />
            <TextField label="Telegram Bot Token" type="password" value={get("notifications", "telegramBotToken")} onChange={(e) => updateField("notifications", "telegramBotToken", e.target.value)} inputClassName="text-xs py-1.5" />
            <TextField label="Telegram Chat ID" value={get("notifications", "telegramChatId")} onChange={(e) => updateField("notifications", "telegramChatId", e.target.value)} inputClassName="text-xs py-1.5" />
          </Card>
        </div>
        <div className="flex gap-3">
          <Button variant="primary" size="sm" leftIcon={Save} onClick={() => onSave("notifications")} disabled={saving} className="bg-[#00D9FF] hover:bg-[#00b8d9] text-black font-bold text-xs">{saving ? "Saving..." : "Save Notifications"}</Button>
          <Button variant="secondary" size="sm" leftIcon={RotateCcw} onClick={() => onReset("notifications")} className="text-xs border-gray-700 text-gray-400">Reset</Button>
        </div>
      </div>
    );
  };

  // == Tab: Appearance ==
  const renderAppearance = () => {
    const themes = ["dark", "midnight", "terminal", "light"];
    const densities = ["compact", "comfortable", "spacious"];
    return (
      <div className="space-y-6 animate-in fade-in duration-300">
        <SectionHeader icon={Palette} title="Appearance & Display" sub="Customize the look and feel of your trading dashboard." />
        <Card className="bg-[#0B0E14] border-gray-800 p-4 space-y-4 max-w-xl">
          <h4 className="text-xs font-bold text-[#00D9FF] uppercase tracking-wider mb-2">Theme & Layout</h4>
          <FieldRow label="Theme">
            <div className="flex gap-2">
              {themes.map((t) => (
                <button key={t} onClick={() => updateField("appearance", "theme", t)}
                  className={`px-3 py-1 text-xs rounded-[8px] border transition-all ${get("appearance", "theme", "dark") === t ? "bg-[rgba(0,217,255,0.15)] text-[#00D9FF] border-[rgba(0,217,255,0.3)] font-bold" : "bg-[#111827] border-gray-700 text-[#9CA3AF] hover:border-gray-500"}`}>{t}</button>
              ))}
            </div>
          </FieldRow>
          <FieldRow label="Density">
            <div className="flex gap-2">
              {densities.map((d) => (
                <button key={d} onClick={() => updateField("appearance", "density", d)}
                  className={`px-3 py-1 text-xs rounded-[8px] border transition-all ${get("appearance", "density", "compact") === d ? "bg-[rgba(0,217,255,0.15)] text-[#00D9FF] border-[rgba(0,217,255,0.3)] font-bold" : "bg-[#111827] border-gray-700 text-[#9CA3AF] hover:border-gray-500"}`}>{d}</button>
              ))}
            </div>
          </FieldRow>
          <TextField label="Chart Default Timeframe" value={get("appearance", "chartTimeframe", "5m")} onChange={(e) => updateField("appearance", "chartTimeframe", e.target.value)} />
          <FieldRow label="Show PnL in Header"><Toggle checked={!!get("appearance", "showPnlHeader", true)} onChange={(v) => updateField("appearance", "showPnlHeader", v)} /></FieldRow>
          <FieldRow label="Enable Animations"><Toggle checked={!!get("appearance", "animations", true)} onChange={(v) => updateField("appearance", "animations", v)} /></FieldRow>
          <FieldRow label="Sound Alerts"><Toggle checked={!!get("appearance", "soundAlerts", false)} onChange={(v) => updateField("appearance", "soundAlerts", v)} /></FieldRow>
        </Card>
        <div className="flex gap-3">
          <Button variant="primary" size="sm" leftIcon={Save} onClick={() => onSave("appearance")} disabled={saving} className="bg-[#00D9FF] hover:bg-[#00b8d9] text-black font-bold">Save</Button>
          <Button variant="secondary" size="sm" leftIcon={RotateCcw} onClick={() => onReset("appearance")} className="text-xs border-gray-700 text-gray-400">Reset</Button>
        </div>
      </div>
    );
  };

  // == Tab: Audit Log (fixed - uses useApi hook instead of raw api) ==
  const renderAuditLog = () => {
    const { data: auditData, loading: logLoading } = useApi("settings", { endpoint: "/audit-log" });
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
  };

  // == Tab: Alignment ==
  const renderAlignment = () => (
    <div className="space-y-6 animate-in fade-in duration-300">
      <SectionHeader icon={ShieldAlert} color="#f59e0b" title="Alignment Engine" sub="Constitutive alignment controls - 6 patterns from the Soul Document architecture." />
      <Card className="bg-[#111827] border border-[rgba(42,52,68,0.5)] rounded-[8px] p-4 space-y-4 max-w-3xl">
        <h4 className="text-xs font-bold text-[#f59e0b] uppercase tracking-wider mb-2">Engine Mode</h4>
        <FieldRow label="Alignment Enabled"><Toggle checked={!!get("alignment", "enabled", true)} onChange={(v) => updateField("alignment", "enabled", v)} /></FieldRow>
        <Select label="Mode" value={get("alignment", "mode", "strict")} options={["strict", "moderate", "advisory"]} onChange={(v) => updateField("alignment", "mode", v)} selectClassName="text-xs py-1.5" />
        <h4 className="text-xs font-bold text-[#f59e0b] uppercase tracking-wider mt-4">Active Checks</h4>
        <FieldRow label="Bright Lines"><Toggle checked={!!get("alignment", "checkBrightLines", true)} onChange={(v) => updateField("alignment", "checkBrightLines", v)} /></FieldRow>
        <FieldRow label="Trading Bible"><Toggle checked={!!get("alignment", "checkBible", true)} onChange={(v) => updateField("alignment", "checkBible", v)} /></FieldRow>
        <FieldRow label="Metacognition"><Toggle checked={!!get("alignment", "checkMetacognition", true)} onChange={(v) => updateField("alignment", "checkMetacognition", v)} /></FieldRow>
        <FieldRow label="Critique"><Toggle checked={!!get("alignment", "checkCritique", true)} onChange={(v) => updateField("alignment", "checkCritique", v)} /></FieldRow>
        <h4 className="text-xs font-bold text-[#f59e0b] uppercase tracking-wider mt-4">Operating Limits</h4>
        <TextField label="Max Position %" type="number" value={get("alignment", "maxPositionPct", 5)} onChange={(e) => updateField("alignment", "maxPositionPct", Math.min(10, Number(e.target.value)))} suffix="% (cap: 10%)" inputClassName="text-xs py-1.5" />
        <TextField label="Max Heat %" type="number" value={get("alignment", "maxHeatPct", 20)} onChange={(e) => updateField("alignment", "maxHeatPct", Math.min(25, Number(e.target.value)))} suffix="% (cap: 25%)" inputClassName="text-xs py-1.5" />
        <TextField label="Max Drawdown %" type="number" value={get("alignment", "maxDrawdownPct", 10)} onChange={(e) => updateField("alignment", "maxDrawdownPct", Math.min(15, Number(e.target.value)))} suffix="% (cap: 15%)" inputClassName="text-xs py-1.5" />
        <TextField label="Daily Trade Cap" type="number" value={get("alignment", "dailyTradeCap", 15)} onChange={(e) => updateField("alignment", "dailyTradeCap", Number(e.target.value))} inputClassName="text-xs py-1.5" />
        <TextField label="Rapid Fire Window" type="number" value={get("alignment", "rapidFireWindowSec", 60)} onChange={(e) => updateField("alignment", "rapidFireWindowSec", Number(e.target.value))} suffix="sec" inputClassName="text-xs py-1.5" />
        <TextField label="Critique Threshold" type="number" value={get("alignment", "critiqueThreshold", 70)} onChange={(e) => updateField("alignment", "critiqueThreshold", Number(e.target.value))} suffix="%" inputClassName="text-xs py-1.5" />
      </Card>
      <div className="flex gap-3">
        <Button variant="primary" size="sm" leftIcon={Save} onClick={() => onSave("alignment")} disabled={saving} className="bg-[#f59e0b] hover:bg-[#d97706] text-black font-bold text-xs">{saving ? "Saving..." : "Save Alignment"}</Button>
        <Button variant="secondary" size="sm" leftIcon={RotateCcw} onClick={() => onReset("alignment")} className="text-xs border-gray-700 text-gray-400">Reset</Button>
      </div>
      <Card className="bg-[#111827] border border-[rgba(42,52,68,0.5)] rounded-[8px] p-4">
        <h4 className="text-xs font-bold text-[#f59e0b] uppercase tracking-wider mb-3">Alignment Engine Dashboard</h4>
        <AlignmentEngine />
      </Card>
    </div>
  );

  // == Tabs array (FIXED: renderRiskLimits not renderRiskManagement) ==
  const tabs = [
    { key: "profile", label: "Profile", icon: User, render: renderProfile },
    { key: "api-keys", label: "API Keys", icon: Key, render: renderApiKeys },
    { key: "trading-params", label: "Trading", icon: TrendingUp, render: renderTradingParams },
    { key: "risk-limits", label: "Risk", icon: Shield, render: renderRiskLimits },
    { key: "ai-ml", label: "AI / ML", icon: Brain, render: renderAiMl },
    { key: "agents", label: "Agents", icon: Bot, render: renderAgents },
    { key: "data-sources", label: "Data Sources", icon: Database, render: renderDataSources },
    { key: "notifications", label: "Notifications", icon: Bell, render: renderNotifications },
    { key: "appearance", label: "Appearance", icon: Palette, render: renderAppearance },
    { key: "audit-log", label: "Audit Log", icon: FileText, render: renderAuditLog },
    { key: "alignment", label: "Alignment", icon: ShieldAlert, render: renderAlignment },
  ];

  const activeTabObj = tabs.find(t => t.key === activeTab) || tabs[0];

  if (loading) {
    return (
      <div className="min-h-screen bg-[#0B0E14] flex items-center justify-center">
        <Loader2 className="w-6 h-6 animate-spin text-[#00D9FF]" />
        <span className="ml-2 text-gray-400 text-sm">Loading settings...</span>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-[#0B0E14] text-gray-100 p-4">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-lg font-bold text-white">Settings</h1>
          <p className="text-xs text-gray-500">Configure your elite trading system</p>
        </div>
        <div className="flex gap-2">
          <Button variant="secondary" size="xs" leftIcon={Download} onClick={onExport} className="text-xs text-gray-400">Export</Button>
          <label className="cursor-pointer">
            <input type="file" accept=".json" className="hidden" onChange={onImport} />
            <Button variant="secondary" size="xs" leftIcon={Upload} className="text-xs text-gray-400">Import</Button>
          </label>
        </div>
      </div>

      {/* Tab nav + content */}
      <div className="flex gap-6">
        {/* Sidebar tabs */}
        <div className="w-48 shrink-0 space-y-1">
          {tabs.map((t) => {
            const Icon = t.icon;
            const isActive = t.key === activeTab;
            return (
              <button key={t.key} onClick={() => setActiveTab(t.key)}
                className={`w-full flex items-center gap-2 px-3 py-2 rounded-[8px] text-xs font-medium transition-all ${
                  isActive ? "bg-[rgba(0,217,255,0.15)] text-[#00D9FF] border border-[rgba(0,217,255,0.3)] shadow-[0_0_10px_rgba(0,217,255,0.1)]" : "bg-[#111827] text-[#9CA3AF] border border-transparent hover:text-gray-200 hover:bg-gray-800/50"
                }`}>
                <Icon className="w-3.5 h-3.5" />
                {t.label}
              </button>
            );
          })}
        </div>

        {/* Content area */}
        <div className="flex-1 min-w-0">
          {activeTabObj.render()}
        </div>
      </div>
    </div>
  );
}
