"""Brain Service gRPC server — runs on PC2 (ProfitTrader).

Provides LLM inference, distributed council stages, feature computation,
batch ML scoring, and universe scanning via Ollama + GPU.

Level 3 Distributed Architecture:
  PC1 (ESPENMAIN) ──gRPC──▶ PC2 (ProfitTrader)
    - InferCandidateContext: LLM hypothesis generation
    - CriticPostmortem: Post-trade analysis
    - RunCouncilStage: Run perception agents on PC2 (Stage 1)
    - ComputeFeatures: GPU feature computation for symbols
    - ScanUniverse: Parallel discovery scanning
    - BatchScore: GPU-accelerated ML scoring

Usage:
    python server.py [--port 50051]
"""
import asyncio
import json
import logging
import os
import signal
import sys
import time
from concurrent import futures
from pathlib import Path

# Load backend/.env so brain_service gets OLLAMA_BASE_URL, BRAIN_PORT, etc.
try:
    from dotenv import load_dotenv
    _env = Path(__file__).parent.parent / "backend" / ".env"
    if _env.exists():
        load_dotenv(_env, override=False)  # don't override explicit system vars
except ImportError:
    pass  # dotenv not required

# ── CPU Affinity: pin brain_service to P-cores for low-latency inference ──
try:
    import psutil
    _p = psutil.Process(os.getpid())
    _cpu_count = psutil.cpu_count(logical=True)
    if _cpu_count and _cpu_count >= 16:
        # i7-13700: P-cores = logical 0-15, E-cores = logical 16-23
        _p.cpu_affinity(list(range(0, 16)))
    # else: fewer cores, let OS schedule freely
except (ImportError, OSError, AttributeError):
    pass  # psutil not installed or platform doesn't support cpu_affinity

# Add proto dir and backend to path for imports
PROTO_DIR = Path(__file__).parent / "proto"
BACKEND_DIR = Path(__file__).parent.parent / "backend"
sys.path.insert(0, str(PROTO_DIR))
if BACKEND_DIR.exists():
    sys.path.insert(0, str(BACKEND_DIR))

try:
    import grpc
    from proto import brain_pb2, brain_pb2_grpc
except ImportError:
    logging.error("gRPC stubs not found. Run: python compile_proto.py")
    sys.exit(1)

from ollama_client import infer_candidate_context, critic_postmortem

logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("brain_service")

PORT = int(os.getenv("BRAIN_PORT", "50051"))
HEALTH_PORT = int(os.getenv("BRAIN_HEALTH_PORT", "50052"))
MAX_WORKERS = int(os.getenv("BRAIN_MAX_WORKERS", "8"))

# ── Inference Metrics Tracker ────────────────────────────────────
_last_inference: dict = {}
_inference_count: int = 0


def record_inference(model: str, latency_ms: float, confidence: float):
    """Record last inference metrics for the health endpoint."""
    global _last_inference, _inference_count
    from datetime import datetime, timezone
    _inference_count += 1
    _last_inference = {
        "model": model,
        "latency_ms": round(latency_ms, 1),
        "confidence": round(confidence, 4),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "total_inferences": _inference_count,
    }


