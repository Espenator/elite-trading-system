import React from 'react';
import './CandidateCard.css';

interface CandidateCardProps {
  rank: number;
  ticker: string;
  change: number;
  tier: 'Core' | 'Hot' | 'Liquid';
  score: number;
  confidence: number;
  volume: string;
  rvol: number;
  onClick?: () => void;
}

const CandidateCard: React.FC<CandidateCardProps> = ({
  rank,
  ticker,
  change,
  tier,
  score,
  confidence,
  volume,
  rvol,
  onClick
}) => {
  const tierColors = {
    Core: '#10b981',
    Hot: '#fbbf24',
    Liquid: '#3b82f6'
  };

  return (
    <div className="candidate-card slide-in" onClick={onClick}>
      <div className="card-header">
        <span className="rank label-text">#{rank}</span>
        <span className="ticker ticker-symbol">{ticker}</span>
        <span className={`change price-medium ${change >= 0 ? 'positive' : 'negative'}`}>
          {change >= 0 ? '+' : ''}{change.toFixed(2)}%
        </span>
        <span 
          className="tier-badge" 
          style={{ backgroundColor: tierColors[tier] }}
        >
          {tier}
        </span>
      </div>

      <div className="sparkline-row">
        {/* SVG sparkline would go here */}
        <svg width="240" height="28" viewBox="0 0 240 28">
          <path 
            d="M0,20 L60,15 L120,10 L180,5 L240,2"
            stroke={tierColors[tier]}
            strokeWidth="2"
            fill="none"
          />
        </svg>
      </div>

      <div className="metrics-row">
        <div className="metric-item">
          <span className="label-text">Score</span>
          <span className="body-text">{score.toFixed(1)}</span>
        </div>
        <div className="metric-item">
          <span className="label-text">Conf</span>
          <span className="body-text">{confidence}%</span>
        </div>
      </div>

      <div className="metrics-row">
        <div className="metric-item">
          <span className="label-text">Vol</span>
          <span className="metadata">{volume}</span>
        </div>
        <div className="metric-item">
          <span className="label-text">RVOL</span>
          <span className="metadata">{rvol.toFixed(1)}x</span>
        </div>
      </div>
    </div>
  );
};

export default CandidateCard;
