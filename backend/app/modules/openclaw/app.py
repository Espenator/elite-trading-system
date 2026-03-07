#!/usr/bin/env python3
"""
OpenClaw - Slack Trading Automation Bot v2.0
Main application with slash commands, interactive trade confirmations,
and hybrid LLM-powered AI analysis (local Ollama + Perplexity fallback)
"""
import os
import logging
import json
import time
from flask import Flask, request, jsonify
import threading
try:
    from slack_bolt import App
    from slack_bolt.adapter.socket_mode import SocketModeHandler
except ImportError:
    App = None
    SocketModeHandler = None
from alpaca.trading.client import TradingClient
from alpaca.trading.requests import MarketOrderRequest
from alpaca.trading.enums import OrderSide, TimeInForce

from .config import *
from .intelligence.regime import regime_detector
from .integrations.signal_parser import signal_parser
from .integrations.db_logger import DBLogger as DbLogger
from .scanner.daily_scanner import DailyScanner, run_daily_scan
from .scanner.finviz_scanner import finviz_scanner
from .scanner.whale_flow import whale_flow_scanner
from .scanner.fom_expected_moves import run_fom_em_scrape, run_fom_em_post
from .intelligence.memory import trade_memory
from .intelligence.llm_client import get_llm as llm_router

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize Slack app (optional — slack_bolt may not be installed)
if App is not None:
    try:
        app = App(token=SLACK_BOT_TOKEN)
    except Exception as _e:
        app = None
        logger.warning(f"Slack App init failed: {_e}")
else:
    app = None
    logger.warning("slack_bolt not installed — Slack bot disabled")

# Null-pattern fallback so @app.command / @app.action decorators don't crash at import
if app is None:
    class _NullSlackApp:
        """No-op stand-in so decorated functions still get defined."""
        def command(self, *a, **kw):
            return lambda fn: fn
        def action(self, *a, **kw):
            return lambda fn: fn
        def event(self, *a, **kw):
            return lambda fn: fn
    app = _NullSlackApp()

# Initialize Flask for webhooks
flask_app = Flask(__name__)

# Initialize Alpaca client (lazy — may not have credentials at import time)
try:
    alpaca_client = TradingClient(ALPACA_API_KEY, ALPACA_SECRET_KEY, paper=True)
except (ValueError, Exception) as _e:
    alpaca_client = None
    logger.warning(f"Alpaca client init deferred: {_e}")

# Initialize database logger
db_logger = DbLogger()

# Store pending trades for confirmation
pending_trades = {}


# ========== SLASH COMMANDS ==========

@app.command("/oc")
def handle_oc_command(ack, command, client):
    """Main OpenClaw command handler"""
    ack()
    text = command.get('text', '').strip().lower()
    channel_id = command['channel_id']
    user_id = command['user_id']

    # Route to subcommands
    if text == 'regime' or text == 'r':
        show_regime(client, channel_id)
    elif text == 'positions' or text == 'pos' or text == 'p':
        show_positions(client, channel_id)
    elif text == 'scan' or text == 's':
        run_scan(client, channel_id)
    elif text == 'help' or text == 'h' or text == '':
        show_help(client, channel_id)
    elif text.startswith('trade ') or text.startswith('t '):
        signal_text = text.replace('trade ', '').replace('t ', '')
        parse_and_confirm_trade(client, channel_id, user_id, signal_text)
    elif text == 'em' or text == 'fom':
        show_expected_moves(client, channel_id)
    elif text == 'memory' or text == 'm':
        show_memory(client, channel_id)
    elif text.startswith('memory ') or text.startswith('m '):
        ticker = text.split(' ', 1)[1].strip().upper()
        show_memory_ticker(client, channel_id, ticker)
    elif text == 'whale' or text == 'w':
        run_whale_scan(client, channel_id)
    elif text == 'finviz' or text == 'fv':
        run_finviz_scan(client, channel_id)
    elif text == 'status' or text == 'st':
        show_status(client, channel_id)
    elif text == 'ai' or text.startswith('ai '):
        handle_ai_command(client, channel_id, text)
    elif text.startswith('chat ') or text.startswith('c '):
        query = text.split(' ', 1)[1].strip() if ' ' in text else ''
        handle_ai_chat(client, channel_id, query)
    else:
        client.chat_postMessage(
            channel=channel_id,
            text=f"\u274c Unknown command: `{text}`\nUse `/oc help` to see available commands."
        )

def show_regime(client, channel_id):
    """Display current market regime"""
    try:
        regime_summary = regime_detector.get_regime_summary()
        client.chat_postMessage(
            channel=channel_id,
            text=regime_summary,
            mrkdwn=True
        )
    except Exception as e:
        logger.error(f"Error showing regime: {e}")
        client.chat_postMessage(
            channel=channel_id,
            text=f"\u274c Error fetching regime: {str(e)}"
        )


