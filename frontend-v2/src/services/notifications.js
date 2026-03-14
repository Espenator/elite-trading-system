/**
 * Centralized notification service for trading alerts.
 * Supports: toast, desktop, sound alerts with priority levels.
 */
import { toast } from 'react-toastify';

const PRIORITY = {
  CRITICAL: 'critical',  // sound + desktop + toast
  HIGH: 'high',          // desktop + toast
  MEDIUM: 'medium',      // toast only
  LOW: 'low',            // badge only (no toast)
};

class NotificationService {
  constructor() {
    this._notifications = [];
    this._maxHistory = 100;
    this._listeners = new Set();
    this._settings = {
      soundEnabled: true,
      desktopEnabled: false,
      quietHoursStart: null, // e.g., '22:00'
      quietHoursEnd: null,   // e.g., '07:00'
    };
    this._unreadCount = 0;
    this._desktopPermission = typeof Notification !== 'undefined' ? Notification.permission : 'denied';
  }

  // Request desktop notification permission
  async requestDesktopPermission() {
    if (typeof Notification !== 'undefined' && Notification.permission === 'default') {
      this._desktopPermission = await Notification.requestPermission();
    }
    return this._desktopPermission;
  }

  // Main notify method
  notify({ title, message, priority = PRIORITY.MEDIUM, category = 'system', data = {} }) {
    const notification = {
      id: Date.now() + Math.random(),
      title,
      message,
      priority,
      category,
      data,
      timestamp: new Date().toISOString(),
      read: false,
    };

    this._notifications.unshift(notification);
    if (this._notifications.length > this._maxHistory) {
      this._notifications = this._notifications.slice(0, this._maxHistory);
    }
    this._unreadCount++;

    // Toast notification (MEDIUM and above)
    if (priority !== PRIORITY.LOW) {
      const toastType = priority === PRIORITY.CRITICAL ? 'error'
        : priority === PRIORITY.HIGH ? 'warning'
        : 'info';
      toast[toastType](`${title}: ${message}`, {
        autoClose: priority === PRIORITY.CRITICAL ? 10000 : 5000,
        position: 'top-right',
      });
    }

    // Desktop notification (HIGH and above)
    if ((priority === PRIORITY.CRITICAL || priority === PRIORITY.HIGH)
        && this._settings.desktopEnabled
        && this._desktopPermission === 'granted'
        && !this._isQuietHours()) {
      try {
        new Notification(title, { body: message, icon: '/favicon.ico', tag: category });
      } catch {}
    }

    // Sound (CRITICAL only)
    if (priority === PRIORITY.CRITICAL && this._settings.soundEnabled && !this._isQuietHours()) {
      this._playAlertSound();
    }

    // Notify listeners (for bell badge, etc.)
    this._listeners.forEach(fn => { try { fn(this.getState()); } catch {} });

    return notification;
  }

  // Convenience methods
  critical(title, message, data) { return this.notify({ title, message, priority: PRIORITY.CRITICAL, data }); }
  high(title, message, data) { return this.notify({ title, message, priority: PRIORITY.HIGH, data }); }
  info(title, message, data) { return this.notify({ title, message, priority: PRIORITY.MEDIUM, data }); }
  low(title, message, data) { return this.notify({ title, message, priority: PRIORITY.LOW, data }); }

  // Trading-specific alerts
  orderFilled(symbol, side, qty, price) {
    this.critical('Order Filled', `${side} ${qty} ${symbol} @ $${price}`, { category: 'trade' });
  }
  circuitBreakerTripped(reason) {
    this.critical('Circuit Breaker', reason, { category: 'risk' });
  }
  newSignal(symbol, score, direction) {
    if (score >= 80) {
      this.high('Strong Signal', `${symbol} ${direction} (score: ${score})`, { category: 'signal' });
    } else {
      this.low('Signal', `${symbol} ${direction} (score: ${score})`, { category: 'signal' });
    }
  }
  agentError(agentName, error) {
    this.high('Agent Error', `${agentName}: ${error}`, { category: 'agent' });
  }

  // State
  getState() {
    return { notifications: this._notifications, unreadCount: this._unreadCount };
  }
  getNotifications() { return this._notifications; }
  getUnreadCount() { return this._unreadCount; }

  markAllRead() {
    this._notifications.forEach(n => { n.read = true; });
    this._unreadCount = 0;
    this._listeners.forEach(fn => { try { fn(this.getState()); } catch {} });
  }

  clearAll() {
    this._notifications = [];
    this._unreadCount = 0;
    this._listeners.forEach(fn => { try { fn(this.getState()); } catch {} });
  }

  subscribe(fn) { this._listeners.add(fn); return () => this._listeners.delete(fn); }

  updateSettings(settings) { Object.assign(this._settings, settings); }

  _isQuietHours() {
    if (!this._settings.quietHoursStart || !this._settings.quietHoursEnd) return false;
    const now = new Date();
    const hhmm = `${String(now.getHours()).padStart(2, '0')}:${String(now.getMinutes()).padStart(2, '0')}`;
    const start = this._settings.quietHoursStart;
    const end = this._settings.quietHoursEnd;
    if (start <= end) return hhmm >= start && hhmm < end;
    return hhmm >= start || hhmm < end; // Overnight range
  }

  _playAlertSound() {
    try {
      const ctx = new (window.AudioContext || window.webkitAudioContext)();
      const osc = ctx.createOscillator();
      const gain = ctx.createGain();
      osc.connect(gain);
      gain.connect(ctx.destination);
      osc.frequency.value = 800;
      gain.gain.value = 0.3;
      osc.start();
      osc.stop(ctx.currentTime + 0.2);
      setTimeout(() => {
        const osc2 = ctx.createOscillator();
        const gain2 = ctx.createGain();
        osc2.connect(gain2);
        gain2.connect(ctx.destination);
        osc2.frequency.value = 1000;
        gain2.gain.value = 0.3;
        osc2.start();
        osc2.stop(ctx.currentTime + 0.15);
      }, 250);
    } catch {}
  }
}

// Singleton
const notificationService = new NotificationService();
export default notificationService;
export { PRIORITY };
