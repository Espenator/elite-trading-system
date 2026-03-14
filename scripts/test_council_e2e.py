"""
End-to-end council test for Embodier Trader.
Verifies PC1 -> council DAG -> PC2 brain_service -> hypothesis inference.

Run from backend/ directory:
    cd backend
    python -m scripts.test_council_e2e

Or from repo root:
    cd backend && python ../scripts/test_council_e2e.py
"""
import asyncio
import os
import sys
import time

# Ensure backend is on the path
_backend_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "backend")
if os.path.isdir(_backend_dir) and _backend_dir not in sys.path:
    sys.path.insert(0, _backend_dir)

# Load .env from backend/
try:
    from dotenv import load_dotenv
    _env_file = os.path.join(_backend_dir, ".env")
    if os.path.exists(_env_file):
        load_dotenv(_env_file)
        print(f"Loaded .env from {_env_file}")
except ImportError:
    pass


async def main():
    symbol = os.getenv("TEST_SYMBOL", "NVDA")
    print(f"\n{'='*60}")
    print(f"  EMBODIER TRADER E2E COUNCIL TEST")
    print(f"{'='*60}")
    print(f"  Symbol:     {symbol}")
    print(f"  BRAIN_HOST: {os.getenv('BRAIN_HOST', 'localhost')}")
    print(f"  BRAIN_PORT: {os.getenv('BRAIN_PORT', '50051')}")
    print(f"  BRAIN_ENABLED: {os.getenv('BRAIN_ENABLED', 'false')}")
    print(f"  LLM_ENABLED:   {os.getenv('LLM_ENABLED', 'false')}")
    print(f"  BRAIN_SERVICE_TIMEOUT: {os.getenv('BRAIN_SERVICE_TIMEOUT', '1.5')}s")
    print()

    # 1. Test brain_client connectivity
    print("[1/3] Testing brain_client connectivity...")
    t0 = time.perf_counter()
    try:
        from app.services.brain_client import get_brain_client
        client = get_brain_client()
        status = client.get_status()
        elapsed = (time.perf_counter() - t0) * 1000
        print(f"  brain_client status: enabled={status['enabled']}, host={status['host']}:{status['port']}")
        print(f"  circuit_state={status['circuit_state']}")
        print(f"  ({elapsed:.0f}ms)")
        if not status["enabled"]:
            print("  WARNING: brain_client is DISABLED. Set BRAIN_ENABLED=true in .env")
    except Exception as e:
        print(f"  ERROR: brain_client import failed: {e}")
        return

    # 2. Run council
    print(f"\n[2/3] Running 35-agent council for {symbol}...")
    t1 = time.perf_counter()
    try:
        from app.council.runner import run_council
        decision = await run_council(symbol=symbol, timeframe="1d")
        total_ms = (time.perf_counter() - t1) * 1000
    except Exception as e:
        print(f"  ERROR: Council run failed: {e}")
        import traceback
        traceback.print_exc()
        return

    # 3. Report results
    print(f"\n{'='*60}")
    print(f"  COUNCIL DECISION")
    print(f"{'='*60}")
    print(f"  Direction:    {decision.final_direction}")
    print(f"  Confidence:   {decision.final_confidence:.3f}")
    print(f"  Vetoed:       {decision.vetoed}")
    print(f"  Exec Ready:   {decision.execution_ready}")
    print(f"  Decision ID:  {decision.council_decision_id}")
    print(f"  Total Time:   {total_ms:.0f}ms")

    print(f"\n  AGENT VOTES ({len(decision.votes)} agents)")
    print(f"  {'Agent':<25} {'Dir':<6} {'Conf':>6}  Source")
    print(f"  {'-'*25} {'-'*6} {'-'*6}  {'-'*15}")

    hyp_vote = None
    for vote in decision.votes:
        meta = vote.metadata if hasattr(vote, "metadata") and vote.metadata else {}
        is_fallback = meta.get("fallback", False)
        is_brain = meta.get("brain_enabled", False)
        is_router = meta.get("router_fallback", False)

        if is_fallback:
            source = "CPU-fallback"
        elif is_brain:
            source = f"brain-PC2 ({meta.get('llm_latency_ms', 0):.0f}ms)"
        elif is_router:
            source = f"router/{meta.get('tier', '?')}"
        else:
            source = "local"

        veto_mark = " [VETO]" if hasattr(vote, "veto") and vote.veto else ""
        print(f"  {vote.agent_name:<25} {vote.direction:<6} {vote.confidence:>6.3f}  {source}{veto_mark}")

        if vote.agent_name == "hypothesis":
            hyp_vote = vote

    # 4. Verdict
    print(f"\n{'='*60}")
    if hyp_vote:
        meta = hyp_vote.metadata if hasattr(hyp_vote, "metadata") and hyp_vote.metadata else {}
        used_llm = meta.get("brain_enabled", False) and not meta.get("fallback", False)
        used_router = meta.get("router_fallback", False)
        is_fallback = meta.get("fallback", False)

        if used_llm:
            print(f"  [PASS] hypothesis used brain_pc2 LLM inference")
            print(f"         latency={meta.get('llm_latency_ms', 0):.0f}ms, conf={meta.get('llm_confidence', 0):.3f}")
        elif used_router:
            print(f"  [OK]   hypothesis used LLM router (tier={meta.get('tier', '?')})")
            print(f"         angles={meta.get('parallel_angles', 0)}, conf={meta.get('llm_confidence', 0):.3f}")
        elif is_fallback:
            print(f"  [WARN] hypothesis used CPU fallback — brain_service unreachable")
            print(f"         error={meta.get('error', 'unknown')}")
        else:
            print(f"  [WARN] hypothesis source unknown: meta={meta}")
    else:
        print(f"  [FAIL] hypothesis agent did not vote!")

    print(f"{'='*60}\n")


if __name__ == "__main__":
    asyncio.run(main())
