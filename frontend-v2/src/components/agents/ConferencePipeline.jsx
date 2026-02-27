import React from 'react';
import { useConferenceStatus } from '../../hooks/useApi';

/**
 * ConferencePipeline - Shows Researcher → RiskOfficer → Adversary → Arbitrator pipeline
 * Matches V3 mockup: Conference Pipeline panel + Last Conference verdict
 */
export default function ConferencePipeline() {
  const { data } = useConferenceStatus(15000);
  const pipeline = data?.pipeline || ['Researcher', 'RiskOfficer', 'Adversary', 'Arbitrator'];
  const currentStage = data?.current_stage || 'idle';
  const last = data?.last_conference || {};

  const stageColor = (stage) => {
    if (currentStage === stage) return '#00d4ff';
    const idx = pipeline.indexOf(stage);
    const currentIdx = pipeline.indexOf(currentStage);
    if (currentIdx >= 0 && idx < currentIdx) return '#00ff88';
    return '#333';
  };

  const verdictColor = (v) => {
    if (!v || v === 'N/A') return '#666';
    return v.includes('BUY') || v.includes('LONG') ? '#00ff88' : 
           v.includes('SELL') || v.includes('SHORT') ? '#ff4444' : '#ffaa00';
  };

  return (
    <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem' }}>
      {/* Pipeline */}
      <div style={{ background: '#0d1117', borderRadius: 8, padding: '1rem', border: '1px solid #1a2332' }}>
        <h3 style={{ color: '#00d4ff', fontSize: 13, margin: '0 0 1rem', fontFamily: 'monospace' }}>
          CONFERENCE PIPELINE
        </h3>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          {pipeline.map((stage, i) => (
            <React.Fragment key={stage}>
              <div style={{
                padding: '8px 12px', borderRadius: 6, fontSize: 11, fontFamily: 'monospace',
                background: stageColor(stage) === '#00d4ff' ? 'rgba(0,212,255,0.15)' : 'rgba(255,255,255,0.03)',
                border: `1px solid ${stageColor(stage)}`, color: stageColor(stage),
                animation: currentStage === stage ? 'pulse 2s infinite' : 'none',
              }}>
                {stage}
              </div>
              {i < pipeline.length - 1 && (
                <span style={{ color: '#333', fontSize: 16 }}>→</span>
              )}
            </React.Fragment>
          ))}
        </div>
        <div style={{ marginTop: 12, fontSize: 10, color: '#555', fontFamily: 'monospace' }}>
          Total Conferences: {data?.total_conferences || 0}
        </div>
      </div>

      {/* Last Conference */}
      <div style={{ background: '#0d1117', borderRadius: 8, padding: '1rem', border: '1px solid #1a2332' }}>
        <h3 style={{ color: '#ffaa00', fontSize: 13, margin: '0 0 0.5rem', fontFamily: 'monospace' }}>
          LAST CONFERENCE
        </h3>
        <div style={{ fontFamily: 'monospace', fontSize: 12 }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 8 }}>
            <span style={{ color: '#8b949e' }}>Ticker</span>
            <span style={{ color: '#00d4ff', fontWeight: 'bold' }}>{last.ticker}</span>
          </div>
          <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 8 }}>
            <span style={{ color: '#8b949e' }}>Verdict</span>
            <span style={{ color: verdictColor(last.verdict), fontWeight: 'bold', fontSize: 14 }}>
              {last.verdict}
            </span>
          </div>
          <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 8 }}>
            <span style={{ color: '#8b949e' }}>Confidence</span>
            <span style={{ color: '#c9d1d9' }}>{last.confidence}%</span>
          </div>
          <div style={{ display: 'flex', justifyContent: 'space-between' }}>
            <span style={{ color: '#8b949e' }}>Duration</span>
            <span style={{ color: '#c9d1d9' }}>{last.duration}ms</span>
          </div>
        </div>
      </div>
    </div>
  );
}