import React from 'react';
import './CandidateCard.css';

interface Candidate {
  id?: string;
  ticker?: string;
  change?: number;
  tier?: 'Core' | 'Hot' | 'Liquid' | string;
  score?: number;
  confidence?: number;
  volume?: string;
  rvol?: number;
}

interface CandidateCardProps {
  candidate?: Candidate;
  isActive?: boolean;
}

const defaultCandidate: Candidate = {
  ticker: 'N/A',
  change: 0,
  tier: 'Core',
  score: 0,
  confidence: 0,
  volume: '0',
  rvol: 0,
};

const CandidateCard: React.FC<CandidateCardProps> = ({
  candidate = defaultCandidate,
  isActive = false,
}) => {
  const {
    ticker = 'N/A',
    change = 0,
    tier = 'Core',
    score = 0,
    confidence = 0,
    volume = '0',
    rvol = 0,
  } = candidate;

  const tierColors: Record<string, string> = {
    Core: '#10b981',
    Hot: '#fbbf24',
    Liquid: '#3b82f6',
  };

  const tierColor = tierColors[tier] ?? '#6b7280';
  const changeClass = change >= 0 ? 'positive' : 'negative';
  const changeSymbol = change >= 0 ? '+' : '';

  return (
    <div className={`candidate-card slide-in ${isActive ? 'active' : ''}`}>
      <div className="card-header">
        <span className="ticker ticker-symbol">{ticker}</span>
        <span className={`change price-medium ${changeClass}`}>
          {changeSymbol}{change.toFixed(2)}%
        </span>
        <span className="tier-badge" style={{ backgroundColor: tierColor }}>
          {tier}
        </span>
      </div>

      <div className="sparkline-row">
        <svg width={240} height={28} viewBox="0 0 240 28">
          <path
            d="M0,20 L60,15 L120,10 L180,5 L240,2"
            stroke={tierColor}
            strokeWidth={2}
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
