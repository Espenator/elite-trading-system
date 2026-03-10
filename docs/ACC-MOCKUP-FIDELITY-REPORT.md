# Agent Command Center — Mockup Fidelity Report

**Date:** March 2, 2026  
**Scope:** Agent Command Center page only (all tabs; this pass focused on Swarm Overview and shared header/footer).  
**Reference mockups:** 01-agent-command-center-final, agent_command_center_brain_map, agent_command_center_node_control, agent_command_center_swarm_overview.

---

## 1. Visual differences found (before fixes)

### Header bar
- Border used `border-gray-800` instead of design system `#1e293b`.
- GREEN badge used Tailwind `emerald-500/20`; design system uses `#064e3b` (green-900) and `#10b981`.
- CPU/RAM/GPU bars: MetricBar default was cyan; mockup shows **blue CPU**, **green RAM**, **purple GPU**.
- ONLINE count showed `totalCount/totalCount`; switched to `onlineCount/totalCount` for correctness when data loads.
- KILL SWITCH was `rounded`; mockup/design system specify **rounded-full** and solid red background.

### Tab bar
- Active tab used `#00D9FF`; design system primary accent is `#06b6d4` (cyan-500). Background was `#00D9FF/5`; aligned to `#164e63/10` (cyan-900).
- Inactive text was `gray-500`; aligned to `#64748b` (--text-muted).

### Footer bar
- Border and text used gray-*; aligned to `#1e293b` and `#64748b` / `#10b981` for status.
- Font size was `9px`; set to `10px` for readability and design system.

### Swarm Overview tab — layout
- Implementation used a **row-based grid** (row 1: Health | Activity | Topology; row 2: Quick+Team+Alerts | Resource | ELO+Conference; row 3: Last Conference | Blackboard | Drift).
- Mockup 01 uses **three vertical columns**: **Left** = Health Matrix, Quick Actions, Team Status, System Alerts; **Center** = Live Activity Feed, Resource Monitor, Blackboard; **Right** = Swarm Topology, ELO Leaderboard, Conference Pipeline, Last Conference, Drift Monitor.

### Swarm Overview — Quick Actions
- Buttons were outline-style (cyan/red/amber/purple borders). Mockup shows **solid filled buttons**: Restart All **blue**, Stop All **red**, Spawn Team **green**, Run Conference **purple**, Emergency Kill **red**.

### Swarm Overview — cards
- Cards used `rounded-lg` and `border-[rgba(42,52,68,0.5)]`. Design system specifies **rounded-md (6px)** and **border `#1e293b`** (--border-default).
- Section headers were `text-white`; design system uses **--text-secondary `#94a3b8`** for card headers.

### Swarm Overview — tables
- Table headers were `text-gray-500` and not explicitly uppercase. Design system: **text-[10px] uppercase text-slate-500** (we use `#64748b`).
- Row hover was `#00D9FF/5`; design system selected row/hover is **--bg-selected #164e63**; used `#164e63/10` for hover.

### Swarm Overview — Drift Monitor
- All drift bars were cyan. Mockup uses **red / orange / green** by severity (high/mid/low). No color differentiation by value.

---

## 2. Files changed

