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
      {type === 'error' ? '❌' : '✅'} {message}
      <button onClick={onDismiss} className="ml-2 opacity-60 hover:opacity-100">✕</button>
    </div>
  );
}

function CredentialModal({ source, onClose, onSave, saving }) {
  const [keys, setKeys] = useState({});
  useEffect(() => {
    const init = {};
    (source.required_keys || []).forEach((k) => { init[k] = ''; });
    setKeys(init);
  }, [source]);
  return (
    <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50" onClick={onClose}>
      <div className="bg-[#1A1F2E] border border-[#2A3444] rounded-xl p-6 w-full max-w-md" onClick={(e) => e.stopPropagation()}>
        <h3 className="text-lg font-bold text-white mb-4">🔑 Credentials — {source.name}</h3>
        {(source.required_keys || []).map((keyName) => (
          <div key={keyName} className="mb-3">
            <label className="text-sm text-gray-400 mb-1 block">{keyName}</label>
            <input
              type="password"
              value={keys[keyName] || ''}
              onChange={(e) => setKeys({ ...keys, [keyName]: e.target.value })}
              className="w-full px-3 py-2 bg-[#0A0E1A] border border-[#2A3444] rounded-lg text-white text-sm focus:border-cyan-500 focus:outline-none"
              placeholder={`Enter ${keyName}...`}
              disabled={saving}
            />
          </div>
        ))}
        <div className="flex gap-2 mt-4">
          <button onClick={onClose} className="flex-1 px-4 py-2 bg-gray-600/20 text-gray-400 rounded-lg hover:bg-gray-600/30 text-sm">Cancel</button>
          <button onClick={() => onSave(keys)} disabled={saving} className="flex-1 px-4 py-2 bg-cyan-600 text-white rounded-lg hover:bg-cyan-700 text-sm font-medium disabled:opacity-50">
            {saving ? '⏳ Saving...' : 'Encrypt & Save'}
          </button>
        </div>
      </div>
    </div>
  );
}

function AddSourceModal({ onClose, onAdd, saving }) {
  const [form, setForm] = useState({ id: '', name: '', base_url: '', test_endpoint: '', type: 'rest', category: 'custom' });
  return (
    <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50" onClick={onClose}>
      <div className="bg-[#1A1F2E] border border-[#2A3444] rounded-xl p-6 w-full max-w-md" onClick={(e) => e.stopPropagation()}>
        <h3 className="text-lg font-bold text-white mb-4">➕ Add Custom Source</h3>
        {['id', 'name', 'base_url', 'test_endpoint'].map((field) => (
          <div key={field} className="mb-3">
            <label className="text-sm text-gray-400 mb-1 block">{field}</label>
            <input
              value={form[field]}
              onChange={(e) => setForm({ ...form, [field]: e.target.value })}
              className="w-full px-3 py-2 bg-[#0A0E1A] border border-[#2A3444] rounded-lg text-white text-sm focus:border-cyan-500 focus:outline-none"
              disabled={saving}
            />
          </div>
        ))}
        <div className="flex gap-2 mt-4">
          <button onClick={onClose} className="flex-1 px-4 py-2 bg-gray-600/20 text-gray-400 rounded-lg hover:bg-gray-600/30 text-sm">Cancel</button>
          <button onClick={() => onAdd(form)} disabled={saving} className="flex-1 px-4 py-2 bg-cyan-600 text-white rounded-lg hover:bg-cyan-700 text-sm font-medium disabled:opacity-50">
            {saving ? '⏳ Adding...' : 'Add Source'}
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
    setDetecting(true);
    setError(null);
    try {
      const res = await onDetect(url);
      setResult(res);
    } catch (err) {
      setError(err.message);
      setResult(null);
    } finally {
      setDetecting(false);
    }
  };
  return (
    <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50" onClick={onClose}>
      <div className="bg-[#1A1F2E] border border-[#2A3444] rounded-xl p-6 w-full max-w-md" onClick={(e) => e.stopPropagation()}>
        <h3 className="text-lg font-bold text-white mb-4">🤖 AI Detect Provider</h3>
        <input
          value={url}
          onChange={(e) => setUrl(e.target.value)}
          placeholder="Paste API URL..."
          className="w-full px-3 py-2 bg-[#0A0E1A] border border-[#2A3444] rounded-lg text-white text-sm mb-4 focus:border-cyan-500 focus:outline-none"
          disabled={detecting}
        />
        <button onClick={handleDetect} disabled={detecting} className="w-full px-4 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700 text-sm font-medium mb-4 disabled:opacity-50">
          {detecting ? '⏳ Detecting...' : 'Detect'}
        </button>
        {error && (
          <div className="p-3 bg-red-500/20 border border-red-500/30 rounded-lg text-red-400 text-sm mb-4">❌ {error}</div>
        )}
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
        <h3 className="text-lg font-bold text-white mb-4">🗑️ Delete Source</h3>
        <p className="text-gray-400 text-sm mb-4">Permanently delete <span className="text-white font-medium">"{sourceId}"</span>? This cannot be undone.</p>
        <div className="flex gap-2">
          <button onClick={onClose} className="flex-1 px-4 py-2 bg-gray-600/20 text-gray-400 rounded-lg hover:bg-gray-600/30 text-sm">Cancel</button>
          <button onClick={onConfirm} disabled={deleting} className="flex-1 px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 text-sm font-medium disabled:opacity-50">
            {deleting ? '⏳ Deleting...' : 'Delete'}
          </button>
        </div>
      </div>
    </div>
  );
}

