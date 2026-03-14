"""ELO Rating Service — real ELO ratings for council agents based on signal outcomes.

When a trade outcome resolves, agents that voted in the correct direction
"win" against agents that voted in the wrong direction. ELO ratings are
updated using the standard chess ELO formula (K=32).

Ratings persist via db_service config so they survive restarts.
All operations are wrapped in try/except so ELO failures never break
the core trading pipeline.

Wire-in points:
  - outcome_tracker._resolve_position() calls elo_service.update_from_outcome()
  - /api/v1/agents/elo-leaderboard reads from elo_service.get_leaderboard()
  - Arbiter can optionally blend ELO into vote weights
"""

import logging
from typing import Any, Dict, List, Optional, Tuple

from app.services.database import db_service

logger = logging.getLogger(__name__)

CONFIG_KEY = "elo_ratings"

# Default seed rating for all agents
SEED_ELO = 1500

# K-factor: how much each game moves ratings (32 is standard chess)
K_FACTOR = 32

# Minimum/maximum ELO to prevent runaway ratings
MIN_ELO = 800
MAX_ELO = 2200


def _elo_update(winner_elo: float, loser_elo: float, k: float = K_FACTOR) -> Tuple[float, float]:
    """Standard ELO update formula.

    Returns (new_winner_elo, new_loser_elo).
    """
    expected_w = 1.0 / (1.0 + 10.0 ** ((loser_elo - winner_elo) / 400.0))
    expected_l = 1.0 - expected_w
    new_winner = winner_elo + k * (1.0 - expected_w)
    new_loser = loser_elo + k * (0.0 - expected_l)
    return new_winner, new_loser


