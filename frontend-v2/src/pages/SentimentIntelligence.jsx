// SENTIMENT INTELLIGENCE - Multi-source sentiment fusion for trade conviction
// GET /api/v1/sentiment - combined sentiment scores across all sources

import { useState } from "react";
import {
  TrendingUp,
  TrendingDown,
  MessageCircle,
  MessageSquare,
  Newspaper,
  Radio,
  AlertCircle,
  ThumbsUp,
  ThumbsDown,
  Minus,
} from "lucide-react";
import PageHeader from "../components/ui/PageHeader";
import Card from "../components/ui/Card";
import Button from "../components/ui/Button";
import { useApi } from "../hooks/useApi";

export default function SentimentIntelligence() {
  const [timeRange, setTimeRange] = useState("24h");
  const { data, loading, error, refetch } = useApi("sentiment", {
    pollIntervalMs: 60000,
  });
  const sentimentData = Array.isArray(data?.items) ? data.items : [];

  const getSentimentColor = (score) => {
    if (score >= 70) return "text-emerald-400";
    if (score >= 55) return "text-cyan-400";
    if (score >= 45) return "text-gray-400";
    if (score >= 30) return "text-orange-400";
    return "text-red-400";
  };

  const getSentimentBg = (score) => {
    if (score >= 70) return "bg-emerald-500/10 border-emerald-500/30";
    if (score >= 55) return "bg-cyan-500/10 border-cyan-500/30";
    if (score >= 45) return "bg-gray-500/10 border-gray-500/30";
    if (score >= 30) return "bg-orange-500/10 border-orange-500/30";
    return "bg-red-500/10 border-red-500/30";
  };

  const getSentimentIcon = (trend) => {
    if (trend === "bullish")
      return <TrendingUp className="w-5 h-5 text-emerald-400" />;
    if (trend === "bearish")
      return <TrendingDown className="w-5 h-5 text-red-400" />;
    return <Minus className="w-5 h-5 text-gray-400" />;
  };

  return (
    <div className="space-y-6">
      <PageHeader
        icon={MessageCircle}
        title="Sentiment Intelligence"
        description={
          error
            ? "Failed to load sentiment"
            : "Multi-source sentiment fusion: Stockgeist + News + Discord + X"
        }
      >
        {error && (
          <span className="text-xs font-medium text-danger">
            Failed to load
          </span>
        )}
        <div className="flex gap-2">
          {["1h", "24h", "7d"].map((range) => (
            <button
              key={range}
              onClick={() => setTimeRange(range)}
              className={`px-3 py-1 text-xs rounded-lg transition-all ${
                timeRange === range
                  ? "bg-cyan-500/20 text-cyan-400"
                  : "text-gray-500 hover:text-gray-300"
              }`}
            >
              {range.toUpperCase()}
            </button>
          ))}
        </div>
      </PageHeader>

      {loading && sentimentData.length === 0 && (
        <div className="flex items-center justify-center py-16">
          <div className="text-center">
            <Radio className="w-8 h-8 text-cyan-400 animate-pulse mx-auto mb-2" />
            <p className="text-gray-400">Loading sentiment data...</p>
          </div>
        </div>
      )}
      {error && sentimentData.length === 0 && (
        <Card className="p-6 text-center">
          <p className="text-secondary mb-2">
            Could not load sentiment. Check GET /api/v1/sentiment.
          </p>
          <Button variant="outline" size="sm" onClick={refetch}>
            Retry
          </Button>
        </Card>
      )}
      {!loading && (!error || sentimentData.length > 0) && (
        <>
          {/* Stats strip */}
          {sentimentData.length > 0 && (
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
              <div className="rounded-xl border border-secondary/40 bg-gradient-to-br from-secondary/10 to-transparent p-4">
                <div className="text-xs font-medium uppercase tracking-wider text-secondary">
                  Sources
                </div>
                <div className="mt-1 text-2xl font-bold text-white">4</div>
              </div>
              <div className="rounded-xl border border-secondary/40 bg-gradient-to-br from-secondary/10 to-transparent p-4">
                <div className="text-xs font-medium uppercase tracking-wider text-secondary">
                  Signals
                </div>
                <div className="mt-1 text-2xl font-bold text-white">
                  {sentimentData.length}
                </div>
              </div>
            </div>
          )}

          {/* Source Status */}
          <Card title="Source Status" subtitle="Active feeds and weights">
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
              {[
                {
                  name: "Stockgeist",
                  icon: Radio,
                  status: "active",
                  weight: "30%",
                },
                {
                  name: "News API",
                  icon: Newspaper,
                  status: "active",
                  weight: "25%",
                },
                {
                  name: "Discord",
                  icon: MessageSquare,
                  status: "active",
                  weight: "25%",
                },
                {
                  name: "X (Twitter)",
                  icon: Radio,
                  status: "active",
                  weight: "20%",
                },
              ].map((source) => (
                <div
                  key={source.name}
                  className="rounded-xl border border-secondary/40 bg-secondary/10 p-4"
                >
                  <div className="flex items-center justify-between mb-2">
                    <source.icon className="w-5 h-5 text-cyan-400" />
                    <div className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
                  </div>
                  <div className="text-sm font-medium text-white">
                    {source.name}
                  </div>
                  <div className="text-xs text-secondary">
                    Weight: {source.weight}
                  </div>
                </div>
              ))}
            </div>
          </Card>

          {/* Sentiment Table */}
          {sentimentData.length === 0 ? (
            <Card className="p-12 text-center">
              <AlertCircle className="w-12 h-12 text-secondary mx-auto mb-4" />
              <p className="text-secondary">No sentiment data available</p>
            </Card>
          ) : (
            <Card title="Active Sentiment Signals">
              <div className="divide-y divide-secondary/30">
                {sentimentData.map((item) => (
                  <div
                    key={item.ticker}
                    className={`p-4 ${getSentimentBg(item.overallScore)}`}
                  >
                    <div className="flex items-center justify-between mb-4">
                      <div className="flex items-center gap-4">
                        <div>
                          <div className="text-xl font-bold text-white">
                            {item.ticker}
                          </div>
                          <div className="flex items-center gap-2 mt-1">
                            {getSentimentIcon(item.trend)}
                            <span className="text-xs text-gray-400 capitalize">
                              {item.trend}
                            </span>
                          </div>
                        </div>
                        <div>
                          <div
                            className={`text-3xl font-bold ${getSentimentColor(item.overallScore)}`}
                          >
                            {item.overallScore}
                          </div>
                          <div className="text-xs text-gray-500">
                            Composite Score
                          </div>
                        </div>
                      </div>
                      <div className="text-right">
                        <div
                          className={`text-sm font-bold ${
                            item.profitSignal?.includes("BUY")
                              ? "text-emerald-400"
                              : "text-red-400"
                          }`}
                        >
                          {item.profitSignal}
                        </div>
                        <div className="text-xs text-gray-500 capitalize">
                          {item.momentum}
                        </div>
                      </div>
                    </div>

                    {/* Source Breakdown */}
                    <div className="grid grid-cols-4 gap-3">
                      <div className="bg-gray-800/50 rounded-lg p-3">
                        <div className="flex items-center justify-between mb-2">
                          <Radio className="w-4 h-4 text-purple-400" />
                          <span
                            className={`text-xs font-bold ${
                              item.sources.stockgeist.change > 0
                                ? "text-emerald-400"
                                : "text-red-400"
                            }`}
                          >
                            {item.sources.stockgeist.change > 0 ? "+" : ""}
                            {item.sources.stockgeist.change}%
                          </span>
                        </div>
                        <div className="text-xs text-gray-500 mb-1">
                          Stockgeist
                        </div>
                        <div className="text-lg font-bold text-white">
                          {item.sources.stockgeist.score}
                        </div>
                        <div className="text-xs text-gray-600">
                          {item.sources.stockgeist.volume} mentions
                        </div>
                      </div>

                      <div className="bg-gray-800/50 rounded-lg p-3">
                        <div className="flex items-center justify-between mb-2">
                          <Newspaper className="w-4 h-4 text-blue-400" />
                          <span
                            className={`text-xs font-bold ${
                              item.sources.news.change > 0
                                ? "text-emerald-400"
                                : "text-red-400"
                            }`}
                          >
                            {item.sources.news.change > 0 ? "+" : ""}
                            {item.sources.news.change}%
                          </span>
                        </div>
                        <div className="text-xs text-gray-500 mb-1">News</div>
                        <div className="text-lg font-bold text-white">
                          {item.sources.news.score}
                        </div>
                        <div className="text-xs text-gray-600">
                          {item.sources.news.articles} articles
                        </div>
                      </div>

                      <div className="bg-gray-800/50 rounded-lg p-3">
                        <div className="flex items-center justify-between mb-2">
                          <MessageSquare className="w-4 h-4 text-indigo-400" />
                          <span
                            className={`text-xs font-bold ${
                              item.sources.discord.change > 0
                                ? "text-emerald-400"
                                : "text-red-400"
                            }`}
                          >
                            {item.sources.discord.change > 0 ? "+" : ""}
                            {item.sources.discord.change}%
                          </span>
                        </div>
                        <div className="text-xs text-gray-500 mb-1">
                          Discord
                        </div>
                        <div className="text-lg font-bold text-white">
                          {item.sources.discord.score}
                        </div>
                        <div className="text-xs text-gray-600">
                          {item.sources.discord.mentions} mentions
                        </div>
                      </div>

                      <div className="bg-gray-800/50 rounded-lg p-3">
                        <div className="flex items-center justify-between mb-2">
                          <Radio className="w-4 h-4 text-sky-400" />
                          <span
                            className={`text-xs font-bold ${
                              item.sources.x.change > 0
                                ? "text-emerald-400"
                                : "text-red-400"
                            }`}
                          >
                            {item.sources.x.change > 0 ? "+" : ""}
                            {item.sources.x.change}%
                          </span>
                        </div>
                        <div className="text-xs text-gray-500 mb-1">
                          X (Twitter)
                        </div>
                        <div className="text-lg font-bold text-white">
                          {item.sources.x.score}
                        </div>
                        <div className="text-xs text-gray-600">
                          {item.sources.x.posts} posts
                        </div>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </Card>
          )}
        </>
      )}
    </div>
  );
}
