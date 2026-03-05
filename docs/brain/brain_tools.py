#!/usr/bin/env python3
"""
🧠 Embodier Trader — Second Brain CLI Tools
Espen Schiefloe's persistent memory system for trading + app dev

Usage:
    python3 .brain/brain_tools.py <command> [args]

Commands:
    session-summary          → Print full current context for Claude
    new-session              → Log a new trading session
    trades [--last N]        → Show recent trades
    add-trade                → Interactive trade journal entry
    performance [--period]   → Show performance stats
    watchlist                → Show active watchlist
    add-watch SYMBOL thesis  → Add to watchlist
    research [--active]      → Show research notes
    add-research title body  → Add research note
    tasks [--status x]       → Show app dev tasks
    add-task title desc      → Add app dev task
    levels SYMBOL            → Show key levels for symbol
    add-level SYM price type → Add a key market level
    update-task ID status    → Update task status
    search QUERY             → Search all brain content
"""

import sqlite3
import json
import argparse
import sys
import os
from datetime import datetime, date

DB_PATH = os.path.join(os.path.dirname(__file__), "brain.db")
CONTEXT_PATH = os.path.join(os.path.dirname(__file__), "CONTEXT.md")


def get_conn():
    return sqlite3.connect(DB_PATH)


def fmt_date(d=None):
    return (d or datetime.now()).strftime("%Y-%m-%d")


def fmt_dt(d=None):
    return (d or datetime.now()).strftime("%Y-%m-%d %H:%M")


