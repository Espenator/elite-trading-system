import { useState } from 'react';
import { useRealtimeSignals } from '../../hooks/useRealtimeSignals';
import CandidateCard from './CandidateCard';
import LiveAnalysisHeader from './LiveAnalysisHeader';
import WatchlistPanel from './WatchlistPanel';
import './IntelligenceRadar.css';

const IntelligenceRadar = () => {
  const { signals, loading, error } = useRealtimeSignals();
  const [activeTab, setActiveTab] = useState<'signals' | 'watchlist'>('signals');

  if (loading) {
    return (
      <div className="intelligence-radar">
        <div className="radar-loading">
          <div className="loading-spinner"></div>
          <p>Connecting to backend...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="intelligence-radar">
        <div className="radar-error">
          <p>⚠️ Backend connection failed</p>
          <p className="error-detail">{error}</p>
        </div>
      </div>
    );
  }

  return (
    <div className="intelligence-radar">
      <div className="radar-tabs">
        <button 
          className={`tab-btn ${activeTab === 'signals' ? 'active' : ''}`}
          onClick={() => setActiveTab('signals')}
        >
          🤖 AI Signals
        </button>
        <button 
          className={`tab-btn ${activeTab === 'watchlist' ? 'active' : ''}`}
          onClick={() => setActiveTab('watchlist')}
        >
          ⭐ Watchlist
        </button>
      </div>

      {activeTab === 'signals' ? (
        <>
          <LiveAnalysisHeader />
          <div className="candidate-stream">
            {signals.length === 0 ? (
              <div className="no-signals">
                <p>No signals available</p>
              </div>
            ) : (
              signals.slice(0, 25).map((signal) => (
                <CandidateCard key={signal.id} candidate={signal} />
              ))
            )}
          </div>
        </>
      ) : (
        <WatchlistPanel />
      )}
    </div>
  );
};

export default IntelligenceRadar;
