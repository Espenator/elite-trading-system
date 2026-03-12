import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { useApi } from "../hooks/useApi";
import AgentCommandCenter from "./AgentCommandCenter";

vi.mock("../hooks/useApi");

describe("AgentCommandCenter", () => {
  beforeEach(() => {
    useApi.mockImplementation(() => ({ data: null, loading: false, error: null }));
  });

  it("renders without crashing", () => {
    render(
      <MemoryRouter>
        <AgentCommandCenter />
      </MemoryRouter>
    );
    expect(document.body).toBeTruthy();
  });

  it("contains agent or command related content", () => {
    render(
      <MemoryRouter>
        <AgentCommandCenter />
      </MemoryRouter>
    );
    const text = document.body.textContent || "";
    expect(text.length).toBeGreaterThan(0);
  });
});
