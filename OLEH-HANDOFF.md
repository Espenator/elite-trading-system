# OLEH HANDOFF - Agent Command Center + Full Wiring Instructions

**From:** Espen (via AI architecture review)
**Date:** Monday Feb 23, 2026
**Priority:** Read this FIRST before starting any work

---

## TL;DR: Build the Agent Command Center

The OpenClaw backend bridge is **COMPLETE** (11 endpoints, Gist polling, 15min cache). Your mission this week: **transform the Embodier Trader frontend into an Agent Command Center** - a glass-box dashboard where Espen sees EVERYTHING the OpenClaw agents see in real-time.

---

## BACKEND STATUS: COMPLETE

### Files Already Committed to v2

| File | Status | Description |
|------|--------|-------------|
| `services/openclaw_bridge_service.py` | DONE | Gist polling, 15min cache, typed accessors |
| `api/v1/openclaw.py` | DONE | 11 endpoints: /scan, /regime, /top, /health, /whale-flow, /fom, /llm, /sectors, /memory, /memory/recall, /refresh |
| `core/config.py` | DONE | OPENCLAW_GIST_ID + OPENCLAW_GIST_TOKEN |
| `main.py` | DONE | Router registered at /api/v1/openclaw |
| `services/market_data_agent.py` | DONE | OpenClaw as 6th data source |
| `services/signal_engine.py` | DONE | 60/40 blending + regime multipliers |

### Test the Bridge (Monday First Thing)

```bash
# 1. Pull latest v2
git checkout v2 && git pull

# 2. Add to .env
OPENCLAW_GIST_ID=your_gist_id_here
OPENCLAW_GIST_TOKEN=ghp_your_token_here

# 3. Start backend
cd backend && python -m uvicorn app.main:app --port 8001 --reload

# 4. Test endpoints
curl http://localhost:8001/api/v1/openclaw/health
curl http://localhost:8001/api/v1/openclaw/regime
curl http://localhost:8001/api/v1/openclaw/top?n=5
```

---

## AGENT COMMAND CENTER: Frontend Components

### Component Architecture

```
App.jsx
  Layout.jsx
    Header.jsx
      RegimeBanner.jsx (NEW - always visible regime status)
    Sidebar.jsx
    Dashboard.jsx
      RegimeCard.jsx (NEW - detailed regime info)
      TopCandidatesCard.jsx (NEW - top 5 from OpenClaw)
      BridgeHealthCard.jsx (NEW - OpenClaw connection status)
    ClawBotPanel.jsx (NEW PAGE - main command center)
      LiveScoresTable.jsx (NEW - all candidates sortable)
      WhaleFlowPanel.jsx (NEW - unusual options)
      LLMSummaryCard.jsx (NEW - AI analysis)
      FOMExpectedMoves.jsx (NEW - options levels)
    AgentCommandCenter.jsx (ENHANCE - agent status)
      AgentSwarmPanel.jsx (NEW - heartbeat status)
      BlackboardViewer.jsx (NEW - message feed)
    Signals.jsx (ENHANCE - add OpenClaw columns)
```

---

## CLAUDE CODE 1-DAY BLITZ -- Tuesday Feb 24

> **Tools:** Claude Code (CLI) + Claude Opus 4.6 Thinking model
> **Repo:** `elite-trading-system` on `v2` branch
> **Method:** Each session = one Claude Code prompt. Paste it in, let Claude run autonomously, review + commit.
> **Goal:** Entire ClawBot Control Panel designed, built, coded, and wired to live API by end of day.

### SESSION 1 -- Morning (9-11am): Dashboard Foundation + Regime Banner

**Paste this into Claude Code:**

