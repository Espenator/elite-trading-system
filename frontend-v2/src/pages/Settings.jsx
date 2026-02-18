// SETTINGS PAGE - Embodier.ai Glass House Intelligence System
// Tabbed settings: General, Trading, Risk, API Keys, Notifications, ML/AI, Agents
import { useState } from 'react';
import {
  Settings as SettingsIcon, Shield, Key, Bell, Brain, Bot,
  TrendingUp, Save, RotateCcw, ChevronRight, ToggleLeft, ToggleRight
} from 'lucide-react';

const TABS = [
  { id: 'general', label: 'General', icon: SettingsIcon },
  { id: 'trading', label: 'Trading', icon: TrendingUp },
  { id: 'risk', label: 'Risk Management', icon: Shield },
  { id: 'api', label: 'API Keys', icon: Key },
  { id: 'notifications', label: 'Notifications', icon: Bell },
  { id: 'ml', label: 'ML / AI', icon: Brain },
  { id: 'agents', label: 'Agents', icon: Bot },
];

function Toggle({ enabled, onChange, label, description }) {
  return (
    <div className="flex items-center justify-between py-3">
      <div>
        <div className="text-sm font-medium text-white">{label}</div>
        {description && <div className="text-xs text-secondary mt-0.5">{description}</div>}
      </div>
      <button onClick={onChange} className="text-secondary hover:text-white transition-colors">
        {enabled ? <ToggleRight className="w-8 h-8 text-emerald-400" /> : <ToggleLeft className="w-8 h-8" />}
      </button>
    </div>
  );
}

function InputField({ label, value, onChange, type = 'text', placeholder, suffix }) {
  return (
    <div className="py-3">
      <label className="text-sm font-medium text-white block mb-2">{label}</label>
      <div className="relative">
        <input
          type={type}
          value={value}
          onChange={e => onChange(e.target.value)}
          placeholder={placeholder}
          className="w-full px-4 py-2.5 bg-slate-800/60 border border-white/10 rounded-xl text-sm text-white placeholder-gray-500 outline-none focus:border-blue-500/50 transition-colors"
        />
        {suffix && <span className="absolute right-4 top-1/2 -translate-y-1/2 text-xs text-secondary">{suffix}</span>}
      </div>
    </div>
  );
}

function SelectField({ label, value, onChange, options }) {
  return (
    <div className="py-3">
      <label className="text-sm font-medium text-white block mb-2">{label}</label>
      <select
        value={value}
        onChange={e => onChange(e.target.value)}
        className="w-full px-4 py-2.5 bg-slate-800/60 border border-white/10 rounded-xl text-sm text-white outline-none focus:border-blue-500/50 transition-colors"
      >
        {options.map(opt => <option key={opt.value} value={opt.value}>{opt.label}</option>)}
      </select>
    </div>
  );
}

function SectionCard({ title, children }) {
  return (
    <div className="bg-slate-800/30 border border-white/10 rounded-2xl p-6 mb-6">
      <h3 className="text-lg font-semibold text-white mb-4">{title}</h3>
      <div className="divide-y divide-white/5">{children}</div>
    </div>
  );
}

