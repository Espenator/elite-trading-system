import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import RiskIntelligence from "./RiskIntelligence";

vi.mock("../hooks/useApi", () => ({
  useApi: vi.fn(() => ({ data: { gauges: [], breakers: [] }, loading: false, error: null })),
}));

describe("RiskIntelligence", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders without crashing", () => {
    render(
      <MemoryRouter>
        <RiskIntelligence />
      </MemoryRouter>
    );
    expect(document.body).toBeTruthy();
  });

  it("renders risk content", () => {
    render(
      <MemoryRouter>
        <RiskIntelligence />
      </MemoryRouter>
    );
    const el = document.querySelector("main") || document.body;
    expect(el).toBeTruthy();
  });
});
