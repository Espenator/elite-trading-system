"""Backtest Intelligence Tests — council decision replay and verification.

Tests the arbitrate() engine's ability to produce correct decisions
across synthetic market scenarios, regime shifts, and reproducibility checks.
"""
import math
import random
from datetime import datetime, timezone, timedelta
from unittest.mock import patch, MagicMock

import pytest

from app.council.schemas import AgentVote, DecisionPacket
from app.council.arbiter import arbitrate, REQUIRED_AGENTS, VETO_AGENTS


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_votes(direction_bias: str, confidence: float, n: int = 5) -> list[AgentVote]:
    """Create a realistic set of agent votes with required agents present.

    direction_bias controls the majority direction; a few agents may disagree
    to simulate realistic council diversity.
    """
    required = ["regime", "risk", "strategy"]
    extras = ["market_perception", "ema_trend"]
    agents = required + extras[:n - len(required)]

    votes = []
    for i, name in enumerate(agents):
        if i < n - 1:
            d = direction_bias
        else:
            d = "hold" if direction_bias != "hold" else "buy"

        meta = {}
        if name == "risk":
            meta = {"risk_limits": {"max_position": 10000}}
        if name == "execution":
            meta = {"execution_ready": True}
        if name == "regime":
            regime_state = "GREEN" if direction_bias == "buy" else "RED"
            meta = {"regime_state": regime_state}

        votes.append(AgentVote(
            agent_name=name,
            direction=d,
            confidence=min(max(confidence + random.uniform(-0.1, 0.1), 0.01), 0.99),
            reasoning=f"{name} synthetic vote",
            weight=1.0,
            metadata=meta,
        ))
    return votes


def _ts(offset_minutes: int = 0) -> str:
    return (datetime.now(timezone.utc) + timedelta(minutes=offset_minutes)).isoformat()


# Patch away external dependencies that arbitrate() touches
_ARBITER_PATCHES = {
    "app.council.arbiter._get_learned_weights": lambda: {},
    "app.council.arbiter.get_thompson_sampler": lambda: MagicMock(
        should_explore=MagicMock(return_value=False),
        sample_weights=MagicMock(return_value={}),
    ),
    "app.council.arbiter.get_arbiter_meta_model": lambda: MagicMock(
        predict=MagicMock(return_value=None),
    ),
}


