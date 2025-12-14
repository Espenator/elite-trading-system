import React, { useState, useEffect } from 'react';
import { Bell, X, Filter, CheckCircle, AlertTriangle, XCircle, DollarSign, Brain } from 'lucide-react';

/**
 * Smart Notification Center - Bloomberg Terminal-style alert system
 * 
 * Features:
 * - Real-time WebSocket alerts
 * - Priority-based filtering
 * - Audio alerts for critical events
 * - Actionable notifications
 * - Auto-dismiss for info-level alerts
 */

class AudioAlertSystem {
  constructor() {
    this.sounds = new Map();
    this.enabled = true;
    this.loadSounds();
  }

  loadSounds() {
    const soundMap = {
      't1_signal': '/sounds/chime.mp3',
      'risk_breach': '/sounds/alert.mp3',
      'trade_closed': '/sounds/cash.mp3',
      'position_opened': '/sounds/ding.mp3'
    };

    Object.entries(soundMap).forEach(([key, path]) => {
      const audio = new Audio(path);
      audio.preload = 'auto';
      this.sounds.set(key, audio);
    });
  }

  play(soundKey, volume = 0.5) {
    if (!this.enabled) return;
    
    const sound = this.sounds.get(soundKey);
    if (sound) {
      sound.volume = Math.min(1, Math.max(0, volume));
      sound.currentTime = 0;
      sound.play().catch(err => console.warn('Audio play failed:', err));
    }
  }

  setEnabled(enabled) {
    this.enabled = enabled;
  }
}

const audioAlerts = new AudioAlertSystem();

const AlertIcon = ({ type }) => {
  const icons = {
    signal: <DollarSign className="text-teal-400" size={20} />,
    risk: <AlertTriangle className="text-red-400" size={20} />,
    trade: <DollarSign className="text-green-400" size={20} />,
    ml: <Brain className="text-purple-400" size={20} />
  };
  return icons[type] || <Bell size={20} />;
};

const AlertItem = ({ alert, onDismiss, onAction }) => {
  const getSeverityStyles = (severity) => {
    const styles = {
      critical: 'border-l-4 border-red-500 bg-red-500/10',
      warning: 'border-l-4 border-yellow-500 bg-yellow-500/10',
      info: 'border-l-4 border-teal-500 bg-teal-500/10'
    };
    return styles[severity] || styles.info;
  };

  const formatTimeAgo = (timestamp) => {
    const seconds = Math.floor((new Date() - new Date(timestamp)) / 1000);
    if (seconds < 60) return `${seconds}s ago`;
    if (seconds < 3600) return `${Math.floor(seconds / 60)}m ago`;
    if (seconds < 86400) return `${Math.floor(seconds / 3600)}h ago`;
    return `${Math.floor(seconds / 86400)}d ago`;
  };

  return (
    <div className={`p-3 border-b border-slate-700/50 hover:bg-teal-500/5 cursor-pointer transition-colors ${getSeverityStyles(alert.severity)}`}>
      <div className="flex items-start gap-3">
        <div className="mt-0.5">
          <AlertIcon type={alert.type} />
        </div>
        <div className="flex-1 min-w-0">
          <p className="text-sm font-medium text-white">{alert.message}</p>
          <p className="text-xs text-gray-400 mt-1">{formatTimeAgo(alert.timestamp)}</p>
          {alert.actionable && (
            <button 
              onClick={() => onAction(alert)}
              className="mt-2 px-3 py-1 bg-teal-500/20 hover:bg-teal-500/30 border border-teal-500/50 text-teal-400 rounded text-xs font-semibold transition-colors"
            >
              {alert.actionLabel || 'Take Action'}
            </button>
          )}
        </div>
        <button
          onClick={() => onDismiss(alert.id)}
          className="text-gray-500 hover:text-white transition-colors"
        >
          <X size={16} />
        </button>
      </div>
    </div>
  );
};

