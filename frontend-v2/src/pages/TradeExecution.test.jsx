import { describe, it, expect, vi, beforeEach } from "vitest";
import { render } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { useApi } from "../hooks/useApi";
import TradeExecution from "./TradeExecution";

vi.mock("../hooks/useApi");

describe("TradeExecution", () => {
  beforeEach(() => {
    useApi.mockImplementation(() => ({ data: null, loading: false, error: null }));
  });

  it("renders without crashing", () => {
    render(
      <MemoryRouter>
        <TradeExecution />
      </MemoryRouter>
    );
    expect(document.body).toBeTruthy();
  });
});
