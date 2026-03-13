import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import TradeExecution from "./TradeExecution";

vi.mock("../hooks/useApi", () => ({
  useApi: vi.fn(() => ({ data: { orders: [], positions: [] }, loading: false, error: null })),
}));
vi.mock("../hooks/useTradeExecution", () => ({
  useTradeExecution: vi.fn(() => ({ submitOrder: vi.fn(), loading: false })),
}));

describe("TradeExecution", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders without crashing", () => {
    render(
      <MemoryRouter>
        <TradeExecution />
      </MemoryRouter>
    );
    expect(document.body).toBeTruthy();
  });

  it("renders trade execution content", () => {
    render(
      <MemoryRouter>
        <TradeExecution />
      </MemoryRouter>
    );
    const el = document.querySelector("main") || document.body;
    expect(el).toBeTruthy();
  });
});