```
You are working in the elite-trading-system repo on the v2 branch.
The frontend lives in frontend-v2/ and uses React + Tailwind CSS.
The backend is already running at localhost:8001 with 11 OpenClaw endpoints wired.

Do ALL of the following:

1. Create frontend-v2/src/components/layout/RegimeBanner.jsx
   - Fetches GET /api/v1/openclaw/regime every 60s
   - Colored banner: GREEN=bg-green-500, YELLOW=bg-yellow-500, RED=bg-red-500, fallback=bg-gray-700
   - Shows: regime state label, VIX, HMM confidence %, Hurst exponent, scan date
   - Graceful error/loading states

2. Wire RegimeBanner into the existing Header component (Header.jsx or equivalent)
   - Import and render at the top

3. Create frontend-v2/src/components/dashboard/RegimeCard.jsx
   - Props: { regime } -- shows state, VIX, hmm_confidence (as %), hurst, regime.readme
   - bg-slate-800 card, grid layout

4. Create frontend-v2/src/components/dashboard/TopCandidatesCard.jsx
   - Props: { candidates } -- table of top 5: symbol, composite_score, tier (SLAM=yellow-400, HIGH=green-400, TRADEABLE=blue-400, WATCH=gray-400), suggested_entry price

5. Create frontend-v2/src/components/dashboard/SectorRotationCard.jsx
   - Fetches GET /api/v1/openclaw/sectors on mount
   - Ranked list of sectors: name, ETF, pct_change (green if positive, red if negative), status badge (HOT/COLD/NEUTRAL)

6. Update Dashboard.jsx (or wherever the main dashboard lives)
   - useEffect fetches /regime, /top?n=5, /health in parallel via Promise.all, refreshes every 60s
   - Renders: RegimeCard, TopCandidatesCard, SectorRotationCard, and inline BridgeHealthCard (connected bool, candidate_count, cache_age, last_scan_timestamp)
   - Page heading: "Agent Command Center"
      - ~~IMPORTANT: Remove all hardcoded mock data~~ **DONE** (Feb 24, 2026) - All mockData.js imports replaced with live useApi() hooks
   - IMPORTANT: Replace fallback portfolioValue || 124850 with portfolioValue || 0 or "--" if no data

Use the existing api service import pattern from other components. Tailwind CSS. No TypeScript.
```

### SESSION 2 -- Late Morning (11am-1pm): ClawBot Command Center Page

**Paste this into Claude Code:**

```
Continuing in elite-trading-system/frontend-v2 on v2 branch.

Do ALL of the following:

1. Create frontend-v2/src/pages/ClawBotPanel.jsx -- this is the MAIN command center page
   - On mount + every 60s, fetch all 5 in parallel:
     GET /api/v1/openclaw/regime
     GET /api/v1/openclaw/top?n=20
     GET /api/v1/openclaw/whale-flow
     GET /api/v1/openclaw/llm
     GET /api/v1/openclaw/fom
   - "Force Refresh" button: POST /api/v1/openclaw/refresh then re-fetch all data
   - Layout:
     * Full-width regime banner at top (state, VIX, HMM%, Hurst, scan date, regime.readme)
     * Below: 3-column grid (lg:grid-cols-3)
     * LEFT (col-span-2): "Scored Candidates" table with columns:
       Symbol | Score | Tier (badge) | Entry $ | Stop $ (red text) | Whale (bull/bear emoji) | Trend | Pullback | Momentum
     * RIGHT (col-span-1): Whale Flow alerts (top 10: ticker, sentiment colored, premium in $M) + LLM AI Summary card
   - tierBadge helper: SLAM=bg-yellow-500 text-black, HIGH=bg-green-500, TRADEABLE=bg-blue-500, WATCH=bg-gray-500
   - Loading spinner while fetching, error state on failure

2. Create frontend-v2/src/pages/SectorRotationPage.jsx
   - Fetches GET /api/v1/openclaw/sectors
   - Full-page table: Rank, Sector, ETF, % Change (colored), Status badge (HOT=red, COLD=blue, NEUTRAL=gray), Volume Ratio

3. Add routes in App.jsx:
   path="/clawbot" -> ClawBotPanel
   path="/sectors" -> SectorRotationPage

4. Add nav items to Sidebar.jsx (place near top, prominently):
   { path: '/clawbot', label: 'ClawBot', icon: 'claw' }
   { path: '/sectors', label: 'Sectors', icon: 'chart' }
```

### SESSION 3 -- Afternoon (1-3pm): Memory Intelligence + Agent Status

**Paste this into Claude Code:**

