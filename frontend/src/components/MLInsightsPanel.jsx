import React, { useState, useEffect } from 'react';
import { Brain, TrendingUp, Target, Zap, AlertCircle } from 'lucide-react';

/**
 * ML Insights Panel - Model Transparency Dashboard
 * Shows real-time ML model performance, feature importance, and predictions
 */

const MetricCard = ({ label, value, trend, icon }) => (
  <div className="bg-slate-800/30 p-3 rounded">
    <div className="flex items-center justify-between mb-1">
      <span className="text-xs text-gray-400">{label}</span>
      <span className="text-lg">{icon}</span>
    </div>
    <div className="text-2xl font-bold text-white">{value}</div>
    {trend && (
      <div className={`text-xs mt-1 ${
        trend > 0 ? 'text-green-400' : 'text-red-400'
      }`}>
        {trend > 0 ? '↑' : '↓'} {Math.abs(trend).toFixed(1)}%
      </div>
    )}
  </div>
);

export default function MLInsightsPanel() {
  const [modelStats, setModelStats] = useState(null);
  const [featureImportance, setFeatureImportance] = useState([]);
  const [driftAlert, setDriftAlert] = useState(false);
  const [recentPredictions, setRecentPredictions] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchStats = async () => {
      try {
        const stats = await fetch('http://localhost:8000/api/v1/ml/stats').then(r => r.json());
        setModelStats(stats);
        
        const features = await fetch('http://localhost:8000/api/v1/ml/feature-importance?top=10').then(r => r.json());
        setFeatureImportance(features);
        
        const predictions = await fetch('http://localhost:8000/api/v1/ml/predictions/recent?limit=10').then(r => r.json());
        setRecentPredictions(predictions);
        
        setDriftAlert(stats?.driftDetected || false);
        setLoading(false);
      } catch (error) {
        console.error('Failed to fetch ML stats:', error);
        setLoading(false);
      }
    };
    
    fetchStats();
    const interval = setInterval(fetchStats, 30000);
    return () => clearInterval(interval);
  }, []);

  const handleRetrain = async () => {
    try {
      await fetch('http://localhost:8000/api/v1/ml/retrain', { method: 'POST' });
      alert('Model retraining initiated');
      setDriftAlert(false);
    } catch (error) {
      alert('Failed to retrain model: ' + error.message);
    }
  };

  if (loading) {
    return <div className="p-6 bg-slate-900/50 rounded-lg">Loading ML insights...</div>;
  }

  return (
    <div className="p-6 bg-slate-900/50 rounded-lg border border-slate-700/50">
      <h3 className="font-bold text-xl mb-4 flex items-center gap-2">
        <Brain className="text-purple-400" size={24} />
        ML Model Insights
      </h3>
      
      {/* Performance Metrics */}
      <div className="grid grid-cols-4 gap-4 mb-6">
        <MetricCard 
          label="Accuracy" 
          value={`${((modelStats?.accuracy || 0) * 100).toFixed(1)}%`}
          trend={modelStats?.accuracyTrend}
          icon="🎯"
        />
        <MetricCard 
          label="Precision" 
          value={`${((modelStats?.precision || 0) * 100).toFixed(1)}%`}
          icon="🔍"
        />
        <MetricCard 
          label="F1 Score" 
          value={`${((modelStats?.f1 || 0) * 100).toFixed(1)}%`}
          icon="⚡"
        />
        <MetricCard 
          label="Samples" 
          value={(modelStats?.nSamples || 0).toLocaleString()}
          icon="📊"
        />
      </div>
      
      {/* Drift Alert */}
      {driftAlert && (
        <div className="mb-6 p-4 bg-red-500/20 border border-red-500/50 rounded">
          <div className="flex justify-between items-start">
            <div>
              <p className="text-red-400 font-bold">🚨 Model Drift Detected!</p>
              <p className="text-xs text-gray-300 mt-1">
                XGBoost accuracy diverged by 18% from River model
              </p>
            </div>
            <button 
              className="px-3 py-1 bg-teal-500 hover:bg-teal-600 rounded text-sm"
              onClick={handleRetrain}
            >
              Retrain Now
            </button>
          </div>
        </div>
      )}
      
      {/* Feature Importance */}
      <div className="mb-6">
        <h4 className="font-semibold mb-3">Top 10 Features Driving Predictions</h4>
        <div className="space-y-2">
          {featureImportance.map((feature, idx) => (
            <div key={idx} className="flex items-center gap-3">
              <span className="text-xs text-gray-400 w-8">{idx + 1}.</span>
              <div className="flex-1">
                <div className="flex justify-between items-center mb-1">
                  <span className="text-sm font-medium">{feature.name}</span>
                  <span className="text-xs text-teal-400">{(feature.importance * 100).toFixed(1)}%</span>
                </div>
                <div className="h-2 bg-slate-800 rounded overflow-hidden">
                  <div 
                    className="h-full bg-gradient-to-r from-teal-500 to-cyan-400"
                    style={{ width: `${feature.importance * 100}%` }}
                  />
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>
      
      {/* Recent Predictions */}
      <div>
        <h4 className="font-semibold mb-3">Last 10 Predictions</h4>
        <div className="space-y-1">
          {recentPredictions.map((pred, idx) => (
            <div 
              key={idx} 
              className={`flex items-center justify-between p-2 rounded text-xs ${
                pred.correct ? 'bg-green-500/20' : 'bg-red-500/20'
              }`}
            >
              <span className="font-mono">{pred.symbol}</span>
              <span>Predicted: {pred.predicted === 1 ? 'WIN' : 'LOSS'}</span>
              <span>Actual: {pred.actual === 1 ? 'WIN' : 'LOSS'}</span>
              <span className="text-gray-400">{pred.confidence}% confidence</span>
              <span className={pred.correct ? 'text-green-400' : 'text-red-400'}>
                {pred.correct ? '✓' : '✗'}
              </span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}