/**
 * CNS (Central Nervous System) Context — provides real-time system state
 * to the entire app via React Context + WebSocket + polling fallback.
 *
 * Exposes: homeostasis mode, circuit breaker status, agent health,
 * latest verdict, connection status, notifications.
 *
 * Usage:
 *   import { CNSProvider, useCNS } from '@/hooks/useCNS';
 *   // Wrap app: <CNSProvider><App /></CNSProvider>
 *   // In components: const { mode, verdict, circuitBreaker } = useCNS();
 */
import { createContext, useContext, useState, useEffect, useCallback, useRef } from 'react';
import ws from '../services/websocket';
import { useHomeostasis, useCircuitBreakerStatus, useCnsLastVerdict } from './useApi';

const CNSContext = createContext(null);

// Event types for the notification system
export const CNS_EVENTS = {
  COUNCIL_VERDICT: 'council_verdict',
  MODE_CHANGE: 'mode_change',
  CIRCUIT_BREAKER_FIRE: 'circuit_breaker_fire',
  AGENT_HIBERNATED: 'agent_hibernated',
  AGENT_PROBATION: 'agent_probation',
  TRADE_EXECUTED: 'trade_executed',
  RISK_ALERT: 'risk_alert',
};

export function CNSProvider({ children }) {
  // Core state
  const [mode, setMode] = useState('NORMAL');
  const [positionScale, setPositionScale] = useState(1.0);
  const [circuitBreakerArmed, setCircuitBreakerArmed] = useState(true);
  const [circuitBreakerFired, setCircuitBreakerFired] = useState(null);
  const [latestVerdict, setLatestVerdict] = useState(null);
  const [wsConnected, setWsConnected] = useState(false);

  // Notification queue — components subscribe to this
  const [notifications, setNotifications] = useState([]);
  const notifIdRef = useRef(0);
  const prevModeRef = useRef('NORMAL');

  // Polling fallbacks
  const homeostasis = useHomeostasis(10000);
  const cbStatus = useCircuitBreakerStatus(15000);
  const lastVerdict = useCnsLastVerdict(10000);

  // Sync polling data into state
  useEffect(() => {
    if (homeostasis.data) {
      const newMode = homeostasis.data.mode || 'NORMAL';
      if (newMode !== prevModeRef.current) {
        addNotification(CNS_EVENTS.MODE_CHANGE, {
          from: prevModeRef.current,
          to: newMode,
          message: `System mode changed: ${prevModeRef.current} → ${newMode}`,
        });
        prevModeRef.current = newMode;
      }
      setMode(newMode);
      setPositionScale(homeostasis.data.position_scale ?? 1.0);
    }
  }, [homeostasis.data]);

  useEffect(() => {
    if (cbStatus.data) {
      setCircuitBreakerArmed(cbStatus.data.armed ?? true);
    }
  }, [cbStatus.data]);

  useEffect(() => {
    if (lastVerdict.data?.verdict) {
      setLatestVerdict(lastVerdict.data.verdict);
    }
  }, [lastVerdict.data]);

  // Add notification helper
  const addNotification = useCallback((type, payload) => {
    const id = ++notifIdRef.current;
    setNotifications(prev => [
      { id, type, payload, timestamp: Date.now(), read: false },
      ...prev.slice(0, 49), // keep last 50
    ]);
  }, []);

  // Mark notification as read
  const markRead = useCallback((id) => {
    setNotifications(prev =>
      prev.map(n => n.id === id ? { ...n, read: true } : n)
    );
  }, []);

  // Clear all notifications
  const clearNotifications = useCallback(() => {
    setNotifications([]);
  }, []);

  // WebSocket subscriptions for real-time updates
  useEffect(() => {
    const unsubs = [];

    // Global connection status
    unsubs.push(ws.on('*', (ev) => {
      if (ev.type === 'connected') setWsConnected(true);
      if (ev.type === 'disconnected') setWsConnected(false);
    }));

    // Council verdicts
    unsubs.push(ws.on('council_verdict', (data) => {
      setLatestVerdict(data);
      const dir = data?.direction || 'hold';
      const conf = data?.confidence || 0;
      const sym = data?.symbol || '???';
      addNotification(CNS_EVENTS.COUNCIL_VERDICT, {
        message: `Council verdict: ${sym} → ${dir.toUpperCase()} (${(conf * 100).toFixed(0)}%)`,
        ...data,
      });
    }));

    // Homeostasis mode changes via WS
    unsubs.push(ws.on('homeostasis', (data) => {
      if (data?.mode) {
        const newMode = data.mode;
        if (newMode !== prevModeRef.current) {
          addNotification(CNS_EVENTS.MODE_CHANGE, {
            from: prevModeRef.current,
            to: newMode,
            message: `System mode: ${prevModeRef.current} → ${newMode}`,
          });
          prevModeRef.current = newMode;
        }
        setMode(newMode);
        setPositionScale(data.position_scale ?? 1.0);
      }
    }));

    // Circuit breaker events
    unsubs.push(ws.on('circuit_breaker', (data) => {
      if (data?.fired) {
        setCircuitBreakerFired(data.reason || 'Unknown');
        addNotification(CNS_EVENTS.CIRCUIT_BREAKER_FIRE, {
          message: `Circuit breaker fired: ${data.reason}`,
          ...data,
        });
      }
    }));

    // Risk alerts
    unsubs.push(ws.on('risk', (data) => {
      if (data?.alert) {
        addNotification(CNS_EVENTS.RISK_ALERT, {
          message: data.alert,
          ...data,
        });
      }
    }));

    // Trade events
    unsubs.push(ws.on('trades', (data) => {
      if (data?.type === 'fill' || data?.status === 'filled') {
        addNotification(CNS_EVENTS.TRADE_EXECUTED, {
          message: `Trade filled: ${data.symbol || '???'} ${data.side || ''} @ ${data.price || ''}`,
          ...data,
        });
      }
    }));

    return () => unsubs.forEach(fn => fn());
  }, [addNotification]);

  const value = {
    // System state
    mode,
    positionScale,
    circuitBreakerArmed,
    circuitBreakerFired,
    latestVerdict,
    wsConnected,

    // Notifications
    notifications,
    unreadCount: notifications.filter(n => !n.read).length,
    addNotification,
    markRead,
    clearNotifications,

    // Refetch helpers
    refetchHomeostasis: homeostasis.refetch,
    refetchVerdict: lastVerdict.refetch,
  };

  return (
    <CNSContext.Provider value={value}>
      {children}
    </CNSContext.Provider>
  );
}

export function useCNS() {
  const ctx = useContext(CNSContext);
  if (!ctx) {
    // Return safe defaults if used outside provider
    return {
      mode: 'NORMAL',
      positionScale: 1.0,
      circuitBreakerArmed: true,
      circuitBreakerFired: null,
      latestVerdict: null,
      wsConnected: false,
      notifications: [],
      unreadCount: 0,
      addNotification: () => {},
      markRead: () => {},
      clearNotifications: () => {},
      refetchHomeostasis: () => {},
      refetchVerdict: () => {},
    };
  }
  return ctx;
}

export default useCNS;