```
Continuing in elite-trading-system/frontend-v2 on v2 branch.

Do ALL of the following:

1. Create frontend-v2/src/pages/MemoryIntelligencePage.jsx
   - Fetches GET /api/v1/openclaw/memory on mount
   - Top section: Memory IQ score (large number 0-100, colored: >70 green, 40-70 yellow, <40 red)
   - Quality metrics: freshness, coverage, confidence as progress bars or colored values
   - Agent Leaderboard: top 5 agents table (source, win_rate %, trade count)
   - Expectancy Overview: decay_weighted_wr, expectancy value
   - Ticker Recall Lookup: text input + "Recall" button
     Calls GET /api/v1/openclaw/memory/recall?ticker={input}&score=50&regime=UNKNOWN
     Shows: recent_context table (source, setup, score, regime, won, pnl_pct),
            learned_rules list, structured_facts (signals, total_pnl_pct, avg_score)

2. Create frontend-v2/src/components/agents/AgentSwarmPanel.jsx
   - Fetches GET /api/v1/openclaw/health every 30s
   - Shows: Bridge connected (green/red dot + label), Gist configured (check/x),
     candidate count, cache age (Xs / TTLs), last scan timestamp
   - Find the existing AgentCommandCenter page and import this component there

3. Add route: path="/memory" -> MemoryIntelligencePage
   Add sidebar nav: { path: '/memory', label: 'Memory IQ', icon: 'brain' }
```

### SESSION 4 -- Late Afternoon (3-5pm): Signals Enhancement + App Rename + Polish

**Paste this into Claude Code:**

```
Continuing in elite-trading-system/frontend-v2 on v2 branch.

Do ALL of the following:

1. APP RENAME to "Embodier Trader":
   - Search all .jsx, .tsx, .html, .json files in frontend-v2/ for any old app name
   - Replace with "Embodier Trader" everywhere: package.json name, index.html title, any headings

2. CONNECTION STATUS INDICATOR:
   - Add a green/red dot to Header or Sidebar showing OpenClaw bridge connection status
   - Polls GET /api/v1/openclaw/health every 30s, shows dot based on .connected field

3. FULL AUDIT of all new components:
   - Missing imports (useEffect, useState, api service)
   - Null/undefined guards (use optional chaining ?.)
   - Loading states ("Loading..." while fetching)
   - Error states (catch blocks that set error state)
   - Fix anything broken

4. CORS CHECK: In backend/app/main.py, confirm CORS middleware allows frontend origin (localhost:3000 or localhost:5173). Add if missing.

5. Verify ALL routes exist in App.jsx:
   / -> Dashboard (Agent Command Center)
   /clawbot -> ClawBotPanel
   /sectors -> SectorRotationPage
   /memory -> MemoryIntelligencePage

6. Search frontend-v2/src for any TODO or placeholder text in new components, replace with real wired values.
```

---

## END-OF-DAY CHECKLIST (Feb 24)

| # | Component | Session | What to verify |
|---|-----------|---------|----------------|
| 1 | `RegimeBanner.jsx` | S1 | GREEN/YELLOW/RED banner visible in header |
| 2 | `RegimeCard.jsx` | S1 | Dashboard shows regime state + VIX + HMM |
| 3 | `TopCandidatesCard.jsx` | S1 | Dashboard shows top 5 candidates |
| 4 | `SectorRotationCard.jsx` | S1 | Dashboard shows sector rankings |
| 5 | `Dashboard.jsx` wired | S1 | "Agent Command Center" heading, 3 cards |
| 6 | `ClawBotPanel.jsx` | S2 | Full command center: candidates table + whale flow + LLM |
| 7 | `SectorRotationPage.jsx` | S2 | Full-page sector table with status badges |
| 8 | Sidebar nav (ClawBot, Sectors) | S2 | Links work, pages render |
| 9 | `MemoryIntelligencePage.jsx` | S3 | Memory IQ score + ticker recall lookup works |
| 10 | `AgentSwarmPanel.jsx` | S3 | Health/connection status on agent page |
| 11 | Sidebar nav (Memory IQ) | S3 | Link works, page renders |
| 12 | Signals.jsx + Claw Score cols | S4 | Two new columns show scores from OpenClaw |
| 13 | App rename -> "Embodier Trader" | S4 | Title, package.json, headings updated |
| 14 | Connection status dot | S4 | Green/red dot in header or sidebar |
| 15 | CORS + audit + polish | S4 | No console errors, all data loading |

