/**
 * Backend Process Manager
 * Spawns and manages the Python/FastAPI backend as a child process.
 * Handles health checks, graceful shutdown, and auto-restart.
 */
const { spawn } = require("child_process");
const path = require("path");
const http = require("http");
const fs = require("fs");
const log = require("electron-log");
const deviceConfig = require("./device-config");

let backendProcess = null;
let healthCheckInterval = null;
let isShuttingDown = false;
let restartCount = 0;

function getBackendPath() {
  const isDev = process.env.NODE_ENV === "development";

  if (isDev) {
    // In development, run uvicorn directly
    return { mode: "dev", cwd: path.join(__dirname, "..", "backend") };
  }

  // In production, use PyInstaller-bundled binary
  const resourcesPath = process.resourcesPath || path.join(__dirname, "..");
  const backendDir = path.join(resourcesPath, "backend");

  if (process.platform === "win32") {
    return { mode: "prod", binary: path.join(backendDir, "embodier-backend.exe"), cwd: backendDir };
  }
  return { mode: "prod", binary: path.join(backendDir, "embodier-backend"), cwd: backendDir };
}

function getDataDir() {
  const { app } = require("electron");
  const dataDir = path.join(app.getPath("userData"), "data");
  if (!fs.existsSync(dataDir)) {
    fs.mkdirSync(dataDir, { recursive: true });
  }
  return dataDir;
}

function buildEnvVars() {
  const port = deviceConfig.getBackendPort();
  const apiKeys = deviceConfig.getApiKeys();
  const tradingMode = deviceConfig.getTradingMode();

  return {
    ...process.env,
    PORT: String(port),
    HOST: "127.0.0.1",
    TRADING_MODE: tradingMode,
    AUTO_EXECUTE_TRADES: "false",
    DATA_DIR: getDataDir(),
    DUCKDB_PATH: path.join(getDataDir(), "analytics.duckdb"),
    // API Keys
    ALPACA_API_KEY: apiKeys.alpacaApiKey || "",
    ALPACA_SECRET_KEY: apiKeys.alpacaSecretKey || "",
    ALPACA_BASE_URL: apiKeys.alpacaBaseUrl || "https://api.alpaca.markets",
    ALPACA_FEED: "sip",
    BRAIN_ENABLED: apiKeys.brainHost !== "disabled" ? "true" : "false",
    BRAIN_HOST: apiKeys.brainHost || "localhost",
    BRAIN_PORT: String(apiKeys.brainPort || 50051),
    FINVIZ_EMAIL: apiKeys.finvizEmail || "",
    FRED_API_KEY: apiKeys.fredApiKey || "",
    NEWS_API_KEY: apiKeys.newsApiKey || "",
    STOCKGEIST_TOKEN: apiKeys.stockgeistToken || "",
    // Prevent Python from buffering stdout
    PYTHONUNBUFFERED: "1",
  };
}

function isPortAvailable(port) {
  return new Promise((resolve) => {
    const net = require("net");
    const server = net.createServer();
    server.once("error", () => resolve(false));
    server.once("listening", () => {
      server.close();
      resolve(true);
    });
    server.listen(port, "127.0.0.1");
  });
}

