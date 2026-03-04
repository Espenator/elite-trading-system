/**
 * Electron Integration Utilities
 *
 * Detects if running inside Electron desktop shell and provides
 * access to native features (device config, backend control, etc.)
 *
 * When running in browser (dev server / web deploy), all functions
 * return safe defaults so the UI works identically.
 */

/** True if running inside Electron desktop shell */
export const isElectron = Boolean(window.embodier?.isElectron);

/** Current platform: "win32" | "darwin" | "linux" | "browser" */
export const platform = window.embodier?.platform || "browser";

/** Get device configuration from Electron store */
export async function getDeviceConfig() {
  if (!isElectron) return null;
  return window.embodier.getDeviceConfig();
}

/** Get system info (hostname, cpus, memory, etc.) */
export async function getSystemInfo() {
  if (!isElectron) return null;
  return window.embodier.getSystemInfo();
}

/** Get backend process status */
export async function getBackendStatus() {
  if (!isElectron) return { running: true, pid: null, port: 8000 };
  return window.embodier.getBackendStatus();
}

/** Restart the backend process */
export async function restartBackend() {
  if (!isElectron) return null;
  return window.embodier.restartBackend();
}

/** Get app version */
export async function getVersion() {
  if (!isElectron) return null;
  return window.embodier.getVersion();
}

/** Open external URL in system browser */
export async function openExternal(url) {
  if (!isElectron) {
    window.open(url, "_blank");
    return;
  }
  return window.embodier.openExternal(url);
}

/** Open the data directory in file explorer */
export async function openDataDir() {
  if (!isElectron) return;
  return window.embodier.openDataDir();
}

/** Listen for backend status changes */
export function onBackendStatus(callback) {
  if (!isElectron) return () => {};
  window.embodier.onBackendStatus(callback);
  return () => {}; // cleanup placeholder
}
