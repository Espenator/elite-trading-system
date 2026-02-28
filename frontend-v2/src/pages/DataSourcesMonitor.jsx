import { useState, useEffect, useCallback } from 'react';
import dataSources from '../services/dataSourcesApi';

const STATUS_COLORS = {
  healthy:        { bg: 'bg-emerald-500/20', text: 'text-emerald-400', dot: 'bg-emerald-400' },
  active:         { bg: 'bg-emerald-500/20', text: 'text-emerald-400', dot: 'bg-emerald-400' },
  error:          { bg: 'bg-red-500/20',     text: 'text-red-400',     dot: 'bg-red-400' },
  timeout:        { bg: 'bg-orange-500/20',  text: 'text-orange-400',  dot: 'bg-orange-400' },
  degraded:       { bg: 'bg-yellow-500/20',  text: 'text-yellow-400',  dot: 'bg-yellow-400' },
  no_credentials: { bg: 'bg-gray-500/20',    text: 'text-gray-400',    dot: 'bg-gray-400' },
  unconfigured:   { bg: 'bg-gray-500/20',    text: 'text-gray-400',    dot: 'bg-gray-400' },
  offline:        { bg: 'bg-red-500/20',      text: 'text-red-400',     dot: 'bg-red-500' },
  beta:           { bg: 'bg-purple-500/20',  text: 'text-purple-400',  dot: 'bg-purple-400' },
  pending:        { bg: 'bg-slate-500/20',   text: 'text-slate-400',   dot: 'bg-slate-400' },
};

const CATEGORY_LABELS = {
  market: 'Market Data',
  options_flow: 'Options Flow',
  economic: 'Economic',
  filings: 'Filings',
  sentiment: 'Sentiment',
  news: 'News',
  social: 'Social',
  alerts: 'Alerts',
  bridge: 'Bridge',
  storage: 'Storage',
  custom: 'Custom',
};

const CATEGORY_ICONS = {
  market: '📈',
  options_flow: '🐋',
  economic: '🏛️',
  filings: '📋',
  sentiment: '🧠',
  news: '📰',
  social: '💬',
  alerts: '🔔',
  bridge: '🔗',
  storage: '💾',
  custom: '⚙️',
};

