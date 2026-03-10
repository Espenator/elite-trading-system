/**
 * Embodier Trader — Electron Main Process
 *
 * Lifecycle:
 *   1. Show splash screen
 *   2. If first run → show setup wizard
 *   3. Auto-update from git (pull + rebuild if needed)
 *   4. Start Python/FastAPI backend from venv
 *   5. Load React frontend from built dist/
 *   6. Show system tray
 *   7. On quit → graceful backend shutdown
 */
const {
  app,
  BrowserWindow,
  ipcMain,
  shell,
  dialog,
  Menu,
  screen,
} = require("electron");
const path = require("path");
const fs = require("fs");
const log = require("electron-log");
const deviceConfig = require("./device-config");
const backendManager = require("./backend-manager");
const autoUpdater = require("./auto-updater");
const { createTray, updateMenu, destroyTray } = require("./tray");
const { peerMonitor } = require("./peer-monitor");
const { serviceOrchestrator } = require("./service-orchestrator");
const { ollamaFallback } = require("./ollama-fallback");

// Configure logging
log.transports.file.level = "info";
log.transports.console.level = "debug";

let mainWindow = null;
let splashWindow = null;

// Prevent multiple instances
const gotLock = app.requestSingleInstanceLock();
if (!gotLock) {
  app.quit();
  process.exit(0);
}

app.on("second-instance", () => {
  if (mainWindow) {
    if (mainWindow.isMinimized()) mainWindow.restore();
    mainWindow.focus();
  }
});

// ── Splash Screen ──────────────────────────────────────────────────────────

function createSplashWindow() {
  splashWindow = new BrowserWindow({
    width: 480,
    height: 360,
    frame: false,
    transparent: true,
    resizable: false,
    alwaysOnTop: true,
    skipTaskbar: true,
    webPreferences: {
      nodeIntegration: false,
      contextIsolation: true,
    },
  });

  splashWindow.loadFile(path.join(__dirname, "pages", "splash.html"));
  splashWindow.center();
  return splashWindow;
}

function updateSplashStatus(text) {
  if (splashWindow && !splashWindow.isDestroyed()) {
    const escaped = JSON.stringify(text);
    splashWindow.webContents.executeJavaScript(
      `(function() {
        var el = document.getElementById('status-text');
        if (el) el.textContent = ${escaped};
      })()`
    ).catch(() => {});
  }
}

// ── Setup Wizard ───────────────────────────────────────────────────────────

function showSetupWizard() {
  return new Promise((resolve) => {
    const setupWindow = new BrowserWindow({
      width: 720,
      height: 700,
      frame: false,
      resizable: false,
      webPreferences: {
        nodeIntegration: false,
        contextIsolation: true,
        preload: path.join(__dirname, "preload.js"),
      },
    });

    setupWindow.loadFile(path.join(__dirname, "pages", "setup.html"));
    setupWindow.center();

    ipcMain.once("setup-complete", (_event, config) => {
      deviceConfig.completeSetup(config);

      // Write .env file for the backend
      const envContent = deviceConfig.generateEnvFile(config);
      const backendDir = path.join(__dirname, "..", "backend");
      const envPath = path.join(backendDir, ".env");
      try {
        fs.writeFileSync(envPath, envContent, "utf8");
        log.info("Generated .env file for backend");
      } catch (err) {
        log.warn("Could not write .env:", err.message);
      }

      setupWindow.close();
      resolve(config);
    });

    setupWindow.on("closed", () => {
      resolve(null);
    });
  });
}

// ── Main Window ────────────────────────────────────────────────────────────

