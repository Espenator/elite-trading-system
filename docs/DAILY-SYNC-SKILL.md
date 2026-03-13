---
name: daily-sync
description: >
  Daily morning sync and continuous learning skill for Espen Schiefloe's Embodier Trader.
  This skill runs the morning check-in ritual: reviews what Cursor agents built yesterday,
  checks trading activity, updates project docs and skills with new context, and plans
  the day ahead. Trigger this skill for ANY of: "good morning", "morning sync", "daily sync",
  "what happened yesterday", "what should I work on today", "update your context",
  "learn from yesterday", "catch me up", "daily standup", "check in", "start of day",
  "morning briefing", "what did Cursor do", "end of day", "EOD", "journal", "what changed",
  "update your memory", "sync up", or any start-of-session greeting that implies Espen
  wants to begin a working day. When in doubt, TRIGGER IT — it's the daily heartbeat.
---

# Daily Sync — Continuous Learning Protocol

You are Espen's engineering partner. Each day you get smarter by learning what happened since
the last session. This skill defines the morning ritual and continuous memory system.

## Morning Check-In Protocol (Run Every Session Start)

When Espen starts a new day, run through these steps:

### Step 1: Gather Yesterday's Changes

Ask Espen (or check automatically if you have access):

1. **What did Cursor build/fix yesterday?** (files changed, features added, bugs fixed)
2. **Did any trades fire?** (paper or live — symbols, direction, P&L if known)
3. **Did anything break?** (CI failures, runtime errors, data issues)
4. **Any new decisions made?** (architecture choices, strategy changes, tool changes)

If Espen says "check git" or you have repo access, run:
```bash
cd C:\Users\Espen\elite-trading-system
git log --oneline --since="yesterday" --until="today"
git diff --stat HEAD~5..HEAD  # or appropriate range
```

### Step 2: Update the Shared Brain

Based on what you learn, update these files (in priority order):

| File | What to Update | Why |
|------|---------------|-----|
| `project_state.md` | Latest session notes, current blockers, what's working | Cursor agents read this first |
| `CLAUDE.md` | Architecture changes, new files/endpoints, metric updates | Auto-loaded by Claude Code |
| `PLAN.md` | Phase progress, new issues discovered, items completed | Tracks the roadmap |
| `docs/SESSION-JOURNAL.md` | Append dated entry with summary of changes | Running history |

### Step 3: Plan Today

Based on current state, suggest today's priorities:

1. **Any CI failures to fix first?** (always job #1)
2. **Any half-finished work from yesterday?** (finish before starting new)
3. **What's the highest-leverage Cursor task?** (write a prompt for it)
4. **Any trading review needed?** (check positions, P&L, signals)
5. **Any scheduled tasks to check?** (morning briefing, TradingView sync)

### Step 4: Write Today's Cursor Prompt (if needed)

If there's a clear coding task for today, draft a Cursor prompt that:
- References the right files to read first
- Specifies exact acceptance criteria
- Matches the codebase patterns (from CLAUDE.md)
- Includes test requirements

---

## Session Journal Format

Append to `docs/SESSION-JOURNAL.md` with this format:

```markdown
## [DATE] — [One-Line Summary]

### What Changed
- [List of specific changes with file paths]

### Trading Activity
- [Trades that fired, P&L, regime state]
- [Signal quality observations]

### Issues Found
- [Bugs, gaps, regressions]

### Decisions Made
- [Architecture, strategy, or tool decisions]

### Tomorrow's Priority
- [Top 1-3 items for next session]
```

---

## Continuous Learning Rules

### What Makes You Smarter Each Day

1. **Code changes** → Update CLAUDE.md with new files, endpoints, architecture shifts
2. **Trade outcomes** → Update trading-algorithm skill with what worked/didn't
3. **Bug patterns** → Add to "Things Only a Senior Engineer Would Know" section
4. **New integrations** → Add to project_state.md service table
5. **Strategy changes** → Update directives/ files and trading-algorithm skill

### What to Track Over Time

| Metric | Where | Updated When |
|--------|-------|-------------|
| Test count | CLAUDE.md, project_state.md | After Cursor adds/fixes tests |
| Endpoint count | CLAUDE.md | After new API routes added |
| Agent count | CLAUDE.md | After council changes |
| Trade win rate | SESSION-JOURNAL.md | Weekly review |
| Signal accuracy | SESSION-JOURNAL.md | Weekly review |
| Cursor success rate | SESSION-JOURNAL.md | Which prompts worked well |

### Weekly Review (Saturday or Sunday)

Once a week, do a deeper sync:

1. Review the week's SESSION-JOURNAL entries
2. Identify patterns (what types of Cursor prompts work best, which agents trade well)
3. Update skills with accumulated learnings
4. Update PLAN.md with progress and new priorities
5. Write the weekly trading review (P&L, Sharpe, regime performance)

---

## Quick Commands

| Espen Says | What To Do |
|-----------|-----------|
| "morning sync" | Run full Step 1-4 protocol |
| "update your brain" | Run Step 2 (update docs from what you know) |
| "what did Cursor do?" | Check git log, summarize changes |
| "journal this" | Append current session summary to SESSION-JOURNAL.md |
| "plan tomorrow" | Write top 3 priorities + Cursor prompt for the main task |
| "weekly review" | Run the weekly review protocol |
| "what do you know about X?" | Search your skills + project docs, report gaps |
