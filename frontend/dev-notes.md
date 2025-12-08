# Dev Notes – Zone1 Intelligence Radar (Espen & Comet) – 2025-12-07 19:10

## What was done today

- Fixed missing React imports across components so Vite/React render again.
- Cleaned up zone: **src/components/Zone1_IntelligenceRadar**:
  - **LiveAnalysisHeader.tsx**
    - Now accepts an optional \progress\ prop with defaults (current/total/tier counts).
    - This prevents crashes when no progress data is passed.
    - New CSS file: \LiveAnalysisHeader.css\ created and wired up.
  - **CandidateCard.tsx**
    - Refactored to be defensive around undefined data.
    - Current intention: used by \IntelligenceRadar.tsx\ from real-time "signals" data.
  - **IntelligenceRadar.tsx**
    - Still the main Zone1 container.
    - Tabs: "AI Signals" / "Watchlist", auto-scroll logic for candidates.
    - Uses \useRealtimeSignals()\ hook to fetch signals from backend.

## Current state

- Vite dev server runs on: [**http://localhost:5173/**](http://localhost:5173/)
- Backend (FastAPI) is expected on **localhost:8000** but some frontend pieces still try **localhost:5172**, causing ERR_CONNECTION_REFUSED in Network tab.
- React compile/runtime errors from:
  - Missing LiveAnalysisHeader CSS – **now fixed**.
  - Undefined props in LiveAnalysisHeader/CandidateCard – **now guarded with defaults**.

## TODO for Oleh (next session)

1. **Verify UI rendering**
   - Start frontend: \
pm run dev\ in \rontend\
   - Start backend: \uvicorn main:app --reload --port 8000\ (in backend folder)
   - Open: http://localhost:5173/
   - Check DevTools Console for *new* errors.

2. **Confirm CandidateCard <-> IntelligenceRadar alignment**
   - In \IntelligenceRadar.tsx\, mapping should be:
     - \signals.slice(0, 25).map((signal, index) => <CandidateCard key={signal.id} candidate={signal} isActive={...} />)\
   - In \CandidateCard.tsx\, props interface is designed for \candidate={signal}\ plus \isActive\.

3. **Backend URL normalization**
   - Find all remaining references to port **5172** in the frontend code:
     - \Select-String -Path "src\**\*.ts*" -Pattern "5172"\
   - Decide whether to:
     - Run a service on 5172 **or**
     - Update calls to use the FastAPI backend on port **8000**.

4. **Final data-safety sweep**
   - Search for unguarded destructuring of API data:
     - \Select-String -Path "src\components\**\*.tsx" -Pattern "{ .* } = props" -CaseSensitive\
   - Ensure all top-level props from API calls have default values or optional chaining.

## Notes for future me (Espen)

- When resuming, start from step 1 above and focus on **backend URL and data wiring**.
- The UI being "just a dark/blue screen" is usually either:
  - A new runtime error in Console, or
  - No signals data coming back from backend (empty lists).
- Once stable, we should:
  - Add type-safe models for \Signal\ returned by \useRealtimeSignals\.
  - Wire real progress into \LiveAnalysisHeader\ instead of the placeholder defaults.

