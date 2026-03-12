import "@testing-library/jest-dom/vitest";
import { vi } from "vitest";

// Default useApi mock: no loading, no error, empty data
vi.mock("../hooks/useApi", () => ({
  useApi: vi.fn(() => ({ data: null, loading: false, error: null })),
}));

// WebSocket mock
vi.mock("../services/websocket", () => ({
  default: {
    subscribe: vi.fn(),
    unsubscribe: vi.fn(),
    connected: false,
  },
}));
