import React, { useState, useEffect, useCallback } from 'react';
import { AlertCircle, CheckCircle, AlertTriangle, Info, X, Bell, BellOff } from 'lucide-react';

interface Notification {
  id: string;
  type: 'success' | 'error' | 'warning' | 'info';
  title: string;
  message: string;
  timestamp: Date;
  read: boolean;
  symbol?: string;
}

const WS_URL = 'ws://localhost:8000/api/v1/notifications/ws/alerts';
const MAX_NOTIFICATIONS = 50;
const RECONNECT_DELAY = 3000;

export function NotificationCenter() {
  const [notifications, setNotifications] = useState<Notification[]>([]);
  const [isConnected, setIsConnected] = useState(false);
  const [isConnecting, setIsConnecting] = useState(true);
  const [isMuted, setIsMuted] = useState(false);
  const [isExpanded, setIsExpanded] = useState(false);
  const [unreadCount, setUnreadCount] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const [ws, setWs] = useState<WebSocket | null>(null);

  useEffect(() => {
    setUnreadCount(notifications.filter(n => !n.read).length);
  }, [notifications]);

  const connect = useCallback(() => {
    setIsConnecting(true);
    setError(null);

    try {
      const websocket = new WebSocket(WS_URL);

      websocket.onopen = () => {
        setIsConnected(true);
        setIsConnecting(false);
        setError(null);
      };

      websocket.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          const newNotification: Notification = {
            id: crypto.randomUUID(),
            type: data.type || 'info',
            title: data.title || 'Notification',
            message: data.message || '',
            timestamp: new Date(),
            read: false,
            symbol: data.symbol
          };
          setNotifications(prev => [newNotification, ...prev].slice(0, MAX_NOTIFICATIONS));
          if (!isMuted && (data.type === 'success' || data.type === 'warning')) {
            playSound(data.type);
          }
        } catch (e) {
          console.error('Failed to parse message:', e);
        }
      };

      websocket.onerror = () => setError('Connection error');
      
      websocket.onclose = (event) => {
        setIsConnected(false);
        setWs(null);
        if (event.code !== 1000) {
          setTimeout(connect, RECONNECT_DELAY);
        }
      };

      setWs(websocket);
    } catch (e) {
      setError('Failed to connect');
      setIsConnecting(false);
    }
  }, [isMuted]);

  useEffect(() => {
    connect();
    return () => { if (ws) ws.close(1000); };
  }, []);

  const playSound = (type: string) => {
    try {
      const ctx = new AudioContext();
      const osc = ctx.createOscillator();
      const gain = ctx.createGain();
      osc.connect(gain);
      gain.connect(ctx.destination);
      osc.frequency.value = type === 'success' ? 880 : 440;
      gain.gain.setValueAtTime(0.1, ctx.currentTime);
      gain.gain.exponentialRampToValueAtTime(0.01, ctx.currentTime + 0.2);
      osc.start();
      osc.stop(ctx.currentTime + 0.2);
    } catch (e) {}
  };

  const markAsRead = (id: string) => setNotifications(prev => prev.map(n => n.id === id ? { ...n, read: true } : n));
  const markAllAsRead = () => setNotifications(prev => prev.map(n => ({ ...n, read: true })));
  const removeNotification = (id: string) => setNotifications(prev => prev.filter(n => n.id !== id));
  const clearAll = () => setNotifications([]);

  const getIcon = (type: Notification['type']) => {
    const icons = { success: <CheckCircle size={18} className="text-green-400" />, error: <AlertCircle size={18} className="text-red-400" />, warning: <AlertTriangle size={18} className="text-yellow-400" />, info: <Info size={18} className="text-cyan-400" /> };
    return icons[type] || icons.info;
  };

  const formatTime = (date: Date) => date.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit', second: '2-digit' });

  return (
    <div className="fixed top-4 right-4 z-50">
      <div className="relative">
        <button onClick={() => setIsExpanded(!isExpanded)} className="p-3 bg-slate-800 border border-slate-700 rounded-full hover:bg-slate-700 transition relative">
          {isMuted ? <BellOff size={20} className="text-slate-400" /> : <Bell size={20} className="text-cyan-400" />}
          {unreadCount > 0 && <span className="absolute -top-1 -right-1 w-5 h-5 bg-red-500 text-white text-xs font-bold rounded-full flex items-center justify-center">{unreadCount > 9 ? '9+' : unreadCount}</span>}
        </button>
        <span className={"absolute bottom-0 right-0 w-3 h-3 rounded-full border-2 border-slate-800 " + (isConnected ? 'bg-green-500' : isConnecting ? 'bg-yellow-500 animate-pulse' : 'bg-red-500')} />
      </div>

      {isExpanded && (
        <div className="absolute top-14 right-0 w-96 max-h-[500px] bg-slate-900 border border-slate-700 rounded-lg shadow-2xl overflow-hidden">
          <div className="p-3 border-b border-slate-700 flex items-center justify-between bg-slate-800">
            <div className="flex items-center gap-2">
              <h3 className="font-bold text-cyan-400">Notifications</h3>
              <span className={"text-xs px-2 py-0.5 rounded " + (isConnected ? 'bg-green-900/50 text-green-400' : 'bg-red-900/50 text-red-400')}>{isConnected ? 'Live' : isConnecting ? 'Connecting...' : 'Disconnected'}</span>
            </div>
            <div className="flex items-center gap-2">
              <button onClick={() => setIsMuted(!isMuted)} className="p-1 hover:bg-slate-700 rounded">{isMuted ? <BellOff size={16} className="text-slate-400" /> : <Bell size={16} className="text-slate-300" />}</button>
              <button onClick={markAllAsRead} className="text-xs text-cyan-400 hover:text-cyan-300">Mark read</button>
              <button onClick={clearAll} className="text-xs text-slate-400 hover:text-slate-300">Clear</button>
            </div>
          </div>

          {error && <div className="p-2 bg-red-900/30 border-b border-red-700 text-red-400 text-xs flex items-center gap-2"><AlertCircle size={14} />{error}<button onClick={connect} className="ml-auto text-red-300 hover:text-white">Retry</button></div>}

          <div className="overflow-y-auto max-h-[400px]">
            {notifications.length === 0 ? (
              <div className="p-8 text-center text-slate-500"><Bell size={32} className="mx-auto mb-2 opacity-50" /><p>No notifications yet</p></div>
            ) : (
              notifications.map(n => (
                <div key={n.id} onClick={() => markAsRead(n.id)} className={"p-3 border-b border-slate-800 cursor-pointer transition hover:bg-slate-800/50 " + (!n.read ? 'bg-slate-800/30' : '')}>
                  <div className="flex items-start gap-3">
                    {getIcon(n.type)}
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center justify-between gap-2">
                        <span className="font-semibold text-sm text-slate-200 truncate">{n.title}</span>
                        <button onClick={(e) => { e.stopPropagation(); removeNotification(n.id); }} className="text-slate-500 hover:text-slate-300"><X size={14} /></button>
                      </div>
                      <p className="text-xs text-slate-400 mt-0.5">{n.message}</p>
                      <div className="flex items-center gap-2 mt-1">
                        <span className="text-xs text-slate-500">{formatTime(n.timestamp)}</span>
                        {n.symbol && <span className="text-xs px-1.5 py-0.5 bg-cyan-900/30 text-cyan-400 rounded">{n.symbol}</span>}
                        {!n.read && <span className="w-2 h-2 bg-cyan-400 rounded-full" />}
                      </div>
                    </div>
                  </div>
                </div>
              ))
            )}
          </div>
        </div>
      )}
    </div>
  );
}