| File | Changes |
|------|--------|
| **`frontend-v2/src/pages/AgentCommandCenter.jsx`** | Header: border `#1e293b`, GREEN badge green-900/10b981, MetricBar colors blue/green/purple for CPU/RAM/GPU, ONLINE = onlineCount/totalCount, KILL SWITCH rounded-full and solid red. Tab bar: active cyan #06b6d4 and bg #164e63/10, inactive #64748b. Footer: border #1e293b, text #64748b/#10b981/#f8fafc, font 10px. |
| **`frontend-v2/src/pages/agent-tabs/SwarmOverviewTab.jsx`** | All cards: border `#1e293b`, rounded-md. All section titles: text-[#94a3b8]. Quick Actions: solid buttons (blue, red, green, purple, red). Layout: 3-column grid (4-4-4) — Col1 Health+Quick+Team+Alerts, Col2 Activity+Resource+Blackboard, Col3 Topology+ELO+Conference+LastConference+Drift. Resource/ELO/Blackboard tables: header text-[#64748b] uppercase, row border/hover #1e293b and #164e63/10. Drift Monitor: bar colors by severity (red ≥0.2, orange ≥0.1, green &lt;0.1), footer “Mean PSI” retained. Swarm Topology card header text-[#94a3b8]. |

---

## 3. Fidelity fixes made

- **Header:** Design system borders and colors; GREEN badge; CPU blue, RAM green, GPU purple bars; KILL SWITCH rounded-full solid red; ELITE TRADING SYSTEM muted.
- **Tabs:** Active tab cyan #06b6d4 with underline; inactive #64748b; ACTIVE label.
- **Footer:** WebSocket Connected, API Healthy, agents, LLM Flow 847, Conference 8/12, Last Refresh, Load 2.4/4.0, Uptime with correct separators and green dots; border and typography aligned to design system.
- **Swarm Overview layout:** Reordered to mockup 01’s three columns (left / center / right) with correct panel stacking.
- **Quick Actions:** Restart All blue, Stop All red, Spawn Team green, Run Conference purple, Emergency Kill red (solid buttons).
- **Cards:** Rounded-md, border #1e293b, bg #111827.
- **Card headers:** Uppercase, tracking-wider, font-mono, color #94a3b8.
- **Tables:** Header 10px uppercase #64748b; row borders #1e293b; hover #164e63/10.
- **Drift Monitor:** Bar fill colors by value (red/orange/green).

---

## 4. Anything still off from the mockup

- **Agent Health Matrix:** Mockup shows a dense 6×2-style grid of **dots only** per category (Scanner, Intelligence, Execution, Streaming, Sentiment, MLLearning, Conference) with a small legend. Current implementation uses mixed labels and dots; dot count/layout is not pixel-matched to mockup. **Remaining:** Optional polish to dot-only grid + legend if product wants exact match.
- **Live Activity Feed:** Mockup shows agent names color-coded (e.g. RegimeDetector green, Scanner-07 blue). We use a rotating color map; colors may not match specific agent types. **Remaining:** Optional mapping of agent type → color per design system.
- **Swarm Topology:** Mockup has a network graph with colored nodes. We have a 5-column DAG with edges; node positions and density may differ. **Remaining:** Optional layout/spacing tweaks to match mockup graph.
- **Conference Pipeline:** Mockup shows horizontal flow with checkmarks. We have the same four stages and checkmarks; arrow styling could be refined. **Remaining:** Minor.
- **Last Conference:** Mockup shows large circular progress ring (e.g. 88%) and participant list. We have ring and list; ring size/style could be tuned. **Remaining:** Minor.
- **Brain Map / Node Control & HITL tabs:** Not changed in this pass (user asked to focus on bringing page to mockup fidelity without moving to another page). Those tabs still need to be compared to their mockups in a future pass.

---

## 5. Ready for approval?

**Swarm Overview tab and shared ACC chrome: Yes, with minor caveats.**

- **Header, tab bar, and footer** match the approved mockup and design system (borders, colors, typography, KILL SWITCH, metric bars).
- **Swarm Overview** uses the correct 3-column structure, panel order, Quick Action button colors, card and table styling, and Drift Monitor bar colors. Remaining items are optional refinements (Health Matrix dots, activity feed agent colors, topology graph detail).
- **Other tabs** (Agent Registry, Spawn & Scale, Live Wiring, Blackboard & Comms, Conference & Consensus, ML Ops, Logs & Telemetry) were not modified this pass; Brain Map and Node Control & HITL were not in scope.

**Verdict:** The Agent Command Center page is **ready for approval** for the Swarm Overview tab and global header/footer. Remaining differences are minor or confined to other tabs.
