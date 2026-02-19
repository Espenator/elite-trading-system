/**
 * WebSocket client for real-time updates.
 * Uses config API_CONFIG.WS_URL (e.g. ws://localhost:8001/ws).
 * Channels: agents, datasources, signals, trades, logs.
 * Auto-reconnects after 3s on disconnect.
 */

import API_CONFIG from "../config/api";

const RECONNECT_DELAY_MS = 3000;

class AppWebSocket {
  constructor() {
    this.ws = null;
    this.handlers = new Map(); // channel -> Set<fn>
    this.reconnectTimer = null;
    this._intentionalClose = false;
  }

  connect() {
    if (this.ws?.readyState === WebSocket.OPEN) return;
    this._intentionalClose = false;
    const url = API_CONFIG.WS_URL;
    try {
      this.ws = new WebSocket(url);
      this.ws.onopen = () => {
        if (this.handlers.has("*"))
          this.handlers.get("*").forEach((fn) => fn({ type: "connected" }));
      };
      this.ws.onmessage = (event) => {
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
        if (this.handlers.has("*"))
          this.handlers.get("*").forEach((fn) => fn({ type: "disconnected" }));
        if (!this._intentionalClose && RECONNECT_DELAY_MS > 0) {
          this.reconnectTimer = setTimeout(
            () => this.connect(),
            RECONNECT_DELAY_MS,
          );
        }
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
}

const ws = new AppWebSocket();

export default ws;
export { ws };
