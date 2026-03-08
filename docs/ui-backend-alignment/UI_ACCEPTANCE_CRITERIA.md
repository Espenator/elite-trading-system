# UI Acceptance Criteria

## Non-negotiable truth criteria
- No visible UI element may present fabricated market, portfolio, risk, model, sentiment, agent, or system data.
- No button, toggle, dropdown, slider, tab action, or destructive control may remain interactive unless it triggers a real backend mutation or a clearly labeled blocked flow.
- No status badge may claim Connected / Healthy / Active / Running / Ready / Synced / Live unless backed by a verified backend or websocket state.
- No chart or table may render synthetic rows/series to fill space.
- If backend has no data, the UI must say so explicitly.
- If backend capability is missing, the UI must remove the control or label it as unavailable; it must not simulate the capability.

## Visibility criteria
- Every real-time page shows freshness (`last updated`, `stale`, or disconnected state).
- Every operator-critical panel shows its backend source or service context clearly enough for auditability.
- Errors, empty states, and partial-data states are visually distinct from healthy states.
- Admin-gated actions clearly communicate auth requirements and backend failure messages.

## Control criteria
- Emergency controls are wired to the real backend and confirm before execution.
- Existing backend control surfaces are discoverable from the most relevant page.
- Read-only surfaces are only read-only when the backend truly lacks a safe mutation endpoint.

## Visual criteria
- Styling follows the repo design language:
  - dark-first operator console
  - dense but legible cards/tables
  - Inter / JetBrains Mono style hierarchy where already established
  - restrained cyan/green/amber/red status semantics
- Removal of fake content must not be replaced with decorative filler; zero-state copy is preferred.

## Validation criteria
A page is only accepted when all of the following are true:
1. Every visible data block is mapped to a verified backend route, websocket channel, config source, or truthful client transformation.
2. Loading, empty, error, stale, and disconnected states are handled.
3. Any visible action path performs a real backend request or is clearly blocked with rationale.
4. The page builds cleanly with `npm run build`.
5. Relevant existing tests still pass (`python -m pytest tests/ -q` for this repo baseline).
6. Manual review confirms no fake/demo/dead UI remains on that page.

## Current branch signoff notes
- Shared footer fake market defaults: removed.
- Agent Command Center fake status/emergency-stop/message-bus/HITL/ELO fallbacks: removed or wired.
- Remaining repo still requires page-by-page completion per `UI_IMPLEMENTATION_PLAN.md` before full signoff.
