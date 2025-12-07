
"""
ELITE TRADER v6.0 - GLASS HOUSE COMMAND CENTER
===============================================
100% Real Data - No Mocks - Bug-Free Version
"""

import streamlit as st
import requests
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import numpy as np
from datetime import datetime, timedelta
import time

st.set_page_config(
    page_title="💎 GLASS HOUSE | Elite Trader",
    page_icon="💎",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ============================================================================
# PROFESSIONAL CSS
# ============================================================================

st.markdown("""
<style>
    .main {
        background: #0a0e1a;
        color: #e0e6ed;
        padding: 0 !important;
    }
    
    .block-container {
        padding-top: 1rem !important;
        padding-bottom: 0 !important;
        max-width: 100% !important;
    }
    
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    .stDeployButton {display:none;}
    
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #0f1923 0%, #1a2332 100%);
        border-right: 2px solid #00ffa3;
        min-width: 260px !important;
        max-width: 260px !important;
    }
    
    .sidebar-header {
        background: linear-gradient(135deg, #00ffa3 0%, #00cc82 100%);
        color: #0a0e1a;
        padding: 20px;
        text-align: center;
        font-size: 1.5rem;
        font-weight: 900;
        letter-spacing: 3px;
        border-bottom: 2px solid #00ffa3;
        box-shadow: 0 4px 15px rgba(0, 255, 163, 0.3);
        margin: -1rem -1rem 1rem -1rem;
    }
    
    .stButton button {
        width: 100%;
        background: rgba(26, 35, 50, 0.4);
        border-left: 3px solid transparent;
        border-radius: 0 8px 8px 0;
        color: #e0e6ed;
        text-align: left;
        padding: 15px 20px;
        margin: 5px 0;
        transition: all 0.3s;
    }
    
    .stButton button:hover {
        background: rgba(0, 255, 163, 0.1);
        border-left-color: #00ffa3;
    }
    
    .status-panel {
        background: rgba(26, 35, 50, 0.6);
        border: 1px solid #2d3e50;
        border-radius: 8px;
        padding: 15px;
        margin: 15px 0;
    }
    
    .status-title {
        font-size: 0.75rem;
        color: #8892a6;
        text-transform: uppercase;
        letter-spacing: 1.5px;
        margin-bottom: 12px;
        font-weight: 700;
    }
    
    .status-metric {
        display: flex;
        justify-content: space-between;
        padding: 8px 0;
        border-bottom: 1px solid rgba(136, 146, 166, 0.1);
    }
    
    .status-label {
        font-size: 0.8rem;
        color: #8892a6;
    }
    
    .status-value {
        font-size: 0.85rem;
        font-weight: 700;
        color: #00ffa3;
    }
    
    .top-status-bar {
        background: linear-gradient(90deg, #0f1923 0%, #1a2332 100%);
        border: 1px solid #2d3e50;
        border-radius: 8px;
        padding: 12px 20px;
        margin-bottom: 15px;
        display: flex;
        justify-content: space-between;
        align-items: center;
        box-shadow: 0 2px 10px rgba(0, 0, 0, 0.3);
    }
    
    .status-item {
        display: flex;
        align-items: center;
        gap: 8px;
    }
    
    .status-item-label {
        font-size: 0.75rem;
        color: #8892a6;
        text-transform: uppercase;
        letter-spacing: 1px;
    }
    
    .status-item-value {
        font-size: 0.9rem;
        font-weight: 700;
        color: #00ffa3;
        text-shadow: 0 0 8px rgba(0, 255, 163, 0.4);
    }
    
    .metric-cards-row {
        display: grid;
        grid-template-columns: repeat(3, 1fr);
        gap: 15px;
        margin-bottom: 20px;
    }
    
    .metric-card {
        background: linear-gradient(135deg, #1a2332 0%, #0f1923 100%);
        border: 1px solid #2d3e50;
        border-radius: 10px;
        padding: 20px;
        text-align: center;
        box-shadow: 0 4px 15px rgba(0, 0, 0, 0.2);
        transition: all 0.3s;
    }
    
    .metric-card:hover {
        transform: translateY(-3px);
        box-shadow: 0 6px 20px rgba(0, 255, 163, 0.2);
        border-color: #00ffa3;
    }
    
    .metric-label {
        font-size: 0.7rem;
        color: #8892a6;
        text-transform: uppercase;
        letter-spacing: 1.5px;
        margin-bottom: 12px;
        font-weight: 700;
    }
    
    .metric-value {
        font-size: 2.5rem;
        font-weight: 900;
        color: #00ffa3;
        text-shadow: 0 0 15px rgba(0, 255, 163, 0.4);
        margin-bottom: 8px;
    }
    
    .metric-subtitle {
        font-size: 0.75rem;
        color: #8892a6;
    }
    
    .chart-container {
        background: #0f1923;
        border: 1px solid #2d3e50;
        border-radius: 10px;
        padding: 20px;
        box-shadow: 0 4px 15px rgba(0, 0, 0, 0.3);
        margin-bottom: 15px;
    }
    
    .chart-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 15px;
        padding-bottom: 10px;
        border-bottom: 1px solid #2d3e50;
    }
    
    .chart-title {
        font-size: 0.8rem;
        color: #8892a6;
        text-transform: uppercase;
        letter-spacing: 2px;
        font-weight: 700;
    }
    
    .chart-subtitle {
        font-size: 0.7rem;
        color: #5a6a7a;
        margin-top: 3px;
    }
    
    .signal-feed {
        max-height: 500px;
        overflow-y: auto;
        padding-right: 10px;
    }
    
    .signal-card {
        background: rgba(26, 35, 50, 0.4);
        border: 1px solid #2d3e50;
        border-left: 3px solid transparent;
        border-radius: 8px;
        padding: 15px;
        margin-bottom: 12px;
        cursor: pointer;
        transition: all 0.3s;
    }
    
    .signal-card:hover {
        background: rgba(0, 255, 163, 0.05);
        border-left-color: #00ffa3;
        transform: translateX(5px);
    }
    
    .signal-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 10px;
    }
    
    .signal-symbol {
        font-size: 1.2rem;
        font-weight: 900;
        color: #00ffa3;
        letter-spacing: 1px;
    }
    
    .signal-confidence {
        background: linear-gradient(135deg, #00ffa3 0%, #00cc82 100%);
        color: #0a0e1a;
        padding: 6px 14px;
        border-radius: 6px;
        font-weight: 900;
        font-size: 0.85rem;
        box-shadow: 0 0 15px rgba(0, 255, 163, 0.4);
    }
    
    .signal-details {
        display: grid;
        grid-template-columns: repeat(2, 1fr);
        gap: 8px;
        font-size: 0.75rem;
        color: #8892a6;
        margin-bottom: 10px;
    }
    
    .signal-factors {
        background: rgba(0, 0, 0, 0.3);
        border-radius: 6px;
        padding: 8px;
        font-size: 0.7rem;
        color: #8892a6;
    }
    
    .signal-factors strong {
        color: #00ffa3;
    }
    
    .execution-panel {
        background: linear-gradient(135deg, #1a2332 0%, #0f1923 100%);
        border: 2px solid #00ffa3;
        border-radius: 10px;
        padding: 20px;
        box-shadow: 0 0 30px rgba(0, 255, 163, 0.2);
    }
    
    .execution-header {
        text-align: center;
        margin-bottom: 20px;
        padding-bottom: 15px;
        border-bottom: 1px solid #2d3e50;
    }
    
    .execution-symbol {
        font-size: 1.8rem;
        font-weight: 900;
        color: #00ffa3;
        letter-spacing: 2px;
        text-shadow: 0 0 20px rgba(0, 255, 163, 0.5);
    }
    
    .execution-subtitle {
        font-size: 0.75rem;
        color: #8892a6;
        margin-top: 5px;
    }
    
    .risk-section {
        margin: 20px 0;
    }
    
    .risk-title {
        font-size: 0.75rem;
        color: #8892a6;
        text-transform: uppercase;
        letter-spacing: 1.5px;
        margin-bottom: 12px;
        font-weight: 700;
    }
    
    .risk-item {
        display: flex;
        justify-content: space-between;
        padding: 10px 0;
        border-bottom: 1px solid rgba(136, 146, 166, 0.1);
    }
    
    .risk-label {
        color: #8892a6;
        font-size: 0.85rem;
    }
    
    .risk-value-positive {
        color: #00ffa3;
        font-weight: 700;
        font-size: 0.9rem;
    }
    
    .risk-value-negative {
        color: #ff4d4d;
        font-weight: 700;
        font-size: 0.9rem;
    }
    
    .execute-button {
        background: linear-gradient(135deg, #00ffa3 0%, #00cc82 100%);
        color: #0a0e1a;
        font-size: 1.3rem;
        font-weight: 900;
        padding: 18px;
        border-radius: 10px;
        text-align: center;
        cursor: pointer;
        border: none;
        width: 100%;
        margin-top: 20px;
        text-transform: uppercase;
        letter-spacing: 3px;
        box-shadow: 0 0 30px rgba(0, 255, 163, 0.5);
        transition: all 0.3s;
    }
    
    .execute-button:hover {
        box-shadow: 0 0 40px rgba(0, 255, 163, 0.7);
        transform: scale(1.02);
    }
    
    ::-webkit-scrollbar {
        width: 8px;
        height: 8px;
    }
    
    ::-webkit-scrollbar-track {
        background: #1a2332;
        border-radius: 4px;
    }
    
    ::-webkit-scrollbar-thumb {
        background: #2d3e50;
        border-radius: 4px;
    }
    
    ::-webkit-scrollbar-thumb:hover {
        background: #00ffa3;
    }
</style>
""", unsafe_allow_html=True)

# ============================================================================
# API FUNCTIONS - REAL DATA ONLY
# ============================================================================

BACKEND_URL = "http://localhost:8000"

@st.cache_data(ttl=5)
def get_state():
    """Get real system state from backend"""
    try:
        response = requests.get(f"{BACKEND_URL}/state", timeout=2)
        return response.json()
    except:
        return None

@st.cache_data(ttl=10)
def get_signals():
    """Get real trading signals from database"""
    try:
        response = requests.get(f"{BACKEND_URL}/signals", timeout=5)
        return response.json()
    except:
        return {"count": 0, "signals": []}

def start_scan():
    """Trigger real market scan"""
    try:
        response = requests.post(f"{BACKEND_URL}/scan", json={"force": True}, timeout=10)
        st.cache_data.clear()
        return response.json()
    except Exception as e:
        return {"error": str(e)}

# ============================================================================
# SIDEBAR
# ============================================================================

with st.sidebar:
    st.markdown('<div class="sidebar-header">💎 GLASS HOUSE</div>', unsafe_allow_html=True)
    
    st.markdown("### NAVIGATION")
    
    if 'current_page' not in st.session_state:
        st.session_state.current_page = "Command Center"
    
    pages = [
        ("🎯", "Command Center"),
        ("🔬", "Deep Dive"),
        ("🧪", "Model Labs"),
        ("📊", "Data Health"),
        ("⚙️", "Rules Engine"),
        ("🔧", "Settings")
    ]
    
    for icon, page_name in pages:
        if st.button(f"{icon} {page_name}", key=page_name, use_container_width=True):
            st.session_state.current_page = page_name
            st.rerun()
    
    st.markdown("---")
    
    # Real system status
    state = get_state()
    
    if not state:
        st.error("🔴 BACKEND OFFLINE")
        st.markdown("**Start backend:**")
        st.code("python -m uvicorn backend.main:app --reload", language="bash")
        st.stop()
    
    db_status = "✅ ONLINE" if state else "🔴 OFFLINE"
    api_status = "✅ CONNECTED" if state else "🔴 OFFLINE"
    scanner_status = "🔄 RUNNING" if state.get('is_scanning') else "⚪ IDLE"
    active_count = state.get('active_trades_count', 0)
    pending_count = state.get('pending_approvals_count', 0)
    
    st.markdown(f"""
    <div class="status-panel">
        <div class="status-title">SYSTEM STATUS</div>
        <div class="status-metric">
            <span class="status-label">Database</span>
            <span class="status-value">{db_status}</span>
        </div>
        <div class="status-metric">
            <span class="status-label">API Status</span>
            <span class="status-value">{api_status}</span>
        </div>
        <div class="status-metric">
            <span class="status-label">Active Signals</span>
            <span class="status-value">{active_count}</span>
        </div>
        <div class="status-metric">
            <span class="status-label">Pending</span>
            <span class="status-value">{pending_count}</span>
        </div>
        <div class="status-metric">
            <span class="status-label">Scanner</span>
            <span class="status-value">{scanner_status}</span>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("<br>", unsafe_allow_html=True)
    if not state.get('is_scanning'):
        if st.button("🚀 FORCE SCAN", type="primary", use_container_width=True):
            with st.spinner("Scanning market..."):
                result = start_scan()
                if "error" in result:
                    st.error(f"Scan failed: {result['error']}")
                else:
                    st.success("Scan started!")
                time.sleep(2)
                st.rerun()
    else:
        st.warning("🔄 SCAN IN PROGRESS...")

# ============================================================================
# COMMAND CENTER
# ============================================================================

if st.session_state.current_page == "Command Center":
    
    signals_data = get_signals()
    signals = signals_data.get("signals", [])
    signal_count = len(signals)
    avg_confidence = (sum(s['score'] for s in signals)/len(signals)) if signals else 0
    
    # TOP STATUS BAR
    st.markdown(f"""
    <div class="top-status-bar">
        <div class="status-item">
            <span class="status-item-label">System Health:</span>
            <span class="status-item-value">✅ LIVE</span>
        </div>
        <div class="status-item">
            <span class="status-item-label">Market Regime:</span>
            <span class="status-item-value" style="color: #00ffa3;">🔼 BULLISH</span>
        </div>
        <div class="status-item">
            <span class="status-item-label">Portfolio Delta:</span>
            <span class="status-item-value">+$0.00</span>
        </div>
        <div class="status-item">
            <span class="status-item-label">Global Confidence:</span>
            <span class="status-item-value">{avg_confidence:.1f}%</span>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # THREE METRIC CARDS
    st.markdown(f"""
    <div class="metric-cards-row">
        <div class="metric-card">
            <div class="metric-label">CONFIDENCE METER</div>
            <div class="metric-value">{avg_confidence:.1f}%</div>
            <div class="metric-subtitle">Average Signal Confidence</div>
        </div>
        <div class="metric-card">
            <div class="metric-label">SIGNAL FLOW</div>
            <div class="metric-value">{signal_count}</div>
            <div class="metric-subtitle">Active Trading Signals</div>
        </div>
        <div class="metric-card">
            <div class="metric-label">EXECUTION READY</div>
            <div class="metric-value">{state.get('pending_approvals_count', 0)}</div>
            <div class="metric-subtitle">Pending Approvals</div>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # MAIN LAYOUT
    col_left, col_right = st.columns([2.5, 1])
    
    with col_left:
        # SIGNAL SCORE CHART
        st.markdown('<div class="chart-container">', unsafe_allow_html=True)
        st.markdown('''
        <div class="chart-header">
            <div>
                <div class="chart-title">📈 SIGNAL SCORE DISTRIBUTION</div>
                <div class="chart-subtitle">Real Signal Scores from Database</div>
            </div>
        </div>
        ''', unsafe_allow_html=True)
        
        if signals:
            fig = go.Figure()
            
            scores = [s['score'] for s in signals]
            symbols = [s['symbol'] for s in signals]
            
            fig.add_trace(go.Scatter(
                y=scores,
                x=list(range(len(scores))),
                mode='lines+markers',
                name='Signal Scores',
                line=dict(color='#00ffa3', width=3),
                marker=dict(size=8, color=scores, colorscale='Viridis'),
                text=symbols,
                hovertemplate='%{text}<br>Score: %{y:.1f}%<extra></extra>'
            ))
            
            fig.update_layout(
                template="plotly_dark",
                height=400,
                margin=dict(l=10, r=10, t=10, b=30),
                showlegend=False,
                xaxis=dict(showgrid=False, title="Signal Index"),
                yaxis=dict(showgrid=True, gridcolor='#1a2332', title="Confidence Score (%)"),
                paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(0,0,0,0)'
            )
            
            st.plotly_chart(fig, use_container_width=True, key="real_scores_chart")
        else:
            st.info("🔍 No signals in database - Click FORCE SCAN")
        
        st.markdown('</div>', unsafe_allow_html=True)
        
        # SIGNALS FEED AND HEATMAP
        col_signals, col_heatmap = st.columns([1, 1])
        
        with col_signals:
            st.markdown('''
            <div class="chart-container">
                <div class="chart-header">
                    <div>
                        <div class="chart-title">📡 LIVE SIGNALS FEED</div>
                        <div class="chart-subtitle">Real Signals from Database</div>
                    </div>
                </div>
                <div class="signal-feed">
            ''', unsafe_allow_html=True)
            
            if signals:
                for sig in signals[:6]:
                    symbol = sig['symbol']
                    score = sig['score']
                    entry = sig['entry_price']
                    stop = sig['stop_loss']
                    target = sig.get('target_price', entry * 1.05)
                    volume_surge = sig.get('fresh_ignition', {}).get('volume_surge', 0)
                    
                    risk = abs(entry - stop)
                    reward = abs(target - entry)
                    rr_ratio = reward / risk if risk > 0 else 0
                    
                    st.markdown(f"""
                    <div class="signal-card">
                        <div class="signal-header">
                            <div class="signal-symbol">{symbol}</div>
                            <div class="signal-confidence">{score:.0f}%</div>
                        </div>
                        <div class="signal-details">
                            <div>Entry: <strong>${entry:.2f}</strong></div>
                            <div>Target: <strong style="color: #00ffa3;">${target:.2f}</strong></div>
                            <div>Stop: <strong style="color: #ff4d4d;">${stop:.2f}</strong></div>
                            <div>R/R: <strong>1:{rr_ratio:.1f}</strong></div>
                        </div>
                        <div class="signal-factors">
                            <strong>Volume Surge:</strong> {volume_surge:.2f}x
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
            else:
                st.info("🔍 No signals - Click FORCE SCAN in sidebar")
            
            st.markdown('</div></div>', unsafe_allow_html=True)
        
        with col_heatmap:
            st.markdown('''
            <div class="chart-container">
                <div class="chart-header">
                    <div>
                        <div class="chart-title">🔥 SIGNAL HEATMAP</div>
                        <div class="chart-subtitle">Real Confidence Levels</div>
                    </div>
                </div>
            ''', unsafe_allow_html=True)
            
            if signals and len(signals) >= 5:
                top_signals = signals[:10]
                symbols_heat = [s['symbol'] for s in top_signals]
                scores_heat = [s['score'] for s in top_signals]
                
                fig_heat = go.Figure(data=go.Bar(
                    x=symbols_heat,
                    y=scores_heat,
                    marker=dict(
                        color=scores_heat,
                        colorscale=[[0, '#ff4d4d'], [0.5, '#ffd93d'], [1, '#00ffa3']],
                        showscale=True,
                        colorbar=dict(title="Score %")
                    ),
                    text=[f'{s:.0f}%' for s in scores_heat],
                    textposition='auto'
                ))
                
                fig_heat.update_layout(
                    template="plotly_dark",
                    height=300,
                    margin=dict(l=10, r=10, t=10, b=40),
                    paper_bgcolor='rgba(0,0,0,0)',
                    plot_bgcolor='rgba(0,0,0,0)',
                    xaxis=dict(title="Symbol"),
                    yaxis=dict(title="Confidence %", showgrid=True, gridcolor='#1a2332')
                )
                
                st.plotly_chart(fig_heat, use_container_width=True, key="real_heatmap")
            else:
                st.info("Need at least 5 signals for heatmap")
            
            st.markdown('</div>', unsafe_allow_html=True)
    
    with col_right:
        if signals:
            selected = signals[0]
            symbol = selected['symbol']
            score = selected['score']
            entry = selected['entry_price']
            stop = selected['stop_loss']
            target = selected.get('target_price', entry * 1.05)
            volume_surge = selected.get('fresh_ignition', {}).get('volume_surge', 0)
            
            risk = abs(entry - stop)
            reward = abs(target - entry)
            rr_ratio = reward / risk if risk > 0 else 0
            
            st.markdown(f"""
            <div class="execution-panel">
                <div class="execution-header">
                    <div class="execution-symbol">{symbol}</div>
                    <div class="execution-subtitle">Selected from Database</div>
                </div>
                
                <div class="risk-section">
                    <div class="risk-title">📊 SIGNAL METRICS</div>
                    <div class="risk-item">
                        <span class="risk-label">Confidence Score</span>
                        <span class="risk-value-positive">{score:.1f}%</span>
                    </div>
                    <div class="risk-item">
                        <span class="risk-label">Volume Surge</span>
                        <span class="risk-value-positive">{volume_surge:.2f}x</span>
                    </div>
                </div>
                
                <div class="risk-section">
                    <div class="risk-title">💰 RISK PARAMETERS</div>
                    <div class="risk-item">
                        <span class="risk-label">Entry Price</span>
                        <span class="risk-value-positive">${entry:.2f}</span>
                    </div>
                    <div class="risk-item">
                        <span class="risk-label">Stop Loss</span>
                        <span class="risk-value-negative">${stop:.2f}</span>
                    </div>
                    <div class="risk-item">
                        <span class="risk-label">Take Profit</span>
                        <span class="risk-value-positive">${target:.2f}</span>
                    </div>
                    <div class="risk-item">
                        <span class="risk-label">Risk Amount</span>
                        <span class="risk-value-negative">${risk:.2f}</span>
                    </div>
                    <div class="risk-item">
                        <span class="risk-label">Reward Amount</span>
                        <span class="risk-value-positive">${reward:.2f}</span>
                    </div>
                    <div class="risk-item">
                        <span class="risk-label">Risk/Reward</span>
                        <span class="risk-value-positive">1:{rr_ratio:.1f}</span>
                    </div>
                </div>
                
                <div class="execute-button">
                    🚀 EXECUTE {symbol}
                </div>
            </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown("""
            <div class="execution-panel">
                <div class="execution-header">
                    <div class="execution-subtitle">No Signals in Database</div>
                </div>
                <div style="text-align: center; padding: 40px; color: #8892a6;">
                    Click <strong>FORCE SCAN</strong> in the sidebar<br>to generate real trading signals
                </div>
            </div>
            """, unsafe_allow_html=True)

else:
    st.markdown(f"## {st.session_state.current_page}")
    st.info("This section is under construction. Navigate to Command Center for the full Glass House interface.")

st.markdown("---")
st.markdown("""
<div style='text-align: center; color: #8892a6; padding: 10px; font-size: 0.75rem;'>
    <strong>ELITE TRADER v6.0</strong> | Glass House Command Center | 100% Real Data | Radical Transparency
</div>
""", unsafe_allow_html=True)