function createMainWindow() {
  const { width, height } = screen.getPrimaryDisplay().workAreaSize;

  mainWindow = new BrowserWindow({
    width: Math.min(1920, width),
    height: Math.min(1080, height),
    minWidth: 1024,
    minHeight: 700,
    title: `Embodier Trader — ${deviceConfig.getDeviceName()}`,
    icon: path.join(__dirname, "icons", process.platform === "win32" ? "icon.ico" : "icon.svg"),
    show: false,
    webPreferences: {
      nodeIntegration: false,
      contextIsolation: true,
      preload: path.join(__dirname, "preload.js"),
    },
  });

  // Application menu
  const menuTemplate = [
    {
      label: "Embodier Trader",
      submenu: [
        { label: `Device: ${deviceConfig.getDeviceName()}`, enabled: false },
        { label: `Mode: ${deviceConfig.getTradingMode().toUpperCase()}`, enabled: false },
        { type: "separator" },
        { label: "Settings", accelerator: "CmdOrCtrl+,", click: () => mainWindow.webContents.send("navigate", "/settings") },
        { label: "Check for Updates", click: () => manualUpdateCheck() },
        { type: "separator" },
        { label: "Quit", accelerator: "CmdOrCtrl+Q", click: () => app.quit() },
      ],
    },
    {
      label: "View",
      submenu: [
        { label: "Dashboard", accelerator: "CmdOrCtrl+1", click: () => mainWindow.webContents.send("navigate", "/") },
        { label: "Agents", accelerator: "CmdOrCtrl+2", click: () => mainWindow.webContents.send("navigate", "/agents") },
        { label: "Signals", accelerator: "CmdOrCtrl+3", click: () => mainWindow.webContents.send("navigate", "/signals") },
        { label: "Risk", accelerator: "CmdOrCtrl+4", click: () => mainWindow.webContents.send("navigate", "/risk") },
        { type: "separator" },
        { role: "reload" },
        { role: "toggleDevTools" },
        { type: "separator" },
        { role: "togglefullscreen" },
      ],
    },
    {
      label: "Trading",
      submenu: [
        { label: "Trade Execution", click: () => mainWindow.webContents.send("navigate", "/trade") },
        { label: "Backtesting", click: () => mainWindow.webContents.send("navigate", "/backtest") },
        { label: "Performance", click: () => mainWindow.webContents.send("navigate", "/performance") },
      ],
    },
    {
      label: "Help",
      submenu: [
        { label: "About Embodier Trader", click: () => showAbout() },
        { label: "Open Data Directory", click: () => shell.openPath(backendManager.getDataDir()) },
        { label: "View Logs", click: () => shell.openPath(log.transports.file.getFile().path) },
      ],
    },
  ];

  Menu.setApplicationMenu(Menu.buildFromTemplate(menuTemplate));

  // Load the frontend from the built dist/ directory
  loadFrontend();

  mainWindow.on("close", (event) => {
    // Minimize to tray instead of quitting
    if (!app.isQuitting) {
      event.preventDefault();
      mainWindow.hide();
    }
  });

  mainWindow.on("closed", () => {
    mainWindow = null;
  });

  return mainWindow;
}

function loadFrontend() {
  const port = deviceConfig.getBackendPort();
  const frontendDist = path.join(__dirname, "..", "frontend-v2", "dist", "index.html");

  if (fs.existsSync(frontendDist)) {
    // Serve from built frontend files
    log.info(`Loading frontend from: ${frontendDist}`);
    mainWindow.loadFile(frontendDist);
  } else if (process.resourcesPath) {
    // Packaged build: check resources path
    const packagedFrontend = path.join(process.resourcesPath, "frontend", "index.html");
    if (fs.existsSync(packagedFrontend)) {
      mainWindow.loadFile(packagedFrontend);
    } else {
      mainWindow.loadURL(`http://127.0.0.1:${port}`);
    }
  } else {
    // Last resort: load from backend
    mainWindow.loadURL(`http://127.0.0.1:${port}`);
  }
}

async function manualUpdateCheck() {
  try {
    const result = await autoUpdater.checkForUpdates((status) => {
      log.info(`Manual update: ${status}`);
    });

    if (result.updated) {
      const response = await dialog.showMessageBox(mainWindow, {
        type: "info",
        title: "Update Available",
        message: "Updates were downloaded. Restart to apply?",
        detail: `${result.changedFiles.length} files updated.`,
        buttons: ["Restart Now", "Later"],
      });
      if (response.response === 0) {
        app.relaunch();
        app.quit();
      }
    } else {
      dialog.showMessageBox(mainWindow, {
        type: "info",
        title: "No Updates",
        message: "Embodier Trader is up to date.",
      });
    }
  } catch (err) {
    dialog.showMessageBox(mainWindow, {
      type: "error",
      title: "Update Error",
      message: "Could not check for updates.",
      detail: err.message,
    });
  }
}

