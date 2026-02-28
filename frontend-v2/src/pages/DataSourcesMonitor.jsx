import { useState, useEffect, useCallback } from 'react';
import dataSources from '../services/dataSourcesApi';

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
  storage: 'Storage', custom: 'Custom',
};

const CATEGORY_ICONS = {
  market: '\u{1F4C8}', options_flow: '\u{1F40B}', economic: '\u{1F3DB}\uFE0F',
  filings: '\u{1F4CB}', sentiment: '\u{1F9E0}', news: '\u{1F4F0}',
  social: '\u{1F4AC}', alerts: '\u{1F514}', bridge: '\u{1F517}',
  storage: '\u{1F4BE}', custom: '\u2699\uFE0F',
};

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
function CredentialPanel({ source, onClose, onSave, saving }) {
  const [keys, setKeys] = useState({});
  const [extraFields, setExtraFields] = useState({ base_url: '', ws_url: '', rate_limit: '', polling_interval: 'real-time', account_type: '' });
  const [testLog, setTestLog] = useState([]);
  useEffect(() => {
    const init = {};
    (source?.required_keys || []).forEach((k) => { init[k] = ''; });
    setKeys(init);
    setExtraFields({
      base_url: source?.base_url || '',
      ws_url: source?.ws_url || '',
      rate_limit: source?.rate_limit || '',
      polling_interval: source?.polling_interval || 'real-time',
      account_type: source?.account_type || '',
    });
    setTestLog(source?.connection_log || []);
  }, [source]);
  if (!source) return (
    <div className="bg-[#1A1F2E] border border-[#2A3444] rounded-xl p-8 text-center">
      <p className="text-gray-500 text-sm">Select a source to edit credentials</p>
    </div>
  );
  return (
    <div className="bg-[#1A1F2E] border border-[#2A3444] rounded-xl overflow-hidden sticky top-6">
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
      <div className="p-4 space-y-3 max-h-[calc(100vh-300px)] overflow-y-auto">
        {(source.required_keys || []).map((keyName) => (
          <div key={keyName}>
            <label className="text-xs text-gray-400 mb-1 block">{keyName}</label>
            <input type="password" value={keys[keyName] || ''}
              onChange={(e) => setKeys({ ...keys, [keyName]: e.target.value })}
              className="w-full px-3 py-2 bg-[#0A0E1A] border border-[#2A3444] rounded-lg text-white text-sm focus:border-cyan-500 focus:outline-none"
              placeholder={source.has_credentials ? '\u2022\u2022\u2022\u2022\u2022\u2022\u2022\u2022' : `Enter ${keyName}...`}
              disabled={saving} />
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
        {/* Connection Test Result */}
        {source.status === 'healthy' && source.last_latency_ms != null && (
          <div className="bg-emerald-500/10 border border-emerald-500/20 rounded-lg p-3">
            <div className="text-emerald-400 text-xs font-bold">\u2705 Connected in {source.last_latency_ms}ms</div>
          </div>
        )}
        <div className="flex gap-2 pt-2">
          <button onClick={() => onSave(keys)} disabled={saving}
            className="flex-1 px-4 py-2 bg-cyan-600 text-white rounded-lg hover:bg-cyan-700 text-sm font-medium disabled:opacity-50">
            {saving ? '\u23F3 Saving...' : 'Save Changes'}
          </button>
        </div>
        {/* Connection Log */}
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
        <h3 className="text-lg font-bold text-white mb-4">{"\u{1F916}"} AI Detect Provider</h3>
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
        <h3 className="text-lg font-bold text-white mb-4">\u{1F5D1}\uFE0F Delete Source</h3>
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

// ══════════════════════════════════════════════════════
// MAIN COMPONENT — Data Sources Manager
// Matches mockup 09: top metrics bar + table layout + persistent right credential panel
// ══════════════════════════════════════════════════════
export default function DataSourcesMonitor() {
  const [sources, setSources] = useState([]);
  const [loading, setLoading] = useState(true);
  const [testing, setTesting] = useState(null);
  const [testingAll, setTestingAll] = useState(false);
  const [testAllProgress, setTestAllProgress] = useState({ current: 0, total: 0 });
  const [actionLoading, setActionLoading] = useState(false);
  const [selectedSource, setSelectedSource] = useState(null); // for right panel
  const [addModal, setAddModal] = useState(false);
  const [detectModal, setDetectModal] = useState(false);
  const [deleteModal, setDeleteModal] = useState(null);
  const [filter, setFilter] = useState('all');
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
      await dataSources.test(sourceId);
      await fetchSources();
      showToast(`${sourceId} test complete`);
    } catch (err) {
      showToast(`Test failed: ${err.message}`, 'error');
      await fetchSources();
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
      showToast(`Source deleted`);
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
  const categories = [...new Set(sources.map((s) => s.category))];
  const filtered = filter === 'all' ? sources : sources.filter((s) => s.category === filter);
  const healthyCount = sources.filter((s) => s.status === 'healthy' || s.status === 'active').length;
  const errorCount = sources.filter((s) => ['error', 'timeout', 'offline'].includes(s.status)).length;
  const systemHealth = sources.length > 0 ? Math.round((healthyCount / sources.length) * 100) : 0;
  const avgLatency = sources.filter((s) => s.last_latency_ms).reduce((a, s) => a + s.last_latency_ms, 0) / (sources.filter((s) => s.last_latency_ms).length || 1);

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

      {/* ══ TOP METRICS BAR (Mockup 09) ══ */}
      <div className="grid grid-cols-2 md:grid-cols-5 gap-3 mb-6">
        <div className="bg-[#1A1F2E] border border-[#2A3444] rounded-xl p-4 text-center">
          <div className="text-2xl font-black text-white">{healthyCount}/{sources.length}</div>
          <div className="text-[10px] text-gray-500 mt-1">Connected Sources</div>
        </div>
        <div className="bg-[#1A1F2E] border border-[#2A3444] rounded-xl p-4 text-center">
          <div className={`text-2xl font-black ${systemHealth >= 80 ? 'text-emerald-400' : systemHealth >= 50 ? 'text-yellow-400' : 'text-red-400'}`}>{systemHealth}%</div>
          <div className="text-[10px] text-gray-500 mt-1">System Health</div>
        </div>
        <div className="bg-[#1A1F2E] border border-[#2A3444] rounded-xl p-4 text-center">
          <div className="text-2xl font-black text-cyan-400">{avgLatency > 0 ? `${Math.round(avgLatency)}ms` : '--'}</div>
          <div className="text-[10px] text-gray-500 mt-1">Avg Latency</div>
        </div>
        <div className="bg-[#1A1F2E] border border-[#2A3444] rounded-xl p-4 text-center">
          <div className="text-2xl font-black text-purple-400">{sources.filter(s => s.type === 'websocket').length > 0 ? 'LIVE' : 'REST'}</div>
          <div className="text-[10px] text-gray-500 mt-1">OpenClaw Bridge</div>
        </div>
        <div className="bg-[#1A1F2E] border border-[#2A3444] rounded-xl p-4 text-center">
          <div className="flex items-center justify-center gap-1.5">
            <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
            <span className="text-emerald-400 text-sm font-bold">CONNECTED</span>
          </div>
          <div className="text-[10px] text-gray-500 mt-1">WebSocket Status</div>
        </div>
      </div>

      {/* ══ HEADER + ACTIONS ══ */}
      <div className="flex items-center justify-between mb-4">
        <div>
          <h1 className="text-2xl font-bold text-white">Data Sources Manager</h1>
          <p className="text-sm text-gray-400 mt-1">{sources.length} sources \u00B7 {healthyCount} healthy \u00B7 {errorCount} errors</p>
        </div>
        <div className="flex gap-2">
          <button onClick={() => setDetectModal(true)} className="px-3 py-2 bg-purple-600/20 text-purple-400 border border-purple-500/30 rounded-lg hover:bg-purple-600/30 text-sm">
            {"\u{1F916}"} AI Detect
          </button>
          <button onClick={() => setAddModal(true)} className="px-3 py-2 bg-cyan-600/20 text-cyan-400 border border-cyan-500/30 rounded-lg hover:bg-cyan-600/30 text-sm">
            \u2795 Add Source
          </button>
          <button onClick={handleTestAll} disabled={testingAll} className="px-3 py-2 bg-amber-600/20 text-amber-400 border border-amber-500/30 rounded-lg hover:bg-amber-600/30 text-sm disabled:opacity-50">
            {testingAll ? `\u23F3 ${testAllProgress.current}/${testAllProgress.total}` : '\u26A1 Test All'}
          </button>
          <button onClick={fetchSources} className="px-3 py-2 bg-gray-600/20 text-gray-400 border border-gray-500/30 rounded-lg hover:bg-gray-600/30 text-sm">
            \u{1F504} Refresh
          </button>
        </div>
      </div>

      {/* ══ CATEGORY FILTER TABS ══ */}
      <div className="flex gap-2 mb-4 flex-wrap">
        <button onClick={() => setFilter('all')}
          className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-colors ${filter === 'all' ? 'bg-cyan-600 text-white' : 'bg-[#1A1F2E] text-gray-400 hover:text-white'}`}>
          All ({sources.length})
        </button>
        {categories.map((cat) => (
          <button key={cat} onClick={() => setFilter(cat)}
            className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-colors ${filter === cat ? 'bg-cyan-600 text-white' : 'bg-[#1A1F2E] text-gray-400 hover:text-white'}`}>
            {CATEGORY_ICONS[cat] || '\u2699\uFE0F'} {CATEGORY_LABELS[cat] || cat} ({sources.filter((s) => s.category === cat).length})
          </button>
        ))}
      </div>

      {/* ══ SPLIT LAYOUT: TABLE + RIGHT CREDENTIAL PANEL ══ */}
      <div className="flex gap-6">
        {/* LEFT: Sources Table */}
        <div className="flex-1 min-w-0">
          <div className="bg-[#1A1F2E] border border-[#2A3444] rounded-xl overflow-hidden">
            <table className="w-full text-left border-collapse">
              <thead>
                <tr className="bg-[#0A0E1A]/50 border-b border-[#2A3444] text-[10px] uppercase tracking-wider text-gray-500">
                  <th className="p-3 font-semibold">Source</th>
                  <th className="p-3 font-semibold">Category</th>
                  <th className="p-3 font-semibold">Status</th>
                  <th className="p-3 font-semibold text-center">Latency</th>
                  <th className="p-3 font-semibold text-center">Last Test</th>
                  <th className="p-3 font-semibold text-center">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[#2A3444]/50">
                {filtered.map((source) => (
                  <tr key={source.id}
                    onClick={() => setSelectedSource(source)}
                    className={`cursor-pointer transition-colors ${selectedSource?.id === source.id ? 'bg-cyan-900/20' : 'hover:bg-[#0A0E1A]/30'} ${!source.enabled ? 'opacity-50' : ''}`}>
                    <td className="p-3">
                      <div className="flex items-center gap-2">
                        <span className="text-lg">{CATEGORY_ICONS[source.category] || '\u2699\uFE0F'}</span>
                        <div>
                          <div className="text-white font-semibold text-sm">{source.name}</div>
                          <div className="text-gray-500 text-[10px]">{source.type} \u00B7 {source.id}</div>
                        </div>
                      </div>
                    </td>
                    <td className="p-3 text-xs text-gray-400">{CATEGORY_LABELS[source.category] || source.category}</td>
                    <td className="p-3"><StatusBadge status={source.status} /></td>
                    <td className="p-3 text-center">
                      <span className="text-sm font-mono text-white">{source.last_latency_ms != null ? `${source.last_latency_ms}ms` : '\u2014'}</span>
                    </td>
                    <td className="p-3 text-center text-xs text-gray-400 font-mono">
                      {source.last_test ? new Date(source.last_test).toLocaleTimeString() : '\u2014'}
                    </td>
                    <td className="p-3">
                      <div className="flex gap-1 justify-center" onClick={(e) => e.stopPropagation()}>
                        <button onClick={() => handleTest(source.id)} disabled={testing === source.id || testingAll}
                          className="px-2 py-1 bg-cyan-600/20 text-cyan-400 rounded text-[10px] font-bold hover:bg-cyan-600/30 disabled:opacity-50">
                          {testing === source.id ? '\u23F3' : '\u26A1'}
                        </button>
                        <button onClick={() => handleToggle(source)}
                          className={`px-2 py-1 rounded text-[10px] font-bold ${source.enabled ? 'bg-emerald-600/20 text-emerald-400 hover:bg-red-600/20 hover:text-red-400' : 'bg-gray-600/20 text-gray-400 hover:bg-emerald-600/20 hover:text-emerald-400'}`}>
                          {source.enabled ? '\u2705' : '\u26D4'}
                        </button>
                        <button onClick={() => setDeleteModal(source.id)}
                          className="px-2 py-1 bg-red-600/20 text-red-400 rounded text-[10px] font-bold hover:bg-red-600/30">
                          \u{1F5D1}\uFE0F
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
                {filtered.length === 0 && (
                  <tr><td colSpan={6} className="p-12 text-center text-gray-500">No sources match filter.</td></tr>
                )}
              </tbody>
            </table>
          </div>
          {/* Footer Telemetry */}
          <div className="flex items-center justify-between mt-3 px-2 text-[10px] text-gray-600">
            <span>{sources.length} total sources \u00B7 {healthyCount} active \u00B7 {errorCount} errors</span>
            <span>Auto-refresh: 30s \u00B7 Last: {new Date().toLocaleTimeString()}</span>
          </div>
        </div>

        {/* RIGHT: Persistent Credential Editor Panel */}
        <div className="w-80 flex-shrink-0 hidden xl:block">
          <CredentialPanel
            source={selectedSource}
            onClose={() => setSelectedSource(null)}
            onSave={handleSaveCreds}
            saving={actionLoading}
          />
        </div>
      </div>

      {/* ══ MODALS ══ */}
      {addModal && <AddSourceModal onClose={() => setAddModal(false)} onAdd={handleAddSource} saving={actionLoading} />}
      {detectModal && <AIDetectModal onClose={() => setDetectModal(false)} onDetect={handleAIDetect} />}
      {deleteModal && <DeleteConfirmModal sourceId={deleteModal} onClose={() => setDeleteModal(null)} onConfirm={handleDelete} deleting={actionLoading} />}
    </div>
  );
}
