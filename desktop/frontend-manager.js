/**
 * Frontend Process Manager
 * In dev mode, spawns `npm run dev` in frontend-v2/ and monitors it.
 * Auto-restarts if the process dies unexpectedly.
 */
const { spawn } = require("child_process");
const path = require("path");
const http = require("http");
const log = require("electron-log");

let frontendProcess = null;
let isShuttingDown = false;

const FRONTEND_PORT = 3000;
const FRONTEND_DIR = path.join(__dirname, "..", "frontend-v2");

function startFrontend() {
  return new Promise((resolve, reject) => {
    if (frontendProcess) {
      log.info("Frontend already running");
      resolve();
      return;
    }

    isShuttingDown = false;
    log.info(`Starting frontend dev server on port ${FRONTEND_PORT}...`);

    const isWin = process.platform === "win32";
    const cmd = isWin ? "npm.cmd" : "npm";

    frontendProcess = spawn(cmd, ["run", "dev"], {
      cwd: FRONTEND_DIR,
      env: { ...process.env, BROWSER: "none" },
      stdio: ["ignore", "pipe", "pipe"],
      shell: isWin,
    });

    frontendProcess.stdout.on("data", (data) => {
      const line = data.toString().trim();
      if (line) log.info(`[frontend] ${line}`);
    });

    frontendProcess.stderr.on("data", (data) => {
      const line = data.toString().trim();
      if (line) log.warn(`[frontend] ${line}`);
    });

    frontendProcess.on("error", (err) => {
      log.error("Failed to start frontend:", err.message);
      frontendProcess = null;
      reject(err);
    });

    frontendProcess.on("exit", (code, signal) => {
      log.info(`Frontend exited (code=${code}, signal=${signal})`);
      frontendProcess = null;
      if (!isShuttingDown && code !== 0) {
        log.warn("Frontend crashed — restarting in 3s...");
        setTimeout(() => {
          if (!isShuttingDown) startFrontend().catch(() => {});
        }, 3000);
      }
    });

    // Wait for Vite to be ready
    waitForReady(FRONTEND_PORT, 30000)
      .then(() => {
        log.info("Frontend dev server is ready");
        resolve();
      })
      .catch((err) => {
        log.error("Frontend failed to start:", err.message);
        reject(err);
      });
  });
}

function waitForReady(port, timeoutMs) {
  const startTime = Date.now();
  return new Promise((resolve, reject) => {
    function check() {
      if (Date.now() - startTime > timeoutMs) {
        reject(new Error(`Frontend health check timed out after ${timeoutMs}ms`));
        return;
      }

      const req = http.get(`http://127.0.0.1:${port}/`, (res) => {
        if (res.statusCode < 500) {
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

function stopFrontend() {
  return new Promise((resolve) => {
    isShuttingDown = true;

    if (!frontendProcess) {
      resolve();
      return;
    }

    log.info("Stopping frontend...");

    const forceKillTimeout = setTimeout(() => {
      if (frontendProcess) {
        log.warn("Frontend did not stop gracefully, force killing...");
        frontendProcess.kill("SIGKILL");
        frontendProcess = null;
        resolve();
      }
    }, 5000);

    frontendProcess.on("exit", () => {
      clearTimeout(forceKillTimeout);
      frontendProcess = null;
      log.info("Frontend stopped");
      resolve();
    });

    frontendProcess.kill("SIGTERM");
  });
}

function isRunning() {
  return frontendProcess !== null;
}

module.exports = { startFrontend, stopFrontend, isRunning };
