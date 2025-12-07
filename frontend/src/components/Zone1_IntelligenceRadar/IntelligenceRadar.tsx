import React, { useState } from 'react';
import { LiveAnalysisHeader } from './LiveAnalysisHeader';
import { CandidateCard } from './CandidateCard';
import { useCandidateStream } from '../../hooks/useCandidateStream';
import './IntelligenceRadar.css';

export const IntelligenceRadar: React.FC = () => {
  const [isHeaderExpanded, setIsHeaderExpanded] = useState(false);
  const { candidates, progress, isAnalyzing } = useCandidateStream();

  const handleCandidateClick = (candidate: any) => {
    console.log('Selected candidate:', candidate);
    // TODO: Load full analysis in Zone 2 & Zone 3
  };

  return (
    <div className="intelligence-radar">
      <LiveAnalysisHeader
        progress={progress}
        isAnalyzing={isAnalyzing}
        isExpanded={isHeaderExpanded}
        onToggle={() => setIsHeaderExpanded(!isHeaderExpanded)}
      />

      <div className="candidates-list">
        {candidates.map((candidate, index) => (
          <CandidateCard
            key={candidate.id}
            candidate={candidate}
            rank={index + 1}
            onClick={handleCandidateClick}
            animationDelay={index * 100}
          />
        ))}

        {isAnalyzing && (
          <div className="analyzing-indicator">
            <div className="spinner" />
            <span>Analyzing more candidates...</span>
          </div>
        )}

        {!isAnalyzing && candidates.length === 0 && (
          <div className="empty-state">
            <p>No candidates yet. Waiting for signals...</p>
          </div>
        )}
      </div>
    </div>
  );
};
