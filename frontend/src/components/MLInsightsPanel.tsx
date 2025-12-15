import React, { useState, useEffect, useCallback } from 'react';
import { Brain, TrendingUp, TrendingDown, RefreshCw, AlertTriangle, Activity, BarChart3, Loader2, CheckCircle, XCircle } from 'lucide-react';

interface ModelStats {
  accuracy: number;
  confidence: number;
  samples: number;
  last_retrain: string;
  drift_detected: boolean;
  model_version: string;
  predictions_today: number;
  correct_predictions: number;
}

interface FeatureImportance {
  name: string;
  importance: number;
  trend: 'up' | 'down' | 'stable';
  change: number;
}

interface PredictionRecord {
  timestamp: string;
  symbol: string;
  prediction: 'LONG' | 'SHORT';
  confidence: number;
  actual?: 'WIN' | 'LOSS' | 'PENDING';
}

const API_URL = 'http://localhost:8000/api/v1/ml';

export function MLInsightsPanel() {
  const [stats, setStats] = useState<ModelStats | null>(null);
  const [features, setFeatures] = useState<FeatureImportance[]>([]);
  const [predictions, setPredictions] = useState<PredictionRecord[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [activeTab, setActiveTab] = useState<'overview' | 'features' | 'history'>('overview');

  const fetchData = useCallback(async (showRefresh = false) => {
    if (showRefresh) setIsRefreshing(true);
    else setIsLoading(true);
    setError(null);

    try {
      const [statsRes, featuresRes, predictionsRes] = await Promise.all([
        fetch(API_URL + '/stats', { signal: AbortSignal.timeout(5000) }),
        fetch(API_URL + '/feature-importance', { signal: AbortSignal.timeout(5000) }),
        fetch(API_URL + '/predictions/history?limit=10', { signal: AbortSignal.timeout(5000) })
      ]);

      if (!statsRes.ok) throw new Error('Failed to fetch model stats');
      if (!featuresRes.ok) throw new Error('Failed to fetch feature importance');

      const statsData = await statsRes.json();
      const featuresData = await featuresRes.json();
      const predictionsData = predictionsRes.ok ? await predictionsRes.json() : [];

      setStats(statsData);
      setFeatures(featuresData);
      setPredictions(predictionsData);
      setLastUpdated(new Date());
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to fetch ML data';
      setError(message);
      console.error('[MLInsightsPanel] Error:', err);
    } finally {
      setIsLoading(false);
      setIsRefreshing(false);
    }
  }, []);

  useEffect(() => {
    fetchData();
    const interval = setInterval(() => fetchData(true), 30000);
    return () => clearInterval(interval);
  }, [fetchData]);

  const getAccuracyColor = (accuracy: number) => {
    if (accuracy >= 75) return 'text-green-400';
    if (accuracy >= 65) return 'text-yellow-400';
    return 'text-red-400';
  };

  const getConfidenceColor = (confidence: number) => {
    if (confidence >= 80) return 'text-cyan-400';
    if (confidence >= 70) return 'text-yellow-400';
    return 'text-orange-400';
  };

  const getTrendIcon = (trend: string) => {
    if (trend === 'up') return <TrendingUp size={12} className="text-green-400" />;
    if (trend === 'down') return <TrendingDown size={12} className="text-red-400" />;
    return <Activity size={12} className="text-slate-400" />;
  };

  const formatTime = (isoString: string) => {
    const date = new Date(isoString);
    return date.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' });
  };

  const formatLastRetrain = (isoString: string) => {
    const date = new Date(isoString);
    const hours = Math.floor((Date.now() - date.getTime()) / 3600000);
    if (hours < 1) return 'Less than 1 hour ago';
    if (hours < 24) return hours + ' hours ago';
    return Math.floor(hours / 24) + ' days ago';
  };

  if (isLoading && !stats) {
    return (
      <div className="bg-slate-900 rounded-lg border border-slate-700 p-4 h-full">
        <div className="flex items-center justify-center gap-3 py-8">
          <Loader2 size={24} className="text-cyan-400 animate-spin" />
          <span className="text-slate-400">Loading ML insights...</span>
        </div>
      </div>
    );
  }

  if (error && !stats) {
    return (
      <div className="bg-slate-900 rounded-lg border border-red-700 p-4 h-full">
        <div className="flex items-center gap-2 mb-4">
          <Brain size={20} className="text-red-400" />
          <h3 className="font-bold text-red-400">ML Insights Error</h3>
        </div>
        <p className="text-sm text-red-300 mb-4">{error}</p>
        <button onClick={() => fetchData()} className="px-3 py-1.5 bg-red-600 hover:bg-red-700 text-white rounded text-sm flex items-center gap-2">
          <RefreshCw size={14} />Retry
        </button>
      </div>
    );
  }

  return (
    <div className="bg-slate-900 rounded-lg border border-slate-700 flex flex-col h-full">
      <div className="p-3 border-b border-slate-700 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Brain size={20} className="text-cyan-400" />
          <h3 className="font-bold text-cyan-400">ML INSIGHTS</h3>
          {stats?.drift_detected && (
            <span className="px-2 py-0.5 bg-yellow-900/50 text-yellow-400 text-xs rounded flex items-center gap-1">
              <AlertTriangle size={12} />Drift
            </span>
          )}
        </div>
        <div className="flex items-center gap-2">
          <span className="text-xs text-slate-500">{stats?.model_version}</span>
          <button onClick={() => fetchData(true)} disabled={isRefreshing} className="p-1 hover:bg-slate-700 rounded">
            <RefreshCw size={14} className={'text-slate-400 ' + (isRefreshing ? 'animate-spin' : '')} />
          </button>
        </div>
      </div>

      <div className="flex border-b border-slate-700">
        {(['overview', 'features', 'history'] as const).map(tab => (
          <button key={tab} onClick={() => setActiveTab(tab)} className={'flex-1 px-3 py-2 text-xs font-medium transition ' + (activeTab === tab ? 'text-cyan-400 border-b-2 border-cyan-400 bg-slate-800/50' : 'text-slate-400 hover:text-slate-300')}>
            {tab.charAt(0).toUpperCase() + tab.slice(1)}
          </button>
        ))}
      </div>

      <div className="flex-1 overflow-y-auto p-3">
        {activeTab === 'overview' && stats && (
          <div className="space-y-3">
            <div className="grid grid-cols-2 gap-2">
              <div className="bg-slate-800 rounded p-3 border border-slate-700">
                <div className="text-xs text-slate-400 mb-1">Accuracy</div>
                <div className={'text-2xl font-bold ' + getAccuracyColor(stats.accuracy)}>{stats.accuracy.toFixed(1)}%</div>
                <div className="text-xs text-slate-500 mt-1">{stats.correct_predictions}/{stats.predictions_today} today</div>
              </div>
              <div className="bg-slate-800 rounded p-3 border border-slate-700">
                <div className="text-xs text-slate-400 mb-1">Confidence</div>
                <div className={'text-2xl font-bold ' + getConfidenceColor(stats.confidence)}>{stats.confidence}%</div>
                <div className="text-xs text-slate-500 mt-1">Current signal</div>
              </div>
            </div>
            <div className="bg-slate-800 rounded p-3 border border-slate-700">
              <div className="flex items-center justify-between mb-2">
                <span className="text-xs text-slate-400">Training Samples</span>
                <span className="text-sm font-bold text-slate-200">{stats.samples.toLocaleString()}</span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-xs text-slate-400">Last Retrain</span>
                <span className="text-sm text-slate-300">{formatLastRetrain(stats.last_retrain)}</span>
              </div>
            </div>
            {stats.drift_detected && (
              <div className="p-3 bg-yellow-900/20 border border-yellow-700 rounded">
                <div className="flex items-center gap-2 text-yellow-400 text-sm font-medium">
                  <AlertTriangle size={16} />Model Drift Detected
                </div>
                <p className="text-xs text-yellow-300 mt-1">Feature distributions have shifted. Consider retraining.</p>
              </div>
            )}
          </div>
        )}

        {activeTab === 'features' && (
          <div className="space-y-2">
            <div className="text-xs text-slate-400 mb-3 font-medium">Top Features by Importance</div>
            {features.map((feature, index) => (
              <div key={index} className="bg-slate-800 rounded p-2 border border-slate-700">
                <div className="flex items-center justify-between mb-1">
                  <div className="flex items-center gap-2">
                    <span className="text-xs text-slate-500 w-4">{index + 1}.</span>
                    <span className="text-sm text-slate-200 font-medium">{feature.name}</span>
                    {getTrendIcon(feature.trend)}
                  </div>
                  <span className="text-sm font-mono font-bold text-cyan-400">{feature.importance.toFixed(1)}%</span>
                </div>
                <div className="flex items-center gap-2">
                  <div className="flex-1 bg-slate-700 rounded h-1.5 overflow-hidden">
                    <div className="bg-cyan-500 h-full transition-all duration-500" style={{ width: (feature.importance * 5) + '%' }} />
                  </div>
                  <span className={'text-xs ' + (feature.change >= 0 ? 'text-green-400' : 'text-red-400')}>
                    {feature.change >= 0 ? '+' : ''}{feature.change.toFixed(1)}%
                  </span>
                </div>
              </div>
            ))}
          </div>
        )}

        {activeTab === 'history' && (
          <div className="space-y-2">
            <div className="text-xs text-slate-400 mb-3 font-medium">Recent Predictions</div>
            {predictions.length === 0 ? (
              <div className="text-center py-8 text-slate-500">
                <BarChart3 size={32} className="mx-auto mb-2 opacity-50" />
                <p className="text-sm">No predictions yet</p>
              </div>
            ) : (
              predictions.map((pred, index) => (
                <div key={index} className="bg-slate-800 rounded p-2 border border-slate-700 flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <span className={'px-2 py-0.5 rounded text-xs font-bold ' + (pred.prediction === 'LONG' ? 'bg-green-900/50 text-green-400' : 'bg-red-900/50 text-red-400')}>
                      {pred.prediction}
                    </span>
                    <span className="font-bold text-slate-200">{pred.symbol}</span>
                  </div>
                  <div className="flex items-center gap-3">
                    <span className="text-xs text-slate-400">{pred.confidence.toFixed(0)}%</span>
                    {pred.actual === 'WIN' && <CheckCircle size={14} className="text-green-400" />}
                    {pred.actual === 'LOSS' && <XCircle size={14} className="text-red-400" />}
                    {pred.actual === 'PENDING' && <Activity size={14} className="text-yellow-400" />}
                    <span className="text-xs text-slate-500">{formatTime(pred.timestamp)}</span>
                  </div>
                </div>
              ))
            )}
          </div>
        )}
      </div>

      {error && stats && (
        <div className="p-2 border-t border-yellow-700 bg-yellow-900/20 text-yellow-400 text-xs flex items-center gap-2">
          <AlertTriangle size={12} />Using cached data
        </div>
      )}
    </div>
  );
}
