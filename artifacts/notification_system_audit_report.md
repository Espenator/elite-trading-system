# Notification System Audit Report

**Date:** March 13, 2026  
**Scope:** Slack token rotation, message deduplication, TradingView webhook validation, Telegram/Resend wiring, graceful degradation.

---

## 1. Slack token usage and startup validation

**Finding:** `SLACK_BOT_TOKEN` is **not** validated on startup.

- **Config:** `backend/app/core/config.py` defines `SLACK_BOT_TOKEN: str = ""`. No startup check.
- **Live-trading guard:** Only when `TRADING_MODE=live` does the app validate `ALPACA_*` and `API_AUTH_TOKEN`. Slack is optional and left unvalidated.
- **Usage:** `SlackNotificationService` reads `settings.SLACK_BOT_TOKEN` in `__init__`; if empty, `_is_configured()` is False and all sends are no-op (graceful degradation).

**Recommendation:** Optionally add a startup probe (e.g. `auth.test`) when `SLACK_BOT_TOKEN` is set, and log a warning if the token is invalid or expired. Do not fail startup.

---

## 2. Token refresh mechanism

**Finding:** There is **no** auto-refresh or expiry detection for Slack bot tokens.

- **Docstring:** `slack_notification_service.py` states: *"Tokens are short-lived (12h) and must be refreshed via Slack API console."*
- **Behavior:** Token is read once at service init. No background refresh, no OAuth2 refresh flow, no `invalid_auth` handling beyond returning `False` and logging.

**Auto-refresh strategy options:**

| Option | Description | Effort |
|--------|-------------|--------|
| **A. Manual refresh** | Keep current behavior; document 12h refresh in runbook; optional startup `auth.test` to warn. | Low |
| **B. Slack OAuth2 (recommended for 24/7)** | Use Bot token from OAuth2 app with refresh token; store `refresh_token` in env or secrets; background job or on-demand refresh when `invalid_auth` is seen. Requires Slack app to be OAuth2-enabled and user to install once. | Medium |
| **C. Service account / legacy token** | Use a token that does not expire (legacy; Slack discourages). | Not recommended |
| **D. On-demand refresh on 401** | When `chat.postMessage` returns `invalid_auth`, call a small refresh routine (e.g. serverless or cron that writes new token to env/secret and signals app to reload). App does not implement refresh itself. | Medium |

**Recommendation for auto-refresh:** Implement **B** (OAuth2 refresh) if 24/7 unattended operation is required; otherwise **A** plus a scheduled reminder (e.g. 11h after start) to refresh the token. No in-process refresh is implemented today.

---

## 3. Message deduplication

**Finding:** There is **no** deduplication for signal or council verdict notifications to Slack.

- **SlackNotificationService:** `send_signal`, `send_council_verdict`, `send_trade_execution` have no per-message or per-symbol deduplication. Only a **rate limit** of 1 message per second per channel (`_RATE_LIMIT_SEC = 1.0`). Same symbol can still flood #trade-alerts if signals are >1s apart.
- **SlackAlerter:** Uses throttling by `hash(title:source)` with `SLACK_ALERT_THROTTLE_SEC` (default 300s). That applies to health/alerts, not to trading signals or verdicts.

**Test coverage:** `tests/test_notification_system_audit.py::test_slack_no_deduplication_same_signal_sent_twice` confirms that two identical signals (same symbol/direction, >1s apart) result in two Slack API calls.

**Recommendation:** Add a short deduplication window (e.g. 5 minutes) for `send_signal` and `send_council_verdict` by key `(channel, symbol, direction)`. Skip send if the same key was sent within the window; optionally extend to include score/confidence for finer control.

---

## 4. Rate limiting

**Finding:** Rate limiting **is** enforced: 1 message per second per channel.

- **Implementation:** `slack_notification_service.py`: `_last_send[channel]` and `_RATE_LIMIT_SEC = 1.0`. If `(now - last) < 1.0`, `_post_message` returns `False` and does not call the API.
- **Test:** `test_slack_rate_limit_one_per_second_per_channel` verifies that a second message to the same channel within the same second is dropped and only one `post` is made.

---

## 5. TradingView webhook signature/secret validation

**Finding:** Validation **is** implemented via a shared **payload secret**, not HTTP signature headers.

