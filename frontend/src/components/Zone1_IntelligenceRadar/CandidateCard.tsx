import React, { useState, useRef, useEffect } from 'react';
import { Candidate } from '../../types/candidate';

interface CandidateCardProps {
  candidate: Candidate;
  rank: number;
  onClick: (candidate: Candidate) => void;
  animationDelay?: number;
}

export const CandidateCard: React.FC<CandidateCardProps> = ({
  candidate,
  rank,
  onClick,
  animationDelay = 0,
}) => {
  const [isHovered, setIsHovered] = useState(false);
  const cardRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (cardRef.current) {
      cardRef.current.style.animationDelay = `${animationDelay}ms`;
    }
  }, [animationDelay]);

  const getTierEmoji = (tier: string) => {
    switch (tier) {
      case 'Core': return '🟢';
      case 'Hot': return '🟡';
      case 'Liquid': return '🔵';
      default: return '⚪';
    }
  };

  return (
    <div
      ref={cardRef}
      className={`candidate-card fade-in-up ${isHovered ? 'hovered' : ''}`}
      onClick={() => onClick(candidate)}
      onMouseEnter={() => setIsHovered(true)}
      onMouseLeave={() => setIsHovered(false)}
    >
      <div className="card-header">
        <span className="rank">#{rank}</span>
        <span className="ticker">{candidate.ticker}</span>
        <span className="price">${candidate.price.toFixed(2)}</span>
        <span className={`change ${candidate.change >= 0 ? 'positive' : 'negative'}`}>
          {candidate.change >= 0 ? '+' : ''}{candidate.change.toFixed(2)}%
        </span>
        <span className="tier-badge">{getTierEmoji(candidate.tier)}</span>
      </div>

      <div className="card-footer">
        <span className="metric">Score: {candidate.score.toFixed(1)}</span>
        <span className="separator">•</span>
        <span className="metric">AI: {candidate.aiConfidence}%</span>
        <span className="separator">•</span>
        <span className="metric">{candidate.rvol.toFixed(1)}x</span>
      </div>

      {isHovered && (
        <div className="hover-hint">Click for full analysis</div>
      )}
    </div>
  );
};
