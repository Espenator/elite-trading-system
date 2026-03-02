import React, { useEffect, useState, useCallback } from 'react';

// ———————————————————————————————————————————————————————————————————
// COLORS — shared dark theme palette
// ———————————————————————————————————————————————————————————————————
const COLORS = {
  bg: '#0a0e17',
  card: '#0d1320',
  cardBorder: '#1a2335',
  text: '#e2e8f0',
  textDim: '#8892a4',
  textMuted: '#4a5568',
  cyan: '#00d4aa',
  cyanDark: '#00b894',
  green: '#00e676',
  greenDim: 'rgba(0, 230, 118, 0.15)',
  red: '#ff5252',
  redDim: 'rgba(255, 82, 82, 0.15)',
  yellow: '#ffd600',
  yellowDim: 'rgba(255, 214, 0, 0.15)',
  blue: '#448aff',
  orange: '#ff9100',
  highlight: '#1a2a40',
};

// ———————————————————————————————————————————————————————————————————
// Card Container
// ———————————————————————————————————————————————————————————————————
const Card = ({ title, children, style = {} }) => (
  <div style={{
    background: COLORS.card,
    border: `1px solid ${COLORS.cardBorder}`,
    borderRadius: 8,
    overflow: 'hidden',
    ...style,
  }}>
    {title && (
      <div style={{
        padding: '10px 16px',
        borderBottom: `1px solid ${COLORS.cardBorder}`,
        fontSize: 12,
        fontWeight: 700,
        color: COLORS.text,
        letterSpacing: '0.5px',
        textTransform: 'uppercase',
      }}>
        {title}
      </div>
    )}
    {children}
  </div>
);

// ———————————————————————————————————————————————————————————————————
// StatusDot
// ———————————————————————————————————————————————————————————————————
const StatusDot = ({ type }) => {
  const color = type === 'success' || type === 'positive' || type === 'info'
    ? COLORS.green
    : type === 'warning' ? COLORS.yellow
    : type === 'negative' || type === 'error' ? COLORS.red
    : COLORS.cyan;
  return <span style={{ display: 'inline-block', width: 6, height: 6, borderRadius: '50%', background: color, marginRight: 8, flexShrink: 0 }} />;
};

