import React, { useState } from "react";
import Card from "../components/ui/Card";
import Button from "../components/ui/Button";
import PageHeader from "../components/ui/PageHeader";
import Toggle from "../components/ui/Toggle";
import TextField from "../components/ui/TextField";
import Select from "../components/ui/Select";
import Badge from "../components/ui/Badge";
import { useSettings } from "../hooks/useSettings";
import { toast } from "react-toastify";
import {
  User, Key, Activity, Bell, Layout, Cpu, Database,
  ShieldAlert, History, Save, RefreshCw, CheckCircle2,
  AlertTriangle, Settings, Terminal, Sliders, Wifi,
  WifiOff, Loader2, RotateCcw, Download, Upload,
  Bot, TrendingUp, BarChart2, Globe, Zap,
} from "lucide-react";

// ── Shared helpers ────────────────────────────────────────────
const TOAST_CFG = { position: "bottom-right", theme: "dark" };

function StatusDot({ ok, testing }) {
  if (testing) return <Loader2 className="w-3 h-3 animate-spin text-[#06b6d4]" />;
  if (ok === true)  return <CheckCircle2 className="w-3 h-3 text-[#10b981]" />;
  if (ok === false) return <AlertTriangle className="w-3 h-3 text-red-400" />;
  return <div className="w-2 h-2 rounded-full bg-gray-600" />;
}

function SectionHeader({ icon: Icon, color = "#06b6d4", title, sub }) {
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
    <div className="flex items-center justify-between p-3 bg-[#0B0E14] border border-gray-800/60 rounded-lg">
      <span className="text-xs text-gray-300 font-medium">{label}</span>
      <div className="flex-shrink-0 ml-4">{children}</div>
    </div>
  );
}

