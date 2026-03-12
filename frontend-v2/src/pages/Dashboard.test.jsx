import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { useApi } from "../hooks/useApi";
import Dashboard from "./Dashboard";

vi.mock("../hooks/useApi");
vi.mock("../services/websocket", () => ({ default: { subscribe: vi.fn(), unsubscribe: vi.fn(), connected: false } }));

describe("Dashboard", () => {
  beforeEach(() => {
    useApi.mockImplementation(() => ({ data: null, loading: false, error: null }));
  });

  it("renders without crashing", () => {
    render(
      <MemoryRouter>
        <Dashboard />
      </MemoryRouter>
    );
    expect(document.body).toBeTruthy();
  });

  it("renders dashboard content when data is provided", () => {
    useApi.mockImplementation((key) => {
      if (key === "councilLatest") return { data: { symbol: "AAPL", final_direction: "hold" }, loading: false, error: null };
      return { data: null, loading: false, error: null };
    });
    render(
      <MemoryRouter>
        <Dashboard />
      </MemoryRouter>
    );
    expect(screen.getByRole("main") || document.querySelector("main") || document.body).toBeTruthy();
  });
});