function StatusBadge({ status }) {
  const colors = STATUS_COLORS[status] || STATUS_COLORS.pending;
  return (
    <span className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium ${colors.bg} ${colors.text}`}>
      <span className={`w-1.5 h-1.5 rounded-full ${colors.dot} animate-pulse`} />
      {status}
    </span>
  );
}

function CredentialModal({ source, onClose, onSave }) {
  const [keys, setKeys] = useState({});
  useEffect(() => {
    const init = {};
    (source.required_keys || []).forEach((k) => { init[k] = ''; });
    setKeys(init);
  }, [source]);
  return (
    <div className="fixed inset-0 bg-black/60 backdrop-blur-sm flex items-center justify-center z-50">
      <div className="bg-[#1A1F2E] border border-[#2A3444] rounded-xl p-6 w-full max-w-md">
        <h3 className="text-lg font-semibold text-white mb-4">
          🔑 Credentials — {source.name}
        </h3>
        {(source.required_keys || []).map((keyName) => (
          <div key={keyName} className="mb-3">
            <label className="block text-sm text-gray-400 mb-1">{keyName}</label>
            <input
              type="password"
              value={keys[keyName] || ''}
              onChange={(e) => setKeys({ ...keys, [keyName]: e.target.value })}
              className="w-full px-3 py-2 bg-[#0A0E1A] border border-[#2A3444] rounded-lg text-white text-sm focus:border-cyan-500 focus:outline-none"
              placeholder={`Enter ${keyName}...`}
            />
          </div>
        ))}
        <div className="flex gap-3 mt-5">
          <button onClick={onClose} className="flex-1 px-4 py-2 bg-[#2A3444] text-gray-300 rounded-lg hover:bg-[#3A4454] text-sm">
            Cancel
          </button>
          <button onClick={() => onSave(keys)} className="flex-1 px-4 py-2 bg-cyan-600 text-white rounded-lg hover:bg-cyan-700 text-sm font-medium">
            Encrypt & Save
          </button>
        </div>
      </div>
    </div>
  );
}

function AddSourceModal({ onClose, onAdd }) {
  const [form, setForm] = useState({ id: '', name: '', base_url: '', test_endpoint: '', type: 'rest', category: 'custom' });
  return (
    <div className="fixed inset-0 bg-black/60 backdrop-blur-sm flex items-center justify-center z-50">
      <div className="bg-[#1A1F2E] border border-[#2A3444] rounded-xl p-6 w-full max-w-md">
        <h3 className="text-lg font-semibold text-white mb-4">➕ Add Custom Source</h3>
        {['id', 'name', 'base_url', 'test_endpoint'].map((field) => (
          <div key={field} className="mb-3">
            <label className="block text-sm text-gray-400 mb-1">{field}</label>
            <input
              value={form[field]}
              onChange={(e) => setForm({ ...form, [field]: e.target.value })}
              className="w-full px-3 py-2 bg-[#0A0E1A] border border-[#2A3444] rounded-lg text-white text-sm focus:border-cyan-500 focus:outline-none"
            />
          </div>
        ))}
        <div className="flex gap-3 mt-5">
          <button onClick={onClose} className="flex-1 px-4 py-2 bg-[#2A3444] text-gray-300 rounded-lg hover:bg-[#3A4454] text-sm">Cancel</button>
          <button onClick={() => onAdd(form)} className="flex-1 px-4 py-2 bg-cyan-600 text-white rounded-lg hover:bg-cyan-700 text-sm font-medium">Add Source</button>
        </div>
      </div>
    </div>
  );
}

function AIDetectModal({ onClose, onDetect }) {
  const [url, setUrl] = useState('');
  const [result, setResult] = useState(null);
  const handleDetect = async () => {
    const res = await onDetect(url);
    setResult(res);
  };
  return (
    <div className="fixed inset-0 bg-black/60 backdrop-blur-sm flex items-center justify-center z-50">
      <div className="bg-[#1A1F2E] border border-[#2A3444] rounded-xl p-6 w-full max-w-md">
        <h3 className="text-lg font-semibold text-white mb-4">🤖 AI Detect Provider</h3>
        <input
          value={url}
          onChange={(e) => setUrl(e.target.value)}
          placeholder="Paste API URL..."
          className="w-full px-3 py-2 bg-[#0A0E1A] border border-[#2A3444] rounded-lg text-white text-sm mb-4 focus:border-cyan-500 focus:outline-none"
        />
        <button onClick={handleDetect} className="w-full px-4 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700 text-sm font-medium mb-4">Detect</button>
        {result && (
          <div className="p-3 bg-[#0A0E1A] rounded-lg text-sm">
            <p className="text-cyan-400 font-medium">{result.detected_provider || 'Unknown'}</p>
            <p className="text-gray-400 mt-1">{result.suggestion}</p>
            {result.confidence > 0 && <p className="text-emerald-400 mt-1">Confidence: {(result.confidence * 100).toFixed(0)}%</p>}
          </div>
        )}
        <button onClick={onClose} className="w-full mt-3 px-4 py-2 bg-[#2A3444] text-gray-300 rounded-lg hover:bg-[#3A4454] text-sm">Close</button>
      </div>
    </div>
  );
}

export default function DataSourcesMonitor() {
    const [sources, setSources] = useState([]);
  const [loading, setLoading] = useState(true);
  const [testing, setTesting] = useState(null);

  const [addModal, setAddModal] = useState(false);
  const [detectModal, setDetectModal] = useState(false);
  const [filter, setFilter] = useState('all');

  const fetchSources = useCallback(async () => {
    try {
      const data = await dataSources.list();
      setSources(data);
    } catch (err) {
      console.error('Failed to fetch sources:', err);
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
    } finally {
      setTesting(null);
    }
  };

  const handleToggle = async (source) => {
    await dataSources.update(source.id, { enabled: !source.enabled });
    await fetchSources();
  };

  const handleSaveCreds = async (keys) => {
    await dataSources.setCredentials(credModal.id, keys);
    setCredModal(null);
    await fetchSources();
  };

  const handleAddSource = async (form) => {
    await dataSources.create(form);
    setAddModal(false);
    await fetchSources();
  };

  const handleDelete = async (sourceId) => {
    if (window.confirm(`Delete source "${sourceId}"?`)) {
      await dataSources.remove(sourceId);
      await fetchSources();
    }
  };

  const handleAIDetect = async (url) => {
    return await dataSources.aiDetect(url);
  };

  const handleTestAll = async () => {
    for (const src of sources.filter((s) => s.enabled)) {
      await handleTest(src.id);
    }
  };

  const categories = [...new Set(sources.map((s) => s.category))];
  const filtered = filter === 'all' ? sources : sources.filter((s) => s.category === filter);
  const healthyCount = sources.filter((s) => s.status === 'healthy').length;
  const errorCount = sources.filter((s) => ['error', 'timeout', 'offline'].includes(s.status)).length;

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-cyan-400" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
        <div>
          <h1 className="text-2xl font-bold text-white">Data Sources Manager</h1>
          <p className="text-gray-400 text-sm mt-1">
            {sources.length} sources configured · {healthyCount} healthy · {errorCount} errors
          </p>
        </div>
        <div className="flex gap-2">
          <button onClick={() => setDetectModal(true)} className="px-3 py-2 bg-purple-600/20 text-purple-400 border border-purple-500/30 rounded-lg hover:bg-purple-600/30 text-sm">
            🤖 AI Detect
          </button>
          <button onClick={() => setAddModal(true)} className="px-3 py-2 bg-cyan-600/20 text-cyan-400 border border-cyan-500/30 rounded-lg hover:bg-cyan-600/30 text-sm">
            ➕ Add Source
          </button>
          <button onClick={handleTestAll} className="px-3 py-2 bg-emerald-600/20 text-emerald-400 border border-emerald-500/30 rounded-lg hover:bg-emerald-600/30 text-sm">
            ⚡ Test All
          </button>
          <button onClick={fetchSources} className="px-3 py-2 bg-[#2A3444] text-gray-300 rounded-lg hover:bg-[#3A4454] text-sm">
            🔄 Refresh
          </button>
        </div>
      </div>

      {/* Category filter */}
      <div className="flex gap-2 flex-wrap">
        <button
          onClick={() => setFilter('all')}
          className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-colors ${filter === 'all' ? 'bg-cyan-600 text-white' : 'bg-[#1A1F2E] text-gray-400 hover:text-white'}`}
        >
          All ({sources.length})
        </button>
        {categories.map((cat) => (
          <button
            key={cat}
            onClick={() => setFilter(cat)}
            className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-colors ${filter === cat ? 'bg-cyan-600 text-white' : 'bg-[#1A1F2E] text-gray-400 hover:text-white'}`}
          >
            {CATEGORY_ICONS[cat] || '⚙️'} {CATEGORY_LABELS[cat] || cat} ({sources.filter((s) => s.category === cat).length})
          </button>
        ))}
      </div>

      {/* Sources grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
        {filtered.map((source) => (
          <div
            key={source.id}
            className={`bg-[#1A1F2E] border rounded-xl p-4 transition-all hover:border-cyan-500/50 ${source.enabled ? 'border-[#2A3444]' : 'border-[#2A3444]/50 opacity-60'}`}
          >
            {/* Card header */}
            <div className="flex items-start justify-between mb-3">
              <div className="flex items-center gap-2">
                <span className="text-lg">{CATEGORY_ICONS[source.category] || '⚙️'}</span>
                <div>
                  <h3 className="text-white font-medium text-sm">{source.name}</h3>
                  <p className="text-gray-500 text-xs">{source.type} · {source.category}</p>
                </div>
              </div>
              <StatusBadge status={source.status} />
            </div>

            {/* Metrics */}
            <div className="grid grid-cols-2 gap-2 mb-3 text-xs">
              <div className="bg-[#0A0E1A] rounded-lg p-2">
                <span className="text-gray-500">Latency</span>
                <p className="text-white font-mono">
                  {source.last_latency_ms != null ? `${source.last_latency_ms}ms` : '—'}
                </p>
              </div>
              <div className="bg-[#0A0E1A] rounded-lg p-2">
                <span className="text-gray-500">Last Test</span>
                <p className="text-white font-mono">
                  {source.last_test ? new Date(source.last_test).toLocaleTimeString() : '—'}
                </p>
              </div>
            </div>

            {/* Error */}
            {source.last_error && (
              <div className="bg-red-500/10 border border-red-500/20 rounded-lg p-2 mb-3">
                <p className="text-red-400 text-xs truncate">{source.last_error}</p>
              </div>
            )}

            {/* Actions */}
            <div className="flex items-center gap-2 pt-2 border-t border-[#2A3444]">
              <button
                onClick={() => handleTest(source.id)}
                disabled={testing === source.id}
                className="flex-1 px-2 py-1.5 bg-cyan-600/20 text-cyan-400 rounded-lg hover:bg-cyan-600/30 text-xs font-medium disabled:opacity-50"
              >
                {testing === source.id ? '⏳ Testing...' : '⚡ Test'}
              </button>
              <button
                onClick={() => setCredModal(source)}
                className="flex-1 px-2 py-1.5 bg-amber-600/20 text-amber-400 rounded-lg hover:bg-amber-600/30 text-xs font-medium"
              >
                {source.has_credentials ? '🔑 Update' : '🔑 Set'}
              </button>
              <button
                onClick={() => handleToggle(source)}
                className={`px-2 py-1.5 rounded-lg text-xs font-medium ${source.enabled ? 'bg-emerald-600/20 text-emerald-400 hover:bg-red-600/20 hover:text-red-400' : 'bg-gray-600/20 text-gray-400 hover:bg-emerald-600/20 hover:text-emerald-400'}`}
              >
                {source.enabled ? '✅' : '⛔'}
              </button>
              <button
                onClick={() => handleDelete(source.id)}
                className="px-2 py-1.5 bg-red-600/20 text-red-400 rounded-lg hover:bg-red-600/30 text-xs font-medium"
              >
                🗑️
              </button>
            </div>
          </div>
        ))}
      </div>

      {/* Modals */}
      {credModal && <CredentialModal source={credModal} onClose={() => setCredModal(null)} onSave={handleSaveCreds} />}
      {addModal && <AddSourceModal onClose={() => setAddModal(false)} onAdd={handleAddSource} />}
      {detectModal && <AIDetectModal onClose={() => setDetectModal(false)} onDetect={handleAIDetect} />}
    </div>
  );
}