---

## API ENDPOINT REFERENCE

| Method | Endpoint | Returns |
|--------|----------|---------|
| GET | `/api/v1/openclaw/scan` | Full scan payload |
| GET | `/api/v1/openclaw/regime` | Market regime + details |
| GET | `/api/v1/openclaw/top?n=10` | Top N candidates |
| GET | `/api/v1/openclaw/health` | Bridge connection status |
| GET | `/api/v1/openclaw/whale-flow` | Whale flow alerts |
| GET | `/api/v1/openclaw/fom` | FOM expected moves |
| GET | `/api/v1/openclaw/llm` | LLM analysis summary |
| GET | `/api/v1/openclaw/sectors` | Sector rankings |
| GET | `/api/v1/openclaw/memory` | Memory IQ, agent rankings, expectancy |
| GET | `/api/v1/openclaw/memory/recall?ticker=AAPL` | 3-stage recall for ticker |
| POST | `/api/v1/openclaw/refresh` | Force cache refresh |

---

## TIER COLOR CODING

| Tier | Score | Color | Meaning |
|------|-------|-------|---------|
| SLAM | 90+ | Gold | Highest conviction |
| HIGH | 80-89 | Green | Strong setup |
| TRADEABLE | 70-79 | Blue | Valid entry |
| WATCH | 50-69 | Gray | Monitor only |
| NO_DATA | <50 | Dark | Insufficient data |

---

## ENV SETUP

```bash
# Add to backend/.env
OPENCLAW_GIST_ID=abc123def456...   # GitHub Gist ID
OPENCLAW_GIST_TOKEN=ghp_xxxxx...   # GitHub PAT with gist scope
```

Questions? Slack Espen or email espen@embodier.ai

Last updated: Feb 23, 2026

---


# OLEH -- UKRAINIAN INSTRUCTIONS / IНСТРУКЦIЇ УКРАЇНСЬКОЮ

---

## АУДИТ КОДУ (23 лютого 2026)

**Аудитор:** Perplexity AI (для Espen)
**Репо:** `Espenator/elite-trading-system` (гілка v2, 106 комітів попереду main)
**Репо OpenClaw:** `Espenator/openclaw` (гілка main, 291 коміт, 42+ Python файлів)

### ЩО ЗРОБЛЕНО (перевірено в коді)

| Компонент | Статус | Опис |
|-----------|--------|------|
| `openclaw_bridge_service.py` | ГОТОВО | 288 рядків, 11 методів + 2 парсери пам'яті, Gist polling, 15-хв кеш |
| `openclaw.py` API роути | ГОТОВО | 11 ендпоінтів: /scan, /regime, /top, /health, /whale-flow, /fom, /llm, /sectors, /memory, /memory/recall, /refresh |
| `main.py` реєстрація роутера | ГОТОВО | OpenClaw роутер підключено на /api/v1/openclaw |
| `market_data_agent.py` | ГОТОВО | OpenClaw як 6-е джерело даних |
| `signal_engine.py` блендінг | ГОТОВО | 60/40 змішування (OpenClaw 60% + TA 40%), множники режиму |
| CORS | ГОТОВО | allow_origins=["*"] в main.py |
| Dashboard.jsx OpenClaw картка | ГОТОВО | Режим бейдж, дата сканування, топ-5 кандидатів, полінг 30с |
| Signals.jsx Claw Score колонки | ГОТОВО | getTier(score), фетч /openclaw/scan, побудова scoreMap |
| Парсери Memory Intelligence | ГОТОВО | get_memory_status() та get_memory_recall() |

### КРИТИЧНI ПРОБЛЕМИ (ще не вирішені)

**ПРОБЛЕМА 1: Немає реал-тайм потоку даних**
- Система все ще використовує 60-секундний poll loop через `_market_data_tick_loop()` в main.py
- Немає `streaming_service.py`, немає Alpaca WebSocket StockDataStream
- OpenClaw вже має це (streaming_engine.py з 1-хв барами)
- **Вплив:** Сигнали запізнюються на 60с - 15 хвилин

