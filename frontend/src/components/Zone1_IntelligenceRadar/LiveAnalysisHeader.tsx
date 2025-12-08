import React from 'react';
import './LiveAnalysisHeader.css';

interface LiveAnalysisHeaderProps {
  progress?: {
    current: number;
    total: number;
    tier3Passed: number;
    tier4Approved: number;
  };
}

const defaultProgress = {
  current: 0,
  total: 0,
  tier3Passed: 0,
  tier4Approved: 0
};

const LiveAnalysisHeader: React.FC<LiveAnalysisHeaderProps> = ({
  progress = defaultProgress
}) => {
  const { current, total, tier3Passed, tier4Approved } = progress;
  const progressPercent = total > 0 ? (current / total) * 100 : 0;

  return (
    <div className="live-analysis-header">
      <div className="header-title">
        <span className="icon">📡</span>
        <h2>LIVE MARKET INTELLIGENCE</h2>
        <span className="status-indicator">●</span>
      </div>
      
      <div className="analysis-progress">
        <div className="progress-stats">
          <div className="stat">
            <span className="label">Scanning:</span>
            <span className="value">{current}/{total}</span>
          </div>
          <div className="stat">
            <span className="label">Tier 3 Passed:</span>
            <span className="value tier3">{tier3Passed}</span>
          </div>
          <div className="stat">
            <span className="label">Tier 4 Approved:</span>
            <span className="value tier4">{tier4Approved}</span>
          </div>
        </div>
        
        <div className="progress-bar">
          <div className="progress-fill" style={{width: `${progressPercent}%`}}></div>
        </div>
      </div>
    </div>
  );
};

export default LiveAnalysisHeader;
