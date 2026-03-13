/**
 * Service Orchestrator — Role-based service launcher.
 *
 * Reads the device role from device-config and starts only the services
 * assigned to this device. Handles service dependency ordering,
 * health monitoring, and fallback service activation.
 *
 * Service dependency order:
 *   backend → frontend → council → ml-engine → event-pipeline
 *   brain-service (independent, secondary role)
 *   scanner (independent, secondary role)
 */
const { spawn } = require("child_process");
const path = require("path");
const http = require("http");
const log = require("electron-log");
const deviceConfig = require("./device-config");
const backendManager = require("./backend-manager");
const { peerMonitor, PEER_STATE } = require("./peer-monitor");
const { MobileServer } = require("./mobile-server");

// ── Frontend (Vite) Process Manager ──────────────────────────────────────
// Spawns `npm run dev` in frontend-v2/ with auto-restart on crash.
class FrontendManager {
  constructor() {
    this._process = null;
    this._running = false;
    this._crashCount = 0;
    this._maxCrashes = 10;
    this._crashWindowMs = 15 * 60 * 1000; // 15 minutes
    this._crashTimestamps = [];
    this._baseDelay = 3000;
    this._maxDelay = 60000;
    this._repoRoot = path.resolve(__dirname, "..");
    this._frontendDir = path.join(this._repoRoot, "frontend-v2");
    this._port = 3000; // matches vite.config.js VITE_PORT default
  }

  async start() {
    if (this._running && this._process) {
      log.info("[FrontendManager] Already running");
      return;
    }
    this._running = true;
    this._spawn();
  }

  _spawn() {
    if (!this._running) return;

    // Prune old crashes outside the window
    const now = Date.now();
    this._crashTimestamps = this._crashTimestamps.filter(
      (t) => now - t < this._crashWindowMs
    );

    if (this._crashTimestamps.length >= this._maxCrashes) {
      log.error(
        `[FrontendManager] Crash budget exhausted (${this._maxCrashes} in ${this._crashWindowMs / 60000}min) — stopping auto-restart`
      );
      this._running = false;
      return;
    }

    const isWin = process.platform === "win32";
    const npmCmd = isWin ? "npm.cmd" : "npm";

    log.info(`[FrontendManager] Spawning: ${npmCmd} run dev in ${this._frontendDir}`);

    this._process = spawn(npmCmd, ["run", "dev"], {
      cwd: this._frontendDir,
      stdio: ["ignore", "pipe", "pipe"],
      shell: false,
      env: { ...process.env, BROWSER: "none" }, // prevent Vite opening browser
    });

    this._process.stdout?.on("data", (data) => {
      const line = data.toString().trim();
      if (line) log.info(`[Vite] ${line}`);
    });

    this._process.stderr?.on("data", (data) => {
      const line = data.toString().trim();
      if (line) log.warn(`[Vite:err] ${line}`);
    });

    this._process.on("exit", (code, signal) => {
      log.warn(
        `[FrontendManager] Vite exited (code=${code}, signal=${signal})`
      );
      this._process = null;

      if (!this._running) return; // intentional stop

      this._crashTimestamps.push(Date.now());
      this._crashCount++;

      const delay = Math.min(
        this._baseDelay * Math.pow(2, this._crashCount - 1),
        this._maxDelay
      );
      log.info(
        `[FrontendManager] Auto-restart in ${delay / 1000}s (crash #${this._crashCount})`
      );
      setTimeout(() => this._spawn(), delay);
    });

    this._process.on("error", (err) => {
      log.error(`[FrontendManager] Spawn error: ${err.message}`);
      this._process = null;
    });
  }

  async stop() {
    this._running = false;
    if (this._process) {
      log.info("[FrontendManager] Stopping Vite dev server...");
      if (process.platform === "win32") {
        // On Windows, npm.cmd spawns a child cmd — kill the whole tree
        try {
          spawn("taskkill", ["/pid", String(this._process.pid), "/T", "/F"], {
            stdio: "ignore",
          });
        } catch (e) {
          this._process.kill("SIGTERM");
        }
      } else {
        this._process.kill("SIGTERM");
      }
      this._process = null;
    }
  }

