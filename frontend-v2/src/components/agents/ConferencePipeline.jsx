import React from 'react';
import { useConferenceStatus, useCouncilLatest } from '../../hooks/useApi';

/**
 * ConferencePipeline - Dual pipeline view:
 *  - Legacy 4-agent: Researcher → RiskOfficer → Adversary → Arbitrator
 *  - New 11-agent Council: Market → Flow → Regime → Social → News → YouTube → Hypothesis → Strategy → Risk → Execution → Critic → Arbiter
 *
 * Council panel shown when COUNCIL_ENABLED=true on backend and data available.
 * Falls back to legacy 4-agent pipeline when council data is not available.
 */

const COUNCIL_STAGES = [
  'Market', 'Flow', 'Regime', 'Hypothesis', 'Strategy', 'Risk', 'Execution', 'Critic',
];

function DirectionBadge({ direction, vetoed }) {
  if (vetoed) return <span style={{ color: '#ff4444', fontWeight: 'bold', fontSize: 14 }}>VETOED</span>;
  const color = direction === 'buy' ? '#00ff88' : direction === 'sell' ? '#ff4444' : '#ffaa00';
  return <span style={{ color, fontWeight: 'bold', fontSize: 14 }}>{(direction || 'N/A').toUpperCase()}</span>;
}

function ConfidenceBar({ value }) {
  const pct = Math.round((value || 0) * 100);
  const color = pct >= 70 ? '#00ff88' : pct >= 50 ? '#ffaa00' : '#ff4444';
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
      <div style={{ flex: 1, height: 6, borderRadius: 3, background: '#1a2332' }}>
        <div style={{ width: `${pct}%`, height: '100%', borderRadius: 3, background: color, transition: 'width 0.3s' }} />
      </div>
      <span style={{ color, fontSize: 11, fontFamily: 'monospace', minWidth: 32 }}>{pct}%</span>
    </div>
  );
}

export default function ConferencePipeline() {
  const { data: confData } = useConferenceStatus(15000);
  const { data: councilData } = useCouncilLatest(15000);

  const pipeline = confData?.pipeline || ['Researcher', 'RiskOfficer', 'Adversary', 'Arbitrator'];
  const currentStage = confData?.current_stage || 'idle';
  const last = confData?.last_conference || {};

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

  const hasCouncil = councilData && councilData.votes;

  return (
    <div style={{ display: 'grid', gridTemplateColumns: hasCouncil ? '1fr' : '1fr 1fr', gap: '1rem' }}>

      {/* 8-Agent Council (shown when available) */}
      {hasCouncil && (
        <div style={{ background: '#0d1117', borderRadius: 8, padding: '1rem', border: '1px solid #1a2332' }}>
          <h3 style={{ color: '#00d4ff', fontSize: 13, margin: '0 0 1rem', fontFamily: 'monospace' }}>
            INTELLIGENCE COUNCIL — {councilData.symbol || '?'}
          </h3>

          {/* Stage flow */}
          <div style={{ display: 'flex', alignItems: 'center', gap: 4, flexWrap: 'wrap', marginBottom: 12 }}>
            {COUNCIL_STAGES.map((stage, i) => {
              const vote = (councilData.votes || []).find(
                v => v.agent_name?.toLowerCase().includes(stage.toLowerCase())
              );
              const color = vote?.veto ? '#ff4444' : vote ? '#00ff88' : '#333';
              return (
                <React.Fragment key={stage}>
                  <div style={{
                    padding: '6px 8px', borderRadius: 4, fontSize: 10, fontFamily: 'monospace',
                    background: color === '#00ff88' ? 'rgba(0,255,136,0.08)' : color === '#ff4444' ? 'rgba(255,68,68,0.08)' : 'rgba(255,255,255,0.02)',
                    border: `1px solid ${color}`, color,
                  }}>
                    {stage}
                  </div>
                  {i < COUNCIL_STAGES.length - 1 && (
                    <span style={{ color: '#333', fontSize: 12 }}>→</span>
                  )}
                </React.Fragment>
              );
            })}
            <span style={{ color: '#333', fontSize: 12 }}>→</span>
            <div style={{
              padding: '6px 8px', borderRadius: 4, fontSize: 10, fontFamily: 'monospace',
              background: 'rgba(0,212,255,0.15)', border: '1px solid #00d4ff', color: '#00d4ff',
            }}>
              Arbiter
            </div>
          </div>

          {/* Council verdict */}
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr 1fr', gap: '0.75rem' }}>
            <div>
              <div style={{ color: '#8b949e', fontSize: 10, marginBottom: 4, fontFamily: 'monospace' }}>DIRECTION</div>
              <DirectionBadge direction={councilData.final_direction} vetoed={councilData.vetoed} />
            </div>
            <div>
              <div style={{ color: '#8b949e', fontSize: 10, marginBottom: 4, fontFamily: 'monospace' }}>CONFIDENCE</div>
              <ConfidenceBar value={councilData.final_confidence} />
            </div>
            <div>
              <div style={{ color: '#8b949e', fontSize: 10, marginBottom: 4, fontFamily: 'monospace' }}>VOTES</div>
              <span style={{ color: '#c9d1d9', fontSize: 12, fontFamily: 'monospace' }}>
                {(councilData.votes || []).length} agents
              </span>
            </div>
            <div>
              <div style={{ color: '#8b949e', fontSize: 10, marginBottom: 4, fontFamily: 'monospace' }}>EXEC READY</div>
              <span style={{
                color: councilData.execution_ready ? '#00ff88' : '#ff4444',
                fontSize: 12, fontFamily: 'monospace',
              }}>
                {councilData.execution_ready ? 'YES' : 'NO'}
              </span>
            </div>
          </div>

          {/* Veto reasons */}
          {councilData.vetoed && councilData.veto_reasons?.length > 0 && (
            <div style={{ marginTop: 8, padding: '6px 8px', borderRadius: 4, background: 'rgba(255,68,68,0.08)', border: '1px solid rgba(255,68,68,0.3)' }}>
              <span style={{ color: '#ff4444', fontSize: 10, fontFamily: 'monospace' }}>
                VETO: {councilData.veto_reasons.join(' | ')}
              </span>
            </div>
          )}
        </div>
      )}

      {/* Legacy 4-Agent Conference Pipeline (fallback when no council data) */}
      {!hasCouncil && (
        <>
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
              Total Conferences: {confData?.total_conferences || 0}
            </div>
          </div>

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
        </>
      )}
    </div>
  );
}
