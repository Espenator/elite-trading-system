// Embodier Trader — Electron main process
// Launches the FastAPI backend and serves the React frontend

const { app, BrowserWindow, ipcMain, Tray, Menu, nativeImage, shell } = require('electron');
const { spawn, execSync } = require('child_process');
const path = require('path');
const fs = require('fs');
const http = require('http');
const https = require('https');

const isDev = process.env.NODE_ENV === 'development' || !app.isPackaged;
const BACKEND_PORT = 8000;
const FRONTEND_PORT = 3000;

let mainWindow = null;
let splashWindow = null;
let tray = null;
let backendProcess = null;
let backendReady = false;

// ── Backend Health Check ───────────────────────────────────────────────────────
function checkBackend(url, retries = 30, interval = 2000) {
  return new Promise((resolve, reject) => {
    let attempts = 0;
    const check = () => {
      const req = (url.startsWith('https') ? https : http).get(url, (res) => {
        if (res.statusCode === 200 || res.statusCode === 404) {
          resolve();
        } else {
          retry();
        }
      });
      req.on('error', retry);
      req.setTimeout(2000, () => { req.destroy(); retry(); });
    };
    const retry = () => {
      attempts++;
      if (attempts >= retries) {
        reject(new Error(`Backend not ready after ${retries} attempts`));
      } else {
        setTimeout(check, interval);
      }
    };
    check();
  });
}

// ── Backend Launcher ──────────────────────────────────────────────────────────
function startBackend() {
  const isWindows = process.platform === 'win32';
  const resourcesPath = process.resourcesPath || path.join(__dirname, '..');

  // In packaged app, backend is bundled via PyInstaller
  const backendExe = isWindows
    ? path.join(resourcesPath, 'backend', 'embodier-backend', 'embodier-backend.exe')
    : path.join(resourcesPath, 'backend', 'embodier-backend', 'embodier-backend');

  // In dev, use the Python venv
  const devPython = isWindows
    ? path.join(__dirname, '..', 'backend', 'venv', 'Scripts', 'python.exe')
    : path.join(__dirname, '..', 'backend', 'venv', 'bin', 'python');
  const devScript = path.join(__dirname, '..', 'backend', 'run.py');

  let cmd, args, cwd;

  if (!isDev && fs.existsSync(backendExe)) {
    cmd = backendExe;
    args = [];
    cwd = path.dirname(backendExe);
  } else if (fs.existsSync(devPython)) {
    cmd = devPython;
    args = [devScript];
    cwd = path.join(__dirname, '..', 'backend');
  } else {
    console.error('Backend executable not found');
    return null;
  }

  const env = { ...process.env, PORT: String(BACKEND_PORT) };
  const proc = spawn(cmd, args, { cwd, env, stdio: 'pipe' });

  proc.stdout.on('data', (d) => console.log('[backend]', d.toString().trim()));
  proc.stderr.on('data', (d) => console.error('[backend]', d.toString().trim()));
  proc.on('exit', (code) => {
    console.log(`Backend exited with code ${code}`);
    backendReady = false;
  });

  return proc;
}

// ── Splash Window ─────────────────────────────────────────────────────────────
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

// ── Main Window ───────────────────────────────────────────────────────────────
function createMainWindow() {
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
    // In dev, load from Vite dev server
    mainWindow.loadURL("http://localhost:3000");
  } else {
    // In production, serve the built frontend through the backend
    const frontendPath = path.join(process.resourcesPath || __dirname, "frontend", "index.html");
    if (fs.existsSync(frontendPath)) {
      mainWindow.loadFile(frontendPath);
    } else {
      mainWindow.loadURL(`http://localhost:${BACKEND_PORT}`);
    }
  }

  mainWindow.once('ready-to-show', () => {
    if (splashWindow) {
      splashWindow.close();
      splashWindow = null;
    }
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
}

// ── Tray ──────────────────────────────────────────────────────────────────────
function createTray() {
  const iconPath = path.join(__dirname, 'assets', 'icon.png');
  const icon = fs.existsSync(iconPath) ? nativeImage.createFromPath(iconPath) : nativeImage.createEmpty();
  tray = new Tray(icon.resize({ width: 16, height: 16 }));

  const menu = Menu.buildFromTemplate([
    { label: 'Open Embodier Trader', click: () => { mainWindow?.show(); mainWindow?.focus(); } },
    { type: 'separator' },
    { label: 'Quit', click: () => app.quit() },
  ]);

  tray.setToolTip('Embodier Trader');
  tray.setContextMenu(menu);
  tray.on('click', () => { mainWindow?.show(); mainWindow?.focus(); });
}

// ── App Lifecycle ─────────────────────────────────────────────────────────────
app.whenReady().then(async () => {
  createSplashWindow();
  createTray();

  // Start backend
  backendProcess = startBackend();

  // Wait for backend to be ready
  try {
    await checkBackend(`http://localhost:${BACKEND_PORT}/health`);
    backendReady = true;
    console.log('Backend ready');
  } catch (e) {
    console.error('Backend health check failed:', e.message);
  }

  createMainWindow();
});

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') app.quit();
});

app.on('activate', () => {
  if (BrowserWindow.getAllWindows().length === 0) createMainWindow();
  else mainWindow?.show();
});

app.on('before-quit', () => {
  if (backendProcess) {
    backendProcess.kill();
  }
});

// IPC handlers
ipcMain.handle('get-app-version', () => app.getVersion());
ipcMain.handle('open-external', (_, url) => shell.openExternal(url));
