"""Intelligence sub-package — LLM routing, AI reasoning, cognitive telemetry.

Re-exports from the flat services/ directory for organized imports.
Existing imports still work.
"""
from app.services import intelligence_orchestrator  # noqa: F401
from app.services import intelligence_cache  # noqa: F401
from app.services import llm_router  # noqa: F401
from app.services import llm_schemas  # noqa: F401
from app.services import adaptive_router  # noqa: F401
from app.services import claude_reasoning  # noqa: F401
from app.services import perplexity_intelligence  # noqa: F401
from app.services import brain_client  # noqa: F401
from app.services import cognitive_telemetry  # noqa: F401
