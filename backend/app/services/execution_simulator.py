"""Execution Simulator — slippage + partial fill realism for paper trading.

Prevents "paper alpha" by applying realistic execution costs:
- Deterministic (seedable) slippage model
- Partial fill simulation based on volume/volatility
- Full logging of intended vs actual fill prices

Usage:
    from app.services.execution_simulator import get_execution_simulator
    sim = get_execution_simulator()
    fill = sim.simulate_fill(price=150.0, side="buy", volume=1_000_000)
"""
import logging
import math
import os
import random
import time
from dataclasses import dataclass
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class SimulatedFill:
    """Result of a simulated order fill."""

    intended_price: float
    fill_price: float
    slippage_bps: float
    fill_ratio: float  # (0, 1]
    timestamp: float
    side: str
    volume_impact_bps: float = 0.0
    spread_cost_bps: float = 0.0


class ExecutionSimulator:
    """Deterministic slippage + partial fill simulator.

    Parameters
    ----------
    slippage_bps : float
        Base slippage in basis points (default 5.0 = 0.05%).
    seed : int or None
        Random seed for reproducibility. 0 or None = random.
    partial_fill_enabled : bool
        If True, simulate partial fills based on volume/volatility.
    """

    def __init__(
        self,
        slippage_bps: float = 5.0,
        seed: Optional[int] = None,
        partial_fill_enabled: bool = True,
    ):
        self.base_slippage_bps = slippage_bps
        self.partial_fill_enabled = partial_fill_enabled
        effective_seed = seed if seed and seed != 0 else None
        self.rng = random.Random(effective_seed)

    def simulate_fill(
        self,
        price: float,
        side: str,
        volume: Optional[float] = None,
        volatility: Optional[float] = None,
        spread: Optional[float] = None,
        order_qty: Optional[int] = None,
    ) -> SimulatedFill:
        """Simulate a realistic fill with slippage and partial fill.

        Args:
            price: Intended fill price.
            side: "buy" or "sell".
            volume: Recent average daily volume (shares). Higher → less slippage.
            volatility: Recent volatility (e.g., 20d annualized). Higher → more slippage.
            spread: Bid-ask spread in dollars. If None, estimated from price.
            order_qty: Number of shares in the order. Affects volume impact.

        Returns:
            SimulatedFill with adjusted price and fill ratio.
        """
        now = time.time()

        # --- Base slippage ---
        total_bps = self.base_slippage_bps

        # --- Volume impact ---
        # Larger orders relative to volume → more slippage
        volume_impact_bps = 0.0
        if volume and volume > 0 and order_qty and order_qty > 0:
            participation_rate = order_qty / volume
            # Impact scales with sqrt of participation rate
            volume_impact_bps = 2.0 * math.sqrt(participation_rate) * 100  # bps
            volume_impact_bps = min(volume_impact_bps, 50.0)  # cap at 50 bps
            total_bps += volume_impact_bps
        elif volume and volume > 0:
            # General volume adjustment: low volume → more slippage
            if volume < 100_000:
                total_bps += 3.0
            elif volume < 500_000:
                total_bps += 1.0

        # --- Volatility impact ---
        if volatility and volatility > 0:
            # Higher vol → more slippage (linear scaling)
            vol_multiplier = max(0.5, min(3.0, volatility / 0.20))
            total_bps *= vol_multiplier

        # --- Spread component ---
        spread_cost_bps = 0.0
        if spread and spread > 0:
            spread_cost_bps = (spread / 2.0) / price * 10_000  # half-spread in bps
        else:
            # Estimate spread from price level
            if price < 10:
                spread_cost_bps = 5.0
            elif price < 50:
                spread_cost_bps = 2.0
            elif price < 200:
                spread_cost_bps = 1.0
            else:
                spread_cost_bps = 0.5
        total_bps += spread_cost_bps

        # --- Add random noise (uniform -20% to +30% of base) ---
        noise_factor = self.rng.uniform(0.80, 1.30)
        total_bps *= noise_factor

        # --- Apply direction ---
        # Slippage always worsens price: buy → higher, sell → lower
        slip_fraction = total_bps / 10_000
        if side.lower() == "buy":
            fill_price = price * (1.0 + slip_fraction)
        else:
            fill_price = price * (1.0 - slip_fraction)

        # --- Partial fill ---
        fill_ratio = 1.0
        if self.partial_fill_enabled:
            fill_ratio = self._compute_fill_ratio(volume, volatility, order_qty)

        fill = SimulatedFill(
            intended_price=price,
            fill_price=round(fill_price, 4),
            slippage_bps=round(total_bps, 2),
            fill_ratio=round(fill_ratio, 4),
            timestamp=now,
            side=side.lower(),
            volume_impact_bps=round(volume_impact_bps, 2),
            spread_cost_bps=round(spread_cost_bps, 2),
        )

        logger.info(
            "SimFill %s: intended=$%.2f → fill=$%.2f (slip=%.1f bps, fill=%.0f%%)",
            side.upper(),
            price,
            fill.fill_price,
            fill.slippage_bps,
            fill.fill_ratio * 100,
        )

        return fill

    def _compute_fill_ratio(
        self,
        volume: Optional[float],
        volatility: Optional[float],
        order_qty: Optional[int],
    ) -> float:
        """Compute probabilistic fill ratio in (0, 1].

        Higher volume and lower volatility → higher fill probability.
        """
        base_fill = 0.95  # Start with 95% fill

        # Volume adjustment
        if volume and volume > 0 and order_qty and order_qty > 0:
            participation = order_qty / volume
            if participation > 0.10:
                base_fill *= 0.60  # Very large order
            elif participation > 0.05:
                base_fill *= 0.80
            elif participation > 0.01:
                base_fill *= 0.90

        # Volatility adjustment (high vol → more partial fills)
        if volatility and volatility > 0.30:
            base_fill *= 0.90
        elif volatility and volatility > 0.50:
            base_fill *= 0.80

        # Add randomness
        fill_ratio = base_fill * self.rng.uniform(0.85, 1.0)

        # Clamp to (0, 1]
        return max(0.01, min(1.0, fill_ratio))


# Singleton
_simulator: Optional[ExecutionSimulator] = None


def get_execution_simulator() -> ExecutionSimulator:
    """Get or create the singleton ExecutionSimulator."""
    global _simulator
    if _simulator is None:
        slippage = float(os.getenv("SLIPPAGE_BPS", "5.0"))
        seed_val = int(os.getenv("FILL_SEED", "0"))
        partial = os.getenv("PARTIAL_FILL_ENABLED", "true").lower() == "true"
        _simulator = ExecutionSimulator(
            slippage_bps=slippage,
            seed=seed_val if seed_val != 0 else None,
            partial_fill_enabled=partial,
        )
    return _simulator
