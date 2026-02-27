import React, { useMemo } from 'react';
import { useSwarmTopology } from '../../hooks/useApi';

/**
 * SwarmTopology - Agent network graph + ELO Leaderboard
 * Matches V3 mockup: Swarm Topology panel with force-directed graph and ELO rankings
 */
export default function SwarmTopology() {
  const { data, loading } = useSwarmTopology(30000);
  const nodes = data?.nodes || [];
  const leaderboard = data?.leaderboard || [];

  const statusColor = (status) => {
    switch (status) {
      case 'running': return '#00ff88';
      case 'stopped': return '#ff4444';
      case 'paused': return '#ffaa00';
      default: return '#666';
    }
  };

  const nodePositions = useMemo(() => {
    const cx = 200, cy = 150, r = 100;
    return nodes.map((n, i) => ({
      ...n,
      x: cx + r * Math.cos((2 * Math.PI * i) / Math.max(nodes.length, 1)),
      y: cy + r * Math.sin((2 * Math.PI * i) / Math.max(nodes.length, 1)),
    }));
  }, [nodes]);

  return (
    <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem' }}>
      {/* Network Graph */}
      <div style={{ background: '#0d1117', borderRadius: 8, padding: '1rem', border: '1px solid #1a2332' }}>
        <h3 style={{ color: '#00d4ff', fontSize: 13, margin: '0 0 0.5rem', fontFamily: 'monospace' }}>
          SWARM TOPOLOGY
        </h3>
        <svg viewBox="0 0 400 300" style={{ width: '100%', height: 250 }}>
          {/* Edges */}
          {(data?.edges || []).map((e, i) => {
            const src = nodePositions.find(n => n.id === e.source);
            const tgt = nodePositions.find(n => n.id === e.target);
            if (!src || !tgt) return null;
            return (
              <line key={i} x1={src.x} y1={src.y} x2={tgt.x} y2={tgt.y}
                stroke="#1a2332" strokeWidth={0.5} opacity={0.4} />
            );
          })}
          {/* Nodes */}
          {nodePositions.map((n) => (
            <g key={n.id}>
              <circle cx={n.x} cy={n.y} r={10} fill={statusColor(n.status)}
                opacity={0.8} style={{ cursor: 'pointer' }} />
              <text x={n.x} y={n.y + 20} textAnchor="middle"
                fill="#8b949e" fontSize={8} fontFamily="monospace">
                {n.name?.split('_')[0]}
              </text>
            </g>
          ))}
        </svg>
      </div>

      {/* ELO Leaderboard */}
      <div style={{ background: '#0d1117', borderRadius: 8, padding: '1rem', border: '1px solid #1a2332' }}>
        <h3 style={{ color: '#ffaa00', fontSize: 13, margin: '0 0 0.5rem', fontFamily: 'monospace' }}>
          ELO LEADERBOARD
        </h3>
        <table style={{ width: '100%', fontSize: 11, fontFamily: 'monospace', borderCollapse: 'collapse' }}>
          <thead>
            <tr style={{ color: '#8b949e', borderBottom: '1px solid #1a2332' }}>
              <th style={{ textAlign: 'left', padding: '4px' }}>#</th>
              <th style={{ textAlign: 'left', padding: '4px' }}>Agent</th>
              <th style={{ textAlign: 'right', padding: '4px' }}>ELO</th>
              <th style={{ textAlign: 'right', padding: '4px' }}>Win%</th>
            </tr>
          </thead>
          <tbody>
            {leaderboard.map((entry) => (
              <tr key={entry.rank} style={{ color: '#c9d1d9', borderBottom: '1px solid #0d1117' }}>
                <td style={{ padding: '3px 4px', color: entry.rank <= 3 ? '#ffaa00' : '#8b949e' }}>
                  {entry.rank}
                </td>
                <td style={{ padding: '3px 4px' }}>{entry.agent}</td>
                <td style={{ padding: '3px 4px', textAlign: 'right', color: '#00d4ff' }}>
                  {entry.elo}
                </td>
                <td style={{ padding: '3px 4px', textAlign: 'right',
                  color: entry.win_pct >= 60 ? '#00ff88' : entry.win_pct >= 40 ? '#ffaa00' : '#ff4444'
                }}>
                  {entry.win_pct}%
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        {loading && <div style={{ color: '#555', fontSize: 10, marginTop: 8 }}>Refreshing...</div>}
      </div>
    </div>
  );
}