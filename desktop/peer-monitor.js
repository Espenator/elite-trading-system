/**
 * Peer Monitor — Monitors peer PC health and manages fallback.
 *
 * State Machine per peer:
 *   CONNECTED → DEGRADED → LOST → RECOVERED → CONNECTED
 *
 * Heartbeat: HTTP GET to peer's /health endpoint every 10s.
 * On peer loss: emits events for service-orchestrator to trigger fallback.
 * On peer recovery: emits events to restore full cluster.
 */
const http = require("http");
const log = require("electron-log");
const { EventEmitter } = require("events");
const deviceConfig = require("./device-config");

const HEARTBEAT_INTERVAL_MS = 10_000; // 10 seconds
const DEGRADED_THRESHOLD = 2;          // 2 missed heartbeats → DEGRADED
const LOST_THRESHOLD = 5;              // 5 missed heartbeats → LOST
const RECOVERY_CONFIRMATIONS = 3;      // 3 consecutive successes → RECOVERED

const PEER_STATE = {
  UNKNOWN: "UNKNOWN",
  CONNECTED: "CONNECTED",
  DEGRADED: "DEGRADED",
  LOST: "LOST",
  RECOVERED: "RECOVERED",
};

class PeerMonitor extends EventEmitter {
  constructor() {
    super();
    this._peers = new Map(); // peerId → { state, missedCount, recoveryCount, lastSeen, config }
    this._intervals = new Map();
    this._running = false;
  }

  /**
   * Start monitoring all configured peer devices.
   */
  start() {
    if (this._running) return;
    this._running = true;

    const peers = deviceConfig.getPeerDevices();
    if (!peers || peers.length === 0) {
      log.info("[PeerMonitor] No peers configured — running in standalone mode");
      return;
    }

    for (const peer of peers) {
      this._initPeer(peer);
    }

    log.info(`[PeerMonitor] Monitoring ${peers.length} peer(s)`);
  }

  /**
   * Stop all monitoring.
   */
  stop() {
    this._running = false;
    for (const [peerId, interval] of this._intervals) {
      clearInterval(interval);
      log.info(`[PeerMonitor] Stopped monitoring ${peerId}`);
    }
    this._intervals.clear();
  }

  /**
   * Initialize monitoring for a single peer.
   */
  _initPeer(peerConfig) {
    const peerId = peerConfig.id || peerConfig.hostname || peerConfig.ip;
    this._peers.set(peerId, {
      state: PEER_STATE.UNKNOWN,
      missedCount: 0,
      recoveryCount: 0,
      lastSeen: null,
      latencyMs: null,
      config: peerConfig,
    });

    // Start heartbeat loop
    const interval = setInterval(() => this._heartbeat(peerId), HEARTBEAT_INTERVAL_MS);
    this._intervals.set(peerId, interval);

    // Initial check immediately
    this._heartbeat(peerId);
  }

  /**
   * Perform a single heartbeat check for a peer.
   */
  async _heartbeat(peerId) {
    const peer = this._peers.get(peerId);
    if (!peer) return;

    const { config } = peer;
    const host = config.ip || config.hostname || config.address;
    const port = config.port || 8000;
    const url = `http://${host}:${port}/health`;
    const startMs = Date.now();

    try {
      const response = await this._httpGet(url, 5000);
      const latencyMs = Date.now() - startMs;

      // Heartbeat succeeded
      peer.missedCount = 0;
      peer.recoveryCount += 1;
      peer.lastSeen = new Date().toISOString();
      peer.latencyMs = latencyMs;

      const previousState = peer.state;

      if (previousState === PEER_STATE.LOST || previousState === PEER_STATE.DEGRADED) {
        if (peer.recoveryCount >= RECOVERY_CONFIRMATIONS) {
          peer.state = PEER_STATE.RECOVERED;
          log.info(`[PeerMonitor] ${peerId}: RECOVERED (latency=${latencyMs}ms)`);
          this.emit("peer-recovered", { peerId, peer: this._peerStatus(peerId) });

          // Transition to CONNECTED after emitting recovery
          peer.state = PEER_STATE.CONNECTED;
          this.emit("peer-connected", { peerId, peer: this._peerStatus(peerId) });
        }
      } else if (previousState !== PEER_STATE.CONNECTED) {
        peer.state = PEER_STATE.CONNECTED;
        peer.recoveryCount = 0;
        log.info(`[PeerMonitor] ${peerId}: CONNECTED (latency=${latencyMs}ms)`);
        this.emit("peer-connected", { peerId, peer: this._peerStatus(peerId) });
      }
    } catch (err) {
      // Heartbeat failed
      peer.missedCount += 1;
      peer.recoveryCount = 0;
      const previousState = peer.state;

      if (peer.missedCount >= LOST_THRESHOLD && previousState !== PEER_STATE.LOST) {
        peer.state = PEER_STATE.LOST;
        log.warn(`[PeerMonitor] ${peerId}: LOST (${peer.missedCount} missed heartbeats)`);
        this.emit("peer-lost", { peerId, peer: this._peerStatus(peerId) });
      } else if (peer.missedCount >= DEGRADED_THRESHOLD && previousState === PEER_STATE.CONNECTED) {
        peer.state = PEER_STATE.DEGRADED;
        log.warn(`[PeerMonitor] ${peerId}: DEGRADED (${peer.missedCount} missed heartbeats)`);
        this.emit("peer-degraded", { peerId, peer: this._peerStatus(peerId) });
      }
    }
  }

