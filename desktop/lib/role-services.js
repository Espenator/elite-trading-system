/**
 * Role → services and service startup order.
 * Single source of truth for orchestrator and device-config; testable without Electron.
 */
const SERVICE_ORDER = {
  backend: 1,
  frontend: 2,
  council: 3,
  "ml-engine": 4,
  "event-pipeline": 5,
  "brain-service": 10,
  scanner: 11,
  "mobile-server": 12,
};

function getServicesForRole(role) {
  switch (role) {
    case "full":
      return ["backend", "frontend", "council", "ml-engine", "event-pipeline", "brain-service", "scanner", "mobile-server"];
    case "primary":
      return ["backend", "frontend", "council", "ml-engine", "event-pipeline", "mobile-server"];
    case "secondary":
      return ["backend", "frontend", "brain-service", "scanner"];
    case "brain-only":
      return ["brain-service"];
    case "scanner-only":
      return ["scanner"];
    default:
      return ["backend", "frontend"];
  }
}

/** Returns service names sorted by startup order (backend first, then frontend, etc.). */
function getServicesInStartupOrder(serviceNames) {
  return [...serviceNames].sort(
    (a, b) => (SERVICE_ORDER[a] ?? 99) - (SERVICE_ORDER[b] ?? 99)
  );
}

module.exports = {
  SERVICE_ORDER,
  getServicesForRole,
  getServicesInStartupOrder,
};
