// Embodier Trader — Electron main process
// Launches services via ServiceOrchestrator, monitors peers, and serves the UI.
// PC1 (ESPENMAIN): primary controller — runs council, ml-engine, event-pipeline
// PC2 (ProfitTrader): secondary — runs brain-service (Ollama/gRPC), scanner

const { app, BrowserWindow, ipcMain, Tray, Menu, nativeImage, shell } = require('electron');
const path = require('path');
const fs = require('fs');
const http = require('http');

const deviceConfig = require('./device-config');
const backendManager = require('./backend-manager');
const { serviceOrchestrator } = require('./service-orchestrator');
const { peerMonitor } = require('./peer-monitor');

const isDev = process.env.NODE_ENV === 'development' || !app.isPackaged;
let appQuitting = false;

// Read ports from .embodier-ports.json (written by run_full_stack_24_7 / start-embodier)
function _readPortsJson() {
  const portsPath = path.join(__dirname, '..', '.embodier-ports.json');
  try {
    if (fs.existsSync(portsPath)) {
      const raw = fs.readFileSync(portsPath, 'utf8');
      return JSON.parse(raw);
    }
  } catch (_) {}
  return {};
}

// In dev, frontend URL from .embodier-ports.json or default 5173
function getDevFrontendUrl() {
  const ports = _readPortsJson();
  const port = ports.frontendPort || 5173;
  return `http://localhost:${port}`;
}

// Backend port from .embodier-ports.json, then device-config store, then default 8000
function getResolvedBackendPort() {
  const ports = _readPortsJson();
  if (ports.backendPort) return ports.backendPort;
  return deviceConfig.getBackendPort() || 8000;
}

// Fix Electron cache permission error — set cache path before any window creation
app.setPath('cache', path.join(app.getPath('userData'), 'Cache'));

let mainWindow = null;
let setupWindow = null;
let splashWindow = null;
let tray = null;

// ── Splash Window ─────────────────────────────────────────────────────────
function createSplashWindow() {
  splashWindow = new BrowserWindow({
    width: 480,
    height: 320,
    transparent: false,
    frame: false,
    alwaysOnTop: true,
    center: true,
    resizable: false,
    webPreferences: { nodeIntegration: false, contextIsolation: true },
  });
  splashWindow.loadFile(path.join(__dirname, 'pages', 'splash.html'));
  splashWindow.show();
}

function closeSplash() {
  if (splashWindow) {
    splashWindow.close();
    splashWindow = null;
  }
}

// ── URL Availability Check ────────────────────────────────────────────────
/**
 * Polls a URL until it responds with HTTP 2xx/3xx.
 * Used to wait for Vite dev server before loading it in BrowserWindow.
 */
function waitForUrl(url, timeoutMs = 30000) {
  const startTime = Date.now();
  return new Promise((resolve, reject) => {
    function check() {
      if (appQuitting) { reject(new Error('App is quitting')); return; }
      if (Date.now() - startTime > timeoutMs) {
        reject(new Error(`Timed out waiting for ${url} after ${timeoutMs / 1000}s`));
        return;
      }
      const req = http.get(url, (res) => {
        // Consume response data to free up memory
        res.resume();
        if (res.statusCode >= 200 && res.statusCode < 400) {
          resolve();
        } else {
          setTimeout(check, 500);
        }
      });
      req.on('error', () => setTimeout(check, 500));
      req.setTimeout(2000, () => { req.destroy(); setTimeout(check, 500); });
    }
    check();
  });
}

// ── Setup Wizard Window ───────────────────────────────────────────────────
function createSetupWindow() {
  setupWindow = new BrowserWindow({
    width: 640,
    height: 720,
    frame: false,
    center: true,
    resizable: false,
    backgroundColor: '#0a0e1a',
    webPreferences: {
      nodeIntegration: false,
      contextIsolation: true,
      preload: path.join(__dirname, 'preload.js'),
    },
  });
  setupWindow.loadFile(path.join(__dirname, 'pages', 'setup.html'));
  setupWindow.show();
}

