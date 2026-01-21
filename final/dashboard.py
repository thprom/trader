"""
MarketSense AI - Streamlit Dashboard
Interactive web interface for the trading bot.
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, timedelta
import json

# Import bot modules
from bot import MarketSenseBot
from database import get_database
from config import DEFAULT_ASSETS, SUPPORTED_TIMEFRAMES, SCORE_THRESHOLDS

# Page configuration
st.set_page_config(
    page_title="MarketSense AI",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #1f77b4;
        text-align: center;
        margin-bottom: 1rem;
    }
    .metric-card {
        background-color: #f0f2f6;
        border-radius: 10px;
        padding: 1rem;
        margin: 0.5rem 0;
    }
    .warning-box {
        background-color: #fff3cd;
        border: 1px solid #ffc107;
        border-radius: 5px;
        padding: 1rem;
        margin: 0.5rem 0;
    }
    .success-box {
        background-color: #d4edda;
        border: 1px solid #28a745;
        border-radius: 5px;
        padding: 1rem;
        margin: 0.5rem 0;
    }
    .danger-box {
        background-color: #f8d7da;
        border: 1px solid #dc3545;
        border-radius: 5px;
        padding: 1rem;
        margin: 0.5rem 0;
    }
</style>
""", unsafe_allow_html=True)


@st.cache_resource
def get_bot():
    """Get or create bot instance."""
    bot = MarketSenseBot()
    bot.initialize()
    return bot


