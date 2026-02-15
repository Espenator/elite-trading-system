// TRADE EXECUTION CENTER - Embodier.ai Glass House Trade Intelligence
// Full transparency: live positions, order entry, execution logs, ML insights
// Backend: GET /api/v1/trades, GET /api/v1/positions, POST /api/v1/orders
// WebSocket: 'trades' channel for real-time execution updates

import { useState, useEffect, useCallback } from 'react';
import { getApiUrl } from '../config/api';

// ========== REUSABLE GLASS PANEL ==========
function GlassPanel({ title, icon, collapsed, onToggle, maxHeight = '500px', children, badge, headerActions, glowColor = 'cyan' }) {
  const glowMap = {
    cyan: 'border-cyan-500/30 shadow-cyan-500/10',
    emerald: 'border-emerald-500/30 shadow-emerald-500/10',
    purple: 'border-purple-500/30 shadow-purple-500/10',
    red: 'border-red-500/30 shadow-red-500/10',
    blue: 'border-blue-500/30 shadow-blue-500/10',
    yellow: 'border-yellow-500/30 shadow-yellow-500/10',
    amber: 'border-amber-500/30 shadow-amber-500/10'
  };
  return (
    <div className={`bg-gradient-to-br from-gray-900/90 to-gray-950/95 backdrop-blur-xl border ${glowMap[glowColor]} rounded-2xl overflow-hidden shadow-2xl`}>
      <div className="flex items-center justify-between px-5 py-3 bg-gradient-to-r from-gray-800/60 to-gray-900/60 cursor-pointer hover:from-gray-700/60 hover:to-gray-800/60 transition-all" onClick={onToggle}>
        <div className="flex items-center gap-3"><span className="text-lg">{icon}</span><h3 className="text-sm font-bold text-white tracking-wide">{title}</h3>{badge && <span className="px-2 py-0.5 text-xs rounded-full bg-cyan-900/60 text-cyan-300 border border-cyan-500/20">{badge}</span>}</div>
        <div className="flex items-center gap-2">{headerActions}<svg className={`w-4 h-4 text-gray-400 transition-transform duration-300 ${collapsed ? '' : 'rotate-180'}`} fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" /></svg></div>
      </div>
      {!collapsed && <div className="overflow-y-auto custom-scrollbar" style={{ maxHeight }}>{children}</div>}
    </div>
  );
}

