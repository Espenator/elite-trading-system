/**
 * WebSocket client for real-time updates.
 * Uses getWsBaseUrl() so in dev it connects via current host (Vite proxy).
 * Channels: agents, data_sources, signals, trades, logs, risk, kelly, sentiment.
 * Auto-reconnects with exponential backoff.
 */

import { getWsBaseUrl } from "../config/api";

const RECONNECT_DELAY_MS = 2000;
const MAX_RECONNECT_DELAY = 60000; // cap backoff at 60s for 24/7 resilience
const HEARTBEAT_INTERVAL = 25000;
// No max reconnect attempts — reconnect forever so WS stays up 24/7

class AppWebSocket {
  constructor() {
    this.ws = null;
    this.handlers = new Map(); // channel -> Set<fn>
    this.reconnectTimer = null;
    this._intentionalClose = false;
    this._reconnectAttempts = 0;
    this._heartbeatTimer = null;
    this.state = "disconnected"; // disconnected | connecting | connected | reconnecting
  }

  connect() {
    if (this.ws?.readyState === WebSocket.OPEN || this.ws?.readyState === WebSocket.CONNECTING) return;
    this._intentionalClose = false;
    this.state = "connecting";
    const url = getWsBaseUrl();
    try {
      this.ws = new WebSocket(url);

      this.ws.onopen = () => {
        this.state = "connected";
        this._reconnectAttempts = 0;

        // Re-subscribe to all active channels on (re)connect
        for (const channel of this.handlers.keys()) {
          if (channel !== "*") {
            this._sendRaw({ type: "subscribe", channel });
          }
        }

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

          // Ignore server pings (heartbeat)
          if (msg.type === "ping") return;

          const channel = msg.channel || "*";
          const data = msg.data !== undefined ? msg.data : msg;

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
        if (this.handlers.has("*"))
          this.handlers.get("*").forEach((fn) => fn({ type: "disconnected" }));
        if (!this._intentionalClose) {
          this.state = "reconnecting";
          if (this.handlers.has("*"))
            this.handlers.get("*").forEach((fn) => fn({ type: "reconnecting" }));
          const baseDelay = Math.min(
            RECONNECT_DELAY_MS * Math.pow(1.5, this._reconnectAttempts),
            MAX_RECONNECT_DELAY
          );
          const delay = baseDelay + Math.random() * 1000;
          this._reconnectAttempts++;
          this.reconnectTimer = setTimeout(() => this.connect(), delay);
        }
      };

      this.ws.onerror = (evt) => {
        console.warn("[WS] connection error", evt);
        if (this.handlers.has("*"))
          this.handlers.get("*").forEach((fn) => fn({ type: "error", error: evt }));
      };
    } catch (err) {
      if (this.handlers.has("*"))
        this.handlers.get("*").forEach((fn) => fn({ type: "error", error: err }));
      this.reconnectTimer = setTimeout(() => this.connect(), RECONNECT_DELAY_MS);
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
    }
  }
}

const ws = new AppWebSocket();

export default ws;
export { ws };