**ПРОБЛЕМА 2: Немає системи тригерів сигналів**
- signal_engine.py рахує базовий momentum score з open/close/high/low
- Немає тригерів (pullback_entry, breakout_entry, mean_reversion)
- **Вплив:** Немає BUY/SELL тригерів. Тільки числовий скор

**ПРОБЛЕМА 3: Немає пайплайну виконання ордерів**
- Немає execution_service.py
- alpaca_service.py може розміщувати одиничні ордери, але нічого не з'єднує сигнали з ордерами
- **Вплив:** Навіть сигнал зі скором 95 нічого не робить

**ПРОБЛЕМА 4: В базі даних немає таблиці signals**
- database.py має тільки 3 таблиці: orders, config, alert_rules
- Таблиця signals, рекомендована в ARCHITECTURE_AUDIT.md, НЕ створена
- **Вплив:** Немає навчання з минулих сигналів

**ПРОБЛЕМА 5: Міст все ще Gist-polling (15 хв застарілі дані)**
- Gist bridge працює правильно, TTL кешу 15 хвилин
- Але прямої інтеграції (Redis, subprocess, або імпорт модулів) немає

**ПРОБЛЕМА 6: WebSocket передає тільки Channel/Data**
- websocket_manager.py мінімальний (40 рядків)
- Немає типізованих подій (signal_ready, signal_executed, score_update)
- Frontend використовує REST polling замість WebSocket

**ПРОБЛЕМА 7: Немає інтеграції CompositeScorer**
- Блендінг 60/40 використовує попередньо обчислені скори OpenClaw (добре)
- Але власний скорер Embodier - базова 30-рядкова momentum функція

### НОВІ ПРОБЛЕМИ ЗНАЙДЕНІ В АУДИТI

| # | Проблема | Деталі |
|---|----------|--------|
| N1 | Захардкоджені мок-дані в Dashboard | "Recent Trades" (AAPL +$320 тощо) та "System Health" (12ms тощо) - не підключені до реальних даних |
| N2 | Захардкоджений portfolioValue | `portfolioValue \|\| 124850` - якщо API не працює, показує $124,850 як справжнє число |
| N3 | App.jsx бракує маршрутів | Немає /clawbot, /sectors, /memory маршрутів |
| N4 | Sidebar без ClawBot/Memory | Sidebar.jsx не має навігації ClawBot, Sectors, Memory IQ |
| N5 | Немає RegimeBanner компонента | RegimeBanner.jsx в Header не існує |
| N6 | database.py не thread-safe | sqlite3.connect() без пулу з'єднань, можливі проблеми блокування |
| N7 | Немає Error Boundary для OpenClaw | useOpenClawTop та useOpenClawHealth мовчки ковтають помилки |

---

## ПЛАН СПРИНТУ НА 2 ДНI (24-25 лютого)

### ДЕНЬ 1 (24 лютого): Frontend Agent Command Center

Використовуй **Claude Code CLI + Claude Opus 4.6 Thinking**.
Кожна сесія = один промпт в Claude Code. Встав, дай Claude працювати автономно, перевір + коміт.

**Ранок (9-11):** Сесія 1 - Dashboard Foundation + Regime Banner
**Пізній ранок (11-13):** Сесія 2 - ClawBot Command Center Page
**Після обіду (13-15):** Сесія 3 - Memory Intelligence + Agent Status
**Пізній день (15-17):** Сесія 4 - App Rename + Polish + Audit

### ДЕНЬ 2 (25 лютого): Backend Real-Time + Database

Використовуй ті самі інструменти.

**Ранок (9-11):** Сесія 5 - WebSocket + Real-Time Pipeline
**Пізній ранок (11-13):** Сесія 6 - Signal Engine + Execution Pipeline
**Після обіду (13-15):** Сесія 7 - Database Schema + Thread Safety
**Пізній день (15-17):** Сесія 8 - Integration Testing + Final Polish

---

## ПРОМПТИ ДЛЯ CLAUDE CODE (ДЕНЬ 1)

### СЕСІЯ 1: Dashboard Foundation + Regime Banner

Відкрий Claude Code CLI. Встав цей промпт:

