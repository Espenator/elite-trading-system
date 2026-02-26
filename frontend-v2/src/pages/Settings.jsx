import React, { useState } from "react";
import Card from "../components/ui/Card";
import Button from "../components/ui/Button";
import PageHeader from "../components/ui/PageHeader";
import Toggle from "../components/ui/Toggle";
import TextField from "../components/ui/TextField";
import Select from "../components/ui/Select";
import Badge from "../components/ui/Badge";
import { useApi } from "../hooks/useApi";
import { toast } from "react-toastify";
import {
  User,
  Key,
  Activity,
  Bell,
  Layout,
  Cpu,
  Database,
  ShieldAlert,
  History,
  Save,
  RefreshCw,
  CheckCircle2,
  AlertTriangle,
  Settings,
  Terminal,
  Sliders,
} from "lucide-react";

export default function SettingsPage() {
  const [activeTab, setActiveTab] = useState("api-keys");

  const handleSave = () => {
    toast.success("Configuration saved successfully", {
      position: "bottom-right",
      theme: "dark",
    });
  };

  const navItems = [
    { id: "profile", label: "User Profile", icon: User },
    { id: "api-keys", label: "API Keys", icon: Key },
    { id: "trading-params", label: "Trading Params", icon: Activity },
    { id: "risk-limits", label: "Risk Limits", icon: ShieldAlert },
    { id: "ai-ml", label: "AI/ML Config", icon: Cpu },
    { id: "data-sources", label: "Data Sources", icon: Database },
    { id: "notifications", label: "Notifications", icon: Bell },
    { id: "appearance", label: "Appearance", icon: Layout },
    { id: "audit-log", label: "Audit Log", icon: History },
  ];

  // Tab Content Renderers
  const renderProfile = () => (
    <div className="space-y-6 animate-in fade-in duration-300">
      <div>
        <h3 className="text-sm font-bold text-white mb-1 uppercase tracking-wide flex items-center gap-2">
          <User className="w-4 h-4 text-[#06b6d4]" /> Identity & Localization
        </h3>
        <p className="text-xs text-gray-500 mb-4">
          Manage your trader identity and locale preferences.
        </p>
      </div>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4 max-w-2xl">
        <TextField label="Display Name" defaultValue="Espen Schiefloe" inputClassName="text-xs py-1.5 rounded-md" />
        <TextField
          label="Email Address"
          type="email"
          defaultValue="espen@embodier.ai"
          inputClassName="text-xs py-1.5 rounded-md"
        />
        <Select
          label="Timezone"
          options={["America/New_York (EST)", "Europe/Oslo (CET)", "UTC"]}
          defaultValue="America/New_York (EST)"
          selectClassName="text-xs py-1.5 rounded-md"
        />
        <TextField label="Base Currency" defaultValue="USD" inputClassName="text-xs py-1.5 rounded-md" />
      </div>
    </div>
  );

  const renderApiKeys = () => {
    const providers = [
      {
        id: "alpaca",
        name: "Alpaca Trading API",
        status: "Connected",
        badge: "bg-[#10b981]/10 text-[#10b981] border-[#10b981]/20",
        key: "PK8V2****************",
        secret: "********************************",
      },
      {
        id: "unusual_whales",
        name: "Unusual Whales",
        status: "Connected",
        badge: "bg-[#10b981]/10 text-[#10b981] border-[#10b981]/20",
        key: "UW_882****************",
        secret: "********************************",
      },
      {
        id: "polygon",
        name: "Polygon.io",
        status: "Degraded",
        badge: "bg-[#f59e0b]/10 text-[#f59e0b] border-[#f59e0b]/20",
        key: "POLY_****************",
        secret: "********************************",
      },
      {
        id: "openai",
        name: "OpenAI (GPT-4)",
        status: "Connected",
        badge: "bg-[#10b981]/10 text-[#10b981] border-[#10b981]/20",
        key: "sk-proj-**************",
        secret: "********************************",
      },
    ];

    return (
      <div className="space-y-6 animate-in fade-in duration-300">
        <div className="flex justify-between items-end">
          <div>
            <h3 className="text-sm font-bold text-white mb-1 uppercase tracking-wide flex items-center gap-2">
              <Key className="w-4 h-4 text-[#06b6d4]" /> API Integrations
            </h3>
            <p className="text-xs text-gray-500">
              Manage connections to external brokers and data feeds.
            </p>
          </div>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          {providers.map((p) => (
            <Card
              key={p.id}
              className="bg-[#0B0E14] border-gray-800/60 p-4 relative overflow-hidden group"
            >
              <div className="absolute top-0 left-0 w-1 h-full bg-gradient-to-b from-[#06b6d4]/50 to-transparent opacity-50"></div>
              <div className="flex justify-between items-center mb-4">
                <span className="text-sm font-bold text-gray-200">
                  {p.name}
                </span>
                <Badge
                  variant={p.status === "Connected" ? "success" : "warning"}
                  size="sm"
                  className="flex items-center gap-1 uppercase"
                >
                  {p.status === "Connected" ? (
                    <CheckCircle2 className="w-3 h-3" />
                  ) : (
                    <AlertTriangle className="w-3 h-3" />
                  )}
                  {p.status}
                </Badge>
              </div>
              <div className="space-y-3">
                <TextField
                  label="API Key"
                  type="password"
                  defaultValue={p.key}
                  readOnly
                  inputClassName="text-xs py-1.5 bg-[#0a0a0f] border-gray-800/80"
                />
                <TextField
                  label="API Secret"
                  type="password"
                  defaultValue={p.secret}
                  readOnly
                  inputClassName="text-xs py-1.5 bg-[#0a0a0f] border-gray-800/80"
                />
                <div className="pt-2 flex gap-2">
                  <Button
                    variant="outline"
                    size="sm"
                    className="bg-[#06b6d4]/10 hover:bg-[#06b6d4]/20 text-[#06b6d4] border-[#06b6d4]/20 h-auto text-[10px] py-1 px-3"
                  >
                    Test Connection
                  </Button>
                  <Button
                    variant="secondary"
                    size="sm"
                    className="bg-gray-800/50 hover:bg-gray-700 text-gray-300 border-gray-700 h-auto text-[10px] py-1 px-3"
                  >
                    Edit Keys
                  </Button>
                </div>
              </div>
            </Card>
          ))}
        </div>
      </div>
    );
  };

  const renderTradingParams = () => (
    <div className="space-y-6 animate-in fade-in duration-300">
      <div>
        <h3 className="text-sm font-bold text-white mb-1 uppercase tracking-wide flex items-center gap-2">
          <Activity className="w-4 h-4 text-[#06b6d4]" /> Execution Parameters
        </h3>
        <p className="text-xs text-gray-500">
          Configure default sizing, targets, and operational limits.
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <Card className="bg-[#0B0E14] border-gray-800 p-4 space-y-4 md:col-span-1">
          <h4 className="text-xs font-bold text-[#06b6d4] uppercase tracking-wider mb-2 flex items-center gap-1">
            <Terminal className="w-3 h-3" /> Position Sizing
          </h4>
          <TextField label="Base Position Size" defaultValue="25,000" suffix="USD" inputClassName="text-xs py-1.5 rounded-md" />
          <TextField label="Max Position Size" defaultValue="100,000" suffix="USD" inputClassName="text-xs py-1.5 rounded-md" />
          <TextField label="Max Concurrent Positions" type="number" defaultValue="5" suffix="POS" inputClassName="text-xs py-1.5 rounded-md" />
        </Card>

        <Card className="bg-[#0B0E14] border-gray-800 p-4 space-y-4 md:col-span-1">
          <h4 className="text-xs font-bold text-[#f59e0b] uppercase tracking-wider mb-2 flex items-center gap-1">
            <Sliders className="w-3 h-3" /> Trade Management
          </h4>
          <TextField label="Default Stop Loss" defaultValue="1.0" suffix="ATR" inputClassName="text-xs py-1.5 rounded-md" />
          <TextField label="Primary Target (TP1)" defaultValue="1.5" suffix="R" inputClassName="text-xs py-1.5 rounded-md" />
          <TextField label="Secondary Target (TP2)" defaultValue="3.0" suffix="R" inputClassName="text-xs py-1.5 rounded-md" />
        </Card>

        <Card className="bg-[#0B0E14] border-gray-800 p-4 space-y-4 md:col-span-1">
          <h4 className="text-xs font-bold text-[#10b981] uppercase tracking-wider mb-2 flex items-center gap-1">
            <Activity className="w-3 h-3" /> Risk Profile
          </h4>
          <TextField label="Max Daily Risk" defaultValue="2.0" suffix="%" inputClassName="text-xs py-1.5 rounded-md" />
          <TextField label="Max Risk Per Trade" defaultValue="0.5" suffix="%" inputClassName="text-xs py-1.5 rounded-md" />
          <Toggle
            checked={true}
            onChange={() => {}}
            label="Auto-Scale Sizing"
            className="pt-2"
          />
        </Card>
      </div>
    </div>
  );

  const renderRiskLimits = () => (
    <div className="space-y-6 animate-in fade-in duration-300">
      <div>
        <h3 className="text-sm font-bold text-white mb-1 uppercase tracking-wide flex items-center gap-2">
          <ShieldAlert className="w-4 h-4 text-red-500" /> Circuit Breakers &
          Risk Limits
        </h3>
        <p className="text-xs text-gray-500">
          Hard halts and emergency killswitches for the automated systems.
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <Card className="bg-red-950/10 border-red-900/30 p-4 space-y-4">
          <h4 className="text-xs font-bold text-red-400 uppercase tracking-wider">
            Market Conditions Halts
          </h4>
          <div className="p-2 bg-[#0a0a0f] rounded border border-gray-800/80">
            <Toggle
              checked={true}
              onChange={() => {}}
              label="VIX Spike Halt"
              description="Halt trading if VIX jumps > 15% intraday"
            />
          </div>
          <div className="p-2 bg-[#0a0a0f] rounded border border-gray-800/80">
            <Toggle
              checked={true}
              onChange={() => {}}
              label="Flash Crash Protection"
              description="Pause if SPY drops > 2% in 15 mins"
            />
          </div>
        </Card>

        <Card className="bg-amber-950/10 border-amber-900/30 p-4 space-y-4">
          <h4 className="text-xs font-bold text-amber-400 uppercase tracking-wider">
            Account Drawdown Halts
          </h4>
          <div className="p-2 bg-[#0a0a0f] rounded border border-gray-800/80">
            <Toggle
              checked={true}
              onChange={() => {}}
              label="Daily Loss Limit Halt"
              description="Killswitch at -$2,500 daily PnL"
            />
          </div>
          <TextField
            label="Max Correlation Limit"
            defaultValue="0.75"
            suffix="PEARSON"
            inputClassName="text-xs py-1.5 rounded-md"
          />
        </Card>
      </div>
    </div>
  );

  const renderNotifications = () => {
    const notifs = [
      {
        id: 1,
        title: "Trade Executions",
        desc: "Alerts for filled orders, partials, and rejections",
        status: true,
      },
      {
        id: 2,
        title: "Pattern Scanner Alerts",
        desc: "When new high-confidence patterns emerge",
        status: true,
      },
      {
        id: 3,
        title: "Risk Threshold Warnings",
        desc: "When daily drawdown approaches limits",
        status: true,
      },
      {
        id: 4,
        title: "API Disconnects",
        desc: "Critical alerts for feed loss or broker disconnects",
        status: true,
      },
      {
        id: 5,
        title: "Options Flow Anomalies",
        desc: "Large blocks or weird put/call ratios detected",
        status: false,
      },
      {
        id: 6,
        title: "End of Day Summary",
        desc: "Daily PnL and system performance report",
        status: true,
      },
    ];

    return (
      <div className="space-y-6 animate-in fade-in duration-300">
        <div>
          <h3 className="text-sm font-bold text-white mb-1 uppercase tracking-wide flex items-center gap-2">
            <Bell className="w-4 h-4 text-[#06b6d4]" /> Notification Routing
          </h3>
          <p className="text-xs text-gray-500">
            Configure which events trigger alerts to your devices.
          </p>
        </div>
        <div className="grid grid-cols-1 gap-2 max-w-3xl">
          {notifs.map((n) => (
            <div
              key={n.id}
              className="flex items-center justify-between p-3 bg-[#0B0E14] border border-gray-800/60 rounded-lg hover:border-gray-700 transition-colors"
            >
              <Toggle
                checked={n.status}
                onChange={() => {}}
                label={n.title}
                description={n.desc}
                className="flex-1"
              />
              <span className="text-[9px] uppercase tracking-wider text-gray-600 font-bold shrink-0 ml-4">
                Discord / SMS
              </span>
            </div>
          ))}
        </div>
      </div>
    );
  };

  const renderAppearance = () => (
    <div className="space-y-6 animate-in fade-in duration-300">
      <div>
        <h3 className="text-sm font-bold text-white mb-1 uppercase tracking-wide flex items-center gap-2">
          <Layout className="w-4 h-4 text-[#06b6d4]" /> Interface & Appearance
        </h3>
        <p className="text-xs text-gray-500">
          Customize the trading terminal aesthetic.
        </p>
      </div>

      <div className="space-y-4 max-w-2xl">
        <label className="text-[10px] font-semibold text-gray-400 uppercase tracking-wider">
          Terminal Theme
        </label>
        <div className="grid grid-cols-3 gap-4">
          <div className="bg-[#0a0a0f] border-2 border-[#06b6d4] rounded-lg p-4 cursor-pointer relative overflow-hidden">
            <div className="absolute top-1 right-2">
              <CheckCircle2 className="w-4 h-4 text-[#06b6d4]" />
            </div>
            <p className="text-xs font-bold text-white mb-2">
              Midnight Bloomberg
            </p>
            <div className="w-full h-12 bg-[#0B0E14] border border-gray-800 rounded flex gap-1 p-1">
              <div className="w-1/3 h-full bg-[#1A1D24] rounded-sm"></div>
              <div className="w-2/3 h-full bg-[#1A1D24] rounded-sm flex flex-col gap-1 p-1">
                <div className="h-1 bg-[#06b6d4]/50 w-full rounded-full"></div>
                <div className="h-1 bg-[#10b981]/50 w-3/4 rounded-full"></div>
              </div>
            </div>
          </div>
          <div className="bg-gray-900 border border-gray-800 rounded-lg p-4 cursor-pointer opacity-60 hover:opacity-100 transition-opacity">
            <p className="text-xs font-bold text-white mb-2">Classic Dark</p>
            <div className="w-full h-12 bg-gray-800 border border-gray-700 rounded p-1"></div>
          </div>
          <div className="bg-black border border-gray-900 rounded-lg p-4 cursor-pointer opacity-60 hover:opacity-100 transition-opacity">
            <p className="text-xs font-bold text-white mb-2">OLED Pure Black</p>
            <div className="w-full h-12 bg-[#050505] border border-gray-900 rounded p-1"></div>
          </div>
        </div>

        <div className="pt-4">
          <Select
            label="Data Density"
            options={[
              "Ultra Dense (Bloomberg Style)",
              "Comfortable (Web Style)",
              "Compact",
            ]}
            defaultValue="Ultra Dense (Bloomberg Style)"
            className="max-w-md"
            selectClassName="text-xs py-1.5"
          />
        </div>
      </div>
    </div>
  );

  const renderAiMlConfig = () => (
    <div className="space-y-6 animate-in fade-in duration-300">
      <div>
        <h3 className="text-sm font-bold text-white mb-1 uppercase tracking-wide flex items-center gap-2">
          <Cpu className="w-4 h-4 text-[#06b6d4]" /> Intelligence & Models
        </h3>
        <p className="text-xs text-gray-500">
          Tune the machine learning components and logic thresholds.
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6 max-w-4xl">
        <div className="space-y-4">
          <Select
            label="Primary Inference Model"
            options={[
              "GPT-4o (Default)",
              "Claude 3.5 Sonnet",
              "Local LLaMA-3-70B",
            ]}
            defaultValue="GPT-4o (Default)"
            selectClassName="text-xs py-1.5"
          />
          <TextField
            label="Min. Pattern Confidence Score"
            type="number"
            defaultValue="75"
            suffix="%"
            inputClassName="text-xs py-1.5 rounded-md"
          />
          <TextField
            label="Sentiment Analysis Lookback"
            type="number"
            defaultValue="24"
            suffix="HOURS"
            inputClassName="text-xs py-1.5 rounded-md"
          />
        </div>

        <Card className="bg-[#0B0E14] border-gray-800 p-4 space-y-4">
          <div className="flex items-center justify-between">
            <Toggle
              checked={true}
              onChange={() => {}}
              label="Flywheel Learning Loop"
              description="Feed trade outcomes back to the model"
            />
          </div>
          <div className="w-full h-[1px] bg-gray-800/60 my-2"></div>
          <div className="flex items-center justify-between">
            <Toggle
              checked={true}
              onChange={() => {}}
              label="Automated Regime Detection"
              description="Adapt strategies based on macro regime"
            />
          </div>
        </Card>
      </div>
    </div>
  );

  const renderAuditLog = () => (
    <div className="space-y-4 animate-in fade-in duration-300">
      <div className="flex justify-between items-center mb-2">
        <div>
          <h3 className="text-sm font-bold text-white mb-1 uppercase tracking-wide flex items-center gap-2">
            <History className="w-4 h-4 text-[#06b6d4]" /> System Audit Trail
          </h3>
          <p className="text-xs text-gray-500">
            Immutable log of system changes and critical events.
          </p>
        </div>
        <Button
          variant="secondary"
          size="sm"
          leftIcon={RefreshCw}
          className="bg-[#0B0E14] text-xs text-gray-300 border border-gray-800 hover:bg-gray-800 h-auto py-1 px-3"
        >
          Refresh
        </Button>
      </div>

      <div className="bg-[#0B0E14] border border-gray-800/80 rounded-lg overflow-hidden">
        <table className="w-full text-left border-collapse">
          <thead>
            <tr className="bg-[#131722] border-b border-gray-800">
              <th className="p-2 text-[10px] uppercase text-gray-500 tracking-wider w-32">
                Timestamp
              </th>
              <th className="p-2 text-[10px] uppercase text-gray-500 tracking-wider w-24">
                Category
              </th>
              <th className="p-2 text-[10px] uppercase text-gray-500 tracking-wider w-32">
                User/System
              </th>
              <th className="p-2 text-[10px] uppercase text-gray-500 tracking-wider">
                Event Details
              </th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-800/50 text-[11px] text-gray-300">
            <tr className="hover:bg-[#1A1D24]/50">
              <td className="p-2 text-gray-500">2026-02-25 10:42:11</td>
              <td className="p-2">
                <span className="text-amber-500">CONFIG</span>
              </td>
              <td className="p-2">Espen Schiefloe</td>
              <td className="p-2">
                Updated Trading Parameter: Max Daily Risk to 2.0%
              </td>
            </tr>
            <tr className="hover:bg-[#1A1D24]/50">
              <td className="p-2 text-gray-500">2026-02-25 09:15:00</td>
              <td className="p-2">
                <span className="text-[#06b6d4]">SYSTEM</span>
              </td>
              <td className="p-2">OpenClaw Bridge</td>
              <td className="p-2">
                WebSocket Reconnection Successful (Latency: 42ms)
              </td>
            </tr>
            <tr className="hover:bg-[#1A1D24]/50">
              <td className="p-2 text-gray-500">2026-02-24 18:30:22</td>
              <td className="p-2">
                <span className="text-emerald-500">SECURITY</span>
              </td>
              <td className="p-2">Espen Schiefloe</td>
              <td className="p-2">
                Successful Login from 104.28.112.4 (Asheville, NC)
              </td>
            </tr>
            <tr className="hover:bg-[#1A1D24]/50">
              <td className="p-2 text-gray-500">2026-02-24 15:05:10</td>
              <td className="p-2">
                <span className="text-red-500">RISK</span>
              </td>
              <td className="p-2">Auto-Killswitch</td>
              <td className="p-2">
                VIX Spike Detected ({">"}15%). New positions temporarily halted.
              </td>
            </tr>
            <tr className="hover:bg-[#1A1D24]/50">
              <td className="p-2 text-gray-500">2026-02-23 11:20:05</td>
              <td className="p-2">
                <span className="text-amber-500">CONFIG</span>
              </td>
              <td className="p-2">Espen Schiefloe</td>
              <td className="p-2">Updated Alpaca API Keys</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  );

  const renderDataSources = () => (
    <div className="space-y-6 animate-in fade-in duration-300">
      <div>
        <h3 className="text-sm font-bold text-white mb-1 uppercase tracking-wide flex items-center gap-2">
          <Database className="w-4 h-4 text-[#06b6d4]" /> Data & Feed Management
        </h3>
        <p className="text-xs text-gray-500">
          Manage priority and failovers for market data streams.
        </p>
      </div>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4 max-w-2xl">
        <Card className="bg-[#0B0E14] border-gray-800 p-4 space-y-3">
          <h4 className="text-xs font-bold text-gray-200 uppercase tracking-wider">
            Primary Pricing Feed
          </h4>
          <Select
            options={[
              "Polygon.io (Real-time SIP)",
              "Alpaca Data V2",
              "Interactive Brokers",
            ]}
            defaultValue="Polygon.io (Real-time SIP)"
            selectClassName="text-xs py-1.5"
          />
        </Card>
        <Card className="bg-[#0B0E14] border-gray-800 p-4 space-y-3">
          <h4 className="text-xs font-bold text-gray-200 uppercase tracking-wider">
            Options Flow Source
          </h4>
          <Select
            options={["Unusual Whales API", "CBOE LiveVol"]}
            defaultValue="Unusual Whales API"
            selectClassName="text-xs py-1.5"
          />
        </Card>
      </div>
    </div>
  );

  return (
    <div className="space-y-6">
      <PageHeader
        icon={Settings}
        title="System Settings"
        description="Configure global parameters, APIs, and risk rules."
      >
        <Button
          variant="primary"
          size="md"
          leftIcon={Save}
          onClick={handleSave}
          className="bg-[#06b6d4] hover:bg-[#0891b2] text-black font-bold text-xs h-auto py-1.5 px-4 shadow-[0_0_10px_rgba(6,182,212,0.3)]"
        >
          Save Changes
        </Button>
      </PageHeader>

      {/* Main Settings Layout Grid */}
      <div className="flex flex-col lg:flex-row gap-6">
        {/* Left Sidebar Navigation */}
        <div className="w-full lg:w-64 shrink-0 space-y-1">
          {navItems.map((item) => {
            const Icon = item.icon;
            const isActive = activeTab === item.id;
            return (
              <Button
                key={item.id}
                type="button"
                variant="ghost"
                onClick={() => setActiveTab(item.id)}
                className={`w-full justify-start gap-3 px-4 py-2.5 rounded-lg text-xs font-semibold uppercase tracking-wider border-r-2 transition-all duration-200 ${
                  isActive
                    ? "bg-[#06b6d4]/10 text-[#06b6d4] border-[#06b6d4]"
                    : "text-gray-500 hover:text-gray-300 hover:bg-gray-800/40 border-transparent"
                }`}
              >
                <Icon
                  className={`w-4 h-4 shrink-0 ${isActive ? "text-[#06b6d4]" : "text-gray-500"}`}
                />
                {item.label}
              </Button>
            );
          })}
        </div>

        {/* Right Content Area */}
        <div className="flex-1 bg-[#050608]/40 border border-gray-800/60 rounded-xl p-6 relative shadow-2xl overflow-hidden backdrop-blur-sm">
          {/* Subtle glow effect behind content */}
          <div className="absolute top-0 right-0 w-96 h-96 bg-[#06b6d4]/5 blur-[120px] rounded-full pointer-events-none"></div>

          <div className="relative z-10">
            {activeTab === "profile" && renderProfile()}
            {activeTab === "api-keys" && renderApiKeys()}
            {activeTab === "trading-params" && renderTradingParams()}
            {activeTab === "risk-limits" && renderRiskLimits()}
            {activeTab === "ai-ml" && renderAiMlConfig()}
            {activeTab === "notifications" && renderNotifications()}
            {activeTab === "appearance" && renderAppearance()}
            {activeTab === "audit-log" && renderAuditLog()}
            {activeTab === "data-sources" && renderDataSources()}
          </div>
        </div>
      </div>
    </div>
  );
}
