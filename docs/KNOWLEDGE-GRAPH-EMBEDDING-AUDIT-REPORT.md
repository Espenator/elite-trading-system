# Knowledge Graph & Embedding System — Audit Report (Prompt 19)

**Date**: March 13, 2026  
**Scope**: Knowledge extraction layer, embedding service, knowledge graph, heuristic engine, memory bank, brain gRPC Embed, council agent wiring.

---

## 1. Executive Summary

The system has a **fully built** embedding service (all-MiniLM-L6-v2, 384-dim), knowledge graph (heuristic co-occurrence edges), heuristic engine (MIN_SAMPLE=25, MIN_WIN_RATE=0.55), and memory bank (agent observations + embeddings). **Part of it is wired**: runner builds `knowledge_context` (heuristics + confirmations/contradictions + `recall_similar` memories) and stores agent memories after each council run; outcome_tracker updates memory outcomes and periodically rebuilds heuristics and knowledge edges. **Critical gaps**: (1) **No consumer of semantic memory in the hypothesis agent** — `blackboard.knowledge_context` and `relevant_memories` are never passed into the LLM prompt. (2) **Brain Embed RPC exists but is never called** from the backend. (3) **Layered memory agent** uses DuckDB lookups only (`query_recent_trades`, `query_sector_patterns`, etc.), not `memory_bank.recall_similar` or the knowledge graph; and `duckdb_service` does not define those query functions, so it always falls back to in-memory store. (4) **Heuristic/heuristic API** is not exposed via a dedicated REST endpoint (only through blackboard during council). (5) **Two outcome stores**: DuckDB `trade_outcomes` (ingested from orders) and `agent_memories.outcome_*` (updated by outcome_tracker); both are updated from the same resolution flow but serve different purposes (analytics vs. agent memory).

---

## 2. Findings

### 2.1 Embedding Service (`backend/app/knowledge/embedding_service.py`)

| Item | Status |
|------|--------|
| Model | all-MiniLM-L6-v2, 384-dim |
| GPU/CPU | Uses `EMBEDDING_DEVICE` or auto `cuda:0` / `cpu` |
| Fallback | Hash-based pseudo-embeddings when sentence-transformers missing; **fixed** to output 384-dim and safe normalization |
| `embed()` / `embed_single()` | OK; L2-normalized when non-zero |
| `find_similar()` | Cosine similarity on normalized vectors; OK |

**Verification**: Tests in `tests/test_knowledge_embedding_system.py` (TestEmbeddingService) confirm 384-dim output, normalization, and find_similar top-k.

### 2.2 Brain Service Embed RPC (`brain_service/server.py`)

| Item | Status |
|------|--------|
| Proto | `Embed(EmbedRequest) returns (EmbedResponse)` with `repeated float embedding` |
| Implementation | Calls `app.knowledge.embedding_service.get_embedding_engine().embed([request.text])[0]` |
| Import | `from app.knowledge.embedding_service import get_embedding_engine` — valid when brain_service runs with `backend` on `sys.path` (server adds `BACKEND_DIR`). **Risk**: brain_service venv may not have `sentence_transformers`; then fallback runs (or error if import fails). |
| Backend usage | **None**. `brain_client.py` has no `embed()` or Embed RPC call; only `infer()` (InferCandidateContext) and optionally CriticPostmortem. |

**Conclusion**: Embed RPC is **implemented** but **dormant** — no caller from backend or frontend.

### 2.3 Knowledge Graph (`backend/app/knowledge/knowledge_graph.py`)

| Item | Status |
|------|--------|
| Edge building | `build_edges()` uses heuristic_engine + memory_bank; pairs with **≥ MIN_CO_OCCURRENCE (5)** get edges |
| Relationships | confirms (win_rate > 0.65), contradicts (< 0.35), amplifies (avg_r > 1.5) |
| Persistence | DuckDB `knowledge_edges` via `duckdb_store.get_thread_cursor()` |
| Consumers | **runner.py**: builds `blackboard.knowledge_context` (active_heuristics, confirmations, contradictions) and passes to DecisionPacket.semantic_context. **outcome_tracker.py**: every 10 resolved trades calls `kg.build_edges()`. **No agent** reads `knowledge_context` to change its vote (hypothesis_agent does not inject it into the LLM). |

**Conclusion**: Edges are built and loaded; context is attached to the blackboard but **not used for reasoning** by any agent.

### 2.4 Heuristic Engine (`backend/app/knowledge/heuristic_engine.py`)

