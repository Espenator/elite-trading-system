/**
 * WebSocket client for real-time updates.
 * Uses getWsBaseUrl() so in dev it connects via current host (Vite proxy).
 * Channels: agents, data_sources, signals, trades, logs, risk, kelly, sentiment.
 * Auto-reconnects with exponential backoff, max retries with polling fallback,
 * connection health metrics, and offline message queue.
 */

import { getWsBaseUrl } from "../config/api";
import notificationService from "./notifications";

const RECONNECT_DELAY_MS = 2000;
const MAX_RECONNECT_DELAY = 60000; // cap backoff at 60s for 24/7 resilience
const HEARTBEAT_INTERVAL = 25000;
const MAX_RETRY_COUNT = 10;
const STEADY_RECONNECT_DELAY = 30000; // 30s for attempts 6-10
const QUEUE_TTL_MS = 30000; // Drop queued messages older than 30s

class AppWebSocket {
  constructor() {
    this.ws = null;
    this.handlers = new Map(); // channel -> Set<fn>
    this.reconnectTimer = null;
    this._intentionalClose = false;
    this._reconnectAttempts = 0;
    this._heartbeatTimer = null;
    this.state = "disconnected"; // disconnected | connecting | connected | reconnecting | fallback

    // Max retries with escalation
    this._retryCount = 0;
    this._fallbackToPolling = false;

    // Connection health metrics
    this._metrics = {
      messagesReceived: 0,
      messagesSent: 0,
      lastMessageAt: null,
      disconnectCount: 0,
      latencyMs: null,
      connectedSince: null,
    };

    // Offline message queue
    this._outboundQueue = [];
  }

  connect() {
    if (this._fallbackToPolling) return;
    if (this.ws?.readyState === WebSocket.OPEN || this.ws?.readyState === WebSocket.CONNECTING) return;
    this._intentionalClose = false;
    this.state = "connecting";
    const url = getWsBaseUrl();
    try {
      this.ws = new WebSocket(url);

      this.ws.onopen = () => {
        this.state = "connected";

        // Reset retry counters on successful connection
        const wasReconnecting = this._reconnectAttempts > 0 || this._retryCount > 0;
        this._reconnectAttempts = 0;
        this._retryCount = 0;
        this._fallbackToPolling = false;

        // Update health metrics
        this._metrics.connectedSince = new Date().toISOString();

        // Broadcast reconnected state if this was a reconnection
        if (wasReconnecting) {
          this._broadcastStatus({ type: "ws_reconnected" });
        }

        // Re-subscribe to all active channels on (re)connect
        for (const channel of this.handlers.keys()) {
          if (channel !== "*") {
            this._sendRaw({ type: "subscribe", channel });
          }
        }

        // Flush offline message queue
        this._flushOutboundQueue();

        // Clear previous heartbeat timer to prevent leak on reconnect
        if (this._heartbeatTimer) clearInterval(this._heartbeatTimer);
        // Start heartbeat pong responses
        this._heartbeatTimer = setInterval(() => {
          if (this.ws?.readyState === WebSocket.OPEN) {
            this._sendRaw({ type: "pong" });
          }
        }, HEARTBEAT_INTERVAL);

        if (this.handlers.has("*"))
          this.handlers.get("*").forEach((fn) => fn({ type: "connected" }));
      };

      this.ws.onmessage = (event) => {
        try {
          const msg =
            typeof event.data === "string"
              ? JSON.parse(event.data)
              : event.data;

          // Update health metrics
          this._metrics.messagesReceived++;
          this._metrics.lastMessageAt = new Date().toISOString();

          // Ignore server pings (heartbeat)
          if (msg.type === "ping") return;

          const channel = msg.channel || "*";
          const data = msg.data !== undefined ? msg.data : msg;

          // Wire critical events to notifications (Task 3)
          if (data.type === "trade_fill" || data.type === "order_filled") {
            notificationService.orderFilled(data.symbol, data.side, data.qty, data.price);
          }
          if (data.type === "circuit_breaker") {
            notificationService.circuitBreakerTripped(data.reason || "Circuit breaker activated");
          }
          if (data.type === "new_signal" && data.score >= 80) {
            notificationService.newSignal(data.symbol, data.score, data.direction);
          }
          if (data.type === "agent_error") {
            notificationService.agentError(data.agent || "Unknown", data.error || "Error occurred");
          }

          if (this.handlers.has(channel))
            this.handlers.get(channel).forEach((fn) => fn(data));
          if (this.handlers.has("*"))
            this.handlers.get("*").forEach((fn) => fn({ channel, data }));
        } catch {
          if (this.handlers.has("*"))
            this.handlers.get("*").forEach((fn) => fn({ raw: event.data }));
        }
      };

      this.ws.onclose = () => {
        clearInterval(this._heartbeatTimer);
        this.state = "disconnected";

        // Update health metrics
        this._metrics.disconnectCount++;
        this._metrics.connectedSince = null;

        if (this.handlers.has("*"))
          this.handlers.get("*").forEach((fn) => fn({ type: "disconnected" }));
        if (!this._intentionalClose) {
          this._scheduleReconnect();
        }
      };

      this.ws.onerror = (evt) => {
        // Browser WS error events are opaque — log the URL and state for debugging
        console.warn("[WS] connection error", { url: this.ws?.url, readyState: this.ws?.readyState });
        // Mark as disconnected so UI reflects the error immediately
        if (this.state === "connected") {
          this.state = "disconnected";
        }
        if (this.handlers.has("*"))
          this.handlers.get("*").forEach((fn) => fn({ type: "error", error: evt }));
      };
    } catch (err) {
      console.warn("[WS] failed to create WebSocket", err.message || err);
      if (this.handlers.has("*"))
        this.handlers.get("*").forEach((fn) => fn({ type: "error", error: err }));
      this._scheduleReconnect();
    }
  }