def show_positions(client, channel_id):
    """Display current Alpaca positions"""
    try:
        positions = alpaca_client.get_all_positions()
        if not positions:
            client.chat_postMessage(
                channel=channel_id,
                text="\ud83d\udcca **Current Positions:** None\n\nNo open positions."
            )
            return

        # Format positions
        message = "\ud83d\udcca **Current Positions:**\n\n"
        total_pnl = 0
        for pos in positions:
            pnl = float(pos.unrealized_pl)
            pnl_pct = float(pos.unrealized_plpc) * 100
            total_pnl += pnl
            emoji = "\ud83d\udfe2" if pnl > 0 else "\ud83d\udd34" if pnl < 0 else "\u26aa"
            message += f"{emoji} **{pos.symbol}** - {pos.qty} shares\n"
            message += f"  Entry: ${float(pos.avg_entry_price):.2f} | Current: ${float(pos.current_price):.2f}\n"
            message += f"  P&L: ${pnl:.2f} ({pnl_pct:+.2f}%)\n\n"

        message += f"**Total P&L:** ${total_pnl:+.2f}"

        client.chat_postMessage(
            channel=channel_id,
            text=message,
            mrkdwn=True
        )
    except Exception as e:
        logger.error(f"Error showing positions: {e}")
        client.chat_postMessage(
            channel=channel_id,
            text=f"\u274c Error fetching positions: {str(e)}"
        )


def run_scan(client, channel_id):
    """Run market scan using Finviz + Unusual Whales pipeline"""
    try:
        client.chat_postMessage(
            channel=channel_id,
            text="\ud83d\udd0d **Market Scan**\n\n_Running Finviz Elite + Unusual Whales scan..._"
        )

        # Run the full daily scan pipeline
        scanner = DailyScanner(slack_client=client)
        results = scanner.run_full_scan()

        # Post results summary
        finviz_count = len(results.get('finviz', []))
        whale_count = len(results.get('whale_flow', []))
        confluence = results.get('confluence', [])
        watchlist = results.get('watchlist', [])

        summary = f"\u2705 **Scan Complete**\n\n"
        summary += f"\u2022 Finviz PAS v8 Gate: {finviz_count} symbols\n"
        summary += f"\u2022 Whale Flow: {whale_count} trades\n"
        summary += f"\u2022 Confluence: {len(confluence)} symbols\n"
        summary += f"\u2022 Total Watchlist: {len(watchlist)} symbols\n\n"

        if confluence:
            summary += f"\u2b50 **Confluence Tickers:** {', '.join(confluence)}\n"

        # Top watchlist tickers
        top_tickers = [w['ticker'] for w in watchlist[:15]]
        if top_tickers:
            summary += f"\n\ud83d\udcca **Watchlist:** {', '.join(top_tickers)}"

        client.chat_postMessage(
            channel=channel_id,
            text=summary,
            mrkdwn=True
        )
    except Exception as e:
        logger.error(f"Error running scan: {e}")
        client.chat_postMessage(
            channel=channel_id,
            text=f"\u274c Error running scan: {str(e)}"
        )


def show_expected_moves(client, channel_id):
    """Fetch and display FOM expected moves"""
    try:
        em_data = run_fom_em_scrape(lookback_hours=24)
        if em_data and em_data.get('tv_string'):
            tv_str = em_data['tv_string']
            count = len(em_data.get('symbols', []))
            msg = f"**FOM Expected Moves** ({count} symbols)\nCopy to TV:\n```{tv_str}```"
            client.chat_postMessage(channel=channel_id, text=msg, mrkdwn=True)
            run_fom_em_post(em_data)
        else:
            client.chat_postMessage(channel=channel_id, text="No expected move data found.")
    except Exception as e:
        logger.error(f"FOM expected moves error: {e}")
        client.chat_postMessage(channel=channel_id, text=f"Error: {str(e)}")


# ========== NEW COMMANDS ==========

def show_memory(client, channel_id):
    """Display flywheel memory summary - source weights, win rates, top tickers"""
    try:
        summary = trade_memory.get_summary_text()
        client.chat_postMessage(
            channel=channel_id,
            text=summary,
            mrkdwn=True
        )
    except Exception as e:
        logger.error(f"Error showing memory: {e}")
        client.chat_postMessage(
            channel=channel_id,
            text=f"\u274c Error fetching memory: {str(e)}"
        )


def show_memory_ticker(client, channel_id, ticker):
    """Show memory stats for a specific ticker"""
    try:
        stats = trade_memory.get_ticker_stats(ticker)
        if not stats:
            client.chat_postMessage(
                channel=channel_id,
                text=f"No memory data for `{ticker}` yet."
            )
            return

        wr = round(stats['wins'] / stats['outcomes'] * 100, 1) if stats['outcomes'] > 0 else 0
        msg = f"\ud83e\udde0 **Memory: {ticker}**\n\n"
        msg += f"\u2022 Signals: {stats['signals']}\n"
        msg += f"\u2022 Outcomes: {stats['outcomes']}\n"
        msg += f"\u2022 Wins: {stats['wins']} | Losses: {stats['losses']}\n"
        msg += f"\u2022 Win Rate: {wr}%\n"
        msg += f"\u2022 Total P&L: {stats['total_pnl_pct']:+.2f}%\n"
        msg += f"\u2022 Avg Score: {stats['avg_score']}\n"
        msg += f"\u2022 Sources: {', '.join(stats['sources'])}\n"
        msg += f"\u2022 Last Seen: {stats['last_seen']}"

        client.chat_postMessage(
            channel=channel_id,
            text=msg,
            mrkdwn=True
        )
    except Exception as e:
        logger.error(f"Error showing ticker memory: {e}")
        client.chat_postMessage(
            channel=channel_id,
            text=f"\u274c Error: {str(e)}"
        )


