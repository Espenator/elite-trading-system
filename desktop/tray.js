/**
 * System Tray Manager
 * Shows Embodier Trader status in the system tray with quick actions.
 */
const { Tray, Menu, nativeImage, app } = require("electron");
const path = require("path");
const log = require("electron-log");
const deviceConfig = require("./device-config");
const backendManager = require("./backend-manager");

let tray = null;

function createTray(mainWindow) {
  const iconPath = path.join(__dirname, "icons", process.platform === "win32" ? "icon.ico" : "icon-tray.png");

  // Create a simple 16x16 icon if no file exists
  let icon;
  try {
    icon = nativeImage.createFromPath(iconPath);
    if (icon.isEmpty()) throw new Error("empty");
  } catch {
    // Fallback: create a simple colored square icon
    icon = nativeImage.createEmpty();
  }

  tray = new Tray(icon);

  const deviceName = deviceConfig.getDeviceName();
  const deviceRole = deviceConfig.getDeviceRole();
  tray.setToolTip(`Embodier Trader — ${deviceName} (${deviceRole})`);

  updateMenu(mainWindow);
  return tray;
}

function updateMenu(mainWindow) {
  if (!tray) return;

  const deviceName = deviceConfig.getDeviceName();
  const deviceRole = deviceConfig.getDeviceRole();
  const backendStatus = backendManager.getStatus();
  const peers = deviceConfig.getPeerDevices();

  const peerItems = peers.length > 0
    ? peers.map((p) => ({
        label: `  ${p.name} (${p.role || "unknown"})`,
        enabled: false,
      }))
    : [{ label: "  No peers configured", enabled: false }];

  const contextMenu = Menu.buildFromTemplate([
    {
      label: `Embodier Trader v${app.getVersion()}`,
      enabled: false,
      icon: null,
    },
    { type: "separator" },
    {
      label: `Device: ${deviceName}`,
      enabled: false,
    },
    {
      label: `Role: ${deviceRole}`,
      enabled: false,
    },
    {
      label: `Backend: ${backendStatus.running ? `Running (port ${backendStatus.port})` : "Stopped"}`,
      enabled: false,
    },
    { type: "separator" },
    {
      label: "Peer Devices",
      submenu: peerItems,
    },
    { type: "separator" },
    {
      label: "Open Embodier Trader",
      click: () => {
        if (mainWindow) {
          mainWindow.show();
          mainWindow.focus();
        }
      },
    },
    {
      label: "Open DevTools",
      click: () => {
        if (mainWindow) {
          mainWindow.webContents.openDevTools();
        }
      },
      visible: process.env.NODE_ENV === "development",
    },
    { type: "separator" },
    {
      label: backendStatus.running ? "Restart Backend" : "Start Backend",
      click: async () => {
        if (backendStatus.running) {
          await backendManager.stopBackend();
        }
        await backendManager.startBackend();
        updateMenu(mainWindow);
      },
    },
    {
      label: "Stop Backend",
      enabled: backendStatus.running,
      click: async () => {
        await backendManager.stopBackend();
        updateMenu(mainWindow);
      },
    },
    { type: "separator" },
    {
      label: "Quit Embodier Trader",
      click: () => {
        app.quit();
      },
    },
  ]);

  tray.setContextMenu(contextMenu);
}

function destroyTray() {
  if (tray) {
    tray.destroy();
    tray = null;
  }
}

module.exports = { createTray, updateMenu, destroyTray };
