import React from 'react';
import { useDriftMetrics } from '../../hooks/useApi';

/**
 * DriftMonitor - Model drift detection with metric sparklines
 * Matches V3 mockup: Drift Monitor panel with PSI values and status indicators
 */
export default function DriftMonitor() {
  const { data } = useDriftMetrics(60000);
  const metrics = data?.metrics || [];
  const meanPsi = data?.mean_psi || 0;
  const driftDetected = data?.drift_detected || false;

  const psiColor = (val) => {
    if (val < 0.1) return '#00ff88';
    if (val < 0.2) return '#ffaa00';
    return '#ff4444';
  };

  return (
    <div style={{ background: '#0d1117', borderRadius: 8, padding: '1rem', border: '1px solid #1a2332' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
        <h3 style={{ color: '#00d4ff', fontSize: 13, margin: 0, fontFamily: 'monospace' }}>
          DRIFT MONITOR
        </h3>
        <div style={{
          padding: '2px 8px', borderRadius: 4, fontSize: 10, fontFamily: 'monospace',
          background: driftDetected ? 'rgba(255,68,68,0.15)' : 'rgba(0,255,136,0.1)',
          color: driftDetected ? '#ff4444' : '#00ff88',
          border: `1px solid ${driftDetected ? '#ff4444' : '#00ff88'}`,
        }}>
          {driftDetected ? 'DRIFT DETECTED' : 'STABLE'}
        </div>
      </div>

      <div style={{ marginBottom: 12, fontFamily: 'monospace', fontSize: 11 }}>
        <span style={{ color: '#8b949e' }}>Mean PSI: </span>
        <span style={{ color: psiColor(meanPsi), fontWeight: 'bold' }}>{meanPsi.toFixed(3)}</span>
      </div>

      <table style={{ width: '100%', fontSize: 11, fontFamily: 'monospace', borderCollapse: 'collapse' }}>
        <thead>
          <tr style={{ color: '#8b949e', borderBottom: '1px solid #1a2332' }}>
            <th style={{ textAlign: 'left', padding: 4 }}>Feature</th>
            <th style={{ textAlign: 'right', padding: 4 }}>PSI</th>
            <th style={{ textAlign: 'center', padding: 4 }}>Trend</th>
            <th style={{ textAlign: 'center', padding: 4 }}>Status</th>
          </tr>
        </thead>
        <tbody>
          {metrics.map((m) => (
            <tr key={m.name} style={{ borderBottom: '1px solid #0d1117' }}>
              <td style={{ padding: '3px 4px', color: '#c9d1d9' }}>{m.name}</td>
              <td style={{ padding: '3px 4px', textAlign: 'right', color: psiColor(m.value) }}>
                {m.value.toFixed(2)}
              </td>
              <td style={{ padding: '3px 4px', textAlign: 'center' }}>
                {/* Mini sparkline placeholder */}
                <svg width={40} height={12} viewBox="0 0 40 12">
                  <polyline points="0,8 8,6 16,9 24,4 32,7 40,5"
                    fill="none" stroke={psiColor(m.value)} strokeWidth={1} />
                </svg>
              </td>
              <td style={{ padding: '3px 4px', textAlign: 'center' }}>
                <span style={{
                  display: 'inline-block', width: 8, height: 8, borderRadius: '50%',
                  background: m.status === 'ok' ? '#00ff88' : m.status === 'warning' ? '#ffaa00' : '#ff4444',
                }} />
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}