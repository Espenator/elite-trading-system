import React from 'react';
import Sparkline from '../Common/Sparkline';
import './CandidateCard.css';

interface CandidateCardProps {
  candidate: any;
}

const CandidateCard: React.FC<CandidateCardProps> = ({ candidate }) => {
  // Generate sample sparkline data
  const sparklineData = Array.from({ length: 24 }, () => 
    Math.random() * 10 + 45
  );

  return (
    <div className="candidate-card">
      <div className="card-header">
        <span className="card-rank">#{candidate.rank || 1}</span>
        <span className="card-ticker">{candidate.ticker}</span>
        <span className={`card-change ${candidate.percentChange >= 0 ? 'positive' : 'negative'}`}>
          {candidate.percentChange >= 0 ? '+' : ''}{candidate.percentChange?.toFixed(2)}%
        </span>
        <span className={`tier-badge ${candidate.tier?.toLowerCase()}`}>
          {candidate.tier}
        </span>
      </div>

      <div className="sparkline-container">
        <Sparkline 
          data={sparklineData} 
          width={240} 
          height={28}
          color={candidate.percentChange >= 0 ? '#10b981' : '#ef4444'}
        />
      </div>

      <div className="card-metrics">
        <div className="metric-item">
          <span className="metric-label">Score</span>
          <span className="metric-value">{candidate.globalConfidence || 0}</span>
        </div>
        <div className="metric-item">
          <span className="metric-label">Conf</span>
          <span className="metric-value">{candidate.modelAgreement || 0}%</span>
        </div>
        <div className="metric-item">
          <span className="metric-label">Vol</span>
          <span className="metric-value">{(candidate.volume / 1000000).toFixed(1)}M</span>
        </div>
        <div className="metric-item">
          <span className="metric-label">RVOL</span>
          <span className="metric-value">{candidate.rvol?.toFixed(1)}x</span>
        </div>
      </div>
    </div>
  );
};

export default CandidateCard;