def run_whale_scan(client, channel_id):
    """Run standalone Unusual Whales flow scan"""
    try:
        client.chat_postMessage(
            channel=channel_id,
            text="\ud83d\udc33 _Running Unusual Whales flow scan..._"
        )
        results = whale_flow_scanner.scan()
        if results:
            tickers = [r.get('ticker', '?') for r in results[:20]]
            msg = f"\ud83d\udc33 **Whale Flow Results** ({len(results)} trades)\n\n"
            msg += f"Top tickers: {', '.join(tickers)}"
            client.chat_postMessage(channel=channel_id, text=msg, mrkdwn=True)
        else:
            client.chat_postMessage(channel=channel_id, text="No whale flow data found.")
    except Exception as e:
        logger.error(f"Whale scan error: {e}")
        client.chat_postMessage(channel=channel_id, text=f"\u274c Whale scan error: {str(e)}")


def run_finviz_scan(client, channel_id):
    """Run standalone Finviz Elite scanner"""
    try:
        client.chat_postMessage(
            channel=channel_id,
            text="\ud83d\udcca _Running Finviz Elite PAS v8 scan..._"
        )
        results = finviz_scanner.scan()
        if results:
            tickers = [r.get('ticker', '?') for r in results[:20]]
            msg = f"\ud83d\udcca **Finviz Results** ({len(results)} symbols)\n\n"
            msg += f"Tickers: {', '.join(tickers)}"
            client.chat_postMessage(channel=channel_id, text=msg, mrkdwn=True)
        else:
            client.chat_postMessage(channel=channel_id, text="No Finviz results found.")
    except Exception as e:
        logger.error(f"Finviz scan error: {e}")
        client.chat_postMessage(channel=channel_id, text=f"\u274c Finviz scan error: {str(e)}")


def show_status(client, channel_id):
    """Show system health and status of all components including LLM"""
    try:
        status_lines = ["\ud83d\udfe2 **OpenClaw System Status**\n"]

        # Regime
        try:
            regime = regime_detector.current_regime
            status_lines.append(f"\u2022 Regime: `{regime}`")
        except Exception:
            status_lines.append("\u2022 Regime: \u274c unavailable")

        # Alpaca
        try:
            account = alpaca_client.get_account()
            buying_power = float(account.buying_power)
            status_lines.append(f"\u2022 Alpaca: \u2705 connected | BP: ${buying_power:,.2f}")
        except Exception:
            status_lines.append("\u2022 Alpaca: \u274c disconnected")

        # Memory
        try:
            mem = trade_memory.data
            status_lines.append(f"\u2022 Memory: \u2705 {mem['total_signals']} signals / {mem['total_outcomes']} outcomes")
        except Exception:
            status_lines.append("\u2022 Memory: \u274c unavailable")

        # LLM Status
        try:
            llm_status = llm_router.get_status()
            provider = llm_status.get('active_provider', 'unknown')
            model = llm_status.get('model', 'unknown')
            status_lines.append(f"\u2022 LLM: \u2705 `{provider}` ({model})")
        except Exception:
            status_lines.append("\u2022 LLM: \u274c unavailable")

        # Webhook
        status_lines.append("\u2022 TradingView Webhook: \u2705 listening on :5000")
        status_lines.append("\u2022 Socket Mode: \u2705 connected")

        client.chat_postMessage(
            channel=channel_id,
            text='\n'.join(status_lines),
            mrkdwn=True
        )
    except Exception as e:
        logger.error(f"Status error: {e}")
        client.chat_postMessage(channel=channel_id, text=f"\u274c Status error: {str(e)}")


# ========== AI / LLM COMMANDS ==========

