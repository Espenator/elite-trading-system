import React from 'react';
import React, { useState, useEffect } from 'react';
import './LoadingStates.css';

// Chart Loading Skeleton
export const ChartSkeleton: React.FC<{ symbol: string }> = ({ symbol }) => {
  return (
    <div className="chart-skeleton">
      <div className="skeleton-header">
        <div className="skeleton-pulse skeleton-text-lg" style={{ width: '120px' }} />
        <div className="skeleton-pulse skeleton-text-sm" style={{ width: '80px' }} />
      </div>
      
      <div className="skeleton-chart-area">
        <div className="skeleton-pulse skeleton-chart" />
        <span className="loading-message">Loading {symbol} chart data...</span>
      </div>
      
      <div className="skeleton-footer">
        {[1, 2, 3, 4].map(i => (
          <div key={i} className="skeleton-pulse skeleton-button" />
        ))}
      </div>
    </div>
  );
};

// Trade Success Animation
export const TradeSuccessAnimation: React.FC<{ 
  symbol: string;
  quantity: number;
  price: number;
  onComplete: () => void;
}> = ({ symbol, quantity, price, onComplete }) => {
  useEffect(() => {
    const timer = setTimeout(onComplete, 2000);
    return () => clearTimeout(timer);
  }, [onComplete]);

  return (
    <div className="trade-success-overlay">
      <div className="trade-success-card">
        <div className="success-icon success-check">
          <svg viewBox="0 0 24 24" width="48" height="48">
            <path 
              fill="#10b981" 
              d="M9 16.17L4.83 12l-1.42 1.41L9 19 21 7l-1.41-1.41L9 16.17z"
            />
          </svg>
        </div>
        
        <h3 className="success-title">Trade Executed!</h3>
        
        <div className="success-details">
          <p>Bought {quantity} shares of {symbol}</p>
          <p className="success-price">${price.toFixed(2)}</p>
        </div>
        
        <div className="confetti">
          {[...Array(12)].map((_, i) => (
            <div key={i} className={`confetti-piece confetti-${i}`} />
          ))}
        </div>
      </div>
    </div>
  );
};

// Error State with Retry
export const ErrorState: React.FC<{
  message: string;
  details?: string;
  onRetry?: () => void;
  onDismiss?: () => void;
}> = ({ message, details, onRetry, onDismiss }) => {
  return (
    <div className="error-state">
      <div className="error-icon">⚠️</div>
      <h4 className="error-title">{message}</h4>
      {details && <p className="error-details">{details}</p>}
      
      <div className="error-actions">
        {onRetry && (
          <button className="error-btn error-btn-retry" onClick={onRetry}>
            🔄 Retry
          </button>
        )}
        {onDismiss && (
          <button className="error-btn error-btn-dismiss" onClick={onDismiss}>
            Dismiss
          </button>
        )}
      </div>
    </div>
  );
};

// Scroll Position Indicator
export const ScrollIndicator: React.FC<{
  current: number;
  total: number;
  label?: string;
}> = ({ current, total, label = 'Showing' }) => {
  const percentage = (current / total) * 100;
  
  return (
    <div className="scroll-indicator">
      <span className="scroll-label">
        {label} {current} of {total}
      </span>
      <div className="scroll-bar">
        <div 
          className="scroll-progress" 
          style={{ width: `${percentage}%` }}
        />
      </div>
    </div>
  );
};

// Loading Dots
export const LoadingDots: React.FC = () => {
  return (
    <div className="loading-dots">
      <span className="dot dot-1">•</span>
      <span className="dot dot-2">•</span>
      <span className="dot dot-3">•</span>
    </div>
  );
};

// API Connection Status
export const APIStatus: React.FC<{
  service: string;
  status: 'connected' | 'degraded' | 'failed';
  lastUpdate?: string;
}> = ({ service, status, lastUpdate }) => {
  const statusConfig = {
    connected: { icon: '🟢', label: 'Connected', color: '#10b981' },
    degraded: { icon: '🟡', label: 'Degraded', color: '#fbbf24' },
    failed: { icon: '🔴', label: 'Failed', color: '#ef4444' },
  };

  const config = statusConfig[status];

  return (
    <div className="api-status">
      <span className="api-icon">{config.icon}</span>
      <div className="api-info">
        <span className="api-service">{service}</span>
        <span className="api-label" style={{ color: config.color }}>
          {config.label}
        </span>
      </div>
      {lastUpdate && (
        <span className="api-update">{lastUpdate}</span>
      )}
    </div>
  );
};

