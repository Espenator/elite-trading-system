/**
 * Embodier Trader — Electron Main Process
 *
 * Lifecycle:
 *   1. Show splash screen
 *   2. If first run → show setup wizard
 *   3. Start Python/FastAPI backend
 *   4. Wait for health check
 *   5. Load React frontend in main window
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
    icon: path.join(__dirname, "icons", "icon.png"),
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
        { type: "separator" },
        { label: "Settings", accelerator: "CmdOrCtrl+,", click: () => mainWindow.webContents.send("navigate", "/settings") },
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
        { type: "separator" },
        { label: `Mode: ${deviceConfig.getTradingMode().toUpperCase()}`, enabled: false },
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

  // Load the frontend
  const isDev = process.env.NODE_ENV === "development";
  const port = deviceConfig.getBackendPort();

  if (isDev) {
    // In dev, load from Vite dev server
    mainWindow.loadURL("http://localhost:3000");
  } else {
    // In production, serve the built frontend through the backend
    const frontendPath = path.join(process.resourcesPath || __dirname, "frontend", "index.html");
    if (fs.existsSync(frontendPath)) {
      mainWindow.loadFile(frontendPath);
    } else {
      // Fallback: load from the backend's static serving
      mainWindow.loadURL(`http://127.0.0.1:${port}`);
    }
  }

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

function showAbout() {
  const sys = deviceConfig.getSystemInfo();
  const deviceName = deviceConfig.getDeviceName();
  const deviceRole = deviceConfig.getDeviceRole();

  dialog.showMessageBox(mainWindow, {
    type: "info",
    title: "About Embodier Trader",
    message: "Embodier Trader",
    detail: [
      `Version: ${app.getVersion()}`,
      `Device: ${deviceName} (${deviceRole})`,
      `Platform: ${sys.platform} ${sys.arch}`,
      `CPUs: ${sys.cpus} cores`,
      `Memory: ${sys.totalMemoryGB} GB`,
      sys.isAppleSilicon ? "Apple Silicon: Yes" : "",
      "",
      "AI-Powered Trading Platform",
      "11-Agent Council | Event-Driven Pipeline",
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
  ipcMain.handle("get-version", () => app.getVersion());
  ipcMain.handle("get-api-keys", () => deviceConfig.getApiKeys());
  ipcMain.handle("get-auth-token", () => deviceConfig.getAuthToken());
  ipcMain.handle("get-peer-devices", () => deviceConfig.getPeerDevices());

  ipcMain.handle("set-api-keys", (_event, keys) => {
    deviceConfig.setApiKeys(keys);
    return { ok: true };
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

  // Start backend
  try {
    await backendManager.startBackend();
    log.info("Backend is ready");
  } catch (err) {
    log.error("Backend failed to start:", err.message);
    if (splashWindow) splashWindow.close();
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
    await peerMonitor.initialize();
    await serviceOrchestrator.initialize(deviceConfig.getDeviceRole());
    log.info("Distributed system initialized");
  } catch (err) {
    log.warn("Distributed system init failed (standalone mode):", err.message);
  }

  // Create main window
  createMainWindow();
  mainWindow.once("ready-to-show", () => {
    if (splashWindow) {
      splashWindow.close();
      splashWindow = null;
    }
    mainWindow.show();
    mainWindow.focus();
    log.info("Main window displayed");
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
  // On macOS, keep running in tray
  if (process.platform !== "darwin") {
    // On Windows/Linux, don't quit — stay in tray
  }
});

app.on("activate", () => {
  // macOS dock click
  if (mainWindow) {
    mainWindow.show();
  }
});