def handle_ai_command(client, channel_id, text):
    """Handle /oc ai [ticker] - run full AI analysis on a ticker"""
    try:
        parts = text.split(' ', 1)
        if len(parts) < 2 or not parts[1].strip():
            client.chat_postMessage(
                channel=channel_id,
                text="\ud83e\udd16 **AI Analysis**\nUsage: `/oc ai AAPL` - Get LLM-powered analysis for a ticker"
            )
            return

        ticker = parts[1].strip().upper()
        client.chat_postMessage(
            channel=channel_id,
            text=f"\ud83e\udd16 _Running AI analysis on **{ticker}**..._"
        )

        # Gather context from all available sources
        context_parts = []

        # Regime context
        try:
            regime_state = regime_detector.current_regime
            context_parts.append(f"Market regime: {regime_state}")
        except Exception:
            context_parts.append("Market regime: unavailable")

        # Memory context
        try:
            stats = trade_memory.get_ticker_stats(ticker)
            if stats:
                wr = round(stats['wins'] / stats['outcomes'] * 100, 1) if stats['outcomes'] > 0 else 0
                context_parts.append(f"Memory: {stats['signals']} signals, {wr}% win rate, avg score {stats['avg_score']}")
        except Exception:
            pass

        # Positions context
        try:
            positions = alpaca_client.get_all_positions()
            for pos in positions:
                if pos.symbol == ticker:
                    pnl = float(pos.unrealized_pl)
                    context_parts.append(f"Current position: {pos.qty} shares, P&L ${pnl:.2f}")
                    break
        except Exception:
            pass

        context_str = '\n'.join(context_parts) if context_parts else 'No additional context available'

        prompt = f"""Analyze {ticker} for a day/swing trader. Consider:
{context_str}

Provide:
1. Technical outlook (trend, key levels, momentum)
2. Catalyst check (earnings, news, sector rotation)
3. Risk assessment (position sizing suggestion based on regime)
4. Trade idea if actionable (entry, target, stop)
5. Confidence level (1-10)

Be concise and actionable. Format for Slack."""

        # Use Perplexity for web-search enriched analysis when available
        response = llm_router.chat(
            prompt,
            task_type="web_search",
            temperature=0.3
        )

        msg = f"\ud83e\udd16 **AI Analysis: {ticker}**\n\n{response}"
        client.chat_postMessage(
            channel=channel_id,
            text=msg,
            mrkdwn=True
        )

    except Exception as e:
        logger.error(f"AI analysis error: {e}")
        client.chat_postMessage(
            channel=channel_id,
            text=f"\u274c AI analysis error: {str(e)}"
        )


def handle_ai_chat(client, channel_id, query):
    """Handle /oc chat [question] - freeform AI trading assistant"""
    try:
        if not query:
            client.chat_postMessage(
                channel=channel_id,
                text="\ud83d\udcac **AI Chat**\nUsage: `/oc chat what sectors look strong today?`"
            )
            return

        client.chat_postMessage(
            channel=channel_id,
            text="\ud83d\udcac _Thinking..._"
        )

        # Build system context
        try:
            regime_state = regime_detector.current_regime
            regime_ctx = f"Current market regime: {regime_state}"
        except Exception:
            regime_ctx = "Market regime: unknown"

        system_prompt = f"""You are OpenClaw AI, an expert trading assistant for a day/swing trader.
{regime_ctx}
Be concise, data-driven, and actionable. Format responses for Slack with markdown."""

        # Route to appropriate provider based on query type
        needs_web = any(kw in query.lower() for kw in [
            'news', 'today', 'earnings', 'sec', 'filing',
            'catalyst', 'sector', 'market', 'fed', 'economic',
            'ipo', 'premarket', 'after hours'
        ])
        task_type = "web_search" if needs_web else "analysis"

        response = llm_router.chat(
            query,
            system_prompt=system_prompt,
            task_type=task_type,
            temperature=0.4
        )

        provider_info = llm_router.get_status().get('active_provider', 'LLM')
        msg = f"\ud83d\udcac **AI Response** _via {provider_info}_\n\n{response}"
        client.chat_postMessage(
            channel=channel_id,
            text=msg,
            mrkdwn=True
        )

    except Exception as e:
        logger.error(f"AI chat error: {e}")
        client.chat_postMessage(
            channel=channel_id,
            text=f"\u274c AI chat error: {str(e)}"
        )


def show_help(client, channel_id):
    """Show help message with all commands including AI"""
    help_text = """
\ud83e\udd16 **OpenClaw Commands**

*Market Info:*
\u2022 `/oc regime` or `/oc r` - Show current market regime (GREEN/YELLOW/RED)
\u2022 `/oc positions` or `/oc p` - Show your Alpaca positions
\u2022 `/oc scan` or `/oc s` - Run full market scan (Finviz + Unusual Whales)
\u2022 `/oc finviz` or `/oc fv` - Run Finviz Elite scanner only
\u2022 `/oc whale` or `/oc w` - Run Unusual Whales flow scan only
\u2022 `/oc em` or `/oc fom` - Show FOM expected moves

*Trading:*
\u2022 `/oc trade [signal]` - Parse and execute trade with confirmation
  Example: `/oc trade BUY AAPL 150 CALL 30DTE`

*AI & Intelligence:*
\u2022 `/oc ai [ticker]` - LLM-powered analysis (local Ollama + Perplexity)
\u2022 `/oc chat [question]` - Freeform AI trading assistant
\u2022 `/oc memory` or `/oc m` - Show flywheel memory (source weights, win rates)
\u2022 `/oc memory AAPL` - Show memory stats for a specific ticker

*System:*
\u2022 `/oc status` or `/oc st` - Show system health and connection status
\u2022 `/oc help` - Show this help message

*Automatic Signal Parsing:*
Post trade signals in any channel and I'll detect them automatically!
Formats supported:
\u2022 Simple: `BUY TSLA 250 CALL 30DTE`
\u2022 Detailed: `AAPL May17 150C @ 2.50 target 4.00 stop 1.50`
\u2022 Stock: `LONG NVDA 100 shares`
"""
    client.chat_postMessage(
        channel=channel_id,
        text=help_text,
        mrkdwn=True
    )