  /**
   * Schedule a reconnect with escalating backoff strategy:
   * - Attempts 1-5: exponential backoff (2s * 1.5^n, capped at 60s)
   * - Attempts 6-10: steady 30s interval
   * - After 10: stop reconnecting, activate polling fallback
   */
  _scheduleReconnect() {
    this._retryCount++;
    this._reconnectAttempts++;

    if (this._retryCount > MAX_RETRY_COUNT) {
      // Activate fallback mode
      this._fallbackToPolling = true;
      this.state = "fallback";
      console.warn("[WS] Max retries exceeded, falling back to polling mode");
      this._broadcastStatus({ type: "ws_fallback" });
      return;
    }

    this.state = "reconnecting";

    // Broadcast reconnecting state
    this._broadcastStatus({ type: "ws_reconnecting", attempt: this._retryCount });

    let delay;
    if (this._retryCount <= 5) {
      // Exponential backoff for attempts 1-5
      const baseDelay = Math.min(
        RECONNECT_DELAY_MS * Math.pow(1.5, this._retryCount - 1),
        MAX_RECONNECT_DELAY
      );
      delay = baseDelay + Math.random() * 1000;
    } else {
      // Steady 30s interval for attempts 6-10
      delay = STEADY_RECONNECT_DELAY + Math.random() * 1000;
    }

    this.reconnectTimer = setTimeout(() => this.connect(), delay);
  }

  /**
   * Broadcast a status message to all subscribers.
   */
  _broadcastStatus(msg) {
    if (this.handlers.has("*")) {
      this.handlers.get("*").forEach((fn) => fn(msg));
    }
  }