| Item | Status |
|------|--------|
| MIN_SAMPLE | 25 |
| MIN_WIN_RATE | 0.55 |
| CONFIDENCE_THRESHOLD | 0.65 (Bayesian) |
| Data source | memory_bank._load_from_store(agent_name, limit=1000) |
| Output | New/updated Heuristic objects persisted to DuckDB `heuristics` |
| API exposure | **None**. No REST endpoint returns heuristics; cognitive.py exposes cognitive_telemetry, not heuristics. |
| Consumers | runner (get_active_heuristics for knowledge_context), outcome_tracker (extract_heuristics + build_edges), knowledge_graph.build_edges (get_active_heuristics). |

**Conclusion**: Pattern extraction works; output is **not exposed via API** and is only used inside the knowledge/runner/outcome_tracker pipeline.

### 2.5 Memory Bank (`backend/app/knowledge/memory_bank.py`)

| Item | Status |
|------|--------|
| Storage | DuckDB `agent_memories` (with embedding FLOAT[]); in-memory cache per agent |
| store_observation | Called from runner after council (batch embed + store per vote) |
| update_outcome | Called from outcome_tracker on trade resolution (trade_id, r_multiple, was_correct) |
| recall_similar | Embedding-based: query embed + cosine similarity over corpus. Used by **runner** to fill `blackboard.knowledge_context["relevant_memories"]` (top_k=5). |
| Relationship to DuckDB trade_outcomes | **Different**. `trade_outcomes` = ingested order/fill P&L (data_ingestion, trade_stats_service). `agent_memories` = per-agent observations + embeddings, outcomes updated by outcome_tracker. Same resolution event updates both feedback_loop (weight_learner) and memory_bank; **two sources of truth** for “trade outcome” (one for weights, one for memory). |

**Conclusion**: Memory bank is **wired** for storage and recall in runner; **not used** by layered_memory_agent (which uses duckdb_service queries that don’t exist, so in-memory only).

### 2.6 Layered Memory Agent (`backend/app/council/agents/layered_memory_agent.py`)

| Item | Status |
|------|--------|
| Data source | **DuckDB**: `query_recent_trades`, `query_sector_patterns`, `query_regime_transitions`, `query_agent_performance` from `app.services.duckdb_service` |
| Problem | **These functions are not defined** in the codebase (grep returns no definitions). So every call raises and the agent falls back to in-memory `_memory_store` (short_term, mid_term, long_term, reflection). |
| knowledge_graph | **Not used**. |
| embedding_service / memory_bank.recall_similar | **Not used**. |

**Conclusion**: Layered memory uses **simple lookups only** (and currently only in-memory); **no semantic memory** or knowledge graph.

### 2.7 RAG / Vector Search

| Item | Status |
|------|--------|
| Vector store | Embeddings stored in DuckDB `agent_memories.embedding` (FLOAT[]). No dedicated vector index (e.g. HNSW). |
| Similarity search | `memory_bank.recall_similar()` does in-memory/corpus cosine similarity via `embedding_engine.find_similar()`. |
| RAG pipeline | **None**. No flow: query → embed → vector search → retrieve → augment LLM prompt. Hypothesis agent gets **no** retrieved memories or heuristics in its prompt. |

---

## 3. Deliverables Completed

### 3.1 Tests (`backend/tests/test_knowledge_embedding_system.py`)

- **Embedding**: 384-dim output, embed_single, batch normalization, find_similar top-k, fallback when sentence_transformers unavailable.
- **Knowledge graph**: MIN_CO_OCCURRENCE=5, get_confirming_patterns, get_contradictions, build_edges with mocked heuristics/memory (min 5 co-occurrences).
- **Heuristic engine**: MIN_SAMPLE=25, MIN_WIN_RATE=0.55, CONFIDENCE_THRESHOLD=0.65; extract_heuristics with insufficient vs sufficient memories; get_applicable_heuristics filter.

### 3.2 Embedding Fallback Fix (`backend/app/knowledge/embedding_service.py`)

- Fallback now produces **384 dimensions** (byte_len = dim*4, extend hash to byte_len) and handles zero-norm (unit vector on first element).

---

## 4. Wiring Plan: embedding_service → brain gRPC → hypothesis_agent → RAG

### 4.1 Target Architecture