// ────────────────────────────────────────────────────────────────
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

  // Helper: get a value from a category, default to empty string if loading
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
      a.href = url; a.download = "elite-settings-export.json"; a.click();
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

  const navItems = [
    { id: "profile",        label: "User Profile",    icon: User },
    { id: "api-keys",       label: "API Keys",         icon: Key },
    { id: "trading-params", label: "Trading Params",   icon: Activity },
    { id: "risk-limits",    label: "Risk Limits",      icon: ShieldAlert },
    { id: "ai-ml",          label: "AI / ML Config",   icon: Cpu },
    { id: "agents",         label: "Agents",           icon: Bot },
    { id: "data-sources",   label: "Data Sources",     icon: Database },
    { id: "notifications",  label: "Notifications",    icon: Bell },
    { id: "appearance",     label: "Appearance",       icon: Layout },
    { id: "audit-log",      label: "Audit Log",        icon: History },
        { id: "alignment",    label: "Alignment",    icon: ShieldAlert },
  ];

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="w-8 h-8 animate-spin text-[#06b6d4]" />
        <span className="ml-3 text-sm text-gray-400">Loading settings...</span>
      </div>
    );
  }

  // ── Tab: User Profile ──────────────────────────────────────────
  const renderProfile = () => (
    <div className="space-y-6 animate-in fade-in duration-300">
      <SectionHeader icon={User} title="Identity & Localization" sub="Trader identity and locale preferences." />
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4 max-w-2xl">
        <TextField label="Display Name" value={get("user", "displayName")} onChange={(e) => updateField("user", "displayName", e.target.value)} inputClassName="text-xs py-1.5 rounded-md" />
        <TextField label="Email" type="email" value={get("user", "email")} onChange={(e) => updateField("user", "email", e.target.value)} inputClassName="text-xs py-1.5 rounded-md" />
        <Select label="Timezone" value={get("user", "timezone", "America/New_York")} options={["America/New_York", "America/Chicago", "America/Los_Angeles", "Europe/Oslo", "UTC"]} onChange={(v) => updateField("user", "timezone", v)} selectClassName="text-xs py-1.5 rounded-md" />
        <Select label="Base Currency" value={get("user", "currency", "USD")} options={["USD", "EUR", "GBP", "NOK"]} onChange={(v) => updateField("user", "currency", v)} selectClassName="text-xs py-1.5 rounded-md" />
        <TextField label="Session Timeout" type="number" value={get("user", "sessionTimeoutMinutes", 30)} onChange={(e) => updateField("user", "sessionTimeoutMinutes", Number(e.target.value))} suffix="min" inputClassName="text-xs py-1.5 rounded-md" />
      </div>
      <div className="max-w-2xl space-y-2">
        <FieldRow label="Two-Factor Authentication">
          <Toggle checked={!!get("user", "twoFactorEnabled", false)} onChange={(v) => updateField("user", "twoFactorEnabled", v)} />
        </FieldRow>
      </div>
      <div className="flex gap-3 pt-2">
        <Button variant="primary" size="sm" leftIcon={Save} onClick={() => onSave("user")} disabled={saving} className="bg-[#06b6d4] hover:bg-[#0891b2] text-black font-bold text-xs">{saving ? "Saving..." : "Save Profile"}</Button>
        <Button variant="secondary" size="sm" leftIcon={RotateCcw} onClick={() => onReset("user")} className="text-xs border-gray-700 text-gray-400">Reset Defaults</Button>
      </div>
    </div>
  );

  // ── Tab: API Keys ──────────────────────────────────────────────
  const renderApiKeys = () => {
    const providers = [
      { id: "alpaca",          label: "Alpaca Trading API",    keyField: "alpacaApiKey",        secretField: "alpacaSecretKey",    source: "alpaca" },
      { id: "unusual_whales",  label: "Unusual Whales",        keyField: "unusualWhalesApiKey",  secretField: null,                source: "unusual_whales" },
      { id: "finviz",          label: "FinViz Elite",          keyField: "finvizApiKey",         secretField: null,                source: "finviz" },
      { id: "fred",            label: "FRED (St. Louis Fed)",  keyField: "fredApiKey",           secretField: null,                source: "fred" },
      { id: "newsapi",         label: "NewsAPI",               keyField: "newsApiKey",           secretField: null,                source: null },
    ];
    return (
      <div className="space-y-5 animate-in fade-in duration-300">
        <div className="flex justify-between items-end">
          <SectionHeader icon={Key} title="API Integrations" sub="Manage connections to brokers and data feeds." />
          <div className="flex gap-2 mb-4">
            <Button variant="outline" size="sm" leftIcon={Download} onClick={onExport} className="text-[10px] h-auto py-1 px-3 border-gray-700 text-gray-400">Export</Button>
            <label className="cursor-pointer">
              <input type="file" accept=".json" className="hidden" onChange={onImport} />
              <span className="inline-flex items-center gap-1.5 text-[10px] py-1 px-3 border border-gray-700 text-gray-400 rounded-md hover:bg-gray-800 transition-colors"><Upload className="w-3 h-3" />Import</span>
            </label>
          </div>
        </div>
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          {providers.map((p) => {
            const cr = connectionResults[p.id] || {};
            const isOk = cr.valid === true;
            const isFail = cr.valid === false;
            return (
              <Card key={p.id} className="bg-[#0B0E14] border-gray-800/60 p-4 relative overflow-hidden">
                <div className="absolute top-0 left-0 w-1 h-full bg-gradient-to-b from-[#06b6d4]/40 to-transparent" />
                <div className="flex justify-between items-center mb-4">
                  <span className="text-sm font-bold text-gray-200">{p.label}</span>
                  <div className="flex items-center gap-2">
                    <StatusDot ok={isOk ? true : isFail ? false : undefined} testing={cr.testing} />
                    <Badge variant={isOk ? "success" : isFail ? "destructive" : "secondary"} size="sm" className="text-[10px] uppercase">
                      {cr.testing ? "Testing" : isOk ? "Connected" : isFail ? "Failed" : "Unknown"}
                    </Badge>
                  </div>
                </div>
                <div className="space-y-3">
                  <TextField label="API Key" type="password" value={get("dataSources", p.keyField)} onChange={(e) => updateField("dataSources", p.keyField, e.target.value)} inputClassName="text-xs py-1.5 bg-[#0a0a0f] border-gray-800/80" />
                  {p.secretField && (
                    <TextField label="API Secret" type="password" value={get("dataSources", p.secretField)} onChange={(e) => updateField("dataSources", p.secretField, e.target.value)} inputClassName="text-xs py-1.5 bg-[#0a0a0f] border-gray-800/80" />
                  )}
                  {cr.message && (
                    <p className={`text-[10px] mt-1 ${isOk ? "text-[#10b981]" : "text-red-400"}`}>{cr.message}</p>
                  )}
                  <div className="pt-1 flex gap-2">
                    {p.source && (
                      <Button variant="outline" size="sm" onClick={() => onTestConn(p.source)} disabled={cr.testing} className="bg-[#06b6d4]/10 hover:bg-[#06b6d4]/20 text-[#06b6d4] border-[#06b6d4]/20 h-auto text-[10px] py-1 px-3">
                        {cr.testing ? <Loader2 className="w-3 h-3 animate-spin" /> : <Wifi className="w-3 h-3" />} Test
                      </Button>
                    )}
                    <Button variant="secondary" size="sm" onClick={() => onSave("dataSources")} className="bg-gray-800/50 hover:bg-gray-700 text-gray-300 border-gray-700 h-auto text-[10px] py-1 px-3"><Save className="w-3 h-3" /> Save</Button>
                  </div>
                </div>
              </Card>
            );
          })}
        </div>
        {/* Alpaca environment */}
        <Card className="bg-[#0B0E14] border-gray-800/60 p-4">
          <h4 className="text-xs font-bold text-[#06b6d4] uppercase tracking-wider mb-3">Alpaca Environment</h4>
          <div className="flex gap-3">
            {["paper", "live"].map((env) => (
              <button key={env} onClick={() => updateField("dataSources", "alpacaBaseUrl", env)}
                className={`px-4 py-2 rounded-lg text-xs font-bold uppercase tracking-wider border transition-all ${
                  get("dataSources", "alpacaBaseUrl", "paper") === env
                    ? "bg-[#06b6d4]/20 border-[#06b6d4] text-[#06b6d4]"
                    : "bg-gray-900 border-gray-700 text-gray-500 hover:border-gray-600"
                }`}>{env}</button>
            ))}
          </div>
          <p className="text-[10px] text-gray-600 mt-2">{get("dataSources", "alpacaBaseUrl") === "live" ? "LIVE trading active - real money" : "Paper trading - simulated orders only"}</p>
        </Card>
      </div>
    );
  };

  // ── Tab: Trading Parameters ────────────────────────────────────
  const renderTradingParams = () => (
    <div className="space-y-6 animate-in fade-in duration-300">
      <SectionHeader icon={Activity} title="Execution Parameters" sub="Default sizing, targets, and operational limits." />
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <Card className="bg-[#0B0E14] border-gray-800 p-4 space-y-4">
          <h4 className="text-xs font-bold text-[#06b6d4] uppercase tracking-wider flex items-center gap-1"><Terminal className="w-3 h-3" />Position Sizing</h4>
          <TextField label="Max Position Size ($)" type="number" value={get("trading", "maxPositionSize", 10000)} onChange={(e) => updateField("trading", "maxPositionSize", Number(e.target.value))} inputClassName="text-xs py-1.5 rounded-md" />
          <TextField label="Max Daily Trades" type="number" value={get("trading", "maxDailyTrades", 20)} onChange={(e) => updateField("trading", "maxDailyTrades", Number(e.target.value))} inputClassName="text-xs py-1.5 rounded-md" />
        </Card>
        <Card className="bg-[#0B0E14] border-gray-800 p-4 space-y-4">
          <h4 className="text-xs font-bold text-[#f59e0b] uppercase tracking-wider flex items-center gap-1"><Sliders className="w-3 h-3" />Trade Management</h4>
          <Select label="Default Order Type" value={get("trading", "defaultOrderType", "market")} options={["market", "limit", "stop", "stop_limit"]} onChange={(v) => updateField("trading", "defaultOrderType", v)} selectClassName="text-xs py-1.5" />
          <Select label="Entry Method" value={get("trading", "entryMethod", "signal")} options={["signal", "manual", "hybrid"]} onChange={(v) => updateField("trading", "entryMethod", v)} selectClassName="text-xs py-1.5" />
        </Card>
        <Card className="bg-[#0B0E14] border-gray-800 p-4 space-y-4">
          <h4 className="text-xs font-bold text-[#10b981] uppercase tracking-wider flex items-center gap-1"><Activity className="w-3 h-3" />Session Hours</h4>
          <TextField label="Market Open" type="time" value={get("trading", "marketOpen", "09:30")} onChange={(e) => updateField("trading", "marketOpen", e.target.value)} inputClassName="text-xs py-1.5 rounded-md" />
          <TextField label="Market Close" type="time" value={get("trading", "marketClose", "16:00")} onChange={(e) => updateField("trading", "marketClose", e.target.value)} inputClassName="text-xs py-1.5 rounded-md" />
        </Card>
      </div>
      <div className="max-w-2xl space-y-2">
        <FieldRow label="Auto Execute Trades">
          <Toggle checked={!!get("trading", "autoExecute", false)} onChange={(v) => updateField("trading", "autoExecute", v)} />
        </FieldRow>
        <FieldRow label="Confirm Before Order">
          <Toggle checked={!!get("trading", "confirmBeforeOrder", true)} onChange={(v) => updateField("trading", "confirmBeforeOrder", v)} />
        </FieldRow>
        <FieldRow label="Pre-Market Trading">
          <Toggle checked={!!get("trading", "preMarketEnabled", false)} onChange={(v) => updateField("trading", "preMarketEnabled", v)} />
        </FieldRow>
        <FieldRow label="After-Hours Trading">
          <Toggle checked={!!get("trading", "afterHoursEnabled", false)} onChange={(v) => updateField("trading", "afterHoursEnabled", v)} />
        </FieldRow>
      </div>
      <div className="flex gap-3">
        <Button variant="primary" size="sm" leftIcon={Save} onClick={() => onSave("trading")} disabled={saving} className="bg-[#06b6d4] hover:bg-[#0891b2] text-black font-bold text-xs">{saving ? "Saving..." : "Save Trading Params"}</Button>
        <Button variant="secondary" size="sm" leftIcon={RotateCcw} onClick={() => onReset("trading")} className="text-xs border-gray-700 text-gray-400">Reset</Button>
      </div>
    </div>
  );

  // ── Tab: Risk Limits ─────────────────────────────────────────────
  const renderRiskLimits = () => (
    <div className="space-y-6 animate-in fade-in duration-300">
      <SectionHeader icon={ShieldAlert} color="#ef4444" title="Circuit Breakers & Risk Limits" sub="Hard halts and emergency killswitches for automated systems." />
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <Card className="bg-red-950/10 border-red-900/30 p-4 space-y-4">
          <h4 className="text-xs font-bold text-red-400 uppercase tracking-wider">Portfolio Risk Limits</h4>
          <TextField label="Max Portfolio Risk" type="number" value={get("risk", "maxPortfolioRisk", 0.06)} onChange={(e) => updateField("risk", "maxPortfolioRisk", parseFloat(e.target.value))} suffix="(ratio)" inputClassName="text-xs py-1.5" />
          <TextField label="Max Position Risk" type="number" value={get("risk", "maxPositionRisk", 0.02)} onChange={(e) => updateField("risk", "maxPositionRisk", parseFloat(e.target.value))} suffix="(ratio)" inputClassName="text-xs py-1.5" />
          <TextField label="Max Drawdown Limit" type="number" value={get("risk", "maxDrawdownLimit", 0.10)} onChange={(e) => updateField("risk", "maxDrawdownLimit", parseFloat(e.target.value))} suffix="(ratio)" inputClassName="text-xs py-1.5" />
          <TextField label="Max Daily Loss %" type="number" value={get("risk", "maxDailyLossPct", 5.0)} onChange={(e) => updateField("risk", "maxDailyLossPct", parseFloat(e.target.value))} suffix="%" inputClassName="text-xs py-1.5" />
          <TextField label="Max Positions" type="number" value={get("risk", "maxPositions", 15)} onChange={(e) => updateField("risk", "maxPositions", Number(e.target.value))} inputClassName="text-xs py-1.5" />
        </Card>
        <Card className="bg-amber-950/10 border-amber-900/30 p-4 space-y-4">
          <h4 className="text-xs font-bold text-amber-400 uppercase tracking-wider">Stop/Target Defaults</h4>
          <TextField label="Default Stop Loss" type="number" value={get("risk", "stopLossDefault", 0.03)} onChange={(e) => updateField("risk", "stopLossDefault", parseFloat(e.target.value))} suffix="(ratio)" inputClassName="text-xs py-1.5" />
          <TextField label="Default Take Profit" type="number" value={get("risk", "takeProfitDefault", 0.06)} onChange={(e) => updateField("risk", "takeProfitDefault", parseFloat(e.target.value))} suffix="(ratio)" inputClassName="text-xs py-1.5" />
          <TextField label="ATR Stop Multiplier" type="number" value={get("risk", "atrStopMultiplier", 2.0)} onChange={(e) => updateField("risk", "atrStopMultiplier", parseFloat(e.target.value))} suffix="x ATR" inputClassName="text-xs py-1.5" />
          <TextField label="Kelly Fraction" type="number" value={get("risk", "kellyFractionMultiplier", 0.5)} onChange={(e) => updateField("risk", "kellyFractionMultiplier", parseFloat(e.target.value))} suffix="multiplier" inputClassName="text-xs py-1.5" />
        </Card>
        <Card className="bg-[#0B0E14] border-gray-800 p-4 space-y-3 md:col-span-2">
          <h4 className="text-xs font-bold text-gray-200 uppercase tracking-wider mb-2">Circuit Breakers</h4>
          <FieldRow label="Circuit Breaker Enabled">
            <Toggle checked={!!get("risk", "circuitBreakerEnabled", true)} onChange={(v) => updateField("risk", "circuitBreakerEnabled", v)} />
          </FieldRow>
        </Card>
      </div>
      <div className="flex gap-3">
        <Button variant="primary" size="sm" leftIcon={Save} onClick={() => onSave("risk")} disabled={saving} className="bg-red-600 hover:bg-red-700 text-white font-bold text-xs">{saving ? "Saving..." : "Save Risk Limits"}</Button>
        <Button variant="secondary" size="sm" leftIcon={RotateCcw} onClick={() => onReset("risk")} className="text-xs border-gray-700 text-gray-400">Reset</Button>
      </div>
    </div>
  );

  // ── Tab: AI / ML Config ──────────────────────────────────────────
  const renderAiMl = () => (
    <div className="space-y-6 animate-in fade-in duration-300">
      <SectionHeader icon={Cpu} title="Intelligence & Models" sub="Tune ML components, thresholds, and Ollama integration." />
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <Card className="bg-[#0B0E14] border-gray-800 p-4 space-y-4">
          <h4 className="text-xs font-bold text-[#06b6d4] uppercase tracking-wider">Model Config</h4>
          <Select label="Model Type" value={get("ml", "modelType", "xgboost")} options={["xgboost", "random_forest", "lstm", "transformer"]} onChange={(v) => updateField("ml", "modelType", v)} selectClassName="text-xs py-1.5" />
          <Select label="Retrain Frequency" value={get("ml", "retrainFrequency", "weekly")} options={["daily", "weekly", "monthly", "manual"]} onChange={(v) => updateField("ml", "retrainFrequency", v)} selectClassName="text-xs py-1.5" />
          <TextField label="Confidence Threshold" type="number" value={get("ml", "confidenceThreshold", 0.65)} onChange={(e) => updateField("ml", "confidenceThreshold", parseFloat(e.target.value))} suffix="ratio" inputClassName="text-xs py-1.5" />
          <TextField label="Min Composite Score" type="number" value={get("ml", "minCompositeScore", 60)} onChange={(e) => updateField("ml", "minCompositeScore", Number(e.target.value))} suffix="pts" inputClassName="text-xs py-1.5" />
          <TextField label="Min ML Confidence" type="number" value={get("ml", "minMLConfidence", 40)} onChange={(e) => updateField("ml", "minMLConfidence", Number(e.target.value))} suffix="pts" inputClassName="text-xs py-1.5" />
          <TextField label="Walk-Forward Window" type="number" value={get("ml", "walkForwardWindow", 60)} onChange={(e) => updateField("ml", "walkForwardWindow", Number(e.target.value))} suffix="days" inputClassName="text-xs py-1.5" />
        </Card>
        <Card className="bg-[#0B0E14] border-gray-800 p-4 space-y-4">
          <h4 className="text-xs font-bold text-[#a78bfa] uppercase tracking-wider">Ollama (Local LLM)</h4>
          <TextField label="Host URL" value={get("ollama", "ollamaHostUrl", "http://localhost:11434")} onChange={(e) => updateField("ollama", "ollamaHostUrl", e.target.value)} inputClassName="text-xs py-1.5" />
          <TextField label="Default Model" value={get("ollama", "ollamaDefaultModel", "llama3.2")} onChange={(e) => updateField("ollama", "ollamaDefaultModel", e.target.value)} inputClassName="text-xs py-1.5" />
          <TextField label="Context Length" type="number" value={get("ollama", "ollamaContextLength", 4096)} onChange={(e) => updateField("ollama", "ollamaContextLength", Number(e.target.value))} suffix="tokens" inputClassName="text-xs py-1.5" />
          <FieldRow label="CUDA Enabled">
            <Toggle checked={!!get("ollama", "ollamaCudaEnabled", true)} onChange={(v) => updateField("ollama", "ollamaCudaEnabled", v)} />
          </FieldRow>
          <div className="pt-2">
            <Button variant="outline" size="sm" onClick={() => onTestConn("ollama")} className="bg-[#a78bfa]/10 hover:bg-[#a78bfa]/20 text-[#a78bfa] border-[#a78bfa]/20 h-auto text-[10px] py-1 px-3 w-full">
              {connectionResults["ollama"]?.testing ? <Loader2 className="w-3 h-3 animate-spin" /> : <Wifi className="w-3 h-3" />} Test Ollama Connection
            </Button>
            {connectionResults["ollama"]?.message && (
              <p className={`text-[10px] mt-1.5 ${connectionResults["ollama"]?.valid ? "text-[#10b981]" : "text-red-400"}`}>{connectionResults["ollama"].message}</p>
            )}
          </div>
        </Card>
        <Card className="bg-[#0B0E14] border-gray-800 p-4 space-y-3 md:col-span-2">
          <h4 className="text-xs font-bold text-gray-200 uppercase tracking-wider mb-2">Drift Detection</h4>
          <div className="grid grid-cols-2 gap-4">
            <FieldRow label="Drift Detection Enabled">
              <Toggle checked={!!get("ml", "driftDetectionEnabled", true)} onChange={(v) => updateField("ml", "driftDetectionEnabled", v)} />
            </FieldRow>
            <TextField label="Drift Threshold" type="number" value={get("ml", "driftThreshold", 0.15)} onChange={(e) => updateField("ml", "driftThreshold", parseFloat(e.target.value))} suffix="ratio" inputClassName="text-xs py-1.5" />
          </div>
        </Card>
      </div>
      <div className="flex gap-3">
        <Button variant="primary" size="sm" leftIcon={Save} onClick={() => { onSave("ml"); onSave("ollama"); }} disabled={saving} className="bg-[#06b6d4] hover:bg-[#0891b2] text-black font-bold text-xs">{saving ? "Saving..." : "Save AI/ML Config"}</Button>
        <Button variant="secondary" size="sm" leftIcon={RotateCcw} onClick={() => { onReset("ml"); onReset("ollama"); }} className="text-xs border-gray-700 text-gray-400">Reset</Button>
      </div>
    </div>
  );

  // ── Tab: Agents ──────────────────────────────────────────────────
  const renderAgents = () => {
    const agentToggles = [
      { key: "marketDataAgent",  label: "Market Data Agent",    desc: "Live feed ingestion and normalization" },
      { key: "riskAgent",        label: "Risk Agent",            desc: "Real-time position risk monitoring" },
      { key: "signalEngine",     label: "Signal Engine",         desc: "ML-based signal generation" },
      { key: "patternAI",        label: "Pattern AI",            desc: "Chart pattern detection (CNN)" },
      { key: "youtubeAgent",     label: "YouTube Agent",         desc: "Transcript ingestion and knowledge base" },
      { key: "driftMonitor",     label: "Drift Monitor",         desc: "Model performance drift detection" },
      { key: "flywheelEngine",   label: "Flywheel Engine",       desc: "Feedback loop for ML self-improvement" },
      { key: "openclawBridge",   label: "OpenClaw Bridge",       desc: "Multi-agent swarm orchestration" },
    ];
    return (
      <div className="space-y-6 animate-in fade-in duration-300">
        <SectionHeader icon={Bot} title="Agent Configuration" sub="Enable/disable individual agents and set operational limits." />
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <Card className="bg-[#0B0E14] border-gray-800 p-4 space-y-3">
            <h4 className="text-xs font-bold text-[#06b6d4] uppercase tracking-wider mb-2">Agent Switches</h4>
            {agentToggles.map((a) => (
              <FieldRow key={a.key} label={<div><div className="text-xs text-gray-200 font-medium">{a.label}</div><div className="text-[10px] text-gray-600">{a.desc}</div></div>}>
                <Toggle checked={!!get("agents", a.key, true)} onChange={(v) => updateField("agents", a.key, v)} />
              </FieldRow>
            ))}
          </Card>
          <Card className="bg-[#0B0E14] border-gray-800 p-4 space-y-4">
            <h4 className="text-xs font-bold text-[#10b981] uppercase tracking-wider">Operational Limits</h4>
            <TextField label="Max Concurrent Agents" type="number" value={get("agents", "maxConcurrentAgents", 4)} onChange={(e) => updateField("agents", "maxConcurrentAgents", Number(e.target.value))} inputClassName="text-xs py-1.5" />
            <TextField label="Agent Timeout" type="number" value={get("agents", "agentTimeout", 30)} onChange={(e) => updateField("agents", "agentTimeout", Number(e.target.value))} suffix="sec" inputClassName="text-xs py-1.5" />
            <TextField label="Scanner Interval" type="number" value={get("agents", "scannerInterval", 300)} onChange={(e) => updateField("agents", "scannerInterval", Number(e.target.value))} suffix="sec" inputClassName="text-xs py-1.5" />
            <FieldRow label="Auto-Restart Crashed Agents">
              <Toggle checked={!!get("agents", "autoRestart", true)} onChange={(v) => updateField("agents", "autoRestart", v)} />
            </FieldRow>
            <div className="border-t border-gray-800 pt-3">
              <h4 className="text-xs font-bold text-[#f59e0b] uppercase tracking-wider mb-3">OpenClaw Bridge</h4>
              <TextField label="WS URL" value={get("openclaw", "openclawWsUrl")} onChange={(e) => updateField("openclaw", "openclawWsUrl", e.target.value)} inputClassName="text-xs py-1.5" />
              <TextField label="API Key" type="password" value={get("openclaw", "openclawApiKey")} onChange={(e) => updateField("openclaw", "openclawApiKey", e.target.value)} inputClassName="text-xs py-1.5 mt-3" />
              <TextField label="Reconnect Interval" type="number" value={get("openclaw", "openclawReconnectInterval", 5)} onChange={(e) => updateField("openclaw", "openclawReconnectInterval", Number(e.target.value))} suffix="sec" inputClassName="text-xs py-1.5 mt-3" />
            </div>
          </Card>
        </div>
        <div className="flex gap-3">
          <Button variant="primary" size="sm" leftIcon={Save} onClick={() => { onSave("agents"); onSave("openclaw"); }} disabled={saving} className="bg-[#06b6d4] hover:bg-[#0891b2] text-black font-bold text-xs">{saving ? "Saving..." : "Save Agent Config"}</Button>
          <Button variant="secondary" size="sm" leftIcon={RotateCcw} onClick={() => { onReset("agents"); onReset("openclaw"); }} className="text-xs border-gray-700 text-gray-400">Reset</Button>
        </div>
      </div>
    );
  };

  // ── Tab: Data Sources ────────────────────────────────────────
  // const renderDataSources = () => (
  //   <div className="space-y-6 animate-in fade-in duration-300">
  //     <SectionHeader icon={Database} title="Data & Feed Management" sub="Configure data refresh intervals and external sources." />
  //     <div className="grid grid-cols-1 md:grid-cols-2 gap-4 max-w-3xl">
  //       <Card className="bg-[#0B0E14] border-gray-800 p-4 space-y-4">
  //         <h4 className="text-xs font-bold text-gray-200 uppercase tracking-wider">Refresh Settings</h4>
  //         <TextField label="Data Refresh Interval" type="number" value={get("dataSources", "refreshIntervalSeconds", 300)} onChange={(e) => updateField("dataSources", "refreshIntervalSeconds", Number(e.target.value))} suffix="sec" inputClassName="text-xs py-1.5" />
  //         <TextField label="StockGeist API Key" type="password" value={get("dataSources", "stockgeistApiKey")} onChange={(e) => updateField("dataSources", "stockgeistApiKey", e.target.value)} inputClassName="text-xs py-1.5" />
  //       </Card>
  //       <Card className="bg-[#0B0E14] border-gray-800 p-4 space-y-4">
  //         <h4 className="text-xs font-bold text-gray-200 uppercase tracking-wider">FinViz Screener</h4>
  //         <TextField label="Filters" value={get("finvizScreener", "finvizFilters", "")} onChange={(e) => updateField("finvizScreener", "finvizFilters", e.target.value)} inputClassName="text-xs py-1.5" />
  //         <TextField label="Scan Interval" type="number" value={get("finvizScreener", "scanInterval", 300)} onChange={(e) => updateField("finvizScreener", "scanInterval", Number(e.target.value))} suffix="sec" inputClassName="text-xs py-1.5" />
  //       </Card>
  //       <Card className="bg-[#0B0E14] border-gray-800 p-4 space-y-4">
  //         <h4 className="text-xs font-bold text-gray-200 uppercase tracking-wider">TradingView</h4>
  //         <TextField label="Webhook Key" type="password" value={get("tradingview", "webhookKey")} onChange={(e) => updateField("tradingview", "webhookKey", e.target.value)} inputClassName="text-xs py-1.5" />
  //         <Select label="Alert Format" value={get("tradingview", "alertFormat", "json")} options={["json", "text", "csv"]} onChange={(v) => updateField("tradingview", "alertFormat", v)} selectClassName="text-xs py-1.5" />
  //       </Card>
  //     </div>
  //     <div className="flex gap-3">
  //       <Button variant="primary" size="sm" leftIcon={Save} onClick={() => { onSave("dataSources"); onSave("finvizScreener"); onSave("tradingview"); }} disabled={saving} className="bg-[#06b6d4] hover:bg-[#0891b2] text-black font-bold text-xs">{saving ? "Saving..." : "Save Data Sources"}</Button>
  //     </div>
  //   </div>
  // );

  // ── Tab: Notifications ──────────────────────────────────────
  const renderNotifications = () => {
    const alertToggles = [
      { key: "tradeAlerts",        label: "Trade Executions",         desc: "Alerts for filled orders, partials, and rejections" },
      { key: "signalAlerts",       label: "Signal Alerts",            desc: "When new high-confidence patterns emerge" },
      { key: "riskAlerts",         label: "Risk Threshold Warnings",  desc: "When daily drawdown approaches limits" },
      { key: "agentStatusAlerts",  label: "Agent Status Alerts",      desc: "Critical alerts for agent crashes or disconnects" },
      { key: "dailySummary",       label: "End of Day Summary",       desc: "Daily PnL and system performance report" },
    ];
    return (
      <div className="space-y-6 animate-in fade-in duration-300">
        <SectionHeader icon={Bell} title="Notification Routing" sub="Configure which events trigger alerts." />
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 max-w-3xl">
          <Card className="bg-[#0B0E14] border-gray-800 p-4 space-y-3">
            <h4 className="text-xs font-bold text-[#06b6d4] uppercase tracking-wider mb-2">Alert Types</h4>
            {alertToggles.map((n) => (
              <FieldRow key={n.key} label={<div><div className="text-xs text-gray-200">{n.label}</div><div className="text-[10px] text-gray-600">{n.desc}</div></div>}>
                <Toggle checked={!!get("notifications", n.key, false)} onChange={(v) => updateField("notifications", n.key, v)} />
              </FieldRow>
            ))}
          </Card>
          <Card className="bg-[#0B0E14] border-gray-800 p-4 space-y-4">
            <h4 className="text-xs font-bold text-[#10b981] uppercase tracking-wider">Channels</h4>
            <TextField label="Discord Webhook URL" type="password" value={get("notifications", "discordWebhookUrl")} onChange={(e) => updateField("notifications", "discordWebhookUrl", e.target.value)} inputClassName="text-xs py-1.5" />
            <TextField label="Slack Webhook URL" type="password" value={get("notifications", "slackWebhookUrl")} onChange={(e) => updateField("notifications", "slackWebhookUrl", e.target.value)} inputClassName="text-xs py-1.5" />
            <TextField label="Telegram Bot Token" type="password" value={get("notifications", "telegramBotToken")} onChange={(e) => updateField("notifications", "telegramBotToken", e.target.value)} inputClassName="text-xs py-1.5" />
            <TextField label="Telegram Chat ID" value={get("notifications", "telegramChatId")} onChange={(e) => updateField("notifications", "telegramChatId", e.target.value)} inputClassName="text-xs py-1.5" />
          </Card>
        </div>
        <div className="flex gap-3">
          <Button variant="primary" size="sm" leftIcon={Save} onClick={() => onSave("notifications")} disabled={saving} className="bg-[#06b6d4] hover:bg-[#0891b2] text-black font-bold text-xs">{saving ? "Saving..." : "Save Notifications"}</Button>
          <Button variant="secondary" size="sm" leftIcon={RotateCcw} onClick={() => onReset("notifications")} className="text-xs border-gray-700 text-gray-400">Reset</Button>
        </div>
      </div>
    );
  };



  // --- Tab: Data Sources ------------------------------------------------
  const renderDataSources = () => {
    const sources = [
      { key: "alpacaMarketData",  label: "Alpaca Market Data",  fields: ["apiUrl", "wsUrl"] },
      { key: "polygon",           label: "Polygon.io",          fields: ["apiKey", "wsEnabled"] },
      { key: "unusualWhales",     label: "Unusual Whales",      fields: ["apiKey", "pollInterval"] },
      { key: "benzinga",          label: "Benzinga",            fields: ["apiKey", "newsEnabled"] },
      { key: "tradingView",       label: "TradingView",         fields: ["webhookSecret"] },
    ];
    return (
      <div className="space-y-6 animate-in fade-in duration-300">
        <SectionHeader icon={Database} title="Data Source Configuration" sub="Manage market data feeds and external data providers." />
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 max-w-3xl">
          {sources.map((s) => (
            <Card key={s.key} className="bg-[#080E14] border-gray-800 p-4 space-y-3">
              <div className="flex items-center justify-between">
                <h4 className="text-xs font-bold text-[#06b6d4] uppercase tracking-wider">{s.label}</h4>
                <Toggle checked={!!get("dataSources", `${s.key}.enabled`, false)} onChange={(v) => updateField("dataSources", `${s.key}.enabled`, v)} />
              </div>
              {s.fields.map((f) => (
                <TextField key={f} label={f.replace(/([A-Z])/g, " $1").trim()} type={f.toLowerCase().includes("key") || f.toLowerCase().includes("secret") ? "password" : "text"} value={get("dataSources", `${s.key}.${f}`) || ""} onChange={(e) => updateField("dataSources", `${s.key}.${f}`, e.target.value)} inputClassName="text-xs" />
              ))}
              <Button variant="ghost" size="xs" leftIcon={Zap} onClick={() => testConnection("dataSources", s.key)} className="text-xs text-gray-400 hover:text-[#06b6d4]">Test</Button>
            </Card>
          ))}
        </div>
        <div className="flex gap-3">
          <Button variant="primary" size="sm" leftIcon={Save} onClick={() => { onSave("dataSources"); }} disabled={saving} className="bg-[#06b6d4] hover:bg-[#0891b2] text-black font-bold">Save</Button>
          <Button variant="secondary" size="sm" leftIcon={RotateCcw} onClick={() => onReset("dataSources")} className="text-xs border-gray-700 text-gray-400">Reset</Button>
        </div>
      </div>
    );
  };

  // --- Tab: Appearance ---------------------------------------------------
  const renderAppearance = () => {
    const themes = ["dark", "midnight", "terminal", "light"];
    const densities = ["compact", "comfortable", "spacious"];
    return (
      <div className="space-y-6 animate-in fade-in duration-300">
        <SectionHeader icon={Palette} title="Appearance & Display" sub="Customize the look and feel of your trading dashboard." />
        <Card className="bg-[#080E14] border-gray-800 p-4 space-y-4 max-w-xl">
          <h4 className="text-xs font-bold text-[#06b6d4] uppercase tracking-wider mb-2">Theme & Layout</h4>
          <FieldRow label="Theme">
            <div className="flex gap-2">
              {themes.map((t) => (
                <button key={t} onClick={() => updateField("appearance", "theme", t)} className={`px-3 py-1 text-xs rounded border ${get("appearance", "theme", "dark") === t ? "bg-[#06b6d4] text-black border-[#06b6d4] font-bold" : "border-gray-700 text-gray-400 hover:border-gray-500"}`}>{t}</button>
              ))}
            </div>
          </FieldRow>
          <FieldRow label="Density">
            <div className="flex gap-2">
              {densities.map((d) => (
                <button key={d} onClick={() => updateField("appearance", "density", d)} className={`px-3 py-1 text-xs rounded border ${get("appearance", "density", "compact") === d ? "bg-[#06b6d4] text-black border-[#06b6d4] font-bold" : "border-gray-700 text-gray-400 hover:border-gray-500"}`}>{d}</button>
              ))}
            </div>
          </FieldRow>
          <TextField label="Chart Default Timeframe" value={get("appearance", "chartTimeframe", "5m")} onChange={(e) => updateField("appearance", "chartTimeframe", e.target.value)} />
          <FieldRow label="Show PnL in Header">
            <Toggle checked={!!get("appearance", "showPnlHeader", true)} onChange={(v) => updateField("appearance", "showPnlHeader", v)} />
          </FieldRow>
          <FieldRow label="Enable Animations">
            <Toggle checked={!!get("appearance", "animations", true)} onChange={(v) => updateField("appearance", "animations", v)} />
          </FieldRow>
          <FieldRow label="Sound Alerts">
            <Toggle checked={!!get("appearance", "soundAlerts", false)} onChange={(v) => updateField("appearance", "soundAlerts", v)} />
          </FieldRow>
        </Card>
        <div className="flex gap-3">
          <Button variant="primary" size="sm" leftIcon={Save} onClick={() => onSave("appearance")} disabled={saving} className="bg-[#06b6d4] hover:bg-[#0891b2] text-black font-bold">Save</Button>
          <Button variant="secondary" size="sm" leftIcon={RotateCcw} onClick={() => onReset("appearance")} className="text-xs border-gray-700 text-gray-400">Reset</Button>
        </div>
      </div>
    );
  };

  // --- Tab: Audit Log ----------------------------------------------------
  const renderAuditLog = () => {
    const [logs, setLogs] = useState([]);
    const [logLoading, setLogLoading] = useState(true);
    useEffect(() => {
      api.get("/api/v1/settings/audit-log").then((r) => { setLogs(r.data?.logs || []); setLogLoading(false); }).catch(() => setLogLoading(false));
    }, []);
    return (
      <div className="space-y-6 animate-in fade-in duration-300">
        <SectionHeader icon={FileText} title="Audit Log" sub="Track all settings changes and system events." />
        <Card className="bg-[#080E14] border-gray-800 p-4">
          {logLoading ? (
            <div className="flex items-center gap-2 text-gray-500 text-xs"><Loader2 className="w-4 h-4 animate-spin" /> Loading audit log...</div>
          ) : logs.length === 0 ? (
            <p className="text-gray-500 text-xs">No audit entries found.</p>
          ) : (
            <div className="space-y-1 max-h-[500px] overflow-y-auto">
              {logs.map((log, i) => (
                <div key={i} className="flex items-center gap-3 py-1.5 px-2 text-xs border-b border-gray-800/50 hover:bg-gray-800/30">
                  <span className="text-gray-500 font-mono w-36 shrink-0">{new Date(log.timestamp).toLocaleString()}</span>
                  <span className={`w-16 shrink-0 font-bold uppercase ${log.action === "update" ? "text-yellow-500" : log.action === "reset" ? "text-red-400" : "text-[#06b6d4]"}`}>{log.action}</span>
                  <span className="text-gray-300">{log.category}</span>
                  <span className="text-gray-500 truncate">{log.detail || ""}</span>
                </div>
              ))}
            </div>
          )}
        </Card>
        <div className="flex gap-3">
          <Button variant="secondary" size="sm" leftIcon={Download} onClick={() => { const blob = new Blob([JSON.stringify(logs, null, 2)], { type: "application/json" }); const a = document.createElement("a"); a.href = URL.createObjectURL(blob); a.download = "audit-log.json"; a.click(); }} className="text-xs border-gray-700 text-gray-400">Export Log</Button>
        </div>
      </div>
    );
  };


    // --- Tab: Alignment Engine -----------------------------------------------
  const renderAlignment = () => (
    <div className="space-y-6 animate-in fade-in duration-300">
      <SectionHeader icon={ShieldAlert} color="#f59e0b" title="Alignment Engine" sub="Constitutive alignment controls — 6 patterns from the Soul Document architecture." />
      <Card className="bg-[#0B0E14] border-gray-800 p-4 space-y-4 max-w-3xl">
        <h4 className="text-xs font-bold text-[#f59e0b] uppercase tracking-wider mb-2">Engine Mode</h4>
        <FieldRow label="Alignment Enabled">
          <Toggle checked={!!get("alignment", "enabled", true)} onChange={(v) => updateField("alignment", "enabled", v)} />
        </FieldRow>
        <Select label="Enforcement Mode" value={get("alignment", "mode", "SHADOW")} options={["OFF", "SHADOW", "PAPER_ENFORCE", "LIVE_ENFORCE"]} onChange={(v) => updateField("alignment", "mode", v)} selectClassName="text-xs py-1.5" />
      </Card>
      <Card className="bg-[#0B0E14] border-gray-800 p-4 space-y-3 max-w-3xl">
        <h4 className="text-xs font-bold text-[#f59e0b] uppercase tracking-wider mb-2">Active Checks</h4>
        <FieldRow label="Bright Lines (hard-coded constitutional limits)">
          <Toggle checked={!!get("alignment", "checkBrightLines", true)} onChange={(v) => updateField("alignment", "checkBrightLines", v)} />
        </FieldRow>
        <FieldRow label="Trading Bible (identity-based filter)">
          <Toggle checked={!!get("alignment", "checkBible", true)} onChange={(v) => updateField("alignment", "checkBible", v)} />
        </FieldRow>
        <FieldRow label="Metacognition (rationalization detection)">
          <Toggle checked={!!get("alignment", "checkMetacognition", true)} onChange={(v) => updateField("alignment", "checkMetacognition", v)} />
        </FieldRow>
        <FieldRow label="Swarm Critique (adversarial role approval)">
          <Toggle checked={!!get("alignment", "checkCritique", true)} onChange={(v) => updateField("alignment", "checkCritique", v)} />
        </FieldRow>
      </Card>
      <Card className="bg-[#0B0E14] border-gray-800 p-4 space-y-3 max-w-3xl">
        <h4 className="text-xs font-bold text-red-400 uppercase tracking-wider mb-2">Operating Limits</h4>
        <TextField label="Max Position %" type="number" value={get("alignment", "maxPositionPct", 10)} onChange={(e) => updateField("alignment", "maxPositionPct", Math.min(10, Number(e.target.value)))} suffix="% (cap: 10%)" inputClassName="text-xs py-1.5" />
        <TextField label="Max Heat %" type="number" value={get("alignment", "maxHeatPct", 25)} onChange={(e) => updateField("alignment", "maxHeatPct", Math.min(25, Number(e.target.value)))} suffix="% (cap: 25%)" inputClassName="text-xs py-1.5" />
        <TextField label="Max Drawdown %" type="number" value={get("alignment", "maxDrawdownPct", 15)} onChange={(e) => updateField("alignment", "maxDrawdownPct", Math.min(15, Number(e.target.value)))} suffix="% (cap: 15%)" inputClassName="text-xs py-1.5" />
        <TextField label="Daily Trade Cap" type="number" value={get("alignment", "dailyTradeCap", 20)} onChange={(e) => updateField("alignment", "dailyTradeCap", Number(e.target.value))} inputClassName="text-xs py-1.5" />
        <TextField label="Rapid-Fire Window" type="number" value={get("alignment", "rapidFireWindowSec", 30)} onChange={(e) => updateField("alignment", "rapidFireWindowSec", Number(e.target.value))} suffix="sec" inputClassName="text-xs py-1.5" />
        <TextField label="Critique Approval Threshold" type="number" value={get("alignment", "critiqueThreshold", 60)} onChange={(e) => updateField("alignment", "critiqueThreshold", Number(e.target.value))} suffix="%" inputClassName="text-xs py-1.5" />
      </Card>
      <div className="flex gap-3">
        <Button variant="primary" size="sm" leftIcon={Save} onClick={() => onSave("alignment")} disabled={saving} className="bg-[#f59e0b] hover:bg-[#d97706] text-black font-bold text-xs">{saving ? "Saving..." : "Save Alignment"}</Button>
        <Button variant="secondary" size="sm" leftIcon={RotateCcw} onClick={() => onReset("alignment")} className="text-xs border-gray-700 text-gray-400">Reset</Button>
      </div>
    </div>
  );

  // --- Tab definitions ---------------------------------------------------
  const tabs = [
    { key: "profile",        label: "Profile",          icon: User,         render: renderProfile },
    { key: "apiKeys",        label: "API Keys",         icon: Key,          render: renderApiKeys },
    { key: "trading",        label: "Trading",          icon: TrendingUp,   render: renderTradingParams },
    { key: "risk",           label: "Risk",             icon: Shield,       render: renderRiskManagement },
    { key: "aiml",           label: "AI / ML",          icon: Brain,        render: renderAiMl },
    { key: "agents",         label: "Agents",           icon: Bot,          render: renderAgents },
    { key: "dataSources",    label: "Data Sources",     icon: Database,     render: renderDataSources },
    { key: "notifications",  label: "Notifications",    icon: Bell,         render: renderNotifications },
    { key: "appearance",     label: "Appearance",       icon: Palette,      render: renderAppearance },
    { key: "auditLog",       label: "Audit Log",        icon: FileText,     render: renderAuditLog },
        { key: "alignment",     label: "Alignment",      icon: ShieldAlert, render: renderAlignment },
  ];

  // --- Main layout -------------------------------------------------------
  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="w-6 h-6 animate-spin text-[#06b6d4]" />
        <span className="ml-2 text-gray-400 text-sm">Loading settings...</span>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-[#040810] text-gray-100 p-4 md:p-6">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-xl font-bold text-white flex items-center gap-2"><Settings2 className="w-5 h-5 text-[#06b6d4]" /> Settings</h1>
          <p className="text-xs text-gray-500 mt-1">Configure your elite trading system</p>
        </div>
        <div className="flex gap-2">
          <Button variant="ghost" size="sm" leftIcon={Download} onClick={async () => { const r = await api.get("/api/v1/settings/export"); const blob = new Blob([JSON.stringify(r.data, null, 2)], { type: "application/json" }); const a = document.createElement("a"); a.href = URL.createObjectURL(blob); a.download = "settings-export.json"; a.click(); }} className="text-xs text-gray-400">Export</Button>
          <Button variant="ghost" size="sm" leftIcon={Upload} onClick={() => { const input = document.createElement("input"); input.type = "file"; input.accept = ".json"; input.onchange = async (e) => { const file = e.target.files[0]; if (!file) return; const text = await file.text(); await api.post("/api/v1/settings/import", JSON.parse(text)); window.location.reload(); }; input.click(); }} className="text-xs text-gray-400">Import</Button>
        </div>
      </div>

      {/* Status banner */}
      {error && <div className="mb-4 p-3 bg-red-900/30 border border-red-800 rounded text-red-300 text-xs flex items-center gap-2"><AlertTriangle className="w-4 h-4" />{error}</div>}
      {saveSuccess && <div className="mb-4 p-3 bg-emerald-900/30 border border-emerald-800 rounded text-emerald-300 text-xs flex items-center gap-2"><CheckCircle2 className="w-4 h-4" />Settings saved successfully</div>}

      {/* Tab nav + content */}
      <div className="flex gap-6">
        {/* Sidebar tabs */}
        <nav className="w-48 shrink-0 space-y-1">
          {tabs.map((t) => {
            const Icon = t.icon;
            const isActive = t.key === tab;
            return (
              <button key={t.key} onClick={() => setTab(t.key)} className={`w-full flex items-center gap-2 px-3 py-2 rounded text-xs font-medium transition-colors ${isActive ? "bg-[#06b6d4]/10 text-[#06b6d4] border-l-2 border-[#06b6d4]" : "text-gray-400 hover:text-gray-200 hover:bg-gray-800/50"}`}>
                <Icon className="w-4 h-4" />{t.label}
              </button>
            );
          })}
        </nav>

        {/* Content area */}
        <div className="flex-1 min-w-0">
          {activeTab.render()}
        </div>
      </div>
    </div>
  );
};