function showAbout() {
  const sys = deviceConfig.getSystemInfo();
  const deviceName = deviceConfig.getDeviceName();
  const deviceRole = deviceConfig.getDeviceRole();
  const status = backendManager.getStatus();

  dialog.showMessageBox(mainWindow, {
    type: "info",
    title: "About Embodier Trader",
    message: "Embodier Trader",
    detail: [
      `Version: ${app.getVersion()}`,
      `Device: ${deviceName} (${deviceRole})`,
      `Trading Mode: ${deviceConfig.getTradingMode().toUpperCase()}`,
      `Backend: ${status.running ? `running (port ${status.port}, ${status.mode})` : "stopped"}`,
      `Platform: ${sys.platform} ${sys.arch}`,
      `CPUs: ${sys.cpus} cores | Memory: ${sys.totalMemoryGB} GB`,
      sys.isAppleSilicon ? "Apple Silicon: Yes" : "",
      "",
      "AI-Powered Trading Platform",
      "33-Agent Council | Event-Driven Pipeline",
      "",
      "© 2026 Embodier.ai",
    ]
      .filter(Boolean)
      .join("\n"),
  });
}

// ── IPC Handlers ───────────────────────────────────────────────────────────

function registerIpcHandlers() {
  ipcMain.handle("get-device-config", () => deviceConfig.getFullConfig());
  ipcMain.handle("get-system-info", () => deviceConfig.getSystemInfo());
  ipcMain.handle("get-backend-status", () => backendManager.getStatus());
  ipcMain.handle("get-orchestrator-status", () => serviceOrchestrator.getStatus());
  ipcMain.handle("get-version", () => app.getVersion());
  ipcMain.handle("get-api-keys", () => deviceConfig.getApiKeys());
  ipcMain.handle("get-auth-token", () => deviceConfig.getAuthToken());
  ipcMain.handle("get-peer-devices", () => deviceConfig.getPeerDevices());

  ipcMain.handle("set-api-keys", (_event, keys) => {
    deviceConfig.setApiKeys(keys);
    return { ok: true };
  });

  ipcMain.handle("set-trading-mode", async (_event, mode) => {
    deviceConfig.setTradingMode(mode);
    // Restart backend with new mode
    await backendManager.stopBackend();
    await backendManager.startBackend();
    if (mainWindow) mainWindow.webContents.send("backend-status", backendManager.getStatus());
    return { ok: true, mode };
  });

  ipcMain.handle("add-peer-device", (_event, peer) => {
    deviceConfig.addPeerDevice(peer);
    return { ok: true };
  });

  ipcMain.handle("remove-peer-device", (_event, id) => {
    deviceConfig.removePeerDevice(id);
    return { ok: true };
  });

  ipcMain.handle("restart-backend", async () => {
    await backendManager.stopBackend();
    await backendManager.startBackend();
    if (mainWindow) mainWindow.webContents.send("backend-status", backendManager.getStatus());
    updateMenu(mainWindow);
    return backendManager.getStatus();
  });

  ipcMain.handle("check-for-updates", async () => {
    return await autoUpdater.checkForUpdates((status) => log.info(status));
  });

  ipcMain.handle("open-external", (_event, url) => shell.openExternal(url));
  ipcMain.handle("open-data-dir", () => shell.openPath(backendManager.getDataDir()));

  ipcMain.on("window-minimize", () => mainWindow?.minimize());
  ipcMain.on("window-maximize", () => {
    if (mainWindow?.isMaximized()) mainWindow.unmaximize();
    else mainWindow?.maximize();
  });
  ipcMain.on("window-close", () => mainWindow?.close());
}