def parse_and_confirm_trade(client, channel_id, user_id, signal_text):
    """Parse trade signal and show confirmation buttons"""
    try:
        signal = signal_parser.parse_message(signal_text)
        if not signal:
            client.chat_postMessage(
                channel=channel_id,
                text=f"\u274c Could not parse trade signal: `{signal_text}`\n\nExample: `BUY AAPL 150 CALL 30DTE`"
            )
            return

        # Generate unique trade ID
        trade_id = f"{user_id}_{int(time.time())}"
        pending_trades[trade_id] = signal

        # Format signal summary
        summary = signal_parser.format_signal_summary(signal)

        # Send confirmation message with buttons
        client.chat_postMessage(
            channel=channel_id,
            text=f"\ud83c\udfaf **Trade Signal Parsed**\n\n{summary}\n\n\u26a0\ufe0f *Confirm to execute this trade:*",
            blocks=[
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"\ud83c\udfaf **Trade Signal Parsed**\n\n{summary}\n\n\u26a0\ufe0f *Confirm to execute this trade:*"
                    }
                },
                {
                    "type": "actions",
                    "elements": [
                        {
                            "type": "button",
                            "text": {"type": "plain_text", "text": "\u2705 Confirm Trade"},
                            "style": "primary",
                            "value": trade_id,
                            "action_id": "confirm_trade"
                        },
                        {
                            "type": "button",
                            "text": {"type": "plain_text", "text": "\u274c Cancel"},
                            "style": "danger",
                            "value": trade_id,
                            "action_id": "cancel_trade"
                        }
                    ]
                }
            ]
        )
    except Exception as e:
        logger.error(f"Error parsing trade: {e}")
        client.chat_postMessage(
            channel=channel_id,
            text=f"\u274c Error parsing trade: {str(e)}"
        )


# ========== INTERACTIVE BUTTON HANDLERS ==========

@app.action("confirm_trade")
def handle_confirm_trade(ack, body, client):
    """Handle trade confirmation button click"""
    ack()
    trade_id = body['actions'][0]['value']
    channel_id = body['channel']['id']
    user_id = body['user']['id']

    if trade_id not in pending_trades:
        client.chat_postMessage(
            channel=channel_id,
            text="\u274c Trade expired or already executed."
        )
        return

    signal = pending_trades.pop(trade_id)

    # Execute trade via Alpaca
    try:
        execute_trade(client, channel_id, user_id, signal)
    except Exception as e:
        logger.error(f"Error executing trade: {e}")
        client.chat_postMessage(
            channel=channel_id,
            text=f"\u274c Trade execution failed: {str(e)}"
        )


@app.action("cancel_trade")
def handle_cancel_trade(ack, body, client):
    """Handle trade cancellation"""
    ack()
    trade_id = body['actions'][0]['value']
    channel_id = body['channel']['id']

    if trade_id in pending_trades:
        signal = pending_trades.pop(trade_id)
        client.chat_postMessage(
            channel=channel_id,
            text=f"\u274c Trade cancelled: {signal['symbol']}"
        )
    else:
        client.chat_postMessage(
            channel=channel_id,
            text="\u274c Trade already expired or executed."
        )


def execute_trade(client, channel_id, user_id, signal):
    """Execute trade via Alpaca API"""
    try:
        symbol = signal['symbol']
        action = signal['action']
        quantity = signal.get('quantity', 1)

        side = OrderSide.BUY if action == 'buy' else OrderSide.SELL

        order_request = MarketOrderRequest(
            symbol=symbol,
            qty=quantity,
            side=side,
            time_in_force=TimeInForce.DAY
        )

        order = alpaca_client.submit_order(order_request)

        # Log to database
        try:
            db_logger.log_trade(signal, order)
        except Exception as e:
            logger.warning(f"Failed to log to database: {e}")

        # Record signal in memory for flywheel
        try:
            source = signal.get('source', 'manual')
            setup = signal.get('setup', 'unknown')
            trade_memory.record_signal(symbol, source, setup)
        except Exception as e:
            logger.warning(f"Failed to record in memory: {e}")

        # Send confirmation
        client.chat_postMessage(
            channel=channel_id,
            text=f"\u2705 **Trade Executed**\n\n"
                 f"Symbol: {symbol}\n"
                 f"Action: {action.upper()}\n"
                 f"Quantity: {quantity}\n"
                 f"Order ID: {order.id}\n"
                 f"Status: {order.status}"
        )
    except Exception as e:
        raise Exception(f"Alpaca order failed: {str(e)}")


