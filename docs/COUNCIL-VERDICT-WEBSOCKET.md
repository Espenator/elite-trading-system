# Council Verdict API & WebSocket

Trigger a council run via REST and receive real-time verdict events on the WebSocket channel `council_verdict`. Same compact payload shape for normal and halted decisions.

## API: Trigger council evaluation

**POST** `/api/v1/council/evaluate` (requires `Authorization: Bearer <API_AUTH_TOKEN>`)

Request body:

```json
{
  "symbol": "AAPL",
  "timeframe": "1d",
  "features": null,
  "context": null
}
```

- **symbol** (required): Ticker symbol.
- **timeframe**: Optional; default `"1d"`.
- **features** / **context**: Optional; passed to the council runner.

Response: Full `DecisionPacket` (200), or 504 on timeout, 500 on error. On completion (success, timeout, or error), a compact verdict is broadcast on the WebSocket channel `council_verdict` so clients get a consistent event stream.

Rate limit: 10 evaluations per minute (429 when exceeded).

## WebSocket: Subscribe to verdicts

Connect to the app WebSocket and subscribe to channel **`council_verdict`**. Each message has the canonical envelope `{ "channel", "type", "data", "ts" }` with `type: "verdict"` and `data` as the compact payload below.

## Compact verdict payload (normal decision)

```json
{
  "councildecisionid": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "symbol": "AAPL",
  "direction": "buy",
  "confidence": 0.72,
  "vote_summary": {
    "buy": 18,
    "sell": 5,
    "hold": 12
  },
  "halt_reason": null,
  "timestamp": "2026-03-12T16:00:00Z",
  "execution_ready": true
}
```

## Compact verdict payload (halted)

When the council is vetoed, held, times out, or errors, the same shape is used with `halt_reason` set and `execution_ready: false`:

```json
{
  "councildecisionid": "",
  "symbol": "GOOG",
  "direction": "hold",
  "confidence": 0.0,
  "vote_summary": {
    "buy": 0,
    "sell": 0,
    "hold": 0
  },
  "halt_reason": "timeout",
  "timestamp": "2026-03-12T16:05:00Z",
  "execution_ready": false
}
```

**halt_reason** values: `"vetoed"`, `"hold"`, `"timeout"`, `"error"`, or `null` when the decision completed normally.

**vote_summary** may include `"vetoed_by": ["risk", "execution"]` when one or more veto agents vetoed.

## Pipeline behavior

- **CouncilGate** (signal-driven): Publishes `council.verdict` for every outcome (approved, vetoed, hold, timeout). The main app bridge converts each to the compact payload and broadcasts on `council_verdict`.
- **POST /council/evaluate**: After each run (success or exception), a compact verdict is broadcast. WebSocket broadcast is best-effort; failures do not affect the HTTP response or the trading pipeline.

## Frontend subscription example

```javascript
// After WS connect and optional token
ws.send(JSON.stringify({ action: "subscribe", channel: "council_verdict" }));

// Incoming message
// { channel: "council_verdict", type: "verdict", data: { councildecisionid, symbol, direction, ... }, ts: 1710244800 }
```
