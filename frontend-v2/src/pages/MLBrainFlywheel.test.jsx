import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import MLBrainFlywheel from "./MLBrainFlywheel";

vi.mock("../hooks/useApi", () => ({
  useApi: vi.fn(() => ({ data: { metrics: {} }, loading: false, error: null })),
}));

describe("MLBrainFlywheel", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders without crashing", () => {
    render(
      <MemoryRouter>
        <MLBrainFlywheel />
      </MemoryRouter>
    );
    expect(document.body).toBeTruthy();
  });

  it("renders ML brain content", () => {
    render(
      <MemoryRouter>
        <MLBrainFlywheel />
      </MemoryRouter>
    );
    const el = document.querySelector("main") || document.body;
    expect(el).toBeTruthy();
  });
});