  /**
   * Simple HTTP GET with timeout.
   */
  _httpGet(url, timeoutMs) {
    return new Promise((resolve, reject) => {
      const req = http.get(url, { timeout: timeoutMs }, (res) => {
        let data = "";
        res.on("data", (chunk) => (data += chunk));
        res.on("end", () => {
          if (res.statusCode >= 200 && res.statusCode < 300) {
            resolve({ statusCode: res.statusCode, body: data });
          } else {
            reject(new Error(`HTTP ${res.statusCode}`));
          }
        });
      });
      req.on("error", reject);
      req.on("timeout", () => {
        req.destroy();
        reject(new Error("Timeout"));
      });
    });
  }

  /**
   * Get status for a specific peer.
   * Derives services from role when peer.config.services is not set (e.g. setup wizard).
   */
  _peerStatus(peerId) {
    const peer = this._peers.get(peerId);
    if (!peer) return null;
    const role = peer.config.role || "unknown";
    const services =
      peer.config.services && peer.config.services.length > 0
        ? peer.config.services
        : (deviceConfig.getServicesForRole && deviceConfig.getServicesForRole(role)) || [];
    return {
      id: peerId,
      state: peer.state,
      lastSeen: peer.lastSeen,
      latencyMs: peer.latencyMs,
      missedCount: peer.missedCount,
      services,
      role,
    };
  }

  /**
   * Get status of all peers.
   */
  getAllPeerStatus() {
    const result = {};
    for (const [peerId] of this._peers) {
      result[peerId] = this._peerStatus(peerId);
    }
    return result;
  }

  /**
   * Get cluster health summary.
   */
  getClusterHealth() {
    const peers = Array.from(this._peers.values());
    const connected = peers.filter((p) => p.state === PEER_STATE.CONNECTED).length;
    const degraded = peers.filter((p) => p.state === PEER_STATE.DEGRADED).length;
    const lost = peers.filter((p) => p.state === PEER_STATE.LOST).length;

    let clusterState = "HEALTHY";
    if (lost > 0) clusterState = "DEGRADED";
    if (lost === peers.length && peers.length > 0) clusterState = "STANDALONE";

    return {
      clusterState,
      totalPeers: peers.length,
      connected,
      degraded,
      lost,
      peers: this.getAllPeerStatus(),
    };
  }

  /**
   * Initialize monitoring (alias for start, matches main.js expected interface).
   */
  async initialize() {
    this.start();
  }

  /**
   * Shutdown monitoring (alias for stop, matches main.js expected interface).
   */
  async shutdown() {
    this.stop();
  }

  /**
   * Check if a specific service is available across the cluster.
   */
  isServiceAvailable(serviceName) {
    for (const [, peer] of this._peers) {
      if (peer.state !== PEER_STATE.CONNECTED) continue;
      const services =
        peer.config.services?.length > 0
          ? peer.config.services
          : (deviceConfig.getServicesForRole && deviceConfig.getServicesForRole(peer.config.role || "full")) || [];
      if (services.includes(serviceName)) return true;
    }
    return false;
  }
}

const peerMonitor = new PeerMonitor();

module.exports = {
  peerMonitor,
  PEER_STATE,
};