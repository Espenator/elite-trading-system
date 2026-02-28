import { useState, useEffect, useCallback } from 'react';
import dataSources from '../services/dataSourcesApi';

// ============================================================
// DataSourcesMonitor.jsx - Data Sources Manager
// Matches mockup 09: split view with inline metrics bar,
// AI-powered add source input, source list table,
// persistent right credential editor panel,
// supplementary sources, and footer telemetry.
// Real API integration via dataSourcesApi.js
// NO yfinance - Primary: Alpaca, Unusual Whales, Finviz
// ============================================================

const STATUS_COLORS = {
  healthy: { bg: 'bg-emerald-500/20', text: 'text-emerald-400', dot: 'bg-emerald-400' },
  active: { bg: 'bg-emerald-500/20', text: 'text-emerald-400', dot: 'bg-emerald-400' },
  error: { bg: 'bg-red-500/20', text: 'text-red-400', dot: 'bg-red-400' },
  timeout: { bg: 'bg-orange-500/20', text: 'text-orange-400', dot: 'bg-orange-400' },
  degraded: { bg: 'bg-yellow-500/20', text: 'text-yellow-400', dot: 'bg-yellow-400' },
  no_credentials: { bg: 'bg-gray-500/20', text: 'text-gray-400', dot: 'bg-gray-400' },
  unconfigured: { bg: 'bg-gray-500/20', text: 'text-gray-400', dot: 'bg-gray-400' },
  offline: { bg: 'bg-red-500/20', text: 'text-red-400', dot: 'bg-red-500' },
  beta: { bg: 'bg-purple-500/20', text: 'text-purple-400', dot: 'bg-purple-400' },
  pending: { bg: 'bg-slate-500/20', text: 'text-slate-400', dot: 'bg-slate-400' },
};

const CATEGORY_LABELS = {
  market: 'Market Data', options_flow: 'Options Flow', economic: 'Economic',
  filings: 'Filings', sentiment: 'Sentiment', news: 'News',
  social: 'Social', alerts: 'Alerts', bridge: 'Bridge',
  storage: 'Storage', custom: 'Custom', screener: 'Screener',
  macro: 'Macro', knowledge: 'Knowledge',
};

const CATEGORY_ICONS = {
  market: '\u{1F4C8}', options_flow: '\u{1F40B}', economic: '\u{1F3DB}\uFE0F',
  filings: '\u{1F4CB}', sentiment: '\u{1F9E0}', news: '\u{1F4F0}',
  social: '\u{1F4AC}', alerts: '\u{1F514}', bridge: '\u{1F517}',
  storage: '\u{1F4BE}', custom: '\u2699\uFE0F', screener: '\u{1F50D}',
  macro: '\u{1F30D}', knowledge: '\u{1F4DA}',
};

// Provider chip suggestions for the AI add-source bar (mockup 09)
const PROVIDER_CHIPS = ['Polygon.io', 'Benzinga', 'Alpha Vantage', 'Quandl', 'IEX Cloud', 'CoinGecko'];

// Filter tabs matching mockup 09
const FILTER_TABS = [
  'all', 'screener', 'options_flow', 'market', 'macro', 'filings',
  'sentiment', 'news', 'social', 'knowledge',
];

// Helper: colored latency text matching mockup (green <100ms, orange <500ms, red >=500ms)
function latencyColor(ms) {
  if (ms == null) return 'text-gray-500';
  if (ms < 100) return 'text-emerald-400';
  if (ms < 500) return 'text-orange-400';
  return 'text-red-400';
}

// Mini sparkline SVG (8 data points)
function MiniSparkline({ data = [], color = '#06b6d4' }) {
  if (!data || data.length < 2) return <span className="text-gray-600 text-xs">--</span>;
  const max = Math.max(...data);
  const min = Math.min(...data);
  const range = max - min || 1;
  const w = 60;
  const h = 20;
  const points = data.map((v, i) => {
    const x = (i / (data.length - 1)) * w;
    const y = h - ((v - min) / range) * h;
    return `${x},${y}`;
  }).join(' ');
  return (
    <svg width={w} height={h} className="inline-block">
      <polyline fill="none" stroke={color} strokeWidth="1.5" points={points} />
    </svg>
  );
}