  /**
   * Send data through the WebSocket. If not connected, queue the message.
   * Queued messages older than 30s are dropped.
   */
  send(data) {
    if (this.ws?.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(data));
      this._metrics.messagesSent++;
    } else {
      this._outboundQueue.push({ data, timestamp: Date.now() });
      // Drop messages older than 30s
      this._outboundQueue = this._outboundQueue.filter(m => Date.now() - m.timestamp < QUEUE_TTL_MS);
    }
  }

  /**
   * Flush queued outbound messages on reconnect.
   */
  _flushOutboundQueue() {
    // Filter out stale messages before flushing
    this._outboundQueue = this._outboundQueue.filter(m => Date.now() - m.timestamp < QUEUE_TTL_MS);
    while (this._outboundQueue.length > 0 && this.ws?.readyState === WebSocket.OPEN) {
      const item = this._outboundQueue.shift();
      this.ws.send(JSON.stringify(item.data));
      this._metrics.messagesSent++;
    }
  }

  /**
   * Subscribe to a channel. Returns an unsubscribe function.
   * Sends subscribe/unsubscribe messages to the backend.
   */
  on(channel, handler) {
    const isNew = !this.handlers.has(channel) || this.handlers.get(channel).size === 0;
    if (!this.handlers.has(channel)) this.handlers.set(channel, new Set());
    this.handlers.get(channel).add(handler);

    // Tell backend about new channel subscription
    if (isNew && channel !== "*") {
      this._sendRaw({ type: "subscribe", channel });
    }

    return () => {
      this.handlers.get(channel)?.delete(handler);
      // If no more handlers for this channel, unsubscribe on backend
      if (channel !== "*" && this.handlers.get(channel)?.size === 0) {
        this._sendRaw({ type: "unsubscribe", channel });
        this.handlers.delete(channel);
      }
    };
  }

  /**
   * Subscribe to a channel (same as on). Use with unsubscribe(channel, handler) in cleanup.
   * AgentCommandCenter and other components use this API.
   */
  subscribe(channel, handler) {
    const unsub = this.on(channel, handler);
    if (!this._subs) this._subs = new Map();
    const key = channel;
    if (!this._subs.has(key)) this._subs.set(key, []);
    this._subs.get(key).push({ handler, unsub });
  }

  /**
   * Unsubscribe a handler from a channel. Pair with subscribe(channel, handler).
   */
  unsubscribe(channel, handler) {
    if (!this._subs || !this._subs.has(channel)) return;
    const arr = this._subs.get(channel);
    const i = arr.findIndex((e) => e.handler === handler);
    if (i !== -1) {
      arr[i].unsub();
      arr.splice(i, 1);
    }
  }

  emit(channel, data) {
    this._sendRaw({ channel, data });
  }

  disconnect() {
    this._intentionalClose = true;
    clearInterval(this._heartbeatTimer);
    this.state = "disconnected";
    this._reconnectAttempts = 0;
    this._retryCount = 0;
    this._fallbackToPolling = false;
    this._outboundQueue = [];
    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer);
      this.reconnectTimer = null;
    }
    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }
  }

  isConnected() {
    return this.ws?.readyState === WebSocket.OPEN;
  }

  /**
   * Returns true if WebSocket has exhausted retries and switched to polling fallback.
   */
  isFallbackMode() {
    return this._fallbackToPolling;
  }

  /**
   * Return the current connection state string.
   * Possible values: "disconnected" | "connecting" | "connected" | "reconnecting" | "fallback"
   */
  getState() {
    return this.state;
  }

  /**
   * Return connection health metrics.
   */
  getHealth() {
    return { ...this._metrics };
  }

  // --- Kelly channel subscriptions ---
  subscribeKelly(callback) {
    return this.on("kelly", callback);
  }

  subscribeKellyWarnings(callback) {
    return this.on("kelly_warning", callback);
  }

  requestKellyRecalc(symbol) {
    this.emit("kelly_recalc", { symbol });
  }

  /** Send raw JSON if socket is open. */
  _sendRaw(obj) {
    if (this.ws?.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(obj));
      this._metrics.messagesSent++;
    }
  }
}

const ws = new AppWebSocket();

export default ws;
export { ws };