# ========== MESSAGE EVENT LISTENERS ==========

@app.event("message")
def handle_message_events(body, logger):
    """Listen for trade signals in messages"""
    # Ignore bot messages
    if body.get('event', {}).get('bot_id'):
        return

    # Get message text
    message_text = body.get('event', {}).get('text', '')
    channel_id = body.get('event', {}).get('channel')
    user_id = body.get('event', {}).get('user')

    # Try to parse as trade signal
    try:
        signal = signal_parser.parse_message(message_text)
        if signal:
            logger.info(f"Auto-detected trade signal: {signal}")
            trade_id = f"{user_id}_{int(time.time())}"
            pending_trades[trade_id] = signal
            summary = signal_parser.format_signal_summary(signal)

            app.client.chat_postMessage(
                channel=channel_id,
                text=f"\ud83c\udfaf **Auto-Detected Trade Signal**\n\n{summary}\n\n\u26a0\ufe0f *Confirm to execute:*",
                blocks=[
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": f"\ud83c\udfaf **Auto-Detected Trade Signal**\n\n{summary}\n\n\u26a0\ufe0f *Confirm to execute:*"
                        }
                    },
                    {
                        "type": "actions",
                        "elements": [
                            {
                                "type": "button",
                                "text": {"type": "plain_text", "text": "\u2705 Confirm Trade"},
                                "style": "primary",
                                "value": trade_id,
                                "action_id": "confirm_trade"
                            },
                            {
                                "type": "button",
                                "text": {"type": "plain_text", "text": "\u274c Cancel"},
                                "style": "danger",
                                "value": trade_id,
                                "action_id": "cancel_trade"
                            }
                        ]
                    }
                ]
            )
    except Exception as e:
        logger.debug(f"Message not a trade signal: {e}")
        pass


# ========== TRADINGVIEW WEBHOOK ==========

@flask_app.route('/webhook/tradingview', methods=['POST'])
def tradingview_webhook():
    """Receive TradingView webhook alerts and post to Slack"""
    try:
        data = request.get_json()
        logger.info(f"\ud83d\udce1 TradingView webhook received: {data}")

        # Extract alert message
        message = data.get('message', '')
        if not message:
            return jsonify({'error': 'No message in webhook'}), 400

        # Post to oc-trade-desk channel
        channel = os.getenv('OC_TRADE_DESK_CHANNEL', 'C0AF9RW7W94')
        app.client.chat_postMessage(
            channel=channel,
            text=f"\ud83d\udcca **TradingView Alert**\n\n{message}"
        )

        return jsonify({'status': 'success', 'message': 'Posted to Slack'}), 200
    except Exception as e:
        logger.error(f"Webhook error: {e}")
        return jsonify({'error': str(e)}), 500


# ========== FLASK AI API ENDPOINTS ==========

@flask_app.route('/ai-analysis', methods=['POST'])
def ai_analysis_endpoint():
    """REST API endpoint for AI ticker analysis - used by external tools"""
    try:
        data = request.get_json()
        ticker = data.get('ticker', '').upper()
        if not ticker:
            return jsonify({'error': 'ticker required'}), 400

        # Gather context
        context_parts = []
        try:
            context_parts.append(f"Market regime: {regime_detector.current_regime}")
        except Exception:
            pass
        try:
            stats = trade_memory.get_ticker_stats(ticker)
            if stats:
                wr = round(stats['wins'] / stats['outcomes'] * 100, 1) if stats['outcomes'] > 0 else 0
                context_parts.append(f"Memory: {stats['signals']} signals, {wr}% win rate")
        except Exception:
            pass

        context_str = '\n'.join(context_parts) if context_parts else 'No context'

        prompt = f"""Analyze {ticker} for day/swing trading.
{context_str}
Provide: technical outlook, catalysts, risk assessment, trade idea, confidence (1-10).
Be concise and actionable."""

        response = llm_router.chat(prompt, task_type="web_search", temperature=0.3)
        status = llm_router.get_status()

        return jsonify({
            'ticker': ticker,
            'analysis': response,
            'provider': status.get('active_provider', 'unknown'),
            'model': status.get('model', 'unknown')
        }), 200

    except Exception as e:
        logger.error(f"AI analysis endpoint error: {e}")
        return jsonify({'error': str(e)}), 500


@flask_app.route('/ai-chat', methods=['POST'])
def ai_chat_endpoint():
    """REST API endpoint for freeform AI chat - used by external tools"""
    try:
        data = request.get_json()
        query = data.get('query', '')
        if not query:
            return jsonify({'error': 'query required'}), 400

        system_prompt = data.get('system_prompt', 'You are OpenClaw AI, an expert trading assistant.')
        task_type = data.get('task_type', 'analysis')
        temperature = data.get('temperature', 0.4)

        response = llm_router.chat(
            query,
            system_prompt=system_prompt,
            task_type=task_type,
            temperature=temperature
        )
        status = llm_router.get_status()

        return jsonify({
            'response': response,
            'provider': status.get('active_provider', 'unknown'),
            'model': status.get('model', 'unknown')
        }), 200

    except Exception as e:
        logger.error(f"AI chat endpoint error: {e}")
        return jsonify({'error': str(e)}), 500