export default function NotificationCenter({ className = '' }) {
  const [alerts, setAlerts] = useState([]);
  const [filter, setFilter] = useState('unread'); // 'all' | 'unread'
  const [readAlerts, setReadAlerts] = useState(new Set());
  const [isOpen, setIsOpen] = useState(false);
  const [wsConnected, setWsConnected] = useState(false);

  useEffect(() => {
    // Connect to WebSocket for real-time alerts
    const ws = new WebSocket('ws://localhost:8000/ws/alerts');

    ws.onopen = () => {
      console.log('✅ Notification WebSocket connected');
      setWsConnected(true);
    };

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        
        if (data.type === 'alert') {
          const newAlert = {
            id: data.data.id || Date.now().toString(),
            type: data.data.topic?.split('.')[0] || 'signal',
            severity: data.data.severity || 'info',
            message: data.data.message,
            timestamp: data.data.timestamp || new Date().toISOString(),
            actionable: data.data.action !== undefined,
            actionLabel: data.data.actionLabel,
            action: data.data.action
          };

          // Play audio alert for critical notifications
          if (newAlert.severity === 'critical') {
            if (newAlert.type === 'signal') {
              audioAlerts.play('t1_signal', 0.8);
            } else if (newAlert.type === 'risk') {
              audioAlerts.play('risk_breach', 0.9);
            }
          }

          setAlerts(prev => [newAlert, ...prev].slice(0, 50));
          
          // Auto-dismiss info alerts after 10 seconds
          if (newAlert.severity === 'info') {
            setTimeout(() => {
              setReadAlerts(prev => new Set([...prev, newAlert.id]));
            }, 10000);
          }
        }
      } catch (error) {
        console.error('Failed to parse WebSocket message:', error);
      }
    };

    ws.onerror = (error) => {
      console.error('WebSocket error:', error);
      setWsConnected(false);
    };

    ws.onclose = () => {
      console.log('WebSocket disconnected');
      setWsConnected(false);
    };

    return () => ws.close();
  }, []);

  const dismissAlert = (alertId) => {
    setReadAlerts(prev => new Set([...prev, alertId]));
  };

  const handleAction = (alert) => {
    if (alert.action) {
      // Execute the action (e.g., open trade dialog, navigate to position)
      console.log('Executing action:', alert.action);
      // TODO: Implement action routing
    }
    dismissAlert(alert.id);
  };

  const clearAll = () => {
    setAlerts([]);
    setReadAlerts(new Set());
  };

  const visibleAlerts = alerts.filter(alert => 
    filter === 'all' || !readAlerts.has(alert.id)
  );

  const unreadCount = alerts.filter(a => !readAlerts.has(a.id)).length;

  return (
    <>
      {/* Bell Icon Button */}
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="relative p-2 hover:bg-slate-800/50 rounded-lg transition-colors"
      >
        <Bell className={wsConnected ? 'text-teal-400' : 'text-gray-500'} size={20} />
        {unreadCount > 0 && (
          <span className="absolute top-0 right-0 w-5 h-5 bg-red-500 text-white text-xs rounded-full flex items-center justify-center font-bold">
            {unreadCount > 9 ? '9+' : unreadCount}
          </span>
        )}
      </button>

      {/* Notification Panel */}
      {isOpen && (
        <div className={`fixed top-16 right-4 w-96 max-h-[600px] bg-slate-900/95 backdrop-blur-lg border border-slate-700/50 rounded-lg shadow-2xl z-50 ${className}`}>
          {/* Header */}
          <div className="flex justify-between items-center p-4 border-b border-slate-700/50">
            <div className="flex items-center gap-2">
              <h3 className="font-bold text-white">Notifications</h3>
              <span className="text-xs text-gray-400">({unreadCount} unread)</span>
            </div>
            <div className="flex items-center gap-2">
              <button
                onClick={() => setFilter('unread')}
                className={`px-2 py-1 text-xs rounded transition-colors ${
                  filter === 'unread' 
                    ? 'bg-teal-500/20 text-teal-400 border border-teal-500/50' 
                    : 'text-gray-400 hover:text-white'
                }`}
              >
                Unread
              </button>
              <button
                onClick={() => setFilter('all')}
                className={`px-2 py-1 text-xs rounded transition-colors ${
                  filter === 'all' 
                    ? 'bg-teal-500/20 text-teal-400 border border-teal-500/50' 
                    : 'text-gray-400 hover:text-white'
                }`}
              >
                All
              </button>
              <button
                onClick={clearAll}
                className="text-xs text-red-400 hover:text-red-300 transition-colors"
              >
                Clear
              </button>
            </div>
          </div>

          {/* Alerts List */}
          <div className="overflow-y-auto max-h-[500px] custom-scrollbar">
            {visibleAlerts.length === 0 ? (
              <div className="p-8 text-center text-gray-500">
                <Bell className="mx-auto mb-2 opacity-50" size={32} />
                <p className="text-sm">No notifications</p>
              </div>
            ) : (
              visibleAlerts.map(alert => (
                <AlertItem
                  key={alert.id}
                  alert={alert}
                  onDismiss={dismissAlert}
                  onAction={handleAction}
                />
              ))
            )}
          </div>

          {/* Connection Status */}
          <div className="p-2 border-t border-slate-700/50 text-center">
            <div className="flex items-center justify-center gap-2 text-xs">
              <div className={`w-2 h-2 rounded-full ${
                wsConnected ? 'bg-green-400 animate-pulse' : 'bg-red-400'
              }`} />
              <span className={wsConnected ? 'text-green-400' : 'text-red-400'}>
                {wsConnected ? 'LIVE' : 'DISCONNECTED'}
              </span>
            </div>
          </div>
        </div>
      )}
    </>
  );
}

export { audioAlerts };