# ─────────────────────────────────────────────
# SESSION SUMMARY — Claude reads this on startup
# ─────────────────────────────────────────────
def session_summary():
    conn = get_conn()
    c = conn.cursor()
    today = fmt_date()

    print("=" * 60)
    print(f"🧠 SECOND BRAIN SESSION SUMMARY — {today}")
    print("=" * 60)

    # Open positions
    c.execute("SELECT symbol, direction, entry_price, size, setup FROM trades WHERE status='open' ORDER BY date DESC")
    open_trades = c.fetchall()
    print(f"\n📍 OPEN POSITIONS ({len(open_trades)})")
    if open_trades:
        for t in open_trades:
            print(f"  {t[1]} {t[0]} | Entry: {t[2]} | Size: {t[3]} | Setup: {t[4]}")
    else:
        print("  None")

    # Active watchlist
    c.execute("SELECT symbol, thesis, target_entry, priority FROM watchlist WHERE is_active=1 ORDER BY priority ASC LIMIT 10")
    wl = c.fetchall()
    print(f"\n👀 WATCHLIST ({len(wl)})")
    prio_map = {1: "🔴 HIGH", 2: "🟡 MED", 3: "⚪ LOW"}
    for w in wl:
        print(f"  {prio_map.get(w[3], '?')} {w[0]} | {w[1]} | Entry: {w[2] or 'TBD'}")

    # Recent trades (last 5)
    c.execute("""SELECT date, symbol, direction, pnl, pnl_r, followed_rules
                 FROM trades WHERE status='closed' ORDER BY date DESC LIMIT 5""")
    recent = c.fetchall()
    print(f"\n📊 RECENT TRADES (last 5)")
    if recent:
        for t in recent:
            pnl_str = f"${t[3]:+.2f}" if t[3] else "N/A"
            r_str = f"{t[4]:+.2f}R" if t[4] else ""
            rules = "✅" if t[5] else "❌"
            print(f"  {t[0]} {t[2]} {t[1]} | {pnl_str} {r_str} {rules}")
    else:
        print("  No closed trades yet")

    # Performance (last 30 days)
    c.execute("""SELECT COUNT(*), SUM(CASE WHEN pnl>0 THEN 1 ELSE 0 END),
                        SUM(pnl), AVG(pnl_r), AVG(followed_rules)
                 FROM trades WHERE status='closed'
                 AND date >= date('now', '-30 days')""")
    row = c.fetchone()
    if row and row[0]:
        total, wins, pnl, avg_r, rule_pct = row
        losses = total - (wins or 0)
        wr = (wins / total * 100) if total > 0 else 0
        print(f"\n📈 LAST 30 DAYS PERFORMANCE")
        print(f"  Trades: {total} | W: {wins} L: {losses} | WR: {wr:.0f}%")
        print(f"  Total P&L: ${pnl:+.2f} | Avg R: {avg_r:.2f}R" if pnl else "  No P&L data")
        print(f"  Rules followed: {(rule_pct or 0)*100:.0f}%")

    # Active research
    c.execute("SELECT title, conviction, instrument FROM research WHERE is_active=1 ORDER BY created_at DESC LIMIT 5")
    research = c.fetchall()
    print(f"\n🔬 ACTIVE RESEARCH ({len(research)})")
    for r in research:
        print(f"  [{r[1] or '?'}] {r[0]} | {r[2] or ''}")

    # App dev tasks
    c.execute("""SELECT title, priority, feature_area FROM app_tasks
                 WHERE status IN ('in_progress','backlog') ORDER BY
                 CASE priority WHEN 'critical' THEN 1 WHEN 'high' THEN 2 WHEN 'medium' THEN 3 ELSE 4 END
                 LIMIT 8""")
    tasks = c.fetchall()
    print(f"\n🛠️  APP DEV TASKS (top {len(tasks)})")
    prio_icons = {"critical": "🔴", "high": "🟠", "medium": "🟡", "low": "⚪"}
    for t in tasks:
        icon = prio_icons.get(t[1], "•")
        print(f"  {icon} [{t[2] or 'general'}] {t[0]}")

    # Key levels
    c.execute("""SELECT symbol, level_price, level_type, description FROM market_levels
                 WHERE is_active=1 ORDER BY symbol, level_price""")
    levels = c.fetchall()
    if levels:
        print(f"\n📐 KEY MARKET LEVELS")
        by_sym = {}
        for lv in levels:
            by_sym.setdefault(lv[0], []).append(lv)
        for sym, lvs in list(by_sym.items())[:6]:
            lv_str = ", ".join([f"{lv[2]} {lv[1]}" for lv in lvs])
            print(f"  {sym}: {lv_str}")

    print("\n" + "=" * 60)
    print("💬 Ready. What are we working on today?")
    print("=" * 60)
    conn.close()


