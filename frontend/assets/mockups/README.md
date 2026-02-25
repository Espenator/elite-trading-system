# UI Mockups - Embodier Trader

## ML Brain & Flywheel Page

**File:** `Embodier_Trader_ML_Brain_Flywheel.png`

**Resolution:** 7680 x 4320 (4K)

**Source:** Generated via Perplexity AI Code Interpreter

**Perplexity Thread:** https://www.perplexity.ai/search/i-approve-all-charts-please-en-q897jXhhRGSDo13toic7NQ

**Local Desktop Copy:** `C:\Users\espen\Desktop\Embodier_Trader_ML_Brain_Flywheel.png`

### Description

Production-ready 4K mockup of the ML Brain & Flywheel dashboard page showing:

- Model Performance Tracking chart (252-day walk-forward accuracy)
- Stage 4: ML Probability Ranking table
- Deployed Inference Fleet (TimescaleDB Connected)
- Flywheel Learning Log (Trade Outcomes)

### Download Instructions

To download the PNG from the Perplexity thread:

1. Open the Perplexity thread link above
2. Scroll to the "ML Brain & Flywheel" section
3. Right-click the mockup image > "Save image as..."
4. Save as `Embodier_Trader_ML_Brain_Flywheel.png`

Or use PowerShell to download directly (run from repo root):

```powershell
# Download from Perplexity S3 (get fresh URL from the thread)
# Then copy to repo and commit:
Copy-Item "$env:USERPROFILE\Downloads\*.png" "frontend\assets\mockups\Embodier_Trader_ML_Brain_Flywheel.png"
git add frontend/assets/mockups/Embodier_Trader_ML_Brain_Flywheel.png
git commit -m "assets: Add ML Brain & Flywheel mockup PNG"
git push
```

### For Oleh

The PNG mockup is the design reference for the `MLBrainFlywheel.jsx` component in `frontend-v2/src/pages/`.

**Related Files:**
| File | Path | Description |
| --- | --- | --- |
| `MLBrainFlywheel.jsx` | `frontend-v2/src/pages/MLBrainFlywheel.jsx` | Production-ready React component |
| `MLBrainAndFlywheel.jsx` | `frontend/components/MLBrainAndFlywheel.jsx` | Original component (legacy path) |
| `ml_api.py` | `core/api/ml_api.py` | FastAPI backend endpoints |

**Wiring checklist:**
- [ ] Register ML router in `main.py`
- [ ] Add `/ml-brain` route in `App.jsx`
- [ ] Add sidebar nav link with brain icon
- [ ] Install Recharts: `npm install recharts`
- [ ] Replace stub data with real TimescaleDB queries
