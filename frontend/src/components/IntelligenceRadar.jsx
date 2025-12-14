import { useState, useEffect } from 'react';
import { apiService } from '../services/api.service';

// Simple Trending icons (replacing lucide-react)
const TrendingUp = ({ className }) => (
  <svg className={className} fill="none" stroke="currentColor" viewBox="0 0 24 24">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 7h8m0 0v8m0-8l-8 8-4-4-6 6" />
  </svg>
);

const TrendingDown = ({ className }) => (
  <svg className={className} fill="none" stroke="currentColor" viewBox="0 0 24 24">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 17h8m0 0V9m0 8l-8-8-4 4-6-6" />
  </svg>
);

// Helper to format volume (e.g., 1500000 -> "1.5M")
const formatVolume = (vol) => {
  if (!vol) return 'N/A';
  if (vol >= 1e9) return (vol / 1e9).toFixed(1) + 'B';
  if (vol >= 1e6) return (vol / 1e6).toFixed(1) + 'M';
  if (vol >= 1e3) return (vol / 1e3).toFixed(1) + 'K';
  return vol.toString();
};

// Parse market cap string (e.g., "100B", "50M") to numeric value
const parseMarketCap = (marketCapStr) => {
  if (!marketCapStr) return 0;
  const match = marketCapStr.match(/^([\d.]+)([BMK]?)$/i);
  if (!match) return 0;
  const value = parseFloat(match[1]);
  const suffix = match[2].toUpperCase();
  if (suffix === 'B') return value * 1e9;
  if (suffix === 'M') return value * 1e6;
  if (suffix === 'K') return value * 1e3;
  return value;
};

// Assign tier based on market cap
const getTier = (marketCapStr) => {
  const marketCap = parseMarketCap(marketCapStr);
  if (marketCap >= 200e9) return 'Core';
  if (marketCap >= 10e9) return 'Hot';
  return 'Liquid';
};

export default function IntelligenceRadar({ onSelectSymbol }) {
  const [candidates, setCandidates] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [lastUpdated, setLastUpdated] = useState(null);

  useEffect(() => {
    const fetchStocks = async () => {
      try {
        setLoading(true);
        const data = await apiService.getStocks({ per_page: 20 });
        
        // Transform backend data to component format
        // Sort by change % descending to show top movers
        const sortedStocks = [...data.stocks].sort((a, b) => (b.change || 0) - (a.change || 0));
        
        const transformed = sortedStocks.map((stock, index) => ({
          rank: index + 1,
          ticker: stock.ticker,
          company: stock.company,
          price: stock.price || 0,
          change: stock.change || 0,
          tier: getTier(stock.market_cap),
          score: Math.round(50 + Math.abs(stock.change || 0) * 5 + (stock.pe_ratio ? 10 : 0)), // Score based on momentum
          confidence: Math.round(70 + Math.min(Math.abs(stock.change || 0) * 3, 25)), // Confidence based on price action
          volume: formatVolume(stock.volume),
          rvol: (1 + Math.abs(stock.change || 0) / 10).toFixed(1), // Simulated RVOL based on change
        }));
        
        setCandidates(transformed);
        setLastUpdated(new Date());
        setError(null);
      } catch (err) {
        setError(err.message);
      } finally {
        setLoading(false);
      }
    };

    fetchStocks();
  }, []);

  const getTimeAgo = () => {
    if (!lastUpdated) return 'Loading...';
    const seconds = Math.floor((new Date() - lastUpdated) / 1000);
    if (seconds < 60) return 'Just now';
    const minutes = Math.floor(seconds / 60);
    return `${minutes} min${minutes > 1 ? 's' : ''} ago`;
  };

  if (loading) {
    return (
      <div className="intelligence-radar flex items-center justify-center h-full">
        <div className="text-slate-400">Loading stocks...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="intelligence-radar flex items-center justify-center h-full">
        <div className="text-red-400">Error: {error}</div>
      </div>
    );
  }

  return (
    <div className="intelligence-radar">
      <div className="p-4 border-b border-slate-700">
        <h3 className="text-sm font-bold uppercase text-slate-400">Top Trade Candidates</h3>
        <p className="text-xs text-slate-500 mt-1">Updated {getTimeAgo()}</p>
      </div>

      <div className="overflow-y-auto h-full p-3 space-y-2">
        {candidates.map((candidate) => (
          <div
            key={candidate.ticker}
            onClick={() => onSelectSymbol(candidate.ticker)}
            className="candidate-card glass-card-hover cursor-pointer p-3 slide-in"
          >
            {/* Header Row */}
            <div className="flex items-start justify-between mb-2">
              <div className="flex items-center gap-2">
                <span className="text-xs text-slate-500 font-semibold">#{candidate.rank}</span>
                <span className="ticker cyan-glow-text">{candidate.ticker}</span>
              </div>
              <div className="flex items-center gap-1">
                <span className={`text-sm font-bold ${candidate.change >= 0 ? 'text-bull' : 'text-bear'}`}>
                  {candidate.change >= 0 ? '+' : ''}{candidate.change}%
                </span>
                {candidate.change >= 0 ? (
                  <TrendingUp className="w-3 h-3 text-bull" />
                ) : (
                  <TrendingDown className="w-3 h-3 text-bear" />
                )}
              </div>
            </div>

            {/* Price & Tier Badge */}
            <div className="flex items-center justify-between mb-2">
              <span className="text-lg font-bold text-mono">${candidate.price}</span>
              <span className={`tier-badge ${candidate.tier.toLowerCase()}`}>
                {candidate.tier}
              </span>
            </div>

            {/* Sparkline Placeholder */}
            <div className="h-7 bg-slate-900/50 rounded mb-2 flex items-center justify-center">
              <span className="text-xs text-slate-600">📈 Sparkline</span>
            </div>

            {/* Metrics Row */}
            <div className="grid grid-cols-2 gap-2 text-xs">
              <div>
                <span className="text-slate-500">Score:</span>
                <span className="ml-1 font-bold text-mono">{candidate.score}</span>
              </div>
              <div>
                <span className="text-slate-500">Conf:</span>
                <span className="ml-1 font-bold text-mono">{candidate.confidence}%</span>
              </div>
              <div>
                <span className="text-slate-500">Vol:</span>
                <span className="ml-1 text-mono">{candidate.volume}</span>
              </div>
              <div>
                <span className="text-slate-500">RVOL:</span>
                <span className="ml-1 font-bold text-mono">{candidate.rvol}x</span>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

