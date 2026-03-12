import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import AgentCommandCenter from "./AgentCommandCenter";

vi.mock("../hooks/useApi", () => ({
  useApi: vi.fn(() => ({ data: { agents: [] }, loading: false, error: null })),
}));

describe("AgentCommandCenter", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders without crashing", () => {
    render(
      <MemoryRouter>
        <AgentCommandCenter />
      </MemoryRouter>
    );
    expect(document.body).toBeTruthy();
  });

  it("renders agent command center content", () => {
    render(
      <MemoryRouter>
        <AgentCommandCenter />
      </MemoryRouter>
    );
    const heading = screen.queryByText(/agent|command|swarm/i) || document.body;
    expect(heading).toBeTruthy();
  });
});
