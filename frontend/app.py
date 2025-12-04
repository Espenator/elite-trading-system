"""
Elite Trading System - Main Dashboard
Streamlit UI for monitoring and control
"""

import streamlit as st
import pandas as pd
import requests
from datetime import datetime
import time
import yaml
import os

# Page config
st.set_page_config(
    page_title="Elite Trading System",
    page_icon="🚀",
    layout="wide",
    initial_sidebar_state="expanded"
)

# API base URL
API_URL = "http://localhost:8000"

# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def get_system_status():
    """Get system status from API"""
    try:
        response = requests.get(f"{API_URL}/api/status", timeout=5)
        return response.json()
    except:
        return None

def get_signals(direction=None):
    """Get current signals"""
    try:
        url = f"{API_URL}/api/signals"
        if direction:
            url += f"?direction={direction}"
        response = requests.get(url, timeout=5)
        return response.json()
    except:
        return []

def get_positions():
    """Get open positions"""
    try:
        response = requests.get(f"{API_URL}/api/positions", timeout=5)
        return response.json()
    except:
        return []

def approve_trade(symbol, approved, notes=""):
    """Approve or reject a trade"""
    try:
        response = requests.post(
            f"{API_URL}/api/approve_trade",
            json={"symbol": symbol, "approved": approved, "notes": notes},
            timeout=5
        )
        return response.json()
    except Exception as e:
        return {"error": str(e)}

def force_scan():
    """Force an immediate scan"""
    try:
        response = requests.post(f"{API_URL}/api/scan/force", timeout=5)
        return response.json()
    except Exception as e:
        return {"error": str(e)}

# =============================================================================
# MAIN APP
# =============================================================================

