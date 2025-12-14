import React, { useState } from 'react';
import { Save, X } from 'lucide-react';

export function SettingsPage({ onClose }) {
  const [activeTab, setActiveTab] = useState('general');
  const [settings, setSettings] = useState({ theme: 'dark', riskTolerance: 50, maxPositions: 15, dailyLossLimit: 3, autoTrade: false, notifications: true });
  const tabs = [{ id: 'general', label: 'General' }, { id: 'trading', label: 'Trading' }, { id: 'api', label: 'API Keys' }, { id: 'notifications', label: 'Alerts' }];

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
      <div className="bg-slate-900 border border-slate-700 rounded-lg w-3/4 max-w-4xl max-h-screen overflow-hidden flex flex-col">
        <div className="p-4 border-b border-slate-700 flex items-center justify-between"><h2 className="text-xl font-bold text-cyan-400">Settings</h2><button onClick={onClose} className="p-1 hover:bg-slate-700 rounded text-slate-400"><X size={20} /></button></div>
        <div className="flex flex-1 overflow-hidden">
          <div className="w-48 border-r border-slate-700 p-4 space-y-2">{tabs.map(tab => (<button key={tab.id} onClick={() => setActiveTab(tab.id)} className={'w-full text-left px-4 py-2 rounded transition ' + (activeTab === tab.id ? 'bg-cyan-600 text-white' : 'hover:bg-slate-700 text-slate-300')}>{tab.label}</button>))}</div>
          <div className="flex-1 p-6 overflow-y-auto space-y-4">
            {activeTab === 'general' && (<div><label className="text-sm text-slate-400 block mb-2">Theme</label><select value={settings.theme} onChange={(e) => setSettings({ ...settings, theme: e.target.value })} className="w-full px-3 py-2 bg-slate-800 border border-slate-600 rounded text-slate-100"><option>dark</option><option>light</option></select></div>)}
            {activeTab === 'trading' && (<div className="space-y-4"><div><label className="text-sm text-slate-400 block mb-2">Risk Tolerance: {settings.riskTolerance}%</label><input type="range" min="0" max="100" value={settings.riskTolerance} onChange={(e) => setSettings({ ...settings, riskTolerance: Number(e.target.value) })} className="w-full" /></div><div><label className="text-sm text-slate-400 block mb-2">Max Positions</label><input type="number" value={settings.maxPositions} onChange={(e) => setSettings({ ...settings, maxPositions: Number(e.target.value) })} className="w-full px-3 py-2 bg-slate-800 border border-slate-600 rounded text-slate-100" /></div></div>)}
            {activeTab === 'api' && (<div className="space-y-4"><div><label className="text-sm text-slate-400 block mb-2">Alpaca API Key</label><input type="password" value="***-HIDDEN-***" className="w-full px-3 py-2 bg-slate-800 border border-slate-600 rounded text-slate-100" /></div></div>)}
            {activeTab === 'notifications' && (<div><label className="flex items-center gap-2"><input type="checkbox" checked={settings.notifications} onChange={(e) => setSettings({ ...settings, notifications: e.target.checked })} /><span className="text-slate-300">Enable Notifications</span></label></div>)}
          </div>
        </div>
        <div className="p-4 border-t border-slate-700 flex gap-2 justify-end"><button onClick={onClose} className="px-4 py-2 hover:bg-slate-700 rounded">Cancel</button><button className="px-4 py-2 bg-cyan-600 hover:bg-cyan-700 rounded text-white font-bold flex items-center gap-2"><Save size={18} />Save</button></div>
      </div>
    </div>
  );
}
