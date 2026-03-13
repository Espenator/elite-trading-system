/**
 * Setup wizard config validation.
 * Returns warnings for missing/invalid values; does not block completion.
 */
function validateSetupConfig(config) {
  const warnings = [];

  if (!config) {
    return { valid: false, warnings: ["No configuration provided."] };
  }

  const keys = config.apiKeys || {};
  const hasAlpacaKey = !!(keys.alpacaApiKey && keys.alpacaApiKey.trim());
  const hasAlpacaSecret = !!(keys.alpacaSecretKey && keys.alpacaSecretKey.trim());

  if (!hasAlpacaKey || !hasAlpacaSecret) {
    warnings.push("Alpaca API key or secret is missing. Paper/live trading will be disabled until set in Settings.");
  }

  const port = config.backendPort || 8000;
  if (port < 1024 || port > 65535) {
    warnings.push("Backend port should be between 1024 and 65535.");
  }

  if (config.peerDevices && config.peerDevices.length > 0) {
    const peer = config.peerDevices[0];
    if (!peer.address || !peer.address.trim()) {
      warnings.push("Peer IP address is missing. Peer monitoring will not work until set.");
    }
  }

  return {
    valid: warnings.filter((w) => w.includes("Alpaca")).length === 0 ? true : true,
    warnings,
  };
}

module.exports = { validateSetupConfig };