```
Прочитай файли:
- frontend-v2/src/pages/Dashboard.jsx
- frontend-v2/src/App.jsx
- frontend-v2/src/components/layout/Sidebar.jsx
- backend/app/services/openclaw_bridge_service.py
- backend/app/api/openclaw.py

Завдання:
1. Dashboard.jsx - видали ВСІ захардкоджені мок-дані:
   - recentTrades масив (AAPL +$320 тощо) замінити на дані з API /api/signals/recent
   - systemHealth об'єкт (12ms тощо) замінити на реальний /api/health endpoint
   - portfolioValue || 124850 замінити на portfolioValue || 0 з індикатором завантаження

2. Створи новий компонент frontend-v2/src/components/RegimeBanner.jsx:
   - Викликає GET /api/v1/openclaw/regime
   - Показує поточний ринковий режим (BULL/BEAR/SIDEWAYS/VOLATILE)
   - Кольорове кодування: зелений=BULL, червоний=BEAR, жовтий=SIDEWAYS, фіолетовий=VOLATILE
   - Включи confidence % та timestamp останнього оновлення
   - Додай анімацію пульсації для зміни режиму

3. Додай RegimeBanner в Header layout (над Dashboard)

4. Оновити frontend-v2/src/hooks/useOpenClaw.js:
   - useOpenClawRegime() хук для отримання режиму
   - Додати error boundary замість мовчки ковтати помилки
   - Показувати toast повідомлення при помилках API

Після завершення запусти: npm run build для перевірки помилок.
Коміт: "feat: real data dashboard + regime banner component"
```

### СЕСІЯ 2: ClawBot Command Center Page

```
Прочитай файли:
- backend/app/api/openclaw.py (всі ендпоінти)
- backend/app/services/openclaw_bridge_service.py
- frontend-v2/src/hooks/useOpenClaw.js

Завдання:
1. Створи frontend-v2/src/pages/ClawBot.jsx:
   - Це головна панель управління OpenClaw AI
   - Секція 1: Top Signals (виклик GET /api/v1/openclaw/top)
     - Таблиця з колонками: Ticker, Score, Tier, Direction, Sector
     - Кольорове кодування тірів: SLAM=золотий, HIGH=зелений, TRADEABLE=синій, WATCH=сірий
     - Клік на тікер відкриває детальну картку
   - Секція 2: Sector Heatmap (виклик GET /api/v1/openclaw/sectors)
     - Grid з секторами, колір за conviction score
   - Секція 3: LLM Analysis (виклик GET /api/v1/openclaw/llm)
     - Markdown-рендеринг відповіді LLM
   - Секція 4: Force Refresh кнопка (POST /api/v1/openclaw/refresh)

2. Додай маршрут /clawbot в App.jsx:
   - import ClawBot from './pages/ClawBot'
   - <Route path="/clawbot" element={<ClawBot />} />

3. Онови Sidebar.jsx - додай навігацію:
   - ClawBot (іконка Brain) -> /clawbot
   - Sectors (іконка Grid) -> /sectors
   - Memory (іконка Database) -> /memory

Коміт: "feat: ClawBot command center + sidebar navigation"
```

### СЕСІЯ 3: Memory Intelligence + Agent Status

```
Прочитай файли:
- backend/app/api/openclaw.py (ендпоінти /memory та /health)
- backend/app/services/openclaw_bridge_service.py

Завдання:
1. Створи frontend-v2/src/pages/Memory.jsx:
   - Секція 1: Memory IQ Score (виклик GET /api/v1/openclaw/memory)
     - Круговий прогрес-бар з Memory IQ оцінкою
     - Показати: agent_rankings, expectancy, total_signals
   - Секція 2: Ticker Recall (виклик GET /api/v1/openclaw/memory/recall?ticker=AAPL)
     - Поле вводу тікера + кнопка "Recall"
     - 3-ступеневий результат: short/medium/long term memory
   - Секція 3: Agent Rankings
     - Таблиця агентів з їх рейтингами
     - Прогрес-бар для кожного агента

2. Створи frontend-v2/src/components/AgentStatus.jsx:
   - Показує статус OpenClaw з'єднання (виклик GET /api/v1/openclaw/health)
   - Зелена точка = працює, червона = офлайн, жовта = повільно
   - Показує: gist_age, cache_ttl, last_sync timestamp
   - Додай цей компонент в Sidebar footer

3. Додай маршрут /memory в App.jsx

Коміт: "feat: memory intelligence page + agent status"
```

