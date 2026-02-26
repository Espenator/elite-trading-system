import React, { useState, useEffect } from 'react';
import Card from '../components/ui/Card';
import Button from '../components/ui/Button';
import { useApi } from '../hooks/useApi';
import { getApiUrl } from '../config/api';
import { toast } from 'react-toastify';
import { 
  User, Key, Activity, Bell, Layout, Cpu, Database, 
  ShieldAlert, History, Eye, EyeOff, Save, RefreshCw, 
  CheckCircle2, AlertTriangle, Settings, Zap, Terminal, Sliders
} from 'lucide-react';

// Reusable custom toggle switch for the dense UI
const Toggle = ({ enabled, onChange }) => (
  <button
    type="button"
    onClick={() => onChange(!enabled)}
    className={`relative inline-flex h-4 w-8 shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors duration-200 ease-in-out focus:outline-none ${
      enabled ? 'bg-[#06b6d4]' : 'bg-gray-700'
    }`}
  >
    <span
      className={`pointer-events-none inline-block h-3 w-3 transform rounded-full bg-white shadow ring-0 transition duration-200 ease-in-out ${
        enabled ? 'translate-x-4' : 'translate-x-0'
      }`}
    />
  </button>
);

// Reusable dense input group
const InputGroup = ({ label, type = "text", defaultValue, addon, icon: Icon }) => (
  <div className="flex flex-col space-y-1.5">
    <label className="text-[10px] font-semibold text-gray-400 uppercase tracking-wider flex items-center gap-1">
      {Icon && <Icon className="w-3 h-3" />}
      {label}
    </label>
    <div className="relative flex items-center">
      <input
        type={type}
        defaultValue={defaultValue}
        className="w-full bg-[#0a0a0f] border border-gray-800 rounded-md px-3 py-1.5 text-xs text-gray-200 font-mono focus:outline-none focus:border-[#06b6d4]/50 focus:ring-1 focus:ring-[#06b6d4]/50 transition-all"
      />
      {addon && (
        <span className="absolute right-3 text-xs text-gray-500 font-mono font-bold">
          {addon}
        </span>
      )}
    </div>
  </div>
);

