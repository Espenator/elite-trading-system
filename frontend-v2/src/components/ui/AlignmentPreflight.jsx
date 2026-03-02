import React from 'react';

/**
 * AlignmentPreflight — Reusable card that shows the result of an alignment
 * preflight check before trade execution.
 *
 * Props:
 *   verdict   – { allowed: bool, blockedBy?: string, summary?: string, checks?: [] }
 *   onRun     – callback to trigger the preflight check
 *   loading   – boolean, show spinner while checking
 */
export default function AlignmentPreflight({ verdict, onRun, loading = false }) {
  const allowed = verdict?.allowed;
  const borderColor = verdict == null ? '#1a2335' : allowed ? '#00e676' : '#ff5252';
  const bgColor = verdict == null ? '#0d1320' : allowed ? 'rgba(0,230,118,0.06)' : 'rgba(255,82,82,0.06)';

  return (
    <div style={{
      background: bgColor,
      border: `1px solid ${borderColor}`,
      borderRadius: 8,
      padding: 16,
      marginBottom: 12,
    }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 8 }}>
        <span style={{ fontSize: 12, fontWeight: 700, color: '#e2e8f0', letterSpacing: '0.5px', textTransform: 'uppercase' }}>
          Alignment Preflight
        </span>
        <button
          onClick={onRun}
          disabled={loading}
          style={{
            padding: '4px 12px',
            borderRadius: 4,
            border: 'none',
            fontSize: 10,
            fontWeight: 600,
            background: '#00d4aa',
            color: '#0a0e17',
            cursor: loading ? 'wait' : 'pointer',
            opacity: loading ? 0.6 : 1,
          }}
        >
          {loading ? 'Checking...' : 'Run Check'}
        </button>
      </div>

      {verdict == null ? (
        <div style={{ fontSize: 11, color: '#8892a4' }}>Click "Run Check" before executing a trade.</div>
      ) : (
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 6 }}>
            <div style={{
              width: 8, height: 8, borderRadius: '50%',
              background: allowed ? '#00e676' : '#ff5252',
            }} />
            <span style={{ fontSize: 13, fontWeight: 700, color: allowed ? '#00e676' : '#ff5252' }}>
              {allowed ? 'TRADE ALLOWED' : 'TRADE BLOCKED'}
            </span>
          </div>
          {verdict.blockedBy && (
            <div style={{ fontSize: 10, color: '#ff5252', marginBottom: 4 }}>
              Blocked by: <strong>{verdict.blockedBy}</strong>
            </div>
          )}
          {verdict.summary && (
            <div style={{ fontSize: 10, color: '#8892a4', lineHeight: 1.5 }}>{verdict.summary}</div>
          )}
          {verdict.checks && verdict.checks.length > 0 && (
            <div style={{ marginTop: 8 }}>
              {verdict.checks.map((c, i) => (
                <div key={i} style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 10, color: '#8892a4', padding: '2px 0' }}>
                  <span style={{ color: c.passed ? '#00e676' : '#ff5252' }}>{c.passed ? '✓' : '✗'}</span>
                  <span>{c.name}</span>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}