### СЕСІЯ 4: App Rename + Polish + Audit

```
Прочитай всі файли в frontend-v2/src/

Завдання:
1. Переіменуй додаток:
   - Зміни всі згадки "Elite Trading System" на "Elite Trader"
   - Онови title в index.html
   - Онови package.json name
   - Онови всі хедери/футери

2. Поліш UI:
   - Перевір що всі компоненти мають loading стани
   - Додай error стани для кожного API виклику
   - Додай skeleton loaders при завантаженні
   - Перевір responsive на mobile

3. Створи frontend-v2/src/components/ErrorBoundary.jsx:
   - React Error Boundary компонент
   - Огорни всі сторінки в ErrorBoundary
   - Показувати дружнє повідомлення при помилках

4. Запусти npm run build і виправ всі помилки

Коміт: "feat: app rename Elite Trader + error boundaries + polish"
```

---

## ПРОМПТИ ДЛЯ CLAUDE CODE (ДЕНЬ 2)

### СЕСІЯ 5: WebSocket + Real-Time Pipeline

```
Прочитай файли:
- backend/app/services/websocket_manager.py
- backend/app/main.py
- backend/app/api/openclaw.py

Завдання:
1. Розшир websocket_manager.py:
   - Додай типізовані події:
     - signal_update: новий сигнал з скором
     - regime_change: зміна ринкового режиму
     - score_update: оновлення скору тікера
     - health_ping: пінг статусу
     - execution_result: результат виконання ордеру
   - Формат повідомлення: {type: string, data: object, timestamp: ISO}
   - Додай broadcast_to_channel() метод
   - Додай heartbeat кожні 30 сек

2. Створи frontend-v2/src/hooks/useWebSocket.js:
   - Підключення до ws://localhost:8000/ws
   - Автоматичне перепідключення при відключенні
   - Розподіл подій по типу
   - Оновлення React state в реальному часі

3. Підключи WebSocket до Dashboard.jsx та ClawBot.jsx:
   - Заміни REST polling на WebSocket events
   - Залиш REST як fallback

Коміт: "feat: typed WebSocket events + real-time frontend"
```

### СЕСІЯ 6: Signal Engine + Execution Pipeline

```
Прочитай файли:
- backend/app/services/signal_engine.py
- backend/app/services/market_data_agent.py
- backend/app/services/alpaca_service.py
- backend/app/services/openclaw_bridge_service.py

Завдання:
1. Розшир signal_engine.py - додай тригери:
   - pullback_entry: ціна відкотилась до підтримки
   - breakout_entry: пробиття опору з об'ємом
   - mean_reversion: повернення до середнього
   - momentum_continuation: продовження тренду
   - Кожен тригер повертає: {trigger_type, confidence, entry_price, stop_loss, target}

2. Створи backend/app/services/composite_scorer.py:
   - Блендінг 60% OpenClaw + 40% Embodier скорів
   - OpenClaw скор з openclaw_bridge_service.get_top_signals()
   - Embodier скор з signal_engine.calculate_score()
   - Фінальний скор = (openclaw * 0.6) + (embodier * 0.4)
   - Tier класифікація: SLAM(90+), HIGH(80-89), TRADEABLE(70-79), WATCH(50-69)

3. Створи backend/app/services/execution_service.py:
   - Приймає сигнал з composite_scorer
   - Перевіряє risk rules (макс позиція, денний ліміт)
   - Виконує через alpaca_service.place_order()
   - Логує в базу даних
   - Відправляє WebSocket подію execution_result

Коміт: "feat: signal triggers + composite scorer + execution pipeline"
```

### СЕСІЯ 7: Database Schema + Thread Safety