  isRunning() {
    return this._running && this._process !== null;
  }

  /**
   * Check if Vite is actually serving HTTP on its port.
   */
  isReachable() {
    return new Promise((resolve) => {
      const req = http.get(`http://127.0.0.1:${this._port}`, (res) => {
        res.resume();
        resolve(res.statusCode >= 200 && res.statusCode < 400);
      });
      req.on("error", () => resolve(false));
      req.setTimeout(2000, () => {
        req.destroy();
        resolve(false);
      });
    });
  }
}

const frontendManager = new FrontendManager();

// Service definitions with start order and health check info
const SERVICE_DEFINITIONS = {
  backend: {
    order: 1,
    startFn: () => backendManager.startBackend(),
    stopFn: () => backendManager.stopBackend(),
    healthFn: function () {
      return this._healthCache["backend"] ?? backendManager.isRunning();
    },
    critical: true,
  },
  frontend: {
    order: 2,
    // Spawn Vite dev server as a managed child process with auto-restart
    startFn: () => frontendManager.start(),
    stopFn: () => frontendManager.stop(),
    healthFn: () => frontendManager.isRunning(),
    critical: true,
  },
  council: {
    order: 3,
    // Council runs inside the backend process
    startFn: async () => log.info("[Orchestrator] Council runs within backend"),
    stopFn: async () => {},
    healthFn: function () {
      return this._healthCache["council"] ?? backendManager.isRunning();
    },
    critical: false,
  },
  "ml-engine": {
    order: 4,
    startFn: async () => log.info("[Orchestrator] ML engine runs within backend"),
    stopFn: async () => {},
    healthFn: function () {
      return this._healthCache["ml-engine"] ?? backendManager.isRunning();
    },
    critical: false,
  },
  "event-pipeline": {
    order: 5,
    startFn: async () => log.info("[Orchestrator] Event pipeline runs within backend"),
    stopFn: async () => {},
    healthFn: () => backendManager.isRunning(),
    critical: false,
  },
  "brain-service": {
    order: 10,
    startFn: async () => {
      const { ollamaFallback } = require("./ollama-fallback");
      await ollamaFallback.initialize();
      log.info("[Orchestrator] Brain service initialized via Ollama");
    },
    stopFn: async () => {
      const { ollamaFallback } = require("./ollama-fallback");
      await ollamaFallback.shutdown();
    },
    healthFn: () => {
      const { ollamaFallback } = require("./ollama-fallback");
      return ollamaFallback.getStatus().available;
    },
    critical: false,
  },
  scanner: {
    order: 11,
    startFn: async () => log.info("[Orchestrator] Scanner runs within backend"),
    stopFn: async () => {},
    healthFn: function () {
      return this._healthCache["scanner"] ?? backendManager.isRunning();
    },
    critical: false,
  },
  "mobile-server": {
    order: 12,
    startFn: null, // set dynamically
    stopFn: null,
    healthFn: () => false,
    critical: false,
  },
};

class ServiceOrchestrator {
  constructor() {
    this._activeServices = new Map(); // serviceName -> { status, startedAt }
    this._role = null;
    this._fallbackActive = false;
    this._healthCache = {};
    this._healthLoopId = null;
  }

  /**
   * HTTP GET health check for a backend API path.
   */
  async _checkEndpoint(path, timeoutMs = 3000) {
    return new Promise((resolve) => {
      const port = deviceConfig.getBackendPort();
      const req = http.get(`http://127.0.0.1:${port}${path}`, (res) => {
        resolve(res.statusCode === 200);
      });
      req.on("error", () => resolve(false));
      req.setTimeout(timeoutMs, () => {
        req.destroy();
        resolve(false);
      });
    });
  }

