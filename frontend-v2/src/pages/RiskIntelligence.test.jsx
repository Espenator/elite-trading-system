import { describe, it, expect, vi, beforeEach } from "vitest";
import { render } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { useApi } from "../hooks/useApi";
import RiskIntelligence from "./RiskIntelligence";

vi.mock("../hooks/useApi");

describe("RiskIntelligence", () => {
  beforeEach(() => {
    useApi.mockImplementation(() => ({ data: null, loading: false, error: null }));
  });

  it("renders without crashing", () => {
    render(
      <MemoryRouter>
        <RiskIntelligence />
      </MemoryRouter>
    );
    expect(document.body).toBeTruthy();
  });
});
