import { useState, useEffect, useCallback } from 'react';
import dataSources from '../services/dataSourcesApi';

// ============================================================
// DataSourcesMonitor.jsx - DATA_SOURCES_MANAGER
// Pixel-perfect match to mockup 09 (Split View Layout)
// Real API via dataSourcesApi.js - NO mocks, NO yfinance
// Primary: Alpaca, Unusual Whales, Finviz
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

// Short tab labels matching mockup 09 exactly
const FILTER_TAB_LABELS = {
  all: 'ALL', screener: 'Screener', options_flow: 'Options',
  market: 'Market', macro: 'Macro', filings: 'Filings',
  sentiment: 'Sentiment', news: 'News', social: 'Social',
  knowledge: 'Knowledge',
};

const FILTER_TABS = ['all', 'screener', 'options_flow', 'market', 'macro', 'filings', 'sentiment', 'news', 'social', 'knowledge'];

const PROVIDER_CHIPS = ['Polygon.io', 'Benzinga', 'Alpha Vantage', 'Quandl', 'IEX Cloud', 'CoinGecko'];

// Colored latency: green <100ms, orange <500ms, red >=500ms (mockup 09)
function latencyColor(ms) {
  if (ms == null) return 'text-gray-500';
  if (ms < 100) return 'text-emerald-400';
  if (ms < 500) return 'text-orange-400';
  return 'text-red-400';
}

