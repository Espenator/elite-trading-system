// SETTINGS PAGE - Embodier.ai Glass House Intelligence System
// GET/PUT /api/v1/settings - load and save user settings
import { useState, useEffect } from "react";
import {
  Settings as SettingsIcon,
  Shield,
  Key,
  Bell,
  Brain,
  Bot,
  TrendingUp,
  Save,
  RotateCcw,
  ChevronRight,
  AlertTriangle,
} from "lucide-react";
import Button from "../components/ui/Button";
import TextField from "../components/ui/TextField";
import Select from "../components/ui/Select";
import Toggle from "../components/ui/Toggle";
import Card from "../components/ui/Card";
import PageHeader from "../components/ui/PageHeader";
import { toast } from "react-toastify";
import { useApi } from "../hooks/useApi";
import { getApiUrl } from "../config/api";

const tabs = [
  { id: "general", label: "General", icon: SettingsIcon },
  { id: "trading", label: "Trading", icon: TrendingUp },
  { id: "risk", label: "Risk Management", icon: Shield },
  { id: "api", label: "API Keys", icon: Key },
  { id: "notifications", label: "Notifications", icon: Bell },
  { id: "alerts", label: "Alerts", icon: AlertTriangle },
  { id: "ml", label: "ML / AI", icon: Brain },
  { id: "agents", label: "Agents", icon: Bot },
];

function SectionCard({ title, children }) {
  return (
    <Card title={title} className="mb-6">
      {children}
    </Card>
  );
}

const DEFAULT_SETTINGS = {
  theme: "dark",
  timezone: "EST",
  currency: "USD",
  defaultTimeframe: "1D",
  maxPositions: 15,
  positionSize: 2.0,
  riskPerTrade: 2.0,
  maxDailyLoss: 5.0,
  circuitBreaker: true,
  stopLossDefault: 2.0,
  alpacaKey: "****",
  alpacaSecret: "****",
  finhubKey: "****",
  unusualWhalesKey: "****",
  telegramEnabled: true,
  emailEnabled: true,
  signalAlerts: true,
  tradeAlerts: true,
  minCompositeScore: 60,
  minMLConfidence: 40,
  autoRetrain: true,
  retrainDay: "Sunday",
  marketScanner: true,
  patternAI: true,
  riskAgent: true,
  youtubeAgent: true,
};

