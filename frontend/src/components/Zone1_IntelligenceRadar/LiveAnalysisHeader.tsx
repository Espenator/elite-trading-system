import React from 'react';

interface LiveAnalysisHeaderProps {
  progress: {
    current: number;
    total: number;
    tier3Passed: number;
    tier4Approved: number;
  };
  isAnalyzing: boolean;
  isExpanded: boolean;
  onToggle: () => void;
}

const LiveAnalysisHeader: React.FC<LiveAnalysisHeaderProps> = ({
  progress,
  isAnalyzing,
  isExpanded,
  onToggle,
}) => {
  const { current, total, tier4Approved } = progress;
  const percentComplete = total > 0 ? (current / total) * 100 : 0;

  return (
    <div className={`live-analysis-header ${isExpanded ? 'expanded' : 'collapsed'}`}>
      {!isExpanded && (
        <div className="header-collapsed">
          <div className="header-title">
            <span className="icon">??</span>
            <span className="title-text">LIVE AI ANALYSIS</span>
            {isAnalyzing && <div className="pulse-indicator" />}
          </div>

          <div className="progress-bar">
            <div className="progress-bar-fill" style={{ width: `${percentComplete}%` }} />
          </div>

          <div className="header-stats">
            <span className="stat">{tier4Approved} Approved</span>
            <span className="separator">•</span>
            <span className="stat-muted">{current}/{total}</span>
          </div>

          <button className="expand-button" onClick={onToggle}>?</button>
        </div>
      )}

      {isExpanded && (
        <div className="header-expanded">
          <div className="header-title-row">
            <span>AI VALIDATION FUNNEL</span>
            <button className="collapse-button" onClick={onToggle}>? Collapse</button>
          </div>
          <p style={{ fontSize: '12px', color: 'var(--color-text-secondary)', marginTop: '8px' }}>
            Detailed funnel visualization coming soon...
          </p>
        </div>
      )}
    </div>
  );
};

export default LiveAnalysisHeader;
