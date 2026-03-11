// Embodier Trader — Electron main process
// Launches services via ServiceOrchestrator, monitors peers, and serves the UI.
// PC1 (ESPENMAIN): primary controller — runs council, ml-engine, event-pipeline
// PC2 (ProfitTrader): secondary — runs brain-service (Ollama/gRPC), scanner

const { app, BrowserWindow, ipcMain, Tray, Menu, nativeImage, shell } = require('electron');
const path = require('path');
const fs = require('fs');

const deviceConfig = require('./device-config');
const backendManager = require('./backend-manager');
const { serviceOrchestrator } = require('./service-orchestrator');
const { peerMonitor } = require('./peer-monitor');

const isDev = process.env.NODE_ENV === 'development' || !app.isPackaged;

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
function createMainWindow() {
  const port = deviceConfig.getBackendPort();

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

  if (isDev) {
    mainWindow.loadURL('http://localhost:3000');
  } else {
    const frontendPath = path.join(process.resourcesPath || __dirname, 'frontend', 'index.html');
    if (fs.existsSync(frontendPath)) {
      mainWindow.loadFile(frontendPath);
    } else {
      mainWindow.loadURL(`http://localhost:${port}`);
    }
  }

  mainWindow.once('ready-to-show', () => {
    closeSplash();
    mainWindow.show();
    if (isDev) mainWindow.webContents.openDevTools({ mode: 'detach' });
  });

  mainWindow.on('close', (e) => {
    if (process.platform !== 'darwin') return;
    e.preventDefault();
    mainWindow.hide();
  });

  mainWindow.webContents.setWindowOpenHandler(({ url }) => {
    shell.openExternal(url);
    return { action: 'deny' };
  });

  // Forward cluster events to frontend via IPC
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

  createMainWindow();
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

    // Save configuration via device-config
    deviceConfig.completeSetup(config);

    // Generate .env file for the backend
    const envContent = deviceConfig.generateEnvFile(config);
    const envPath = path.join(__dirname, '..', 'backend', '.env');
    try {
      fs.writeFileSync(envPath, envContent, 'utf8');
      console.log('[main] Generated backend/.env');
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
  console.log('[main] Shutting down...');
  try {
    await serviceOrchestrator.shutdown();
  } catch (err) {
    console.error('[main] Shutdown error:', err.message);
  }
});
