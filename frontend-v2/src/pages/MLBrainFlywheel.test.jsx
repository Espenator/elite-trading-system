import { describe, it, expect, vi, beforeEach } from "vitest";
import { render } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { useApi } from "../hooks/useApi";
import MLBrainFlywheel from "./MLBrainFlywheel";

vi.mock("../hooks/useApi");

describe("MLBrainFlywheel", () => {
  beforeEach(() => {
    useApi.mockImplementation(() => ({ data: null, loading: false, error: null }));
  });

  it("renders without crashing", () => {
    render(
      <MemoryRouter>
        <MLBrainFlywheel />
      </MemoryRouter>
    );
    expect(document.body).toBeTruthy();
  });
});
