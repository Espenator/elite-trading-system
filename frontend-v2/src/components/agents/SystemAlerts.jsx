import React from 'react';
import { useSystemAlerts } from '../../hooks/useApi';

/**
 * SystemAlerts - RED/AMBER/INFO alert feed
 * Matches V3 mockup: System Alerts panel with severity-colored alerts
 */
export default function SystemAlerts() {
  const { data } = useSystemAlerts(10000);
  const alerts = data?.alerts || [];

  const levelStyles = {
    RED: { color: '#ff4444', bg: 'rgba(255,68,68,0.08)', icon: '⚠' },
    AMBER: { color: '#ffaa00', bg: 'rgba(255,170,0,0.08)', icon: '⚠' },
    INFO: { color: '#00d4ff', bg: 'rgba(0,212,255,0.05)', icon: 'ℹ' },
  };

  return (
    <div style={{ background: '#0d1117', borderRadius: 8, padding: '1rem', border: '1px solid #1a2332' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
        <h3 style={{ color: '#ff4444', fontSize: 13, margin: 0, fontFamily: 'monospace' }}>
          SYSTEM ALERTS
        </h3>
        <span style={{ color: '#8b949e', fontSize: 10, fontFamily: 'monospace' }}>
          {alerts.length} active
        </span>
      </div>

      <div style={{ display: 'flex', flexDirection: 'column', gap: 6, maxHeight: 200, overflowY: 'auto' }}>
        {alerts.length === 0 && (
          <div style={{ color: '#00ff88', fontSize: 11, fontFamily: 'monospace', padding: 8, textAlign: 'center' }}>
            All systems nominal
          </div>
        )}
        {alerts.map((alert, i) => {
          const style = levelStyles[alert.level] || levelStyles.INFO;
          return (
            <div key={i} style={{
              display: 'flex', alignItems: 'center', gap: 8, padding: '6px 8px',
              background: style.bg, borderRadius: 4, borderLeft: `3px solid ${style.color}`,
            }}>
              <span style={{ fontSize: 12 }}>{style.icon}</span>
              <span style={{
                padding: '1px 6px', borderRadius: 3, fontSize: 9, fontWeight: 'bold',
                background: style.color, color: '#000', fontFamily: 'monospace',
              }}>
                {alert.level}
              </span>
              <span style={{ color: '#c9d1d9', fontSize: 11, fontFamily: 'monospace', flex: 1 }}>
                {alert.message}
              </span>
            </div>
          );
        })}
      </div>
    </div>
  );
}