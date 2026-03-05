/**
 * Device Configuration Manager
 * Handles device identity, peer discovery, and role assignment.
 *
 * Device Roles:
 *   "full"         — Runs backend + frontend (standalone)
 *   "primary"      — Main control station (e.g., ESPENMAIN)
 *   "secondary"    — Satellite node (e.g., Profit Trader)
 *   "brain-only"   — LLM inference node only
 *   "scanner-only" — OpenClaw scanner only
 */
const os = require("os");
const path = require("path");
const Store = require("electron-store");

const store = new Store({ name: "device-config" });

// Default device profiles for known machines
const KNOWN_DEVICES = {
  ESPENMAIN: {
    role: "primary",
    displayName: "ESPENMAIN",
    description: "Primary Control Station",
    services: ["backend", "frontend", "council", "ml-engine", "event-pipeline"],
    isController: true,
  },
  "Profit Trader": {
    role: "secondary",
    displayName: "Profit Trader",
    description: "Secondary Trading Node",
    services: ["backend", "frontend", "brain-service", "scanner"],
    isController: false,
  },
};

function getSystemInfo() {
  const interfaces = os.networkInterfaces();
  const addresses = [];
  for (const [name, nets] of Object.entries(interfaces)) {
    for (const net of nets) {
      if (net.family === "IPv4" && !net.internal) {
        addresses.push({ interface: name, address: net.address });
      }
    }
  }

  return {
    hostname: os.hostname(),
    platform: os.platform(),
    arch: os.arch(),
    cpus: os.cpus().length,
    totalMemoryGB: Math.round(os.totalmem() / (1024 * 1024 * 1024)),
    networkAddresses: addresses,
    homeDir: os.homedir(),
    isAppleSilicon: os.platform() === "darwin" && os.arch() === "arm64",
    isWindows: os.platform() === "win32",
    isMac: os.platform() === "darwin",
    isLinux: os.platform() === "linux",
  };
}

function getDeviceId() {
  let deviceId = store.get("deviceId");
  if (!deviceId) {
    deviceId = `${os.hostname()}-${Date.now().toString(36)}`;
    store.set("deviceId", deviceId);
  }
  return deviceId;
}

function getDeviceName() {
  return store.get("deviceName") || os.hostname();
}

function setDeviceName(name) {
  store.set("deviceName", name);
}

function getDeviceRole() {
  return store.get("deviceRole") || "full";
}

function setDeviceRole(role) {
  store.set("deviceRole", role);
}

function isFirstRun() {
  return !store.get("setupComplete");
}

function completeSetup(config) {
  store.set("deviceName", config.deviceName);
  store.set("deviceRole", config.deviceRole);
  store.set("peerDevices", config.peerDevices || []);
  store.set("backendPort", config.backendPort || 8000);
  store.set("brainHost", config.brainHost || "localhost");
  store.set("brainPort", config.brainPort || 50051);
  store.set("apiKeys", config.apiKeys || {});
  store.set("tradingMode", config.tradingMode || "paper");
  store.set("setupComplete", true);
  store.set("setupDate", new Date().toISOString());
}

function getPeerDevices() {
  return store.get("peerDevices") || [];
}

function addPeerDevice(peer) {
  const peers = getPeerDevices();
  const existing = peers.findIndex((p) => p.id === peer.id);
  if (existing >= 0) {
    peers[existing] = { ...peers[existing], ...peer, lastSeen: new Date().toISOString() };
  } else {
    peers.push({ ...peer, addedAt: new Date().toISOString(), lastSeen: new Date().toISOString() });
  }
  store.set("peerDevices", peers);
}

function removePeerDevice(peerId) {
  const peers = getPeerDevices().filter((p) => p.id !== peerId);
  store.set("peerDevices", peers);
}

function getBackendPort() {
  return store.get("backendPort") || 8000;
}

function getApiKeys() {
  return store.get("apiKeys") || {};
}

function setApiKeys(keys) {
  store.set("apiKeys", { ...getApiKeys(), ...keys });
}

function getTradingMode() {
  return store.get("tradingMode") || "paper";
}

function getFullConfig() {
  return {
    deviceId: getDeviceId(),
    deviceName: getDeviceName(),
    deviceRole: getDeviceRole(),
    systemInfo: getSystemInfo(),
    peerDevices: getPeerDevices(),
    backendPort: getBackendPort(),
    tradingMode: getTradingMode(),
    setupComplete: store.get("setupComplete") || false,
    knownProfiles: KNOWN_DEVICES,
  };
}

function generateEnvFile(config) {
  const keys = config.apiKeys || {};
  const lines = [
    "# Embodier Trader — Auto-generated .env",
    `# Device: ${config.deviceName} (${config.deviceRole})`,
    `# Generated: ${new Date().toISOString()}`,
    "",
    "# --- Server ---",
    `HOST=0.0.0.0`,
    `PORT=${config.backendPort || 8000}`,
    "",
    "# --- Trading Mode ---",
    `TRADING_MODE=${config.tradingMode || "live"}`,
    `AUTO_EXECUTE_TRADES=true`,
    "",
    "# --- Alpaca (Live Trading) ---",
    `ALPACA_API_KEY=${keys.alpacaApiKey || ""}`,
    `ALPACA_SECRET_KEY=${keys.alpacaSecretKey || ""}`,
    `ALPACA_BASE_URL=${keys.alpacaBaseUrl || "https://api.alpaca.markets"}`,
    `ALPACA_FEED=sip`,
    "",
    "# --- Brain Service (LLM) ---",
    `BRAIN_ENABLED=${config.brainHost !== "disabled" ? "true" : "false"}`,
    `BRAIN_HOST=${config.brainHost || "localhost"}`,
    `BRAIN_PORT=${config.brainPort || 50051}`,
    `OLLAMA_MODEL=llama3.2`,
    "",
    "# --- Data Sources ---",
    `FINVIZ_EMAIL=${keys.finvizEmail || ""}`,
    `FRED_API_KEY=${keys.fredApiKey || ""}`,
    `UNUSUAL_WHALES_TOKEN=${keys.unusualWhalesToken || ""}`,
    `NEWS_API_KEY=${keys.newsApiKey || ""}`,
    `STOCKGEIST_TOKEN=${keys.stockgeistToken || ""}`,
    `DISCORD_BOT_TOKEN=${keys.discordBotToken || ""}`,
    `X_BEARER_TOKEN=${keys.xBearerToken || ""}`,
    `YOUTUBE_API_KEY=${keys.youtubeApiKey || ""}`,
    "",
    "# --- Security ---",
    `API_AUTH_TOKEN=${keys.apiAuthToken || ""}`,
    `FERNET_KEY=`,
    "",
    "# --- Peer Devices ---",
    `OPENCLAW_API_URL=${config.peerDevices?.[0]?.address ? `http://${config.peerDevices[0].address}:5000` : ""}`,
    `ELITE_API_URL=${config.peerDevices?.[0]?.address ? `http://${config.peerDevices[0].address}:8000` : ""}`,
  ];
  return lines.join("\n") + "\n";
}

module.exports = {
  getSystemInfo,
  getDeviceId,
  getDeviceName,
  setDeviceName,
  getDeviceRole,
  setDeviceRole,
  isFirstRun,
  completeSetup,
  getPeerDevices,
  addPeerDevice,
  removePeerDevice,
  getBackendPort,
  getApiKeys,
  setApiKeys,
  getTradingMode,
  getFullConfig,
  generateEnvFile,
  KNOWN_DEVICES,
};
