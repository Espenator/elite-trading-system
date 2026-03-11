/**
 * Backend Process Manager
 *
 * Runs the Python/FastAPI backend from the repo's venv.
 * Handles health checks, graceful shutdown, and auto-restart.
 *
 * Mode priority:
 *   1. Repo venv (default) — runs from backend/venv/bin/python
 *   2. System python (fallback) — runs from global python3
 *   3. PyInstaller binary (packaged builds only)
 */
const { spawn } = require("child_process");
const path = require("path");
const http = require("http");
const fs = require("fs");
const log = require("electron-log");
const deviceConfig = require("./device-config");

const REPO_ROOT = path.join(__dirname, "..");
const BACKEND_DIR = path.join(REPO_ROOT, "backend");

let backendProcess = null;
let healthCheckInterval = null;
let isShuttingDown = false;
let restartCount = 0;

// ── Python Resolution ────────────────────────────────────────────────────────

function getVenvPython() {
  const venvDir = path.join(BACKEND_DIR, "venv");
  if (process.platform === "win32") {
    return path.join(venvDir, "Scripts", "python.exe");
  }
  return path.join(venvDir, "bin", "python");
}

function getBackendConfig() {
  const venvPython = getVenvPython();

  // Option 1: Repo venv (preferred — created by auto-updater)
  if (fs.existsSync(venvPython)) {
    return {
      mode: "venv",
      python: venvPython,
      cwd: BACKEND_DIR,
    };
  }

  // Option 2: PyInstaller binary (packaged/distributed builds)
  const resourcesPath = process.resourcesPath || path.join(__dirname, "..");
  const binaryDir = path.join(resourcesPath, "backend");
  const binaryName = process.platform === "win32" ? "embodier-backend.exe" : "embodier-backend";
  const binaryPath = path.join(binaryDir, binaryName);
  if (fs.existsSync(binaryPath)) {
    return {
      mode: "binary",
      binary: binaryPath,
      cwd: binaryDir,
    };
  }

  // Option 3: System python (last resort)
  return {
    mode: "system",
    python: process.platform === "win32" ? "python" : "python3",
    cwd: BACKEND_DIR,
  };
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
    AUTO_EXECUTE_TRADES: tradingMode === "live" ? "true" : "false",
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
    FINVIZ_API_KEY: apiKeys.finvizApiKey || "",
    FRED_API_KEY: apiKeys.fredApiKey || "",
    NEWS_API_KEY: apiKeys.newsApiKey || "",
    UNUSUAL_WHALES_API_KEY: apiKeys.unusualWhalesToken || "",
    STOCKGEIST_API_KEY: apiKeys.stockgeistToken || "",
    DISCORD_BOT_TOKEN: apiKeys.discordBotToken || "",
    X_BEARER_TOKEN: apiKeys.xBearerToken || "",
    YOUTUBE_API_KEY: apiKeys.youtubeApiKey || "",
    // LLM cloud APIs
    ANTHROPIC_API_KEY: apiKeys.anthropicApiKey || "",
    PERPLEXITY_API_KEY: apiKeys.perplexityApiKey || "",
    // Auth token for API security
    API_AUTH_TOKEN: deviceConfig.getAuthToken(),
    // Council
    COUNCIL_GATE_ENABLED: "true",
    // Prevent Python from buffering stdout
    PYTHONUNBUFFERED: "1",
    // Ensure .env file is also loaded by backend
    ENVIRONMENT: "production",
  };
}

// ── Port Check ───────────────────────────────────────────────────────────────

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

async function killProcessOnPort(port) {
  // Auto-clean stale processes on our port
  try {
    if (process.platform === "win32") {
      const { execSync } = require("child_process");
      const result = execSync(`netstat -ano | findstr :${port}`, { encoding: "utf8", timeout: 5000 });
      const lines = result.split("\n").filter((l) => l.includes("LISTENING"));
      for (const line of lines) {
        const pid = line.trim().split(/\s+/).pop();
        if (pid && pid !== "0") {
          log.info(`Killing stale process on port ${port} (PID ${pid})`);
          execSync(`taskkill /PID ${pid} /F`, { timeout: 5000 });
        }
      }
    } else {
      const { execSync } = require("child_process");
      const result = execSync(`lsof -ti:${port}`, { encoding: "utf8", timeout: 5000 });
      const pids = result.trim().split("\n").filter(Boolean);
      for (const pid of pids) {
        log.info(`Killing stale process on port ${port} (PID ${pid})`);
        execSync(`kill -9 ${pid}`, { timeout: 5000 });
      }
    }
  } catch {
    // No process found or kill failed — that's fine
  }
}

// ── Start / Stop ─────────────────────────────────────────────────────────────

function startBackend() {
  return new Promise(async (resolve, reject) => {
    if (backendProcess) {
      log.info("Backend already running");
      resolve();
      return;
    }

    isShuttingDown = false;
    const config = getBackendConfig();
    const port = deviceConfig.getBackendPort();

    // Auto-kill stale processes on our port
    const portFree = await isPortAvailable(port);
    if (!portFree) {
      log.warn(`Port ${port} in use — attempting to free it`);
      await killProcessOnPort(port);
      // Wait a moment for port to be released
      await new Promise((r) => setTimeout(r, 1000));
      const stillBusy = !(await isPortAvailable(port));
      if (stillBusy) {
        reject(new Error(`Port ${port} is still in use. Close the other application or change the backend port in Settings.`));
        return;
      }
    }

    const env = buildEnvVars();
    log.info(`Starting backend (${config.mode}) on port ${port}...`);

    if (config.mode === "binary") {
      // PyInstaller binary
      if (!fs.existsSync(config.binary)) {
        reject(new Error(`Backend binary not found: ${config.binary}`));
        return;
      }
      backendProcess = spawn(config.binary, [], {
        cwd: config.cwd,
        env,
        stdio: ["ignore", "pipe", "pipe"],
      });
    } else {
      // Venv or system python — use run_server.py for consistent startup
      // (handles loop="asyncio", access_log, .env loading)
      const python = config.python;
      const runServer = path.join(BACKEND_DIR, "run_server.py");
      if (fs.existsSync(runServer)) {
        backendProcess = spawn(
          python,
          [runServer],
          { cwd: config.cwd, env, stdio: ["ignore", "pipe", "pipe"] }
        );
      } else {
        // Fallback: direct uvicorn
        backendProcess = spawn(
          python,
          ["-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", String(port)],
          { cwd: config.cwd, env, stdio: ["ignore", "pipe", "pipe"] }
        );
      }
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
    waitForHealth(port, 60_000)
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
        reject(new Error(`Backend health check timed out after ${timeoutMs / 1000}s`));
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
    backendProcess.kill("SIGTERM");
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
    mode: getBackendConfig().mode,
  };
}

module.exports = { startBackend, stopBackend, isRunning, getStatus, getDataDir };