```
1. Backend (PC1) / Brain (PC2)
   - Option A: hypothesis_agent calls brain_client.embed(text) for query embedding; backend uses local get_embedding_engine() for corpus (agent_memories).
   - Option B: hypothesis_agent sends (query_text, top_k) to brain; brain runs embed(query) + vector search over a synced/cached corpus and returns top-k memory snippets.
   - Recommendation: **Option A** — backend already has memory_bank and embeddings; only query embedding can go to brain if we want GPU on PC2. Otherwise keep everything on backend with get_embedding_engine().

2. RAG flow for hypothesis_agent
   - Before calling client.infer():
     a. Build query string from symbol, regime, features, and optional blackboard summary.
     b. Call memory_bank.recall_similar(agent_name="hypothesis" or "council", current_context=..., regime=regime, top_k=5).
     c. Optionally add blackboard.knowledge_context["active_heuristics"] and ["relevant_memories"] to the context string.
     d. Pass augmented context (e.g. "Relevant past cases: ..." + "Active heuristics: ...") into the existing brain_context JSON so the LLM sees it.

3. Brain Embed RPC
   - Add brain_client.embed(text: str) -> List[float] for optional use when backend wants to offload embedding to PC2. Not required if backend does all embedding locally.

4. Heuristic / pattern API
   - Expose GET /api/v1/cognitive/heuristics or /knowledge/heuristics returning get_heuristic_engine().get_active_heuristics() (and optionally get_applicable_heuristics(agent, regime, direction)) for Research Dashboard and debugging.
```

### 4.2 Implementation Order

1. **RAG in hypothesis_agent**  
   In `hypothesis_agent.evaluate()`, after building `brain_context`, call `memory_bank.recall_similar(...)` (and optionally read `blackboard.knowledge_context`); append "Relevant past cases" and "Active heuristics" to the context string passed to `client.infer()`.

2. **Layered memory + memory_bank**  
   In `layered_memory_agent.evaluate()`, add a path that calls `memory_bank.recall_similar(agent_name=NAME, current_context=..., regime=regime, top_k=10)` and merges results into short_term / pattern_signal or blackboard so that semantic recall influences the vote.

3. **DuckDB helpers for layered_memory_agent**  
   Implement `query_recent_trades`, `query_sector_patterns`, `query_regime_transitions`, `query_agent_performance` in `duckdb_service` (or equivalent) so layered_memory_agent can use DB-backed history when available.

4. **Optional: brain Embed**  
   Implement `brain_client.embed()` and use it in backend only if we want query embedding on PC2; otherwise keep using backend `get_embedding_engine()` for both query and corpus.

5. **Heuristics API**  
   New route (e.g. under cognitive or knowledge) to return active/applicable heuristics for dashboard and tooling.

---

## 5. Council Agents That Would Benefit From Semantic Memory Lookup

| Agent | Benefit |
|-------|--------|
| **hypothesis_agent** | RAG over past council outcomes and similar market contexts; “in similar regimes we did X and outcome was Y.” |
| **layered_memory_agent** | Replace or complement missing duckdb_service with `memory_bank.recall_similar` and optionally knowledge_graph get_confirming_patterns / get_contradictions. |
| **strategy_agent** | Feed applicable heuristics and confirming/contradicting edges so strategy can lean on learned patterns. |
| **risk_agent** | Similar past contexts where risk was high or stops were hit; improve veto reasoning. |
| **critic_agent** | Retrieve similar past decisions and outcomes for post-decision critique. |
| **regime_agent** | Optional: similar past regime transitions and outcomes (if stored in agent_memories or a dedicated store). |

**Highest impact**: **hypothesis_agent** (RAG) and **layered_memory_agent** (semantic recall + graph confirmations/contradictions).

---

## 6. References

- `backend/app/knowledge/embedding_service.py` — EmbeddingEngine, 384-dim, fallback
- `backend/app/knowledge/knowledge_graph.py` — MIN_CO_OCCURRENCE=5, build_edges, get_confirming_patterns
- `backend/app/knowledge/heuristic_engine.py` — MIN_SAMPLE=25, MIN_WIN_RATE=0.55, extract_heuristics
- `backend/app/knowledge/memory_bank.py` — store_observation, recall_similar, update_outcome
- `brain_service/server.py` — Embed RPC (implemented, unused)
- `backend/app/services/brain_client.py` — no Embed call
- `backend/app/council/runner.py` — knowledge_context, relevant_memories, store agent memories
- `backend/app/council/agents/hypothesis_agent.py` — no knowledge_context or RAG in prompt
- `backend/app/council/agents/layered_memory_agent.py` — duckdb_service (missing) + in-memory; no memory_bank/knowledge_graph
- `backend/tests/test_knowledge_embedding_system.py` — new tests for embedding, knowledge graph, heuristic engine