export default function SettingsPage() {
  const [activeTab, setActiveTab] = useState('api-keys');
  const [showKeys, setShowKeys] = useState({});
  const { request, loading } = useApi();

  const toggleKeyVisibility = (provider) => {
    setShowKeys(prev => ({ ...prev, [provider]: !prev[provider] }));
  };

  const handleSave = () => {
    toast.success('Configuration saved successfully', {
      position: "bottom-right",
      theme: "dark"
    });
  };

  const navItems = [
    { id: 'profile', label: 'User Profile', icon: User },
    { id: 'api-keys', label: 'API Keys', icon: Key },
    { id: 'trading-params', label: 'Trading Params', icon: Activity },
    { id: 'risk-limits', label: 'Risk Limits', icon: ShieldAlert },
    { id: 'ai-ml', label: 'AI/ML Config', icon: Cpu },
    { id: 'data-sources', label: 'Data Sources', icon: Database },
    { id: 'notifications', label: 'Notifications', icon: Bell },
    { id: 'appearance', label: 'Appearance', icon: Layout },
    { id: 'audit-log', label: 'Audit Log', icon: History },
  ];

  // Tab Content Renderers
  const renderProfile = () => (
    <div className="space-y-6 animate-in fade-in duration-300">
      <div>
        <h3 className="text-sm font-bold text-white mb-1 uppercase tracking-wide flex items-center gap-2">
          <User className="w-4 h-4 text-[#06b6d4]" /> Identity & Localization
        </h3>
        <p className="text-xs text-gray-500 mb-4">Manage your trader identity and locale preferences.</p>
      </div>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4 max-w-2xl">
        <InputGroup label="Display Name" defaultValue="Espen Schiefloe" />
        <InputGroup label="Email Address" type="email" defaultValue="espen@embodier.ai" />
        <div className="flex flex-col space-y-1.5">
          <label className="text-[10px] font-semibold text-gray-400 uppercase tracking-wider">Timezone</label>
          <select className="w-full bg-[#0a0a0f] border border-gray-800 rounded-md px-3 py-1.5 text-xs text-gray-200 focus:outline-none focus:border-[#06b6d4]/50 focus:ring-1 focus:ring-[#06b6d4]/50">
            <option>America/New_York (EST)</option>
            <option>Europe/Oslo (CET)</option>
            <option>UTC</option>
          </select>
        </div>
        <InputGroup label="Base Currency" defaultValue="USD" />
      </div>
    </div>
  );

  const renderApiKeys = () => {
    const providers = [
      { id: 'alpaca', name: 'Alpaca Trading API', status: 'Connected', badge: 'bg-[#10b981]/10 text-[#10b981] border-[#10b981]/20', key: 'PK8V2****************', secret: '********************************' },
      { id: 'unusual_whales', name: 'Unusual Whales', status: 'Connected', badge: 'bg-[#10b981]/10 text-[#10b981] border-[#10b981]/20', key: 'UW_882****************', secret: '********************************' },
      { id: 'polygon', name: 'Polygon.io', status: 'Degraded', badge: 'bg-[#f59e0b]/10 text-[#f59e0b] border-[#f59e0b]/20', key: 'POLY_****************', secret: '********************************' },
      { id: 'openai', name: 'OpenAI (GPT-4)', status: 'Connected', badge: 'bg-[#10b981]/10 text-[#10b981] border-[#10b981]/20', key: 'sk-proj-**************', secret: '********************************' },
    ];

    return (
      <div className="space-y-6 animate-in fade-in duration-300">
        <div className="flex justify-between items-end">
          <div>
            <h3 className="text-sm font-bold text-white mb-1 uppercase tracking-wide flex items-center gap-2">
              <Key className="w-4 h-4 text-[#06b6d4]" /> API Integrations
            </h3>
            <p className="text-xs text-gray-500">Manage connections to external brokers and data feeds.</p>
          </div>
        </div>
        
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          {providers.map((p) => (
            <Card key={p.id} className="bg-[#0B0E14] border-gray-800/60 p-4 relative overflow-hidden group">
              <div className="absolute top-0 left-0 w-1 h-full bg-gradient-to-b from-[#06b6d4]/50 to-transparent opacity-50"></div>
              <div className="flex justify-between items-center mb-4">
                <span className="text-sm font-bold text-gray-200">{p.name}</span>
                <span className={`text-[9px] px-2 py-0.5 rounded uppercase font-mono border ${p.badge} flex items-center gap-1`}>
                  {p.status === 'Connected' ? <CheckCircle2 className="w-3 h-3" /> : <AlertTriangle className="w-3 h-3" />}
                  {p.status}
                </span>
              </div>
              <div className="space-y-3">
                <div className="relative">
                  <label className="text-[9px] text-gray-500 uppercase tracking-wider mb-1 block">API Key</label>
                  <input 
                    type={showKeys[p.id] ? "text" : "password"} 
                    defaultValue={p.key}
                    className="w-full bg-[#0a0a0f] border border-gray-800/80 rounded px-2 py-1.5 text-xs font-mono text-gray-300" 
                    readOnly
                  />
                </div>
                <div className="relative">
                  <label className="text-[9px] text-gray-500 uppercase tracking-wider mb-1 block">API Secret</label>
                  <div className="flex gap-2">
                    <input 
                      type={showKeys[p.id] ? "text" : "password"} 
                      defaultValue={p.secret}
                      className="w-full bg-[#0a0a0f] border border-gray-800/80 rounded px-2 py-1.5 text-xs font-mono text-gray-300"
                      readOnly
                    />
                    <button onClick={() => toggleKeyVisibility(p.id)} className="px-2 bg-gray-800/50 hover:bg-gray-700 rounded border border-gray-700 text-gray-400">
                      {showKeys[p.id] ? <EyeOff className="w-3 h-3" /> : <Eye className="w-3 h-3" />}
                    </button>
                  </div>
                </div>
                <div className="pt-2 flex gap-2">
                  <Button className="bg-[#06b6d4]/10 hover:bg-[#06b6d4]/20 text-[#06b6d4] text-[10px] py-1 px-3 border border-[#06b6d4]/20 h-auto rounded">
                    Test Connection
                  </Button>
                  <Button className="bg-gray-800/50 hover:bg-gray-700 text-gray-300 text-[10px] py-1 px-3 border border-gray-700 h-auto rounded">
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
        <p className="text-xs text-gray-500">Configure default sizing, targets, and operational limits.</p>
      </div>
      
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <Card className="bg-[#0B0E14] border-gray-800 p-4 space-y-4 md:col-span-1">
          <h4 className="text-xs font-bold text-[#06b6d4] uppercase tracking-wider mb-2 flex items-center gap-1"><Terminal className="w-3 h-3" /> Position Sizing</h4>
          <InputGroup label="Base Position Size" defaultValue="25,000" addon="USD" />
          <InputGroup label="Max Position Size" defaultValue="100,000" addon="USD" />
          <InputGroup label="Max Concurrent Positions" defaultValue="5" addon="POS" type="number" />
        </Card>
        
        <Card className="bg-[#0B0E14] border-gray-800 p-4 space-y-4 md:col-span-1">
          <h4 className="text-xs font-bold text-[#f59e0b] uppercase tracking-wider mb-2 flex items-center gap-1"><Sliders className="w-3 h-3" /> Trade Management</h4>
          <InputGroup label="Default Stop Loss" defaultValue="1.0" addon="ATR" />
          <InputGroup label="Primary Target (TP1)" defaultValue="1.5" addon="R" />
          <InputGroup label="Secondary Target (TP2)" defaultValue="3.0" addon="R" />
        </Card>

        <Card className="bg-[#0B0E14] border-gray-800 p-4 space-y-4 md:col-span-1">
          <h4 className="text-xs font-bold text-[#10b981] uppercase tracking-wider mb-2 flex items-center gap-1"><Activity className="w-3 h-3" /> Risk Profile</h4>
          <InputGroup label="Max Daily Risk" defaultValue="2.0" addon="%" />
          <InputGroup label="Max Risk Per Trade" defaultValue="0.5" addon="%" />
          <div className="pt-2 flex items-center justify-between">
            <span className="text-[10px] font-semibold text-gray-400 uppercase">Auto-Scale Sizing</span>
            <Toggle enabled={true} onChange={() => {}} />
          </div>
        </Card>
      </div>
    </div>
  );

  const renderRiskLimits = () => (
    <div className="space-y-6 animate-in fade-in duration-300">
      <div>
        <h3 className="text-sm font-bold text-white mb-1 uppercase tracking-wide flex items-center gap-2">
          <ShieldAlert className="w-4 h-4 text-red-500" /> Circuit Breakers & Risk Limits
        </h3>
        <p className="text-xs text-gray-500">Hard halts and emergency killswitches for the automated systems.</p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <Card className="bg-red-950/10 border-red-900/30 p-4 space-y-4">
          <h4 className="text-xs font-bold text-red-400 uppercase tracking-wider">Market Conditions Halts</h4>
          <div className="flex items-center justify-between p-2 bg-[#0a0a0f] rounded border border-gray-800/80">
            <div>
              <p className="text-xs text-gray-200 font-bold">VIX Spike Halt</p>
              <p className="text-[9px] text-gray-500 uppercase">Halt trading if VIX jumps {'>'} 15% intraday</p>
            </div>
            <Toggle enabled={true} onChange={() => {}} />
          </div>
          <div className="flex items-center justify-between p-2 bg-[#0a0a0f] rounded border border-gray-800/80">
            <div>
              <p className="text-xs text-gray-200 font-bold">Flash Crash Protection</p>
              <p className="text-[9px] text-gray-500 uppercase">Pause if SPY drops {'>'} 2% in 15 mins</p>
            </div>
            <Toggle enabled={true} onChange={() => {}} />
          </div>
        </Card>

        <Card className="bg-amber-950/10 border-amber-900/30 p-4 space-y-4">
          <h4 className="text-xs font-bold text-amber-400 uppercase tracking-wider">Account Drawdown Halts</h4>
          <div className="flex items-center justify-between p-2 bg-[#0a0a0f] rounded border border-gray-800/80">
            <div>
              <p className="text-xs text-gray-200 font-bold">Daily Loss Limit Halt</p>
              <p className="text-[9px] text-gray-500 uppercase">Killswitch at -$2,500 daily PnL</p>
            </div>
            <Toggle enabled={true} onChange={() => {}} />
          </div>
          <InputGroup label="Max Correlation Limit" defaultValue="0.75" addon="PEARSON" />
        </Card>
      </div>
    </div>
  );

  const renderNotifications = () => {
    const notifs = [
      { id: 1, title: 'Trade Executions', desc: 'Alerts for filled orders, partials, and rejections', status: true },
      { id: 2, title: 'Pattern Scanner Alerts', desc: 'When new high-confidence patterns emerge', status: true },
      { id: 3, title: 'Risk Threshold Warnings', desc: 'When daily drawdown approaches limits', status: true },
      { id: 4, title: 'API Disconnects', desc: 'Critical alerts for feed loss or broker disconnects', status: true },
      { id: 5, title: 'Options Flow Anomalies', desc: 'Large blocks or weird put/call ratios detected', status: false },
      { id: 6, title: 'End of Day Summary', desc: 'Daily PnL and system performance report', status: true },
    ];

    return (
      <div className="space-y-6 animate-in fade-in duration-300">
        <div>
          <h3 className="text-sm font-bold text-white mb-1 uppercase tracking-wide flex items-center gap-2">
            <Bell className="w-4 h-4 text-[#06b6d4]" /> Notification Routing
          </h3>
          <p className="text-xs text-gray-500">Configure which events trigger alerts to your devices.</p>
        </div>
        <div className="grid grid-cols-1 gap-2 max-w-3xl">
          {notifs.map(n => (
            <div key={n.id} className="flex items-center justify-between p-3 bg-[#0B0E14] border border-gray-800/60 rounded-lg hover:border-gray-700 transition-colors">
              <div>
                <p className="text-xs font-bold text-gray-200">{n.title}</p>
                <p className="text-[10px] text-gray-500 font-mono mt-0.5">{n.desc}</p>
              </div>
              <div className="flex items-center gap-4">
                <span className="text-[9px] uppercase tracking-wider text-gray-600 font-bold">Discord / SMS</span>
                <Toggle enabled={n.status} onChange={() => {}} />
              </div>
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
        <p className="text-xs text-gray-500">Customize the trading terminal aesthetic.</p>
      </div>
      
      <div className="space-y-4 max-w-2xl">
        <label className="text-[10px] font-semibold text-gray-400 uppercase tracking-wider">Terminal Theme</label>
        <div className="grid grid-cols-3 gap-4">
          <div className="bg-[#0a0a0f] border-2 border-[#06b6d4] rounded-lg p-4 cursor-pointer relative overflow-hidden">
            <div className="absolute top-1 right-2"><CheckCircle2 className="w-4 h-4 text-[#06b6d4]" /></div>
            <p className="text-xs font-bold text-white mb-2">Midnight Bloomberg</p>
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
          <label className="text-[10px] font-semibold text-gray-400 uppercase tracking-wider mb-2 block">Data Density</label>
          <select className="w-full md:w-1/2 bg-[#0a0a0f] border border-gray-800 rounded-md px-3 py-1.5 text-xs text-gray-200">
            <option>Ultra Dense (Bloomberg Style)</option>
            <option>Comfortable (Web Style)</option>
            <option>Compact</option>
          </select>
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
        <p className="text-xs text-gray-500">Tune the machine learning components and logic thresholds.</p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6 max-w-4xl">
        <div className="space-y-4">
          <div className="flex flex-col space-y-1.5">
            <label className="text-[10px] font-semibold text-gray-400 uppercase tracking-wider">Primary Inference Model</label>
            <select className="w-full bg-[#0a0a0f] border border-gray-800 rounded-md px-3 py-1.5 text-xs text-gray-200">
              <option>GPT-4o (Default)</option>
              <option>Claude 3.5 Sonnet</option>
              <option>Local LLaMA-3-70B</option>
            </select>
          </div>
          <InputGroup label="Min. Pattern Confidence Score" defaultValue="75" addon="%" type="number" />
          <InputGroup label="Sentiment Analysis Lookback" defaultValue="24" addon="HOURS" type="number" />
        </div>

        <Card className="bg-[#0B0E14] border-gray-800 p-4 space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-xs font-bold text-[#06b6d4]">Flywheel Learning Loop</p>
              <p className="text-[9px] text-gray-500 uppercase mt-0.5">Feed trade outcomes back to the model</p>
            </div>
            <Toggle enabled={true} onChange={() => {}} />
          </div>
          <div className="w-full h-[1px] bg-gray-800/60 my-2"></div>
          <div className="flex items-center justify-between">
            <div>
              <p className="text-xs font-bold text-gray-200">Automated Regime Detection</p>
              <p className="text-[9px] text-gray-500 uppercase mt-0.5">Adapt strategies based on macro regime</p>
            </div>
            <Toggle enabled={true} onChange={() => {}} />
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
          <p className="text-xs text-gray-500">Immutable log of system changes and critical events.</p>
        </div>
        <Button className="bg-[#0B0E14] text-xs text-gray-300 border border-gray-800 hover:bg-gray-800 px-3 py-1 h-auto rounded flex gap-2 items-center">
          <RefreshCw className="w-3 h-3" /> Refresh
        </Button>
      </div>
      
      <div className="bg-[#0B0E14] border border-gray-800/80 rounded-lg overflow-hidden">
        <table className="w-full text-left border-collapse">
          <thead>
            <tr className="bg-[#131722] border-b border-gray-800">
              <th className="p-2 text-[10px] uppercase font-mono text-gray-500 tracking-wider w-32">Timestamp</th>
              <th className="p-2 text-[10px] uppercase font-mono text-gray-500 tracking-wider w-24">Category</th>
              <th className="p-2 text-[10px] uppercase font-mono text-gray-500 tracking-wider w-32">User/System</th>
              <th className="p-2 text-[10px] uppercase font-mono text-gray-500 tracking-wider">Event Details</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-800/50 text-[11px] font-mono text-gray-300">
            <tr className="hover:bg-[#1A1D24]/50">
              <td className="p-2 text-gray-500">2026-02-25 10:42:11</td>
              <td className="p-2"><span className="text-amber-500">CONFIG</span></td>
              <td className="p-2">Espen Schiefloe</td>
              <td className="p-2">Updated Trading Parameter: Max Daily Risk to 2.0%</td>
            </tr>
            <tr className="hover:bg-[#1A1D24]/50">
              <td className="p-2 text-gray-500">2026-02-25 09:15:00</td>
              <td className="p-2"><span className="text-[#06b6d4]">SYSTEM</span></td>
              <td className="p-2">OpenClaw Bridge</td>
              <td className="p-2">WebSocket Reconnection Successful (Latency: 42ms)</td>
            </tr>
            <tr className="hover:bg-[#1A1D24]/50">
              <td className="p-2 text-gray-500">2026-02-24 18:30:22</td>
              <td className="p-2"><span className="text-emerald-500">SECURITY</span></td>
              <td className="p-2">Espen Schiefloe</td>
              <td className="p-2">Successful Login from 104.28.112.4 (Asheville, NC)</td>
            </tr>
            <tr className="hover:bg-[#1A1D24]/50">
              <td className="p-2 text-gray-500">2026-02-24 15:05:10</td>
              <td className="p-2"><span className="text-red-500">RISK</span></td>
              <td className="p-2">Auto-Killswitch</td>
              <td className="p-2">VIX Spike Detected ({'>'}15%). New positions temporarily halted.</td>
            </tr>
            <tr className="hover:bg-[#1A1D24]/50">
              <td className="p-2 text-gray-500">2026-02-23 11:20:05</td>
              <td className="p-2"><span className="text-amber-500">CONFIG</span></td>
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
        <p className="text-xs text-gray-500">Manage priority and failovers for market data streams.</p>
      </div>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4 max-w-2xl">
         <Card className="bg-[#0B0E14] border-gray-800 p-4 space-y-3">
            <h4 className="text-xs font-bold text-gray-200 uppercase tracking-wider">Primary Pricing Feed</h4>
            <select className="w-full bg-[#0a0a0f] border border-gray-800 rounded-md px-3 py-1.5 text-xs text-gray-200">
              <option>Polygon.io (Real-time SIP)</option>
              <option>Alpaca Data V2</option>
              <option>Interactive Brokers</option>
            </select>
         </Card>
         <Card className="bg-[#0B0E14] border-gray-800 p-4 space-y-3">
            <h4 className="text-xs font-bold text-gray-200 uppercase tracking-wider">Options Flow Source</h4>
            <select className="w-full bg-[#0a0a0f] border border-gray-800 rounded-md px-3 py-1.5 text-xs text-gray-200">
              <option>Unusual Whales API</option>
              <option>CBOE LiveVol</option>
            </select>
         </Card>
      </div>
    </div>
  );

  return (
    <div className="w-full min-h-screen bg-[#0a0a0f] font-sans text-gray-200 flex flex-col items-center">
      {/* Container simulating max widescreen width similar to a Bloomberg terminal workspace */}
      <div className="max-w-[1920px] w-full p-4 md:p-6 lg:p-8 flex flex-col gap-6">
        
        {/* Page Header Component Match */}
        <div className="flex justify-between items-end border-b border-gray-800/50 pb-4">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-[#06b6d4]/10 rounded-lg border border-[#06b6d4]/20">
              <Settings className="w-6 h-6 text-[#06b6d4]" />
            </div>
            <div>
              <h1 className="text-2xl font-bold text-white tracking-tight">System Settings</h1>
              <p className="text-sm text-gray-500">Configure global parameters, APIs, and risk rules.</p>
            </div>
          </div>
          <Button 
            onClick={handleSave}
            className="bg-[#06b6d4] hover:bg-[#0891b2] text-black font-bold text-xs py-1.5 px-4 rounded shadow-[0_0_10px_rgba(6,182,212,0.3)] transition-all flex gap-2 items-center h-auto"
          >
            <Save className="w-3.5 h-3.5" /> Save Changes
          </Button>
        </div>

        {/* Main Settings Layout Grid */}
        <div className="flex flex-col lg:flex-row gap-6">
          
          {/* Left Sidebar Navigation */}
          <div className="w-full lg:w-64 shrink-0 space-y-1">
            {navItems.map((item) => {
              const Icon = item.icon;
              const isActive = activeTab === item.id;
              return (
                <button
                  key={item.id}
                  onClick={() => setActiveTab(item.id)}
                  className={`w-full flex items-center gap-3 px-4 py-2.5 rounded-lg text-xs font-semibold uppercase tracking-wider transition-all duration-200 ${
                    isActive 
                      ? 'bg-[#06b6d4]/10 text-[#06b6d4] border-r-2 border-[#06b6d4]' 
                      : 'text-gray-500 hover:text-gray-300 hover:bg-gray-800/40 border-r-2 border-transparent'
                  }`}
                >
                  <Icon className={`w-4 h-4 ${isActive ? 'text-[#06b6d4]' : 'text-gray-500'}`} />
                  {item.label}
                </button>
              );
            })}
          </div>

          {/* Right Content Area */}
          <div className="flex-1 bg-[#050608]/40 border border-gray-800/60 rounded-xl p-6 relative shadow-2xl overflow-hidden backdrop-blur-sm">
            {/* Subtle glow effect behind content */}
            <div className="absolute top-0 right-0 w-96 h-96 bg-[#06b6d4]/5 blur-[120px] rounded-full pointer-events-none"></div>
            
            <div className="relative z-10">
              {activeTab === 'profile' && renderProfile()}
              {activeTab === 'api-keys' && renderApiKeys()}
              {activeTab === 'trading-params' && renderTradingParams()}
              {activeTab === 'risk-limits' && renderRiskLimits()}
              {activeTab === 'ai-ml' && renderAiMlConfig()}
              {activeTab === 'notifications' && renderNotifications()}
              {activeTab === 'appearance' && renderAppearance()}
              {activeTab === 'audit-log' && renderAuditLog()}
              {activeTab === 'data-sources' && renderDataSources()}
            </div>
          </div>
          
        </div>
      </div>
    </div>
  );
}