  /**
   * Run health checks for backend-backed services and update cache.
   */
  async _runHealthChecks() {
    if (!backendManager.isRunning()) {
      this._healthCache["backend"] = false;
      this._healthCache["council"] = false;
      this._healthCache["ml-engine"] = false;
      this._healthCache["scanner"] = false;
      return;
    }
    const [backendOk, councilOk, mlOk, scannerOk] = await Promise.all([
      this._checkEndpoint("/api/v1/status"),
      this._checkEndpoint("/api/v1/agents/health"),
      this._checkEndpoint("/api/v1/ml-brain/status"),
      this._checkEndpoint("/api/v1/openclaw/scanner/status"),
    ]);
    this._healthCache["backend"] = backendOk;
    this._healthCache["council"] = councilOk;
    this._healthCache["ml-engine"] = mlOk;
    this._healthCache["scanner"] = scannerOk;
  }

  /**
   * Start the periodic health check loop (every 30s).
   */
  _startHealthLoop() {
    this._runHealthChecks().catch((err) =>
      log.warn("[Orchestrator] Health check error:", err?.message)
    );
    this._healthLoopId = setInterval(() => {
      this._runHealthChecks().catch((err) =>
        log.warn("[Orchestrator] Health check error:", err?.message)
      );
    }, 30000);
  }

  /**
   * Initialize orchestrator based on device role.
   */
  async initialize(role) {
    this._role = role || deviceConfig.getDeviceRole();
    const services = deviceConfig.getDeviceServices?.() || this._getServicesForRole(this._role);

    log.info(`[Orchestrator] Role: ${this._role}`);
    log.info(`[Orchestrator] Services to start: ${services.join(", ")}`);

    // Sort by dependency order
    const sorted = services
      .filter((s) => SERVICE_DEFINITIONS[s])
      .sort((a, b) => (SERVICE_DEFINITIONS[a].order || 99) - (SERVICE_DEFINITIONS[b].order || 99));

    // Wire up mobile-server dynamically when it is in the service list
    if (sorted.includes("mobile-server")) {
      this._mobileServer = new MobileServer({
        port: 8765,
        backendPort: deviceConfig.getBackendPort(),
      });
      const def = SERVICE_DEFINITIONS["mobile-server"];
      def.startFn = () => this._mobileServer.start();
      def.stopFn = () => this._mobileServer.stop();
      def.healthFn = () => this._mobileServer.isRunning();
    }

    // Start services sequentially (respecting dependency order)
    for (const serviceName of sorted) {
      try {
        await this._startService(serviceName);
      } catch (err) {
        const def = SERVICE_DEFINITIONS[serviceName];
        if (def?.critical) {
          throw new Error(`Critical service '${serviceName}' failed to start: ${err.message}`);
        }
        log.warn(`[Orchestrator] Non-critical service '${serviceName}' failed: ${err.message}`);
      }
    }

    // Start peer monitoring if in multi-PC mode
    if (this._role === "primary" || this._role === "secondary") {
      this._setupPeerMonitoring();
    }

    this._startHealthLoop();
    log.info(`[Orchestrator] All services started for role: ${this._role}`);
  }

  /**
   * Start a single service.
   */
  async _startService(serviceName) {
    const def = SERVICE_DEFINITIONS[serviceName];
    if (!def) {
      log.warn(`[Orchestrator] Unknown service: ${serviceName}`);
      return;
    }

    log.info(`[Orchestrator] Starting service: ${serviceName}`);
    this._activeServices.set(serviceName, { status: "starting", startedAt: null });

    if (def.startFn) {
      await def.startFn();
    }

    this._activeServices.set(serviceName, {
      status: "running",
      startedAt: new Date().toISOString(),
    });
    log.info(`[Orchestrator] Service started: ${serviceName}`);
  }

  /**
   * Get default services for a role.
   */
  _getServicesForRole(role) {
    switch (role) {
      case "full":
        return ["backend", "frontend", "council", "ml-engine", "event-pipeline", "brain-service", "scanner", "mobile-server"];
      case "primary":
        return ["backend", "frontend", "council", "ml-engine", "event-pipeline", "mobile-server"];
      case "secondary":
        return ["backend", "frontend", "brain-service", "scanner"];
      case "brain-only":
        return ["brain-service"];
      case "scanner-only":
        return ["scanner"];
      default:
        return ["backend", "frontend"];
    }
  }