def main():
    # Header
    st.title("🚀 Elite Trading System")
    st.caption("AI-Powered Paper Trading Dashboard")
    
    # Sidebar
    with st.sidebar:
        st.header("⚙️ Control Panel")
        
        # System status
        status = get_system_status()
        
        if status:
            if status['is_scanning']:
                st.info("🔍 Scanning in progress...")
            else:
                st.success("✅ System Online")
            
            st.metric("Active Positions", status['active_positions'])
            st.metric("Pending Signals", status['pending_signals'])
            
            if status['last_scan_time']:
                scan_time = datetime.fromisoformat(status['last_scan_time'])
                st.caption(f"Last scan: {scan_time.strftime('%I:%M %p')}")
        else:
            st.error("❌ Backend Offline")
            st.caption("Run: python run.py")
        
        st.divider()
        
        # Actions
        st.subheader("Actions")
        
        if st.button("🔍 Force Scan", use_container_width=True):
            with st.spinner("Scanning..."):
                result = force_scan()
                if 'error' in result:
                    st.error(result['error'])
                else:
                    st.success("Scan initiated!")
                    time.sleep(2)
                    st.rerun()
        
        if st.button("⏸️ Pause System", use_container_width=True):
            st.warning("System paused")
        
        if st.button("▶️ Resume System", use_container_width=True):
            st.success("System resumed")
        
        st.divider()
        
        # Settings summary
        st.subheader("Quick Info")
        if status:
            config = status['config']
            st.caption(f"Trading Style: {config['trading_style']}")
            st.caption(f"AI Trust: {config['ai_trust_level']}%")
            st.caption(f"Max Positions: {config['max_positions']}")
    
    # Main content tabs
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "📊 Signals",
        "💼 Positions",
        "📈 Performance",
        "🤖 AI Insights",
        "⚙️ Settings"
    ])
    
    # TAB 1: SIGNALS
    with tab1:
        st.header("📊 Top Signals (Awaiting Approval)")
        
        # Filter
        col1, col2 = st.columns([1, 3])
        with col1:
            filter_direction = st.selectbox("Filter", ["All", "LONG", "SHORT"])
        
        # Get signals
        signals = get_signals(
            direction=filter_direction if filter_direction != "All" else None
        )
        
        if not signals:
            st.info("No signals found. Run a scan to find opportunities.")
        else:
            # Display signals in grid
            for i, signal in enumerate(signals[:20]):  # Show top 20
                with st.expander(
                    f"{signal['symbol']} ({signal['direction']}) - Score: {signal['score']:.1f}",
                    expanded=(i < 3)  # Expand top 3
                ):
                    col1, col2, col3, col4 = st.columns(4)
                    
                    with col1:
                        st.metric("Composite Score", f"{signal['score']:.1f}")
                        st.metric("Velez Score", f"{signal['velez_score']['composite']:.1f}")
                    
                    with col2:
                        st.metric("Entry Price", f"${signal['entry_price']:.2f}")
                        st.metric("Stop Loss", f"${signal['stop_price']:.2f}")
                    
                    with col3:
                        st.metric("Target", f"${signal['target_price']:.2f}")
                        r_ratio = abs((signal['target_price'] - signal['entry_price']) / 
                                     (signal['entry_price'] - signal['stop_price']))
                        st.metric("R:R Ratio", f"{r_ratio:.1f}:1")
                    
                    with col4:
                        explosive = "✅ Yes" if signal['explosive_signal'] else "❌ No"
                        st.metric("Explosive", explosive)
                        fresh_mins = signal['fresh_ignition']['minutes_since_breakout']
                        st.metric("Fresh", f"{fresh_mins} min ago")
                    
                    st.divider()
                    
                    # Approval buttons
                    col1, col2, col3 = st.columns([1, 1, 2])
                    
                    with col1:
                        if st.button("✅ Approve", key=f"approve_{signal['symbol']}", 
                                   use_container_width=True):
                            result = approve_trade(signal['symbol'], True)
                            if 'error' not in result:
                                st.success(f"Approved {signal['symbol']}!")
                                time.sleep(1)
                                st.rerun()
                    
                    with col2:
                        if st.button("❌ Reject", key=f"reject_{signal['symbol']}", 
                                   use_container_width=True):
                            result = approve_trade(signal['symbol'], False)
                            if 'error' not in result:
                                st.info(f"Rejected {signal['symbol']}")
                                time.sleep(1)
                                st.rerun()
    
    # TAB 2: POSITIONS
    with tab2:
        st.header("💼 Open Positions")
        
        positions = get_positions()
        
        if not positions:
            st.info("No open positions")
        else:
            # Summary metrics
            col1, col2, col3, col4 = st.columns(4)
            
            total_pnl = sum(p['unrealized_pnl'] for p in positions)
            avg_r = sum(p['r_multiple'] for p in positions) / len(positions)
            
            with col1:
                st.metric("Total P&L", f"${total_pnl:,.0f}")
            with col2:
                st.metric("Positions", len(positions))
            with col3:
                st.metric("Avg R-Multiple", f"{avg_r:.2f}R")
            with col4:
                winners = sum(1 for p in positions if p['unrealized_pnl'] > 0)
                st.metric("Winners", f"{winners}/{len(positions)}")
            
            st.divider()
            
            # Position table
            df = pd.DataFrame(positions)
            
            # Format columns
            df['entry_price'] = df['entry_price'].apply(lambda x: f"${x:.2f}")
            df['current_price'] = df['current_price'].apply(lambda x: f"${x:.2f}")
            df['stop_loss'] = df['stop_loss'].apply(lambda x: f"${x:.2f}")
            df['unrealized_pnl'] = df['unrealized_pnl'].apply(lambda x: f"${x:,.0f}")
            df['r_multiple'] = df['r_multiple'].apply(lambda x: f"{x:.2f}R")
            
            st.dataframe(
                df[['symbol', 'direction', 'shares', 'entry_price', 'current_price', 
                    'stop_loss', 'unrealized_pnl', 'r_multiple']],
                use_container_width=True
            )
    
    # TAB 3: PERFORMANCE
    with tab3:
        st.header("📈 Performance Metrics")
        st.info("Coming soon: Charts, equity curve, trade history")
    
    # TAB 4: AI INSIGHTS
    with tab4:
        st.header("🤖 AI Learning Insights")
        st.info("Coming soon: AI discoveries, pattern analysis, optimization results")
    
    # TAB 5: SETTINGS (NEW!)
    with tab5:
        st.header("⚙️ System Settings")
        
        # Load current config
        try:
            with open('config.yaml') as f:
                config = yaml.safe_load(f)
        except:
            st.error("Could not load config.yaml")
            return
        
        # Load .env
        from dotenv import load_dotenv
        load_dotenv()
        
        # User Preferences Section
        st.subheader("👤 Trading Preferences")
        
        col1, col2 = st.columns(2)
        
        with col1:
            trading_style = st.selectbox(
                "Trading Style",
                ['scalper', 'balanced', 'swing'],
                index=['scalper', 'balanced', 'swing'].index(
                    config['user_preferences']['trading_style']
                ),
                help="Scalper: 15-30min | Balanced: 1-3hr | Swing: Multi-day"
            )
            
            ai_trust = st.slider(
                "AI Trust Level (%)",
                0, 100,
                config['ai_control']['ai_trust_level'],
                help="0% = Manual approval | 50% = Semi-auto | 100% = Full auto"
            )
        
        with col2:
            max_positions = st.number_input(
                "Max Positions",
                min_value=1,
                max_value=50,
                value=config['account']['max_positions'],
                help="Maximum number of concurrent positions"
            )
            
            capital = st.number_input(
                "Paper Capital ($)",
                min_value=1000,
                max_value=10000000,
                value=config['account']['capital'],
                step=10000,
                help="Virtual trading capital"
            )
        
        st.divider()
        
        # Alert Settings Section
        st.subheader("📱 Alert Configuration")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.markdown("**Telegram**")
            telegram_enabled = st.checkbox(
                "Enable Telegram Alerts",
                value=config['alerts'].get('telegram_enabled', True)
            )
            
            if telegram_enabled:
                telegram_token = st.text_input(
                    "Bot Token",
                    value=os.getenv('TELEGRAM_BOT_TOKEN', ''),
                    type="password",
                    placeholder="123456789:ABCdef..."
                )
                telegram_chat = st.text_input(
                    "Chat ID",
                    value=os.getenv('TELEGRAM_CHAT_ID', ''),
                    placeholder="123456789"
                )
                
                st.caption("Get from @BotFather")
        
        with col2:
            st.markdown("**Email**")
            email_enabled = st.checkbox(
                "Enable Email Alerts",
                value=config['alerts'].get('email_enabled', False)
            )
            
            if email_enabled:
                email_sender = st.text_input(
                    "Email Address",
                    value=os.getenv('EMAIL_SENDER', ''),
                    placeholder="you@gmail.com"
                )
                email_password = st.text_input(
                    "App Password",
                    value=os.getenv('EMAIL_PASSWORD', ''),
                    type="password",
                    placeholder="xxxx xxxx xxxx xxxx"
                )
                
                st.caption("Use Gmail App Password")
        
        with col3:
            st.markdown("**Alert Threshold**")
            min_alert_score = st.slider(
                "Min Signal Score",
                50, 100,
                config['alerts'].get('min_signal_score_to_alert', 85),
                help="Only alert for signals with score >= this"
            )
        
        st.divider()
        
        # Google Sheets Section
        st.subheader("📊 Google Sheets Integration")
        
        col1, col2 = st.columns(2)
        
        with col1:
            sheets_id = st.text_input(
                "Spreadsheet ID",
                value=os.getenv('GOOGLE_SHEETS_SPREADSHEET_ID', ''),
                placeholder="1ABC...xyz",
                help="From spreadsheet URL: /d/{THIS_PART}/edit"
            )
        
        with col2:
            uploaded_file = st.file_uploader(
                "Upload Credentials JSON",
                type=['json'],
                help="Download from Google Cloud Console"
            )
            
            # Check if credentials exist
            if os.path.exists('credentials/google_sheets_credentials.json'):
                st.success("✅ Credentials file exists")
        
        st.divider()
        
        # Risk Management Section
        st.subheader("🛡️ Risk Management")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            risk_pct = st.number_input(
                "Risk Per Trade (%)",
                min_value=0.1,
                max_value=10.0,
                value=config['user_preferences']['risk_per_trade_pct'].get(trading_style, 2.0),
                step=0.1,
                help="Percentage of capital to risk per trade"
            )
        
        with col2:
            trailing_stop = st.number_input(
                "Trailing Stop (%)",
                min_value=0.5,
                max_value=20.0,
                value=config['user_preferences']['trailing_stop_pct'].get(trading_style, 3.0),
                step=0.5,
                help="Distance for trailing stop loss"
            )
        
        with col3:
            max_position_pct = st.number_input(
                "Max Position Size (%)",
                min_value=1.0,
                max_value=50.0,
                value=config['account'].get('max_position_pct', 10.0),
                step=1.0,
                help="Max % of capital per position"
            )
        
        st.divider()
        
        # Save Button
        col1, col2, col3 = st.columns([1, 2, 1])
        
        with col2:
            if st.button("💾 Save All Settings", type="primary", use_container_width=True):
                with st.spinner("Saving..."):
                    try:
                        # Update config.yaml
                        config['user_preferences']['trading_style'] = trading_style
                        config['user_preferences']['risk_per_trade_pct'][trading_style] = risk_pct
                        config['user_preferences']['trailing_stop_pct'][trading_style] = trailing_stop
                        config['ai_control']['ai_trust_level'] = ai_trust
                        config['account']['max_positions'] = max_positions
                        config['account']['capital'] = capital
                        config['account']['max_position_pct'] = max_position_pct
                        config['alerts']['telegram_enabled'] = telegram_enabled
                        config['alerts']['email_enabled'] = email_enabled
                        config['alerts']['min_signal_score_to_alert'] = min_alert_score
                        
                        with open('config.yaml', 'w') as f:
                            yaml.dump(config, f, default_flow_style=False, sort_keys=False)
                        
                        # Update .env
                        env_lines = []
                        
                        if telegram_enabled and telegram_token:
                            env_lines.append(f"TELEGRAM_BOT_TOKEN={telegram_token}")
                            env_lines.append(f"TELEGRAM_CHAT_ID={telegram_chat}")
                        
                        if email_enabled and email_sender:
                            env_lines.append(f"EMAIL_SENDER={email_sender}")
                            env_lines.append(f"EMAIL_PASSWORD={email_password}")
                        
                        if sheets_id:
                            env_lines.append(f"GOOGLE_SHEETS_SPREADSHEET_ID={sheets_id}")
                        
                        with open('.env', 'w') as f:
                            f.write('\n'.join(env_lines))
                        
                        # Save credentials file
                        if uploaded_file:
                            os.makedirs('credentials', exist_ok=True)
                            with open('credentials/google_sheets_credentials.json', 'wb') as f:
                                f.write(uploaded_file.getvalue())
                        
                        st.success("✅ Settings saved successfully!")
                        st.info("⚠️ Restart the system to apply changes:\n``````")
                        
                    except Exception as e:
                        st.error(f"❌ Error saving settings: {e}")

# =============================================================================
# RUN APP
# =============================================================================

if __name__ == "__main__":
    main()