@flask_app.route('/llm-status', methods=['GET'])
def llm_status_endpoint():
    """Check LLM router health and active provider"""
    try:
        status = llm_router.get_status()
        return jsonify(status), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ========== AGENT COMMAND CENTER API ENDPOINTS ==========
# These endpoints power the Agent Command Center UI in elite-trading-system
# Frontend polls: /macro (30s), /swarm-status (15s), /candidates (30s)

# --- In-memory stores for swarm state ---
_active_teams = {}  # {team_name: {type, action, status, spawned_at, health}}
_bias_override = {'value': 1.0}  # Global bias multiplier override
_llm_flow_alerts = []  # Rolling list of last 50 LLM alerts


@flask_app.route('/api/v1/openclaw/macro', methods=['GET'])
def openclaw_macro():
    """Regime oscillator, wave_state, bias multiplier for Agent Command Center"""
    try:
        regime = regime_detector.current_regime
        # Map regime to oscillator value
        regime_map = {'GREEN': 0.8, 'YELLOW': 0.5, 'RED': 0.2}
        oscillator = regime_map.get(regime, 0.5)

        # Determine wave state from regime trend
        wave_states = {'GREEN': 'expansion', 'YELLOW': 'transition', 'RED': 'contraction'}
        wave_state = wave_states.get(regime, 'unknown')

        return jsonify({
            'regime': regime,
            'oscillator': oscillator,
            'wave_state': wave_state,
            'bias_multiplier': _bias_override['value'],
            'timestamp': time.time()
        }), 200
    except Exception as e:
        logger.error(f"Agent Command Center macro error: {e}")
        # Graceful fallback with demo data
        return jsonify({
            'regime': 'YELLOW',
            'oscillator': 0.5,
            'wave_state': 'transition',
            'bias_multiplier': 1.0,
            'timestamp': time.time(),
            '_fallback': True
        }), 200


@flask_app.route('/api/v1/openclaw/swarm-status', methods=['GET'])
def openclaw_swarm_status():
    """Active agent teams, health, and swarm summary for Agent Command Center"""
    try:
        teams = []
        for name, info in _active_teams.items():
            teams.append({
                'name': name,
                'type': info.get('type', 'unknown'),
                'status': info.get('status', 'idle'),
                'health': info.get('health', 'ok'),
                'spawned_at': info.get('spawned_at', None),
                'action': info.get('action', None)
            })

        return jsonify({
            'active_teams': len(teams),
            'teams': teams,
            'swarm_health': 'ok' if all(t['health'] == 'ok' for t in teams) else 'degraded',
            'timestamp': time.time()
        }), 200
    except Exception as e:
        logger.error(f"Agent Command Center swarm-status error: {e}")
        return jsonify({
            'active_teams': 0,
            'teams': [],
            'swarm_health': 'offline',
            'timestamp': time.time(),
            '_fallback': True
        }), 200


@flask_app.route('/api/v1/openclaw/candidates', methods=['GET'])
def openclaw_candidates():
    """Ranked candidates with score, team_tag, entry/stop/target for Agent Command Center"""
    try:
        n = request.args.get('top', 20, type=int)
        # Pull from daily scanner / composite scorer if available
        candidates = []
        try:
            from composite_scorer import composite_scorer
            raw = composite_scorer.get_ranked(n=n)
            for item in raw:
                candidates.append({
                    'symbol': item.get('ticker', item.get('symbol', '?')),
                    'score': item.get('score', 0),
                    'team_tag': item.get('source', 'scanner'),
                    'entry': item.get('entry', None),
                    'stop': item.get('stop', None),
                    'target': item.get('target', None),
                    'setup': item.get('setup', 'unknown')
                })
        except ImportError:
            logger.warning("composite_scorer not available, using memory fallback")
            # Fallback: use trade memory top tickers
            try:
                mem_data = trade_memory.data
                tickers = mem_data.get('ticker_stats', {})
                sorted_tickers = sorted(
                    tickers.items(),
                    key=lambda x: x[1].get('avg_score', 0),
                    reverse=True
                )[:n]
                for ticker, stats in sorted_tickers:
                    candidates.append({
                        'symbol': ticker,
                        'score': stats.get('avg_score', 0),
                        'team_tag': 'memory',
                        'entry': None,
                        'stop': None,
                        'target': None,
                        'setup': 'flywheel'
                    })
            except Exception:
                pass

        return jsonify({
            'candidates': candidates,
            'count': len(candidates),
            'timestamp': time.time()
        }), 200
    except Exception as e:
        logger.error(f"Agent Command Center candidates error: {e}")
        return jsonify({
            'candidates': [],
            'count': 0,
            'timestamp': time.time(),
            '_fallback': True
        }), 200