- **Mechanism:** `backend/app/api/v1/webhooks.py` uses `_validate_tradingview_secret(payload.secret, configured_secret)`. If `TRADINGVIEW_WEBHOOK_SECRET` is set, the payload must include a matching `secret`; otherwise 401.
- **Not implemented:** HMAC of request body (e.g. `X-Signature` header). TradingView may support that; current code only checks a secret field in the JSON body.

**Tests:**  
- `test_tradingview_webhook_invalid_secret_returns_401` and `test_tradingview_webhook_valid_secret_accepts` in `test_tradingview_webhook.py`.  
- Audit tests in `test_notification_system_audit.py`: missing secret → 401, wrong secret → 401, no secret configured → accept without secret.

**Recommendation:** If TradingView supports request signing (e.g. HMAC-SHA256 of body), add header-based verification in addition to (or instead of) the payload secret for stronger security.

---

## 6. Telegram integration

**Finding:** **Config only** — not wired for sending.

- **Config:** `config.py` has `TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHAT_ID`; `settings_service.py` maps them for the UI.
- **Usage:** No service or API sends Telegram messages. No `telegram` or `TELEGRAM` usage in notification flows. `test_agent7_websocket_telegram_frontend.py` has a placeholder `test_telegram_notification_code_path_exists` for a future path.

**Conclusion:** Telegram is configured but not used for notifications. Add a small `telegram_notification_service` and wire it to the same events as Slack (e.g. verdicts, alerts) if Telegram delivery is required.

---

## 7. Resend (email) integration

**Finding:** **Wired** for test and alert emails.

- **Config:** `RESEND_API_KEY`, `RESEND_FROM_EMAIL`, `RESEND_ALERT_TO_EMAIL` in `config.py`.
- **Usage:** `backend/app/api/v1/alerts.py`: `POST /api/v1/alerts/test-email` uses `_send_email_via_resend()` with `settings.RESEND_API_KEY` and `RESEND_ALERT_TO_EMAIL`. Settings validation supports `resend` in `validate_api_key` (e.g. test-connection). No evidence of automatic risk/drawdown emails in this audit; the hook exists for test and future alert routing.

**Conclusion:** Resend is integrated for test email and is the intended channel for email alerts; ensure risk/drawdown alerts call the same `_send_email_via_resend` path where applicable.

---

## 8. Graceful degradation when Slack token expires

**Finding:** Failures are handled without raising; messages are **silently dropped**.

- **Behavior:** In `_post_message`, any exception is caught and logged with `logger.warning`; Slack API responses with `ok: false` (e.g. `invalid_auth`) cause a log and `return False`. Callers (e.g. `_bridge_council_to_slack`, `_slack_alert` in order_executor) do not retry or escalate; they only log on failure.
- **Test:** `test_slack_token_expiry_returns_false_does_not_raise` and `test_slack_http_401_returns_false_does_not_raise` confirm that 401/invalid_auth results in `False` and no exception.

**Recommendation:** Consider a circuit-breaker or health flag: after N consecutive `invalid_auth` (or 401), set “Slack unavailable” and optionally send one alert via an alternate channel (e.g. Resend or log to a file). That avoids log spam while making expiry visible.

---

## Summary table

| Item | Status | Notes |
|------|--------|------|
| SLACK_BOT_TOKEN validated on startup | No | Optional; no check |
| Token refresh / expiry detection | No | Manual refresh only |
| Message deduplication (signals/verdicts) | No | Rate limit 1/sec only |
| Rate limit 1 msg/sec per channel | Yes | Enforced and tested |
| TradingView webhook secret validation | Yes | Payload secret; no HTTP signature |
| Telegram wired for sending | No | Config only |
| Resend wired | Yes | Test email + validation |
| Graceful degradation on Slack 401 | Yes | Returns False; no raise; silent drop |

---

## Test file

All audit behaviors above are covered by:

- **`backend/tests/test_notification_system_audit.py`**
  - Slack token expiry (invalid_auth and HTTP 401)
  - No deduplication (same signal twice → two API calls)
  - Rate limit 1 msg/sec per channel
  - TradingView: missing/wrong secret → 401; no secret configured → accept

Run: `cd backend && python -m pytest tests/test_notification_system_audit.py -v`