// ── App Lifecycle ──────────────────────────────────────────────────────────

app.whenReady().then(async () => {
  log.info("=".repeat(60));
  log.info("Embodier Trader starting...");
  log.info(`Version: ${app.getVersion()}`);
  log.info(`Platform: ${process.platform} ${process.arch}`);
  log.info(`Device: ${deviceConfig.getDeviceName()} (${deviceConfig.getDeviceRole()})`);
  log.info(`Trading Mode: ${deviceConfig.getTradingMode()}`);
  log.info("=".repeat(60));

  registerIpcHandlers();

  // Show splash
  createSplashWindow();

  // First-run setup
  if (deviceConfig.isFirstRun()) {
    log.info("First run detected — showing setup wizard");
    if (splashWindow) splashWindow.close();
    const config = await showSetupWizard();
    if (!config) {
      log.info("Setup cancelled — quitting");
      app.quit();
      return;
    }
    createSplashWindow();
  }

  // Auto-update + environment setup
  try {
    updateSplashStatus("Checking for updates...");
    const setupResult = await autoUpdater.runStartupSequence((status) => {
      updateSplashStatus(status);
      log.info(`[startup] ${status}`);
    });

    if (setupResult.updateCheck?.updated) {
      log.info(`Updated: ${setupResult.updateCheck.changedFiles.length} files changed`);
    }
    if (setupResult.errors.length > 0) {
      log.warn("Startup warnings:", setupResult.errors);
    }
  } catch (err) {
    log.error("Startup setup failed:", err.message);
    if (splashWindow && !splashWindow.isDestroyed()) splashWindow.close();

    const result = await dialog.showMessageBox({
      type: "error",
      title: "Setup Error",
      message: "Embodier Trader could not complete setup.",
      detail: `${err.message}\n\nMake sure Python 3.10+ and Node.js 18+ are installed and available in PATH.`,
      buttons: ["Retry", "Quit"],
    });
    if (result.response === 0) {
      app.relaunch();
    }
    app.quit();
    return;
  }

  // Start backend
  try {
    updateSplashStatus("Starting trading backend...");
    await backendManager.startBackend();
    log.info("Backend is ready");
  } catch (err) {
    log.error("Backend failed to start:", err.message);
    if (splashWindow && !splashWindow.isDestroyed()) splashWindow.close();
    const result = await dialog.showMessageBox({
      type: "error",
      title: "Backend Error",
      message: "Embodier Trader backend failed to start.",
      detail: err.message,
      buttons: ["Retry", "Quit"],
    });
    if (result.response === 0) {
      app.relaunch();
    }
    app.quit();
    return;
  }

  // Initialize distributed system
  try {
    updateSplashStatus("Connecting to trading network...");
    await peerMonitor.initialize();
    await serviceOrchestrator.initialize(deviceConfig.getDeviceRole());
    log.info("Distributed system initialized");
  } catch (err) {
    log.warn("Distributed system init failed (standalone mode):", err.message);
  }

  // Create main window
  updateSplashStatus("Loading dashboard...");
  createMainWindow();
  mainWindow.once("ready-to-show", () => {
    if (splashWindow && !splashWindow.isDestroyed()) {
      splashWindow.close();
      splashWindow = null;
    }
    mainWindow.show();
    mainWindow.focus();
    log.info("Main window displayed — Embodier Trader is live");
  });

  // System tray
  createTray(mainWindow);
  log.info("System tray created");
});

app.on("before-quit", async (event) => {
  app.isQuitting = true;
  if (backendManager.isRunning()) {
    event.preventDefault();
    log.info("Shutting down backend before quit...");
    await peerMonitor.shutdown();
    await serviceOrchestrator.shutdown();
    await ollamaFallback.shutdown();
    await backendManager.stopBackend();
    destroyTray();
    app.quit();
  }
});

app.on("window-all-closed", () => {
  // Stay in tray on all platforms
});

app.on("activate", () => {
  // macOS dock click
  if (mainWindow) {
    mainWindow.show();
  }
});