// ── Main Window ───────────────────────────────────────────────────────────
async function createMainWindow() {
  const port = getResolvedBackendPort();

  mainWindow = new BrowserWindow({
    width: 1920,
    height: 1080,
    minWidth: 1280,
    minHeight: 720,
    title: 'Embodier Trader',
    backgroundColor: '#0B0E14',
    frame: true,
    show: false,
    webPreferences: {
      nodeIntegration: false,
      contextIsolation: true,
      preload: path.join(__dirname, 'preload.js'),
    },
  });

  // ── Close / external-link handlers (always needed) ──
  mainWindow.on('close', (e) => {
    if (process.platform !== 'darwin' || appQuitting) return;
    e.preventDefault();
    mainWindow.hide();
  });

  mainWindow.webContents.setWindowOpenHandler(({ url }) => {
    shell.openExternal(url);
    return { action: 'deny' };
  });

  // ── Forward cluster events to frontend via IPC ──
  peerMonitor.on('peer-connected', (data) => {
    mainWindow?.webContents.send('cluster-event', { type: 'peer-connected', ...data });
  });
  peerMonitor.on('peer-degraded', (data) => {
    mainWindow?.webContents.send('cluster-event', { type: 'peer-degraded', ...data });
  });
  peerMonitor.on('peer-lost', (data) => {
    mainWindow?.webContents.send('cluster-event', { type: 'peer-lost', ...data });
  });
  peerMonitor.on('peer-recovered', (data) => {
    mainWindow?.webContents.send('cluster-event', { type: 'peer-recovered', ...data });
  });

  // ── Dev mode: bulletproof Vite connection ──────────────────────────────
  if (isDev) {
    const devUrl = getDevFrontendUrl();
    let devToolsOpened = false;
    let loadRetryCount = 0;
    const MAX_LOAD_RETRIES = 30;
    const RETRY_DELAY_MS = 2000;

    // 1) Show loading page immediately (so user never sees blank)
    mainWindow.loadFile(path.join(__dirname, 'pages', 'loading.html'));

    mainWindow.once('ready-to-show', () => {
      closeSplash();
      mainWindow.show();
    });

    // 2) Retry on failed loads (safety net for Vite restarts / network hiccups)
    mainWindow.webContents.on('did-fail-load', (_event, errorCode, errorDescription, validatedURL) => {
      if (appQuitting || !mainWindow || mainWindow.isDestroyed()) return;

      // Only retry for our dev URL, not for the loading page
      if (validatedURL && validatedURL.startsWith('http://localhost')) {
        loadRetryCount++;
        if (loadRetryCount <= MAX_LOAD_RETRIES) {
          console.log(`[main] Load failed: ${errorDescription} — retry ${loadRetryCount}/${MAX_LOAD_RETRIES} in ${RETRY_DELAY_MS / 1000}s`);
          setTimeout(() => {
            if (mainWindow && !mainWindow.isDestroyed()) {
              mainWindow.loadURL(devUrl);
            }
          }, RETRY_DELAY_MS);
        } else {
          console.error(`[main] Gave up after ${MAX_LOAD_RETRIES} retries — showing loading page`);
          mainWindow.loadFile(path.join(__dirname, 'pages', 'loading.html'));
        }
      }
    });

    // 3) Open DevTools once the real app loads
    mainWindow.webContents.on('did-finish-load', () => {
      if (!mainWindow || mainWindow.isDestroyed()) return;
      const currentUrl = mainWindow.webContents.getURL();
      if (currentUrl.startsWith('http://localhost') && !devToolsOpened) {
        devToolsOpened = true;
        loadRetryCount = 0; // Reset retries on success
        console.log('[main] Vite app loaded successfully');
        mainWindow.webContents.openDevTools({ mode: 'detach' });
      }
    });

    // 4) Poll for Vite in background, then redirect when ready
    console.log('[main] Dev mode — polling for Vite at', devUrl);
    try {
      await waitForUrl(devUrl, 60000);
      console.log('[main] Vite dev server detected — loading app');
      if (mainWindow && !mainWindow.isDestroyed()) {
        mainWindow.loadURL(devUrl);
      }
    } catch (err) {
      console.warn('[main] Vite not detected after 60s:', err.message);
      // Loading page is already shown with instructions — user can start Vite manually
      // Keep polling in background (non-blocking) so if they start Vite later, it auto-loads
      continuousVitePoll(devUrl);
    }

  // ── Production mode: load from dist or backend ─────────────────────────
  } else {
    const frontendPath = path.join(process.resourcesPath || __dirname, 'frontend', 'index.html');
    const distPath = path.join(__dirname, '..', 'frontend-v2', 'dist', 'index.html');

    if (fs.existsSync(frontendPath)) {
      mainWindow.loadFile(frontendPath);
    } else if (fs.existsSync(distPath)) {
      mainWindow.loadFile(distPath);
    } else {
      mainWindow.loadURL(`http://localhost:${port}`);
    }

    mainWindow.once('ready-to-show', () => {
      closeSplash();
      mainWindow.show();
    });
  }
}

