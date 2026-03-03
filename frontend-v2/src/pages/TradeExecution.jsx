import React, { useEffect, useCallback } from 'react';
import useTradeExecution from '../hooks/useTradeExecution';
import AlignmentEngine from "../components/settings/AlignmentEngine";

// ========== UI-DESIGN-SYSTEM.md EXACT COLORS ==========
const C = {
  bg: '#0B0E14',
  card: '#111827',
  cardAlt: '#1a1e2f',
  input: '#0f1219',
  hover: '#1e293b',
  selected: '#164e63',
  border: '#1e293b',
  borderAccent: '#00D9FF',
  borderSubtle: '#374151',
  cyan500: '#00D9FF',
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
  <div style={{ background: '#111827', border: '1px solid rgba(42,52,68,0.5)', borderRadius: 8, overflow: 'hidden', transition: 'box-shadow 0.2s, border-color 0.2s', ...style }}
    onMouseEnter={e => { e.currentTarget.style.boxShadow = '0 0 20px rgba(0,217,255,0.12)'; e.currentTarget.style.borderColor = 'rgba(0,217,255,0.3)'; }}
    onMouseLeave={e => { e.currentTarget.style.boxShadow = 'none'; e.currentTarget.style.borderColor = 'rgba(42,52,68,0.5)'; }}>
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

// ========== Volume Bar (depth visualization) ==========
const VolumeBar = ({ value, max, color, side = 'right' }) => {
  const pct = Math.min((value / max) * 100, 100);
  return (
    <div style={{ position: 'absolute', top: 0, bottom: 0, [side]: 0, width: `${pct}%`, background: color, opacity: 0.12, pointerEvents: 'none' }} />
  );
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
  const maxLadderSize = Math.max(...(priceLadder || []).map(r => r.size || 0), 1);
  const maxBookSize = Math.max(...(orderBook || []).map(r => r.size || 0), 1);

  return (
    <div style={{ background: C.bg, minHeight: '100vh', padding: 16, fontFamily: "'Inter', sans-serif" }}>
      {/* === HEADER BAR (from mockup 12) === */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12, padding: '10px 16px', background: '#111827', borderRadius: 8, border: '1px solid rgba(42,52,68,0.5)' }}>
        <h1 style={{ fontSize: 16, fontWeight: 700, color: C.cyan500, margin: 0, letterSpacing: 1 }}>TRADE EXECUTION</h1>
        <div style={{ display: 'flex', gap: 20, fontSize: 12, fontFamily: "'JetBrains Mono', monospace" }}>
          <span style={{ color: C.textMuted }}>Portfolio: <b style={{ color: C.text }}>{fmtUsd(portfolio.value)}</b></span>
          <span style={{ color: C.textMuted }}>Daily P/L: <b style={{ color: portfolio.dailyPnl >= 0 ? C.green : C.red }}>{portfolio.dailyPnl >= 0 ? '+' : ''}{fmtUsd(portfolio.dailyPnl)}</b></span>
          <span style={{ color: C.textMuted }}>Status: <b style={{ color: C.green }}>{portfolio.status}</b></span>
          <span style={{ color: C.textMuted }}>Latency: <b style={{ color: C.cyan400 }}>{portfolio.latency}ms</b></span>
        </div>
      </div>

      {/* === QUICK EXECUTION BAR === */}
      <div style={{ display: 'flex', gap: 8, marginBottom: 12, flexWrap: 'wrap' }}>
        {[
          { label: 'Market Buy [B]', color: C.green, bg: C.greenDim, action: executeMarketBuy },
          { label: 'Market Sell [S]', color: C.red, bg: C.redDim, action: executeMarketSell },
          { label: 'Limit Buy [L]', color: C.blue, bg: 'transparent', border: C.blue, action: executeLimitBuy },
          { label: 'Limit Sell [O]', color: C.blue, bg: 'transparent', border: C.blue, action: executeLimitSell },
          { label: 'Stop Loss [T]', color: C.red, bg: 'transparent', border: C.red, action: executeStopLoss },
        ].map(btn => (
          <button key={btn.label} onClick={btn.action}
            style={{ padding: '8px 18px', borderRadius: 6, border: btn.border ? `1px solid ${btn.border}` : 'none', fontSize: 12, fontWeight: 700, fontFamily: "'JetBrains Mono', monospace", background: btn.bg, color: btn.color, cursor: 'pointer', letterSpacing: 0.5, transition: 'all 0.2s' }}
            onMouseEnter={e => { e.currentTarget.style.boxShadow = `0 0 16px ${btn.color}33`; e.currentTarget.style.transform = 'translateY(-1px)'; }}
            onMouseLeave={e => { e.currentTarget.style.boxShadow = 'none'; e.currentTarget.style.transform = 'none'; }}>
            {btn.label}
          </button>
        ))}
      </div>

      {/* === MAIN GRID: 4 COLUMNS (from mockup) === */}
      <div style={{ display: 'grid', gridTemplateColumns: '200px 1fr 1fr 1fr', gap: 10, marginBottom: 10 }}>

        {/* COL 1: Multi-Price Ladder with Volume Bars */}
        <Card title="Multi-Price Ladder">
          <div style={{ padding: '0 8px 8px', overflowY: 'auto', maxHeight: 480 }}>
            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 11, fontFamily: "'JetBrains Mono', monospace" }}>
              <thead>
                <tr>
                  {['Row', 'Price', 'Size'].map(h => (
                    <th key={h} style={{ padding: '4px 6px', textAlign: h === 'Size' ? 'right' : 'left', color: C.textMuted, fontSize: 10, fontWeight: 600, borderBottom: `1px solid ${C.border}` }}>{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {priceLadder.map((row, i) => {
                  const isSelected = i + 1 === selectedRow;
                  const priceColor = row.size > 15 ? C.green : row.size > 5 ? C.amber : C.red;
                  return (
                    <tr key={i} onClick={() => setSelectedRow(i + 1)}
                      style={{ cursor: 'pointer', background: isSelected ? C.selected : 'transparent', borderLeft: isSelected ? `3px solid #00D9FF` : '3px solid transparent', transition: 'all 0.15s', position: 'relative' }}
                      onMouseEnter={e => { if (!isSelected) e.currentTarget.style.background = 'rgba(0,217,255,0.04)'; }}
                      onMouseLeave={e => { if (!isSelected) e.currentTarget.style.background = 'transparent'; }}>
                      <td style={{ padding: '3px 6px', color: C.textDim, fontSize: 10 }}>{row.row}</td>
                      <td style={{ padding: '3px 6px', color: isSelected ? C.cyan400 : C.text, fontWeight: isSelected ? 700 : 400 }}>{parseFloat(row.price).toFixed(2)}</td>
                      <td style={{ padding: '3px 6px', textAlign: 'right', color: priceColor, position: 'relative' }}>
                        <div style={{ position: 'absolute', top: 0, bottom: 0, right: 0, width: `${Math.min(row.size * 4, 100)}%`, background: priceColor, opacity: 0.15 }} />
                        <span style={{ position: 'relative', zIndex: 1 }}>{row.size}</span>
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
          <div style={{ padding: '8px 12px', display: 'grid', gap: 8 }}>
            <div style={{ display: 'grid', gridTemplateColumns: '60px 1fr', alignItems: 'center', gap: 6 }}>
              <span style={{ fontSize: 11, color: C.textMuted }}>Symbol</span>
              <select value={orderForm.symbol} onChange={e => updateOrderForm({ symbol: e.target.value })} style={{ background: '#0B0E14', border: '1px solid rgba(42,52,68,0.5)', borderRadius: 8, padding: '8px 12px', color: C.text, fontSize: 13 }}>
                {['SPX', 'SPY', 'QQQ', 'AAPL', 'TSLA', 'NVDA', 'AMD', 'AMZN', 'MSFT', 'META'].map(s => <option key={s} value={s}>{s}</option>)}
              </select>
              <span style={{ fontSize: 11, color: C.textMuted }}>Strategy</span>
              <select value={orderForm.strategy} onChange={e => updateOrderForm({ strategy: e.target.value })} style={{ background: '#0B0E14', border: '1px solid rgba(42,52,68,0.5)', borderRadius: 8, padding: '8px 12px', color: C.text, fontSize: 13 }}>
                {['Iron Condor', 'Bull Call Spread', 'Bear Put Spread', 'Straddle', 'Strangle', 'Butterfly', 'Calendar Spread', 'Single Option'].map(s => <option key={s} value={s}>{s}</option>)}
              </select>
            </div>

            {/* Call Section */}
            <Card title="Call" style={{ background: C.cardAlt }}>
              <div style={{ padding: 8, display: 'flex', gap: 6 }}>
                <span style={{ fontSize: 10, color: C.green, width: 28 }}>Call</span>
                {[4460, 4470, 4460, 4450, 4460].map((v, i) => (
                  <span key={i} style={{ padding: '2px 8px', borderRadius: 4, fontSize: 11, fontFamily: "'JetBrains Mono', monospace", background: i >= 1 && i <= 2 ? C.greenDim : 'transparent', color: i >= 1 && i <= 2 ? C.green : C.textMuted, border: `1px solid ${i >= 1 && i <= 2 ? C.green + '44' : C.border}`, cursor: 'pointer' }}>{v}</span>
                ))}
              </div>
              <div style={{ padding: '0 8px 8px', display: 'flex', gap: 6 }}>
                <span style={{ fontSize: 10, color: C.red, width: 28 }}>Put</span>
                {[4440, 4430, 4430, 4430, 4380].map((v, i) => (
                  <span key={i} style={{ padding: '2px 8px', borderRadius: 4, fontSize: 11, fontFamily: "'JetBrains Mono', monospace", background: 'transparent', color: C.textMuted, border: `1px solid ${C.border}`, cursor: 'pointer' }}>{v}</span>
                ))}
              </div>
            </Card>

            {/* Put Section */}
            <Card title="Put" style={{ background: C.cardAlt }}>
              <div style={{ padding: 8, display: 'flex', gap: 6 }}>
                <span style={{ fontSize: 10, color: C.green, width: 28 }}>Call</span>
                {[4440, 4450, 4430, 4430, 4430].map((v, i) => (
                  <span key={i} style={{ padding: '2px 8px', borderRadius: 4, fontSize: 11, fontFamily: "'JetBrains Mono', monospace", background: i >= 2 ? C.blueDim : 'transparent', color: i >= 2 ? C.blue : C.textMuted, border: `1px solid ${i >= 2 ? C.blue + '44' : C.border}`, cursor: 'pointer' }}>{v}</span>
                ))}
              </div>
              <div style={{ padding: '0 8px 8px', display: 'flex', gap: 6 }}>
                <span style={{ fontSize: 10, color: C.red, width: 28 }}>Put</span>
                {[4440, 4430, 4430, 4430, 4430].map((v, i) => (
                  <span key={i} style={{ padding: '2px 8px', borderRadius: 4, fontSize: 11, fontFamily: "'JetBrains Mono', monospace", background: i >= 2 ? C.blueDim : 'transparent', color: i >= 2 ? C.blue : C.textMuted, border: `1px solid ${i >= 2 ? C.blue + '44' : C.border}`, cursor: 'pointer' }}>{v}</span>
                ))}
              </div>
            </Card>

            {/* Quantity + Limits */}
            <div style={{ display: 'grid', gridTemplateColumns: '60px 1fr 1fr', gap: 6, alignItems: 'center' }}>
              <span style={{ fontSize: 11, color: C.textMuted }}>Quantity</span>
              <input type="number" value={orderForm.quantity} onChange={e => updateOrderForm({ quantity: parseInt(e.target.value) || 0 })} style={{ background: '#0B0E14', border: '1px solid rgba(42,52,68,0.5)', borderRadius: 8, padding: '8px 12px', color: C.text, fontSize: 13, fontFamily: 'monospace' }} />
              <select value={orderForm.quantityType} onChange={e => updateOrderForm({ quantityType: e.target.value })} style={{ background: '#0B0E14', border: '1px solid rgba(42,52,68,0.5)', borderRadius: 8, padding: '8px 12px', color: C.text, fontSize: 13 }}>
                {['Contracts', 'Shares', 'Lots'].map(t => <option key={t} value={t}>{t}</option>)}
              </select>
              <span style={{ fontSize: 11, color: C.textMuted }}>Limit</span>
              <input type="number" step="0.01" value={orderForm.limitPrice} onChange={e => updateOrderForm({ limitPrice: parseFloat(e.target.value) || 0 })} style={{ background: '#0B0E14', border: '1px solid rgba(42,52,68,0.5)', borderRadius: 8, padding: '8px 12px', color: C.text, fontSize: 13, fontFamily: 'monospace', gridColumn: 'span 2' }} />
              <span style={{ fontSize: 11, color: C.textMuted }}>Stop</span>
              <input type="number" step="0.01" value={orderForm.stopPrice} onChange={e => updateOrderForm({ stopPrice: parseFloat(e.target.value) || 0 })} style={{ background: '#0B0E14', border: '1px solid rgba(42,52,68,0.5)', borderRadius: 8, padding: '8px 12px', color: C.text, fontSize: 13, fontFamily: 'monospace', gridColumn: 'span 2' }} />
            </div>

            {/* Execute Button */}
            <button onClick={executeAdvancedOrder} disabled={loading}
              style={{ padding: '10px 16px', borderRadius: 8, border: 'none', fontSize: 13, fontWeight: 700, fontFamily: "'JetBrains Mono', monospace", background: `linear-gradient(135deg, #00D9FF, ${C.blue})`, color: '#fff', cursor: loading ? 'wait' : 'pointer', opacity: loading ? 0.6 : 1, letterSpacing: 0.5, transition: 'all 0.2s' }}
              onMouseEnter={e => { if (!loading) { e.currentTarget.style.boxShadow = '0 0 20px rgba(0,217,255,0.25)'; e.currentTarget.style.transform = 'translateY(-1px)'; } }}
              onMouseLeave={e => { e.currentTarget.style.boxShadow = 'none'; e.currentTarget.style.transform = 'none'; }}>
              {loading ? 'Executing...' : 'Execute Order [E]'}
            </button>
          </div>
        </Card>

        {/* COL 3: Live Order Book with Depth Bars */}
        <Card title="Live Order Book">
          <div style={{ padding: '0 8px 8px', overflowY: 'auto', maxHeight: 480 }}>
            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 11, fontFamily: "'JetBrains Mono', monospace" }}>
              <thead>
                <tr>
                  {['', 'Bid', 'Size', 'Total'].map(h => (
                    <th key={h} style={{ padding: '4px 6px', textAlign: 'right', color: C.textMuted, fontSize: 10, fontWeight: 600, borderBottom: `1px solid ${C.border}` }}>{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {orderBook.map((row, i) => (
                  <tr key={i} style={{ position: 'relative', transition: 'background 0.15s', cursor: 'pointer' }}
                    onMouseEnter={e => { e.currentTarget.style.background = 'rgba(0,217,255,0.04)'; }}
                    onMouseLeave={e => { e.currentTarget.style.background = 'transparent'; }}>
                    <td style={{ padding: '3px 6px', color: C.textDim, fontSize: 10, position: 'relative' }}>
                      <VolumeBar value={row.size} max={maxBookSize} color={row.bid >= 4450 ? C.green : C.red} side="left" />
                      <span style={{ position: 'relative', zIndex: 1 }}>{row.price}</span>
                    </td>
                    <td style={{ padding: '3px 6px', textAlign: 'right', color: row.bid >= 4450 ? C.green : C.red }}>{row.bid}</td>
                    <td style={{ padding: '3px 6px', textAlign: 'right', color: C.text }}>{row.size}</td>
                    <td style={{ padding: '3px 6px', textAlign: 'right', color: C.textMuted }}>{row.total}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>

        {/* COL 4: Price Charts + News Feed */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
          <Card title="Price Charts" subtitle="SPX \u00B7 S&P 500 Index \u00B7 1M">
            <div style={{ padding: '8px 12px' }}>
              <div style={{ fontSize: 18, fontWeight: 700, color: C.text, fontFamily: "'JetBrains Mono', monospace" }}>
                4450.25 <span style={{ fontSize: 12, color: C.green }}>+430.50 (+0.35%)</span>
              </div>
              <svg width="100%" height="160" viewBox="0 0 300 160" style={{ marginTop: 8 }}>
                {Array.from({ length: 30 }, (_, i) => {
                  const h = 20 + Math.random() * 80 + (i > 20 ? i * 3 : 0);
                  const isGreen = Math.random() > 0.4;
                  return <rect key={i} x={i * 10} y={160 - h} width={7} height={h} rx={1} fill={isGreen ? C.green : C.red} opacity={0.8} />;
                })}
                {/* Volume bars at bottom */}
                {Array.from({ length: 30 }, (_, i) => {
                  const vol = 5 + Math.random() * 20;
                  return <rect key={`v${i}`} x={i * 10} y={155} width={7} height={vol * 0.2} fill={C.textDim} opacity={0.3} />;
                })}
              </svg>
              <div style={{ textAlign: 'right', marginTop: 4 }}>
                <span style={{ fontSize: 10, color: C.textMuted, background: C.cardAlt, padding: '2px 6px', borderRadius: 3, cursor: 'pointer' }}>TV</span>
              </div>
            </div>
          </Card>
          <Card title="News Feed">
            <div style={{ padding: '4px 8px', maxHeight: 200, overflowY: 'auto' }}>
              {newsFeed.map((item, i) => (
                <div key={i} style={{ padding: '4px 0', borderBottom: i < newsFeed.length - 1 ? `1px solid ${C.border}` : 'none', fontSize: 11, lineHeight: 1.4 }}>
                  <span style={{ color: C.cyan500, fontWeight: 600, marginRight: 8 }}>{item.time}</span>
                  <span style={{ color: C.textMuted }}>| {item.text}</span>
                </div>
              ))}
            </div>
          </Card>
        </div>

      </div>

      {/* === BOTTOM GRID: 2x2 === */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10, marginBottom: 10 }}>

        {/* Live Positions */}
        <Card title="Live Positions" style={{ gridColumn: 'span 2' }}>
          <div style={{ padding: '0 8px 8px', overflowX: 'auto' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 11, fontFamily: "'JetBrains Mono', monospace" }}>
              <thead>
                <tr>
                  {['Symbol', 'Side', 'Quantity', 'Avg. Price', 'Current Price', 'P/L', 'Actions'].map(h => (
                    <th key={h} style={{ padding: '6px 8px', textAlign: 'left', color: C.textMuted, fontSize: 10, fontWeight: 600, borderBottom: `1px solid ${C.border}` }}>{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {positions.map((pos, i) => (
                  <tr key={i} style={{ borderBottom: `1px solid ${C.border}` }}>
                    <td style={{ padding: '6px 8px', color: C.cyan400, fontWeight: 600 }}>{pos.symbol}</td>
                    <td style={{ padding: '6px 8px', color: pos.side === 'Long' ? C.green : C.red }}>{pos.side}</td>
                    <td style={{ padding: '6px 8px', color: C.text }}>{pos.quantity}</td>
                    <td style={{ padding: '6px 8px', color: C.text }}>{pos.avgPrice.toFixed(2)}</td>
                    <td style={{ padding: '6px 8px', color: C.text }}>{pos.currentPrice.toFixed(2)}</td>
                    <td style={{ padding: '6px 8px', color: pos.pnl >= 0 ? C.green : C.red, fontWeight: 600 }}>{pos.pnl >= 0 ? '+' : ''}{fmtUsd(pos.pnl)}</td>
                    <td style={{ padding: '6px 8px' }}>
                      <button onClick={() => closePosition(pos.symbol, pos.side)} style={{ padding: '4px 12px', borderRadius: 4, border: 'none', fontSize: 11, fontWeight: 600, background: C.redDim, color: C.red, cursor: 'pointer', marginRight: 4 }}>Close</button>
                      <button onClick={() => adjustPosition(pos.symbol, pos.side)} style={{ padding: '4px 12px', borderRadius: 4, border: `1px solid ${C.border}`, fontSize: 11, fontWeight: 600, background: 'transparent', color: C.textMuted, cursor: 'pointer' }}>Adjust</button>
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
            </div>
            {preflightVerdict?.blockedBy && (
              <span style={{ fontSize: 9, fontWeight: 700, padding: '2px 6px', borderRadius: 4, backgroundColor: C.redDim, color: C.red }}>{preflightVerdict.blockedBy}</span>
            )}
            {preflightVerdict?.summary && <div style={{ fontSize: 10, color: C.textMuted, marginTop: 4 }}>{preflightVerdict.summary}</div>}
            {preflightVerdict?.adjustments && <div style={{ fontSize: 10, color: C.amber, marginTop: 4 }}>Adjustments: {JSON.stringify(preflightVerdict.adjustments)}</div>}
            <button onClick={() => runAlignmentPreflight()}
              style={{ marginTop: 8, padding: '4px 12px', borderRadius: 6, border: '1px solid rgba(0,217,255,0.3)', fontSize: 11, fontWeight: 600, backgroundColor: 'rgba(0,217,255,0.1)', color: '#00D9FF', cursor: 'pointer', transition: 'all 0.2s' }}
              onMouseEnter={e => { e.currentTarget.style.backgroundColor = 'rgba(0,217,255,0.2)'; e.currentTarget.style.boxShadow = '0 0 12px rgba(0,217,255,0.15)'; }}
              onMouseLeave={e => { e.currentTarget.style.backgroundColor = 'rgba(0,217,255,0.1)'; e.currentTarget.style.boxShadow = 'none'; }}>Run Preflight Check</button>
          </div>
        </Card>

        {/* System Status Log */}
        <Card title="System Status Log">
          <div style={{ padding: '8px 12px', maxHeight: 200, overflowY: 'auto' }}>
            {systemStatus.map((item, i) => (
              <div key={i} style={{ display: 'flex', alignItems: 'flex-start', padding: '6px 0', borderBottom: i < systemStatus.length - 1 ? `1px solid ${C.border}` : 'none' }}>
                <StatusDot type={item.type} />
                <div style={{ fontSize: 12, lineHeight: 1.4 }}>
                  <span style={{ color: item.type === 'warning' ? C.amber : item.type === 'error' ? C.red : C.cyan500, fontWeight: 600, marginRight: 8 }}>{item.time}</span>
                  <span style={{ color: C.textMuted }}>| {item.text}</span>
                </div>
              </div>
            ))}
          </div>
        </Card>

      </div>

      {/* Alignment Engine */}
      <Card title="Alignment Engine">
        <div style={{ padding: '8px 12px', maxHeight: 400, overflowY: 'auto' }}>
          <AlignmentEngine />
        </div>
      </Card>

    </div>
  );
}