/**
 * WebSocket client for real-time updates.
 * Uses getWsBaseUrl() so in dev it connects via current host (Vite proxy).
 * Channels: agents, datasources, signals, trades, logs.
 * Auto-reconnects after 3s on disconnect.
 */

import { getWsBaseUrl } from "../config/api";

const RECONNECT_DELAY_MS = 2000;
const MAX_RECONNECT_DELAY = 30000;
const MAX_RECONNECT_ATTEMPTS = 20;
const HEARTBEAT_INTERVAL = 25000;

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
    if (this.ws?.readyState === WebSocket.OPEN) return;
    this._intentionalClose = false;
    const url = getWsBaseUrl();
    try {
      this.ws = new WebSocket(url);
            this.ws.onopen = () => {
        this.state = "connected";
        this._reconnectAttempts = 0;
        // Start heartbeat pong responses
        this._heartbeatTimer = setInterval(() => {
          if (this.ws?.readyState === WebSocket.OPEN) {
            this.ws.send(JSON.stringify({ type: "pong" }));
          }
        }, HEARTBEAT_INTERVAL);
        if (this.handlers.has("*"))
          this.handlers.get("*").forEach((fn) => fn({ type: "connected" }));
      };
        try {
          const msg =
            typeof event.data === "string"
              ? JSON.parse(event.data)
              : event.data;
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
        if (!this._intentionalClose && this._reconnectAttempts < MAX_RECONNECT_ATTEMPTS) {
          this.state = "reconnecting";
          const delay = Math.min(
            RECONNECT_DELAY_MS * Math.pow(1.5, this._reconnectAttempts),
            MAX_RECONNECT_DELAY
          );
          this._reconnectAttempts++;
          this.reconnectTimer = setTimeout(
            () => this.connect(),
            delay,
          );
        }
      };
      };
      this.ws.onerror = () => {};
    } catch (err) {
      if (this.handlers.has("*"))
        this.handlers
          .get("*")
          .forEach((fn) => fn({ type: "error", error: err }));
      this.reconnectTimer = setTimeout(
        () => this.connect(),
        RECONNECT_DELAY_MS,
      );
    }
  }

  on(channel, handler) {
    if (!this.handlers.has(channel)) this.handlers.set(channel, new Set());
    this.handlers.get(channel).add(handler);
    return () => this.handlers.get(channel)?.delete(handler);
  }

  emit(channel, data) {
    if (this.ws?.readyState !== WebSocket.OPEN) return;
    this.ws.send(JSON.stringify({ channel, data }));
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

      // --- Kelly channel subscriptions ---
  subscribeKelly(callback) {
    return this.on('kelly_update', callback);
  }

  subscribeKellyWarnings(callback) {
    return this.on('kelly_warning', callback);
  }

  requestKellyRecalc(symbol) {
    this.emit('kelly_recalc', { symbol });
  }
  }
}

const ws = new AppWebSocket();

export default ws;
export { ws };
