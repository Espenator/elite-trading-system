/**
 * Desktop Electron app — service orchestration & resilience tests.
 * Run with: node desktop/tests/desktop-orchestration.test.js
 * Tests service startup order, peer offline fallback, and setup wizard validation.
 */
const assert = require("assert");
const path = require("path");

// Run from repo root or desktop/
const desktopRoot = path.join(__dirname, "..");
const libPath = path.join(desktopRoot, "lib", "role-services.js");
const validatorPath = path.join(desktopRoot, "setup-validator.js");

const { SERVICE_ORDER, getServicesForRole, getServicesInStartupOrder } = require(libPath);
const { validateSetupConfig } = require(validatorPath);

function testServiceStartupOrder() {
  // Backend must start before frontend; frontend before council, ml-engine, event-pipeline
  assert.strictEqual(SERVICE_ORDER.backend, 1, "backend order should be 1");
  assert.strictEqual(SERVICE_ORDER.frontend, 2, "frontend order should be 2");
  assert.ok(SERVICE_ORDER.backend < SERVICE_ORDER.frontend, "backend before frontend");
  assert.ok(SERVICE_ORDER.frontend < SERVICE_ORDER.council, "frontend before council");
  assert.ok(SERVICE_ORDER.council < SERVICE_ORDER["ml-engine"], "council before ml-engine");
  assert.ok(SERVICE_ORDER["ml-engine"] < SERVICE_ORDER["event-pipeline"], "ml-engine before event-pipeline");

  const primary = getServicesForRole("primary");
  const ordered = getServicesInStartupOrder(primary);
  const backendIdx = ordered.indexOf("backend");
  const frontendIdx = ordered.indexOf("frontend");
  assert.ok(backendIdx >= 0 && frontendIdx >= 0, "primary role includes backend and frontend");
  assert.ok(backendIdx < frontendIdx, "backend appears before frontend in startup order");

  console.log("[PASS] Service startup order: backend(1) → frontend(2) → council(3) → ml-engine(4) → event-pipeline(5)");
}

function testPeerOfflineFallback() {
  // When PC2 (secondary) goes offline, orchestrator checks peer.services.includes("brain-service")
  // to activate Ollama fallback. Peer config may not have .services set; peer-monitor derives
  // services from role via getServicesForRole(role). So secondary must include brain-service.
  const secondaryServices = getServicesForRole("secondary");
  assert.ok(
    secondaryServices.includes("brain-service"),
    "secondary role must include brain-service for peer-lost fallback"
  );
  assert.ok(
    secondaryServices.includes("scanner"),
    "secondary role must include scanner"
  );

  const primaryServices = getServicesForRole("primary");
  assert.ok(
    !primaryServices.includes("brain-service"),
    "primary role does not run brain-service locally (expects PC2)"
  );

  console.log("[PASS] Peer offline detection: secondary role includes brain-service → fallback activation");
}

function testSetupWizardValidation() {
  const missingAlpaca = validateSetupConfig({
    deviceName: "Test",
    deviceRole: "full",
    backendPort: 8000,
    apiKeys: {},
  });
  assert.ok(missingAlpaca.warnings.length > 0, "missing Alpaca keys should produce warnings");
  assert.ok(
    missingAlpaca.warnings.some((w) => w.includes("Alpaca")),
    "warning should mention Alpaca"
  );

  const withAlpaca = validateSetupConfig({
    deviceName: "Test",
    deviceRole: "full",
    backendPort: 8000,
    apiKeys: { alpacaApiKey: "PK123", alpacaSecretKey: "secret" },
  });
  assert.ok(
    !withAlpaca.warnings.some((w) => w.includes("Alpaca")),
    "valid Alpaca keys should not add Alpaca warning"
  );

  const invalidPort = validateSetupConfig({
    deviceName: "Test",
    backendPort: 80,
    apiKeys: { alpacaApiKey: "PK", alpacaSecretKey: "s" },
  });
  assert.ok(
    invalidPort.warnings.some((w) => w.includes("port")),
    "invalid port should produce warning"
  );

  const missingPeerIp = validateSetupConfig({
    deviceName: "Test",
    peerDevices: [{ id: "p1", address: "", port: 8000 }],
    apiKeys: { alpacaApiKey: "PK", alpacaSecretKey: "s" },
  });
  assert.ok(
    missingPeerIp.warnings.some((w) => w.includes("Peer") || w.includes("IP")),
    "missing peer IP should produce warning"
  );

  console.log("[PASS] Setup wizard validation: missing API keys / invalid port / missing peer IP produce warnings");
}

function run() {
  console.log("Desktop orchestration tests\n");
  testServiceStartupOrder();
  testPeerOfflineFallback();
  testSetupWizardValidation();
  console.log("\nAll tests passed.");
}

run();