/**
 * Keeps polling for Vite in the background after the initial timeout.
 * If Vite becomes available later, auto-redirect the main window.
 */
function continuousVitePoll(devUrl) {
  const pollInterval = setInterval(() => {
    if (appQuitting || !mainWindow || mainWindow.isDestroyed()) {
      clearInterval(pollInterval);
      return;
    }

    const req = http.get(devUrl, (res) => {
      res.resume();
      if (res.statusCode >= 200 && res.statusCode < 400) {
        console.log('[main] Vite dev server detected (background poll) — loading app');
        clearInterval(pollInterval);
        if (mainWindow && !mainWindow.isDestroyed()) {
          mainWindow.loadURL(devUrl);
        }
      }
    });
    req.on('error', () => {}); // Vite still not up, keep polling
    req.setTimeout(2000, () => req.destroy());
  }, 3000);
}

// ── Tray ──────────────────────────────────────────────────────────────────
function createTray() {
  const iconPath = path.join(__dirname, 'icons', 'icon.png');
  let icon;
  if (fs.existsSync(iconPath)) {
    icon = nativeImage.createFromPath(iconPath);
  } else {
    icon = nativeImage.createEmpty();
  }
  tray = new Tray(icon.isEmpty() ? icon : icon.resize({ width: 16, height: 16 }));

  const role = deviceConfig.getDeviceRole();
  const name = deviceConfig.getDeviceName();

  const menu = Menu.buildFromTemplate([
    { label: `${name} (${role})`, enabled: false },
    { type: 'separator' },
    { label: 'Open Embodier Trader', click: () => { mainWindow?.show(); mainWindow?.focus(); } },
    {
      label: 'Cluster Status',
      click: () => {
        const health = peerMonitor.getClusterHealth();
        const status = serviceOrchestrator.getStatus();
        console.log('[Cluster]', JSON.stringify(health, null, 2));
        console.log('[Services]', JSON.stringify(status, null, 2));
      },
    },
    { type: 'separator' },
    { label: 'Quit', click: () => app.quit() },
  ]);

  tray.setToolTip(`Embodier Trader — ${name}`);
  tray.setContextMenu(menu);
  tray.on('click', () => { mainWindow?.show(); mainWindow?.focus(); });
}

// ── Boot Sequence ─────────────────────────────────────────────────────────
async function bootSystem() {
  const role = deviceConfig.getDeviceRole();
  console.log(`[main] Booting as ${deviceConfig.getDeviceName()} (role: ${role})`);

  try {
    // Initialize services via orchestrator (handles dependency ordering,
    // peer monitoring, and fallback activation)
    await serviceOrchestrator.initialize(role);
    console.log('[main] All services started');
  } catch (err) {
    console.error('[main] Service startup failed:', err.message);
  }

  await createMainWindow();
}

