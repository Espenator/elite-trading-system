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
const crypto = require("crypto");
const path = require("path");
const Store = require("electron-store");

const store = new Store({ name: "device-config" });

// ── API Key Defaults ─────────────────────────────────────────────────────
// Keys are loaded from electron-store (set during first-run setup).
// Fallback: read from process.env (populated by backend/.env on ESPENMAIN).
// NEVER hardcode real secrets here — this file is committed to git.
const DEFAULT_API_KEYS = {
  // Alpaca — ESPENMAIN (Key 1, paper trading)
  alpacaApiKey: process.env.ALPACA_API_KEY || "",
  alpacaSecretKey: process.env.ALPACA_SECRET_KEY || "",
  alpacaBaseUrl: process.env.ALPACA_BASE_URL || "https://paper-api.alpaca.markets",
  // Alpaca — ProfitTrader (Key 2, discovery)
  alpacaKey2: process.env.ALPACA_KEY_2 || "",
  alpacaSecret2: process.env.ALPACA_SECRET_2 || "",
  // LLM Cloud
  anthropicApiKey: process.env.ANTHROPIC_API_KEY || "",
  perplexityApiKey: process.env.PERPLEXITY_API_KEY || "",
  // Data Sources
  finvizApiKey: process.env.FINVIZ_API_KEY || "",
  finvizEmail: process.env.FINVIZ_EMAIL || "",
  fredApiKey: process.env.FRED_API_KEY || "",
  unusualWhalesToken: process.env.UNUSUAL_WHALES_API_KEY || "",
  newsApiKey: process.env.NEWS_API_KEY || "",
  // Notifications
  resendApiKey: process.env.RESEND_API_KEY || "",
  // Scrapers
  benzingaEmail: process.env.BENZINGA_EMAIL || "",
  benzingaPassword: process.env.BENZINGA_PASSWORD || "",
};

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

const { getServicesForRole: getServicesForRoleFromLib } = require("./lib/role-services");

/** Role → services mapping (used by orchestrator and peer-monitor for fallback). */
function getServicesForRole(role) {
  return getServicesForRoleFromLib(role);
}

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
  store.set("backendPort", config.backendPort || 8001);
  store.set("brainHost", config.brainHost || "localhost");
  store.set("brainPort", config.brainPort || 50051);
  store.set("apiKeys", config.apiKeys || {});
  store.set("tradingMode", config.tradingMode || "paper");
  store.set("setupComplete", true);
  store.set("setupDate", new Date().toISOString());

  // Auto-generate API auth token on first setup
  if (!store.get("apiAuthToken")) {
    store.set("apiAuthToken", crypto.randomBytes(32).toString("base64url"));
  }
}

