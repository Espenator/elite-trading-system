import { useEffect, useState } from 'react';

export default function LiveSignalFeed({ onSelectSymbol }) {
  const [signals, setSignals] = useState([]);
  const [isPaused, setIsPaused] = useState(false);
  const [connectionStatus, setConnectionStatus] = useState('connecting');
  const [sortConfig, setSortConfig] = useState({ key: 'score', direction: 'desc' });
  const [filterTier, setFilterTier] = useState('all'); // all, T1, T2, T3
  const [filterType, setFilterType] = useState('all'); // all, MOMENTUM, VOLUME_SPIKE, RSI, etc

  useEffect(() => {
    let ws = null;
    let reconnectTimeout;
    
    const connect = () => {
      try {
        setConnectionStatus('connecting');
        const wsHost = (import.meta.env.VITE_API_BASE_URL || 'http://localhost:8001/api/v1').replace(/^https/, 'wss').replace(/^http/, 'ws').replace(/\/api\/v1.*/, '') || 'ws://localhost:8001';
        ws = new WebSocket(`${wsHost}/ws`);
        
        ws.onopen = () => {
          console.log('✅ WebSocket Connected to signal feed');
          setConnectionStatus('connected');
        };
        
        ws.onclose = () => {
          console.log('❌ WebSocket Disconnected');
          setConnectionStatus('disconnected');
          reconnectTimeout = setTimeout(() => {
            console.log('🔄 Attempting to reconnect signal feed...');
            connect();
          }, 3000);
        };
        
        ws.onerror = (error) => {
          console.error('WebSocket Error:', error);
          setConnectionStatus('error');
        };
        
        ws.onmessage = (event) => {
          if (isPaused) return;
          
          try {
            const message = JSON.parse(event.data);
            console.log('📡 Received message:', message.type);
            
            if (message.type === 'signals_update' && message.signals) {
              console.log(`📊 Received ${message.signals.length} signals`);
              
              const formattedSignals = message.signals.map((sig, index) => ({
                id: `sig_${Date.now()}_${index}`,
                time: sig.timestamp ? new Date(sig.timestamp).toLocaleTimeString() : new Date().toLocaleTimeString(),
                ticker: sig.symbol || sig.ticker || 'N/A',
                tier: sig.tier || (sig.composite_score ? 
                  (sig.composite_score >= 80 ? 'T1' : sig.composite_score >= 60 ? 'T2' : 'T3') : 'T3'),
                score: sig.composite_score || sig.score || 0,
                aiConf: sig.composite_score || sig.aiConf || 0,
                rvol: sig.volume_ratio || sig.rvol || 1.0,
                catalyst: sig.catalyst || 'Signal detected',
                signalType: sig.signal_type || 'MOMENTUM',
                rsi: sig.rsi || 50,
                momentum: sig.momentum || 0,
                vwap: sig.vwap || 0,
                vwapDist: sig.vwap_distance !== undefined ? sig.vwap_distance : 0,
                entryPrice: sig.entry_price || 0,
                stopPrice: sig.stop_price || 0,
                targetPrice: sig.target_price || 0,
                riskReward: sig.risk_reward || 1.0
              }));
              
              setSignals(formattedSignals);
            }
            else if (message.type === 'new_signal' && message.signal) {
              const sig = message.signal;
              const newSignal = {
                id: `sig_${Date.now()}`,
                time: sig.timestamp ? new Date(sig.timestamp).toLocaleTimeString() : new Date().toLocaleTimeString(),
                ticker: sig.symbol || sig.ticker || 'N/A',
                tier: sig.tier || (sig.composite_score ? 
                  (sig.composite_score >= 80 ? 'T1' : sig.composite_score >= 60 ? 'T2' : 'T3') : 'T3'),
                score: sig.composite_score || sig.score || 0,
                aiConf: sig.composite_score || sig.aiConf || 0,
                rvol: sig.volume_ratio || sig.rvol || 1.0,
                catalyst: sig.catalyst || 'Signal detected',
                signalType: sig.signal_type || 'MOMENTUM',
                rsi: sig.rsi || 50,
                momentum: sig.momentum || 0,
                vwap: sig.vwap || 0,
                vwapDist: sig.vwap_distance !== undefined ? sig.vwap_distance : 0,
                entryPrice: sig.entry_price || 0,
                stopPrice: sig.stop_price || 0,
                targetPrice: sig.target_price || 0,
                riskReward: sig.risk_reward || 1.0
              };
              
              setSignals(prev => [newSignal, ...prev].slice(0, 100));
            }
            else if (message.type === 'connection') {
              console.log('✅ Connection confirmed:', message.message);
            }
            else if (message.type === 'scan_complete') {
              console.log('✅ Scan complete');
            }
          } catch (err) {
            console.error('Error parsing signal:', err);
          }
        };
      } catch (error) {
        console.error('Failed to create WebSocket:', error);
        setConnectionStatus('error');
      }
    };

    connect();

    return () => {
      if (reconnectTimeout) clearTimeout(reconnectTimeout);
      if (ws) ws.close();
    };
  }, [isPaused]);

  // ==================== SORTING ====================
  const sortedAndFilteredSignals = () => {
    let filtered = signals;
    
    // Apply tier filter
    if (filterTier !== 'all') {
      filtered = filtered.filter(s => s.tier === filterTier);
    }
    
    // Apply signal type filter
    if (filterType !== 'all') {
      filtered = filtered.filter(s => s.signalType === filterType);
    }
    
    // Apply sorting
    const sorted = [...filtered].sort((a, b) => {
      const aVal = a[sortConfig.key];
      const bVal = b[sortConfig.key];
      
      if (typeof aVal === 'number' && typeof bVal === 'number') {
        return sortConfig.direction === 'asc' ? aVal - bVal : bVal - aVal;
      }
      
      return sortConfig.direction === 'asc' ? 
        String(aVal).localeCompare(String(bVal)) : 
        String(bVal).localeCompare(String(aVal));
    });
    
    return sorted;
  };

  const handleSort = (key) => {
    setSortConfig(prev => ({
      key,
      direction: prev.key === key && prev.direction === 'desc' ? 'asc' : 'desc'
    }));
  };

  // ==================== QUICK TRADE ====================
  const handleQuickTrade = (ticker, entryPrice, quantity) => {
    const toast = document.createElement('div');
    toast.className = 'trade-toast';
    toast.textContent = `✓ BUY ${quantity} ${ticker} @ $${entryPrice.toFixed(2)}`;
    document.body.appendChild(toast);
    
    setTimeout(() => {
      toast.classList.add('fade-out');
      setTimeout(() => toast.remove(), 300);
    }, 3000);
    
    // TODO: Call actual trade execution API
    console.log(`Execute: BUY ${quantity} ${ticker} @ $${entryPrice}`);
  };

  // ==================== HELPERS ====================
  const getSignalTypeBadge = (type) => {
    const types = {
      'MOMENTUM': { color: '#00c8ff', bg: 'rgba(0, 200, 255, 0.15)' },
      'VOLUME_SPIKE': { color: '#c864ff', bg: 'rgba(200, 100, 255, 0.15)' },
      'RSI_OVERSOLD': { color: '#00ff88', bg: 'rgba(0, 255, 136, 0.15)' },
      'RSI_OVERBOUGHT': { color: '#ff5459', bg: 'rgba(255, 84, 89, 0.15)' },
      'MACD': { color: '#ffa500', bg: 'rgba(255, 165, 0, 0.15)' }
    };
    return types[type] || { color: '#aaa', bg: 'rgba(100, 100, 100, 0.15)' };
  };

  const getRSIColor = (rsi) => {
    if (rsi > 70) return '#ff5459'; // Red - overbought
    if (rsi < 30) return '#00ff88'; // Green - oversold
    return '#e68161'; // Orange - neutral
  };

  const getMomentumColor = (momentum) => {
    return momentum > 0 ? '#00ff88' : momentum < 0 ? '#ff5459' : '#aaa';
  };

  const getVWAPColor = (vwapDist) => {
    return vwapDist > 0 ? '#00ff88' : vwapDist < 0 ? '#ff5459' : '#aaa';
  };

  const getRRColor = (rr) => {
    if (rr > 1.5) return '#00ff88'; // Green - excellent
    if (rr > 1.0) return '#e68161'; // Orange - good
    return '#ff5459'; // Red - poor
  };

  const formatPrice = (price) => {
    return price ? `$${price.toFixed(2)}` : '-';
  };

  const handleClearSignals = () => {
    setSignals([]);
  };

  const displaySignals = sortedAndFilteredSignals();

  return (
    <div className="live-signal-feed">
      <div className="feed-header">
        <h2 className="feed-title">
          {connectionStatus === 'connected' ? '🟢' : connectionStatus === 'connecting' ? '🟡' : '🔴'}
          {' '}LIVE SIGNAL FEED - INSTITUTIONAL GRADE
        </h2>
        <div className="feed-controls">
          <span className="signal-count">{displaySignals.length} signals</span>
          
          {/* Tier Filter */}
          <select 
            value={filterTier} 
            onChange={(e) => setFilterTier(e.target.value)}
            className="filter-select"
          >
            <option value="all">All Tiers</option>
            <option value="T1">T1 Only</option>
            <option value="T2">T2 Only</option>
            <option value="T3">T3 Only</option>
          </select>
          
          {/* Signal Type Filter */}
          <select 
            value={filterType} 
            onChange={(e) => setFilterType(e.target.value)}
            className="filter-select"
          >
            <option value="all">All Types</option>
            <option value="MOMENTUM">Momentum</option>
            <option value="VOLUME_SPIKE">Volume Spike</option>
            <option value="RSI_OVERSOLD">RSI Oversold</option>
            <option value="RSI_OVERBOUGHT">RSI Overbought</option>
          </select>
          
          <button 
            className="feed-control-btn"
            onClick={() => setIsPaused(!isPaused)}
          >
            {isPaused ? '▶ Resume' : '⏸ Pause'}
          </button>
          <button 
            className="feed-control-btn"
            onClick={handleClearSignals}
          >
            🗑️ Clear
          </button>
        </div>
      </div>

      <div className="feed-table-container">
        <table className="feed-table">
          <thead>
            <tr>
              <th onClick={() => handleSort('time')} className="sortable">TIME {sortConfig.key === 'time' && (sortConfig.direction === 'asc' ? '↑' : '↓')}</th>
              <th onClick={() => handleSort('ticker')} className="sortable">TICKER {sortConfig.key === 'ticker' && (sortConfig.direction === 'asc' ? '↑' : '↓')}</th>
              <th onClick={() => handleSort('tier')} className="sortable">TIER {sortConfig.key === 'tier' && (sortConfig.direction === 'asc' ? '↑' : '↓')}</th>
              <th onClick={() => handleSort('score')} className="sortable">SCORE {sortConfig.key === 'score' && (sortConfig.direction === 'asc' ? '↑' : '↓')}</th>
              <th onClick={() => handleSort('signalType')} className="sortable">SIGNAL TYPE {sortConfig.key === 'signalType' && (sortConfig.direction === 'asc' ? '↑' : '↓')}</th>
              <th onClick={() => handleSort('rsi')} className="sortable">RSI {sortConfig.key === 'rsi' && (sortConfig.direction === 'asc' ? '↑' : '↓')}</th>
              <th onClick={() => handleSort('momentum')} className="sortable">MOMENTUM {sortConfig.key === 'momentum' && (sortConfig.direction === 'asc' ? '↑' : '↓')}</th>
              <th onClick={() => handleSort('vwapDist')} className="sortable">VWAP DIST {sortConfig.key === 'vwapDist' && (sortConfig.direction === 'asc' ? '↑' : '↓')}</th>
              <th onClick={() => handleSort('entryPrice')} className="sortable">ENTRY {sortConfig.key === 'entryPrice' && (sortConfig.direction === 'asc' ? '↑' : '↓')}</th>
              <th onClick={() => handleSort('riskReward')} className="sortable">R:R {sortConfig.key === 'riskReward' && (sortConfig.direction === 'asc' ? '↑' : '↓')}</th>
              <th>CATALYST</th>
              <th>ACTIONS</th>
            </tr>
          </thead>
          <tbody>
            {displaySignals.length === 0 ? (
              <tr className="empty-row">
                <td colSpan={12}>
                  <div className="feed-empty-state">
                    {connectionStatus === 'connected' ? (
                      <p>✅ Connected - Waiting for signals...</p>
                    ) : connectionStatus === 'connecting' ? (
                      <p>🟡 Connecting to backend...</p>
                    ) : (
                      <p>❌ Connection error - Check backend is running</p>
                    )}
                  </div>
                </td>
              </tr>
            ) : (
              displaySignals.map(signal => {
                const typeBadge = getSignalTypeBadge(signal.signalType);
                return (
                  <tr key={signal.id} className="feed-row">
                    <td className="time-cell">{signal.time || '-'}</td>
                    <td className="ticker-cell" onClick={() => onSelectSymbol(signal.ticker || 'SPY')}>
                      <strong>{signal.ticker || '-'}</strong>
                    </td>
                    <td>
                      <span className={`tier-badge ${(signal.tier || 'default').toLowerCase()}`}>
                        {signal.tier || 'N/A'}
                      </span>
                    </td>
                    <td className="score-cell">
                      <span className={`score-badge score-${signal.score >= 80 ? 'high' : signal.score >= 60 ? 'medium' : 'low'}`}>
                        {signal.score ? signal.score.toFixed(0) : '-'}
                      </span>
                    </td>
                    <td>
                      <span 
                        className="signal-type-badge" 
                        style={{ color: typeBadge.color, backgroundColor: typeBadge.bg }}
                      >
                        {signal.signalType || 'N/A'}
                      </span>
                    </td>
                    <td className="rsi-cell">
                      <span style={{ color: getRSIColor(signal.rsi) }}>
                        {signal.rsi ? signal.rsi.toFixed(0) : '-'}
                      </span>
                    </td>
                    <td className="momentum-cell">
                      <span style={{ color: getMomentumColor(signal.momentum), fontWeight: '600' }}>
                        {signal.momentum > 0 ? '+' : ''}{signal.momentum ? signal.momentum.toFixed(2) : '-'}%
                      </span>
                    </td>
                    <td className="vwap-cell">
                      <span style={{ color: getVWAPColor(signal.vwapDist), fontWeight: '600' }}>
                        {signal.vwapDist > 0 ? '+' : ''}{signal.vwapDist ? signal.vwapDist.toFixed(2) : '-'}
                      </span>
                    </td>
                    <td className="entry-cell">{formatPrice(signal.entryPrice)}</td>
                    <td className="rr-cell">
                      <span 
                        style={{ 
                          color: getRRColor(signal.riskReward),
                          fontWeight: '700'
                        }}
                      >
                        {signal.riskReward ? signal.riskReward.toFixed(2) : '-'}
                      </span>
                    </td>
                    <td className="catalyst-cell" title={signal.catalyst}>
                      {signal.catalyst ? signal.catalyst.substring(0, 30) : '-'}...
                    </td>
                    <td className="actions-cell">
                      <div className="action-buttons">
                        <button 
                          className="trade-btn buy-100"
                          onClick={() => handleQuickTrade(signal.ticker, signal.entryPrice, 100)}
                          title="Buy 100 shares"
                        >
                          100
                        </button>
                        <button 
                          className="trade-btn buy-500"
                          onClick={() => handleQuickTrade(signal.ticker, signal.entryPrice, 500)}
                          title="Buy 500 shares"
                        >
                          500
                        </button>
                      </div>
                    </td>
                  </tr>
                );
              })
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