  /**
   * Setup peer monitoring and fallback handlers.
   */
  _setupPeerMonitoring() {
    peerMonitor.start();

    peerMonitor.on("peer-lost", ({ peerId, peer }) => {
      log.warn(`[Orchestrator] Peer lost: ${peerId} (role=${peer.role})`);
      this._handlePeerLost(peerId, peer);
    });

    peerMonitor.on("peer-recovered", ({ peerId, peer }) => {
      log.info(`[Orchestrator] Peer recovered: ${peerId}`);
      this._handlePeerRecovered(peerId, peer);
    });

    peerMonitor.on("peer-degraded", ({ peerId, peer }) => {
      log.warn(`[Orchestrator] Peer degraded: ${peerId}`);
    });
  }

  /**
   * Handle a peer going offline — activate fallback services if needed.
   */
  async _handlePeerLost(peerId, peer) {
    if (this._role !== "primary") return;

    // If the lost peer was running brain-service, activate local Ollama fallback
    if (peer.services && peer.services.includes("brain-service")) {
      log.warn("[Orchestrator] Brain service peer lost — activating local Ollama fallback");
      try {
        const { ollamaFallback } = require("./ollama-fallback");
        await ollamaFallback.activate();
        this._fallbackActive = true;
      } catch (err) {
        log.error("[Orchestrator] Failed to activate Ollama fallback:", err.message);
      }
    }

    // Tighten risk parameters when running in degraded mode
    try {
      const port = deviceConfig.getBackendPort();
      // Notify backend to enter degraded mode
      const req = http.request({
        hostname: "127.0.0.1",
        port,
        path: "/api/v1/cluster/degraded",
        method: "POST",
        headers: { "Content-Type": "application/json" },
      });
      req.write(JSON.stringify({ peerId, lostServices: peer.services }));
      req.end();
    } catch (err) {
      log.debug("[Orchestrator] Could not notify backend of degraded mode:", err.message);
    }
  }

  /**
   * Handle a peer coming back online — deactivate fallbacks.
   */
  async _handlePeerRecovered(peerId, peer) {
    if (this._fallbackActive) {
      log.info("[Orchestrator] Peer recovered — deactivating local fallbacks");
      try {
        const { ollamaFallback } = require("./ollama-fallback");
        await ollamaFallback.deactivate();
        this._fallbackActive = false;
      } catch (err) {
        log.warn("[Orchestrator] Error deactivating fallback:", err.message);
      }
    }

    // Notify backend to restore normal mode
    try {
      const port = deviceConfig.getBackendPort();
      const req = http.request({
        hostname: "127.0.0.1",
        port,
        path: "/api/v1/cluster/restored",
        method: "POST",
        headers: { "Content-Type": "application/json" },
      });
      req.write(JSON.stringify({ peerId, restoredServices: peer.services }));
      req.end();
    } catch (err) {
      log.debug("[Orchestrator] Could not notify backend of restoration:", err.message);
    }
  }

  /**
   * Stop all services gracefully.
   */
  async shutdown() {
    log.info("[Orchestrator] Shutting down all services...");
    if (this._healthLoopId) {
      clearInterval(this._healthLoopId);
      this._healthLoopId = null;
    }
    peerMonitor.stop();

    // Stop in reverse order
    const services = Array.from(this._activeServices.keys()).reverse();
    for (const serviceName of services) {
      try {
        const def = SERVICE_DEFINITIONS[serviceName];
        if (def?.stopFn) await def.stopFn();
        this._activeServices.delete(serviceName);
        log.info(`[Orchestrator] Stopped: ${serviceName}`);
      } catch (err) {
        log.warn(`[Orchestrator] Error stopping ${serviceName}:`, err.message);
      }
    }
  }

  /**
   * Get status of all managed services.
   */
  getStatus() {
    const services = {};
    for (const [name, info] of this._activeServices) {
      const def = SERVICE_DEFINITIONS[name];
      services[name] = {
        ...info,
        healthy: def?.healthFn ? def.healthFn.call(this) : false,
      };
    }

    return {
      role: this._role,
      fallbackActive: this._fallbackActive,
      services,
      healthCache: { ...this._healthCache },
      cluster: peerMonitor.getClusterHealth(),
    };
  }
}

const serviceOrchestrator = new ServiceOrchestrator();

module.exports = { serviceOrchestrator, frontendManager };