export default function DataSourcesMonitor() {
  const [sources, setSources] = useState([]);
  const [loading, setLoading] = useState(true);
  const [testing, setTesting] = useState(null);
  const [testingAll, setTestingAll] = useState(false);
  const [testAllProgress, setTestAllProgress] = useState({ current: 0, total: 0 });
  const [actionLoading, setActionLoading] = useState(false);

  const [credModal, setCredModal] = useState(null);
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
      console.error(`Test failed for ${sourceId}:`, err);
      showToast(`Test failed for ${sourceId}: ${err.message}`, 'error');
      await fetchSources();
    } finally {
      setTesting(null);
    }
  };

  const handleToggle = async (source) => {
    try {
      await dataSources.update(source.id, { enabled: !source.enabled });
      await fetchSources();
      showToast(`${source.name} ${source.enabled ? 'disabled' : 'enabled'}`);
    } catch (err) {
      console.error('Toggle failed:', err);
      showToast(`Toggle failed: ${err.message}`, 'error');
    }
  };

  const handleSaveCreds = async (keys) => {
    setActionLoading(true);
    try {
      await dataSources.setCredentials(credModal.id, keys);
      setCredModal(null);
      await fetchSources();
      showToast('Credentials saved & encrypted');
    } catch (err) {
      console.error('Save credentials failed:', err);
      showToast(`Credential save failed: ${err.message}`, 'error');
    } finally {
      setActionLoading(false);
    }
  };

  const handleAddSource = async (form) => {
    setActionLoading(true);
    try {
      await dataSources.create(form);
      setAddModal(false);
      await fetchSources();
      showToast(`Source "${form.name}" added`);
    } catch (err) {
      console.error('Add source failed:', err);
      showToast(`Add source failed: ${err.message}`, 'error');
    } finally {
      setActionLoading(false);
    }
  };

  const handleDelete = async () => {
    if (!deleteModal) return;
    setActionLoading(true);
    try {
      await dataSources.remove(deleteModal);
      setDeleteModal(null);
      await fetchSources();
      showToast(`Source "${deleteModal}" deleted`);
    } catch (err) {
      console.error('Delete failed:', err);
      showToast(`Delete failed: ${err.message}`, 'error');
    } finally {
      setActionLoading(false);
    }
  };

  const handleAIDetect = async (url) => {
    return await dataSources.aiDetect(url);
  };

  const handleTestAll = async () => {
    const enabledSources = sources.filter((s) => s.enabled);
    setTestingAll(true);
    setTestAllProgress({ current: 0, total: enabledSources.length });
    try {
      for (let i = 0; i < enabledSources.length; i++) {
        setTestAllProgress({ current: i + 1, total: enabledSources.length });
        try {
          await dataSources.test(enabledSources[i].id);
        } catch (err) {
          console.error(`Test failed for ${enabledSources[i].id}:`, err);
        }
      }
      await fetchSources();
      showToast(`Tested ${enabledSources.length} sources`);
    } catch (err) {
      showToast(`Test All failed: ${err.message}`, 'error');
    } finally {
      setTestingAll(false);
      setTestAllProgress({ current: 0, total: 0 });
    }
  };

  const categories = [...new Set(sources.map((s) => s.category))];
  const filtered = filter === 'all' ? sources : sources.filter((s) => s.category === filter);
  const healthyCount = sources.filter((s) => s.status === 'healthy').length;
  const errorCount = sources.filter((s) => ['error', 'timeout', 'offline'].includes(s.status)).length;

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
    <div className="p-6 max-w-7xl mx-auto">
      <Toast message={toast.message} type={toast.type} onDismiss={() => setToast({ message: '', type: 'success' })} />

      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-white">Data Sources Manager</h1>
          <p className="text-sm text-gray-400 mt-1">{sources.length} sources configured &middot; {healthyCount} healthy &middot; {errorCount} errors</p>
        </div>
        <div className="flex gap-2">
          <button onClick={() => setDetectModal(true)} className="px-3 py-2 bg-purple-600/20 text-purple-400 border border-purple-500/30 rounded-lg hover:bg-purple-600/30 text-sm">
            🤖 AI Detect
          </button>
          <button onClick={() => setAddModal(true)} className="px-3 py-2 bg-cyan-600/20 text-cyan-400 border border-cyan-500/30 rounded-lg hover:bg-cyan-600/30 text-sm">
            ➕ Add Source
          </button>
          <button onClick={handleTestAll} disabled={testingAll} className="px-3 py-2 bg-amber-600/20 text-amber-400 border border-amber-500/30 rounded-lg hover:bg-amber-600/30 text-sm disabled:opacity-50">
            {testingAll ? `⏳ ${testAllProgress.current}/${testAllProgress.total}` : '⚡ Test All'}
          </button>
          <button onClick={fetchSources} className="px-3 py-2 bg-gray-600/20 text-gray-400 border border-gray-500/30 rounded-lg hover:bg-gray-600/30 text-sm">
            🔄 Refresh
          </button>
        </div>
      </div>

      {/* Category filter */}
      <div className="flex gap-2 mb-6 flex-wrap">
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
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
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
                  <h3 className="text-white font-semibold text-sm">{source.name}</h3>
                  <p className="text-gray-500 text-xs">{source.type} &middot; {source.category}</p>
                </div>
              </div>
              <StatusBadge status={source.status} />
            </div>

            {/* Metrics */}
            <div className="grid grid-cols-2 gap-2 mb-3">
              <div className="bg-[#0A0E1A] rounded-lg p-2">
                <div className="text-gray-500 text-xs">Latency</div>
                <div className="text-white text-sm font-mono">{source.last_latency_ms != null ? `${source.last_latency_ms}ms` : '—'}</div>
              </div>
              <div className="bg-[#0A0E1A] rounded-lg p-2">
                <div className="text-gray-500 text-xs">Last Test</div>
                <div className="text-white text-sm font-mono">{source.last_test ? new Date(source.last_test).toLocaleTimeString() : '—'}</div>
              </div>
            </div>

            {/* Error */}
            {source.last_error && (
              <div className="bg-red-500/10 border border-red-500/20 rounded-lg p-2 mb-3 text-red-400 text-xs truncate">{source.last_error}</div>
            )}

            {/* Actions */}
            <div className="flex gap-2">
              <button
                onClick={() => handleTest(source.id)}
                disabled={testing === source.id || testingAll}
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
                onClick={() => setDeleteModal(source.id)}
                className="px-2 py-1.5 bg-red-600/20 text-red-400 rounded-lg hover:bg-red-600/30 text-xs font-medium"
              >
                🗑️
              </button>
            </div>
          </div>
        ))}
      </div>

      {/* Modals */}
      {credModal && <CredentialModal source={credModal} onClose={() => setCredModal(null)} onSave={handleSaveCreds} saving={actionLoading} />}
      {addModal && <AddSourceModal onClose={() => setAddModal(false)} onAdd={handleAddSource} saving={actionLoading} />}
      {detectModal && <AIDetectModal onClose={() => setDetectModal(false)} onDetect={handleAIDetect} />}
      {deleteModal && <DeleteConfirmModal sourceId={deleteModal} onClose={() => setDeleteModal(null)} onConfirm={handleDelete} deleting={actionLoading} />}
    </div>
  );
}