function getAuthToken() {
  let token = store.get("apiAuthToken");
  if (!token) {
    token = crypto.randomBytes(32).toString("base64url");
    store.set("apiAuthToken", token);
  }
  return token;
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
  return store.get("backendPort") || 8001;
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

function setTradingMode(mode) {
  if (mode !== "paper" && mode !== "live") {
    throw new Error(`Invalid trading mode: ${mode}. Must be "paper" or "live".`);
  }
  store.set("tradingMode", mode);
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
  // Merge: user-provided keys > stored keys > hardcoded defaults
  const keys = { ...DEFAULT_API_KEYS, ...getApiKeys(), ...(config.apiKeys || {}) };
  const tradingMode = config.tradingMode || "paper";
  const isLive = tradingMode === "live";
  const peerAddr = config.peerDevices?.[0]?.address || "";
  const peerPort = config.peerDevices?.[0]?.port || 8001;
  const isPrimary = config.deviceRole === "primary" || config.deviceName === "ESPENMAIN";

  const lines = [
    "# Embodier Trader — Auto-generated .env",
    `# Device: ${config.deviceName} (${config.deviceRole})`,
    `# Generated: ${new Date().toISOString()}`,
    "",
    "# --- Server ---",
    `HOST=0.0.0.0`,
    `PORT=${config.backendPort || 8000}`,
    `ENVIRONMENT=production`,
    "",
    "# --- Trading Mode ---",
    `TRADING_MODE=${tradingMode}`,
    `AUTO_EXECUTE_TRADES=${isLive ? "true" : "false"}`,
    "",
    "# --- Alpaca (Key 1 — ESPENMAIN portfolio trading) ---",
    `ALPACA_API_KEY=${keys.alpacaApiKey}`,
    `ALPACA_SECRET_KEY=${keys.alpacaSecretKey}`,
    `ALPACA_BASE_URL=${keys.alpacaBaseUrl || (isLive ? "https://api.alpaca.markets" : "https://paper-api.alpaca.markets")}`,
    `ALPACA_FEED=sip`,
    "",
    "# --- Alpaca (Key 2 — ProfitTrader discovery) ---",
    `ALPACA_KEY_2=${keys.alpacaKey2}`,
    `ALPACA_SECRET_2=${keys.alpacaSecret2}`,
    "",
    "# --- Brain Service (LLM) ---",
    `BRAIN_ENABLED=${config.brainHost !== "disabled" ? "true" : "false"}`,
    `BRAIN_HOST=${config.brainHost || (isPrimary ? "192.168.1.116" : "localhost")}`,
    `BRAIN_PORT=${config.brainPort || 50051}`,
    `OLLAMA_MODEL=llama3.2`,
    "",
    "# --- LLM Cloud APIs ---",
    `ANTHROPIC_API_KEY=${keys.anthropicApiKey}`,
    `PERPLEXITY_API_KEY=${keys.perplexityApiKey}`,
    "",
    "# --- Data Sources ---",
    `FINVIZ_API_KEY=${keys.finvizApiKey}`,
    `FINVIZ_EMAIL=${keys.finvizEmail}`,
    `FRED_API_KEY=${keys.fredApiKey}`,
    `UNUSUAL_WHALES_API_KEY=${keys.unusualWhalesToken}`,
    `UNUSUALWHALES_API_KEY=${keys.unusualWhalesToken}`,
    `NEWS_API_KEY=${keys.newsApiKey}`,
    `STOCKGEIST_API_KEY=${keys.stockgeistToken || ""}`,
    `DISCORD_BOT_TOKEN=${keys.discordBotToken || ""}`,
    `X_BEARER_TOKEN=${keys.xBearerToken || ""}`,
    `YOUTUBE_API_KEY=${keys.youtubeApiKey || ""}`,
    "",
    "# --- Notifications ---",
    `RESEND_API_KEY=${keys.resendApiKey}`,
    `SLACK_BOT_TOKEN=${keys.slackBotToken || ""}`,
    "",
    "# --- Scrapers ---",
    `BENZINGA_EMAIL=${keys.benzingaEmail}`,
    `BENZINGA_PASSWORD=${keys.benzingaPassword}`,
    `SQUEEZEMETRICS_ENABLED=true`,
    "",
    "# --- Security ---",
    `API_AUTH_TOKEN=${getAuthToken()}`,
    `FERNET_KEY=`,
    "",
    "# --- SEC EDGAR ---",
    `SEC_EDGAR_USER_AGENT=Embodier.ai espen@embodier.ai`,
    "",
    "# --- Council ---",
    `COUNCIL_GATE_ENABLED=true`,
    `COUNCIL_GATE_THRESHOLD=65`,
    `COUNCIL_MAX_CONCURRENT=3`,
    "",
    "# --- Risk Params ---",
    `KELLY_MAX_ALLOCATION=0.25`,
    `MAX_PORTFOLIO_HEAT=0.06`,
    `MAX_DAILY_TRADES=10`,
    "",
    "# --- Peer Devices ---",
    `PC2_API_URL=${peerAddr ? `http://${peerAddr}:${peerPort}` : (isPrimary ? "http://192.168.1.116:8001" : "")}`,
    `BRAIN_SERVICE_URL=${isPrimary ? "192.168.1.116:50051" : "localhost:50051"}`,
    `AWARENESS_WORKER_URL=${peerAddr ? `http://${peerAddr}:${peerPort}` : ""}`,
    `REDIS_URL=${peerAddr ? `redis://${peerAddr}:6379/0` : ""}`,
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
  getServicesForRole,
  isFirstRun,
  completeSetup,
  getPeerDevices,
  addPeerDevice,
  removePeerDevice,
  getBackendPort,
  getApiKeys,
  setApiKeys,
  getTradingMode,
  setTradingMode,
  getAuthToken,
  getFullConfig,
  generateEnvFile,
  KNOWN_DEVICES,
};