# ─────────────────────────────────────────────
# TRADE JOURNAL
# ─────────────────────────────────────────────
def add_trade_interactive():
    """Interactive trade journal entry"""
    print("📝 LOG TRADE\n")
    t = {}
    t["date"] = input("Date (YYYY-MM-DD) [today]: ").strip() or fmt_date()
    t["symbol"] = input("Symbol (e.g. NVDA, BTC): ").strip().upper()
    t["market"] = input("Market [equity/crypto/forex/options]: ").strip() or "equity"
    t["direction"] = input("Direction [LONG/SHORT]: ").strip().upper()
    t["entry_price"] = float(input("Entry price: ").strip() or 0)
    exit_p = input("Exit price (blank if still open): ").strip()
    t["exit_price"] = float(exit_p) if exit_p else None
    t["size"] = float(input("Size (shares/units): ").strip() or 0)
    pnl = input("P&L ($): ").strip()
    t["pnl"] = float(pnl) if pnl else None
    pnl_r = input("P&L in R multiples (e.g. 1.5): ").strip()
    t["pnl_r"] = float(pnl_r) if pnl_r else None
    t["setup"] = input("Setup type (e.g. zone_test, structural_break): ").strip()
    t["structure"] = input("Structure (e.g. HH/HL, CHOCH): ").strip()
    t["timeframe"] = input("Timeframe (e.g. 15m, 1H, Daily): ").strip()
    t["entry_reason"] = input("Entry reason: ").strip()
    t["exit_reason"] = input("Exit reason (blank if open): ").strip() or None
    t["mistakes"] = input("Mistakes made (blank if none): ").strip() or None
    t["lessons"] = input("Lessons learned: ").strip() or None
    followed = input("Followed all rules? [y/n]: ").strip().lower()
    t["followed_rules"] = 1 if followed == "y" else 0
    t["tags"] = input("Tags (comma-separated, e.g. momentum,gap): ").strip()
    t["status"] = "open" if not exit_p else "closed"

    conn = get_conn()
    c = conn.cursor()
    c.execute("""INSERT INTO trades
        (date, symbol, market, direction, entry_price, exit_price, size, pnl, pnl_r,
         setup, structure, timeframe, entry_reason, exit_reason, mistakes, lessons,
         followed_rules, tags, status)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        (t["date"], t["symbol"], t["market"], t["direction"], t["entry_price"],
         t["exit_price"], t["size"], t["pnl"], t["pnl_r"], t["setup"], t["structure"],
         t["timeframe"], t["entry_reason"], t["exit_reason"], t["mistakes"], t["lessons"],
         t["followed_rules"], t["tags"], t["status"]))
    conn.commit()
    trade_id = c.lastrowid
    conn.close()
    print(f"\n✅ Trade #{trade_id} logged: {t['direction']} {t['symbol']}")


def add_trade_quick(symbol, direction, entry, setup="", notes=""):
    """Programmatic trade add (used by other scripts)"""
    conn = get_conn()
    c = conn.cursor()
    c.execute("""INSERT INTO trades (date, symbol, direction, entry_price, setup, entry_reason, status)
                 VALUES (?, ?, ?, ?, ?, ?, 'open')""",
              (fmt_date(), symbol.upper(), direction.upper(), float(entry), setup, notes))
    conn.commit()
    trade_id = c.lastrowid
    conn.close()
    return trade_id


def show_trades(last=20, symbol=None, status=None):
    conn = get_conn()
    c = conn.cursor()
    query = "SELECT id, date, symbol, direction, entry_price, exit_price, pnl, pnl_r, setup, followed_rules, status FROM trades WHERE 1=1"
    params = []
    if symbol:
        query += " AND symbol=?"; params.append(symbol.upper())
    if status:
        query += " AND status=?"; params.append(status)
    query += " ORDER BY date DESC LIMIT ?"
    params.append(last)
    c.execute(query, params)
    rows = c.fetchall()
    print(f"\n{'ID':>4} {'Date':>10} {'Dir':>5} {'Sym':>6} {'Entry':>8} {'Exit':>8} {'P&L':>8} {'R':>5} {'Setup':>15} {'Rules':>5}")
    print("-" * 85)
    for r in rows:
        pnl_str = f"${r[6]:+.2f}" if r[6] else "  open"
        r_str = f"{r[7]:+.2f}" if r[7] else ""
        rules = "✅" if r[9] else "❌"
        print(f"{r[0]:>4} {r[1]:>10} {r[3]:>5} {r[2]:>6} {r[4]:>8.2f} {str(r[5] or ''):>8} {pnl_str:>8} {r_str:>5} {(r[8] or ''):>15} {rules:>5}")
    conn.close()


def show_performance(period="all"):
    conn = get_conn()
    c = conn.cursor()
    where = "WHERE status='closed'"
    if period == "today":
        where += f" AND date='{fmt_date()}'"
    elif period == "week":
        where += " AND date >= date('now', '-7 days')"
    elif period == "month":
        where += " AND date >= date('now', '-30 days')"

    c.execute(f"""SELECT COUNT(*), SUM(CASE WHEN pnl>0 THEN 1 ELSE 0 END),
                         SUM(pnl), AVG(pnl), AVG(pnl_r),
                         MAX(pnl), MIN(pnl), AVG(followed_rules)
                  FROM trades {where}""")
    row = c.fetchone()
    if not row or not row[0]:
        print("No closed trades found for this period.")
        conn.close()
        return

    total, wins, total_pnl, avg_pnl, avg_r, best, worst, rule_pct = row
    losses = total - (wins or 0)
    wr = ((wins or 0) / total * 100) if total > 0 else 0

    print(f"\n📈 PERFORMANCE ({period.upper()})")
    print(f"  Total Trades:   {total}")
    print(f"  Wins / Losses:  {wins} / {losses}  (WR: {wr:.1f}%)")
    print(f"  Total P&L:      ${(total_pnl or 0):+.2f}")
    print(f"  Avg P&L:        ${(avg_pnl or 0):+.2f}")
    print(f"  Avg R:          {(avg_r or 0):+.2f}R")
    print(f"  Best Trade:     ${(best or 0):+.2f}")
    print(f"  Worst Trade:    ${(worst or 0):+.2f}")
    print(f"  Rules Followed: {(rule_pct or 0)*100:.0f}%")
    conn.close()


# ─────────────────────────────────────────────
# WATCHLIST
# ─────────────────────────────────────────────
def show_watchlist():
    conn = get_conn()
    c = conn.cursor()
    c.execute("""SELECT symbol, market, thesis, target_entry, priority, notes, added_at
                 FROM watchlist WHERE is_active=1 ORDER BY priority ASC, added_at DESC""")
    rows = c.fetchall()
    prio_map = {1: "🔴 HIGH", 2: "🟡 MED ", 3: "⚪ LOW "}
    print(f"\n👀 ACTIVE WATCHLIST ({len(rows)} symbols)")
    for r in rows:
        print(f"\n  {prio_map.get(r[4], '?')} {r[0]} [{r[1] or 'equity'}]")
        print(f"  Thesis:  {r[2] or 'N/A'}")
        print(f"  Entry:   {r[3] or 'TBD'} | Added: {r[6][:10]}")
        if r[5]: print(f"  Notes:   {r[5]}")
    conn.close()


def add_watch(symbol, thesis, market="equity", entry=None, priority=2, notes=None):
    conn = get_conn()
    c = conn.cursor()
    try:
        c.execute("""INSERT INTO watchlist (symbol, market, thesis, target_entry, priority, notes)
                     VALUES (?,?,?,?,?,?)""",
                  (symbol.upper(), market, thesis, entry, int(priority), notes))
        conn.commit()
        print(f"✅ Added {symbol.upper()} to watchlist")
    except sqlite3.IntegrityError:
        c.execute("UPDATE watchlist SET thesis=?, target_entry=?, is_active=1 WHERE symbol=?",
                  (thesis, entry, symbol.upper()))
        conn.commit()
        print(f"✅ Updated {symbol.upper()} in watchlist")
    conn.close()


def remove_watch(symbol):
    conn = get_conn()
    c = conn.cursor()
    c.execute("UPDATE watchlist SET is_active=0 WHERE symbol=?", (symbol.upper(),))
    conn.commit()
    conn.close()
    print(f"✅ Removed {symbol.upper()} from watchlist")


# ─────────────────────────────────────────────
# RESEARCH NOTES
# ─────────────────────────────────────────────
def add_research(title, content, category="general", instrument=None, conviction="MEDIUM", timeframe=None, tags=None):
    conn = get_conn()
    c = conn.cursor()
    c.execute("""INSERT INTO research (date, title, content, category, instrument, conviction, timeframe_relevant, tags)
                 VALUES (?,?,?,?,?,?,?,?)""",
              (fmt_date(), title, content, category, instrument, conviction.upper(), timeframe, tags))
    conn.commit()
    rid = c.lastrowid
    conn.close()
    print(f"✅ Research note #{rid} saved: {title}")

    # Also save as markdown file
    fname = f"{fmt_date()}-{title[:40].replace(' ', '_').replace('/', '-')}.md"
    fpath = os.path.join(os.path.dirname(__file__), "research", fname)
    with open(fpath, "w") as f:
        f.write(f"# {title}\n")
        f.write(f"**Date:** {fmt_date()} | **Conviction:** {conviction} | **Instrument:** {instrument or 'General'}\n\n")
        f.write(content + "\n")
    print(f"   Saved to: .brain/research/{fname}")


def show_research(active_only=True, instrument=None):
    conn = get_conn()
    c = conn.cursor()
    query = "SELECT id, date, title, category, instrument, conviction FROM research WHERE 1=1"
    params = []
    if active_only:
        query += " AND is_active=1"
    if instrument:
        query += " AND instrument=?"; params.append(instrument.upper())
    query += " ORDER BY created_at DESC LIMIT 20"
    c.execute(query, params)
    rows = c.fetchall()
    conv_icon = {"HIGH": "🔴", "MEDIUM": "🟡", "LOW": "⚪"}
    print(f"\n🔬 RESEARCH NOTES ({len(rows)} {'active' if active_only else 'total'})")
    for r in rows:
        icon = conv_icon.get(r[5], "•")
        print(f"  #{r[0]} {r[1]} {icon} [{r[3]}] {r[2]} | {r[4] or 'General'}")
    conn.close()


# ─────────────────────────────────────────────
# APP DEV TASKS (Embodier Trader)
# ─────────────────────────────────────────────
def add_task(title, description="", priority="medium", feature_area="", files=""):
    conn = get_conn()
    c = conn.cursor()
    c.execute("""INSERT INTO app_tasks (title, description, priority, feature_area, files_affected)
                 VALUES (?,?,?,?,?)""",
              (title, description, priority.lower(), feature_area, files))
    conn.commit()
    tid = c.lastrowid
    conn.close()
    print(f"✅ Task #{tid} added: [{priority.upper()}] {title}")


def update_task(task_id, status, notes=None):
    conn = get_conn()
    c = conn.cursor()
    completed_at = fmt_dt() if status == "done" else None
    c.execute("UPDATE app_tasks SET status=?, completed_at=?, notes=COALESCE(?,notes) WHERE id=?",
              (status, completed_at, notes, int(task_id)))
    conn.commit()
    conn.close()
    print(f"✅ Task #{task_id} → {status}")


def show_tasks(status_filter=None):
    conn = get_conn()
    c = conn.cursor()
    status_list = (status_filter or "backlog,in_progress").split(",")
    placeholders = ",".join("?" * len(status_list))
    c.execute(f"""SELECT id, title, priority, status, feature_area, description
                  FROM app_tasks WHERE status IN ({placeholders})
                  ORDER BY CASE priority WHEN 'critical' THEN 1 WHEN 'high' THEN 2
                           WHEN 'medium' THEN 3 ELSE 4 END, id""", status_list)
    rows = c.fetchall()
    prio_icons = {"critical": "🔴", "high": "🟠", "medium": "🟡", "low": "⚪"}
    status_icons = {"in_progress": "⚡", "backlog": "📋", "done": "✅", "blocked": "🚫"}
    print(f"\n🛠️  APP DEV TASKS ({len(rows)})")
    for r in rows:
        p = prio_icons.get(r[2], "•")
        s = status_icons.get(r[3], "•")
        area = f"[{r[4]}] " if r[4] else ""
        print(f"  #{r[0]:>3} {p} {s} {area}{r[1]}")
        if r[5]: print(f"         → {r[5][:80]}")
    conn.close()


# ─────────────────────────────────────────────
# MARKET LEVELS
# ─────────────────────────────────────────────
def add_level(symbol, price, level_type, description="", timeframe="daily"):
    conn = get_conn()
    c = conn.cursor()
    c.execute("""INSERT INTO market_levels (symbol, level_price, level_type, description, timeframe)
                 VALUES (?,?,?,?,?)""",
              (symbol.upper(), float(price), level_type, description, timeframe))
    conn.commit()
    conn.close()
    print(f"✅ Level added: {symbol.upper()} {level_type} @ {price}")


def show_levels(symbol):
    conn = get_conn()
    c = conn.cursor()
    c.execute("""SELECT level_price, level_type, timeframe, description
                 FROM market_levels WHERE symbol=? AND is_active=1
                 ORDER BY level_price DESC""", (symbol.upper(),))
    rows = c.fetchall()
    print(f"\n📐 KEY LEVELS: {symbol.upper()}")
    for r in rows:
        print(f"  {r[1]:>12} @ {r[0]:>10.4f}  [{r[2]}]  {r[3] or ''}")
    conn.close()


# ─────────────────────────────────────────────
# SEARCH
# ─────────────────────────────────────────────
def search_brain(query):
    conn = get_conn()
    c = conn.cursor()
    q = f"%{query}%"
    print(f"\n🔍 SEARCH: '{query}'\n")

    c.execute("SELECT id, date, symbol, direction, setup, entry_reason FROM trades WHERE symbol LIKE ? OR setup LIKE ? OR entry_reason LIKE ?", (q, q, q))
    trades = c.fetchall()
    if trades:
        print(f"📊 Trades ({len(trades)}):")
        for t in trades: print(f"  #{t[0]} {t[1]} {t[2]} {t[3]} - {t[4]}")

    c.execute("SELECT id, date, title, content FROM research WHERE title LIKE ? OR content LIKE ?", (q, q))
    research = c.fetchall()
    if research:
        print(f"\n🔬 Research ({len(research)}):")
        for r in research: print(f"  #{r[0]} {r[1]} {r[2]}")

    c.execute("SELECT id, title, description FROM app_tasks WHERE title LIKE ? OR description LIKE ?", (q, q))
    tasks = c.fetchall()
    if tasks:
        print(f"\n🛠️  Tasks ({len(tasks)}):")
        for t in tasks: print(f"  #{t[0]} {t[1]}")

    conn.close()


# ─────────────────────────────────────────────
# NEW SESSION LOG
# ─────────────────────────────────────────────
def new_session():
    print("🗓️  NEW SESSION LOG\n")
    date_str = input("Date [today]: ").strip() or fmt_date()
    bias = input("Market bias [LONG/SHORT/NEUTRAL]: ").strip().upper() or "NEUTRAL"
    vix = input("VIX level: ").strip()
    watchlist_str = input("Today's watchlist (comma-separated symbols): ").strip()
    context = input("Market context notes: ").strip()
    levels_json = input("Key levels JSON (or blank): ").strip() or "{}"
    positions_json = input("Open positions JSON (or blank): ").strip() or "[]"

    conn = get_conn()
    c = conn.cursor()
    c.execute("""INSERT INTO sessions (date, daily_bias, vix_level, watchlist, market_context, key_levels, open_positions)
                 VALUES (?,?,?,?,?,?,?)""",
              (date_str, bias, float(vix) if vix else None,
               watchlist_str, context, levels_json, positions_json))
    conn.commit()
    conn.close()

    # Save as markdown
    fname = f"{date_str}-session.md"
    fpath = os.path.join(os.path.dirname(__file__), "sessions", fname)
    with open(fpath, "w") as f:
        f.write(f"# Session: {date_str}\n\n")
        f.write(f"**Bias:** {bias} | **VIX:** {vix or 'N/A'}\n\n")
        f.write(f"**Watchlist:** {watchlist_str}\n\n")
        f.write(f"## Market Context\n{context}\n\n")
        f.write(f"## Key Levels\n```json\n{levels_json}\n```\n")
    print(f"✅ Session logged → .brain/sessions/{fname}")


# ─────────────────────────────────────────────
# CLI ENTRYPOINT
# ─────────────────────────────────────────────
def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return

    cmd = sys.argv[1].lower()
    args = sys.argv[2:]

    if cmd == "session-summary":
        session_summary()

    elif cmd == "new-session":
        new_session()

    elif cmd == "add-trade":
        add_trade_interactive()

    elif cmd == "trades":
        last = 20
        symbol = None
        status = None
        for i, a in enumerate(args):
            if a == "--last" and i+1 < len(args): last = int(args[i+1])
            if a == "--symbol" and i+1 < len(args): symbol = args[i+1]
            if a == "--status" and i+1 < len(args): status = args[i+1]
        show_trades(last=last, symbol=symbol, status=status)

    elif cmd == "performance":
        period = args[0] if args else "all"
        show_performance(period)

    elif cmd == "watchlist":
        show_watchlist()

    elif cmd == "add-watch":
        if len(args) < 2:
            print("Usage: add-watch SYMBOL 'thesis' [--market crypto] [--entry 45000] [--priority 1]")
            return
        sym = args[0]
        thesis = args[1]
        market = "equity"
        entry = None
        priority = 2
        for i, a in enumerate(args):
            if a == "--market" and i+1 < len(args): market = args[i+1]
            if a == "--entry" and i+1 < len(args): entry = args[i+1]
            if a == "--priority" and i+1 < len(args): priority = int(args[i+1])
        add_watch(sym, thesis, market=market, entry=entry, priority=priority)

    elif cmd == "remove-watch":
        if args: remove_watch(args[0])

    elif cmd == "research":
        active = "--all" not in args
        instrument = None
        for i, a in enumerate(args):
            if a == "--instrument" and i+1 < len(args): instrument = args[i+1]
        show_research(active_only=active, instrument=instrument)

    elif cmd == "add-research":
        if len(args) < 2:
            print("Usage: add-research 'title' 'content' [--conviction HIGH] [--category macro] [--instrument BTC]")
            return
        title = args[0]
        content = args[1]
        conviction = "MEDIUM"
        category = "general"
        instrument = None
        for i, a in enumerate(args):
            if a == "--conviction" and i+1 < len(args): conviction = args[i+1]
            if a == "--category" and i+1 < len(args): category = args[i+1]
            if a == "--instrument" and i+1 < len(args): instrument = args[i+1]
        add_research(title, content, category=category, instrument=instrument, conviction=conviction)

    elif cmd == "tasks":
        status = None
        for i, a in enumerate(args):
            if a == "--status" and i+1 < len(args): status = args[i+1]
        show_tasks(status_filter=status)

    elif cmd == "add-task":
        if len(args) < 1:
            print("Usage: add-task 'title' ['description'] [--priority high] [--area scanner]")
            return
        title = args[0]
        desc = args[1] if len(args) > 1 and not args[1].startswith("--") else ""
        priority = "medium"
        area = ""
        for i, a in enumerate(args):
            if a == "--priority" and i+1 < len(args): priority = args[i+1]
            if a == "--area" and i+1 < len(args): area = args[i+1]
        add_task(title, description=desc, priority=priority, feature_area=area)

    elif cmd == "update-task":
        if len(args) < 2:
            print("Usage: update-task ID status [notes]")
            return
        notes = args[2] if len(args) > 2 else None
        update_task(args[0], args[1], notes=notes)

    elif cmd == "levels":
        if args: show_levels(args[0])

    elif cmd == "add-level":
        if len(args) < 3:
            print("Usage: add-level SYMBOL price type ['description'] [--tf daily]")
            return
        desc = args[3] if len(args) > 3 else ""
        tf = "daily"
        for i, a in enumerate(args):
            if a == "--tf" and i+1 < len(args): tf = args[i+1]
        add_level(args[0], args[1], args[2], description=desc, timeframe=tf)

    elif cmd == "search":
        if args: search_brain(" ".join(args))

    else:
        print(f"Unknown command: {cmd}")
        print(__doc__)


if __name__ == "__main__":
    main()
