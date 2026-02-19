// SENTIMENT INTELLIGENCE - Multi-source sentiment fusion for trade conviction
// PURPOSE: Aggregate sentiment from Stockgeist, News API, Discord, X (Twitter) to gauge market mood
// PROFIT FOCUS: Strong sentiment shifts = early alpha, helps confirm or reject trade signals
// BACKEND: /api/v1/sentiment - combined sentiment scores across all sources

import { useState, useEffect } from 'react';
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
  Minus
} from 'lucide-react';
import PageHeader from '../components/ui/PageHeader';

export default function SentimentIntelligence() {
  const [sentimentData, setSentimentData] = useState([]);
  const [loading, setLoading] = useState(true);
  const [timeRange, setTimeRange] = useState('24h');

  useEffect(() => {
    fetchSentiment();
    const interval = setInterval(fetchSentiment, 60000); // Refresh every 1min
    return () => clearInterval(interval);
  }, [timeRange]);

  const fetchSentiment = async () => {
    try {
      // TODO: Connect to real backend
      // const response = await fetch(`/api/v1/sentiment?timeRange=${timeRange}`);
      // const data = await response.json();
      
      // Mock data showing expected backend structure
      const mockData = [
        {
          ticker: 'NVDA',
          overallScore: 82, // 0-100, weighted composite
          trend: 'bullish',
          sources: {
            stockgeist: { score: 85, volume: 1250, change: +12 },
            news: { score: 78, articles: 45, change: +8 },
            discord: { score: 88, mentions: 320, change: +15 },
            x: { score: 80, posts: 890, change: +5 }
          },
          momentum: 'accelerating',
          profitSignal: 'STRONG BUY'
        }
      ];
      
      setSentimentData(mockData);
      setLoading(false);
    } catch (error) {
      console.error('Failed to fetch sentiment:', error);
      setLoading(false);
    }
  };

  const getSentimentColor = (score) => {
    if (score >= 70) return 'text-emerald-400';
    if (score >= 55) return 'text-cyan-400';
    if (score >= 45) return 'text-gray-400';
    if (score >= 30) return 'text-orange-400';
    return 'text-red-400';
  };

  const getSentimentBg = (score) => {
    if (score >= 70) return 'bg-emerald-500/10 border-emerald-500/30';
    if (score >= 55) return 'bg-cyan-500/10 border-cyan-500/30';
    if (score >= 45) return 'bg-gray-500/10 border-gray-500/30';
    if (score >= 30) return 'bg-orange-500/10 border-orange-500/30';
    return 'bg-red-500/10 border-red-500/30';
  };

  const getSentimentIcon = (trend) => {
    if (trend === 'bullish') return <TrendingUp className="w-5 h-5 text-emerald-400" />;
    if (trend === 'bearish') return <TrendingDown className="w-5 h-5 text-red-400" />;
    return <Minus className="w-5 h-5 text-gray-400" />;
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-96">
        <div className="text-center">
          <Radio className="w-8 h-8 text-cyan-400 animate-pulse mx-auto mb-2" />
          <p className="text-gray-400">Loading sentiment data...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <PageHeader
        icon={MessageCircle}
        title="Sentiment Intelligence"
        description="Multi-source sentiment fusion: Stockgeist + News + Discord + X"
      >
        <div className="flex gap-2">
          {['1h', '24h', '7d'].map(range => (
            <button
              key={range}
              onClick={() => setTimeRange(range)}
              className={`px-3 py-1 text-xs rounded-lg transition-all ${
                timeRange === range
                  ? 'bg-cyan-500/20 text-cyan-400'
                  : 'text-gray-500 hover:text-gray-300'
              }`}
            >
              {range.toUpperCase()}
            </button>
          ))}
        </div>
      </PageHeader>

      {/* Source Status */}
      <div className="grid grid-cols-4 gap-4">
        {[
          { name: 'Stockgeist', icon: Radio, status: 'active', weight: '30%' },
          { name: 'News API', icon: Newspaper, status: 'active', weight: '25%' },
          { name: 'Discord', icon: MessageSquare, status: 'active', weight: '25%' },
          { name: 'X (Twitter)', icon: Radio, status: 'active', weight: '20%' }
        ].map(source => (
          <div key={source.name} className="bg-gray-800/30 rounded-xl p-4 border border-gray-700/50">
            <div className="flex items-center justify-between mb-2">
              <source.icon className="w-5 h-5 text-cyan-400" />
              <div className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
            </div>
            <div className="text-sm font-medium text-white">{source.name}</div>
            <div className="text-xs text-gray-500">Weight: {source.weight}</div>
          </div>
        ))}
      </div>

      {/* Sentiment Table */}
      {sentimentData.length === 0 ? (
        <div className="bg-gray-800/30 rounded-xl p-12 text-center border border-gray-700/50">
          <AlertCircle className="w-12 h-12 text-gray-600 mx-auto mb-4" />
          <p className="text-gray-400">No sentiment data available</p>
        </div>
      ) : (
        <div className="bg-gray-800/30 rounded-xl border border-gray-700/50">
          <div className="p-4 border-b border-gray-700/50">
            <h2 className="text-lg font-semibold text-white">Active Sentiment Signals</h2>
          </div>
          <div className="divide-y divide-gray-700/30">
            {sentimentData.map(item => (
              <div key={item.ticker} className={`p-4 ${getSentimentBg(item.overallScore)}`}>
                <div className="flex items-center justify-between mb-4">
                  <div className="flex items-center gap-4">
                    <div>
                      <div className="text-xl font-bold text-white">{item.ticker}</div>
                      <div className="flex items-center gap-2 mt-1">
                        {getSentimentIcon(item.trend)}
                        <span className="text-xs text-gray-400 capitalize">{item.trend}</span>
                      </div>
                    </div>
                    <div>
                      <div className={`text-3xl font-bold ${getSentimentColor(item.overallScore)}`}>
                        {item.overallScore}
                      </div>
                      <div className="text-xs text-gray-500">Composite Score</div>
                    </div>
                  </div>
                  <div className="text-right">
                    <div className={`text-sm font-bold ${
                      item.profitSignal.includes('BUY') ? 'text-emerald-400' : 'text-red-400'
                    }`}>
                      {item.profitSignal}
                    </div>
                    <div className="text-xs text-gray-500 capitalize">{item.momentum}</div>
                  </div>
                </div>

                {/* Source Breakdown */}
                <div className="grid grid-cols-4 gap-3">
                  <div className="bg-gray-800/50 rounded-lg p-3">
                    <div className="flex items-center justify-between mb-2">
                      <Radio className="w-4 h-4 text-purple-400" />
                      <span className={`text-xs font-bold ${
                        item.sources.stockgeist.change > 0 ? 'text-emerald-400' : 'text-red-400'
                      }`}>
                        {item.sources.stockgeist.change > 0 ? '+' : ''}{item.sources.stockgeist.change}%
                      </span>
                    </div>
                    <div className="text-xs text-gray-500 mb-1">Stockgeist</div>
                    <div className="text-lg font-bold text-white">{item.sources.stockgeist.score}</div>
                    <div className="text-xs text-gray-600">{item.sources.stockgeist.volume} mentions</div>
                  </div>

                  <div className="bg-gray-800/50 rounded-lg p-3">
                    <div className="flex items-center justify-between mb-2">
                      <Newspaper className="w-4 h-4 text-blue-400" />
                      <span className={`text-xs font-bold ${
                        item.sources.news.change > 0 ? 'text-emerald-400' : 'text-red-400'
                      }`}>
                        {item.sources.news.change > 0 ? '+' : ''}{item.sources.news.change}%
                      </span>
                    </div>
                    <div className="text-xs text-gray-500 mb-1">News</div>
                    <div className="text-lg font-bold text-white">{item.sources.news.score}</div>
                    <div className="text-xs text-gray-600">{item.sources.news.articles} articles</div>
                  </div>

                  <div className="bg-gray-800/50 rounded-lg p-3">
                    <div className="flex items-center justify-between mb-2">
                      <MessageSquare className="w-4 h-4 text-indigo-400" />
                      <span className={`text-xs font-bold ${
                        item.sources.discord.change > 0 ? 'text-emerald-400' : 'text-red-400'
                      }`}>
                        {item.sources.discord.change > 0 ? '+' : ''}{item.sources.discord.change}%
                      </span>
                    </div>
                    <div className="text-xs text-gray-500 mb-1">Discord</div>
                    <div className="text-lg font-bold text-white">{item.sources.discord.score}</div>
                    <div className="text-xs text-gray-600">{item.sources.discord.mentions} mentions</div>
                  </div>

                  <div className="bg-gray-800/50 rounded-lg p-3">
                    <div className="flex items-center justify-between mb-2">
                      <Radio className="w-4 h-4 text-sky-400" />
                      <span className={`text-xs font-bold ${
                        item.sources.x.change > 0 ? 'text-emerald-400' : 'text-red-400'
                      }`}>
                        {item.sources.x.change > 0 ? '+' : ''}{item.sources.x.change}%
                      </span>
                    </div>
                    <div className="text-xs text-gray-500 mb-1">X (Twitter)</div>
                    <div className="text-lg font-bold text-white">{item.sources.x.score}</div>
                    <div className="text-xs text-gray-600">{item.sources.x.posts} posts</div>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
