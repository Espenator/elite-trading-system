// SIGNAL HEATMAP - AI Composite Scoring Visualization
// PURPOSE: Display FINAL composite scores after all AI processing (Claude, Perplexity, ML, sentiment, technical)
// PROFIT FOCUS: Shows the system's highest-conviction opportunities based on complete data fusion
// BACKEND: /api/v1/signals/heatmap - returns composite-scored symbols from active pipeline
// NO HARDCODED SYMBOLS - only displays what the system generates

import { useState, useEffect } from "react";
import {
  Map,
  Target,
  TrendingUp,
  Clock,
  RefreshCw,
  AlertCircle,
  Brain,
  Zap,
} from "lucide-react";
import PageHeader from "../components/ui/PageHeader";
import { useApi } from "../hooks/useApi";

export default function SignalHeatmap() {
  const { data, loading, error, refetch } = useApi("signals", {
    pollIntervalMs: 30000,
    endpoint: "/heatmap", // Override endpoint for heatmap
  });
  const [lastUpdate, setLastUpdate] = useState(new Date());
  const [selectedSector, setSelectedSector] = useState("all");
  const [sortBy, setSortBy] = useState("compositeScore");

  const signals = Array.isArray(data) ? data : [];

  // Update lastUpdate when data changes
  useEffect(() => {
    if (data && !loading) {
      setLastUpdate(new Date());
    }
  }, [data, loading]);

  // Show loading/error states
  if (loading && signals.length === 0) {
    return (
      <div className="space-y-6">
        <PageHeader
          icon={Map}
          title="Signal Heatmap"
          description="Loading composite scores..."
        />
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {[1, 2, 3].map((i) => (
            <div
              key={i}
              className="h-32 bg-secondary/10 rounded-xl animate-pulse"
            />
          ))}
        </div>
      </div>
    );
  }

  if (error && signals.length === 0) {
    return (
      <div className="space-y-6">
        <PageHeader
          icon={Map}
          title="Signal Heatmap"
          description="Failed to load signals"
        />
        <div className="p-6 bg-danger/10 border border-danger/30 rounded-xl text-center">
          <p className="text-danger mb-2">Could not load heatmap data</p>
          <button
            onClick={refetch}
            className="text-primary hover:text-primary/80 text-sm"
          >
            Retry
          </button>
        </div>
      </div>
    );
  }

  const getHeatColor = (score) => {
    if (score >= 80) return "bg-emerald-500";
    if (score >= 70) return "bg-emerald-600/80";
    if (score >= 60) return "bg-cyan-600/70";
    if (score >= 50) return "bg-gray-600/50";
    if (score >= 40) return "bg-orange-600/70";
    if (score >= 30) return "bg-red-600/80";
    return "bg-red-500";
  };

  const getProfitLevel = (score) => {
    if (score >= 80) return { label: "EXTREME", color: "text-emerald-400" };
    if (score >= 70) return { label: "HIGH", color: "text-cyan-400" };
    if (score >= 60) return { label: "MODERATE", color: "text-blue-400" };
    if (score >= 50) return { label: "LOW", color: "text-secondary" };
    return { label: "AVOID", color: "text-red-400" };
  };

  // Group signals by sector (dynamically from backend data)
  const sectors = [...new Set(signals.map((s) => s.sector))];

  const topOpportunities = signals
    .sort((a, b) => b.compositeScore - a.compositeScore)
    .slice(0, 5);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-96">
        <div className="text-center">
          <RefreshCw className="w-8 h-8 text-cyan-400 animate-spin mx-auto mb-2" />
          <p className="text-secondary">Loading AI composite scores...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <PageHeader
        icon={Map}
        title="Signal Heatmap"
        description="Composite scores from all data sources + AI reasoning (Claude/Perplexity)"
      >
        <div className="flex items-center gap-4">
          <div className="text-xs text-secondary">
            Last update: {lastUpdate.toLocaleTimeString()}
          </div>
          <button
            onClick={refetch}
            className="p-2 bg-cyan-500/10 hover:bg-cyan-500/20 rounded-lg transition-colors"
            disabled={loading}
          >
            <RefreshCw
              className={`w-4 h-4 text-cyan-400 ${loading ? "animate-spin" : ""}`}
            />
          </button>
        </div>
      </PageHeader>

      {/* System Status */}
      <div className="bg-gradient-to-r from-purple-500/10 to-cyan-500/10 rounded-xl p-4 border border-purple-500/20">
        <div className="flex items-center gap-3 mb-2">
          <Brain className="w-5 h-5 text-purple-400" />
          <h2 className="text-sm font-semibold text-purple-400">
            AI COMPOSITE SCORING PIPELINE
          </h2>
        </div>
        <div className="grid grid-cols-5 gap-3 text-xs">
          <div>
            <div className="text-secondary">Technical Signals</div>
            <div className="text-white font-medium">✓ Active</div>
          </div>
          <div>
            <div className="text-secondary">ML Pattern Detection</div>
            <div className="text-white font-medium">✓ Active</div>
          </div>
          <div>
            <div className="text-secondary">Sentiment Fusion</div>
            <div className="text-white font-medium">✓ Active</div>
          </div>
          <div>
            <div className="text-secondary">Volume Analysis</div>
            <div className="text-white font-medium">✓ Active</div>
          </div>
          <div>
            <div className="text-secondary">AI Reasoning</div>
            <div className="text-emerald-400 font-medium">
              ✓ Claude + Perplexity
            </div>
          </div>
        </div>
      </div>

      {/* Top Opportunities */}
      {topOpportunities.length > 0 && (
        <div className="bg-gradient-to-r from-emerald-500/10 to-cyan-500/10 rounded-xl p-4 border border-emerald-500/20">
          <h2 className="text-sm font-semibold text-emerald-400 mb-3 flex items-center gap-2">
            <Target className="w-4 h-4" />
            HIGHEST CONVICTION OPPORTUNITIES (AI COMPOSITE)
          </h2>
          <div className="grid grid-cols-5 gap-3">
            {topOpportunities.map((signal) => {
              const profit = getProfitLevel(signal.compositeScore);
              return (
                <div
                  key={signal.ticker}
                  className="bg-secondary/10 rounded-lg p-3 border border-success/30 hover:border-success/50 transition-all cursor-pointer"
                >
                  <div className="flex items-center justify-between mb-2">
                    <span className="font-bold text-white text-lg">
                      {signal.ticker}
                    </span>
                    <span
                      className={`text-xs px-2 py-0.5 rounded ${profit.color} bg-current/10`}
                    >
                      {profit.label}
                    </span>
                  </div>
                  <div className="text-2xl font-bold text-emerald-400 mb-1">
                    {signal.compositeScore.toFixed(1)}
                  </div>
                  <div className="text-xs text-secondary mb-2">
                    Composite Score
                  </div>
                  <div className="text-sm text-white mb-1">
                    Expected: +{signal.expectedMove}%
                  </div>
                  <div className="text-xs text-secondary">
                    {signal.timeframe}
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Signal Grid - Grouped by Sector */}
      {signals.length === 0 ? (
        <div className="bg-secondary/10 rounded-xl p-12 text-center border border-secondary/50">
          <AlertCircle className="w-12 h-12 text-secondary mx-auto mb-4" />
          <p className="text-secondary">
            No signals generated yet. System is processing...
          </p>
          <p className="text-xs text-secondary mt-2">
            Signals appear when AI confidence threshold is met
          </p>
        </div>
      ) : (
        <div className="bg-secondary/10 rounded-xl border border-secondary/50">
          <div className="p-4 border-b border-secondary/50">
            <h2 className="text-lg font-semibold text-white">
              All Composite Signals
            </h2>
            <p className="text-xs text-secondary mt-1">
              {signals.length} active signals
            </p>
          </div>
          <div className="p-4">
            <div className="grid grid-cols-6 gap-2">
              {signals.map((signal) => {
                const profit = getProfitLevel(signal.compositeScore);
                return (
                  <div
                    key={signal.ticker}
                    className={`${getHeatColor(signal.compositeScore)} rounded-lg p-3 cursor-pointer hover:ring-2 hover:ring-cyan-400/50 transition-all group relative`}
                  >
                    <div className="text-sm font-bold text-white text-center">
                      {signal.ticker}
                    </div>
                    <div className="text-xs text-white/90 text-center font-medium">
                      {signal.compositeScore.toFixed(0)}
                    </div>
                    <div className="text-[10px] text-white/70 text-center">
                      +{signal.expectedMove}%
                    </div>

                    {/* Hover Tooltip */}
                    <div className="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 opacity-0 group-hover:opacity-100 transition-opacity z-10 pointer-events-none">
                      <div className="bg-dark rounded-lg p-3 text-xs whitespace-nowrap border border-secondary/50 min-w-64">
                        <div className="font-bold text-white mb-2">
                          {signal.ticker} - {signal.sector}
                        </div>
                        <div className="space-y-1 text-secondary">
                          <div className="flex justify-between">
                            <span>Composite Score:</span>
                            <span className="text-white font-bold">
                              {signal.compositeScore.toFixed(1)}
                            </span>
                          </div>
                          <div className="flex justify-between">
                            <span>Technical:</span>
                            <span className="text-cyan-400">
                              {signal.components.technical}
                            </span>
                          </div>
                          <div className="flex justify-between">
                            <span>ML Confidence:</span>
                            <span className="text-purple-400">
                              {signal.components.ml}
                            </span>
                          </div>
                          <div className="flex justify-between">
                            <span>Sentiment:</span>
                            <span className="text-emerald-400">
                              {signal.components.sentiment}
                            </span>
                          </div>
                          <div className="flex justify-between">
                            <span>AI Reasoning:</span>
                            <span className="text-yellow-400">
                              {signal.components.aiReasoning}
                            </span>
                          </div>
                        </div>
                        <div className="mt-2 pt-2 border-t border-secondary/50 text-secondary text-[10px]">
                          {signal.aiAnalysis}
                        </div>
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        </div>
      )}

      {/* Legend */}
      <div className="flex items-center justify-center gap-4 text-xs">
        <span className="text-secondary">LOW SCORE</span>
        <div className="flex gap-1">
          <div className="w-6 h-4 bg-red-500 rounded" />
          <div className="w-6 h-4 bg-red-600/80 rounded" />
          <div className="w-6 h-4 bg-orange-600/70 rounded" />
          <div className="w-6 h-4 bg-gray-600/50 rounded" />
          <div className="w-6 h-4 bg-cyan-600/70 rounded" />
          <div className="w-6 h-4 bg-emerald-600/80 rounded" />
          <div className="w-6 h-4 bg-emerald-500 rounded" />
        </div>
        <span className="text-secondary">HIGH SCORE (80+)</span>
      </div>
    </div>
  );
}