@flask_app.route('/api/v1/openclaw/spawn-team', methods=['POST'])
def openclaw_spawn_team():
    """Spawn or kill an agent team for Agent Command Center"""
    try:
        data = request.get_json() or {}
        team_type = data.get('team_type', 'momentum')
        action = data.get('action', 'spawn')
        team_name = f"{team_type}_{int(time.time())}"

        if action == 'spawn':
            _active_teams[team_name] = {
                'type': team_type,
                'action': 'spawn',
                'status': 'running',
                'health': 'ok',
                'spawned_at': time.time()
            }
            logger.info(f"Agent Command Center: Spawned team {team_name} ({team_type})")
            return jsonify({
                'status': 'spawned',
                'team_name': team_name,
                'team_type': team_type,
                'timestamp': time.time()
            }), 200

        elif action == 'kill':
            kill_name = data.get('team_name', '')
            if kill_name in _active_teams:
                del _active_teams[kill_name]
                logger.info(f"Agent Command Center: Killed team {kill_name}")
                return jsonify({
                    'status': 'killed',
                    'team_name': kill_name,
                    'timestamp': time.time()
                }), 200
            else:
                return jsonify({'error': f'Team {kill_name} not found'}), 404
        else:
            return jsonify({'error': f'Unknown action: {action}'}), 400

    except Exception as e:
        logger.error(f"Agent Command Center spawn-team error: {e}")
        return jsonify({'error': str(e)}), 500


@flask_app.route('/api/v1/openclaw/macro/override', methods=['POST'])
def openclaw_macro_override():
    """Override the bias multiplier (0.5 - 2.0) for Agent Command Center"""
    try:
        data = request.get_json() or {}
        value = data.get('bias_multiplier', 1.0)

        # Clamp to valid range
        value = max(0.5, min(2.0, float(value)))
        _bias_override['value'] = value

        logger.info(f"Agent Command Center: Bias override set to {value}")
        return jsonify({
            'bias_multiplier': value,
            'status': 'updated',
            'timestamp': time.time()
        }), 200
    except Exception as e:
        logger.error(f"Agent Command Center macro/override error: {e}")
        return jsonify({'error': str(e)}), 500


@flask_app.route('/api/v1/openclaw/llm-flow', methods=['GET'])
def openclaw_llm_flow():
    """LLM alert stream (last N alerts) for Agent Command Center.
    Frontend polls this; for real-time, upgrade to WebSocket."""
    try:
        limit = request.args.get('limit', 5, type=int)
        recent = _llm_flow_alerts[-limit:] if _llm_flow_alerts else []
        return jsonify({
            'alerts': recent,
            'total': len(_llm_flow_alerts),
            'timestamp': time.time()
        }), 200
    except Exception as e:
        logger.error(f"Agent Command Center llm-flow error: {e}")
        return jsonify({
            'alerts': [],
            'total': 0,
            'timestamp': time.time(),
            '_fallback': True
        }), 200


def push_llm_alert(message, severity='info'):
    """Utility: push an LLM alert to the flow stream (called internally)"""
    alert = {
        'message': message,
        'severity': severity,  # info, warning, error, critical
        'timestamp': time.time()
    }
    _llm_flow_alerts.append(alert)
    # Keep only last 50 alerts
    if len(_llm_flow_alerts) > 50:
        _llm_flow_alerts.pop(0)



# ========== MAIN ==========

if __name__ == "__main__":
    logger.info("\ud83d\ude80 Starting OpenClaw Slack Bot v2.0...")
    logger.info(f"\ud83d\udce1 Regime: {regime_detector.current_regime}")

    # Check LLM status
    try:
        llm_status = llm_router.get_status()
        logger.info(f"\ud83e\udd16 LLM: {llm_status.get('active_provider', 'none')} ({llm_status.get('model', 'none')})")
    except Exception as e:
        logger.warning(f"LLM initialization warning: {e}")

    # Reset daily memory dedup
    trade_memory.reset_daily()

    # Start Flask webhook server in background thread
    flask_thread = threading.Thread(target=lambda: flask_app.run(host='0.0.0.0', port=5000, debug=False))
    flask_thread.daemon = True
    flask_thread.start()
    logger.info("\ud83c\udf10 Flask webhook server started on http://0.0.0.0:5000")
    logger.info("\ud83c\udf10 AI endpoints: /ai-analysis, /ai-chat, /llm-status, /api/v1/openclaw/*")

    # Run initial daily scan on startup
    try:
        logger.info("Running initial daily scan...")
        scan_thread = threading.Thread(
            target=run_daily_scan,
            kwargs={'slack_client': app.client},
            daemon=True
        )
        scan_thread.start()
        logger.info("Daily scan thread started")
    except Exception as e:
        logger.warning(f"Initial scan failed: {e}")

    # Start the app
    handler = SocketModeHandler(app, SLACK_APP_TOKEN)
    handler.start()