function startBackend() {
  return new Promise(async (resolve, reject) => {
    if (backendProcess) {
      log.info("Backend already running");
      resolve();
      return;
    }

    isShuttingDown = false;
    const backendPath = getBackendPath();
    const port = deviceConfig.getBackendPort();

    const portFree = await isPortAvailable(port);
    if (!portFree) {
      reject(new Error(`Port ${port} is already in use. Change the backend port in Settings.`));
      return;
    }

    const env = buildEnvVars();

    log.info(`Starting backend (${backendPath.mode}) on port ${port}...`);

    if (backendPath.mode === "dev") {
      // Development: run uvicorn directly
      backendProcess = spawn(
        "python",
        ["-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", String(port)],
        { cwd: backendPath.cwd, env, stdio: ["ignore", "pipe", "pipe"] }
      );
    } else {
      // Production: run bundled binary
      if (!fs.existsSync(backendPath.binary)) {
        reject(
          new Error(
            `Backend binary not found at: ${backendPath.binary}\nRun 'npm run build:backend' to build the PyInstaller package.`
          )
        );
        return;
      }
      backendProcess = spawn(backendPath.binary, [], {
        cwd: backendPath.cwd,
        env,
        stdio: ["ignore", "pipe", "pipe"],
      });
    }

    backendProcess.stdout.on("data", (data) => {
      const line = data.toString().trim();
      if (line) log.info(`[backend] ${line}`);
    });

    backendProcess.stderr.on("data", (data) => {
      const line = data.toString().trim();
      if (line) log.warn(`[backend] ${line}`);
    });

    backendProcess.on("error", (err) => {
      log.error("Failed to start backend:", err.message);
      backendProcess = null;
      reject(err);
    });

    backendProcess.on("exit", (code, signal) => {
      log.info(`Backend exited (code=${code}, signal=${signal})`);
      backendProcess = null;
      if (!isShuttingDown && code !== 0) {
        restartCount++;
        if (restartCount > 5) {
          log.error("Backend crashed too many times (5), giving up auto-restart");
          return;
        }
        const delay = Math.min(3000 * Math.pow(2, restartCount - 1), 60000);
        log.warn(`Backend crashed — restart #${restartCount} in ${delay}ms...`);
        setTimeout(() => {
          if (!isShuttingDown) startBackend().catch(() => {});
        }, delay);
      } else {
        restartCount = 0;
      }
    });

    // Wait for health check to pass
    waitForHealth(port, 30000)
      .then(() => {
        log.info("Backend is healthy and ready");
        startHealthMonitor(port);
        resolve();
      })
      .catch((err) => {
        log.error("Backend failed to become healthy:", err.message);
        reject(err);
      });
  });
}

function waitForHealth(port, timeoutMs) {
  const startTime = Date.now();
  return new Promise((resolve, reject) => {
    function check() {
      if (Date.now() - startTime > timeoutMs) {
        reject(new Error(`Backend health check timed out after ${timeoutMs}ms`));
        return;
      }

      const req = http.get(`http://127.0.0.1:${port}/healthz`, (res) => {
        if (res.statusCode === 200) {
          resolve();
        } else {
          setTimeout(check, 500);
        }
      });

      req.on("error", () => {
        setTimeout(check, 500);
      });

      req.setTimeout(2000, () => {
        req.destroy();
        setTimeout(check, 500);
      });
    }

    check();
  });
}

function startHealthMonitor(port) {
  if (healthCheckInterval) clearInterval(healthCheckInterval);

  healthCheckInterval = setInterval(() => {
    if (isShuttingDown) return;

    const req = http.get(`http://127.0.0.1:${port}/healthz`, (res) => {
      if (res.statusCode !== 200) {
        log.warn(`Backend health check failed: status ${res.statusCode}`);
      }
    });

    req.on("error", (err) => {
      log.warn(`Backend health check error: ${err.message}`);
    });

    req.setTimeout(5000, () => {
      req.destroy();
      log.warn("Backend health check timed out");
    });
  }, 15000);
}

function stopBackend() {
  return new Promise((resolve) => {
    isShuttingDown = true;

    if (healthCheckInterval) {
      clearInterval(healthCheckInterval);
      healthCheckInterval = null;
    }

    if (!backendProcess) {
      resolve();
      return;
    }

    log.info("Stopping backend...");

    const forceKillTimeout = setTimeout(() => {
      if (backendProcess) {
        log.warn("Backend did not stop gracefully, force killing...");
        backendProcess.kill("SIGKILL");
        backendProcess = null;
        resolve();
      }
    }, 10000);

    backendProcess.on("exit", () => {
      clearTimeout(forceKillTimeout);
      backendProcess = null;
      log.info("Backend stopped");
      resolve();
    });

    // Graceful shutdown
    if (process.platform === "win32") {
      backendProcess.kill("SIGTERM");
    } else {
      backendProcess.kill("SIGTERM");
    }
  });
}

function isRunning() {
  return backendProcess !== null;
}

function getStatus() {
  return {
    running: isRunning(),
    pid: backendProcess?.pid || null,
    port: deviceConfig.getBackendPort(),
  };
}

module.exports = { startBackend, stopBackend, isRunning, getStatus, getDataDir };
