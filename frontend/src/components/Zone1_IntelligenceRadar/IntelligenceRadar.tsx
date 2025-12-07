import { useRealtimeSignals } from '../../hooks/useRealtimeSignals';
import CandidateCard from './CandidateCard';
import LiveAnalysisHeader from './LiveAnalysisHeader';
import './IntelligenceRadar.css';

const IntelligenceRadar = () => {
  const { signals, loading, error } = useRealtimeSignals();

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
          <p className="error-hint">Make sure backend is running on port 8000</p>
        </div>
      </div>
    );
  }

  return (
    <div className="intelligence-radar">
      <LiveAnalysisHeader />
      <div className="candidate-stream">
        {signals.length === 0 ? (
          <div className="no-signals">
            <p>No signals available</p>
            <p className="hint">Waiting for trading signals...</p>
          </div>
        ) : (
          signals.map((signal) => (
            <CandidateCard key={signal.id} candidate={signal} />
          ))
        )}
      </div>
    </div>
  );
};

export default IntelligenceRadar;