// ———————————————————————————————————————————————————————————————————
// MAIN COMPONENT
// ———————————————————————————————————————————————————————————————————
export default function AlignmentEngine() {
  const [alignmentState, setAlignmentState] = useState(null);
  const [patterns, setPatterns] = useState([]);
  const [auditLog, setAuditLog] = useState([]);
  const [constitutionText, setConstitutionText] = useState('');
  const [loading, setLoading] = useState(true);
  const [driftHistory, setDriftHistory] = useState([]);

  // —— Fetch alignment state on mount
  const fetchAll = useCallback(async () => {
    setLoading(true);
    try {
      const [stateRes, patternsRes, auditRes, constitutionRes, driftRes] = await Promise.all([
        fetch('/api/v1/alignment/state'),
        fetch('/api/v1/alignment/patterns'),
        fetch('/api/v1/alignment/audit'),
        fetch('/api/v1/alignment/constitution'),
        fetch('/api/v1/alignment/drift-history'),
      ]);
      setAlignmentState(await stateRes.json());
      setPatterns(await patternsRes.json());
      setAuditLog(await auditRes.json());
      const cData = await constitutionRes.json();
      setConstitutionText(cData.text || JSON.stringify(cData, null, 2));
      setDriftHistory(await driftRes.json());
    } catch (err) {
      console.error('Alignment fetch error:', err);
    }
    setLoading(false);
  }, []);

  useEffect(() => { fetchAll(); }, [fetchAll]);

  // —— Helpers
  const fmtPct = (v) => v != null ? `${(v * 100).toFixed(1)}%` : '—';
  const fmtTime = (t) => t ? new Date(t).toLocaleTimeString() : '—';

  // —— Render
  return (
    <div style={{ background: COLORS.bg, minHeight: '100vh', color: COLORS.text, fontFamily: "'Inter', -apple-system, sans-serif" }}>
      {/* Header */}
      <div style={{ padding: '16px 24px', borderBottom: `1px solid ${COLORS.cardBorder}`, display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <div>
          <h1 style={{ fontSize: 18, fontWeight: 700, margin: 0, color: COLORS.cyan }}>Alignment Engine</h1>
          <span style={{ fontSize: 11, color: COLORS.textDim }}>Constitutive Alignment Design Patterns Dashboard</span>
        </div>
        <button
          onClick={fetchAll}
          style={{ padding: '6px 16px', borderRadius: 4, border: 'none', fontSize: 11, fontWeight: 600, background: COLORS.cyan, color: COLORS.bg, cursor: 'pointer' }}
        >Refresh All</button>
      </div>

      {loading ? (
        <div style={{ padding: 40, textAlign: 'center', color: COLORS.textDim }}>Loading alignment state...</div>
      ) : (
        <div style={{ padding: 16, display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(420px, 1fr))', gap: 16 }}>

          {/* ——— ALIGNMENT STATE OVERVIEW ——— */}
          <Card title="Alignment State Overview">
            <div style={{ padding: '12px 16px' }}>
              {alignmentState ? (
                <div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 12 }}>
                    <div style={{
                      width: 10, height: 10, borderRadius: '50%',
                      background: alignmentState.aligned ? COLORS.green : COLORS.red,
                    }} />
                    <span style={{ fontSize: 14, fontWeight: 700 }}>
                      {alignmentState.aligned ? 'SYSTEM ALIGNED' : 'ALIGNMENT BREACH'}
                    </span>
                  </div>
                  <div style={{ fontSize: 11, color: COLORS.textDim, lineHeight: 1.8 }}>
                    <div>Drift Score: <span style={{ color: COLORS.cyan, fontWeight: 600 }}>{fmtPct(alignmentState.driftScore)}</span></div>
                    <div>Constitution Version: <span style={{ color: COLORS.text }}>{alignmentState.constitutionVersion || '—'}</span></div>
                    <div>Last Check: <span style={{ color: COLORS.text }}>{fmtTime(alignmentState.lastCheck)}</span></div>
                    <div>Active Patterns: <span style={{ color: COLORS.cyan }}>{alignmentState.activePatterns || patterns.length}</span></div>
                  </div>
                </div>
              ) : (
                <div style={{ color: COLORS.textMuted, fontSize: 11 }}>No alignment state available</div>
              )}
            </div>
          </Card>

          {/* ——— DESIGN PATTERNS STATUS ——— */}
          <Card title="Constitutive Design Patterns">
            <div style={{ padding: '8px 12px', maxHeight: 280, overflowY: 'auto' }}>
              {patterns.length > 0 ? patterns.map((p, i) => (
                <div key={i} style={{
                  display: 'flex', alignItems: 'center', padding: '6px 0',
                  borderBottom: i < patterns.length - 1 ? `1px solid ${COLORS.cardBorder}` : 'none',
                }}>
                  <StatusDot type={p.status === 'active' ? 'success' : p.status === 'degraded' ? 'warning' : 'error'} />
                  <div style={{ flex: 1 }}>
                    <div style={{ fontSize: 11, fontWeight: 600 }}>{p.name}</div>
                    <div style={{ fontSize: 10, color: COLORS.textDim }}>{p.description || p.type}</div>
                  </div>
                  <span style={{ fontSize: 10, fontWeight: 600, color: p.status === 'active' ? COLORS.green : p.status === 'degraded' ? COLORS.yellow : COLORS.red }}>
                    {p.status?.toUpperCase()}
                  </span>
                </div>
              )) : (
                <div style={{ color: COLORS.textMuted, fontSize: 11, padding: 12, textAlign: 'center' }}>No patterns loaded</div>
              )}
            </div>
          </Card>

          {/* ——— DRIFT MONITOR ——— */}
          <Card title="Drift Monitor">
            <div style={{ padding: '12px 16px' }}>
              {driftHistory.length > 0 ? (
                <div>
                  <div style={{ display: 'flex', gap: 4, alignItems: 'flex-end', height: 60, marginBottom: 8 }}>
                    {driftHistory.slice(-30).map((d, i) => (
                      <div key={i} style={{
                        flex: 1,
                        height: `${Math.max(2, (d.score || 0) * 100)}%`,
                        background: (d.score || 0) > 0.3 ? COLORS.red : (d.score || 0) > 0.15 ? COLORS.yellow : COLORS.green,
                        borderRadius: 2,
                        minWidth: 3,
                      }} />
                    ))}
                  </div>
                  <div style={{ fontSize: 10, color: COLORS.textDim, display: 'flex', justifyContent: 'space-between' }}>
                    <span>Last 30 checks</span>
                    <span>Current: {fmtPct(driftHistory[driftHistory.length - 1]?.score)}</span>
                  </div>
                </div>
              ) : (
                <div style={{ color: COLORS.textMuted, fontSize: 11, textAlign: 'center' }}>No drift data yet</div>
              )}
            </div>
          </Card>

          {/* ——— CONSTITUTION VIEWER ——— */}
          <Card title="Constitution">
            <div style={{ padding: '8px 12px', maxHeight: 200, overflowY: 'auto' }}>
              <pre style={{ fontSize: 10, color: COLORS.textDim, whiteSpace: 'pre-wrap', margin: 0, fontFamily: 'monospace', lineHeight: 1.5 }}>
                {constitutionText || 'No constitution loaded'}
              </pre>
            </div>
          </Card>

          {/* ——— AUDIT LOG ——— */}
          <Card title="Alignment Audit Log" style={{ gridColumn: '1 / -1' }}>
            <div style={{ padding: '8px 12px', maxHeight: 250, overflowY: 'auto' }}>
              {auditLog.length > 0 ? auditLog.slice(-50).reverse().map((entry, i) => (
                <div key={i} style={{
                  display: 'flex', alignItems: 'flex-start', padding: '6px 0',
                  borderBottom: i < Math.min(auditLog.length, 50) - 1 ? `1px solid ${COLORS.cardBorder}` : 'none',
                }}>
                  <StatusDot type={entry.type || 'info'} />
                  <div style={{ fontSize: 12, lineHeight: 1.4 }}>
                    <span style={{
                      color: entry.type === 'warning' ? COLORS.yellow : entry.type === 'error' ? COLORS.red : COLORS.cyan,
                      fontWeight: 600, marginRight: 8,
                    }}>
                      {fmtTime(entry.time)}
                    </span>
                    <span style={{ color: COLORS.textDim }}>| {entry.text || entry.message}</span>
                  </div>
                </div>
              )) : (
                <div style={{ color: COLORS.textMuted, fontSize: 11, padding: 12, textAlign: 'center' }}>No audit entries</div>
              )}
            </div>
          </Card>

        </div>
      )}
    </div>
  );
}