def main():
    """Main dashboard function."""
    # Initialize bot
    bot = get_bot()
    db = get_database()
    
    # Sidebar
    with st.sidebar:
        st.image("https://via.placeholder.com/150x50?text=MarketSense+AI", width=200)
        st.markdown("---")
        
        # Mode selection
        mode = st.selectbox(
            "Operating Mode",
            ["Simulation", "Manual Assist"],
            index=0 if bot.mode == 'simulation' else 1
        )
        if mode == "Simulation" and bot.mode != 'simulation':
            bot.set_mode('simulation')
        elif mode == "Manual Assist" and bot.mode != 'manual_assist':
            bot.set_mode('manual_assist')
        
        st.markdown("---")
        
        # Asset selection
        selected_assets = st.multiselect(
            "Preferred Assets",
            DEFAULT_ASSETS,
            default=bot.preferred_assets[:3]
        )
        if selected_assets != bot.preferred_assets:
            bot.preferred_assets = selected_assets
        
        # Timeframe selection
        timeframe = st.selectbox(
            "Timeframe",
            SUPPORTED_TIMEFRAMES,
            index=SUPPORTED_TIMEFRAMES.index(bot.preferred_timeframe)
        )
        if timeframe != bot.preferred_timeframe:
            bot.preferred_timeframe = timeframe
        
        st.markdown("---")
        
        # Quick actions
        st.subheader("Quick Actions")
        
        if st.button("🔄 Scan Markets", use_container_width=True):
            st.session_state['scan_results'] = bot.scan_markets()
        
        if st.button("📊 Generate Report", use_container_width=True):
            st.session_state['daily_report'] = bot.get_daily_report()
        
        if st.button("🧠 Train AI Model", use_container_width=True):
            result = bot.train_ai()
            st.session_state['train_result'] = result
    
    # Main content
    st.markdown('<h1 class="main-header">📊 MarketSense AI Dashboard</h1>', unsafe_allow_html=True)
    
    # Status overview
    status = bot.get_status()
    
    # Top metrics row
    col1, col2, col3, col4, col5 = st.columns(5)
    
    with col1:
        balance = status['simulation']['balance']
        pnl = status['simulation']['pnl']
        st.metric(
            "Balance",
            f"${balance:,.2f}",
            f"${pnl:+,.2f}" if pnl != 0 else None,
            delta_color="normal" if pnl >= 0 else "inverse"
        )
    
    with col2:
        stats = status['simulation']['stats']
        win_rate = stats.get('win_rate', 0)
        st.metric(
            "Win Rate",
            f"{win_rate:.1f}%",
            delta_color="normal" if win_rate >= 50 else "inverse"
        )
    
    with col3:
        total_trades = stats.get('total_trades', 0)
        st.metric("Total Trades", total_trades)
    
    with col4:
        discipline = status['psychology']['discipline_score']
        st.metric(
            "Discipline",
            f"{discipline['score']:.0f}/100",
            discipline['grade']
        )
    
    with col5:
        emotional_state = status['psychology']['emotional_state']['state']
        state_colors = {
            'CALM': '🟢',
            'CAUTIOUS': '🟡',
            'FRUSTRATED': '🟠',
            'TILTED': '🔴'
        }
        st.metric(
            "Emotional State",
            f"{state_colors.get(emotional_state, '⚪')} {emotional_state}"
        )
    
    # Warnings
    warnings = status['psychology']['warnings']
    if warnings:
        st.markdown("---")
        for warning in warnings:
            st.warning(warning)
    
    # Trading paused indicator
    if status['simulation']['is_paused']:
        st.error(f"⚠️ Trading Paused: {status['simulation']['pause_reason']}")
        if st.button("Resume Trading"):
            bot.resume()
            st.rerun()
    
    st.markdown("---")
    
    # Main tabs
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "📈 Analysis", "💹 Trade", "📋 History", "📊 Reports", "🧠 AI Insights"
    ])
    
    # Analysis Tab
    with tab1:
        st.subheader("Market Analysis")
        
        col1, col2 = st.columns([1, 2])
        
        with col1:
            analysis_asset = st.selectbox(
                "Select Asset",
                selected_assets if selected_assets else DEFAULT_ASSETS[:3],
                key="analysis_asset"
            )
            
            analysis_direction = st.radio(
                "Direction",
                ["Auto", "CALL", "PUT"],
                horizontal=True
            )
            
            if st.button("Analyze Setup", type="primary", use_container_width=True):
                direction = None if analysis_direction == "Auto" else analysis_direction
                analysis = bot.analyze(analysis_asset, timeframe, direction)
                st.session_state['current_analysis'] = analysis
        
        with col2:
            if 'current_analysis' in st.session_state:
                analysis = st.session_state['current_analysis']
                
                if analysis.get('error'):
                    st.error(analysis.get('message'))
                else:
                    # Score display
                    score = analysis['score']['final_score']
                    grade = analysis['score']['grade']
                    
                    score_color = (
                        "green" if score >= 76 else
                        "blue" if score >= 61 else
                        "orange" if score >= 41 else
                        "red"
                    )
                    
                    st.markdown(f"""
                    <div style="text-align: center; padding: 1rem; background-color: #f0f2f6; border-radius: 10px;">
                        <h2 style="color: {score_color}; margin: 0;">Score: {score:.1f}</h2>
                        <p style="margin: 0;">{grade}</p>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    # AI Prediction
                    ai_pred = analysis['ai_prediction']
                    col_a, col_b, col_c = st.columns(3)
                    
                    with col_a:
                        st.metric("Probability", f"{ai_pred.get('probability', 0):.1f}%")
                    with col_b:
                        st.metric("Risk Level", ai_pred.get('risk_level', 'N/A'))
                    with col_c:
                        rec = ai_pred.get('recommendation', 'WAIT')
                        rec_color = "🟢" if rec == "ENTER" else "🟡" if rec == "WAIT" else "🔴"
                        st.metric("Recommendation", f"{rec_color} {rec}")
                    
                    # Trap Analysis
                    trap = analysis['trap_analysis']
                    if trap.get('traps_detected'):
                        st.warning(f"⚠️ Trap Detected: {trap['recommendation']}")
                    
                    # Signals breakdown
                    with st.expander("📊 Signal Details"):
                        signals = analysis['signals']
                        
                        signal_data = {
                            'Indicator': ['RSI', 'EMA', 'MACD', 'Bollinger', 'Candle'],
                            'Signal': [
                                signals.get('rsi', {}).get('signal', 'N/A'),
                                signals.get('ema', {}).get('signal', 'N/A'),
                                signals.get('macd', {}).get('trend', 'N/A'),
                                signals.get('bollinger', {}).get('signal', 'N/A'),
                                signals.get('candle', {}).get('type', 'N/A')
                            ],
                            'Value': [
                                f"{signals.get('rsi', {}).get('value', 0):.1f}",
                                f"Fast: {signals.get('ema', {}).get('fast', 0):.5f}",
                                f"{signals.get('macd', {}).get('histogram', 0):.5f}",
                                f"{signals.get('bollinger', {}).get('percent', 0):.2%}",
                                signals.get('candle', {}).get('pattern', 'N/A')
                            ]
                        }
                        st.dataframe(pd.DataFrame(signal_data), hide_index=True)
    
    # Trade Tab
    with tab2:
        st.subheader("Execute Trade")
        
        if bot.mode == 'manual_assist':
            st.info("📝 Manual Assist Mode: AI will provide suggestions only. No automatic execution.")
        
        col1, col2 = st.columns(2)
        
        with col1:
            trade_asset = st.selectbox(
                "Asset",
                selected_assets if selected_assets else DEFAULT_ASSETS[:3],
                key="trade_asset"
            )
            
            trade_direction = st.radio(
                "Direction",
                ["CALL", "PUT"],
                horizontal=True,
                key="trade_direction"
            )
            
            journal_entry = st.text_area(
                "Journal Entry (Recommended)",
                placeholder="Describe your reasoning for this trade..."
            )
            
            if bot.mode == 'simulation':
                if st.button("Execute Trade", type="primary", use_container_width=True):
                    result = bot.execute(
                        trade_asset,
                        trade_direction,
                        timeframe,
                        journal_entry if journal_entry else None
                    )
                    st.session_state['trade_result'] = result
            else:
                if st.button("Get Suggestion", type="primary", use_container_width=True):
                    suggestion = bot.suggest_trade(trade_asset, timeframe)
                    st.session_state['trade_suggestion'] = suggestion
        
        with col2:
            if 'trade_result' in st.session_state:
                result = st.session_state['trade_result']
                
                if result['success']:
                    st.success(f"✅ Trade Executed! ID: {result['trade_id']}")
                    st.metric("Entry Price", f"{result['entry_price']:.5f}")
                    st.metric("Position Size", f"${result['position_size']:.2f}")
                    st.metric("Score", f"{result['score']:.1f}")
                    
                    if result.get('warnings'):
                        for warning in result['warnings']:
                            st.warning(warning)
                else:
                    st.error(f"❌ {result.get('message', 'Trade failed')}")
            
            if 'trade_suggestion' in st.session_state:
                suggestion = st.session_state['trade_suggestion']
                
                st.subheader("AI Suggestion")
                rec = suggestion.get('recommendation', {})
                
                action = rec.get('action', 'WAIT')
                action_color = "green" if action == "ENTER" else "orange" if action == "WAIT" else "red"
                
                st.markdown(f"""
                <div style="text-align: center; padding: 1rem; background-color: #f0f2f6; border-radius: 10px;">
                    <h3 style="color: {action_color}; margin: 0;">{action}</h3>
                    <p>{rec.get('message', '')}</p>
                </div>
                """, unsafe_allow_html=True)
        
        # Open trades
        st.markdown("---")
        st.subheader("Open Trades")
        
        open_trades = bot.get_open_trades()
        
        if open_trades:
            for trade in open_trades:
                with st.expander(f"Trade #{trade['id']} - {trade['asset']} {trade['direction']}"):
                    col_a, col_b, col_c = st.columns(3)
                    
                    with col_a:
                        st.write(f"**Entry:** {trade['entry_price']:.5f}")
                        st.write(f"**Amount:** ${trade['amount']:.2f}")
                    
                    with col_b:
                        st.write(f"**Score:** {trade.get('strategy_score', 'N/A')}")
                        st.write(f"**Session:** {trade.get('session', 'N/A')}")
                    
                    with col_c:
                        exit_price = st.number_input(
                            "Exit Price",
                            value=float(trade['entry_price']),
                            key=f"exit_{trade['id']}"
                        )
                        
                        if st.button("Close Trade", key=f"close_{trade['id']}"):
                            result = bot.close(trade['id'], exit_price)
                            if result['success']:
                                st.success(f"Trade closed! P&L: ${result['pnl']:.2f}")
                                st.rerun()
        else:
            st.info("No open trades")
    
    # History Tab
    with tab3:
        st.subheader("Trade History")
        
        trades_df = db.get_trades(limit=100)
        
        if not trades_df.empty:
            # Summary metrics
            col1, col2, col3, col4 = st.columns(4)
            
            wins = (trades_df['outcome'] == 'WIN').sum()
            losses = (trades_df['outcome'] == 'LOSS').sum()
            total_pnl = trades_df['pnl'].sum()
            
            with col1:
                st.metric("Wins", wins)
            with col2:
                st.metric("Losses", losses)
            with col3:
                st.metric("Win Rate", f"{wins/(wins+losses)*100:.1f}%" if (wins+losses) > 0 else "N/A")
            with col4:
                st.metric("Total P&L", f"${total_pnl:.2f}")
            
            # P&L chart
            if 'entry_time' in trades_df.columns:
                trades_df['entry_time'] = pd.to_datetime(trades_df['entry_time'])
                trades_df = trades_df.sort_values('entry_time')
                trades_df['cumulative_pnl'] = trades_df['pnl'].cumsum()
                
                fig = go.Figure()
                fig.add_trace(go.Scatter(
                    x=trades_df['entry_time'],
                    y=trades_df['cumulative_pnl'],
                    mode='lines+markers',
                    name='Cumulative P&L',
                    line=dict(color='#1f77b4', width=2),
                    marker=dict(
                        color=trades_df['outcome'].map({'WIN': 'green', 'LOSS': 'red'}),
                        size=8
                    )
                ))
                fig.update_layout(
                    title='Cumulative P&L Over Time',
                    xaxis_title='Date',
                    yaxis_title='P&L ($)',
                    height=400
                )
                st.plotly_chart(fig, use_container_width=True)
            
            # Trade table
            display_cols = ['id', 'asset', 'direction', 'entry_price', 'exit_price', 
                          'pnl', 'outcome', 'strategy_score', 'entry_time']
            available_cols = [c for c in display_cols if c in trades_df.columns]
            
            st.dataframe(
                trades_df[available_cols].head(50),
                hide_index=True,
                use_container_width=True
            )
        else:
            st.info("No trade history yet. Start trading to see your history.")
    
    # Reports Tab
    with tab4:
        st.subheader("Performance Reports")
        
        report_type = st.radio(
            "Report Type",
            ["Daily", "Weekly"],
            horizontal=True
        )
        
        if st.button("Generate Report", type="primary"):
            if report_type == "Daily":
                report = bot.get_daily_report()
            else:
                report = bot.get_weekly_report()
            st.session_state['current_report'] = report
            st.session_state['report_type'] = report_type.lower()
        
        if 'current_report' in st.session_state:
            report = st.session_state['current_report']
            
            # Performance summary
            perf = report.get('performance', {}) if 'performance' in report else report.get('overview', {}).get('performance', {})
            
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric("Trades", f"{perf.get('wins', 0)}W / {perf.get('losses', 0)}L")
            with col2:
                st.metric("Win Rate", f"{perf.get('win_rate', 0):.1f}%")
            with col3:
                st.metric("Total P&L", f"${perf.get('total_pnl', 0):.2f}")
            with col4:
                st.metric("Profit Factor", f"{perf.get('profit_factor', 0):.2f}")
            
            # Mistakes
            mistakes = report.get('mistakes', [])
            if mistakes:
                st.subheader("❌ Mistakes Identified")
                for mistake in mistakes:
                    st.warning(f"**{mistake.get('type', 'Unknown')}**: {mistake.get('description', '')}")
                    st.caption(f"💡 {mistake.get('suggestion', '')}")
            
            # Improvements
            improvements = report.get('improvements', [])
            if improvements:
                st.subheader("💡 Improvement Suggestions")
                for imp in improvements:
                    st.info(imp)
            
            # Full report text
            with st.expander("📄 Full Report"):
                report_text = bot.reporter.format_report_text(report, st.session_state.get('report_type', 'daily'))
                st.code(report_text, language=None)
    
    # AI Insights Tab
    with tab5:
        st.subheader("AI Model Insights")
        
        ai_status = bot.ai_engine.get_model_status()
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("### Model Status")
            
            status_color = "🟢" if ai_status['is_trained'] else "🔴"
            st.write(f"**Status:** {status_color} {'Trained' if ai_status['is_trained'] else 'Not Trained'}")
            st.write(f"**Model Type:** {ai_status['model_type']}")
            st.write(f"**Min Training Samples:** {ai_status['min_training_samples']}")
            
            if ai_status['metrics']:
                st.markdown("### Model Metrics")
                metrics = ai_status['metrics']
                
                metric_col1, metric_col2 = st.columns(2)
                with metric_col1:
                    st.metric("Accuracy", f"{metrics.get('accuracy', 0)*100:.1f}%")
                    st.metric("Precision", f"{metrics.get('precision', 0)*100:.1f}%")
                with metric_col2:
                    st.metric("Recall", f"{metrics.get('recall', 0)*100:.1f}%")
                    st.metric("F1 Score", f"{metrics.get('f1_score', 0)*100:.1f}%")
                
                st.write(f"**Training Samples:** {metrics.get('training_samples', 0)}")
                st.write(f"**Last Trained:** {metrics.get('trained_at', 'Never')}")
        
        with col2:
            st.markdown("### Feature Importance")
            
            importance = ai_status.get('feature_importance', {})
            
            if importance:
                imp_df = pd.DataFrame([
                    {'Feature': k, 'Importance': v}
                    for k, v in sorted(importance.items(), key=lambda x: x[1], reverse=True)
                ])
                
                fig = px.bar(
                    imp_df,
                    x='Importance',
                    y='Feature',
                    orientation='h',
                    title='Feature Importance'
                )
                fig.update_layout(height=400)
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("Train the model to see feature importance")
        
        # Psychology Analysis
        st.markdown("---")
        st.subheader("🧠 Psychology Analysis")
        
        psych = bot.get_psychology_analysis()
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            discipline = psych['discipline_score']
            
            fig = go.Figure(go.Indicator(
                mode="gauge+number",
                value=discipline['score'],
                title={'text': "Discipline Score"},
                gauge={
                    'axis': {'range': [0, 100]},
                    'bar': {'color': "darkblue"},
                    'steps': [
                        {'range': [0, 60], 'color': "red"},
                        {'range': [60, 80], 'color': "yellow"},
                        {'range': [80, 100], 'color': "green"}
                    ]
                }
            ))
            fig.update_layout(height=250)
            st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            st.markdown("### Behavior Flags")
            
            if psych['overtrading']['is_overtrading']:
                st.error("⚠️ Overtrading Detected")
            else:
                st.success("✅ Trading Frequency OK")
            
            if psych['revenge_trading']['detected']:
                st.error(f"⚠️ Revenge Trading ({psych['revenge_trading']['instances']} instances)")
            else:
                st.success("✅ No Revenge Trading")
            
            if psych['emotional_clusters']['detected']:
                st.warning(f"⚠️ Emotional Clusters ({psych['emotional_clusters']['clusters']})")
            else:
                st.success("✅ No Emotional Clusters")
        
        with col3:
            st.markdown("### Recommendations")
            
            for rec in psych.get('recommendations', [])[:5]:
                st.info(rec)
    
    # Footer
    st.markdown("---")
    st.markdown("""
    <div style="text-align: center; color: #666; font-size: 0.8rem;">
        <p>MarketSense AI - Educational Trading Intelligence Bot</p>
        <p>⚠️ This is a simulation tool for learning purposes only. Not financial advice.</p>
    </div>
    """, unsafe_allow_html=True)


if __name__ == "__main__":
    main()