function StatusBadge({ status }) {
  const colors = STATUS_COLORS[status] || STATUS_COLORS.pending;
  return (
    <span className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium ${colors.bg} ${colors.text}`}>
      <span className={`w-1.5 h-1.5 rounded-full ${colors.dot}`} />
      {status}
    </span>
  );
}

function Toast({ message, type, onDismiss }) {
  if (!message) return null;
  const colors = type === 'error'
    ? 'bg-red-500/20 border-red-500/40 text-red-400'
    : 'bg-emerald-500/20 border-emerald-500/40 text-emerald-400';
  return (
    <div className={`fixed top-4 right-4 z-50 px-4 py-3 rounded-lg border ${colors} flex items-center gap-2 shadow-lg`}>
      {type === 'error' ? '\u274C' : '\u2705'} {message}
      <button onClick={onDismiss} className="ml-2 opacity-60 hover:opacity-100">\u2715</button>
    </div>
  );
}
// Persistent right-side Credential Editor Panel (matches mockup 09)
function CredentialPanel({ source, onClose, onSave, onTest, saving, testing }) {
  const [keys, setKeys] = useState({});
  const [showKeys, setShowKeys] = useState({});
  const [extraFields, setExtraFields] = useState({ base_url: '', ws_url: '', rate_limit: '', polling_interval: 'real-time', account_type: '' });
  const [testLog, setTestLog] = useState([]);
  const [testResult, setTestResult] = useState(null);

  useEffect(() => {
    const init = {};
    const vis = {};
    (source?.required_keys || []).forEach((k) => { init[k] = ''; vis[k] = false; });
    setKeys(init);
    setShowKeys(vis);
    setExtraFields({
      base_url: source?.base_url || '',
      ws_url: source?.ws_url || '',
      rate_limit: source?.rate_limit || '',
      polling_interval: source?.polling_interval || 'real-time',
      account_type: source?.account_type || '',
    });
    setTestLog(source?.connection_log || []);
    setTestResult(source?.status === 'healthy' && source?.last_latency_ms != null
      ? { ok: true, latency: source.last_latency_ms, detail: source.account_info || '' }
      : null);
  }, [source]);

  const handleTest = async () => {
    if (!source || !onTest) return;
    const result = await onTest(source.id);
    if (result) setTestResult(result);
  };

  if (!source) return (
    <div className="bg-[#1A1F2E] border border-[#2A3444] rounded-xl p-8 text-center">
      <p className="text-gray-500 text-sm">Select a source to edit credentials</p>
    </div>
  );

  return (
    <div className="bg-[#1A1F2E] border border-[#2A3444] rounded-xl overflow-hidden sticky top-6">
      {/* Header */}
      <div className="p-4 border-b border-[#2A3444] bg-[#0A0E1A]/50">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <span className="text-2xl">{CATEGORY_ICONS[source.category] || '\u2699\uFE0F'}</span>
            <div>
              <h3 className="text-white font-bold">{source.name}</h3>
              <span className="text-xs text-gray-500">{CATEGORY_LABELS[source.category] || source.category}</span>
            </div>
          </div>
          <button onClick={onClose} className="text-gray-500 hover:text-white text-sm">\u2715</button>
        </div>
      </div>

      {/* Fields */}
      <div className="p-4 space-y-3 max-h-[calc(100vh-300px)] overflow-y-auto">
        {(source.required_keys || []).map((keyName) => (
          <div key={keyName}>
            <label className="text-xs text-gray-400 mb-1 block">{keyName}</label>
            <div className="flex gap-1">
              <input type={showKeys[keyName] ? 'text' : 'password'} value={keys[keyName] || ''}
                onChange={(e) => setKeys({ ...keys, [keyName]: e.target.value })}
                className="flex-1 px-3 py-2 bg-[#0A0E1A] border border-[#2A3444] rounded-lg text-white text-sm focus:border-cyan-500 focus:outline-none"
                placeholder={source.has_credentials ? '\u2022\u2022\u2022\u2022\u2022\u2022\u2022\u2022' : `Enter ${keyName}...`}
                disabled={saving} />
              <button onClick={() => setShowKeys({ ...showKeys, [keyName]: !showKeys[keyName] })}
                className="px-2 py-1 bg-[#0A0E1A] border border-[#2A3444] rounded-lg text-gray-400 hover:text-white text-xs"
                title="Show/Hide">{showKeys[keyName] ? '\u{1F441}' : '\u2022\u2022'}</button>
              <button onClick={() => navigator.clipboard.writeText(keys[keyName] || '')}
                className="px-2 py-1 bg-[#0A0E1A] border border-[#2A3444] rounded-lg text-gray-400 hover:text-white text-xs"
                title="Copy">Copy</button>
              <button className="px-2 py-1 bg-[#0A0E1A] border border-[#2A3444] rounded-lg text-gray-400 hover:text-white text-xs"
                title="Rotate">Rotate</button>
            </div>
          </div>
        ))}

        <div>
          <label className="text-xs text-gray-400 mb-1 block">Base URL</label>
          <input value={extraFields.base_url} onChange={(e) => setExtraFields({ ...extraFields, base_url: e.target.value })}
            className="w-full px-3 py-2 bg-[#0A0E1A] border border-[#2A3444] rounded-lg text-white text-sm focus:border-cyan-500 focus:outline-none" disabled={saving} />
        </div>
        <div>
          <label className="text-xs text-gray-400 mb-1 block">WebSocket URL</label>
          <input value={extraFields.ws_url} onChange={(e) => setExtraFields({ ...extraFields, ws_url: e.target.value })}
            className="w-full px-3 py-2 bg-[#0A0E1A] border border-[#2A3444] rounded-lg text-white text-sm focus:border-cyan-500 focus:outline-none" disabled={saving} />
        </div>
        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="text-xs text-gray-400 mb-1 block">Rate Limit</label>
            <input value={extraFields.rate_limit} onChange={(e) => setExtraFields({ ...extraFields, rate_limit: e.target.value })}
              className="w-full px-3 py-2 bg-[#0A0E1A] border border-[#2A3444] rounded-lg text-white text-sm focus:border-cyan-500 focus:outline-none" disabled={saving} />
          </div>
          <div>
            <label className="text-xs text-gray-400 mb-1 block">Polling Interval</label>
            <select value={extraFields.polling_interval} onChange={(e) => setExtraFields({ ...extraFields, polling_interval: e.target.value })}
              className="w-full px-3 py-2 bg-[#0A0E1A] border border-[#2A3444] rounded-lg text-white text-sm focus:border-cyan-500 focus:outline-none">
              <option value="real-time">Real-time (WebSocket)</option>
              <option value="1s">1 second</option>
              <option value="5s">5 seconds</option>
              <option value="30s">30 seconds</option>
              <option value="1m">1 minute</option>
              <option value="5m">5 minutes</option>
              <option value="15m">15 minutes</option>
            </select>
          </div>
        </div>
        <div>
          <label className="text-xs text-gray-400 mb-1 block">Account Type</label>
          <select value={extraFields.account_type} onChange={(e) => setExtraFields({ ...extraFields, account_type: e.target.value })}
            className="w-full px-3 py-2 bg-[#0A0E1A] border border-[#2A3444] rounded-lg text-white text-sm focus:border-cyan-500 focus:outline-none">
            <option value="">Select...</option>
            <option value="paper">Paper Trading</option>
            <option value="live">Live Trading</option>
            <option value="free">Free Tier</option>
            <option value="pro">Pro / Paid</option>
          </select>
        </div>

        {/* Connection Test Result (mockup 09) */}
        {testResult && testResult.ok && (
          <div className="bg-emerald-500/10 border border-emerald-500/20 rounded-lg p-3">
            <div className="text-emerald-400 text-xs font-bold">Connection Test Result</div>
            <div className="text-emerald-400 text-xs mt-1">\u2705 Connected in {testResult.latency}ms{testResult.detail ? ` - ${testResult.detail}` : ''}</div>
          </div>
        )}

        {/* Action Buttons (mockup 09: Test Connection, Save Changes, Cancel, Reset to Default) */}
        <div className="flex gap-2 pt-2 flex-wrap">
          <button onClick={handleTest} disabled={testing}
            className="px-3 py-2 bg-cyan-600/20 text-cyan-400 border border-cyan-500/30 rounded-lg hover:bg-cyan-600/30 text-xs font-medium disabled:opacity-50">
            {testing ? '\u23F3 Testing...' : 'Test Connection'}
          </button>
          <button onClick={() => onSave(keys)} disabled={saving}
            className="px-3 py-2 bg-emerald-600 text-white rounded-lg hover:bg-emerald-700 text-xs font-medium disabled:opacity-50">
            {saving ? '\u23F3 Saving...' : 'Save Changes'}
          </button>
          <button onClick={onClose}
            className="px-3 py-2 bg-gray-600/20 text-gray-400 rounded-lg hover:bg-gray-600/30 text-xs">
            Cancel
          </button>
          <button className="px-3 py-2 bg-gray-600/20 text-gray-400 rounded-lg hover:bg-gray-600/30 text-xs">
            Reset to Default
          </button>
        </div>

        {/* Connection Log (mockup 09) */}
        {testLog.length > 0 && (
          <div className="mt-3">
            <label className="text-xs text-gray-500 mb-1 block">Connection Log</label>
            <div className="bg-[#0A0E1A] border border-[#2A3444] rounded-lg p-2 max-h-32 overflow-y-auto font-mono text-[10px] text-gray-400 space-y-0.5">
              {testLog.map((log, i) => <div key={i}>{log}</div>)}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

function AddSourceModal({ onClose, onAdd, saving }) {
  const [form, setForm] = useState({ id: '', name: '', base_url: '', test_endpoint: '', type: 'rest', category: 'custom' });
  return (
    <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50" onClick={onClose}>
      <div className="bg-[#1A1F2E] border border-[#2A3444] rounded-xl p-6 w-full max-w-md" onClick={(e) => e.stopPropagation()}>
        <h3 className="text-lg font-bold text-white mb-4">\u2795 Add Custom Source</h3>
        {['id', 'name', 'base_url', 'test_endpoint'].map((field) => (
          <div key={field} className="mb-3">
            <label className="text-sm text-gray-400 mb-1 block">{field}</label>
            <input value={form[field]} onChange={(e) => setForm({ ...form, [field]: e.target.value })}
              className="w-full px-3 py-2 bg-[#0A0E1A] border border-[#2A3444] rounded-lg text-white text-sm focus:border-cyan-500 focus:outline-none" disabled={saving} />
          </div>
        ))}
        <div className="flex gap-2 mt-4">
          <button onClick={onClose} className="flex-1 px-4 py-2 bg-gray-600/20 text-gray-400 rounded-lg hover:bg-gray-600/30 text-sm">Cancel</button>
          <button onClick={() => onAdd(form)} disabled={saving} className="flex-1 px-4 py-2 bg-cyan-600 text-white rounded-lg hover:bg-cyan-700 text-sm font-medium disabled:opacity-50">
            {saving ? '\u23F3 Adding...' : 'Add Source'}
          </button>
        </div>
      </div>
    </div>
  );
}

function AIDetectModal({ onClose, onDetect }) {
  const [url, setUrl] = useState('');
  const [result, setResult] = useState(null);
  const [detecting, setDetecting] = useState(false);
  const [error, setError] = useState(null);
  const handleDetect = async () => {
    setDetecting(true); setError(null);
    try { const res = await onDetect(url); setResult(res); }
    catch (err) { setError(err.message); setResult(null); }
    finally { setDetecting(false); }
  };
  return (
    <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50" onClick={onClose}>
      <div className="bg-[#1A1F2E] border border-[#2A3444] rounded-xl p-6 w-full max-w-md" onClick={(e) => e.stopPropagation()}>
        <h3 className="text-lg font-bold text-white mb-4">\u2699 AI Detect Provider</h3>
        <input value={url} onChange={(e) => setUrl(e.target.value)} placeholder="Paste API URL..."
          className="w-full px-3 py-2 bg-[#0A0E1A] border border-[#2A3444] rounded-lg text-white text-sm mb-4 focus:border-cyan-500 focus:outline-none" disabled={detecting} />
        <button onClick={handleDetect} disabled={detecting} className="w-full px-4 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700 text-sm font-medium mb-4 disabled:opacity-50">
          {detecting ? '\u23F3 Detecting...' : 'Detect'}
        </button>
        {error && <div className="p-3 bg-red-500/20 border border-red-500/30 rounded-lg text-red-400 text-sm mb-4">\u274C {error}</div>}
        {result && (
          <div className="p-3 bg-[#0A0E1A] border border-[#2A3444] rounded-lg text-sm">
            <div className="text-cyan-400 font-bold">{result.detected_provider || 'Unknown'}</div>
            <div className="text-gray-400 mt-1">{result.suggestion}</div>
            {result.confidence > 0 && <div className="text-emerald-400 mt-1">Confidence: {(result.confidence * 100).toFixed(0)}%</div>}
          </div>
        )}
        <button onClick={onClose} className="w-full mt-4 px-4 py-2 bg-gray-600/20 text-gray-400 rounded-lg hover:bg-gray-600/30 text-sm">Close</button>
      </div>
    </div>
  );
}

function DeleteConfirmModal({ sourceId, onClose, onConfirm, deleting }) {
  return (
    <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50" onClick={onClose}>
      <div className="bg-[#1A1F2E] border border-[#2A3444] rounded-xl p-6 w-full max-w-sm" onClick={(e) => e.stopPropagation()}>
        <h3 className="text-lg font-bold text-white mb-4">Delete Source</h3>
        <p className="text-gray-400 text-sm mb-4">Permanently delete <span className="text-white font-medium">"{sourceId}"</span>? This cannot be undone.</p>
        <div className="flex gap-2">
          <button onClick={onClose} className="flex-1 px-4 py-2 bg-gray-600/20 text-gray-400 rounded-lg hover:bg-gray-600/30 text-sm">Cancel</button>
          <button onClick={onConfirm} disabled={deleting} className="flex-1 px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 text-sm font-medium disabled:opacity-50">
            {deleting ? '\u23F3 Deleting...' : 'Delete'}
          </button>
        </div>
      </div>
    </div>
  );
}

// ============================================================
// MAIN COMPONENT - Data Sources Manager
// Matches mockup 09: inline top metrics bar, AI add-source input,
// category filter tabs, source table with sparklines/latency/uptime,
// persistent right credential panel, supplementary sources, footer
// ============================================================
export default function DataSourcesMonitor() {
  const [sources, setSources] = useState([]);
  const [loading, setLoading] = useState(true);
  const [testing, setTesting] = useState(null);
  const [testingAll, setTestingAll] = useState(false);
  const [testAllProgress, setTestAllProgress] = useState({ current: 0, total: 0 });
  const [actionLoading, setActionLoading] = useState(false);
  const [selectedSource, setSelectedSource] = useState(null);
  const [addModal, setAddModal] = useState(false);
  const [detectModal, setDetectModal] = useState(false);
  const [deleteModal, setDeleteModal] = useState(null);
  const [filter, setFilter] = useState('all');
  const [searchQuery, setSearchQuery] = useState('');
  const [addSourceInput, setAddSourceInput] = useState('');
  const [toast, setToast] = useState({ message: '', type: 'success' });

  const showToast = (message, type = 'success') => {
    setToast({ message, type });
    setTimeout(() => setToast({ message: '', type: 'success' }), 4000);
  };

  const fetchSources = useCallback(async () => {
    try {
      const data = await dataSources.list();
      setSources(data);
    } catch (err) {
      console.error('Failed to fetch sources:', err);
      showToast(`Refresh failed: ${err.message}`, 'error');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchSources();
    const interval = setInterval(fetchSources, 30000);
    return () => clearInterval(interval);
  }, [fetchSources]);

  const handleTest = async (sourceId) => {
    setTesting(sourceId);
    try {
      const result = await dataSources.test(sourceId);
      await fetchSources();
      showToast(`${sourceId} test complete`);
      return result;
    } catch (err) {
      showToast(`Test failed: ${err.message}`, 'error');
      await fetchSources();
      return null;
    } finally { setTesting(null); }
  };

  const handleToggle = async (source) => {
    try {
      await dataSources.update(source.id, { enabled: !source.enabled });
      await fetchSources();
      showToast(`${source.name} ${source.enabled ? 'disabled' : 'enabled'}`);
    } catch (err) { showToast(`Toggle failed: ${err.message}`, 'error'); }
  };

  const handleSaveCreds = async (keys) => {
    setActionLoading(true);
    try {
      await dataSources.setCredentials(selectedSource.id, keys);
      await fetchSources();
      showToast('Credentials saved & encrypted');
    } catch (err) { showToast(`Save failed: ${err.message}`, 'error'); }
    finally { setActionLoading(false); }
  };

  const handleAddSource = async (form) => {
    setActionLoading(true);
    try {
      await dataSources.create(form);
      setAddModal(false);
      await fetchSources();
      showToast(`Source "${form.name}" added`);
    } catch (err) { showToast(`Add failed: ${err.message}`, 'error'); }
    finally { setActionLoading(false); }
  };

  const handleDelete = async () => {
    if (!deleteModal) return;
    setActionLoading(true);
    try {
      await dataSources.remove(deleteModal);
      setDeleteModal(null);
      if (selectedSource?.id === deleteModal) setSelectedSource(null);
      await fetchSources();
      showToast('Source deleted');
    } catch (err) { showToast(`Delete failed: ${err.message}`, 'error'); }
    finally { setActionLoading(false); }
  };

  const handleAIDetect = async (url) => await dataSources.aiDetect(url);

  const handleTestAll = async () => {
    const enabled = sources.filter((s) => s.enabled);
    setTestingAll(true);
    setTestAllProgress({ current: 0, total: enabled.length });
    try {
      for (let i = 0; i < enabled.length; i++) {
        setTestAllProgress({ current: i + 1, total: enabled.length });
        try { await dataSources.test(enabled[i].id); } catch (e) { /* continue */ }
      }
      await fetchSources();
      showToast(`Tested ${enabled.length} sources`);
    } catch (err) { showToast(`Test All failed: ${err.message}`, 'error'); }
    finally { setTestingAll(false); setTestAllProgress({ current: 0, total: 0 }); }
  };

  // Derived data
  const healthyCount = sources.filter((s) => s.status === 'healthy' || s.status === 'active').length;
  const errorCount = sources.filter((s) => ['error', 'timeout', 'offline'].includes(s.status)).length;
  const systemHealth = sources.length > 0 ? Math.round((healthyCount / sources.length) * 100) : 0;
  const totalIngestion = sources.reduce((sum, s) => sum + (s.records_per_min || 0), 0);
  const hasWs = sources.some((s) => s.type === 'websocket');

  // Separate primary (table rows) from supplementary (bottom cards)
  const primarySources = sources.filter((s) => !s.supplementary);
  const supplementarySources = sources.filter((s) => s.supplementary);

  // Apply filter + search
  const filtered = primarySources
    .filter((s) => filter === 'all' || s.category === filter)
    .filter((s) => !searchQuery || s.name.toLowerCase().includes(searchQuery.toLowerCase()) || s.id.toLowerCase().includes(searchQuery.toLowerCase()));

  if (loading) {
    return (
      <div className="flex items-center justify-center h-96">
        <div className="text-center">
          <div className="w-8 h-8 border-2 border-cyan-500 border-t-transparent rounded-full animate-spin mx-auto mb-4" />
          <p className="text-gray-400">Loading data sources...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="p-6 max-w-[1600px] mx-auto">
      <Toast message={toast.message} type={toast.type} onDismiss={() => setToast({ message: '', type: 'success' })} />

      {/* TOP METRICS BAR (Mockup 09 - inline bar) */}
      <div className="flex items-center justify-between bg-[#1A1F2E] border border-[#2A3444] rounded-xl px-5 py-3 mb-4 text-sm">
        <div className="flex items-center gap-6">
          <span className="text-gray-400">Connected: <span className="text-white font-bold">{healthyCount}/{sources.length} sources</span>
            <span className={`ml-1 w-2 h-2 rounded-full inline-block ${healthyCount > 0 ? 'bg-emerald-400' : 'bg-red-400'}`} /></span>
          <span className="text-gray-400">System Health: <span className={`font-bold ${systemHealth >= 80 ? 'text-emerald-400' : systemHealth >= 50 ? 'text-yellow-400' : 'text-red-400'}`}>{systemHealth}%</span></span>
          <span className="text-gray-400">Ingestion: <span className="text-white font-bold">{totalIngestion > 1000 ? `${(totalIngestion / 1000).toFixed(1)}K` : totalIngestion} rec/min</span></span>
          <span className="text-gray-400">OpenClaw Bridge: <span className="text-emerald-400 font-bold">CONNECTED</span></span>
        </div>
        <div className="flex items-center gap-4">
          <span className="flex items-center gap-1.5">
            <span className={`w-2 h-2 rounded-full ${hasWs ? 'bg-emerald-400 animate-pulse' : 'bg-gray-500'}`} />
            <span className="text-gray-400">WS: <span className={hasWs ? 'text-emerald-400 font-bold' : 'text-gray-500'}>CONNECTED</span></span>
          </span>
          <button onClick={fetchSources} className="px-3 py-1.5 bg-cyan-600 text-white rounded-lg hover:bg-cyan-700 text-xs font-medium">
            Refresh
          </button>
        </div>
      </div>
      {/* AI-POWERED ADD SOURCE INPUT (Mockup 09) */}
      <div className="bg-[#1A1F2E] border border-[#2A3444] rounded-xl px-5 py-4 mb-4">
        <div className="flex items-center gap-3">
          <div className="flex-1 relative">
            <span className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-500">\u{1F50D}</span>
            <input value={addSourceInput} onChange={(e) => setAddSourceInput(e.target.value)}
              placeholder="Type a service name, URL, or paste API docs link..."
              className="w-full pl-10 pr-4 py-2.5 bg-[#0A0E1A] border border-[#2A3444] rounded-lg text-white text-sm focus:border-cyan-500 focus:outline-none" />
          </div>
          <button onClick={() => setDetectModal(true)} className="px-4 py-2.5 bg-gray-600/20 text-gray-400 border border-[#2A3444] rounded-lg hover:bg-gray-600/30 text-sm whitespace-nowrap">
            Or browse...
          </button>
        </div>
        <div className="flex gap-2 mt-3 flex-wrap">
          {PROVIDER_CHIPS.map((chip) => (
            <button key={chip} onClick={() => setAddSourceInput(chip)}
              className="px-3 py-1 bg-[#0A0E1A] border border-[#2A3444] rounded-full text-xs text-gray-400 hover:text-white hover:border-cyan-500/50 transition-colors">
              {chip}
            </button>
          ))}
        </div>
      </div>

      {/* CATEGORY FILTER TABS + SEARCH (Mockup 09) */}
      <div className="flex items-center justify-between mb-3">
        <div className="flex gap-1.5 flex-wrap">
          {FILTER_TABS.map((tab) => {
            const count = tab === 'all' ? primarySources.length : primarySources.filter((s) => s.category === tab).length;
            if (tab !== 'all' && count === 0) return null;
            return (
              <button key={tab} onClick={() => setFilter(tab)}
                className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-colors ${filter === tab ? 'bg-cyan-600 text-white' : 'bg-[#1A1F2E] text-gray-400 hover:text-white border border-[#2A3444]'}`}>
                {tab === 'all' ? 'ALL' : `[${CATEGORY_LABELS[tab] || tab}]`}
              </button>
            );
          })}
        </div>
        <input value={searchQuery} onChange={(e) => setSearchQuery(e.target.value)}
          placeholder="Search" className="px-3 py-1.5 bg-[#0A0E1A] border border-[#2A3444] rounded-lg text-white text-xs w-40 focus:border-cyan-500 focus:outline-none" />
      </div>

      {/* SPLIT LAYOUT: SOURCE TABLE + RIGHT CREDENTIAL PANEL */}
      <div className="flex gap-6">
        <div className="flex-1 min-w-0">
          <div className="bg-[#1A1F2E] border border-[#2A3444] rounded-xl overflow-hidden">
            <div className="divide-y divide-[#2A3444]/50">
              {filtered.map((source) => (
                <div key={source.id} onClick={() => setSelectedSource(source)}
                  className={`flex items-center gap-4 px-4 py-3 cursor-pointer transition-colors ${selectedSource?.id === source.id ? 'bg-cyan-900/20' : 'hover:bg-[#0A0E1A]/30'} ${!source.enabled ? 'opacity-50' : ''}`}>
                  <div className="flex items-center gap-3 w-48 flex-shrink-0">
                    <span className="text-lg">{CATEGORY_ICONS[source.category] || '\u2699\uFE0F'}</span>
                    <div>
                      <div className="text-white font-semibold text-sm">{source.name}</div>
                      <div className="text-gray-500 text-[10px]">{CATEGORY_LABELS[source.category] || source.category}</div>
                    </div>
                  </div>
                  <div className="w-24 flex-shrink-0"><StatusBadge status={source.status} /></div>
                  <div className={`w-16 text-right font-mono text-sm flex-shrink-0 ${latencyColor(source.last_latency_ms)}`}>
                    {source.last_latency_ms != null ? `${source.last_latency_ms}ms` : '\u2014'}
                  </div>
                  <div className="w-16 flex-shrink-0"><MiniSparkline data={source.latency_history} /></div>
                  <div className="w-14 text-right text-white text-xs font-mono flex-shrink-0">
                    {source.record_count != null ? (source.record_count > 1000 ? `${(source.record_count / 1000).toFixed(1)}K` : source.record_count) : ''}
                  </div>
                  <div className="w-14 text-right text-gray-400 text-xs font-mono flex-shrink-0">
                    {source.uptime_pct != null ? `${source.uptime_pct}%` : ''}
                  </div>
                  <div className="flex-1 min-w-0 text-right text-gray-500 text-[10px] font-mono truncate">
                    {source.masked_key || ''}
                    {source.live_ping && <span className="ml-2 px-1.5 py-0.5 bg-emerald-500/20 text-emerald-400 rounded text-[9px] font-bold">LIVE PING</span>}
                    {source.sync_schedule && <span className="ml-2 text-gray-600">{source.sync_schedule}</span>}
                  </div>
                  <div className="flex gap-1 flex-shrink-0" onClick={(e) => e.stopPropagation()}>
                    <button onClick={() => handleTest(source.id)} disabled={testing === source.id || testingAll}
                      className="px-2 py-1 bg-cyan-600/20 text-cyan-400 rounded text-[10px] font-bold hover:bg-cyan-600/30 disabled:opacity-50">
                      {testing === source.id ? '\u23F3' : '\u26A1'}
                    </button>
                    <button onClick={() => handleToggle(source)}
                      className={`px-2 py-1 rounded text-[10px] font-bold ${source.enabled ? 'bg-emerald-600/20 text-emerald-400 hover:bg-red-600/20 hover:text-red-400' : 'bg-gray-600/20 text-gray-400 hover:bg-emerald-600/20 hover:text-emerald-400'}`}>
                      {source.enabled ? '\u2705' : '\u26D4'}
                    </button>
                    <button onClick={() => setDeleteModal(source.id)}
                      className="px-2 py-1 bg-red-600/20 text-red-400 rounded text-[10px] font-bold hover:bg-red-600/30">\u2715</button>
                  </div>
                </div>
              ))}
              {filtered.length === 0 && <div className="p-12 text-center text-gray-500">No sources match filter.</div>}
            </div>
          </div>

          {/* SUPPLEMENTARY SOURCES (Mockup 09 bottom) */}
          {supplementarySources.length > 0 && (
            <div className="mt-4">
              <div className="text-[10px] text-gray-500 uppercase tracking-wider mb-2 font-semibold">Supplementary</div>
              <div className="flex gap-3 flex-wrap">
                {supplementarySources.map((s) => (
                  <div key={s.id} className="flex items-center gap-2 bg-[#1A1F2E] border border-[#2A3444] rounded-lg px-3 py-2">
                    <span className="text-sm">{CATEGORY_ICONS[s.category] || '\u2699\uFE0F'}</span>
                    <span className="text-white text-xs font-medium">{s.name}</span>
                    <StatusBadge status={s.status} />
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* FOOTER TELEMETRY (Mockup 09) */}
          <div className="flex items-center justify-between mt-3 px-2 text-[10px] text-gray-600">
            <div className="flex gap-4">
              {sources.filter((s) => s.sync_schedule).map((s) => (
                <span key={s.id}>{s.name}: {s.sync_schedule}</span>
              ))}
            </div>
            <span>System telemetry: {sources.length} | Auto-refresh: 30s</span>
          </div>
        </div>

        {/* RIGHT: Credential Editor Panel (Mockup 09) */}
        <div className="w-80 flex-shrink-0 hidden xl:block">
          <CredentialPanel source={selectedSource} onClose={() => setSelectedSource(null)}
            onSave={handleSaveCreds} onTest={handleTest} saving={actionLoading} testing={testing === selectedSource?.id} />
        </div>
      </div>

      {/* MODALS */}
      {addModal && <AddSourceModal onClose={() => setAddModal(false)} onAdd={handleAddSource} saving={actionLoading} />}
      {detectModal && <AIDetectModal onClose={() => setDetectModal(false)} onDetect={handleAIDetect} />}
      {deleteModal && <DeleteConfirmModal sourceId={deleteModal} onClose={() => setDeleteModal(null)} onConfirm={handleDelete} deleting={actionLoading} />}
    </div>
  );
}