// ========== MAIN TRADES COMPONENT ==========
export default function Trades() {
  const [panels, setPanels] = useState({ positions: true, history: true, performance: true, orders: true, orderEntry: true, mlInsights: false, advancedOrders: false });
  const togglePanel = useCallback((key) => setPanels(prev => ({ ...prev, [key]: !prev[key] })), []);
  const [filterStatus, setFilterStatus] = useState('ALL');
  const [selectedTicker, setSelectedTicker] = useState('TSLA');
  const [orderType, setOrderType] = useState('limit');
  const [orderSide, setOrderSide] = useState('buy');
  const [orderQty, setOrderQty] = useState(100);
  const [orderPrice, setOrderPrice] = useState(150.25);
  const [bracketEnabled, setBracketEnabled] = useState(true);
  const [takeProfitPct, setTakeProfitPct] = useState(2.0);
  const [stopLossPct, setStopLossPct] = useState(1.5);
  const [trailingStop, setTrailingStop] = useState(false);
  const [trailingPct, setTrailingPct] = useState(1.0);
  const [timeInForce, setTimeInForce] = useState('DAY');

  // OLEH: Replace with GET /api/v1/positions - real-time from Alpaca
  const positions = [
    { ticker: 'NVDA', direction: 'LONG', qty: 50, avgEntry: 874.50, current: 882.30, pnl: 390, pnlPct: 0.89, stopLoss: 857.50, takeProfit: 910.00, riskReward: '1:2.1', signal: 'AI Signal #s1', agent: 'Trade Executor', time: '14:32:07' },
    { ticker: 'AAPL', direction: 'LONG', qty: 100, avgEntry: 185.50, current: 186.20, pnl: 70, pnlPct: 0.38, stopLoss: 181.00, takeProfit: 194.00, riskReward: '1:1.9', signal: 'AI Signal #s2', agent: 'Trade Executor', time: '14:28:32' },
    { ticker: 'AMD', direction: 'LONG', qty: 75, avgEntry: 165.00, current: 168.40, pnl: 255, pnlPct: 2.06, stopLoss: 158.00, takeProfit: 180.00, riskReward: '1:2.1', signal: 'AI Signal #s4', agent: 'Trade Executor', time: '13:55:12' },
    { ticker: 'AMZN', direction: 'LONG', qty: 60, avgEntry: 185.00, current: 187.50, pnl: 150, pnlPct: 1.35, stopLoss: 178.00, takeProfit: 198.00, riskReward: '1:1.9', signal: 'AI Signal #s8', agent: 'Trade Executor', time: '12:30:02' },
    { ticker: 'MSFT', direction: 'LONG', qty: 150, avgEntry: 415.50, current: 420.10, pnl: 690, pnlPct: 1.11, stopLoss: 405.00, takeProfit: 435.00, riskReward: '1:1.9', signal: 'AI Signal #s3', agent: 'Trade Executor', time: '11:45:18' },
  ];

  // OLEH: Replace with GET /api/v1/trades - historical from Alpaca
  const tradeHistory = [
    { id: 't1', ticker: 'NVDA', direction: 'BUY', qty: 50, price: 874.50, time: '14:32:07', status: 'filled', pnl: null, fees: 0.50, ordType: 'limit', fillTime: '0.3s', slippage: 0.02 },
    { id: 't2', ticker: 'AAPL', direction: 'BUY', qty: 100, price: 185.50, time: '14:28:32', status: 'filled', pnl: null, fees: 0.35, ordType: 'limit', fillTime: '0.5s', slippage: 0.01 },
    { id: 't3', ticker: 'TSLA', direction: 'SELL', qty: 30, price: 248.00, time: '13:12:45', status: 'filled', pnl: 210, fees: 0.40, ordType: 'market', fillTime: '0.1s', slippage: 0.15 },
    { id: 't4', ticker: 'AMD', direction: 'BUY', qty: 75, price: 165.00, time: '13:55:12', status: 'filled', pnl: null, fees: 0.45, ordType: 'limit', fillTime: '0.4s', slippage: 0.03 },
    { id: 't5', ticker: 'META', direction: 'SELL', qty: 25, price: 520.00, time: '12:45:00', status: 'filled', pnl: 375, fees: 0.55, ordType: 'limit', fillTime: '0.6s', slippage: 0.05 },
    { id: 't6', ticker: 'AMZN', direction: 'BUY', qty: 60, price: 185.00, time: '12:30:02', status: 'filled', pnl: null, fees: 0.30, ordType: 'limit', fillTime: '0.3s', slippage: 0.01 },
    { id: 't7', ticker: 'GOOG', direction: 'SELL', qty: 20, price: 175.50, time: '11:15:30', status: 'filled', pnl: -120, fees: 0.25, ordType: 'stop', fillTime: '0.1s', slippage: 0.20 },
    { id: 't8', ticker: 'MSFT', direction: 'BUY', qty: 40, price: 418.00, time: '10:30:15', status: 'cancelled', pnl: null, fees: 0, ordType: 'limit', fillTime: '-', slippage: 0 },
  ];

  const totalPnl = positions.reduce((s, p) => s + p.pnl, 0);
  const totalValue = positions.reduce((s, p) => s + (p.current * p.qty), 0);
  const winCount = tradeHistory.filter(t => t.pnl > 0).length;
  const lossCount = tradeHistory.filter(t => t.pnl !== null && t.pnl < 0).length;
  const totalFees = tradeHistory.reduce((s, t) => s + t.fees, 0);
  const avgSlippage = (tradeHistory.filter(t => t.slippage > 0).reduce((s, t) => s + t.slippage, 0) / tradeHistory.filter(t => t.slippage > 0).length).toFixed(3);
  const filteredHistory = filterStatus === 'ALL' ? tradeHistory : tradeHistory.filter(t => t.status === filterStatus.toLowerCase());
  const estimatedCost = orderQty * orderPrice;
  const estimatedMargin = estimatedCost / 2;

  return (
    <div className="space-y-4">
      {/* ===== PAGE HEADER ===== */}
      <div className="relative">
        <div className="absolute inset-0 bg-gradient-to-r from-emerald-500/5 via-transparent to-red-500/5 rounded-2xl" />
        <div className="relative flex items-center justify-between p-4">
          <div>
            <h1 className="text-2xl font-bold text-transparent bg-clip-text bg-gradient-to-r from-emerald-400 to-cyan-400">Trade Execution Center</h1>
            <p className="text-gray-400 text-sm">Live positions, execution details, and P&L analysis</p>
          </div>
          <div className="flex gap-2">
            <button className="px-3 py-1.5 text-xs bg-red-600/80 hover:bg-red-500 text-white rounded-xl transition-colors font-bold border border-red-500/30">Close All Positions</button>
            <button className="px-3 py-1.5 text-xs bg-gray-700 hover:bg-gray-600 text-gray-300 rounded-xl transition-colors">Export CSV</button>
          </div>
        </div>
      </div>

      {/* ===== Performance Summary ===== */}
      <GlassPanel title="Performance Summary" icon="\u{1F4B0}" collapsed={!panels.performance} onToggle={() => togglePanel('performance')} maxHeight="220px" glowColor="emerald">
        <div className="p-4">
          <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-7 gap-3">
            <div className="bg-gradient-to-br from-emerald-900/30 to-emerald-950/50 border border-emerald-500/20 rounded-xl p-3">
              <p className="text-xs text-emerald-400/70 uppercase tracking-wider">Total P&L</p>
              <p className={`text-xl font-bold font-mono ${totalPnl >= 0 ? 'text-emerald-300' : 'text-red-300'}`}>${totalPnl.toLocaleString()}</p>
            </div>
            <div className="bg-gradient-to-br from-cyan-900/30 to-cyan-950/50 border border-cyan-500/20 rounded-xl p-3">
              <p className="text-xs text-cyan-400/70 uppercase tracking-wider">Portfolio Value</p>
              <p className="text-xl font-bold text-cyan-300 font-mono">${totalValue.toLocaleString()}</p>
            </div>
            <div className="bg-gradient-to-br from-blue-900/30 to-blue-950/50 border border-blue-500/20 rounded-xl p-3">
              <p className="text-xs text-blue-400/70 uppercase tracking-wider">Open Positions</p>
              <p className="text-xl font-bold text-blue-300 font-mono">{positions.length}</p>
            </div>
            <div className="bg-gradient-to-br from-purple-900/30 to-purple-950/50 border border-purple-500/20 rounded-xl p-3">
              <p className="text-xs text-purple-400/70 uppercase tracking-wider">Win Rate</p>
              <p className="text-xl font-bold text-purple-300 font-mono">{winCount + lossCount > 0 ? ((winCount / (winCount + lossCount)) * 100).toFixed(1) : 0}%</p>
            </div>
            <div className="bg-gradient-to-br from-yellow-900/30 to-yellow-950/50 border border-yellow-500/20 rounded-xl p-3">
              <p className="text-xs text-yellow-400/70 uppercase tracking-wider">Today Trades</p>
              <p className="text-xl font-bold text-yellow-300 font-mono">{tradeHistory.length}</p>
            </div>
            <div className="bg-gradient-to-br from-amber-900/30 to-amber-950/50 border border-amber-500/20 rounded-xl p-3">
              <p className="text-xs text-amber-400/70 uppercase tracking-wider">Total Fees</p>
              <p className="text-xl font-bold text-amber-300 font-mono">${totalFees.toFixed(2)}</p>
            </div>
            <div className="bg-gradient-to-br from-red-900/30 to-red-950/50 border border-red-500/20 rounded-xl p-3">
              <p className="text-xs text-red-400/70 uppercase tracking-wider">Avg Slippage</p>
              <p className="text-xl font-bold text-red-300 font-mono">${avgSlippage}</p>
            </div>
          </div>
        </div>
      </GlassPanel>

      {/* ===== Chart + Order Entry Row ===== */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        {/* Chart Panel - 2/3 width */}
        <div className="lg:col-span-2">
          <GlassPanel title={`${selectedTicker} Chart`} icon="\u{1F4C8}" collapsed={false} onToggle={() => {}} maxHeight="400px" glowColor="blue"
            headerActions={
              <div className="flex gap-1 mr-2">
                {['15M','1H','4H','1D'].map(tf => (
                  <button key={tf} className="px-2 py-0.5 text-xs rounded bg-gray-700/60 hover:bg-cyan-600/40 text-gray-300 hover:text-white transition-colors">{tf}</button>
                ))}
              </div>
            }>
            <div className="p-4 flex items-center justify-center h-64 bg-gradient-to-br from-gray-900/50 to-gray-950/80">
              <div className="text-center">
                <p className="text-gray-500 text-lg">Interactive Chart for {selectedTicker}</p>
                <p className="text-gray-600 text-xs mt-2">OLEH: Integrate TradingView Lightweight Charts or similar</p>
                <p className="text-gray-600 text-xs">WebSocket: real-time candle updates from Alpaca stream</p>
              </div>
            </div>
          </GlassPanel>
        </div>

        {/* Order Entry Panel - 1/3 width */}
        <div>
          <GlassPanel title={`Order Entry for ${selectedTicker}`} icon="\u{1F4DD}" collapsed={!panels.orderEntry} onToggle={() => togglePanel('orderEntry')} maxHeight="500px" glowColor="emerald">
            <div className="p-4 space-y-4">
              {/* Order Type */}
              <div>
                <label className="text-xs text-gray-400 block mb-1">Order Type</label>
                <select value={orderType} onChange={e => setOrderType(e.target.value)} className="w-full bg-gray-800/80 border border-gray-600/50 rounded-lg px-3 py-2 text-sm text-white focus:border-cyan-500 focus:outline-none">
                  <option value="limit">Limit</option>
                  <option value="market">Market</option>
                  <option value="stop">Stop</option>
                  <option value="stop_limit">Stop Limit</option>
                </select>
              </div>
              {/* Quantity */}
              <div>
                <label className="text-xs text-gray-400 block mb-1">Quantity</label>
                <input type="number" value={orderQty} onChange={e => setOrderQty(Number(e.target.value))} className="w-full bg-gray-800/80 border border-gray-600/50 rounded-lg px-3 py-2 text-sm text-white font-mono focus:border-cyan-500 focus:outline-none" />
              </div>
              {/* Price */}
              {orderType !== 'market' && (
                <div>
                  <label className="text-xs text-gray-400 block mb-1">Price</label>
                  <input type="number" step="0.01" value={orderPrice} onChange={e => setOrderPrice(Number(e.target.value))} className="w-full bg-gray-800/80 border border-gray-600/50 rounded-lg px-3 py-2 text-sm text-white font-mono focus:border-cyan-500 focus:outline-none" />
                </div>
              )}
              {/* Buy / Sell Buttons */}
              <div className="grid grid-cols-2 gap-2">
                <button onClick={() => setOrderSide('buy')} className={`py-2.5 rounded-xl font-bold text-sm transition-all ${orderSide === 'buy' ? 'bg-emerald-600 text-white shadow-lg shadow-emerald-500/20' : 'bg-gray-700/60 text-gray-400 hover:bg-gray-600/60'}`}>Buy</button>
                <button onClick={() => setOrderSide('sell')} className={`py-2.5 rounded-xl font-bold text-sm transition-all ${orderSide === 'sell' ? 'bg-red-600 text-white shadow-lg shadow-red-500/20' : 'bg-gray-700/60 text-gray-400 hover:bg-gray-600/60'}`}>Sell</button>
              </div>
              {/* Order Preview */}
              <div className="bg-gray-800/40 rounded-xl p-3 border border-gray-700/30 space-y-2">
                <h4 className="text-xs font-bold text-gray-300 uppercase tracking-wider">Order Preview</h4>
                <div className="flex justify-between text-xs"><span className="text-gray-400">Estimated Cost:</span><span className="text-white font-mono">${estimatedCost.toLocaleString()}</span></div>
                <div className="flex justify-between text-xs"><span className="text-gray-400">Required Margin:</span><span className="text-white font-mono">${estimatedMargin.toLocaleString()}</span></div>
                <div className="flex justify-between text-xs"><span className="text-gray-400">Risk Status:</span><span className="text-emerald-400 font-mono">Within Limits</span></div>
              </div>
              {/* Submit */}
              <button className={`w-full py-3 rounded-xl font-bold text-sm transition-all ${orderSide === 'buy' ? 'bg-gradient-to-r from-emerald-600 to-emerald-500 hover:from-emerald-500 hover:to-emerald-400 text-white shadow-lg shadow-emerald-500/20' : 'bg-gradient-to-r from-red-600 to-red-500 hover:from-red-500 hover:to-red-400 text-white shadow-lg shadow-red-500/20'}`}>
                {orderSide === 'buy' ? 'Submit Buy Order' : 'Submit Sell Order'}
              </button>
            </div>
          </GlassPanel>
        </div>
      </div>

      {/* ===== Live Positions ===== */}
      <GlassPanel title="Live Positions" icon="\u{1F4CD}" collapsed={!panels.positions} onToggle={() => togglePanel('positions')} badge={`${positions.length} open`} maxHeight="400px" glowColor="cyan">
        <div className="p-3">
          <div className="overflow-x-auto">
            <table className="w-full text-xs">
              <thead><tr className="text-gray-400 border-b border-gray-700">
                <th className="py-2 px-2 text-left">Ticker</th><th className="py-2 px-2">Dir</th><th className="py-2 px-2">Qty</th><th className="py-2 px-2">Entry</th><th className="py-2 px-2">Current</th><th className="py-2 px-2">P&L</th><th className="py-2 px-2">P&L%</th><th className="py-2 px-2">SL</th><th className="py-2 px-2">TP</th><th className="py-2 px-2">R:R</th><th className="py-2 px-2">Signal</th><th className="py-2 px-2">Actions</th>
              </tr></thead>
              <tbody>{positions.map((p, i) => (
                <tr key={i} className="border-b border-gray-800/50 hover:bg-gray-800/30">
                  <td className="py-2 px-2 text-white font-bold cursor-pointer hover:text-cyan-300" onClick={() => setSelectedTicker(p.ticker)}>{p.ticker}</td>
                  <td className="py-2 px-2"><span className={`px-1.5 py-0.5 rounded text-xs ${p.direction === 'LONG' ? 'bg-emerald-900/50 text-emerald-300' : 'bg-red-900/50 text-red-300'}`}>{p.direction}</span></td>
                  <td className="py-2 px-2 text-white font-mono">{p.qty}</td>
                  <td className="py-2 px-2 text-gray-300 font-mono">${p.avgEntry}</td>
                  <td className="py-2 px-2 text-white font-mono">${p.current}</td>
                  <td className={`py-2 px-2 font-mono font-bold ${p.pnl >= 0 ? 'text-emerald-300' : 'text-red-300'}`}>{p.pnl >= 0 ? '+' : ''}${p.pnl}</td>
                  <td className={`py-2 px-2 font-mono ${p.pnlPct >= 0 ? 'text-emerald-300' : 'text-red-300'}`}>{p.pnlPct >= 0 ? '+' : ''}{p.pnlPct}%</td>
                  <td className="py-2 px-2 text-red-400 font-mono">${p.stopLoss}</td>
                  <td className="py-2 px-2 text-emerald-400 font-mono">${p.takeProfit}</td>
                  <td className="py-2 px-2 text-cyan-300 font-mono">{p.riskReward}</td>
                  <td className="py-2 px-2 text-purple-300 text-xs">{p.signal}</td>
                  <td className="py-2 px-2"><div className="flex gap-1"><button className="px-1.5 py-0.5 text-xs bg-red-600/60 hover:bg-red-500 text-white rounded">Close</button><button className="px-1.5 py-0.5 text-xs bg-gray-700 hover:bg-gray-600 text-gray-300 rounded">Modify</button></div></td>
                </tr>
              ))}</tbody>
            </table>
          </div>
        </div>
      </GlassPanel>

      {/* ===== ML Insights + Advanced Orders Row ===== */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {/* ML Insights */}
        <GlassPanel title={`ML Insights for ${selectedTicker}`} icon="\u{1F9E0}" collapsed={!panels.mlInsights} onToggle={() => togglePanel('mlInsights')} maxHeight="300px" glowColor="purple">
          <div className="p-4 space-y-3">
            <div className="flex justify-between items-center">
              <span className="text-xs text-gray-400">Sentiment:</span>
              <span className="px-2 py-0.5 text-xs rounded-full bg-emerald-900/60 text-emerald-300 border border-emerald-500/20">Bullish</span>
            </div>
            <div className="flex justify-between items-center">
              <span className="text-xs text-gray-400">Confidence:</span>
              <span className="text-sm font-bold text-white font-mono">85%</span>
            </div>
            <div className="flex justify-between items-center">
              <span className="text-xs text-gray-400">Predicted Move:</span>
              <span className="text-sm font-bold text-emerald-300 font-mono">+2.3%</span>
            </div>
            <div className="flex justify-between items-center">
              <span className="text-xs text-gray-400">Time Horizon:</span>
              <span className="text-sm text-gray-300">4 hours</span>
            </div>
            <div className="bg-gray-800/40 rounded-lg p-3 border border-gray-700/30">
              <p className="text-xs text-gray-400">AI Analysis: Price increase expected based on momentum indicators, volume profile, and options flow analysis. Support at $148, resistance at $155.</p>
            </div>
            <p className="text-xs text-gray-600 italic">OLEH: Connect to /api/v1/ml/predict endpoint</p>
          </div>
        </GlassPanel>

        {/* Advanced Order Settings */}
        <GlassPanel title="Advanced Order Settings" icon="\u{2699}" collapsed={!panels.advancedOrders} onToggle={() => togglePanel('advancedOrders')} maxHeight="300px" glowColor="amber">
          <div className="p-4 space-y-4">
            {/* Bracket Orders OCO */}
            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <span className="text-xs font-bold text-gray-300">Bracket Orders (OCO)</span>
                <button onClick={() => setBracketEnabled(!bracketEnabled)} className={`w-10 h-5 rounded-full transition-colors ${bracketEnabled ? 'bg-cyan-600' : 'bg-gray-600'}`}>
                  <div className={`w-4 h-4 bg-white rounded-full transition-transform ${bracketEnabled ? 'translate-x-5' : 'translate-x-0.5'}`} />
                </button>
              </div>
              {bracketEnabled && (
                <div className="grid grid-cols-2 gap-2">
                  <div>
                    <label className="text-xs text-gray-500">Take Profit %</label>
                    <input type="number" step="0.1" value={takeProfitPct} onChange={e => setTakeProfitPct(Number(e.target.value))} className="w-full bg-gray-800/80 border border-gray-600/50 rounded-lg px-2 py-1.5 text-xs text-white font-mono focus:border-emerald-500 focus:outline-none" />
                  </div>
                  <div>
                    <label className="text-xs text-gray-500">Stop Loss %</label>
                    <input type="number" step="0.1" value={stopLossPct} onChange={e => setStopLossPct(Number(e.target.value))} className="w-full bg-gray-800/80 border border-gray-600/50 rounded-lg px-2 py-1.5 text-xs text-white font-mono focus:border-red-500 focus:outline-none" />
                  </div>
                </div>
              )}
            </div>
            {/* Trailing Stop */}
            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <span className="text-xs font-bold text-gray-300">Trailing Stop</span>
                <button onClick={() => setTrailingStop(!trailingStop)} className={`w-10 h-5 rounded-full transition-colors ${trailingStop ? 'bg-cyan-600' : 'bg-gray-600'}`}>
                  <div className={`w-4 h-4 bg-white rounded-full transition-transform ${trailingStop ? 'translate-x-5' : 'translate-x-0.5'}`} />
                </button>
              </div>
              {trailingStop && (
                <div>
                  <label className="text-xs text-gray-500">Trail %</label>
                  <input type="number" step="0.1" value={trailingPct} onChange={e => setTrailingPct(Number(e.target.value))} className="w-full bg-gray-800/80 border border-gray-600/50 rounded-lg px-2 py-1.5 text-xs text-white font-mono focus:border-cyan-500 focus:outline-none" />
                </div>
              )}
            </div>
            {/* Time in Force */}
            <div>
              <label className="text-xs font-bold text-gray-300 block mb-1">Time in Force</label>
              <select value={timeInForce} onChange={e => setTimeInForce(e.target.value)} className="w-full bg-gray-800/80 border border-gray-600/50 rounded-lg px-2 py-1.5 text-xs text-white focus:border-cyan-500 focus:outline-none">
                <option value="DAY">Day</option>
                <option value="GTC">Good Till Cancelled</option>
                <option value="IOC">Immediate or Cancel</option>
                <option value="FOK">Fill or Kill</option>
              </select>
            </div>
          </div>
        </GlassPanel>
      </div>

      {/* ===== Detailed Execution Logs ===== */}
      <GlassPanel title="Detailed Execution Logs" icon="\u{1F4CB}" collapsed={!panels.history} onToggle={() => togglePanel('history')} badge={`${tradeHistory.length} trades`} maxHeight="500px" glowColor="yellow"
        headerActions={
          <div className="flex gap-1 mr-2">
            {['ALL','FILLED','CANCELLED','PENDING'].map(s => (
              <button key={s} onClick={(e) => { e.stopPropagation(); setFilterStatus(s); }} className={`px-2 py-0.5 text-xs rounded transition-colors ${filterStatus === s ? 'bg-cyan-600/80 text-white' : 'bg-gray-700/60 text-gray-400 hover:bg-gray-600/60'}`}>{s}</button>
            ))}
          </div>
        }>
        <div className="p-3">
          <div className="overflow-x-auto">
            <table className="w-full text-xs">
              <thead><tr className="text-gray-400 border-b border-gray-700">
                <th className="py-2 px-2 text-left">Time</th><th className="py-2 px-2">Symbol</th><th className="py-2 px-2">Type</th><th className="py-2 px-2">Side</th><th className="py-2 px-2">Qty</th><th className="py-2 px-2">Price</th><th className="py-2 px-2">P&L</th><th className="py-2 px-2">Fees</th><th className="py-2 px-2">Fill Time</th><th className="py-2 px-2">Slippage</th><th className="py-2 px-2">Status</th>
              </tr></thead>
              <tbody>{filteredHistory.map((t) => (
                <tr key={t.id} className="border-b border-gray-800/50 hover:bg-gray-800/30">
                  <td className="py-2 px-2 text-gray-300 font-mono">{t.time}</td>
                  <td className="py-2 px-2 text-white font-bold cursor-pointer hover:text-cyan-300" onClick={() => setSelectedTicker(t.ticker)}>{t.ticker}</td>
                  <td className="py-2 px-2 text-gray-400 capitalize">{t.ordType}</td>
                  <td className="py-2 px-2"><span className={`px-1.5 py-0.5 rounded text-xs ${t.direction === 'BUY' ? 'bg-emerald-900/50 text-emerald-300' : 'bg-red-900/50 text-red-300'}`}>{t.direction}</span></td>
                  <td className="py-2 px-2 text-white font-mono">{t.qty}</td>
                  <td className="py-2 px-2 text-white font-mono">${t.price.toFixed(2)}</td>
                  <td className={`py-2 px-2 font-mono ${t.pnl === null ? 'text-gray-500' : t.pnl >= 0 ? 'text-emerald-300' : 'text-red-300'}`}>{t.pnl === null ? '-' : `${t.pnl >= 0 ? '+' : ''}$${t.pnl}`}</td>
                  <td className="py-2 px-2 text-amber-300 font-mono">${t.fees.toFixed(2)}</td>
                  <td className="py-2 px-2 text-gray-300 font-mono">{t.fillTime}</td>
                  <td className="py-2 px-2 text-gray-300 font-mono">${t.slippage.toFixed(2)}</td>
                  <td className="py-2 px-2"><span className={`px-1.5 py-0.5 rounded text-xs ${t.status === 'filled' ? 'bg-emerald-900/50 text-emerald-300' : t.status === 'cancelled' ? 'bg-red-900/50 text-red-300' : 'bg-yellow-900/50 text-yellow-300'}`}>{t.status}</span></td>
                </tr>
              ))}</tbody>
            </table>
          </div>
        </div>
      </GlassPanel>

    </div>
  );
}
