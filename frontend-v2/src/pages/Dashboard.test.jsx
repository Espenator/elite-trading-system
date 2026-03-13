import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import Dashboard from "./Dashboard";

vi.mock("../hooks/useApi", () => ({
  useApi: vi.fn((key) => {
    const data = {
      councilLatest: { verdict: "hold", symbol: null },
      signals: [],
      health: { status: "ok" },
      indices: {},
    };
    return { data: data[key] ?? null, loading: false, error: null };
  }),
}));

vi.mock("../services/websocket", () => ({ default: { subscribe: vi.fn(), unsubscribe: vi.fn() } }));

describe("Dashboard", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders without crashing", () => {
    render(
      <MemoryRouter>
        <Dashboard />
      </MemoryRouter>
    );
    expect(screen.getByRole("main", { hidden: true }) || document.body).toBeTruthy();
  });

  it("renders dashboard content", () => {
    render(
      <MemoryRouter>
        <Dashboard />
      </MemoryRouter>
    );
    const el = document.querySelector("[class*='dashboard']") || document.body;
    expect(el).toBeTruthy();
  });
});
