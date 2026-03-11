"""Direct council evaluation test — bypasses HTTP server overhead.

Tests the full 33-agent council pipeline for AAPL.
"""
import asyncio
import json
import logging
import os
import sys
import time

# Set up env
os.environ.setdefault("TRADING_MODE", "paper")
os.environ.setdefault("ENVIRONMENT", "production")

# Load .env
from dotenv import load_dotenv
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-7s %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("test_council")


async def main():
    t0 = time.time()
    logger.info("=== Council Direct Test — AAPL ===")

    # Initialize DuckDB schema
    try:
        from app.data.duckdb_storage import duckdb_store
        duckdb_store.init_schema()
        logger.info("DuckDB schema initialized")
    except Exception as e:
        logger.warning("DuckDB init: %s", e)

    # Import after env setup
    from app.council.runner import run_council

    try:
        decision = await asyncio.wait_for(
            run_council(symbol="AAPL", timeframe="1d"),
            timeout=120.0,
        )
    except asyncio.TimeoutError:
        logger.error("Council timed out after 120s")
        sys.exit(1)
    except Exception as e:
        logger.exception("Council failed: %s", e)
        sys.exit(1)

    elapsed = time.time() - t0
    result = decision.to_dict()

    logger.info("=== Council Result (%.1fs) ===", elapsed)
    logger.info("Direction: %s", result.get("final_direction"))
    logger.info("Confidence: %.2f", result.get("final_confidence", 0))
    logger.info("Execution Ready: %s", result.get("execution_ready"))
    logger.info("Vetoed: %s", result.get("vetoed"))
    logger.info("Council Decision ID: %s", result.get("council_decision_id"))

    # Count non-neutral votes
    votes = result.get("votes", [])
    non_neutral = [v for v in votes if v.get("direction") != "hold" or v.get("confidence", 0) > 0.3]
    logger.info("Total votes: %d, Non-neutral: %d (%.0f%%)",
                len(votes), len(non_neutral), 100 * len(non_neutral) / max(len(votes), 1))

    # Print each vote
    logger.info("--- Individual Votes ---")
    for v in votes:
        logger.info("  %-30s %s  conf=%.2f  %s",
                     v.get("agent_name", "?"),
                     v.get("direction", "?"),
                     v.get("confidence", 0),
                     (v.get("reasoning") or "")[:80])

    # Save full result
    with open("council_test_result.json", "w") as f:
        json.dump(result, f, indent=2, default=str)
    logger.info("Full result saved to council_test_result.json")


if __name__ == "__main__":
    asyncio.run(main())
