import React from 'react';
import Card from '../components/ui/Card';
import Badge from '../components/ui/Badge';

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
  const getStatusVariant = (status) => {
    switch (status) {
      case 'healthy': return 'success';
      case 'degraded': return 'warning';
      case 'error': return 'danger';
      default: return 'secondary';
    }
  };

  const getCardBorder = (status) => {
    switch (status) {
      case 'healthy': return 'border-success/50';
      case 'degraded': return 'border-warning/50';
      case 'error': return 'border-danger/50';
      default: return 'border-secondary/50';
    }
  };

  return (
    <div className="min-h-screen bg-dark text-white p-6">
      <div className="mb-6">
        <h1 className="text-3xl font-bold text-white">Data Sources Monitor</h1>
        <p className="text-secondary mt-1">Health of all 10 feeds with latency and record counts.</p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {MOCK_SOURCES.map((source) => (
          <Card key={source.id} className={`p-5 border-2 ${getCardBorder(source.status)}`} noPadding>
            <div className="p-5">
              <div className="flex items-start justify-between mb-3">
                <div>
                  <h3 className="text-lg font-bold text-white">{source.name}</h3>
                  <span className="text-xs text-secondary">{source.type}</span>
                </div>
                <Badge variant={getStatusVariant(source.status)}>{source.status}</Badge>
              </div>
              <div className="grid grid-cols-2 gap-3 text-sm">
                <div>
                  <span className="text-secondary">Latency</span>
                  <p className="text-white">{source.latencyMs != null ? `${source.latencyMs} ms` : '—'}</p>
                </div>
                <div>
                  <span className="text-secondary">Last sync</span>
                  <p className="text-white">{source.lastSync}</p>
                </div>
                <div>
                  <span className="text-secondary">Records</span>
                  <p className="text-white">{source.recordCount.toLocaleString()}</p>
                </div>
              </div>
            </div>
          </Card>
        ))}
      </div>

      <Card title="FRED Macro / SEC Placeholders" className="mt-8">
        <p className="text-secondary text-sm">Connect to GET /api/v1/data-sources, /data-sources/fred/regime, /data-sources/edgar/filings for live data.</p>
      </Card>
    </div>
  );
};

export default DataSourcesMonitor;
