import React from 'react';
import { useState, useEffect, useRef } from 'react';
import { useRealtimeSignals } from '../../hooks/useRealtimeSignals';
import CandidateCard from './CandidateCard';
import LiveAnalysisHeader from './LiveAnalysisHeader';
import WatchlistPanel from './WatchlistPanel';
import './IntelligenceRadar.css';

const IntelligenceRadar = () => {
  const { signals, loading, error } = useRealtimeSignals();
  const [activeTab, setActiveTab] = useState<'signals' | 'watchlist'>('signals');
  const [isPaused, setIsPaused] = useState(false);
  const [scrollIndex, setScrollIndex] = useState(0);
  const scrollRef = useRef<HTMLDivElement>(null);

  // Auto-scroll every 3 seconds
  useEffect(() => {
    if (isPaused || activeTab !== 'signals' || signals.length === 0) return;

    const interval = setInterval(() => {
      setScrollIndex((prev) => {
        const next = (prev + 1) % signals.length;
        
        // Smooth scroll to next card
        if (scrollRef.current) {
          const cardHeight = 140; // Approximate card height
          scrollRef.current.scrollTo({
            top: next * cardHeight,
            behavior: 'smooth'
          });
        }
        
        return next;
      });
    }, 3000);

    return () => clearInterval(interval);
  }, [isPaused, activeTab, signals.length]);

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
        
        {activeTab === 'signals' && (
          <button 
            className="pause-btn"
            onClick={() => setIsPaused(!isPaused)}
            title={isPaused ? 'Resume auto-scroll' : 'Pause auto-scroll'}
          >
            {isPaused ? '▶️' : '⏸️'}
          </button>
        )}
      </div>

      {activeTab === 'signals' ? (
        <>
          <LiveAnalysisHeader />
          <div className="candidate-stream" ref={scrollRef}>
            {signals.length === 0 ? (
              <div className="no-signals">
                <p>No signals available</p>
              </div>
            ) : (
              signals.slice(0, 25).map((signal, index) => (
                <CandidateCard 
                  key={signal.id} 
                  candidate={signal}
                  isActive={index === scrollIndex && !isPaused}
                />
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

