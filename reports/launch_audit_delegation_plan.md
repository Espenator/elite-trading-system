# Launch Audit — Delegation Plan

**Audit**: Production launch (Alpaca real-money trading)  
**Date**: 2026-03-12

## Specialist Agent → Checklist Mapping

| Specialist | Owns | Checklist IDs |
|------------|------|----------------|
| **Safety Systems Auditor** | Circuit breaker, regime gate, paper/live safety, TRADING_MODE default, live credential check | PF-01, PF-02, PF-03, PF-04, PF-05 |
| **Trading Mode + Security Auditor** | Bearer auth fail-closed, require_auth on state-changing routes, no hardcoded secrets | BE-01, BE-02, BE-03 |
| **Data Integrity Auditor** | .env gitignore, config validation at startup | BE-02, BE-03, PF-02 |
| **Backend Reliability Auditor** | Pytest critical + full suite, startup flow | BE-04, BE-05 |
| **Frontend QA Auditor** | E2E audit tests, CORS, agents payload contract | FE-01, FE-02 |
| **End-to-End Trading Pipeline Auditor** | Council→OrderExecutor, gate logic, paper-only tests | E2E-01, E2E-02, E2E-03 |
| **Deployment + Monitoring Auditor** | .env.example, emergency endpoints auth | DP-01, DP-02 |

## Status Format (Required for All Specialists)

- **✅ PASS** — verified with evidence (command output, log, code ref with file:line, API response, test output)
- **❌ FAIL** — broken; include suggested fix
- **⚠️ NEEDS ATTENTION** — works but concern remains
- **⏭️ SKIPPED** — blocked; explain exactly what blocked verification

## Evidence Requirements

- **Code**: exact file path + line numbers
- **API**: curl/httpie output or test logs
- **Config/secrets**: grep/ripgrep results
- **Frontend**: screenshots or saved console/network logs (when applicable)
- **Order flow**: paper-trading-only execution for tests

## Deliverables (Consolidated)

1. **reports/launch_audit_master.md** — full checklist with evidence (this audit)
2. **reports/launch_audit_summary.json** — machine-readable scorecard
3. **reports/launch_audit_delegation_plan.md** — this file
4. **Unresolved dependencies** — listed in master (startup timing, real Alpaca, frontend screenshots)
