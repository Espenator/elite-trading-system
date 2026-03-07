// NotificationCenter — toast notifications for CNS events.
// Shows transient toasts at bottom-right that auto-dismiss after 5s.

import { useState, useEffect, useRef } from 'react';
import { X, Brain, Shield, Gauge, TrendingUp, Activity, AlertTriangle } from 'lucide-react';
import { useCNS, CNS_EVENTS } from '../../hooks/useCNS';

const EVENT_CONFIG = {
  [CNS_EVENTS.COUNCIL_VERDICT]: { icon: Brain, color: 'border-cyan-500/50 bg-cyan-500/10', iconColor: 'text-cyan-400' },
  [CNS_EVENTS.MODE_CHANGE]: { icon: Gauge, color: 'border-amber-500/50 bg-amber-500/10', iconColor: 'text-amber-400' },
  [CNS_EVENTS.CIRCUIT_BREAKER_FIRE]: { icon: Shield, color: 'border-red-500/50 bg-red-500/10', iconColor: 'text-red-400' },
  [CNS_EVENTS.TRADE_EXECUTED]: { icon: TrendingUp, color: 'border-green-500/50 bg-green-500/10', iconColor: 'text-green-400' },
  [CNS_EVENTS.RISK_ALERT]: { icon: AlertTriangle, color: 'border-amber-500/50 bg-amber-500/10', iconColor: 'text-amber-400' },
  [CNS_EVENTS.AGENT_HIBERNATED]: { icon: Activity, color: 'border-red-500/50 bg-red-500/10', iconColor: 'text-red-400' },
  [CNS_EVENTS.AGENT_PROBATION]: { icon: Activity, color: 'border-amber-500/50 bg-amber-500/10', iconColor: 'text-amber-400' },
};

export default function NotificationCenter() {
  const { notifications } = useCNS();
  const [toasts, setToasts] = useState([]);
  const lastSeenRef = useRef(0);

  // Watch for new notifications and create toasts
  useEffect(() => {
    if (notifications.length === 0) return;
    const newest = notifications[0]; // sorted newest first
    if (newest && newest.id > lastSeenRef.current) {
      lastSeenRef.current = newest.id;
      setToasts(prev => [
        { ...newest, expiresAt: Date.now() + 5000 },
        ...prev.slice(0, 4), // max 5 toasts
      ]);
    }
  }, [notifications]);

  // Auto-dismiss expired toasts
  useEffect(() => {
    if (toasts.length === 0) return;
    const timer = setInterval(() => {
      setToasts(prev => prev.filter(t => t.expiresAt > Date.now()));
    }, 1000);
    return () => clearInterval(timer);
  }, [toasts.length]);

  const dismissToast = (id) => {
    setToasts(prev => prev.filter(t => t.id !== id));
  };

  if (toasts.length === 0) return null;

  return (
    <div className="fixed bottom-6 right-6 z-50 flex flex-col gap-2 pointer-events-none">
      {toasts.map((toast) => {
        const config = EVENT_CONFIG[toast.type] || EVENT_CONFIG[CNS_EVENTS.RISK_ALERT];
        const Icon = config.icon;
        return (
          <div
            key={toast.id}
            className={`pointer-events-auto flex items-start gap-3 px-4 py-3 rounded-md border ${config.color} backdrop-blur-xl shadow-2xl shadow-black/50 max-w-sm animate-slide-in`}
          >
            <Icon className={`w-5 h-5 ${config.iconColor} flex-shrink-0 mt-0.5`} />
            <div className="flex-1 min-w-0">
              <p className="text-sm text-white leading-snug">
                {toast.payload?.message || toast.type}
              </p>
            </div>
            <button
              onClick={() => dismissToast(toast.id)}
              className="text-secondary hover:text-white transition-colors flex-shrink-0"
            >
              <X className="w-4 h-4" />
            </button>
          </div>
        );
      })}
    </div>
  );
}
