import React, { useEffect, useCallback } from 'react';
import useTradeExecution from '../hooks/useTradeExecution';
import AlignmentEngine from "./AlignmentEngine";

// ========== UI-DESIGN-SYSTEM.md EXACT COLORS ==========
const C = {
  bg: '#0B0E14',
  card: '#111827',
  cardAlt: '#1a1e2f',
  input: '#0f1219',
  hover: '#1e293b',
  selected: '#164e63',
  border: '#1e293b',
  borderAccent: '#06b6d4',
  borderSubtle: '#374151',
  cyan500: '#06b6d4',
  cyan400: '#22d3ee',
  cyan300: '#67e8f9',
  green: '#10b981',
  greenDim: 'rgba(16,185,129,0.15)',
  red: '#ef4444',
  redDim: 'rgba(239,68,68,0.15)',
  amber: '#f59e0b',
  amberDim: 'rgba(245,158,11,0.15)',
  blue: '#3b82f6',
  blueDim: 'rgba(59,130,246,0.15)',
  purple: '#8b5cf6',
  text: '#f8fafc',
  textMuted: '#64748b',
  textDim: '#475569',
};

// ========== Card Component ==========
const Card = ({ title, subtitle, children, style = {} }) => (
  <div style={{ background: C.card, border: `1px solid ${C.border}`, borderRadius: 8, overflow: 'hidden', ...style }}>
    {title && (
      <div style={{ padding: '10px 16px', borderBottom: `1px solid ${C.border}`, display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <span style={{ fontSize: 11, fontWeight: 700, color: C.text, letterSpacing: '0.5px', textTransform: 'uppercase' }}>{title}</span>
        {subtitle && <span style={{ fontSize: 10, color: C.textMuted }}>{subtitle}</span>}
      </div>
    )}
    {children}
  </div>
);

// ========== Status Dot ==========
const StatusDot = ({ type }) => {
  const color = type === 'success' || type === 'positive' || type === 'info' ? C.green
    : type === 'warning' ? C.amber
    : type === 'negative' || type === 'error' ? C.red
    : C.cyan500;
  return <span style={{ display: 'inline-block', width: 6, height: 6, borderRadius: '50%', background: color, marginRight: 8, flexShrink: 0 }} />;
};

// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
// TRADE EXECUTION - No-nonsense execution terminal
// Mockup: 12-trade-execution.png
// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
export default function TradeExecution() {
  const {
    portfolio, priceLadder, orderBook, positions, newsFeed, systemStatus,
    selectedRow, setSelectedRow, orderForm, updateOrderForm, loading,
    executeMarketBuy, executeMarketSell, executeLimitBuy, executeLimitSell,
    executeStopLoss, executeAdvancedOrder, closePosition, adjustPosition,
  } = useTradeExecution();

  // Alignment Preflight State
  const [preflightVerdict, setPreflightVerdict] = React.useState(null);
  const runAlignmentPreflight = async () => {
    try {
      const res = await fetch('/api/v1/alignment/preflight', { method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ symbol: orderForm?.symbol || 'SPY', side: orderForm?.side || 'buy', quantity: orderForm?.quantity || 1, strategy: 'manual' })
      });
      const data = await res.json();
      setPreflightVerdict(data);
    } catch (err) {
      setPreflightVerdict({ allowed: false, blockedBy: 'NETWORK_ERROR', summary: err.message });
    }
  };

  // Keyboard Shortcuts
  const handleKeyDown = useCallback((e) => {
    if (e.target.tagName === 'INPUT' || e.target.tagName === 'SELECT') return;
    switch (e.key.toUpperCase()) {
      case 'B': executeMarketBuy(); break;
      case 'S': executeMarketSell(); break;
      case 'L': executeLimitBuy(); break;
      case 'O': executeLimitSell(); break;
      case 'T': executeStopLoss(); break;
      case 'E': executeAdvancedOrder(); break;
      default: break;
    }
  }, [executeMarketBuy, executeMarketSell, executeLimitBuy, executeLimitSell, executeStopLoss, executeAdvancedOrder]);

  useEffect(() => {
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [handleKeyDown]);

  const fmt = (v) => v?.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 }) || '0.00';
  const fmtUsd = (v) => `$${fmt(v)}`;

  return (
    <div style={{ padding: '0 24px 24px', background: C.bg, minHeight: '100vh', color: C.text, fontFamily: "'Inter', -apple-system, sans-serif" }}>

      {/* === HEADER BAR (from mockup 12) === */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '16px 0 20px', borderBottom: `1px solid ${C.border}`, marginBottom: 20 }}>
        <h1 style={{ fontSize: 22, fontWeight: 800, color: C.cyan500, margin: 0, letterSpacing: '1px' }}>TRADE EXECUTION</h1>
        <div style={{ display: 'flex', gap: 24, fontSize: 13, color: C.textMuted }}>
          <span>Portfolio: <strong style={{ color: C.text }}>{fmtUsd(portfolio.value)}</strong></span>
          <span>Daily P/L: <strong style={{ color: portfolio.dailyPnl >= 0 ? C.green : C.red }}>{portfolio.dailyPnl >= 0 ? '+' : ''}{fmtUsd(portfolio.dailyPnl)}</strong></span>
          <span>Status: <strong style={{ color: C.cyan500 }}>{portfolio.status}</strong></span>
          <span>Latency: <strong style={{ color: C.cyan500 }}>{portfolio.latency}ms</strong></span>
        </div>
      </div>

      {/* === QUICK EXECUTION BAR === */}
      <Card title="Quick Execution" style={{ marginBottom: 16 }}>
        <div style={{ display: 'flex', gap: 12, padding: '12px 16px', flexWrap: 'wrap' }}>
          {[
            { label: 'Market Buy [B]', color: C.green, bg: C.greenDim, action: executeMarketBuy },
            { label: 'Market Sell [S]', color: C.red, bg: C.redDim, action: executeMarketSell },
            { label: 'Limit Buy [L]', color: C.blue, bg: 'transparent', border: C.blue, action: executeLimitBuy },
            { label: 'Limit Sell [O]', color: C.blue, bg: 'transparent', border: C.blue, action: executeLimitSell },
            { label: 'Stop Loss [T]', color: C.red, bg: 'transparent', border: C.red, action: executeStopLoss },
          ].map(btn => (
            <button key={btn.label} onClick={btn.action} disabled={loading}
              style={{ padding: '8px 20px', borderRadius: 6, border: btn.border ? `1px solid ${btn.border}` : 'none', background: btn.bg, color: btn.color, fontSize: 13, fontWeight: 600, cursor: loading ? 'not-allowed' : 'pointer', opacity: loading ? 0.6 : 1, transition: 'all 0.15s', letterSpacing: '0.3px' }}>
              {btn.label}
            </button>
          ))}
        </div>
      </Card>

      {/* === MAIN GRID: 4 COLUMNS (from mockup) === */}
      <div style={{ display: 'grid', gridTemplateColumns: '280px 1fr 300px 320px', gap: 16, marginBottom: 16 }}>

        {/* COL 1: Multi-Price Ladder */}
        <Card title="Multi-Price Ladder">
          <div style={{ maxHeight: 480, overflowY: 'auto' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 12 }}>
              <thead>
                <tr style={{ borderBottom: `1px solid ${C.border}` }}>
                  {['Row', 'Price', 'Size'].map(h => (
                    <th key={h} style={{ padding: '8px 10px', textAlign: h === 'Size' ? 'right' : 'left', color: C.textMuted, fontWeight: 600, fontSize: 11, textTransform: 'uppercase' }}>{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {priceLadder.map((row, i) => {
                  const isSelected = i + 1 === selectedRow;
                  const priceColor = row.size > 15 ? C.green : row.size > 5 ? C.amber : C.red;
                  const barWidth = Math.min(row.size * 3, 80);
                  return (
                    <tr key={i} onClick={() => setSelectedRow(i + 1)}
                      style={{ cursor: 'pointer', background: isSelected ? C.selected : 'transparent', borderLeft: isSelected ? `3px solid ${C.cyan500}` : '3px solid transparent', transition: 'background 0.1s' }}>
                      <td style={{ padding: '6px 10px', color: C.textMuted }}>{row.row}</td>
                      <td style={{ padding: '6px 10px', fontWeight: 600, fontFamily: 'monospace', color: isSelected ? C.cyan500 : C.text }}>
                        {parseFloat(row.price).toFixed(2)}
                      </td>
                      <td style={{ padding: '6px 10px', textAlign: 'right', position: 'relative' }}>
                        <div style={{ position: 'absolute', right: 40, top: '50%', transform: 'translateY(-50%)', height: 14, width: barWidth, borderRadius: 2, background: `linear-gradient(90deg, ${priceColor}33, ${priceColor}66)` }} />
                        <span style={{ position: 'relative', fontFamily: 'monospace', color: C.text }}>{row.size}</span>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </Card>

        {/* COL 2: Advanced Order Builder */}
        <Card title="Advanced Order Builder">
          <div style={{ padding: 16 }}>
            <div style={{ display: 'grid', gridTemplateColumns: '80px 1fr', gap: '12px 16px', alignItems: 'center', marginBottom: 16 }}>
              <label style={{ fontSize: 12, color: C.textMuted, fontWeight: 600 }}>Symbol</label>
              <select value={orderForm.symbol} onChange={e => updateOrderForm({ symbol: e.target.value })}
                style={{ background: C.input, border: `1px solid ${C.border}`, borderRadius: 6, padding: '8px 12px', color: C.text, fontSize: 13 }}>
                {['SPX', 'SPY', 'QQQ', 'AAPL', 'TSLA', 'NVDA', 'AMD', 'AMZN', 'MSFT', 'META'].map(s => <option key={s} value={s}>{s}</option>)}
              </select>
              <label style={{ fontSize: 12, color: C.textMuted, fontWeight: 600 }}>Strategy</label>
              <select value={orderForm.strategy} onChange={e => updateOrderForm({ strategy: e.target.value })}
                style={{ background: C.input, border: `1px solid ${C.border}`, borderRadius: 6, padding: '8px 12px', color: C.text, fontSize: 13 }}>
                {['Iron Condor', 'Bull Call Spread', 'Bear Put Spread', 'Straddle', 'Strangle', 'Butterfly', 'Calendar Spread', 'Single Option'].map(s => <option key={s} value={s}>{s}</option>)}
              </select>
            </div>

            {/* Call Section */}
            <div style={{ marginBottom: 16 }}>
              <div style={{ fontSize: 12, fontWeight: 700, color: C.text, marginBottom: 8, textTransform: 'uppercase' }}>Call</div>
              <div style={{ display: 'flex', gap: 6, marginBottom: 6 }}>
                <span style={{ fontSize: 11, color: C.textMuted, width: 32, display: 'flex', alignItems: 'center' }}>Call</span>
                {[4460, 4470, 4460, 4450, 4460].map((v, i) => (
                  <span key={i} style={{ padding: '5px 10px', borderRadius: 4, fontSize: 12, fontFamily: 'monospace', fontWeight: 600, background: i <= 1 ? C.cyan500 + '22' : 'transparent', color: i <= 1 ? C.cyan500 : C.textMuted, border: `1px solid ${i <= 1 ? C.cyan500 + '44' : C.border}`, cursor: 'pointer' }}>{v}</span>
                ))}
              </div>
              <div style={{ display: 'flex', gap: 6 }}>
                <span style={{ fontSize: 11, color: C.textMuted, width: 32, display: 'flex', alignItems: 'center' }}>Put</span>
                {[4440, 4430, 4430, 4430, 4380].map((v, i) => (
                  <span key={i} style={{ padding: '5px 10px', borderRadius: 4, fontSize: 12, fontFamily: 'monospace', fontWeight: 600, background: i <= 1 ? C.cyan500 + '22' : 'transparent', color: i <= 1 ? C.cyan500 : C.textMuted, border: `1px solid ${i <= 1 ? C.cyan500 + '44' : C.border}`, cursor: 'pointer' }}>{v}</span>
                ))}
              </div>
            </div>

            {/* Put Section */}
            <div style={{ marginBottom: 16 }}>
              <div style={{ fontSize: 12, fontWeight: 700, color: C.text, marginBottom: 8, textTransform: 'uppercase' }}>Put</div>
              <div style={{ display: 'flex', gap: 6, marginBottom: 6 }}>
                <span style={{ fontSize: 11, color: C.textMuted, width: 32, display: 'flex', alignItems: 'center' }}>Call</span>
                {[4440, 4450, 4430, 4430, 4430].map((v, i) => (
                  <span key={i} style={{ padding: '5px 10px', borderRadius: 4, fontSize: 12, fontFamily: 'monospace', fontWeight: 600, background: i >= 2 ? C.blue + '22' : 'transparent', color: i >= 2 ? C.blue : C.textMuted, border: `1px solid ${i >= 2 ? C.blue + '44' : C.border}`, cursor: 'pointer' }}>{v}</span>
                ))}
              </div>
              <div style={{ display: 'flex', gap: 6 }}>
                <span style={{ fontSize: 11, color: C.textMuted, width: 32, display: 'flex', alignItems: 'center' }}>Put</span>
                {[4440, 4430, 4430, 4430, 4430].map((v, i) => (
                  <span key={i} style={{ padding: '5px 10px', borderRadius: 4, fontSize: 12, fontFamily: 'monospace', fontWeight: 600, background: i >= 2 ? C.blue + '22' : 'transparent', color: i >= 2 ? C.blue : C.textMuted, border: `1px solid ${i >= 2 ? C.blue + '44' : C.border}`, cursor: 'pointer' }}>{v}</span>
                ))}
              </div>
            </div>

            {/* Quantity + Limits */}
            <div style={{ display: 'grid', gridTemplateColumns: '80px 1fr 1fr', gap: '12px 12px', alignItems: 'center', marginBottom: 20 }}>
              <label style={{ fontSize: 12, color: C.textMuted, fontWeight: 600 }}>Quantity</label>
              <input type="number" value={orderForm.quantity} onChange={e => updateOrderForm({ quantity: parseInt(e.target.value) || 0 })}
                style={{ background: C.input, border: `1px solid ${C.border}`, borderRadius: 6, padding: '8px 12px', color: C.text, fontSize: 13, fontFamily: 'monospace' }} />
              <select value={orderForm.quantityType} onChange={e => updateOrderForm({ quantityType: e.target.value })}
                style={{ background: C.input, border: `1px solid ${C.border}`, borderRadius: 6, padding: '8px 12px', color: C.text, fontSize: 13 }}>
                {['Contracts', 'Shares', 'Lots'].map(t => <option key={t} value={t}>{t}</option>)}
              </select>
              <label style={{ fontSize: 12, color: C.textMuted, fontWeight: 600 }}>Limit</label>
              <input type="number" step="0.01" value={orderForm.limitPrice} onChange={e => updateOrderForm({ limitPrice: parseFloat(e.target.value) || 0 })}
                style={{ background: C.input, border: `1px solid ${C.border}`, borderRadius: 6, padding: '8px 12px', color: C.text, fontSize: 13, fontFamily: 'monospace', gridColumn: 'span 2' }} />
              <label style={{ fontSize: 12, color: C.textMuted, fontWeight: 600 }}>Stop</label>
              <input type="number" step="0.01" value={orderForm.stopPrice} onChange={e => updateOrderForm({ stopPrice: parseFloat(e.target.value) || 0 })}
                style={{ background: C.input, border: `1px solid ${C.border}`, borderRadius: 6, padding: '8px 12px', color: C.text, fontSize: 13, fontFamily: 'monospace', gridColumn: 'span 2' }} />
            </div>

            {/* Execute Button */}
            <button onClick={executeAdvancedOrder} disabled={loading}
              style={{ width: '100%', padding: '12px 0', borderRadius: 6, border: 'none', background: loading ? C.textDim : `linear-gradient(135deg, ${C.cyan500}, ${C.cyan400})`, color: '#fff', fontSize: 14, fontWeight: 700, cursor: loading ? 'not-allowed' : 'pointer', letterSpacing: '0.5px', transition: 'all 0.2s' }}>
              {loading ? 'Executing...' : 'Execute Order [E]'}
            </button>
          </div>
        </Card>

        {/* COL 3: Live Order Book */}
        <Card title="Live Order Book">
          <div style={{ maxHeight: 480, overflowY: 'auto' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 12 }}>
              <thead>
                <tr style={{ borderBottom: `1px solid ${C.border}` }}>
                  {['', 'Bid', 'Size', 'Total'].map(h => (
                    <th key={h} style={{ padding: '8px 8px', textAlign: 'right', color: C.textMuted, fontWeight: 600, fontSize: 11, textTransform: 'uppercase' }}>{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {orderBook.map((row, i) => (
                  <tr key={i} style={{ borderBottom: `1px solid ${C.border}15` }}>
                    <td style={{ padding: '5px 8px', fontFamily: 'monospace', color: C.textMuted, textAlign: 'right' }}>{row.price}</td>
                    <td style={{ padding: '5px 8px', fontFamily: 'monospace', textAlign: 'right' }}>
                      <span style={{ color: parseFloat(row.bid) >= 4450 ? C.green : C.red }}>{row.bid}</span>
                    </td>
                    <td style={{ padding: '5px 8px', fontFamily: 'monospace', color: C.text, textAlign: 'right' }}>{row.size}</td>
                    <td style={{ padding: '5px 8px', fontFamily: 'monospace', color: C.text, textAlign: 'right' }}>{row.total}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>

        {/* COL 4: Price Charts + News Feed */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
          <Card title="Price Charts" style={{ flex: '1 1 auto' }}>
            <div style={{ padding: 12, height: 220, display: 'flex', alignItems: 'center', justifyContent: 'center', position: 'relative' }}>
              <div style={{ position: 'absolute', top: 8, left: 12, fontSize: 11, color: C.textMuted }}>SPX \u00B7 S&P 500 Index \u00B7 1M</div>
              <div style={{ position: 'absolute', top: 22, left: 12, fontSize: 16, fontWeight: 700, color: C.text }}>
                4450.25 <span style={{ color: C.green, fontSize: 12 }}>+430.50 (+0.35%)</span>
              </div>
              <div style={{ width: '100%', height: '100%', display: 'flex', alignItems: 'flex-end', justifyContent: 'space-around', paddingTop: 50 }}>
                {Array.from({ length: 30 }, (_, i) => {
                  const h = 20 + Math.random() * 80 + (i > 20 ? i * 3 : 0);
                  const isGreen = Math.random() > 0.4;
                  return <div key={i} style={{ width: 6, height: h, borderRadius: 1, background: isGreen ? C.green + '88' : C.red + '88' }} />;
                })}
              </div>
              <div style={{ position: 'absolute', bottom: 8, right: 12 }}>
                <span style={{ fontSize: 9, color: C.textDim }}>TV</span>
              </div>
            </div>
          </Card>

          <Card title="News Feed" style={{ flex: '1 1 auto' }}>
            <div style={{ padding: '8px 12px', maxHeight: 200, overflowY: 'auto' }}>
              {newsFeed.map((item, i) => (
                <div key={i} style={{ display: 'flex', alignItems: 'flex-start', padding: '6px 0', borderBottom: i < newsFeed.length - 1 ? `1px solid ${C.border}15` : 'none' }}>
                  <StatusDot type={item.type} />
                  <div style={{ fontSize: 12, lineHeight: 1.4 }}>
                    <span style={{ color: item.type === 'warning' ? C.amber : item.type === 'negative' ? C.red : C.green, fontWeight: 600, marginRight: 8 }}>{item.time}</span>
                    <span style={{ color: C.textMuted }}>| {item.text}</span>
                  </div>
                </div>
              ))}
            </div>
          </Card>
        </div>
      </div>

      {/* === BOTTOM GRID: 2x2 === */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16 }}>

        {/* Live Positions */}
        <Card title="Live Positions">
          <div style={{ overflowX: 'auto' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 12 }}>
              <thead>
                <tr style={{ borderBottom: `1px solid ${C.border}` }}>
                  {['Symbol', 'Side', 'Quantity', 'Avg. Price', 'Current Price', 'P/L', 'Actions'].map(h => (
                    <th key={h} style={{ padding: '10px 12px', textAlign: h === 'Actions' ? 'center' : 'left', color: C.textMuted, fontWeight: 600, fontSize: 11, textTransform: 'uppercase' }}>{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {positions.map((pos, i) => (
                  <tr key={i} style={{ borderBottom: `1px solid ${C.border}15` }}>
                    <td style={{ padding: '10px 12px', fontWeight: 600 }}>{pos.symbol}</td>
                    <td style={{ padding: '10px 12px' }}>
                      <span style={{ color: pos.side === 'Long' ? C.green : C.red, fontWeight: 600 }}>{pos.side}</span>
                    </td>
                    <td style={{ padding: '10px 12px', fontFamily: 'monospace' }}>{pos.quantity}</td>
                    <td style={{ padding: '10px 12px', fontFamily: 'monospace' }}>{pos.avgPrice.toFixed(2)}</td>
                    <td style={{ padding: '10px 12px', fontFamily: 'monospace' }}>{pos.currentPrice.toFixed(2)}</td>
                    <td style={{ padding: '10px 12px', fontFamily: 'monospace' }}>
                      <span style={{ color: pos.pnl >= 0 ? C.green : C.red, fontWeight: 600 }}>{pos.pnl >= 0 ? '+' : ''}{fmtUsd(pos.pnl)}</span>
                    </td>
                    <td style={{ padding: '10px 12px', textAlign: 'center' }}>
                      <div style={{ display: 'flex', gap: 6, justifyContent: 'center' }}>
                        <button onClick={() => closePosition(pos.symbol, pos.side)}
                          style={{ padding: '4px 12px', borderRadius: 4, border: 'none', fontSize: 11, fontWeight: 600, background: C.redDim, color: C.red, cursor: 'pointer' }}>Close</button>
                        <button onClick={() => adjustPosition(pos.symbol, pos.side)}
                          style={{ padding: '4px 12px', borderRadius: 4, border: `1px solid ${C.border}`, fontSize: 11, fontWeight: 600, background: 'transparent', color: C.textMuted, cursor: 'pointer' }}>Adjust</button>
                      </div>
                    </td>
                  </tr>
                ))}
                {positions.length === 0 && (
                  <tr><td colSpan={7} style={{ padding: 24, textAlign: 'center', color: C.textDim }}>No open positions</td></tr>
                )}
              </tbody>
            </table>
          </div>
        </Card>

        {/* Alignment Preflight */}
        <Card title="Alignment Preflight">
          <div style={{ padding: '12px 16px' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 8 }}>
              <div style={{ width: 8, height: 8, borderRadius: '50%', backgroundColor: preflightVerdict?.allowed ? C.green : preflightVerdict ? C.red : C.textDim }} />
              <span style={{ fontSize: 11, fontWeight: 700, color: preflightVerdict?.allowed ? C.green : preflightVerdict ? C.red : C.textDim }}>
                {preflightVerdict ? (preflightVerdict.allowed ? 'ALIGNMENT: PASS' : 'ALIGNMENT: BLOCKED') : 'No preflight run yet'}
              </span>
              {preflightVerdict?.blockedBy && (
                <span style={{ fontSize: 9, fontWeight: 700, padding: '2px 6px', borderRadius: 4, backgroundColor: C.redDim, color: C.red }}>{preflightVerdict.blockedBy}</span>
              )}
            </div>
            {preflightVerdict?.summary && <div style={{ fontSize: 10, color: C.textMuted }}>{preflightVerdict.summary}</div>}
            {preflightVerdict?.adjustments && <div style={{ fontSize: 10, color: C.amber, marginTop: 4 }}>Adjustments: {JSON.stringify(preflightVerdict.adjustments)}</div>}
            <button onClick={() => runAlignmentPreflight()}
              style={{ marginTop: 8, padding: '4px 12px', borderRadius: 4, border: 'none', fontSize: 11, fontWeight: 600, backgroundColor: C.selected, color: C.cyan500, cursor: 'pointer' }}>Run Preflight Check</button>
          </div>
        </Card>

        {/* System Status Log */}
        <Card title="System Status Log">
          <div style={{ padding: '8px 12px', maxHeight: 200, overflowY: 'auto' }}>
            {systemStatus.map((item, i) => (
              <div key={i} style={{ display: 'flex', alignItems: 'flex-start', padding: '6px 0', borderBottom: i < systemStatus.length - 1 ? `1px solid ${C.border}15` : 'none' }}>
                <StatusDot type={item.type} />
                <div style={{ fontSize: 12, lineHeight: 1.4 }}>
                  <span style={{ color: item.type === 'warning' ? C.amber : item.type === 'error' ? C.red : C.cyan500, fontWeight: 600, marginRight: 8 }}>{item.time}</span>
                  <span style={{ color: C.textMuted }}>| {item.text}</span>
                </div>
              </div>
            ))}
          </div>
        </Card>

        {/* Alignment Engine */}
        <Card title="Alignment Engine">
          <div style={{ padding: '8px 12px', maxHeight: 400, overflowY: 'auto' }}>
            <AlignmentEngine />
          </div>
        </Card>
      </div>
    </div>
  );
}