export default function Settings() {
  const [activeTab, setActiveTab] = useState("general");
  const [settings, setSettings] = useState(DEFAULT_SETTINGS);
  const [saving, setSaving] = useState(false);
  const [saveMessage, setSaveMessage] = useState(null);
  const { data: apiSettings, loading, refetch } = useApi("settings");
  const { data: alertsData, refetch: refetchAlerts } = useApi("alerts");
  const alertRules = Array.isArray(alertsData?.rules) ? alertsData.rules : [];

  useEffect(() => {
    if (
      apiSettings &&
      typeof apiSettings === "object" &&
      Object.keys(apiSettings).length > 0
    ) {
      setSettings((prev) => ({ ...DEFAULT_SETTINGS, ...prev, ...apiSettings }));
    }
  }, [apiSettings]);

  const update = (key, val) => setSettings((p) => ({ ...p, [key]: val }));

  const handleSave = async () => {
    setSaving(true);
    setSaveMessage(null);
    try {
      const res = await fetch(getApiUrl("settings"), {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(settings),
      });
      if (!res.ok) throw new Error("Save failed");
      await refetch();
      setSaveMessage("Saved");
      toast.success("Settings saved");
      setTimeout(() => setSaveMessage(null), 2000);
    } catch (err) {
      setSaveMessage(err.message || "Failed to save");
      toast.error(err.message || "Failed to save settings");
    } finally {
      setSaving(false);
    }
  };

  const handleReset = () => setSettings(DEFAULT_SETTINGS);

  const setAlertEnabled = async (ruleId, enabled) => {
    try {
      const res = await fetch(`${getApiUrl("alerts")}/${ruleId}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ enabled }),
      });
      if (res.ok) {
        await refetchAlerts();
        toast.success(enabled ? "Alert enabled" : "Alert disabled");
      } else {
        toast.error("Failed to update alert");
      }
    } catch (err) {
      console.error("Failed to update alert", err);
      toast.error("Failed to update alert");
    }
  };

  const renderContent = () => {
    switch (activeTab) {
      case "general":
        return (
          <>
            <SectionCard title="Appearance">
              <div className="py-3">
                <Select
                  label="Theme"
                  value={settings.theme}
                  onChange={(e) => update("theme", e.target.value)}
                  options={[
                    { value: "dark", label: "Dark (Glass House)" },
                    { value: "light", label: "Light" },
                    { value: "midnight", label: "Midnight Blue" },
                  ]}
                />
              </div>
              <div className="py-3">
                <Select
                  label="Timezone"
                  value={settings.timezone}
                  onChange={(e) => update("timezone", e.target.value)}
                  options={[
                    { value: "EST", label: "Eastern (EST)" },
                    { value: "CST", label: "Central (CST)" },
                    { value: "PST", label: "Pacific (PST)" },
                    { value: "UTC", label: "UTC" },
                  ]}
                />
              </div>
              <div className="py-3">
                <Select
                  label="Currency"
                  value={settings.currency}
                  onChange={(e) => update("currency", e.target.value)}
                  options={[
                    { value: "USD", label: "USD ($)" },
                    { value: "EUR", label: "EUR" },
                    { value: "GBP", label: "GBP" },
                  ]}
                />
              </div>
            </SectionCard>
          </>
        );
      case "trading":
        return (
          <>
            <SectionCard title="Position Settings">
              <div className="py-3">
                <TextField
                  label="Max Concurrent Positions"
                  value={settings.maxPositions}
                  onChange={(e) => update("maxPositions", e.target.value)}
                  type="number"
                />
              </div>
              <div className="py-3">
                <TextField
                  label="Default Position Size"
                  value={settings.positionSize}
                  onChange={(e) => update("positionSize", e.target.value)}
                  type="number"
                  suffix="%"
                />
              </div>
              <div className="py-3">
                <Select
                  label="Default Timeframe"
                  value={settings.defaultTimeframe}
                  onChange={(e) => update("defaultTimeframe", e.target.value)}
                  options={[
                    { value: "1m", label: "1 Minute" },
                    { value: "5m", label: "5 Minutes" },
                    { value: "15m", label: "15 Minutes" },
                    { value: "1H", label: "1 Hour" },
                    { value: "1D", label: "1 Day" },
                  ]}
                />
              </div>
            </SectionCard>
          </>
        );
      case "risk":
        return (
          <>
            <SectionCard title="Risk Controls">
              <div className="py-3">
                <TextField
                  label="Risk Per Trade"
                  value={settings.riskPerTrade}
                  onChange={(e) => update("riskPerTrade", e.target.value)}
                  type="number"
                  suffix="%"
                />
              </div>
              <div className="py-3">
                <TextField
                  label="Max Daily Loss"
                  value={settings.maxDailyLoss}
                  onChange={(e) => update("maxDailyLoss", e.target.value)}
                  type="number"
                  suffix="%"
                />
              </div>
              <div className="py-3">
                <TextField
                  label="Default Stop Loss"
                  value={settings.stopLossDefault}
                  onChange={(e) => update("stopLossDefault", e.target.value)}
                  type="number"
                  suffix="%"
                />
              </div>
              <div className="py-3">
                <Toggle
                  label="Circuit Breaker"
                  description="Auto-halt trading when daily loss limit hit"
                  checked={settings.circuitBreaker}
                  onChange={() =>
                    update("circuitBreaker", !settings.circuitBreaker)
                  }
                />
              </div>
            </SectionCard>
          </>
        );
      case "api":
        return (
          <>
            <SectionCard title="Broker API">
              <div className="py-3">
                <TextField
                  label="Alpaca API Key"
                  value={settings.alpacaKey}
                  onChange={(e) => update("alpacaKey", e.target.value)}
                  type="password"
                />
              </div>
              <div className="py-3">
                <TextField
                  label="Alpaca Secret Key"
                  value={settings.alpacaSecret}
                  onChange={(e) => update("alpacaSecret", e.target.value)}
                  type="password"
                />
              </div>
            </SectionCard>
            <SectionCard title="Data Providers">
              <div className="py-3">
                <TextField
                  label="Finnhub API Key"
                  value={settings.finhubKey}
                  onChange={(e) => update("finhubKey", e.target.value)}
                  type="password"
                />
              </div>
              <div className="py-3">
                <TextField
                  label="Unusual Whales Key"
                  value={settings.unusualWhalesKey}
                  onChange={(e) => update("unusualWhalesKey", e.target.value)}
                  type="password"
                />
              </div>
            </SectionCard>
          </>
        );
      case "notifications":
        return (
          <>
            <SectionCard title="Notification Channels">
              <div className="py-3">
                <Toggle
                  label="Telegram Notifications"
                  description="Send alerts to Telegram bot"
                  checked={settings.telegramEnabled}
                  onChange={() =>
                    update("telegramEnabled", !settings.telegramEnabled)
                  }
                />
              </div>
              <div className="py-3">
                <Toggle
                  label="Email Notifications"
                  description="Send daily summaries via email"
                  checked={settings.emailEnabled}
                  onChange={() =>
                    update("emailEnabled", !settings.emailEnabled)
                  }
                />
              </div>
            </SectionCard>
            <SectionCard title="Alert Types">
              <div className="py-3">
                <Toggle
                  label="Signal Alerts"
                  description="New trade signals detected"
                  checked={settings.signalAlerts}
                  onChange={() =>
                    update("signalAlerts", !settings.signalAlerts)
                  }
                />
              </div>
              <div className="py-3">
                <Toggle
                  label="Trade Execution Alerts"
                  description="Order fills and position changes"
                  checked={settings.tradeAlerts}
                  onChange={() => update("tradeAlerts", !settings.tradeAlerts)}
                />
              </div>
            </SectionCard>
          </>
        );
      case "ml":
        return (
          <>
            <SectionCard title="ML Model Settings">
              <div className="py-3">
                <TextField
                  label="Min Composite Score"
                  value={settings.minCompositeScore}
                  onChange={(e) => update("minCompositeScore", e.target.value)}
                  type="number"
                  suffix="/ 100"
                />
              </div>
              <div className="py-3">
                <TextField
                  label="Min ML Confidence"
                  value={settings.minMLConfidence}
                  onChange={(e) => update("minMLConfidence", e.target.value)}
                  type="number"
                  suffix="%"
                />
              </div>
              <div className="py-3">
                <Toggle
                  label="Auto Retrain Models"
                  description="Automatically retrain on new data"
                  checked={settings.autoRetrain}
                  onChange={() => update("autoRetrain", !settings.autoRetrain)}
                />
              </div>
              <div className="py-3">
                <Select
                  label="Retrain Schedule"
                  value={settings.retrainDay}
                  onChange={(e) => update("retrainDay", e.target.value)}
                  options={[
                    { value: "Daily", label: "Daily" },
                    { value: "Sunday", label: "Weekly (Sunday)" },
                    { value: "Monthly", label: "Monthly" },
                  ]}
                />
              </div>
            </SectionCard>
          </>
        );
      case "alerts":
        return (
          <>
            <SectionCard
              title="Alert Rules"
              subtitle="Enable or disable notification rules. Changes apply immediately."
            >
              {alertRules.length === 0 && (
                <p className="text-secondary text-sm py-4">
                  No alert rules configured.
                </p>
              )}
              <div className="space-y-3">
                {alertRules.map((rule) => (
                  <div
                    key={rule.id}
                    className="flex items-center justify-between py-3 border-b border-secondary/30 last:border-0"
                  >
                    <div>
                      <div className="text-sm font-medium text-white">
                        {rule.name}
                      </div>
                      <div className="text-xs text-secondary">
                        {rule.condition}
                      </div>
                    </div>
                    <Toggle
                      checked={!!rule.enabled}
                      onChange={() => setAlertEnabled(rule.id, !rule.enabled)}
                    />
                  </div>
                ))}
              </div>
            </SectionCard>
          </>
        );
      case "agents":
        return (
          <>
            <SectionCard title="Agent Controls">
              <div className="py-3">
                <Toggle
                  label="Market Scanner Agent"
                  description="24/7 scanning for opportunities"
                  checked={settings.marketScanner}
                  onChange={() =>
                    update("marketScanner", !settings.marketScanner)
                  }
                />
              </div>
              <div className="py-3">
                <Toggle
                  label="Pattern AI Agent"
                  description="Real-time pattern recognition"
                  checked={settings.patternAI}
                  onChange={() => update("patternAI", !settings.patternAI)}
                />
              </div>
              <div className="py-3">
                <Toggle
                  label="Risk Manager Agent"
                  description="Portfolio risk monitoring"
                  checked={settings.riskAgent}
                  onChange={() => update("riskAgent", !settings.riskAgent)}
                />
              </div>
              <div className="py-3">
                <Toggle
                  label="YouTube Ingestion Agent"
                  description="Process financial video transcripts"
                  checked={settings.youtubeAgent}
                  onChange={() =>
                    update("youtubeAgent", !settings.youtubeAgent)
                  }
                />
              </div>
            </SectionCard>
          </>
        );
      default:
        return null;
    }
  };

  return (
    <div className="space-y-6">
      <PageHeader
        icon={SettingsIcon}
        title="Settings"
        description={
          loading ? "Loading…" : saveMessage || "Configure your trading system"
        }
      >
        {saveMessage && (
          <span
            className={`text-xs font-medium ${saveMessage === "Saved" ? "text-success" : "text-danger"}`}
          >
            {saveMessage}
          </span>
        )}
        <Button
          variant="outline"
          leftIcon={RotateCcw}
          onClick={handleReset}
          disabled={loading}
        >
          Reset
        </Button>
        <Button
          variant="primary"
          leftIcon={Save}
          onClick={handleSave}
          disabled={saving || loading}
        >
          {saving ? "Saving…" : "Save Changes"}
        </Button>
      </PageHeader>

      <div className="flex gap-8">
        <div className="w-56 flex-shrink-0">
          <nav className="space-y-1">
            {tabs.map((tab) => {
              const Icon = tab.icon;
              return (
                <Button
                  key={tab.id}
                  variant={activeTab === tab.id ? "secondary" : "ghost"}
                  size="md"
                  onClick={() => setActiveTab(tab.id)}
                  className={`w-full !justify-start ${activeTab === tab.id ? "border-primary/30" : ""}`}
                >
                  <Icon className="w-4 h-4 shrink-0" />
                  {tab.label}
                  {activeTab === tab.id && (
                    <ChevronRight className="w-4 h-4 ml-auto" />
                  )}
                </Button>
              );
            })}
          </nav>
        </div>

        <div className="flex-1 min-w-0">{renderContent()}</div>
      </div>
    </div>
  );
}
