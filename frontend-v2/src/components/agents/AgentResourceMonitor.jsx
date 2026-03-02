import React from 'react';
import { useAgentResources } from '../../hooks/useApi';

/**
 * AgentResourceMonitor - Per-agent CPU, MEM, Tokens/hr metrics
 * Matches V3 mockup: Agent Resource Monitor table with bar charts
 */
export default function AgentResourceMonitor() {
  const { data } = useAgentResources(15000);
  const resources = data?.resources || [];

  const barStyle = (pct, color) => ({
    width: `${Math.min(pct, 100)}%`, height: 6, borderRadius: 3,
    background: color, transition: 'width 0.3s ease',
  });

  return (
    <div style={{ background: '#0d1117', borderRadius: 8, padding: '1rem', border: '1px solid #1a2332' }}>
      <h3 style={{ color: '#00d4ff', fontSize: 13, margin: '0 0 0.5rem', fontFamily: 'monospace' }}>
        AGENT RESOURCE MONITOR
      </h3>
      <table style={{ width: '100%', fontSize: 10, fontFamily: 'monospace', borderCollapse: 'collapse' }}>
        <thead>
          <tr style={{ color: '#8b949e', borderBottom: '1px solid #1a2332' }}>
            <th style={{ textAlign: 'left', padding: 4 }}>Agent</th>
            <th style={{ textAlign: 'left', padding: 4, width: 120 }}>CPU</th>
            <th style={{ textAlign: 'right', padding: 4 }}>MEM</th>
            <th style={{ textAlign: 'right', padding: 4 }}>Tok/hr</th>
          </tr>
        </thead>
        <tbody>
          {resources.map((r) => (
            <tr key={r.agent} style={{ borderBottom: '1px solid rgba(255,255,255,0.03)' }}>
              <td style={{ padding: '4px', color: r.status === 'running' ? '#c9d1d9' : '#555' }}>
                {r.agent}
              </td>
              <td style={{ padding: '4px' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                  <div style={{ flex: 1, height: 6, background: '#1a2332', borderRadius: 3 }}>
                    <div style={barStyle(r.cpu_pct, r.cpu_pct > 80 ? '#ff4444' : r.cpu_pct > 50 ? '#ffaa00' : '#00ff88')} />
                  </div>
                  <span style={{ color: '#8b949e', minWidth: 28, textAlign: 'right' }}>{r.cpu_pct}%</span>
                </div>
              </td>
              <td style={{ padding: '4px', textAlign: 'right', color: '#c9d1d9' }}>
                {r.mem_mb}MB
              </td>
              <td style={{ padding: '4px', textAlign: 'right', color: '#00d4ff' }}>
                {(r.tokens_hr / 1000).toFixed(1)}k
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}