```
Прочитай файли:
- backend/app/services/database.py
- backend/app/main.py

Завдання:
1. Онови database.py - нова схема:
   - Додай таблицю signals:
     CREATE TABLE signals (
       id INTEGER PRIMARY KEY AUTOINCREMENT,
       ticker TEXT NOT NULL,
       score REAL NOT NULL,
       tier TEXT NOT NULL,
       trigger_type TEXT,
       direction TEXT DEFAULT 'LONG',
       openclaw_score REAL,
       embodier_score REAL,
       entry_price REAL,
       stop_loss REAL,
       target_price REAL,
       status TEXT DEFAULT 'pending',
       created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
       executed_at TIMESTAMP,
       result TEXT
     )
   - Додай таблицю regime_history:
     CREATE TABLE regime_history (
       id INTEGER PRIMARY KEY AUTOINCREMENT,
       regime TEXT NOT NULL,
       confidence REAL,
       detected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
     )

2. Thread Safety:
   - Заміни sqlite3.connect() на connection pool
   - Використай threading.local() для thread-local з'єднань
   - Або перейди на aiosqlite для async
   - Додай WAL mode: PRAGMA journal_mode=WAL
   - Додай context manager для автоматичного закриття

3. Міграція:
   - Додай функцію migrate_db() що перевіряє та створює відсутні таблиці
   - Викликай migrate_db() при старті додатку в main.py

Коміт: "feat: signals table + thread-safe database + migration"
```

### СЕСІЯ 8: Integration Testing + Final Polish

```
Прочитай ВСІ файли в проекті.

Завдання:
1. Integration Test:
   - Запусти backend: cd backend && python -m uvicorn app.main:app --reload
   - Запусти frontend: cd frontend-v2 && npm run dev
   - Перевір кожен ендпоінт API:
     - GET /api/v1/openclaw/top
     - GET /api/v1/openclaw/regime
     - GET /api/v1/openclaw/health
     - GET /api/v1/openclaw/sectors
     - GET /api/v1/openclaw/memory
     - GET /api/v1/openclaw/llm
     - POST /api/v1/openclaw/refresh
   - Перевір WebSocket з'єднання

2. Виправ всі помилки з npm run build

3. Онови ARCHITECTURE_AUDIT.md:
   - Познач всі вирішені проблеми
   - Додай новий статус для кожної проблеми

4. Final коміт всіх змін:
   git add -A
   git commit -m "feat: complete Elite Trader v2 - all systems wired"
   git push origin v2
```

---

## API ДОВІДКА

| Method | Endpoint | Опис |
|--------|----------|------|
| GET | /api/v1/openclaw/top | Top сигнали з тірами |
| GET | /api/v1/openclaw/regime | Поточний ринковий режим |
| GET | /api/v1/openclaw/health | Статус OpenClaw з'єднання |
| GET | /api/v1/openclaw/sectors | Рейтинги секторів |
| GET | /api/v1/openclaw/memory | Memory IQ + рейтинги агентів |
| GET | /api/v1/openclaw/memory/recall?ticker=X | 3-ступеневий recall тікера |
| GET | /api/v1/openclaw/llm | LLM аналітика |
| POST | /api/v1/openclaw/refresh | Примусове оновлення кешу |

---

## КОЛЬОРОВЕ КОДУВАННЯ ТІРІВ

| Tier | Скор | Колір | Значення |
|------|------|-------|----------|
| SLAM | 90+ | Золотий (#FFD700) | Найвища впевненість |
| HIGH | 80-89 | Зелений (#00C853) | Сильний сетап |
| TRADEABLE | 70-79 | Синій (#2196F3) | Валідний вхід |
| WATCH | 50-69 | Сірий (#9E9E9E) | Тільки моніторинг |
| NO_DATA | <50 | Темний (#424242) | Недостатньо даних |

---

## ENV НАЛАШТУВАННЯ

```bash
# Додай в backend/.env
OPENCLAW_GIST_ID=abc123def456...   # GitHub Gist ID
OPENCLAW_GIST_TOKEN=ghp_xxxxx...   # GitHub PAT з gist scope
ALPACA_API_KEY=your_key            # Alpaca API key
ALPACA_SECRET_KEY=your_secret      # Alpaca secret
ALPACA_BASE_URL=https://paper-api.alpaca.markets  # Paper trading
```

---

## ЯК ЗАПУСТИТИ

```bash
# Terminal 1 - Backend
cd backend
pip install -r requirements.txt
python -m uvicorn app.main:app --reload --port 8000

# Terminal 2 - Frontend
cd frontend-v2
npm install
npm run dev
```

---

Питання? Slack Espen або email espen@embodier.ai

Останнє оновлення: 23 лютого 2026