// ── IPC Handlers ──────────────────────────────────────────────────────────
function registerIpcHandlers() {
  // Device config
  ipcMain.handle('get-device-config', () => deviceConfig.getFullConfig());
  ipcMain.handle('get-system-info', () => deviceConfig.getSystemInfo());

  // Backend control
  ipcMain.handle('get-backend-status', () => backendManager.getStatus());
  ipcMain.handle('restart-backend', async () => {
    await backendManager.stopBackend();
    await backendManager.startBackend();
    return backendManager.getStatus();
  });

  // API keys
  ipcMain.handle('get-api-keys', () => deviceConfig.getApiKeys());
  ipcMain.handle('set-api-keys', (_e, keys) => { deviceConfig.setApiKeys(keys); return true; });
  ipcMain.handle('set-trading-mode', (_e, mode) => { deviceConfig.setTradingMode(mode); return true; });

  // Peer devices
  ipcMain.handle('get-peer-devices', () => deviceConfig.getPeerDevices());
  ipcMain.handle('add-peer-device', (_e, peer) => { deviceConfig.addPeerDevice(peer); return true; });
  ipcMain.handle('remove-peer-device', (_e, id) => { deviceConfig.removePeerDevice(id); return true; });

  // Auth
  ipcMain.handle('get-auth-token', () => deviceConfig.getAuthToken());

  // App info
  ipcMain.handle('get-version', () => app.getVersion());
  ipcMain.handle('get-app-version', () => app.getVersion());
  ipcMain.handle('open-external', (_e, url) => shell.openExternal(url));
  ipcMain.handle('open-data-dir', () => {
    const dataDir = backendManager.getDataDir();
    shell.openPath(dataDir);
    return dataDir;
  });

  // Cluster status (for frontend dashboard)
  ipcMain.handle('get-cluster-health', () => peerMonitor.getClusterHealth());
  ipcMain.handle('get-orchestrator-status', () => serviceOrchestrator.getStatus());

  // Updates (stub — wired in auto-updater.js)
  ipcMain.handle('check-for-updates', () => ({ available: false }));

  // Window controls
  ipcMain.on('window-minimize', () => mainWindow?.minimize());
  ipcMain.on('window-maximize', () => {
    if (mainWindow?.isMaximized()) mainWindow.unmaximize();
    else mainWindow?.maximize();
  });
  ipcMain.on('window-close', () => mainWindow?.close());

  // Setup wizard completion
  ipcMain.on('setup-complete', async (_event, config) => {
    console.log('[main] Setup wizard completed:', config.deviceName, config.deviceRole);

    // Validate and log warnings (do not block launch)
    try {
      const { validateSetupConfig } = require('./setup-validator');
      const { valid, warnings } = validateSetupConfig(config);
      if (warnings && warnings.length > 0) {
        warnings.forEach((w) => console.warn('[main] Setup warning:', w));
      }
    } catch (err) {
      console.warn('[main] Setup validation error:', err.message);
    }

    // Save configuration via device-config
    deviceConfig.completeSetup(config);

    // Generate .env file for the backend (with safety guard)
    const envContent = deviceConfig.generateEnvFile(config);
    const envPath = path.join(__dirname, '..', 'backend', '.env');
    try {
      // Safety: never overwrite a .env that has real Alpaca keys with one that doesn't
      if (fs.existsSync(envPath)) {
        const existing = fs.readFileSync(envPath, 'utf8');
        const existingHasKeys = existing.includes('ALPACA_API_KEY=PK');
        const newHasKeys = envContent.includes('ALPACA_API_KEY=PK');
        if (existingHasKeys && !newHasKeys) {
          console.log('[main] Skipping .env write — existing file has API keys, new one does not');
        } else {
          fs.writeFileSync(envPath, envContent, 'utf8');
          console.log('[main] Updated backend/.env (keys preserved via defaults)');
        }
      } else {
        fs.writeFileSync(envPath, envContent, 'utf8');
        console.log('[main] Generated backend/.env');
      }
    } catch (err) {
      console.error('[main] Failed to write .env:', err.message);
    }

    // Close setup wizard, show splash, boot system
    if (setupWindow) {
      setupWindow.close();
      setupWindow = null;
    }

    createSplashWindow();
    await bootSystem();
  });
}

// ── App Lifecycle ─────────────────────────────────────────────────────────
app.whenReady().then(async () => {
  registerIpcHandlers();
  createTray();

  if (deviceConfig.isFirstRun()) {
    // First run → show setup wizard (no splash)
    console.log('[main] First run detected — launching setup wizard');
    createSetupWindow();
  } else {
    // Normal boot → splash then services
    createSplashWindow();
    await bootSystem();
  }
});

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') app.quit();
});

app.on('activate', () => {
  if (BrowserWindow.getAllWindows().length === 0) {
    if (deviceConfig.isFirstRun()) createSetupWindow();
    else createMainWindow();
  } else {
    mainWindow?.show();
  }
});

app.on('before-quit', async () => {
  appQuitting = true;
  console.log('[main] Shutting down...');
  try {
    await serviceOrchestrator.shutdown();
  } catch (err) {
    console.error('[main] Shutdown error:', err.message);
  }
});
