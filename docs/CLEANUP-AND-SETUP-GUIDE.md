# Embodier Trader — PC Organization Guide
**Last updated: March 2, 2026**

## OneDrive Folder Structure (Synced to Both PCs)

```
OneDrive/
├── Embodier-Trader/        ← All trading system work
│   ├── brain/              ← AI context, instructions, brain.db
│   ├── mockups/            ← ALL UI mockup PNGs (single source of truth)
│   ├── research/           ← Trading research, strategies, market studies
│   ├── prompts/            ← AI prompts (Comet, Claude, trading assistant)
│   ├── backtest-results/   ← Backtest outputs
│   ├── docs/               ← Dev guides, system design, task notes
│   ├── pine-scripts/       ← TradingView scripts
│   └── logs/               ← System logs
│
├── Credentials/            ← ALL secrets consolidated
│   ├── env-configs/        ← .env files
│   ├── gcp-keys/           ← GCP service account JSONs
│   └── api-tokens/         ← LinkedIn, OAuth, API keys, etc.
│
├── Business/               ← Non-trading Embodier business docs
│   ├── plans/              ← Business plans, proposals
│   ├── legal/              ← Legal docs, contracts
│   └── marketing/          ← Sales funnels, video promotion
│
├── Archive/                ← Old stuff, kept but out of the way
│   ├── old-projects/       ← gemini-signal-app, embodier-soul-test, etc.
│   ├── old-trading-scripts/← Pre-repo Python scripts
│   └── old-docs/           ← Outdated business plans
│
├── Documents/              ← Standard Windows docs
├── Desktop/                ← SHORTCUTS ONLY
├── Pictures/
├── Music/
└── Videos/
```

## Git Repo Setup (BOTH PCs — NOT in OneDrive!)

The elite-trading-system repo MUST be cloned locally, NOT inside OneDrive.
OneDrive corrupts .git folders during sync.

### Clone on each PC:

```powershell
cd C:\Users\Espen
git clone https://github.com/Espenator/elite-trading-system.git
```

Repo path on both PCs: `C:\Users\Espen\elite-trading-system\`

## ESPENMAIN Cleanup Checklist

Since ESPENMAIN already has the repo cloned, the main task is:

1. **Delete scattered files on ESPENMAIN Desktop/Documents**
   - Any .py/.jsx/.md files that are NOT in the git repo → delete (they're now in OneDrive)
   - Any mockup PNGs → already in OneDrive/Embodier-Trader/mockups/
   - Any .exe installers → delete
   - Any credential files → already in OneDrive/Credentials/

2. **Verify the repo on ESPENMAIN is up to date**
   ```powershell
   cd C:\Users\Espen\elite-trading-system
   git pull origin main
   ```

3. **Clone repo on Profit Trader**
   ```powershell
   cd C:\Users\Espen
   git clone https://github.com/Espenator/elite-trading-system.git
   ```

4. **Verify OneDrive sync** — open OneDrive on both PCs and confirm
   the Embodier-Trader/ folder appears with all contents.

## Security Notes

- **NEVER put .env or credential files in the git repo**
- **All API keys are now in OneDrive/Credentials/** — consider
  migrating to a proper secrets manager (1Password, Bitwarden)
- **5 GCP service account keys found** — review if all are still active,
  revoke unused ones in Google Cloud Console
- **Multiple OAuth JSONs** — likely duplicates, audit and clean up

## What Was Deleted (March 2, 2026)

- DiscordSetup.exe (107MB)
- GoogleDriveSetup.exe x2 (640MB total)
- Duplicate mockup PNGs
- Empty files (cd, dir, python — from terminal accidents)
- ge sheet.exe
- __pycache__ directories

## What Was Archived

- gemini-signal-app (old project)
- embodier-soul-test (old project)
- GeminSignal App (old project)
- Web app (old project)
- EmbodierMobile (Unreal project)
- Embodier Projects/AppDashboard (Unreal project)
- PureWeb_Test (old project)
- Sara.zip (4.4GB) + environment images
- 12 pre-repo Python trading scripts
- August 2025 Embodier Development Folder
- Microsoft Copilot/Teams Chat Files
- Desktop "clean up desktop" folder
