import React from 'react';

// Mock: 10 data feeds per V2-EMBODIER-AI-README (Finviz, UW, Alpaca, FRED, SEC EDGAR, Stockgeist, News API, Discord, X, YouTube)
const MOCK_SOURCES = [
  { id: 1, name: 'Finviz', type: 'Screener', status: 'healthy', latencyMs: 120, lastSync: '2m ago', recordCount: 12450 },
  { id: 2, name: 'Unusual Whales (UW)', type: 'Options Flow', status: 'healthy', latencyMs: 85, lastSync: '1m ago', recordCount: 892 },
  { id: 3, name: 'Alpaca', type: 'Market Data', status: 'healthy', latencyMs: 45, lastSync: '30s ago', recordCount: 156000 },
  { id: 4, name: 'FRED', type: 'Macro', status: 'healthy', latencyMs: 320, lastSync: '1h ago', recordCount: 234 },
  { id: 5, name: 'SEC EDGAR', type: 'Filings', status: 'degraded', latencyMs: 2100, lastSync: '15m ago', recordCount: 89 },
  { id: 6, name: 'Stockgeist', type: 'Sentiment', status: 'healthy', latencyMs: 180, lastSync: '5m ago', recordCount: 4500 },
  { id: 7, name: 'News API', type: 'News', status: 'healthy', latencyMs: 95, lastSync: '1m ago', recordCount: 1203 },
  { id: 8, name: 'Discord', type: 'Social', status: 'healthy', latencyMs: 200, lastSync: '3m ago', recordCount: 567 },
  { id: 9, name: 'X (Twitter)', type: 'Social', status: 'error', latencyMs: null, lastSync: '—', recordCount: 0 },
  { id: 10, name: 'YouTube', type: 'Knowledge', status: 'healthy', latencyMs: 410, lastSync: '10m ago', recordCount: 42 },
];

const DataSourcesMonitor = () => {
  const getStatusStyle = (status) => {
    switch (status) {
      case 'healthy': return 'text-green-500 bg-green-900/20 border-green-700';
      case 'degraded': return 'text-yellow-500 bg-yellow-900/20 border-yellow-700';
      case 'error': return 'text-red-500 bg-red-900/20 border-red-700';
      default: return 'text-gray-500 bg-gray-900/20 border-gray-700';
    }
  };

  return (
    <div className="min-h-screen bg-gray-900 text-white p-6">
      <div className="mb-6">
        <h1 className="text-3xl font-bold">Data Sources Monitor</h1>
        <p className="text-gray-400 mt-1">Health of all 10 feeds with latency and record counts.</p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {MOCK_SOURCES.map((source) => (
          <div
            key={source.id}
            className={`rounded-lg p-5 border ${getStatusStyle(source.status)}`}
          >
            <div className="flex items-start justify-between mb-3">
              <div>
                <h3 className="text-lg font-bold">{source.name}</h3>
                <span className="text-xs text-gray-400">{source.type}</span>
              </div>
              <span className={`text-sm font-semibold capitalize px-2 py-1 rounded ${getStatusStyle(source.status)}`}>
                {source.status}
              </span>
            </div>
            <div className="grid grid-cols-2 gap-3 text-sm">
              <div>
                <span className="text-gray-400">Latency</span>
                <p className="font-mono">{source.latencyMs != null ? `${source.latencyMs} ms` : '—'}</p>
              </div>
              <div>
                <span className="text-gray-400">Last sync</span>
                <p>{source.lastSync}</p>
              </div>
              <div>
                <span className="text-gray-400">Records</span>
                <p className="font-mono">{source.recordCount.toLocaleString()}</p>
              </div>
            </div>
          </div>
        ))}
      </div>

      <div className="mt-8 bg-gray-800/50 rounded-lg p-6">
        <h2 className="text-xl font-bold mb-4">FRED Macro / SEC Placeholders</h2>
        <p className="text-gray-400 text-sm">Connect to GET /api/v1/data-sources, /data-sources/fred/regime, /data-sources/edgar/filings for live data.</p>
      </div>
    </div>
  );
};

export default DataSourcesMonitor;
