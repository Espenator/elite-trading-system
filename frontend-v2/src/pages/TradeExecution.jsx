import React, { useEffect, useCallback } from 'react';
import useTradeExecution from '../hooks/useTradeExecution';

// ─── Shared Style Constants ────────────────────────────────
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
  blueDim: 'rgba(68, 138, 255, 0.15)',
  orange: '#ff9100',
  orangeDim: 'rgba(255, 145, 0, 0.15)',
  highlight: '#1a2a40',
  input: '#111827',
  inputBorder: '#1e293b',
};

// ─── Card Container ────────────────────────────────────────
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

// ─── Status Dot ────────────────────────────────────────────
const StatusDot = ({ type }) => {
  const color = type === 'success' || type === 'positive' || type === 'info'
    ? COLORS.green
    : type === 'warning'
      ? COLORS.yellow
      : type === 'negative' || type === 'error'
        ? COLORS.red
        : COLORS.cyan;
  return <span style={{ display: 'inline-block', width: 6, height: 6, borderRadius: '50%', background: color, marginRight: 8, flexShrink: 0 }} />;
};

// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
// MAIN COMPONENT
// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
export default function TradeExecution() {
  const {
    portfolio,
    priceLadder,
    orderBook,
    positions,
    newsFeed,
    systemStatus,
    selectedRow,
    setSelectedRow,
    orderForm,
    updateOrderForm,
    loading,
    executeMarketBuy,
    executeMarketSell,
    executeLimitBuy,
    executeLimitSell,
    executeStopLoss,
    executeAdvancedOrder,
    closePosition,
    adjustPosition,
  } = useTradeExecution();

    // —— Alignment Preflight State ——————————————————————
  const [preflightVerdict, setPreflightVerdict] = React.useState(null);

  const runAlignmentPreflight = async () => {
    try {
            const res = await fetch('/api/v1/alignment/preflight', {  method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          symbol: orderForm?.symbol || 'SPY',
          side: orderForm?.side || 'buy',
          quantity: orderForm?.quantity || 1,
          strategy: 'manual'
        })
      });
      const data = await res.json();
      setPreflightVerdict(data);
    } catch (err) {
      setPreflightVerdict({ allowed: false, blockedBy: 'NETWORK_ERROR', summary: err.message });
    }
  };

  // ─── Keyboard Shortcuts ──────────────────────────────────
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

  // ─── Helpers ─────────────────────────────────────────────
  const fmt = (v) => v?.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 }) || '0.00';
  const fmtUsd = (v) => `$${fmt(v)}`;

  return (
    <div style={{ padding: '0 24px 24px', background: COLORS.bg, minHeight: '100vh', color: COLORS.text, fontFamily: "'Inter', -apple-system, sans-serif" }}>

      {/* ━━━ HEADER BAR ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '16px 0 20px', borderBottom: `1px solid ${COLORS.cardBorder}`, marginBottom: 20 }}>
        <h1 style={{ fontSize: 22, fontWeight: 800, color: COLORS.cyan, margin: 0, letterSpacing: '1px' }}>TRADE EXECUTION</h1>
        <div style={{ display: 'flex', gap: 24, fontSize: 13, color: COLORS.textDim }}>
          <span>Portfolio: <strong style={{ color: COLORS.text }}>{fmtUsd(portfolio.value)}</strong></span>
          <span>Daily P/L: <strong style={{ color: portfolio.dailyPnl >= 0 ? COLORS.green : COLORS.red }}>+{fmtUsd(portfolio.dailyPnl)}</strong></span>
          <span>Status: <strong style={{ color: COLORS.cyan }}>{portfolio.status}</strong></span>
          <span>Latency: <strong style={{ color: COLORS.cyan }}>{portfolio.latency}ms</strong></span>
        </div>
      </div>

      {/* ━━━ QUICK EXECUTION BAR ━━━━━━━━━━━━━━━━━━━━━━━━━━━ */}
      <Card title="Quick Execution" style={{ marginBottom: 16 }}>
        <div style={{ display: 'flex', gap: 12, padding: '12px 16px', flexWrap: 'wrap' }}>
          {[
            { label: 'Market Buy [B]', color: COLORS.green, bg: COLORS.greenDim, action: executeMarketBuy },
            { label: 'Market Sell [S]', color: COLORS.red, bg: COLORS.redDim, action: executeMarketSell },
            { label: 'Limit Buy [L]', color: COLORS.blue, bg: 'transparent', border: COLORS.blue, action: executeLimitBuy },
            { label: 'Limit Sell [O]', color: COLORS.blue, bg: 'transparent', border: COLORS.blue, action: executeLimitSell },
            { label: 'Stop Loss [T]', color: COLORS.red, bg: 'transparent', border: COLORS.red, action: executeStopLoss },
          ].map(btn => (
            <button
              key={btn.label}
              onClick={btn.action}
              disabled={loading}
              style={{
                padding: '8px 20px',
                borderRadius: 6,
                border: btn.border ? `1px solid ${btn.border}` : 'none',
                background: btn.bg,
                color: btn.color,
                fontSize: 13,
                fontWeight: 600,
                cursor: loading ? 'not-allowed' : 'pointer',
                opacity: loading ? 0.6 : 1,
                transition: 'all 0.15s',
                letterSpacing: '0.3px',
              }}
            >
              {btn.label}
            </button>
          ))}
        </div>
      </Card>

      {/* ━━━ MAIN GRID: 4 COLUMNS ━━━━━━━━━━━━━━━━━━━━━━━━━ */}
      <div style={{ display: 'grid', gridTemplateColumns: '280px 1fr 300px 320px', gap: 16, marginBottom: 16 }}>

        {/* ── COL 1: Multi-Price Ladder ──────────────────── */}
        <Card title="Multi-Price Ladder">
          <div style={{ maxHeight: 480, overflowY: 'auto' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 12 }}>
              <thead>
                <tr style={{ borderBottom: `1px solid ${COLORS.cardBorder}` }}>
                  {['Row', 'Price', 'Size'].map(h => (
                    <th key={h} style={{ padding: '8px 10px', textAlign: h === 'Size' ? 'right' : 'left', color: COLORS.textDim, fontWeight: 600, fontSize: 11, textTransform: 'uppercase' }}>{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {priceLadder.map((row, i) => {
                  const isSelected = i + 1 === selectedRow;
                  const priceColor = row.size > 15 ? COLORS.green : row.size > 5 ? COLORS.yellow : COLORS.red;
                  const barWidth = Math.min(row.size * 3, 80);
                  return (
                    <tr
                      key={i}
                      onClick={() => setSelectedRow(i + 1)}
                      style={{
                        cursor: 'pointer',
                        background: isSelected ? COLORS.highlight : 'transparent',
                        borderLeft: isSelected ? `3px solid ${COLORS.cyan}` : '3px solid transparent',
                        transition: 'background 0.1s',
                      }}
                    >
                      <td style={{ padding: '6px 10px', color: COLORS.textDim }}>{row.row}</td>
                      <td style={{ padding: '6px 10px', fontWeight: 600, fontFamily: 'monospace', color: isSelected ? COLORS.cyan : COLORS.text }}>
                        {parseFloat(row.price).toFixed(2)}
                      </td>
                      <td style={{ padding: '6px 10px', textAlign: 'right', position: 'relative' }}>
                        <div style={{
                          position: 'absolute', right: 40, top: '50%', transform: 'translateY(-50%)',
                          height: 14, width: barWidth, borderRadius: 2,
                          background: `linear-gradient(90deg, ${priceColor}33, ${priceColor}66)`,
                        }} />
                        <span style={{ position: 'relative', fontFamily: 'monospace', color: COLORS.text }}>{row.size}</span>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </Card>

        {/* ── COL 2: Advanced Order Builder ──────────────── */}
        <Card title="Advanced Order Builder">
          <div style={{ padding: 16 }}>
            {/* Symbol + Strategy */}
            <div style={{ display: 'grid', gridTemplateColumns: '80px 1fr', gap: '12px 16px', alignItems: 'center', marginBottom: 16 }}>
              <label style={{ fontSize: 12, color: COLORS.textDim, fontWeight: 600 }}>Symbol</label>
              <select
                value={orderForm.symbol}
                onChange={e => updateOrderForm({ symbol: e.target.value })}
                style={{ background: COLORS.input, border: `1px solid ${COLORS.inputBorder}`, borderRadius: 6, padding: '8px 12px', color: COLORS.text, fontSize: 13 }}
              >
                {['SPX', 'SPY', 'QQQ', 'AAPL', 'TSLA', 'NVDA', 'AMD', 'AMZN', 'MSFT', 'META'].map(s => <option key={s} value={s}>{s}</option>)}
              </select>

              <label style={{ fontSize: 12, color: COLORS.textDim, fontWeight: 600 }}>Strategy</label>
              <select
                value={orderForm.strategy}
                onChange={e => updateOrderForm({ strategy: e.target.value })}
                style={{ background: COLORS.input, border: `1px solid ${COLORS.inputBorder}`, borderRadius: 6, padding: '8px 12px', color: COLORS.text, fontSize: 13 }}
              >
                {['Iron Condor', 'Bull Call Spread', 'Bear Put Spread', 'Straddle', 'Strangle', 'Butterfly', 'Calendar Spread', 'Single Option'].map(s => <option key={s} value={s}>{s}</option>)}
              </select>
            </div>

            {/* Call Section */}
            <div style={{ marginBottom: 16 }}>
              <div style={{ fontSize: 12, fontWeight: 700, color: COLORS.text, marginBottom: 8, textTransform: 'uppercase' }}>Call</div>
              <div style={{ display: 'flex', gap: 6, marginBottom: 6 }}>
                <span style={{ fontSize: 11, color: COLORS.textDim, width: 32, display: 'flex', alignItems: 'center' }}>Call</span>
                {[4460, 4470, 4460, 4450, 4460].map((v, i) => (
                  <span key={i} style={{
                    padding: '5px 10px', borderRadius: 4, fontSize: 12, fontFamily: 'monospace', fontWeight: 600,
                    background: i <= 1 ? COLORS.cyan + '22' : 'transparent',
                    color: i <= 1 ? COLORS.cyan : COLORS.textDim,
                    border: `1px solid ${i <= 1 ? COLORS.cyan + '44' : COLORS.cardBorder}`,
                    cursor: 'pointer',
                  }}>{v}</span>
                ))}
              </div>
              <div style={{ display: 'flex', gap: 6 }}>
                <span style={{ fontSize: 11, color: COLORS.textDim, width: 32, display: 'flex', alignItems: 'center' }}>Put</span>
                {[4440, 4430, 4430, 4430, 4380].map((v, i) => (
                  <span key={i} style={{
                    padding: '5px 10px', borderRadius: 4, fontSize: 12, fontFamily: 'monospace', fontWeight: 600,
                    background: i <= 1 ? COLORS.cyan + '22' : 'transparent',
                    color: i <= 1 ? COLORS.cyan : COLORS.textDim,
                    border: `1px solid ${i <= 1 ? COLORS.cyan + '44' : COLORS.cardBorder}`,
                    cursor: 'pointer',
                  }}>{v}</span>
                ))}
              </div>
            </div>

            {/* Put Section */}
            <div style={{ marginBottom: 16 }}>
              <div style={{ fontSize: 12, fontWeight: 700, color: COLORS.text, marginBottom: 8, textTransform: 'uppercase' }}>Put</div>
              <div style={{ display: 'flex', gap: 6, marginBottom: 6 }}>
                <span style={{ fontSize: 11, color: COLORS.textDim, width: 32, display: 'flex', alignItems: 'center' }}>Call</span>
                {[4440, 4450, 4430, 4430, 4430].map((v, i) => (
                  <span key={i} style={{
                    padding: '5px 10px', borderRadius: 4, fontSize: 12, fontFamily: 'monospace', fontWeight: 600,
                    background: i >= 2 ? COLORS.blue + '22' : 'transparent',
                    color: i >= 2 ? COLORS.blue : COLORS.textDim,
                    border: `1px solid ${i >= 2 ? COLORS.blue + '44' : COLORS.cardBorder}`,
                    cursor: 'pointer',
                  }}>{v}</span>
                ))}
              </div>
              <div style={{ display: 'flex', gap: 6 }}>
                <span style={{ fontSize: 11, color: COLORS.textDim, width: 32, display: 'flex', alignItems: 'center' }}>Put</span>
                {[4440, 4430, 4430, 4430, 4430].map((v, i) => (
                  <span key={i} style={{
                    padding: '5px 10px', borderRadius: 4, fontSize: 12, fontFamily: 'monospace', fontWeight: 600,
                    background: i >= 2 ? COLORS.blue + '22' : 'transparent',
                    color: i >= 2 ? COLORS.blue : COLORS.textDim,
                    border: `1px solid ${i >= 2 ? COLORS.blue + '44' : COLORS.cardBorder}`,
                    cursor: 'pointer',
                  }}>{v}</span>
                ))}
              </div>
            </div>

            {/* Quantity + Limits */}
            <div style={{ display: 'grid', gridTemplateColumns: '80px 1fr 1fr', gap: '12px 12px', alignItems: 'center', marginBottom: 20 }}>
              <label style={{ fontSize: 12, color: COLORS.textDim, fontWeight: 600 }}>Quantity</label>
              <input
                type="number"
                value={orderForm.quantity}
                onChange={e => updateOrderForm({ quantity: parseInt(e.target.value) || 0 })}
                style={{ background: COLORS.input, border: `1px solid ${COLORS.inputBorder}`, borderRadius: 6, padding: '8px 12px', color: COLORS.text, fontSize: 13, fontFamily: 'monospace' }}
              />
              <select
                value={orderForm.quantityType}
                onChange={e => updateOrderForm({ quantityType: e.target.value })}
                style={{ background: COLORS.input, border: `1px solid ${COLORS.inputBorder}`, borderRadius: 6, padding: '8px 12px', color: COLORS.text, fontSize: 13 }}
              >
                {['Contracts', 'Shares', 'Lots'].map(t => <option key={t} value={t}>{t}</option>)}
              </select>

              <label style={{ fontSize: 12, color: COLORS.textDim, fontWeight: 600 }}>Limit</label>
              <input
                type="number"
                step="0.01"
                value={orderForm.limitPrice}
                onChange={e => updateOrderForm({ limitPrice: parseFloat(e.target.value) || 0 })}
                style={{ background: COLORS.input, border: `1px solid ${COLORS.inputBorder}`, borderRadius: 6, padding: '8px 12px', color: COLORS.text, fontSize: 13, fontFamily: 'monospace', gridColumn: 'span 2' }}
              />

              <label style={{ fontSize: 12, color: COLORS.textDim, fontWeight: 600 }}>Limit</label>
              <input
                type="number"
                step="0.01"
                value={orderForm.stopPrice}
                onChange={e => updateOrderForm({ stopPrice: parseFloat(e.target.value) || 0 })}
                style={{ background: COLORS.input, border: `1px solid ${COLORS.inputBorder}`, borderRadius: 6, padding: '8px 12px', color: COLORS.text, fontSize: 13, fontFamily: 'monospace', gridColumn: 'span 2' }}
              />
            </div>

            {/* Execute Button */}
            <button
              onClick={executeAdvancedOrder}
              disabled={loading}
              style={{
                width: '100%', padding: '12px 0', borderRadius: 6, border: 'none',
                background: loading ? COLORS.textMuted : `linear-gradient(135deg, ${COLORS.cyan}, ${COLORS.cyanDark})`,
                color: '#fff', fontSize: 14, fontWeight: 700, cursor: loading ? 'not-allowed' : 'pointer',
                letterSpacing: '0.5px', transition: 'all 0.2s',
              }}
            >
              {loading ? 'Executing...' : 'Execute Order [E]'}
            </button>
          </div>
        </Card>

        {/* ── COL 3: Live Order Book ────────────────────── */}
        <Card title="Live Order Book">
          <div style={{ maxHeight: 480, overflowY: 'auto' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 12 }}>
              <thead>
                <tr style={{ borderBottom: `1px solid ${COLORS.cardBorder}` }}>
                  {['', 'Bid', 'Size', 'Total'].map(h => (
                    <th key={h} style={{ padding: '8px 8px', textAlign: 'right', color: COLORS.textDim, fontWeight: 600, fontSize: 11, textTransform: 'uppercase' }}>{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {orderBook.map((row, i) => (
                  <tr key={i} style={{ borderBottom: `1px solid ${COLORS.cardBorder}15` }}>
                    <td style={{ padding: '5px 8px', fontFamily: 'monospace', color: COLORS.textDim, textAlign: 'right' }}>
                      {row.price}
                    </td>
                    <td style={{ padding: '5px 8px', fontFamily: 'monospace', textAlign: 'right' }}>
                      <span style={{ color: parseFloat(row.bid) >= 4450 ? COLORS.green : COLORS.red }}>{row.bid}</span>
                    </td>
                    <td style={{ padding: '5px 8px', fontFamily: 'monospace', color: COLORS.text, textAlign: 'right' }}>{row.size}</td>
                    <td style={{ padding: '5px 8px', fontFamily: 'monospace', color: COLORS.text, textAlign: 'right' }}>{row.total}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>

        {/* ── COL 4: Price Charts + News Feed ───────────── */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
          {/* Price Charts */}
          <Card title="Price Charts" style={{ flex: '1 1 auto' }}>
            <div style={{ padding: 12, height: 220, display: 'flex', alignItems: 'center', justifyContent: 'center', position: 'relative' }}>
              <div style={{ position: 'absolute', top: 8, left: 12, fontSize: 11, color: COLORS.textDim }}>
                SPX \u00B7 S&P 500 Index \u00B7 1M
              </div>
              <div style={{ position: 'absolute', top: 22, left: 12, fontSize: 16, fontWeight: 700, color: COLORS.text }}>
                4450.25 <span style={{ color: COLORS.green, fontSize: 12 }}>+430.50 (+0.35%)</span>
              </div>
              {/* Chart placeholder - TradingView widget would go here */}
              <div style={{ width: '100%', height: '100%', display: 'flex', alignItems: 'flex-end', justifyContent: 'space-around', paddingTop: 50 }}>
                {Array.from({ length: 30 }, (_, i) => {
                  const h = 20 + Math.random() * 80 + (i > 20 ? i * 3 : 0);
                  const isGreen = Math.random() > 0.4;
                  return (
                    <div key={i} style={{
                      width: 6, height: h, borderRadius: 1,
                      background: isGreen ? COLORS.green + '88' : COLORS.red + '88',
                    }} />
                  );
                })}
              </div>
              <div style={{ position: 'absolute', bottom: 8, right: 12 }}>
                <svg width="16" height="16" viewBox="0 0 16 16" fill="none"><text x="0" y="12" fontSize="9" fill={COLORS.textDim}>TV</text></svg>
              </div>
            </div>
          </Card>

          {/* News Feed */}
          <Card title="News Feed" style={{ flex: '1 1 auto' }}>
            <div style={{ padding: '8px 12px', maxHeight: 200, overflowY: 'auto' }}>
              {newsFeed.map((item, i) => (
                <div key={i} style={{ display: 'flex', alignItems: 'flex-start', padding: '6px 0', borderBottom: i < newsFeed.length - 1 ? `1px solid ${COLORS.cardBorder}15` : 'none' }}>
                  <StatusDot type={item.type} />
                  <div style={{ fontSize: 12, lineHeight: 1.4 }}>
                    <span style={{
                      color: item.type === 'warning' ? COLORS.yellow : item.type === 'negative' ? COLORS.red : COLORS.green,
                      fontWeight: 600, marginRight: 8,
                    }}>
                      {item.time}
                    </span>
                    <span style={{ color: COLORS.textDim }}>| {item.text}</span>
                  </div>
                </div>
              ))}
            </div>
          </Card>
        </div>
      </div>

      {/* ━━━ BOTTOM GRID: 2 COLUMNS ━━━━━━━━━━━━━━━━━━━━━━━ */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16 }}>

        {/* ── Live Positions ─────────────────────────────── */}
        <Card title="Live Positions">
          <div style={{ overflowX: 'auto' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 12 }}>
              <thead>
                <tr style={{ borderBottom: `1px solid ${COLORS.cardBorder}` }}>
                  {['Symbol', 'Side', 'Quantity', 'Avg. Price', 'Current Price', 'P/L', 'Actions'].map(h => (
                    <th key={h} style={{ padding: '10px 12px', textAlign: h === 'Actions' ? 'center' : 'left', color: COLORS.textDim, fontWeight: 600, fontSize: 11, textTransform: 'uppercase' }}>{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {positions.map((pos, i) => (
                  <tr key={i} style={{ borderBottom: `1px solid ${COLORS.cardBorder}15` }}>
                    <td style={{ padding: '10px 12px', fontWeight: 600 }}>{pos.symbol}</td>
                    <td style={{ padding: '10px 12px' }}>
                      <span style={{ color: pos.side === 'Long' ? COLORS.green : COLORS.red, fontWeight: 600 }}>{pos.side}</span>
                    </td>
                    <td style={{ padding: '10px 12px', fontFamily: 'monospace' }}>{pos.quantity}</td>
                    <td style={{ padding: '10px 12px', fontFamily: 'monospace' }}>{pos.avgPrice.toFixed(2)}</td>
                    <td style={{ padding: '10px 12px', fontFamily: 'monospace' }}>{pos.currentPrice.toFixed(2)}</td>
                    <td style={{ padding: '10px 12px', fontFamily: 'monospace' }}>
                      <span style={{ color: pos.pnl >= 0 ? COLORS.green : COLORS.red, fontWeight: 600 }}>
                        {pos.pnl >= 0 ? '+' : ''}{fmtUsd(pos.pnl)}
                      </span>
                    </td>
                    <td style={{ padding: '10px 12px', textAlign: 'center' }}>
                      <div style={{ display: 'flex', gap: 6, justifyContent: 'center' }}>
                        <button
                          onClick={() => closePosition(pos.symbol, pos.side)}
                          style={{
                            padding: '4px 12px', borderRadius: 4, border: 'none', fontSize: 11, fontWeight: 600,
                            background: COLORS.redDim, color: COLORS.red, cursor: 'pointer',
                          }}
                        >Close</button>
                        <button
                          onClick={() => adjustPosition(pos.symbol, pos.side)}
                          style={{
                            padding: '4px 12px', borderRadius: 4, border: `1px solid ${COLORS.cardBorder}`, fontSize: 11, fontWeight: 600,
                            background: 'transparent', color: COLORS.textDim, cursor: 'pointer',
                          }}
                        >Adjust</button>
                      </div>
                    </td>
                  </tr>
                ))}
                {positions.length === 0 && (
                  <tr><td colSpan={7} style={{ padding: 24, textAlign: 'center', color: COLORS.textMuted }}>No open positions</td></tr>
                )}
              </tbody>
            </table>
          </div>
        </Card>

              {/* ── ALIGNMENT PREFLIGHT ── */}
      <Card title="Alignment Preflight">
        <div style={{ padding: '12px 16px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 8 }}>
            <div style={{ width: 8, height: 8, borderRadius: '50%', backgroundColor: preflightVerdict?.allowed ? COLORS.green : preflightVerdict ? COLORS.red : COLORS.textDim }} />
            <span style={{ fontSize: 11, fontWeight: 700, color: preflightVerdict?.allowed ? COLORS.green : preflightVerdict ? COLORS.red : COLORS.textDim }}>
              {preflightVerdict ? (preflightVerdict.allowed ? 'ALIGNMENT: PASS' : 'ALIGNMENT: BLOCKED') : 'No preflight run yet'}
            </span>
            {preflightVerdict?.blockedBy && (
              <span style={{ fontSize: 9, fontWeight: 700, padding: '2px 6px', borderRadius: 4, backgroundColor: COLORS.redDim, color: COLORS.red }}>{preflightVerdict.blockedBy}</span>
            )}
          </div>
          {preflightVerdict?.summary && <div style={{ fontSize: 10, color: COLORS.textDim }}>{preflightVerdict.summary}</div>}
          {preflightVerdict?.adjustments && <div style={{ fontSize: 10, color: COLORS.yellow, marginTop: 4 }}>Adjustments: {JSON.stringify(preflightVerdict.adjustments)}</div>}
          <button
            onClick={() => runAlignmentPreflight()}
            style={{ marginTop: 8, padding: '4px 12px', borderRadius: 4, border: 'none', fontSize: 11, fontWeight: 600, backgroundColor: COLORS.cyanDark, color: COLORS.cyan, cursor: 'pointer' }}
          >Run Preflight Check</button>
        </div>
      </Card>

        {/* ── System Status Log ──────────────────────────── */}
        <Card title="System Status Log">
          <div style={{ padding: '8px 12px', maxHeight: 200, overflowY: 'auto' }}>
            {systemStatus.map((item, i) => (
              <div key={i} style={{ display: 'flex', alignItems: 'flex-start', padding: '6px 0', borderBottom: i < systemStatus.length - 1 ? `1px solid ${COLORS.cardBorder}15` : 'none' }}>
                <StatusDot type={item.type} />
                <div style={{ fontSize: 12, lineHeight: 1.4 }}>
                  <span style={{
                    color: item.type === 'warning' ? COLORS.yellow : item.type === 'error' ? COLORS.red : COLORS.cyan,
                    fontWeight: 600, marginRight: 8,
                  }}>
                    {item.time}
                  </span>
                  <span style={{ color: COLORS.textDim }}>
                    | {item.text}
                  </span>
                </div>
              </div>
            ))}
          </div>
        </Card>
      </div>
    </div>
  );
}