export default function Settings() {
  const [activeTab, setActiveTab] = useState('general');
  const [settings, setSettings] = useState({
    theme: 'dark', timezone: 'EST', currency: 'USD',
    defaultTimeframe: '1D', maxPositions: 15, positionSize: 2.0,
    riskPerTrade: 2.0, maxDailyLoss: 5.0, circuitBreaker: true, stopLossDefault: 2.0,
    alpacaKey: '****', alpacaSecret: '****', finhubKey: '****', unusualWhalesKey: '****',
    telegramEnabled: true, emailEnabled: true, signalAlerts: true, tradeAlerts: true,
    minCompositeScore: 60, minMLConfidence: 40, autoRetrain: true, retrainDay: 'Sunday',
    marketScanner: true, patternAI: true, riskAgent: true, youtubeAgent: true,
  });

  const update = (key, val) => setSettings(p => ({ ...p, [key]: val }));

  const renderContent = () => {
    switch (activeTab) {
      case 'general': return (
        <>
          <SectionCard title="Appearance">
            <SelectField label="Theme" value={settings.theme} onChange={v => update('theme', v)}
              options={[{value:'dark',label:'Dark (Glass House)'},{value:'light',label:'Light'},{value:'midnight',label:'Midnight Blue'}]} />
            <SelectField label="Timezone" value={settings.timezone} onChange={v => update('timezone', v)}
              options={[{value:'EST',label:'Eastern (EST)'},{value:'CST',label:'Central (CST)'},{value:'PST',label:'Pacific (PST)'},{value:'UTC',label:'UTC'}]} />
            <SelectField label="Currency" value={settings.currency} onChange={v => update('currency', v)}
              options={[{value:'USD',label:'USD ($)'},{value:'EUR',label:'EUR'},{value:'GBP',label:'GBP'}]} />
          </SectionCard>
        </>
      );
      case 'trading': return (
        <>
          <SectionCard title="Position Settings">
            <InputField label="Max Concurrent Positions" value={settings.maxPositions} onChange={v => update('maxPositions', v)} type="number" />
            <InputField label="Default Position Size" value={settings.positionSize} onChange={v => update('positionSize', v)} type="number" suffix="%" />
            <SelectField label="Default Timeframe" value={settings.defaultTimeframe} onChange={v => update('defaultTimeframe', v)}
              options={[{value:'1m',label:'1 Minute'},{value:'5m',label:'5 Minutes'},{value:'15m',label:'15 Minutes'},{value:'1H',label:'1 Hour'},{value:'1D',label:'1 Day'}]} />
          </SectionCard>
        </>
      );
      case 'risk': return (
        <>
          <SectionCard title="Risk Controls">
            <InputField label="Risk Per Trade" value={settings.riskPerTrade} onChange={v => update('riskPerTrade', v)} type="number" suffix="%" />
            <InputField label="Max Daily Loss" value={settings.maxDailyLoss} onChange={v => update('maxDailyLoss', v)} type="number" suffix="%" />
            <InputField label="Default Stop Loss" value={settings.stopLossDefault} onChange={v => update('stopLossDefault', v)} type="number" suffix="%" />
            <Toggle label="Circuit Breaker" description="Auto-halt trading when daily loss limit hit" enabled={settings.circuitBreaker} onChange={() => update('circuitBreaker', !settings.circuitBreaker)} />
          </SectionCard>
        </>
      );
      case 'api': return (
        <>
          <SectionCard title="Broker API">
            <InputField label="Alpaca API Key" value={settings.alpacaKey} onChange={v => update('alpacaKey', v)} type="password" />
            <InputField label="Alpaca Secret Key" value={settings.alpacaSecret} onChange={v => update('alpacaSecret', v)} type="password" />
          </SectionCard>
          <SectionCard title="Data Providers">
            <InputField label="Finnhub API Key" value={settings.finhubKey} onChange={v => update('finhubKey', v)} type="password" />
            <InputField label="Unusual Whales Key" value={settings.unusualWhalesKey} onChange={v => update('unusualWhalesKey', v)} type="password" />
          </SectionCard>
        </>
      );
      case 'notifications': return (
        <>
          <SectionCard title="Notification Channels">
            <Toggle label="Telegram Notifications" description="Send alerts to Telegram bot" enabled={settings.telegramEnabled} onChange={() => update('telegramEnabled', !settings.telegramEnabled)} />
            <Toggle label="Email Notifications" description="Send daily summaries via email" enabled={settings.emailEnabled} onChange={() => update('emailEnabled', !settings.emailEnabled)} />
          </SectionCard>
          <SectionCard title="Alert Types">
            <Toggle label="Signal Alerts" description="New trade signals detected" enabled={settings.signalAlerts} onChange={() => update('signalAlerts', !settings.signalAlerts)} />
            <Toggle label="Trade Execution Alerts" description="Order fills and position changes" enabled={settings.tradeAlerts} onChange={() => update('tradeAlerts', !settings.tradeAlerts)} />
          </SectionCard>
        </>
      );
      case 'ml': return (
        <>
          <SectionCard title="ML Model Settings">
            <InputField label="Min Composite Score" value={settings.minCompositeScore} onChange={v => update('minCompositeScore', v)} type="number" suffix="/ 100" />
            <InputField label="Min ML Confidence" value={settings.minMLConfidence} onChange={v => update('minMLConfidence', v)} type="number" suffix="%" />
            <Toggle label="Auto Retrain Models" description="Automatically retrain on new data" enabled={settings.autoRetrain} onChange={() => update('autoRetrain', !settings.autoRetrain)} />
            <SelectField label="Retrain Schedule" value={settings.retrainDay} onChange={v => update('retrainDay', v)}
              options={[{value:'Daily',label:'Daily'},{value:'Sunday',label:'Weekly (Sunday)'},{value:'Monthly',label:'Monthly'}]} />
          </SectionCard>
        </>
      );
      case 'agents': return (
        <>
          <SectionCard title="Agent Controls">
            <Toggle label="Market Scanner Agent" description="24/7 scanning for opportunities" enabled={settings.marketScanner} onChange={() => update('marketScanner', !settings.marketScanner)} />
            <Toggle label="Pattern AI Agent" description="Real-time pattern recognition" enabled={settings.patternAI} onChange={() => update('patternAI', !settings.patternAI)} />
            <Toggle label="Risk Manager Agent" description="Portfolio risk monitoring" enabled={settings.riskAgent} onChange={() => update('riskAgent', !settings.riskAgent)} />
            <Toggle label="YouTube Ingestion Agent" description="Process financial video transcripts" enabled={settings.youtubeAgent} onChange={() => update('youtubeAgent', !settings.youtubeAgent)} />
          </SectionCard>
        </>
      );
      default: return null;
    }
  };

  return (
    <div className="space-y-6">
      {/* Page header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">Settings</h1>
          <p className="text-sm text-secondary mt-1">Configure your trading system</p>
        </div>
        <div className="flex gap-3">
          <button className="flex items-center gap-2 px-4 py-2.5 rounded-xl bg-slate-800/60 border border-white/10 text-sm text-secondary hover:text-white hover:border-white/20 transition-all">
            <RotateCcw className="w-4 h-4" /> Reset
          </button>
          <button className="flex items-center gap-2 px-6 py-2.5 rounded-xl bg-blue-600 hover:bg-blue-500 text-sm font-medium text-white transition-colors">
            <Save className="w-4 h-4" /> Save Changes
          </button>
        </div>
      </div>

      {/* Tab navigation + Content */}
      <div className="flex gap-8">
        {/* Sidebar tabs */}
        <div className="w-56 flex-shrink-0">
          <nav className="space-y-1">
            {TABS.map(tab => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`w-full flex items-center gap-3 px-4 py-3 rounded-xl text-sm font-medium transition-all ${
                  activeTab === tab.id
                    ? 'bg-blue-600/20 text-blue-400 border border-blue-500/30'
                    : 'text-secondary hover:text-white hover:bg-white/5'
                }`}
              >
                <tab.icon className="w-4 h-4" />
                {tab.label}
                {activeTab === tab.id && <ChevronRight className="w-4 h-4 ml-auto" />}
              </button>
            ))}
          </nav>
        </div>

        {/* Content area */}
        <div className="flex-1 min-w-0">
          {renderContent()}
        </div>
      </div>
    </div>
  );
}