// Mini sparkline SVG matching mockup 09 inline charts
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
    <span className={`inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full text-[10px] font-semibold uppercase ${colors.bg} ${colors.text}`}>
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
// Credential Editor Panel - right side (mockup 09)
// Shows: icon + name + category badge, API Key/Secret with masked values,
// Show/Copy/Rotate icon buttons, Base URL, WebSocket URL, Rate Limit,
// Polling Interval, Account Type, Connection Test Result box, action buttons, log
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
      {/* Panel Header - icon + name + category badge (mockup 09) */}
      <div className="p-4 border-b border-[#2A3444] bg-[#0A0E1A]/50">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-[#0A0E1A] rounded-lg flex items-center justify-center text-xl">
              {source.icon || CATEGORY_LABELS[source.category]?.[0] || '\u2699'}
            </div>
            <div>
              <h3 className="text-white font-bold text-base">{source.name}</h3>
              <span className="text-[10px] px-2 py-0.5 bg-cyan-600/20 text-cyan-400 rounded-full font-medium">
                {CATEGORY_LABELS[source.category] || source.category}
              </span>
            </div>
          </div>
          <button onClick={onClose} className="text-gray-500 hover:text-white text-sm">\u2715</button>
        </div>
      </div>

      {/* Credential Fields */}
      <div className="p-4 space-y-3 max-h-[calc(100vh-300px)] overflow-y-auto">
        {(source.required_keys || []).map((keyName) => (
          <div key={keyName}>
            <label className="text-xs text-gray-400 mb-1 block">{keyName}</label>
            <div className="flex items-center gap-1">
              <input type={showKeys[keyName] ? 'text' : 'password'} value={keys[keyName] || ''}
                onChange={(e) => setKeys({ ...keys, [keyName]: e.target.value })}
                className="flex-1 px-3 py-2 bg-[#0A0E1A] border border-[#2A3444] rounded-lg text-white text-sm focus:border-cyan-500 focus:outline-none font-mono"
                placeholder={source.has_credentials ? source[`masked_${keyName}`] || '\u2022\u2022\u2022\u2022\u2022\u2022\u2022\u2022' : `Enter ${keyName}...`}
                disabled={saving} />
              {/* Show/Copy/Rotate icon buttons (mockup 09) */}
              <button onClick={() => setShowKeys({ ...showKeys, [keyName]: !showKeys[keyName] })}
                className="w-7 h-7 flex items-center justify-center bg-[#0A0E1A] border border-[#2A3444] rounded text-gray-500 hover:text-white text-[10px]"
                title="Show/Hide">{showKeys[keyName] ? '\u{1F441}' : '\u25CF'}</button>
              <button onClick={() => navigator.clipboard.writeText(keys[keyName] || '')}
                className="w-7 h-7 flex items-center justify-center bg-[#0A0E1A] border border-[#2A3444] rounded text-gray-500 hover:text-white text-[10px]"
                title="Copy">\u{1F4CB}</button>
              <button className="w-7 h-7 flex items-center justify-center bg-[#0A0E1A] border border-[#2A3444] rounded text-gray-500 hover:text-white text-[10px]"
                title="Rotate">\u21BB</button>
            </div>
          </div>
        ))}

        <div>
          <label className="text-xs text-gray-400 mb-1 block">Base URL</label>
          <input value={extraFields.base_url} onChange={(e) => setExtraFields({ ...extraFields, base_url: e.target.value })}
            className="w-full px-3 py-2 bg-[#0A0E1A] border border-[#2A3444] rounded-lg text-white text-sm focus:border-cyan-500 focus:outline-none font-mono" disabled={saving} />
        </div>
        <div>
          <label className="text-xs text-gray-400 mb-1 block">WebSocket URL</label>
          <input value={extraFields.ws_url} onChange={(e) => setExtraFields({ ...extraFields, ws_url: e.target.value })}
            className="w-full px-3 py-2 bg-[#0A0E1A] border border-[#2A3444] rounded-lg text-white text-sm focus:border-cyan-500 focus:outline-none font-mono" disabled={saving} />
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
              <option value="1s">1 second</option><option value="5s">5 seconds</option>
              <option value="30s">30 seconds</option><option value="1m">1 minute</option>
              <option value="5m">5 minutes</option><option value="15m">15 minutes</option>
            </select>
          </div>
        </div>
        <div>
          <label className="text-xs text-gray-400 mb-1 block">Account Type</label>
          <select value={extraFields.account_type} onChange={(e) => setExtraFields({ ...extraFields, account_type: e.target.value })}
            className="w-full px-3 py-2 bg-[#0A0E1A] border border-[#2A3444] rounded-lg text-white text-sm focus:border-cyan-500 focus:outline-none">
            <option value="">Select...</option><option value="paper">Paper Trading</option>
            <option value="live">Live Trading</option><option value="free">Free Tier</option>
            <option value="pro">Pro / Paid</option>
          </select>
        </div>

        {/* Connection Test Result box (mockup 09 green box) */}
        {testResult && testResult.ok && (
          <div className="bg-emerald-500/10 border border-emerald-500/20 rounded-lg p-3">
            <div className="text-emerald-400 text-xs font-bold">Connection Test Result</div>
            <div className="text-emerald-400 text-xs mt-1">\u2705 Connected in {testResult.latency}ms{testResult.detail ? ` - ${testResult.detail}` : ''}</div>
          </div>
        )}

        {/* Action buttons row (mockup 09: Test Connection, Save Changes, Cancel, Reset to Default) */}
        <div className="flex gap-2 pt-2 flex-wrap">
          <button onClick={handleTest} disabled={testing}
            className="px-3 py-2 bg-cyan-600/20 text-cyan-400 border border-cyan-500/30 rounded-lg hover:bg-cyan-600/30 text-xs font-medium disabled:opacity-50">
            {testing ? '\u23F3 Testing...' : 'Test Connection'}
          </button>
          <button onClick={() => onSave(keys)} disabled={saving}
            className="px-3 py-2 bg-emerald-600 text-white rounded-lg hover:bg-emerald-700 text-xs font-medium disabled:opacity-50">
            {saving ? '\u23F3 Saving...' : 'Save Changes'}
          </button>
          <button onClick={onClose} className="px-3 py-2 bg-gray-600/20 text-gray-400 rounded-lg hover:bg-gray-600/30 text-xs">Cancel</button>
          <button className="px-3 py-2 bg-gray-600/20 text-gray-400 rounded-lg hover:bg-gray-600/30 text-xs">Reset to Default</button>
        </div>

        {/* Connection Log (mockup 09 bottom of panel) */}
        {testLog.length > 0 && (
          <div className="mt-3">
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
        <h3 className="text-lg font-bold text-white mb-4">Add Custom Source</h3>
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
            {saving ? 'Adding...' : 'Add Source'}
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
        <h3 className="text-lg font-bold text-white mb-4">AI Detect Provider</h3>
        <input value={url} onChange={(e) => setUrl(e.target.value)} placeholder="Paste API URL..."
          className="w-full px-3 py-2 bg-[#0A0E1A] border border-[#2A3444] rounded-lg text-white text-sm mb-4 focus:border-cyan-500 focus:outline-none" disabled={detecting} />
        <button onClick={handleDetect} disabled={detecting} className="w-full px-4 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700 text-sm font-medium mb-4 disabled:opacity-50">
          {detecting ? 'Detecting...' : 'Detect'}
        </button>
        {error && <div className="p-3 bg-red-500/20 border border-red-500/30 rounded-lg text-red-400 text-sm mb-4">{error}</div>}
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
        <p className="text-gray-400 text-sm mb-4">Permanently delete <span className="text-white font-medium">"{sourceId}"</span>?</p>
        <div className="flex gap-2">
          <button onClick={onClose} className="flex-1 px-4 py-2 bg-gray-600/20 text-gray-400 rounded-lg hover:bg-gray-600/30 text-sm">Cancel</button>
          <button onClick={onConfirm} disabled={deleting} className="flex-1 px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 text-sm font-medium disabled:opacity-50">
            {deleting ? 'Deleting...' : 'Delete'}
          </button>
        </div>
      </div>
    </div>
  );
}
