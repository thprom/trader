#!/usr/bin/env python3
"""
MarketSense AI - Live Trading Dashboard
Real-time web dashboard for trading signals on Pocket Option.
"""

import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, timedelta
import time

from live_data import get_signal_generator, get_live_data_fetcher

# Page configuration
st.set_page_config(
    page_title="MarketSense AI - Live Signals",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        text-align: center;
        margin-bottom: 1rem;
        background: linear-gradient(90deg, #1f77b4, #2ca02c);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }
    .signal-box {
        padding: 1.5rem;
        border-radius: 15px;
        margin: 1rem 0;
        text-align: center;
    }
    .buy-signal {
        background: linear-gradient(135deg, #28a745, #20c997);
        color: white;
    }
    .sell-signal {
        background: linear-gradient(135deg, #dc3545, #fd7e14);
        color: white;
    }
    .wait-signal {
        background: linear-gradient(135deg, #ffc107, #fd7e14);
        color: black;
    }
    .no-trade-signal {
        background: linear-gradient(135deg, #6c757d, #343a40);
        color: white;
    }
    .metric-card {
        background-color: #f8f9fa;
        border-radius: 10px;
        padding: 1rem;
        text-align: center;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    .warning-text {
        color: #ffc107;
        font-weight: bold;
    }
    .success-text {
        color: #28a745;
        font-weight: bold;
    }
    .danger-text {
        color: #dc3545;
        font-weight: bold;
    }
    .big-number {
        font-size: 2.5rem;
        font-weight: bold;
    }
    .live-indicator {
        display: inline-block;
        width: 10px;
        height: 10px;
        background-color: #28a745;
        border-radius: 50%;
        animation: pulse 1s infinite;
    }
    @keyframes pulse {
        0% { opacity: 1; }
        50% { opacity: 0.5; }
        100% { opacity: 1; }
    }
</style>
""", unsafe_allow_html=True)


@st.cache_resource
def get_generator():
    """Get signal generator instance."""
    return get_signal_generator()


@st.cache_resource
def get_fetcher():
    """Get data fetcher instance."""
    return get_live_data_fetcher()


def render_signal_card(signal: dict):
    """Render a signal card."""
    action = signal['signal']
    direction = signal.get('direction', '')
    
    if action == 'BUY':
        signal_class = 'buy-signal'
        icon = '🟢'
        action_text = 'BUY (CALL)'
    elif action == 'SELL':
        signal_class = 'sell-signal'
        icon = '🔴'
        action_text = 'SELL (PUT)'
    elif action == 'WAIT':
        signal_class = 'wait-signal'
        icon = '🟡'
        action_text = 'WAIT'
    else:
        signal_class = 'no-trade-signal'
        icon = '⛔'
        action_text = 'DO NOT TRADE'
    
    price = signal.get('price', 'N/A')
    asset = signal.get('asset', 'Unknown')
    
    st.markdown(f"""
    <div class="signal-box {signal_class}">
        <h1>{icon} {action_text}</h1>
        <h3>{asset} @ {price}</h3>
    </div>
    """, unsafe_allow_html=True)


def render_metrics(signal: dict):
    """Render signal metrics."""
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        score = signal.get('score', 0)
        score_color = 'success' if score >= 70 else 'warning' if score >= 50 else 'danger'
        st.metric("Score", f"{score:.0f}/100", delta=f"{'Good' if score >= 60 else 'Low'}")
    
    with col2:
        prob = signal.get('probability', 0)
        st.metric("Probability", f"{prob:.0f}%", delta=f"{'High' if prob >= 60 else 'Medium' if prob >= 50 else 'Low'}")
    
    with col3:
        confidence = signal.get('confidence', 'N/A')
        st.metric("Confidence", confidence)
    
    with col4:
        st.metric("Risk Level", signal.get('risk_level', 'N/A'))


def render_reasons(signal: dict):
    """Render signal reasons."""
    st.subheader("📋 Analysis Reasons")
    
    for reason in signal.get('reasons', []):
        if '✅' in reason or '📈' in reason:
            st.success(reason)
        elif '⚠️' in reason or '📉' in reason:
            st.warning(reason)
        elif '❌' in reason:
            st.error(reason)
        else:
            st.info(reason)


def render_warnings(signal: dict):
    """Render warnings."""
    warnings = signal.get('warnings', [])
    if warnings:
        st.subheader("⚠️ Warnings")
        for warning in warnings:
            st.warning(warning)


def render_chart(asset: str, timeframe: str):
    """Render price chart."""
    fetcher = get_fetcher()
    df = fetcher.fetch_live_data(asset, timeframe)
    
    if df.empty:
        st.warning("No chart data available")
        return
    
    # Create candlestick chart
    fig = go.Figure(data=[go.Candlestick(
        x=df['timestamp'],
        open=df['open'],
        high=df['high'],
        low=df['low'],
        close=df['close'],
        name=asset
    )])
    
    fig.update_layout(
        title=f'{asset} - {timeframe}',
        yaxis_title='Price',
        xaxis_title='Time',
        height=400,
        template='plotly_white',
        xaxis_rangeslider_visible=False
    )
    
    st.plotly_chart(fig, use_container_width=True)


def main():
    """Main dashboard function."""
    generator = get_generator()
    fetcher = get_fetcher()
    
    # Header
    st.markdown('<h1 class="main-header">🎯 MarketSense AI - Live Trading Signals</h1>', unsafe_allow_html=True)
    
    # Live indicator
    st.markdown(f"""
    <div style="text-align: center; margin-bottom: 1rem;">
        <span class="live-indicator"></span>
        <span style="margin-left: 5px;">LIVE</span>
        <span style="margin-left: 20px;">Last Update: {datetime.now().strftime('%H:%M:%S')}</span>
    </div>
    """, unsafe_allow_html=True)
    
    # Sidebar
    with st.sidebar:
        st.image("https://via.placeholder.com/200x60?text=MarketSense+AI", width=200)
        st.markdown("---")
        
        st.subheader("⚙️ Settings")
        
        # Asset selection
        available_assets = fetcher.get_available_assets()
        selected_asset = st.selectbox(
            "Select Asset",
            available_assets,
            index=0
        )
        
        # Timeframe selection
        timeframe = st.selectbox(
            "Timeframe",
            ['1m', '5m', '15m'],
            index=1
        )
        
        # Auto-refresh
        auto_refresh = st.checkbox("Auto-refresh (60s)", value=True)
        
        st.markdown("---")
        
        # Market status
        st.subheader("📊 Market Status")
        market_status = fetcher.get_market_status()
        
        st.write(f"**Session:** {market_status['current_session']}")
        st.write(f"**Forex:** {'🟢 Open' if market_status['forex_open'] else '🔴 Closed'}")
        st.write(f"**Crypto:** {'🟢 Open' if market_status['crypto_open'] else '🔴 Closed'}")
        
        st.markdown("---")
        
        # Quick scan button
        if st.button("🔍 Scan All Markets", use_container_width=True):
            st.session_state['show_scan'] = True
        
        st.markdown("---")
        
        st.markdown("""
        **⚠️ Disclaimer:**
        This is for educational purposes only. 
        Not financial advice. Trade at your own risk.
        """)
    
    # Main content
    col1, col2 = st.columns([2, 1])
    
    with col1:
        # Get signal
        with st.spinner(f'Analyzing {selected_asset}...'):
            signal = generator.generate_signal(selected_asset, timeframe)
        
        # Signal card
        render_signal_card(signal)
        
        # Metrics
        render_metrics(signal)
        
        # Chart
        st.markdown("---")
        render_chart(selected_asset, timeframe)
    
    with col2:
        # Reasons
        render_reasons(signal)
        
        # Warnings
        render_warnings(signal)
        
        # Action guide
        st.markdown("---")
        st.subheader("📝 How to Trade")
        
        if signal['signal'] == 'BUY':
            st.success("""
            **Action: CALL (UP)**
            1. Open Pocket Option
            2. Select {asset}
            3. Choose CALL/UP
            4. Set your amount
            5. Execute trade
            """.format(asset=selected_asset))
        elif signal['signal'] == 'SELL':
            st.error("""
            **Action: PUT (DOWN)**
            1. Open Pocket Option
            2. Select {asset}
            3. Choose PUT/DOWN
            4. Set your amount
            5. Execute trade
            """.format(asset=selected_asset))
        elif signal['signal'] == 'WAIT':
            st.warning("""
            **Action: WAIT**
            - No clear setup right now
            - Wait for better opportunity
            - Check back in a few minutes
            """)
        else:
            st.error("""
            **Action: DO NOT TRADE**
            - High risk detected
            - Avoid this setup
            - Protect your capital
            """)
    
    # Market scan results
    if st.session_state.get('show_scan', False):
        st.markdown("---")
        st.subheader("🔍 Market Scan Results")
        
        with st.spinner('Scanning all markets...'):
            opportunities = generator.get_best_opportunities(timeframe, min_score=50)
        
        if opportunities:
            scan_df = pd.DataFrame([{
                'Asset': o['asset'],
                'Signal': o['signal'],
                'Direction': o.get('direction', '-'),
                'Score': f"{o['score']:.0f}",
                'Probability': f"{o['probability']:.0f}%",
                'Confidence': o['confidence']
            } for o in opportunities])
            
            st.dataframe(scan_df, use_container_width=True, hide_index=True)
        else:
            st.info("No strong opportunities found. Wait for better setups.")
        
        st.session_state['show_scan'] = False
    
    # Auto-refresh
    if auto_refresh:
        time.sleep(60)
        st.rerun()


if __name__ == "__main__":
    main()
