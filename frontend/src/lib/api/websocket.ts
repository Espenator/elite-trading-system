// frontend/src/lib/api/websocket.ts
import {
  PriceTick,
  TradingSignal,
  ActivePosition,
  OrderBook,
  SystemHealth,
  AgentActivityLog
} from '../types';

type EventType =
  | 'price_tick'
  | 'order_book'
  | 'trading_signal'
  | 'active_positions'
  | 'system_health'
  | 'agent_activity';

type EventCallback = (data: any) => void;

class WebSocketManager {
  private ws: WebSocket | null = null;
  private url: string;
  private reconnectAttempts = 0;
  private maxReconnectAttempts = 10;
  private baseReconnectTimeout = 1000; // 1 second
  private isConnecting = false;

  // Event listeners mapped by event type
  private listeners: Map<string, Set<EventCallback>> = new Map();

  // Keep track of active subscriptions to restore them on reconnect
  private activeSubscriptions: Set<string> = new Set();

  // Message queue for payloads sent while disconnected
  private messageQueue: string[] = [];

  private heartbeatInterval: NodeJS.Timeout | null = null;

  constructor(url: string) {
    this.url = url;
  }

  public connect(): void {
    if (this.ws?.readyState === WebSocket.OPEN || this.isConnecting) return;

    this.isConnecting = true;
    this.ws = new WebSocket(this.url);

    this.ws.onopen = this.handleOpen.bind(this);
    this.ws.onmessage = this.handleMessage.bind(this);
    this.ws.onclose = this.handleClose.bind(this);
    this.ws.onerror = this.handleError.bind(this);
  }

  private handleOpen(): void {
    console.log('[WebSocket] Connected to Elite Trading Backend');
    this.isConnecting = false;
    this.reconnectAttempts = 0;

    // Start Heartbeat
    this.heartbeatInterval = setInterval(() => {
      this.send(JSON.stringify({ action: 'ping' }));
    }, 30000);

    // Resubscribe to previous channels
    this.activeSubscriptions.forEach((subPayload) => {
      this.ws?.send(subPayload);
    });

    // Flush queued messages
    while (this.messageQueue.length > 0) {
      const msg = this.messageQueue.shift();
      if (msg) this.ws?.send(msg);
    }
  }

  private handleMessage(event: MessageEvent): void {
    try {
      const payload = JSON.parse(event.data);
      const { type, data } = payload;

      if (type === 'pong') return;

      // Route high-frequency data to registered listeners
      if (this.listeners.has(type)) {
        this.listeners.get(type)!.forEach((callback) => callback(data));
      }
    } catch (error) {
      console.error('[WebSocket] Failed to parse message', error);
    }
  }

  private handleClose(event: CloseEvent): void {
    console.warn(`[WebSocket] Disconnected (Code: ${event.code})`);
    this.cleanup();
    this.attemptReconnect();
  }

  private handleError(error: Event): void {
    console.error('[WebSocket] Error encountered', error);
    this.ws?.close();
  }

  private attemptReconnect(): void {
    if (this.reconnectAttempts >= this.maxReconnectAttempts) {
      console.error('[WebSocket] Max reconnect attempts reached. Please check the backend.');
      return;
    }

    const timeout = Math.min(
      this.baseReconnectTimeout * Math.pow(2, this.reconnectAttempts),
      30000 // Max 30 seconds between attempts
    );

    this.reconnectAttempts++;
    console.log(`[WebSocket] Reconnecting in ${timeout}ms... (Attempt ${this.reconnectAttempts})`);

    setTimeout(() => this.connect(), timeout);
  }

  private cleanup(): void {
    this.isConnecting = false;
    if (this.heartbeatInterval) clearInterval(this.heartbeatInterval);
  }

  public send(payload: string): void {
    if (this.ws?.readyState === WebSocket.OPEN) {
      this.ws.send(payload);
    } else {
      this.messageQueue.push(payload);
    }
  }

  public subscribe(channel: string, symbol?: string): void {
    const payload = JSON.stringify({ action: 'subscribe', channel, symbol });
    this.activeSubscriptions.add(payload);
    this.send(payload);
  }

  public unsubscribe(channel: string, symbol?: string): void {
    const payload = JSON.stringify({ action: 'unsubscribe', channel, symbol });
    const subPayload = JSON.stringify({ action: 'subscribe', channel, symbol });
    this.activeSubscriptions.delete(subPayload);
    this.send(payload);
  }

  // Type-safe event registration
  public on(event: 'price_tick', callback: (data: PriceTick) => void): void;
  public on(event: 'order_book', callback: (data: OrderBook) => void): void;
  public on(event: 'trading_signal', callback: (data: TradingSignal) => void): void;
  public on(event: 'active_positions', callback: (data: ActivePosition[]) => void): void;
  public on(event: 'system_health', callback: (data: SystemHealth) => void): void;
  public on(event: 'agent_activity', callback: (data: AgentActivityLog) => void): void;
  public on(event: EventType, callback: EventCallback): void {
    if (!this.listeners.has(event)) {
      this.listeners.set(event, new Set());
    }
    this.listeners.get(event)!.add(callback);
  }

  public off(event: EventType, callback: EventCallback): void {
    if (this.listeners.has(event)) {
      this.listeners.get(event)!.delete(callback);
    }
  }
}

// Export a singleton instance using the environment variable or fallback
const WS_URL = process.env.NEXT_PUBLIC_WS_URL || 'ws://localhost:8000/ws';
export const wsManager = new WebSocketManager(WS_URL);
