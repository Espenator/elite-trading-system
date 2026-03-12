# Git push/pull setup (Cursor + CLI)

So that **git push** and **git pull** work from both the terminal and Cursor (and any agent using this repo), configure GitHub auth once using one of these methods.

## If push already works (Windows Credential Manager)

If you previously fixed 403 by clearing the old GitHub credential and then running `git push` and entering your **GitHub username** and **classic PAT** as password when prompted, Git stored that in **Windows Credential Manager**. In that case:

- **CLI / Cursor terminal:** `git push` and `git pull` from the repo directory should already work (same user, same stored credential).
- **Agent/automation:** To let scripts or the agent push without relying on Credential Manager, put the same PAT in `.github-token` or `GITHUB_TOKEN` and run `.\scripts\set-git-remote-from-token.ps1` once; that embeds the token in the remote URL for this repo so no prompt is needed.

One-liner that was used successfully in a past session (clear cached credential then push; you enter username + PAT when prompted):

```powershell
cmdkey /delete:git:https://github.com 2>$null; Set-Location "c:\Users\Espen\Dev\elite-trading-system"; git push origin main
```

## Option A: Token in a file (recommended for Cursor/agent)

1. Create a [GitHub Personal Access Token](https://github.com/settings/tokens) (classic) with **repo** scope.
2. In the **repo root**, create a file named `.github-token` containing only the token (one line, no quotes).
   - This file is in `.gitignore` and will never be committed.
3. Run:
   ```powershell
   .\scripts\set-git-remote-from-token.ps1
   ```
4. After that, `git push` and `git pull` work for both you and Cursor.

If the repo is under `Dev`, run from that path, e.g.:
```powershell
cd C:\Users\Espen\Dev\elite-trading-system
.\scripts\set-git-remote-from-token.ps1
```

## Option B: Token in environment

1. Set `GITHUB_TOKEN` to your PAT (e.g. in root `.env` or your shell profile).
2. Run:
   ```powershell
   .\scripts\set-git-remote-from-token.ps1
   ```
   The script reads `$env:GITHUB_TOKEN` and configures the remote.

## Option C: Interactive (fix-git-auth.ps1)

Run `.\scripts\fix-git-auth.ps1` and follow the prompts to paste your token or set up SSH. If you choose HTTPS + PAT, you can paste the token and it is written into the remote URL (local only), or you can skip and use Credential Manager so Git prompts on next push and stores it in Windows.

---

## Where tokens live

| Place              | Purpose                          | Committed? |
|--------------------|----------------------------------|------------|
| `.github-token`    | PAT for git push/pull (this repo)| No (.gitignore) |
| `.env` / `GITHUB_TOKEN` | Same; script reads it         | No (.env* gitignored) |
| `GIST_TOKEN` in `.env.example` | OpenClaw gist sync (gist scope) | Example only |

Use a **repo**-scope PAT for push/pull. You can use the same PAT for `GIST_TOKEN` if it has both **repo** and **gist** scopes.

## Verifying

From repo root:
```powershell
git fetch origin
git push origin main
```
If both succeed, setup is correct.