class BrainServiceServicer(brain_pb2_grpc.BrainServiceServicer):
    """gRPC service implementation — LLM + distributed compute."""

    def __init__(self):
        self._call_count = 0
        self._total_infer_ms = 0.0
        self._total_critic_ms = 0.0
        self._infer_count = 0
        self._critic_count = 0

    async def InferCandidateContext(self, request, context):
        t0 = time.monotonic()
        logger.info(
            "InferCandidateContext: symbol=%s, timeframe=%s, regime=%s",
            request.symbol, request.timeframe, request.regime,
        )
        try:
            result = await infer_candidate_context(
                symbol=request.symbol,
                timeframe=request.timeframe,
                feature_json=request.feature_json,
                regime=request.regime,
                context=request.context,
            )
            latency_ms = (time.monotonic() - t0) * 1000
            self._infer_count += 1
            self._total_infer_ms += latency_ms
            model_used = result.get("_model_used", "unknown")
            record_inference(
                model=model_used,
                latency_ms=latency_ms,
                confidence=result["confidence"],
            )
            logger.info(
                "InferCandidateContext done: symbol=%s, model=%s, conf=%.2f, %.0fms",
                request.symbol, model_used, result["confidence"], latency_ms,
            )
            return brain_pb2.InferResponse(
                summary=result["summary"],
                confidence=result["confidence"],
                risk_flags=result["risk_flags"],
                reasoning_bullets=result["reasoning_bullets"],
            )
        except Exception as e:
            latency_ms = (time.monotonic() - t0) * 1000
            logger.exception("InferCandidateContext error (%.0fms): %s", latency_ms, e)
            return brain_pb2.InferResponse(
                summary="Internal error",
                confidence=0.1,
                risk_flags=["internal_error"],
                error=str(e),
            )

    async def CriticPostmortem(self, request, context):
        t0 = time.monotonic()
        logger.info(
            "CriticPostmortem: trade_id=%s, symbol=%s",
            request.trade_id, request.symbol,
        )
        try:
            result = await critic_postmortem(
                trade_id=request.trade_id,
                symbol=request.symbol,
                entry_context=request.entry_context,
                outcome_json=request.outcome_json,
            )
            latency_ms = (time.monotonic() - t0) * 1000
            self._critic_count += 1
            self._total_critic_ms += latency_ms
            model_used = result.get("_model_used", "unknown")
            record_inference(
                model=model_used,
                latency_ms=latency_ms,
                confidence=result["performance_score"],
            )
            logger.info(
                "CriticPostmortem done: symbol=%s, model=%s, score=%.2f, %.0fms",
                request.symbol, model_used, result["performance_score"], latency_ms,
            )
            return brain_pb2.CriticResponse(
                analysis=result["analysis"],
                lessons=result["lessons"],
                performance_score=result["performance_score"],
            )
        except Exception as e:
            latency_ms = (time.monotonic() - t0) * 1000
            logger.exception("CriticPostmortem error (%.0fms): %s", latency_ms, e)
            return brain_pb2.CriticResponse(
                analysis="Internal error",
                error=str(e),
            )

    async def Embed(self, request, context):
        """Embed text using sentence-transformers on GPU."""
        try:
            from app.knowledge.embedding_service import get_embedding_engine
            engine = get_embedding_engine()
            embedding = engine.embed([request.text])[0]
            return brain_pb2.EmbedResponse(
                embedding=embedding.tolist() if hasattr(embedding, "tolist") else list(embedding),
            )
        except Exception as e:
            logger.warning("Embed error: %s", e)
            return brain_pb2.EmbedResponse(embedding=[], error=str(e))

    # ── Level 3A: Distributed Council Stage ─────────────────────────────

    async def RunCouncilStage(self, request, context):
        """Run a council stage (set of agents) on PC2 and return votes.

        This allows PC1 to offload Stage 1 (13 perception agents) to PC2,
        effectively doubling council throughput by running stages in parallel
        across both PCs.
        """
        t0 = time.monotonic()
        logger.info(
            "RunCouncilStage: symbol=%s, stage=%d, agents=%s",
            request.symbol, request.stage, list(request.agent_types),
        )
        try:
            features = json.loads(request.feature_json) if request.feature_json else {}
            ctx = json.loads(request.context_json) if request.context_json else {}

            from app.council.blackboard import BlackboardState
            from app.council.task_spawner import TaskSpawner

            blackboard = BlackboardState(
                symbol=request.symbol,
                raw_features=features,
            )
            ctx["blackboard"] = blackboard

            spawner = TaskSpawner(blackboard)
            spawner.register_all_agents()

            configs = [
                {
                    "agent_type": at,
                    "symbol": request.symbol,
                    "timeframe": request.timeframe or "1d",
                    "context": ctx,
                }
                for at in request.agent_types
                if at in spawner.registered_agents
            ]

            votes = await spawner.spawn_parallel(configs)
            latency_ms = (time.monotonic() - t0) * 1000

            proto_votes = []
            for v in votes:
                proto_votes.append(brain_pb2.AgentVoteProto(
                    agent_name=v.agent_name,
                    direction=v.direction,
                    confidence=v.confidence,
                    reasoning=v.reasoning[:500],
                    veto=v.veto if hasattr(v, "veto") else False,
                    veto_reason=v.veto_reason if hasattr(v, "veto_reason") else "",
                    metadata_json=json.dumps(v.metadata) if hasattr(v, "metadata") and v.metadata else "{}",
                ))

            logger.info(
                "RunCouncilStage: stage=%d, %d votes, %.0fms",
                request.stage, len(proto_votes), latency_ms,
            )
            return brain_pb2.CouncilStageResponse(
                votes=proto_votes,
                stage_latency_ms=latency_ms,
            )
        except Exception as e:
            logger.exception("RunCouncilStage error: %s", e)
            return brain_pb2.CouncilStageResponse(
                error=str(e),
                stage_latency_ms=(time.monotonic() - t0) * 1000,
            )

    # ── Level 3B: Feature Computation ───────────────────────────────────

    async def ComputeFeatures(self, request, context):
        """Compute feature vectors for symbols using PC2's GPU/CPU.

        Allows PC1 to offload heavy TA computation to PC2, freeing PC1
        for council evaluation and order execution.
        """
        t0 = time.monotonic()
        logger.info("ComputeFeatures: %d symbols", len(request.symbols))
        try:
            from app.features.feature_aggregator import aggregate

            results = {}
            tasks = [
                aggregate(sym, timeframe=request.timeframe or "1d")
                for sym in request.symbols
            ]
            fvs = await asyncio.gather(*tasks, return_exceptions=True)

            for sym, fv in zip(request.symbols, fvs):
                if isinstance(fv, Exception):
                    logger.warning("Feature computation failed for %s: %s", sym, fv)
                    results[sym] = json.dumps({"error": str(fv)})
                else:
                    results[sym] = json.dumps(fv.to_dict())

            latency_ms = (time.monotonic() - t0) * 1000
            logger.info("ComputeFeatures: %d symbols in %.0fms", len(results), latency_ms)
            return brain_pb2.FeatureResponse(
                feature_vectors=results,
                compute_latency_ms=latency_ms,
            )
        except Exception as e:
            logger.exception("ComputeFeatures error: %s", e)
            return brain_pb2.FeatureResponse(
                error=str(e),
                compute_latency_ms=(time.monotonic() - t0) * 1000,
            )

    # ── Level 3C: Universe Scanner ──────────────────────────────────────

    async def ScanUniverse(self, request, context):
        """Scan symbols for trading opportunities on PC2.

        PC2 uses its Alpaca Key 2 (discovery account) to scan the universe
        and report high-score candidates back to PC1 for council evaluation.
        """
        t0 = time.monotonic()
        logger.info(
            "ScanUniverse: %d symbols, regime=%s, min_score=%.1f",
            len(request.symbols), request.regime, request.min_score,
        )
        try:
            candidates = []
            # Score each symbol using signal engine logic
            for sym in request.symbols:
                try:
                    from app.features.feature_aggregator import aggregate
                    fv = await aggregate(sym, timeframe="1d")
                    features = fv.to_dict().get("features", {})

                    # Simple composite scoring from price + volume + momentum
                    rsi = features.get("ind_rsi_14", 50)
                    vol_surge = features.get("volume_surge_ratio", 1.0)
                    ret_1d = features.get("return_1d", 0)

                    # Long score: momentum + volume confirmation
                    long_score = 50.0
                    if rsi < 30:
                        long_score += 15  # Oversold bounce
                    elif rsi > 70:
                        long_score -= 10  # Overbought risk
                    if vol_surge > 2.0:
                        long_score += 10  # Volume breakout
                    if ret_1d > 0.02:
                        long_score += 10  # Strong momentum
                    elif ret_1d < -0.03:
                        long_score += 5   # Potential reversal

                    # Short score
                    short_score = 50.0
                    if rsi > 75:
                        short_score += 15
                    if ret_1d < -0.02:
                        short_score += 10
                    if vol_surge > 2.0:
                        short_score += 5

                    # Report if above threshold
                    if long_score >= request.min_score:
                        candidates.append(brain_pb2.ScanCandidate(
                            symbol=sym,
                            signal_score=long_score,
                            direction="long",
                            label=f"Discovery scan: RSI={rsi:.0f}, VolSurge={vol_surge:.1f}x",
                            volume_surge=vol_surge,
                        ))
                    if short_score >= request.min_score:
                        candidates.append(brain_pb2.ScanCandidate(
                            symbol=sym,
                            signal_score=short_score,
                            direction="short",
                            label=f"Short scan: RSI={rsi:.0f}, Ret1d={ret_1d:.2%}",
                            volume_surge=vol_surge,
                        ))
                except Exception as e:
                    logger.debug("Scan failed for %s: %s", sym, e)

            latency_ms = (time.monotonic() - t0) * 1000
            # Sort by score descending
            candidates.sort(key=lambda c: c.signal_score, reverse=True)

            logger.info(
                "ScanUniverse: scanned %d, found %d candidates in %.0fms",
                len(request.symbols), len(candidates), latency_ms,
            )
            return brain_pb2.ScanResponse(
                candidates=candidates[:50],  # Cap at top 50
                symbols_scanned=len(request.symbols),
                scan_latency_ms=latency_ms,
            )
        except Exception as e:
            logger.exception("ScanUniverse error: %s", e)
            return brain_pb2.ScanResponse(
                error=str(e),
                scan_latency_ms=(time.monotonic() - t0) * 1000,
            )

    # ── Level 2B: Batch ML Scoring ──────────────────────────────────────

    async def BatchScore(self, request, context):
        """Batch-score multiple symbols using XGBoost + LSTM ensemble on GPU."""
        t0 = time.monotonic()
        logger.info("BatchScore: %d symbols", len(request.symbols))
        try:
            import pandas as pd
            from app.modules.ml_engine.ensemble_scorer import get_ensemble_scorer

            scorer = get_ensemble_scorer()
            features_df = pd.read_json(request.feature_json) if request.feature_json else pd.DataFrame()
            feature_cols = list(request.feature_cols)

            results = await scorer.batch_score(
                symbols=list(request.symbols),
                features=features_df,
                feature_cols=feature_cols,
            )

            scores = []
            for sym, result in results.items():
                scores.append(brain_pb2.SymbolScore(
                    symbol=sym,
                    prob_up=result.get("prob_up", 0.5),
                    xgb_prob=result.get("xgb_prob", 0.0) or 0.0,
                    lstm_prob=result.get("lstm_prob", 0.0) or 0.0,
                    ensemble=result.get("ensemble", False),
                ))

            latency_ms = (time.monotonic() - t0) * 1000
            logger.info("BatchScore: %d scores in %.0fms", len(scores), latency_ms)
            return brain_pb2.BatchScoreResponse(
                scores=scores,
                scoring_latency_ms=latency_ms,
            )
        except Exception as e:
            logger.exception("BatchScore error: %s", e)
            return brain_pb2.BatchScoreResponse(
                error=str(e),
                scoring_latency_ms=(time.monotonic() - t0) * 1000,
            )


