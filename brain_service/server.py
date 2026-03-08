"""Brain Service gRPC server — runs on PC2 (ProfitTrader).

Provides LLM inference via Ollama for the trading system.

Usage:
    python server.py [--port 50051]
"""
import asyncio
import logging
import os
import signal
import sys
from concurrent import futures
from pathlib import Path

# Add proto dir to path for imports
PROTO_DIR = Path(__file__).parent / "proto"
sys.path.insert(0, str(PROTO_DIR))

# Auto-compile proto if stubs missing
_proto_stubs = [PROTO_DIR / "brain_pb2.py", PROTO_DIR / "brain_pb2_grpc.py"]
if not all(stub.exists() for stub in _proto_stubs):
    logging.basicConfig(level="INFO", format="%(message)s")
    _logger = logging.getLogger("brain_service.setup")
    _logger.info("Proto stubs missing — compiling...")
    import subprocess

    _compile_script = Path(__file__).parent / "compile_proto.py"
    if not _compile_script.exists():
        _logger.error("compile_proto.py not found at %s", _compile_script)
        sys.exit(1)

    _result = subprocess.run(
        [sys.executable, str(_compile_script)],
        capture_output=True,
        text=True,
        cwd=str(Path(__file__).parent)
    )

    if _result.returncode != 0:
        _logger.error("Proto compilation failed:")
        _logger.error(_result.stderr)
        sys.exit(1)

    _logger.info("Proto compilation complete")

try:
    import grpc
    from proto import brain_pb2, brain_pb2_grpc
except ImportError as e:
    logging.error("Failed to import gRPC stubs: %s", e)
    logging.error("Try manually running: python compile_proto.py")
    sys.exit(1)

from ollama_client import infer_candidate_context, critic_postmortem

logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("brain_service")

PORT = int(os.getenv("BRAIN_PORT", "50051"))
MAX_WORKERS = int(os.getenv("BRAIN_MAX_WORKERS", "4"))


class BrainServiceServicer(brain_pb2_grpc.BrainServiceServicer):
    """gRPC service implementation wrapping Ollama LLM calls."""

    async def InferCandidateContext(self, request, context):
        logger.info(
            "InferCandidateContext: symbol=%s, timeframe=%s",
            request.symbol,
            request.timeframe,
        )
        try:
            result = await infer_candidate_context(
                symbol=request.symbol,
                timeframe=request.timeframe,
                feature_json=request.feature_json,
                regime=request.regime,
                context=request.context,
            )
            return brain_pb2.InferResponse(
                summary=result["summary"],
                confidence=result["confidence"],
                risk_flags=result["risk_flags"],
                reasoning_bullets=result["reasoning_bullets"],
            )
        except Exception as e:
            logger.exception("InferCandidateContext error: %s", e)
            return brain_pb2.InferResponse(
                summary="Internal error",
                confidence=0.1,
                risk_flags=["internal_error"],
                error=str(e),
            )

    async def CriticPostmortem(self, request, context):
        logger.info(
            "CriticPostmortem: trade_id=%s, symbol=%s",
            request.trade_id,
            request.symbol,
        )
        try:
            result = await critic_postmortem(
                trade_id=request.trade_id,
                symbol=request.symbol,
                entry_context=request.entry_context,
                outcome_json=request.outcome_json,
            )
            return brain_pb2.CriticResponse(
                analysis=result["analysis"],
                lessons=result["lessons"],
                performance_score=result["performance_score"],
            )
        except Exception as e:
            logger.exception("CriticPostmortem error: %s", e)
            return brain_pb2.CriticResponse(
                analysis="Internal error",
                error=str(e),
            )

    async def Embed(self, request, context):
        logger.info("Embed request (stub — not yet implemented)")
        return brain_pb2.EmbedResponse(
            embedding=[],
            error="not_implemented",
        )


async def serve():
    server = grpc.aio.server(futures.ThreadPoolExecutor(max_workers=MAX_WORKERS))
    brain_pb2_grpc.add_BrainServiceServicer_to_server(
        BrainServiceServicer(), server
    )
    server.add_insecure_port(f"[::]:{PORT}")

    logger.info("Brain Service starting on port %d (max_workers=%d)", PORT, MAX_WORKERS)
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
    await server.stop(grace=5)
    logger.info("Brain Service stopped")


if __name__ == "__main__":
    asyncio.run(serve())