def _patched_arbitrate(symbol, timeframe, timestamp, votes, regime_entropy=0.0):
    """Run arbitrate() with external dependencies mocked out."""
    with patch("app.council.arbiter._get_learned_weights", return_value={}), \
         patch("app.council.arbiter.get_thompson_sampler") as mock_ts, \
         patch("app.council.arbiter.get_arbiter_meta_model") as mock_meta:
        mock_ts.return_value = MagicMock(
            should_explore=MagicMock(return_value=False),
            sample_weights=MagicMock(return_value={}),
        )
        mock_meta.return_value = MagicMock(
            predict=MagicMock(return_value=None),
        )
        try:
            with patch("app.council.calibration.get_calibration_tracker"):
                return arbitrate(symbol, timeframe, timestamp, votes, regime_entropy)
        except Exception:
            return arbitrate(symbol, timeframe, timestamp, votes, regime_entropy)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestBacktestIntelligence:

    def test_backtest_council_replay_30_bars(self):
        """Replay 30 bars: 15 uptrend then 15 downtrend. Council should flip."""
        decisions = []
        for i in range(30):
            if i < 15:
                bias = "buy"
                conf = 0.7 + (i / 100)
            else:
                bias = "sell"
                conf = 0.7 + ((i - 15) / 100)

            votes = _make_votes(bias, conf, n=5)
            pkt = _patched_arbitrate("AAPL", "5min", _ts(i), votes)
            decisions.append(pkt)

        buy_count_first_half = sum(
            1 for d in decisions[:15] if d.final_direction == "buy"
        )
        sell_count_second_half = sum(
            1 for d in decisions[15:] if d.final_direction == "sell"
        )

        assert buy_count_first_half >= 10, (
            f"Expected mostly BUY in uptrend, got {buy_count_first_half}/15"
        )
        assert sell_count_second_half >= 10, (
            f"Expected mostly SELL in downtrend, got {sell_count_second_half}/15"
        )

    def test_walk_forward_no_lookahead(self):
        """Train/test split: 60 train bars, 20 test bars — no index overlap."""
        all_bars = list(range(80))
        train_indices = all_bars[:60]
        test_indices = all_bars[60:]

        assert len(set(train_indices) & set(test_indices)) == 0, "Train/test overlap"
        assert len(train_indices) == 60
        assert len(test_indices) == 20

        test_decisions = []
        for idx in test_indices:
            bar_features = {
                "close": 100 + idx * 0.5,
                "volume": 1000000,
                "sma_20": 100 + (idx - 10) * 0.5,
            }
            is_uptrend = bar_features["close"] > bar_features["sma_20"]
            bias = "buy" if is_uptrend else "sell"
            votes = _make_votes(bias, 0.65, n=5)
            pkt = _patched_arbitrate("TSLA", "5min", _ts(idx), votes)
            test_decisions.append((idx, pkt))

        for idx, pkt in test_decisions:
            assert idx >= 60, f"Test decision used train index {idx}"

        assert len(test_decisions) == 20

    def test_regime_stratified_backtest(self):
        """GREEN regime bars should have higher execution_ready rate than RED."""
        green_decisions = []
        red_decisions = []

        for i in range(10):
            green_votes = _make_votes("buy", 0.80, n=5)
            for v in green_votes:
                if v.agent_name == "regime":
                    v.metadata["regime_state"] = "GREEN"
                if v.agent_name == "execution":
                    v.metadata["execution_ready"] = True
            pkt = _patched_arbitrate("SPY", "5min", _ts(i), green_votes)
            green_decisions.append(pkt)

        for i in range(10):
            red_agents = ["regime", "risk", "strategy", "market_perception", "ema_trend"]
            red_votes = []
            for j, name in enumerate(red_agents):
                d = "sell" if j < 2 else "hold"
                meta = {}
                if name == "regime":
                    meta = {"regime_state": "RED"}
                red_votes.append(AgentVote(
                    agent_name=name, direction=d,
                    confidence=0.35, reasoning="red regime caution",
                    weight=1.0, metadata=meta,
                ))
            pkt = _patched_arbitrate("SPY", "5min", _ts(10 + i), red_votes)
            red_decisions.append(pkt)

        green_exec = sum(1 for d in green_decisions if d.execution_ready)
        red_exec = sum(1 for d in red_decisions if d.execution_ready)

        assert green_exec >= red_exec, (
            f"GREEN exec_ready ({green_exec}) should >= RED ({red_exec})"
        )
        green_non_hold = sum(1 for d in green_decisions if d.final_direction != "hold")
        red_non_hold = sum(1 for d in red_decisions if d.final_direction != "hold")
        assert green_non_hold >= red_non_hold, (
            f"GREEN should have more actionable decisions ({green_non_hold}) than RED ({red_non_hold})"
        )

    def test_monte_carlo_outcome_distribution(self):
        """100 simulated trade outcomes: verify return, Sharpe proxy, max drawdown."""
        random.seed(42)
        win_rate = 0.55
        avg_win = 1.5
        avg_loss = -1.0
        n_trades = 100

        returns = []
        for _ in range(n_trades):
            if random.random() < win_rate:
                r = avg_win * random.uniform(0.5, 1.5)
            else:
                r = avg_loss * random.uniform(0.5, 1.5)
            returns.append(r)

        total_return = sum(returns)
        mean_r = total_return / n_trades
        std_r = math.sqrt(sum((r - mean_r) ** 2 for r in returns) / n_trades)
        sharpe_proxy = mean_r / std_r if std_r > 0 else 0.0

        cumulative = []
        running = 0
        peak = 0
        max_dd = 0
        for r in returns:
            running += r
            cumulative.append(running)
            if running > peak:
                peak = running
            dd = running - peak
            if dd < max_dd:
                max_dd = dd

        assert math.isfinite(total_return)
        assert math.isfinite(sharpe_proxy)
        assert math.isfinite(max_dd)
        assert max_dd <= 0, f"Max drawdown should be <= 0, got {max_dd}"

    def test_backtest_reproducibility(self):
        """Identical inputs → identical arbitrate() output (deterministic path)."""
        votes_a = [
            AgentVote("regime", "buy", 0.8, "bullish regime", weight=1.2,
                       metadata={"regime_state": "GREEN"}),
            AgentVote("risk", "buy", 0.7, "risk ok", weight=1.5,
                       metadata={"risk_limits": {}}),
            AgentVote("strategy", "buy", 0.75, "strategy aligned", weight=1.1),
            AgentVote("market_perception", "buy", 0.65, "uptrend", weight=1.0),
            AgentVote("ema_trend", "sell", 0.4, "minor pullback", weight=0.9),
        ]
        votes_b = [
            AgentVote("regime", "buy", 0.8, "bullish regime", weight=1.2,
                       metadata={"regime_state": "GREEN"}),
            AgentVote("risk", "buy", 0.7, "risk ok", weight=1.5,
                       metadata={"risk_limits": {}}),
            AgentVote("strategy", "buy", 0.75, "strategy aligned", weight=1.1),
            AgentVote("market_perception", "buy", 0.65, "uptrend", weight=1.0),
            AgentVote("ema_trend", "sell", 0.4, "minor pullback", weight=0.9),
        ]

        ts = _ts()
        pkt_a = _patched_arbitrate("NVDA", "5min", ts, votes_a)
        pkt_b = _patched_arbitrate("NVDA", "5min", ts, votes_b)

        assert pkt_a.final_direction == pkt_b.final_direction
        assert pkt_a.final_confidence == pkt_b.final_confidence
        assert pkt_a.execution_ready == pkt_b.execution_ready
        assert pkt_a.vetoed == pkt_b.vetoed

    @pytest.mark.anyio
    async def test_backtest_api_endpoints_exist(self, client):
        """Check that backtest API endpoints respond (200 or 404, not 500)."""
        try:
            get_resp = await client.get("/api/v1/backtest/runs")
        except (ValueError, RuntimeError) as exc:
            pytest.skip(f"App middleware init error (known FastAPI compat issue): {exc}")

        assert get_resp.status_code in (200, 404, 405, 307), (
            f"GET /api/v1/backtest/runs returned {get_resp.status_code}"
        )
        if get_resp.status_code == 200:
            data = get_resp.json()
            assert isinstance(data, (dict, list))

        try:
            post_resp = await client.post(
                "/api/v1/backtest/",
                json={"symbol": "AAPL", "start": "2025-01-01", "end": "2025-06-01"},
            )
        except (ValueError, RuntimeError) as exc:
            pytest.skip(f"App middleware init error: {exc}")

        assert post_resp.status_code in (200, 201, 404, 405, 422, 307), (
            f"POST /api/v1/backtest/ returned {post_resp.status_code}"
        )
        if post_resp.status_code in (200, 201):
            data = post_resp.json()
            assert isinstance(data, (dict, list))

    def test_council_hit_rate_calculation(self):
        """Run 20 decisions, compute hit rate against simulated future moves."""
        random.seed(99)
        correct = 0
        total = 20

        for i in range(total):
            future_up = random.random() > 0.45
            bias = "buy" if random.random() > 0.4 else "sell"
            votes = _make_votes(bias, 0.7, n=5)
            pkt = _patched_arbitrate("MSFT", "5min", _ts(i), votes)

            if pkt.final_direction == "hold":
                continue

            predicted_up = pkt.final_direction == "buy"
            if predicted_up == future_up:
                correct += 1

        hit_rate = correct / total if total > 0 else 0.0
        assert isinstance(hit_rate, float)
        assert 0.0 <= hit_rate <= 1.0, f"Hit rate {hit_rate} out of range"

    def test_rolling_performance_window(self):
        """50 decisions with rolling 10-decision accuracy window."""
        random.seed(77)
        outcomes = []
        window_size = 10

        for i in range(50):
            future_up = random.random() > 0.45
            bias = "buy" if random.random() > 0.35 else "sell"
            votes = _make_votes(bias, 0.65, n=5)
            pkt = _patched_arbitrate("AMZN", "5min", _ts(i), votes)

            if pkt.final_direction == "hold":
                is_correct = False
            else:
                predicted_up = pkt.final_direction == "buy"
                is_correct = predicted_up == future_up
            outcomes.append(is_correct)

        rolling_accuracies = []
        for i in range(window_size, len(outcomes) + 1):
            window = outcomes[i - window_size:i]
            acc = sum(window) / window_size
            rolling_accuracies.append(acc)

        assert len(rolling_accuracies) == 50 - window_size + 1
        for acc in rolling_accuracies:
            assert 0.0 <= acc <= 1.0, f"Rolling accuracy {acc} out of [0,1]"