async def _build_health_response() -> dict:
    """Build the full health response for the /health HTTP endpoint.

    Returns all fields that PC1's /api/health/pc2 proxy expects:
    VRAM metrics, loaded models, last_inference, cpu_affinity, ollama env flags.
    """
    from datetime import datetime, timezone

    # GPU info via PyTorch
    cuda_available = False
    gpu_name = "none"
    cuda_version = "unavailable"
    total_vram_gb = used_vram_gb = free_vram_gb = 0.0
    try:
        import torch
        cuda_available = torch.cuda.is_available()
        if cuda_available:
            props = torch.cuda.get_device_properties(0)
            total_vram_gb = props.total_memory / 1e9
            cuda_version = torch.version.cuda or "unknown"
            try:
                free_bytes, total_bytes = torch.cuda.mem_get_info(0)
                used_vram_gb = (total_bytes - free_bytes) / 1e9
                free_vram_gb = free_bytes / 1e9
            except Exception:
                used_vram_gb = torch.cuda.memory_allocated(0) / 1e9
                free_vram_gb = total_vram_gb - used_vram_gb
            gpu_name = props.name
    except ImportError:
        pass

    # Market hours check for VRAM budget status
    market_hours_mode = False
    try:
        from app.jobs.gpu_trainer import is_market_hours
        market_hours_mode = is_market_hours()
    except Exception:
        pass

    # VRAM budget object
    vram_budget = {
        "total_gb": round(total_vram_gb, 2),
        "used_gb": round(used_vram_gb, 2),
        "free_gb": round(free_vram_gb, 2),
        "budget_ok": free_vram_gb >= 0.7,  # True if headroom maintained
        "market_hours_mode": market_hours_mode,
    }

    # Ollama loaded models
    ollama_models = []
    ollama_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    try:
        import httpx
        async with httpx.AsyncClient(timeout=2.0) as client:
            r = await client.get(f"{ollama_url}/api/tags")
            ollama_models = [
                {
                    "name": m["name"],
                    "size_gb": round(m.get("size", 0) / 1e9, 2),
                }
                for m in r.json().get("models", [])
            ]
    except Exception:
        pass

    # CPU affinity
    affinity_info = {"cpu_affinity": "unknown"}
    try:
        from app.core.hardware_profile import get_affinity_info
        affinity_info = get_affinity_info()
    except Exception:
        pass

    return {
        "pc": "PC2-ProfitTrader",
        "status": "healthy",
        "role": "secondary",
        # GPU
        "cuda_available": cuda_available,
        "cuda_version": cuda_version,
        "gpu_name": gpu_name,
        "vram": vram_budget,
        # Flat fields kept for PC1 proxy backwards compat
        "vram_total_gb": vram_budget["total_gb"],
        "vram_used_gb": vram_budget["used_gb"],
        "vram_free_gb": vram_budget["free_gb"],
        # Models
        "loaded_models": ollama_models,
        # Inference
        "last_inference": _last_inference or None,
        "grpc_status": "healthy",
        "gpu_worker": "active",
        # Hardware
        "cpu_affinity": affinity_info,
        # Ollama env flags
        "ollama_flash_attention": os.getenv("OLLAMA_FLASH_ATTENTION", "0"),
        "ollama_kv_cache_type": os.getenv("OLLAMA_KV_CACHE_TYPE", "default"),
        # Connectivity
        "redis_mesh": "connected",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


async def _start_health_http_server(port: int):
    """Start a lightweight aiohttp server for the /health endpoint."""
    try:
        from aiohttp import web

        async def health_handler(request):
            data = await _build_health_response()
            return web.json_response(data)

        app = web.Application()
        app.router.add_get("/health", health_handler)

        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, "0.0.0.0", port)
        await site.start()
        logger.info("Health HTTP endpoint running on http://0.0.0.0:%d/health", port)
        return runner
    except ImportError:
        logger.warning("aiohttp not installed — /health HTTP endpoint disabled")
        return None
    except Exception as e:
        logger.warning("Failed to start health HTTP server: %s", e)
        return None


