# Cursor Agent — Git Workflow & Branch Rules

**Repo**: `github.com/Espenator/elite-trading-system`
**Owner**: Espenator (Espen Schiefloe)

## CRITICAL: Branch & PR Rules

### Before You Start Coding

1. **ALWAYS create a new feature branch** from `main` before making changes:
   ```bash
   git fetch origin main
   git checkout -b cursor/<short-description> origin/main
   ```
   Branch naming: `cursor/<2-4-word-description>` (e.g. `cursor/health-api-fixes`, `cursor/pc2-gpu-tuning`)

2. **NEVER commit directly to `main`**. All work goes on a feature branch.

3. **NEVER force-push** (`git push --force`). If push is rejected, pull first:
   ```bash
   git pull origin <your-branch> --rebase
   git push -u origin <your-branch>
   ```

### While Coding

4. **Commit early and often** with clear messages:
   ```bash
   git add <specific-files>
   git commit -m "feat(scope): short description [Prompt N]"
   ```
   Prefix: `feat:`, `fix:`, `chore:`, `docs:`, `test:` — include `[Prompt N]` tag if working from a numbered prompt.

5. **Do NOT commit**:
   - `.env` or any file with secrets/API keys
   - `node_modules/`, `__pycache__/`, `venv/`
   - Large binary files

6. **Run tests before pushing**:
   ```bash
   cd backend && python -m pytest --tb=short -q
   cd frontend-v2 && npm run build
   ```

### When Done — Push & Create PR

7. **Push your branch**:
   ```bash
   git push -u origin cursor/<your-branch>
   ```

8. **Create a Pull Request** targeting `main`:
   ```bash
   gh pr create \
     --title "feat: short title of changes" \
     --body "## Summary
   - Bullet point 1
   - Bullet point 2

   ## Test Results
   - Backend: X passed, Y failed
   - Frontend: build clean

   ## Files Changed
   - path/to/file1.py — what changed
   - path/to/file2.jsx — what changed" \
     --base main \
     --head cursor/<your-branch>
   ```

   If `gh` is not available, output this message instead:
   ```
   PR READY — Create manually at:
   https://github.com/Espenator/elite-trading-system/compare/main...<your-branch>

   Title: <your title>
   Summary: <your summary>
   ```

9. **Do NOT merge the PR yourself**. Leave it for human review.

### If Working on an EXISTING Branch

If instructed to work on a specific branch (e.g. `claude/review-repo-docs-LmWVI`):
```bash
git fetch origin <branch>
git checkout <branch>
git pull origin <branch>
# ... make changes ...
git push origin <branch>
```

### Multi-PC Setup Awareness

This repo runs on 2 PCs:
- **PC1 (ESPENMAIN)**: Primary — backend API, frontend, DuckDB, trading
- **PC2 (ProfitTrader)**: Secondary — GPU, brain_service (gRPC), Ollama

If your changes affect PC2 (brain_service/, start-pc2.ps1, .env.pc2), note it in the PR description.

### What NOT to Do

- Do NOT push to `main` directly
- Do NOT delete branches
- Do NOT rebase or amend published commits
- Do NOT create branches without the `cursor/` prefix
- Do NOT merge PRs — leave for human review
- Do NOT modify `.github/workflows/` without explicit permission

### Existing Branch Map (for reference)

| Branch | Owner | Status |
|--------|-------|--------|
| `main` | protected | Production — PR merge only |
| `claude/review-repo-docs-LmWVI` | Claude Code | Active — Prompt 3A/3B work |
| `copilot/review-embodier-trader-logic` | Copilot | Active — trade pipeline audit |
| `copilot/update-project-documents` | Copilot | Docs update |
| `chore/agent-work-review-bundle-2026-03-13` | Cursor | Checkpoint of agent work |
| `feature/trade-execution-full` | Cursor | Trade execution consolidation |

### PR Template

```markdown
## Summary
<!-- 2-4 bullet points of what changed and why -->

## Changes by Area
### Backend
- [ ] path/to/file.py — description

### Frontend
- [ ] path/to/file.jsx — description

### Config / Infra
- [ ] path/to/file — description

## Test Results
- Backend pytest: __ passed / __ failed
- Frontend build: clean / errors
- Affected PCs: PC1 only / PC2 only / Both

## Prompt Reference
<!-- If following a numbered prompt, reference it -->
Prompt 3C / Issue #42 / etc.
```
