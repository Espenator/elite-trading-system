import { useEffect, useState } from 'react';

export default function LiveSignalFeed({ onSelectSymbol }) {
  const [signals, setSignals] = useState([]);
  const [isPaused, setIsPaused] = useState(false);
  const [connectionStatus, setConnectionStatus] = useState('connecting');

  useEffect(() => {
    let ws = null;
    let reconnectTimeout;
    
    const connect = () => {
      try {
        setConnectionStatus('connecting');
        ws = new WebSocket('ws://localhost:8000/ws');
        
        ws.onopen = () => {
          console.log('✅ WebSocket Connected to signal feed');
          setConnectionStatus('connected');
        };
        
        ws.onclose = () => {
          console.log('❌ WebSocket Disconnected');
          setConnectionStatus('disconnected');
          // Attempt to reconnect after 3 seconds
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
            
            // Handle different message types
            if (message.type === 'signals_update' && message.signals) {
              // Full signals update from scanner
              console.log(`📊 Received ${message.signals.length} signals`);
              
              const formattedSignals = message.signals.map((sig, index) => ({
                id: `sig_${Date.now()}_${index}`,
                time: sig.timestamp ? new Date(sig.timestamp).toLocaleTimeString() : new Date().toLocaleTimeString(),
                ticker: sig.symbol || sig.ticker || 'N/A',
                tier: sig.composite_score ? 
                  (sig.composite_score >= 80 ? 'T1' : sig.composite_score >= 60 ? 'T2' : 'T3') : 
                  sig.tier || 'T3',
                score: sig.composite_score || sig.score || 0,
                aiConf: sig.composite_score || sig.aiConf || 0,
                rvol: sig.volume_ratio || sig.rvol || 1.0,
                catalyst: sig.catalyst || 'Signal detected'
              }));
              
              setSignals(formattedSignals);
            }
            else if (message.type === 'new_signal' && message.signal) {
              // Individual signal update
              const sig = message.signal;
              const newSignal = {
                id: `sig_${Date.now()}`,
                time: sig.timestamp ? new Date(sig.timestamp).toLocaleTimeString() : new Date().toLocaleTimeString(),
                ticker: sig.symbol || sig.ticker || 'N/A',
                tier: sig.composite_score ? 
                  (sig.composite_score >= 80 ? 'T1' : sig.composite_score >= 60 ? 'T2' : 'T3') : 
                  sig.tier || 'T3',
                score: sig.composite_score || sig.score || 0,
                aiConf: sig.composite_score || sig.aiConf || 0,
                rvol: sig.volume_ratio || sig.rvol || 1.0,
                catalyst: sig.catalyst || 'Signal detected'
              };
              
              setSignals(prev => [newSignal, ...prev].slice(0, 100));
            }
            else if (message.type === 'connection') {
              console.log('✅ Connection confirmed:', message.message);
            }
            else if (message.type === 'scan_complete') {
              console.log('✅ Scan complete');
            }
            else if (message.type === 'status') {
              console.log('ℹ️ Status:', message.message);
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

  const handleClearSignals = () => {
    setSignals([]);
  };

  return (
    <div className="live-signal-feed">
      <div className="feed-header">
        <h2 className="feed-title">
          {connectionStatus === 'connected' ? '🟢' : connectionStatus === 'connecting' ? '🟡' : '🔴'}
          {' '}LIVE SIGNAL FEED
        </h2>
        <div className="feed-controls">
          <span className="signal-count">{signals.length} signals</span>
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
              <th>TIME</th>
              <th>TICKER</th>
              <th>TIER</th>
              <th>SCORE</th>
              <th>AI CONF</th>
              <th>RVOL</th>
              <th>CATALYST</th>
            </tr>
          </thead>
          <tbody>
            {signals.length === 0 ? (
              <tr className="empty-row">
                <td colSpan={7}>
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
              signals.map(signal => (
                <tr 
                  key={signal.id}
                  className="feed-row"
                  onClick={() => onSelectSymbol(signal.ticker || 'SPY')}
                >
                  <td className="time-cell">{signal.time || '-'}</td>
                  <td className="ticker-cell">{signal.ticker || '-'}</td>
                  <td>
                    <span className={`tier-badge ${(signal.tier || 'default').toLowerCase()}`}>
                      {signal.tier || 'N/A'}
                    </span>
                  </td>
                  <td className="score-cell">{signal.score ? signal.score.toFixed(1) : '-'}</td>
                  <td className="conf-cell">{signal.aiConf ? `${signal.aiConf.toFixed(0)}%` : '-'}</td>
                  <td className="rvol-cell">{signal.rvol ? `${signal.rvol.toFixed(1)}x` : '-'}</td>
                  <td className="catalyst-cell">{signal.catalyst || '-'}</td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}