async def serve():
    # Pin brain_service to P-cores for low-latency inference dispatch (PC2 only)
    try:
        from app.core.hardware_profile import apply_affinity, set_process_priority, pin_to_p_cores
        apply_affinity("p_cores")  # Logical CPUs 0-15 on i7-13700
        set_process_priority("above_normal")
        logger.info("Brain Service pinned to P-cores with above_normal priority")
    except Exception as e:
        logger.debug("CPU affinity/priority not applied: %s", e)

    # Start HTTP health endpoint
    health_runner = await _start_health_http_server(HEALTH_PORT)

    server = grpc.aio.server(futures.ThreadPoolExecutor(max_workers=MAX_WORKERS))
    brain_pb2_grpc.add_BrainServiceServicer_to_server(
        BrainServiceServicer(), server
    )
    # Bind address: use BRAIN_SERVICE_HOST env var for cross-PC access.
    # Default to 0.0.0.0 to accept connections from PC1 over LAN.
    bind_host = os.getenv("BRAIN_SERVICE_HOST", "0.0.0.0")
    bind_addr = f"{bind_host}:{PORT}"
    server.add_insecure_port(bind_addr)

    logger.info("Brain Service starting on port %d (max_workers=%d)", PORT, MAX_WORKERS)
    logger.info(
        "Distributed RPCs: InferCandidateContext, CriticPostmortem, Embed, "
        "RunCouncilStage, ComputeFeatures, ScanUniverse, BatchScore"
    )
    await server.start()
    logger.info("Brain Service READY — waiting for requests")

    stop_event = asyncio.Event()

    def _signal_handler():
        logger.info("Shutdown signal received")
        stop_event.set()

    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, _signal_handler)
        except NotImplementedError:
            pass  # Windows doesn't support add_signal_handler

    try:
        await stop_event.wait()
    except KeyboardInterrupt:
        pass

    logger.info("Shutting down Brain Service...")
    if health_runner:
        await health_runner.cleanup()
        logger.info("Health HTTP server stopped")
    await server.stop(grace=5)
    logger.info("Brain Service stopped")


if __name__ == "__main__":
    asyncio.run(serve())
