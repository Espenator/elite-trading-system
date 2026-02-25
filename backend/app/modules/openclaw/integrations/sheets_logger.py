"""Google Sheets trade logger for OpenClaw.
Logs all signals, trades, veto/confirms, and daily journals to Google Sheets.
"""
import gspread
import json
import os
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
from config import GOOGLE_SHEETS_CREDENTIALS, TRADE_LOG_SHEET_ID


class SheetsLogger:
    SCOPES = [
        "https://spreadsheets.google.com/feeds",
        "https://www.googleapis.com/auth/drive",
    ]

    # Sheet tab names
    TRADE_LOG = "Trade Log"
    SIGNALS = "Signals"
    JOURNAL = "Daily Journal"
    AUDIT = "Audit Trail"

    # Headers for each sheet
    TRADE_HEADERS = [
        "Timestamp", "Ticker", "Action", "Qty", "Entry", "Stop", "Target",
        "Status", "Fill Price", "P&L", "P&L %", "Velez Score", "Regime",
        "Source Channel", "Order ID", "Notes"
    ]
    SIGNAL_HEADERS = [
        "Timestamp", "Ticker", "Action", "Entry", "Stop", "Target",
        "Velez Score", "Quality", "Source Channel", "Source User",
        "Raw Text", "Decision", "Decision Time"
    ]
    JOURNAL_HEADERS = [
        "Date", "Regime", "VIX", "Trades Taken", "Wins", "Losses",
        "Gross P&L", "Net P&L", "Win Rate", "Best Trade", "Worst Trade",
        "Notes"
    ]
    AUDIT_HEADERS = [
        "Timestamp", "Action", "User", "Details", "Channel"
    ]

    def __init__(self):
        self.client = None
        self.spreadsheet = None
        self._connect()

    def _get_credentials(self):
        """Get credentials from JSON string, file path, or credentials.json fallback."""
        creds_value = GOOGLE_SHEETS_CREDENTIALS

        # Strategy 1: If value looks like JSON (starts with {), parse it directly
        if creds_value and creds_value.strip().startswith('{'):
            try:
                creds_dict = json.loads(creds_value)
                return ServiceAccountCredentials.from_json_keyfile_dict(
                    creds_dict, self.SCOPES
                )
            except (json.JSONDecodeError, Exception) as e:
                print(f"Failed to parse credentials JSON string: {e}")

        # Strategy 2: If value is a file path that exists, use it
        if creds_value and os.path.isfile(creds_value):
            return ServiceAccountCredentials.from_json_keyfile_name(
                creds_value, self.SCOPES
            )

        # Strategy 3: Fallback to credentials.json in current directory
        if os.path.isfile('credentials.json'):
            return ServiceAccountCredentials.from_json_keyfile_name(
                'credentials.json', self.SCOPES
            )

        raise FileNotFoundError(
            "No valid Google Sheets credentials found. "
            "Set GOOGLE_SHEETS_CREDENTIALS as JSON string, file path, "
            "or place credentials.json in project root."
        )

    def _connect(self):
        """Connect to Google Sheets API."""
        try:
            creds = self._get_credentials()
            self.client = gspread.authorize(creds)
            if TRADE_LOG_SHEET_ID:
                self.spreadsheet = self.client.open_by_key(TRADE_LOG_SHEET_ID)
            else:
                self.spreadsheet = self._create_spreadsheet()
            self._ensure_sheets()
            print("Google Sheets connected successfully")
        except Exception as e:
            print(f"Google Sheets connection failed: {e}")
            print("Trades will still execute but won't be logged to Sheets.")

    def _create_spreadsheet(self):
        """Create a new spreadsheet if none exists."""
        ss = self.client.create("OpenClaw Trade Log")
        ss.share(None, perm_type="anyone", role="writer")
        print(f"Created new spreadsheet: {ss.url}")
        print(f"Sheet ID: {ss.id}")
        print("Add this ID to your .env as TRADE_LOG_SHEET_ID")
        return ss

    def _ensure_sheets(self):
        """Ensure all required sheet tabs exist with headers."""
        if not self.spreadsheet:
            return
        existing = [ws.title for ws in self.spreadsheet.worksheets()]
        sheets_config = {
            self.TRADE_LOG: self.TRADE_HEADERS,
            self.SIGNALS: self.SIGNAL_HEADERS,
            self.JOURNAL: self.JOURNAL_HEADERS,
            self.AUDIT: self.AUDIT_HEADERS,
        }
        for name, headers in sheets_config.items():
            if name not in existing:
                ws = self.spreadsheet.add_worksheet(title=name, rows=1000, cols=len(headers))
                ws.append_row(headers)
            else:
                ws = self.spreadsheet.worksheet(name)
                if ws.row_count == 0 or ws.row_values(1) != headers:
                    ws.insert_row(headers, 1)

    def log_signal(self, signal):
        """Log a parsed signal to the Signals sheet."""
        if not self.spreadsheet:
            return
        try:
            ws = self.spreadsheet.worksheet(self.SIGNALS)
            row = [
                signal.get("timestamp", datetime.now().isoformat()),
                signal.get("ticker", ""),
                signal.get("action", ""),
                signal.get("entry", ""),
                signal.get("stop", ""),
                signal.get("target", ""),
                signal.get("velez_score", ""),
                signal.get("quality", ""),
                signal.get("source_channel", ""),
                signal.get("source_user", ""),
                signal.get("raw_text", "")[:200],
                "",  # Decision (filled on confirm/veto)
                "",  # Decision time
            ]
            ws.append_row(row)
        except Exception as e:
            print(f"Failed to log signal: {e}")

    def log_trade(self, trade):
        """Log an executed trade to the Trade Log sheet."""
        if not self.spreadsheet:
            return
        try:
            ws = self.spreadsheet.worksheet(self.TRADE_LOG)
            row = [
                trade.get("timestamp", datetime.now().isoformat()),
                trade.get("ticker", ""),
                trade.get("action", ""),
                trade.get("qty", ""),
                trade.get("entry", ""),
                trade.get("stop", ""),
                trade.get("target", ""),
                trade.get("status", ""),
                trade.get("fill_price", ""),
                trade.get("pnl", ""),
                trade.get("pnl_pct", ""),
                trade.get("velez_score", ""),
                trade.get("regime", ""),
                trade.get("source_channel", ""),
                trade.get("order_id", ""),
                trade.get("notes", ""),
            ]
            ws.append_row(row)
        except Exception as e:
            print(f"Failed to log trade: {e}")

    def log_decision(self, signal_ticker, decision, timestamp=None):
        """Update a signal row with the user's decision (CONFIRM/VETO/MODIFY)."""
        if not self.spreadsheet:
            return
        try:
            ws = self.spreadsheet.worksheet(self.SIGNALS)
            cells = ws.findall(signal_ticker)
            if cells:
                last_row = cells[-1].row
                ws.update_cell(last_row, 12, decision)
                ws.update_cell(last_row, 13, timestamp or datetime.now().isoformat())
        except Exception as e:
            print(f"Failed to log decision: {e}")

    def log_audit(self, action, user="system", details="", channel=""):
        """Log an audit trail entry."""
        if not self.spreadsheet:
            return
        try:
            ws = self.spreadsheet.worksheet(self.AUDIT)
            ws.append_row([
                datetime.now().isoformat(),
                action, user, details, channel
            ])
        except Exception as e:
            print(f"Failed to log audit: {e}")

    def log_daily_journal(self, journal_data):
        """Log daily trading journal entry."""
        if not self.spreadsheet:
            return
        try:
            ws = self.spreadsheet.worksheet(self.JOURNAL)
            row = [
                journal_data.get("date", datetime.now().strftime("%Y-%m-%d")),
                journal_data.get("regime", ""),
                journal_data.get("vix", ""),
                journal_data.get("trades_taken", 0),
                journal_data.get("wins", 0),
                journal_data.get("losses", 0),
                journal_data.get("gross_pnl", 0),
                journal_data.get("net_pnl", 0),
                journal_data.get("win_rate", ""),
                journal_data.get("best_trade", ""),
                journal_data.get("worst_trade", ""),
                journal_data.get("notes", ""),
            ]
            ws.append_row(row)
        except Exception as e:
            print(f"Failed to log journal: {e}")

    def get_todays_trades(self):
        """Get all trades from today."""
        if not self.spreadsheet:
            return []
        try:
            ws = self.spreadsheet.worksheet(self.TRADE_LOG)
            records = ws.get_all_records()
            today = datetime.now().strftime("%Y-%m-%d")
            return [r for r in records if r.get("Timestamp", "").startswith(today)]
        except:
            return []

    def get_performance_summary(self, days=30):
        """Get performance summary for last N days."""
        if not self.spreadsheet:
            return {}
        try:
            ws = self.spreadsheet.worksheet(self.TRADE_LOG)
            records = ws.get_all_records()
            if not records:
                return {"total_trades": 0}
            trades = [r for r in records if r.get("Status") == "FILLED"]
            wins = [t for t in trades if float(t.get("P&L", 0) or 0) > 0]
            losses = [t for t in trades if float(t.get("P&L", 0) or 0) < 0]
            total_pnl = sum(float(t.get("P&L", 0) or 0) for t in trades)
            return {
                "total_trades": len(trades),
                "wins": len(wins),
                "losses": len(losses),
                "win_rate": f"{len(wins)/len(trades)*100:.1f}%" if trades else "0%",
                "total_pnl": round(total_pnl, 2),
                "avg_pnl": round(total_pnl / len(trades), 2) if trades else 0,
            }
        except:
            return {"error": "Could not retrieve performance data"}


# Singleton
sheets = SheetsLogger()
sheets_logger = sheets