class EloService:
    """Manages ELO ratings for all council agents."""

    def __init__(self):
        self._ratings: Dict[str, float] = {}
        self._games: Dict[str, int] = {}  # games played per agent
        self._wins: Dict[str, int] = {}
        self._losses: Dict[str, int] = {}
        self._streaks: Dict[str, int] = {}  # positive = win streak, negative = loss streak
        self._last_updated: Optional[str] = None
        self._load()

    def _load(self) -> None:
        """Load persisted ELO ratings from config store."""
        try:
            saved = db_service.get_config(CONFIG_KEY)
            if saved and isinstance(saved, dict):
                self._ratings = saved.get("ratings", {})
                self._games = saved.get("games", {})
                self._wins = saved.get("wins", {})
                self._losses = saved.get("losses", {})
                self._streaks = saved.get("streaks", {})
                self._last_updated = saved.get("last_updated")
                if self._ratings:
                    logger.info(
                        "EloService: loaded %d agent ratings (range %.0f-%.0f)",
                        len(self._ratings),
                        min(self._ratings.values()),
                        max(self._ratings.values()),
                    )
        except Exception as e:
            logger.debug("EloService: using seed ratings (load failed: %s)", e)

    def _save(self) -> None:
        """Persist ELO ratings to config store."""
        try:
            from datetime import datetime, timezone
            self._last_updated = datetime.now(timezone.utc).isoformat()
            db_service.set_config(CONFIG_KEY, {
                "ratings": self._ratings,
                "games": self._games,
                "wins": self._wins,
                "losses": self._losses,
                "streaks": self._streaks,
                "last_updated": self._last_updated,
            })
        except Exception as e:
            logger.debug("EloService: persist failed: %s", e)

    def get_elo(self, agent_name: str) -> float:
        """Get current ELO rating for an agent (seed if unknown)."""
        return self._ratings.get(agent_name, SEED_ELO)

    def get_all_ratings(self) -> Dict[str, float]:
        """Return all agent ratings."""
        return dict(self._ratings)

    def get_leaderboard(self) -> List[Dict[str, Any]]:
        """Return sorted leaderboard with stats."""
        entries = []
        for agent, elo in self._ratings.items():
            games = self._games.get(agent, 0)
            wins = self._wins.get(agent, 0)
            streak = self._streaks.get(agent, 0)
            win_rate = round(wins / games, 4) if games > 0 else 0.0
            entries.append({
                "agent_id": agent,
                "name": agent.replace("_", " ").title(),
                "elo": round(elo),
                "games": games,
                "wins": wins,
                "losses": self._losses.get(agent, 0),
                "win_rate": win_rate,
                "streak": streak,
            })
        entries.sort(key=lambda x: x["elo"], reverse=True)
        for i, entry in enumerate(entries):
            entry["rank"] = i + 1
        return entries

    def update_from_outcome(
        self,
        votes: List[Dict[str, Any]],
        outcome: str,
        final_direction: str,
        symbol: str = "",
    ) -> Dict[str, float]:
        """Update ELO ratings based on a resolved trade outcome.

        Parameters
        ----------
        votes : list of dicts
            Each dict has at least {agent_name, direction, confidence}.
        outcome : str
            "win" or "loss" (scratches are ignored).
        final_direction : str
            The council's final direction ("buy" or "sell").
        symbol : str
            For logging only.

        Returns
        -------
        Dict of {agent_name: new_elo} for all updated agents.
        """
        if outcome not in ("win", "loss"):
            return {}  # Scratches don't update ELO

        if not votes:
            return {}

        # Determine correct direction
        if outcome == "win":
            correct_direction = final_direction
        else:
            correct_direction = "sell" if final_direction == "buy" else "buy"

        # Split agents into winners and losers
        winners = []
        losers = []
        for v in votes:
            agent = v.get("agent_name", v.get("agent", ""))
            direction = v.get("direction", "hold")
            if not agent:
                continue
            # Ensure agent has a rating
            if agent not in self._ratings:
                self._ratings[agent] = SEED_ELO
                self._games[agent] = 0
                self._wins[agent] = 0
                self._losses[agent] = 0
                self._streaks[agent] = 0

            if direction == correct_direction:
                winners.append(agent)
            elif direction != "hold":
                losers.append(agent)
            # hold votes don't participate in ELO updates

        if not winners or not losers:
            # Need both sides for ELO updates
            return {}

        # Each winner plays against each loser (round-robin)
        # Scale K down by number of matchups to prevent inflation
        num_matchups = len(winners) * len(losers)
        k = K_FACTOR / max(1, num_matchups ** 0.5)  # sqrt scaling

        updated = {}
        for w_agent in winners:
            for l_agent in losers:
                w_elo = self._ratings[w_agent]
                l_elo = self._ratings[l_agent]
                new_w, new_l = _elo_update(w_elo, l_elo, k=k)
                self._ratings[w_agent] = max(MIN_ELO, min(MAX_ELO, new_w))
                self._ratings[l_agent] = max(MIN_ELO, min(MAX_ELO, new_l))

        # Update stats for all participants
        for agent in winners:
            self._games[agent] = self._games.get(agent, 0) + 1
            self._wins[agent] = self._wins.get(agent, 0) + 1
            streak = self._streaks.get(agent, 0)
            self._streaks[agent] = max(1, streak + 1) if streak >= 0 else 1
            updated[agent] = round(self._ratings[agent])

        for agent in losers:
            self._games[agent] = self._games.get(agent, 0) + 1
            self._losses[agent] = self._losses.get(agent, 0) + 1
            streak = self._streaks.get(agent, 0)
            self._streaks[agent] = min(-1, streak - 1) if streak <= 0 else -1
            updated[agent] = round(self._ratings[agent])

        self._save()

        logger.info(
            "ELO updated for %s %s: %d winners, %d losers, %d agents adjusted (k=%.1f)",
            symbol, outcome, len(winners), len(losers), len(updated), k,
        )
        return updated

    def get_elo_weights(self) -> Dict[str, float]:
        """Return ELO-based weights normalized so they can be blended into council voting.

        Higher ELO = higher weight. Normalized so the mean is 1.0.
        Only returns weights for agents with at least 1 game played.
        """
        active = {
            agent: elo
            for agent, elo in self._ratings.items()
            if self._games.get(agent, 0) > 0
        }
        if not active:
            return {}

        total = sum(active.values())
        count = len(active)
        if total <= 0 or count == 0:
            return {}

        mean_elo = total / count
        if mean_elo <= 0:
            return {}

        return {
            agent: round(elo / mean_elo, 4)
            for agent, elo in active.items()
        }


# Module-level singleton
_elo_instance: Optional[EloService] = None


def get_elo_service() -> EloService:
    """Get or create the global EloService singleton."""
    global _elo_instance
    if _elo_instance is None:
        _elo_instance = EloService()
    return _elo_instance
