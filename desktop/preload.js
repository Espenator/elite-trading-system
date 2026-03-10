/**
 * Electron Preload Script
 * Exposes safe IPC channels to the renderer (React frontend).
 * The frontend can call window.embodier.* to interact with the desktop shell.
 */
const { contextBridge, ipcRenderer } = require("electron");

contextBridge.exposeInMainWorld("embodier", {
  // Device info
  getDeviceConfig: () => ipcRenderer.invoke("get-device-config"),
  getSystemInfo: () => ipcRenderer.invoke("get-system-info"),

  // Backend control
  getBackendStatus: () => ipcRenderer.invoke("get-backend-status"),
  restartBackend: () => ipcRenderer.invoke("restart-backend"),

  // Settings
  getApiKeys: () => ipcRenderer.invoke("get-api-keys"),
  setApiKeys: (keys) => ipcRenderer.invoke("set-api-keys", keys),

  // Peer devices
  getPeerDevices: () => ipcRenderer.invoke("get-peer-devices"),
  addPeerDevice: (peer) => ipcRenderer.invoke("add-peer-device", peer),
  removePeerDevice: (id) => ipcRenderer.invoke("remove-peer-device", id),

  // Setup wizard
  sendSetupComplete: (config) => ipcRenderer.send("setup-complete", config),

  // Window controls
  minimize: () => ipcRenderer.send("window-minimize"),
  maximize: () => ipcRenderer.send("window-maximize"),
  close: () => ipcRenderer.send("window-close"),

  // App info
  getVersion: () => ipcRenderer.invoke("get-version"),
  openExternal: (url) => ipcRenderer.invoke("open-external", url),
  openDataDir: () => ipcRenderer.invoke("open-data-dir"),

  // Events from main process
  onBackendStatus: (callback) => {
    ipcRenderer.on("backend-status", (_event, status) => callback(status));
  },
  onUpdateAvailable: (callback) => {
    ipcRenderer.on("update-available", (_event, info) => callback(info));
  },

  // Platform detection
  platform: process.platform,
  isElectron: true,
});
