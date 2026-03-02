import { useState, useEffect, useRef, useCallback } from 'react';
import { getWsUrl, WS_CHANNELS } from '../config/api';

/**
 * useWebSocket — reusable hook for real-time WebSocket streams.
 *
 * Usage:
 *   const { data, connected, error, send } = useWebSocket('agents');
 *   const { data } = useWebSocket('signals', { onMessage: (msg) => console.log(msg) });
 *
 * Channels (from api.js WS_CHANNELS):
 *   agents, datasources, signals, trades, logs, sentiment, risk, kelly, alignment
 *
 * Features:
 *   - Auto-reconnect with exponential backoff (max 30s)
 *   - Heartbeat ping/pong (30s interval)
 *   - Connection state tracking
 *   - Message buffer (last 200 messages)
 *   - Graceful cleanup on unmount
 */
export default function useWebSocket(channel, options = {}) {
  const {
    onMessage = null,
    onOpen = null,
    onClose = null,
    onError = null,
    maxBufferSize = 200,
    reconnectMaxDelay = 30000,
    heartbeatInterval = 30000,
    autoConnect = true,
  } = options;

  const [data, setData] = useState(null);
  const [messages, setMessages] = useState([]);
  const [connected, setConnected] = useState(false);
  const [error, setError] = useState(null);
  const [reconnectCount, setReconnectCount] = useState(0);

  const wsRef = useRef(null);
  const heartbeatRef = useRef(null);
  const reconnectRef = useRef(null);
  const mountedRef = useRef(true);

  const cleanup = useCallback(() => {
    if (heartbeatRef.current) clearInterval(heartbeatRef.current);
    if (reconnectRef.current) clearTimeout(reconnectRef.current);
    if (wsRef.current) {
      wsRef.current.onclose = null; // prevent reconnect on intentional close
      wsRef.current.close(1000, 'Component unmounted');
      wsRef.current = null;
    }
  }, []);

  const connect = useCallback(() => {
    if (!mountedRef.current) return;
    cleanup();

    const wsUrl = getWsUrl(channel);
    if (!wsUrl) {
      setError(`Unknown WebSocket channel: ${channel}`);
      return;
    }

    try {
      const ws = new WebSocket(wsUrl);
      wsRef.current = ws;

      ws.onopen = () => {
        if (!mountedRef.current) return;
        setConnected(true);
        setError(null);
        setReconnectCount(0);
        console.log(`[WS:${channel}] Connected to ${wsUrl}`);

        // Start heartbeat
        heartbeatRef.current = setInterval(() => {
          if (ws.readyState === WebSocket.OPEN) {
            ws.send(JSON.stringify({ type: 'ping', ts: Date.now() }));
          }
        }, heartbeatInterval);

        onOpen?.();
      };

      ws.onmessage = (event) => {
        if (!mountedRef.current) return;
        try {
          const parsed = JSON.parse(event.data);
          // Skip pong responses
          if (parsed.type === 'pong') return;

          setData(parsed);
          setMessages(prev => {
            const next = [...prev, { ...parsed, _receivedAt: Date.now() }];
            return next.length > maxBufferSize ? next.slice(-maxBufferSize) : next;
          });
          onMessage?.(parsed);
        } catch {
          // Non-JSON message — treat as raw text
          setData(event.data);
          onMessage?.(event.data);
        }
      };

      ws.onclose = (event) => {
        if (!mountedRef.current) return;
        setConnected(false);
        if (heartbeatRef.current) clearInterval(heartbeatRef.current);
        console.log(`[WS:${channel}] Closed (code: ${event.code})`);
        onClose?.(event);

        // Auto-reconnect with exponential backoff
        if (event.code !== 1000 && mountedRef.current) {
          setReconnectCount(prev => prev + 1);
          const delay = Math.min(1000 * Math.pow(2, reconnectCount), reconnectMaxDelay);
          console.log(`[WS:${channel}] Reconnecting in ${delay}ms (attempt ${reconnectCount + 1})`);
          reconnectRef.current = setTimeout(connect, delay);
        }
      };

      ws.onerror = (event) => {
        if (!mountedRef.current) return;
        setError(`WebSocket error on ${channel}`);
        console.error(`[WS:${channel}] Error:`, event);
        onError?.(event);
      };
    } catch (err) {
      setError(err.message);
    }
  }, [channel, cleanup, heartbeatInterval, maxBufferSize, onClose, onError, onMessage, onOpen, reconnectCount, reconnectMaxDelay]);

  const send = useCallback((payload) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(typeof payload === 'string' ? payload : JSON.stringify(payload));
      return true;
    }
    return false;
  }, []);

  const disconnect = useCallback(() => {
    cleanup();
    setConnected(false);
  }, [cleanup]);

  useEffect(() => {
    mountedRef.current = true;
    if (autoConnect) connect();
    return () => {
      mountedRef.current = false;
      cleanup();
    };
  }, [autoConnect, connect, cleanup]);

  return {
    data,           // latest message
    messages,       // ring buffer of last N messages
    connected,      // boolean connection state
    error,          // error string or null
    reconnectCount, // how many reconnects attempted
    send,           // send a message
    connect,        // manually connect
    disconnect,     // manually disconnect
  };
}

// Re-export channels for convenience
export { WS_CHANNELS };