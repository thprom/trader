#!/usr/bin/env python3
"""
MarketSense AI - Real-Time Trading Signal Web App
Interactive dashboard with live candlestick chart and BUY/SELL markers.
"""

import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from flask import Flask, render_template, jsonify, request
from datetime import datetime, timedelta
import json
import threading
import time
import numpy as np

from live_data import get_signal_generator, get_live_data_fetcher

app = Flask(__name__)

# Global cache for signals
signal_cache = {}
cache_lock = threading.Lock()

def get_generator():
    return get_signal_generator()

def get_fetcher():
    return get_live_data_fetcher()


def calculate_trade_duration(signal: dict, volatility: float = None) -> dict:
    """
    Calculate recommended trade duration based on analysis.
    Returns duration in seconds (30s to 5min).
    """
    score = signal.get('score', 50)
    confidence = signal.get('confidence', 'MEDIUM')
    probability = signal.get('probability', 50)
    timeframe = signal.get('timeframe', '5m')
    
    # Base duration based on timeframe
    tf_base = {
        '1m': 60,    # 1 minute base
        '5m': 180,   # 3 minute base
        '15m': 300,  # 5 minute base
    }
    base_duration = tf_base.get(timeframe, 120)
    
    # Adjust based on score
    if score >= 75:
        # High score = can hold longer
        duration_multiplier = 1.2
    elif score >= 60:
        duration_multiplier = 1.0
    elif score >= 50:
        # Lower score = shorter duration safer
        duration_multiplier = 0.7
    else:
        duration_multiplier = 0.5
    
    # Adjust based on confidence
    confidence_adj = {
        'HIGH': 1.2,
        'MEDIUM': 1.0,
        'LOW': 0.7
    }
    duration_multiplier *= confidence_adj.get(confidence, 1.0)
    
    # Calculate final duration
    duration = int(base_duration * duration_multiplier)
    
    # Clamp to 30 seconds - 5 minutes
    duration = max(30, min(300, duration))
    
    # Round to nice values
    if duration <= 45:
        duration = 30
    elif duration <= 75:
        duration = 60
    elif duration <= 105:
        duration = 90
    elif duration <= 150:
        duration = 120
    elif duration <= 210:
        duration = 180
    elif duration <= 270:
        duration = 240
    else:
        duration = 300
    
    # Format for display
    if duration < 60:
        duration_text = f"{duration} seconds"
    else:
        minutes = duration // 60
        seconds = duration % 60
        if seconds == 0:
            duration_text = f"{minutes} minute{'s' if minutes > 1 else ''}"
        else:
            duration_text = f"{minutes}m {seconds}s"
    
    return {
        'seconds': duration,
        'text': duration_text,
        'reason': f"Based on {confidence.lower()} confidence and {score:.0f} score"
    }


@app.route('/')
def index():
    """Main dashboard page."""
    return render_template('index.html')


@app.route('/api/assets')
def get_assets():
    """Get list of available assets."""
    fetcher = get_fetcher()
    assets = fetcher.get_available_assets()
    
    # Group by category
    grouped = {
        'forex': [],
        'crypto': [],
        'commodities': [],
        'indices': []
    }
    
    for asset in assets:
        if 'BTC' in asset or 'ETH' in asset or 'XRP' in asset or 'LTC' in asset or 'DOGE' in asset:
            grouped['crypto'].append(asset)
        elif asset in ['GOLD', 'SILVER', 'OIL']:
            grouped['commodities'].append(asset)
        elif 'US' in asset and '/' not in asset:
            grouped['indices'].append(asset)
        else:
            grouped['forex'].append(asset)
    
    return jsonify(grouped)


@app.route('/api/signal/<asset>')
def get_signal(asset):
    """Get trading signal for a specific asset."""
    timeframe = request.args.get('timeframe', '5m')
    
    # Check cache first (valid for 10 seconds)
    cache_key = f"{asset}_{timeframe}"
    with cache_lock:
        if cache_key in signal_cache:
            cached = signal_cache[cache_key]
            if (datetime.now() - cached['cached_at']).seconds < 10:
                return jsonify(cached['signal'])
    
    # Generate new signal
    generator = get_generator()
    signal = generator.generate_signal(asset, timeframe)
    
    # Add trade duration recommendation
    signal['trade_duration'] = calculate_trade_duration(signal)
    
    # Cache it
    with cache_lock:
        signal_cache[cache_key] = {
            'signal': signal,
            'cached_at': datetime.now()
        }
    
    return jsonify(signal)


@app.route('/api/candles/<asset>')
def get_candles(asset):
    """Get candle data for chart."""
    timeframe = request.args.get('timeframe', '5m')
    
    fetcher = get_fetcher()
    df = fetcher.fetch_live_data(asset, timeframe)
    
    if df.empty:
        return jsonify({'error': True, 'message': 'No data available'})
    
    # Convert to list of candles for chart
    candles = []
    for _, row in df.iterrows():
        candles.append({
            'time': int(row['timestamp'].timestamp()),
            'open': float(row['open']),
            'high': float(row['high']),
            'low': float(row['low']),
            'close': float(row['close']),
            'volume': float(row.get('volume', 0))
        })
    
    return jsonify({
        'candles': candles,
        'asset': asset,
        'timeframe': timeframe
    })


@app.route('/api/signals_history/<asset>')
def get_signals_history(asset):
    """Get historical signals for chart markers."""
    timeframe = request.args.get('timeframe', '5m')
    
    fetcher = get_fetcher()
    generator = get_generator()
    
    df = fetcher.fetch_live_data(asset, timeframe)
    
    if df.empty or len(df) < 30:
        return jsonify({'signals': []})
    
    # Generate current signal
    signal = generator.generate_signal(asset, timeframe)
    
    # Add trade duration
    signal['trade_duration'] = calculate_trade_duration(signal)
    
    # Create marker for current candle
    markers = []
    if signal['signal'] in ['BUY', 'SELL']:
        last_candle = df.iloc[-1]
        markers.append({
            'time': int(last_candle['timestamp'].timestamp()),
            'position': 'aboveBar' if signal['signal'] == 'BUY' else 'belowBar',
            'color': '#00d26a' if signal['signal'] == 'BUY' else '#ff4757',
            'shape': 'arrowUp' if signal['signal'] == 'BUY' else 'arrowDown',
            'text': f"{signal['signal']} {signal['trade_duration']['text']}",
            'signal': signal['signal'],
            'direction': signal.get('direction'),
            'duration': signal['trade_duration'],
            'score': signal['score'],
            'probability': signal['probability']
        })
    
    return jsonify({
        'signals': markers,
        'current_signal': signal
    })


@app.route('/api/scan')
def scan_markets():
    """Scan all markets for opportunities."""
    timeframe = request.args.get('timeframe', '5m')
    min_score = float(request.args.get('min_score', 50))
    
    generator = get_generator()
    opportunities = generator.get_best_opportunities(timeframe, min_score)
    
    # Add trade duration to each
    for opp in opportunities:
        opp['trade_duration'] = calculate_trade_duration(opp)
    
    return jsonify(opportunities)


@app.route('/api/quick_signals')
def quick_signals():
    """Get quick signals for all forex pairs."""
    fetcher = get_fetcher()
    generator = get_generator()
    
    assets = fetcher.get_available_assets()
    timeframe = request.args.get('timeframe', '5m')
    
    results = []
    forex_assets = [a for a in assets if '/' in a and 'BTC' not in a][:10]
    
    for asset in forex_assets:
        try:
            cache_key = f"{asset}_{timeframe}"
            with cache_lock:
                if cache_key in signal_cache:
                    cached = signal_cache[cache_key]
                    if (datetime.now() - cached['cached_at']).seconds < 30:
                        signal = cached['signal']
                        results.append({
                            'asset': asset,
                            'signal': signal['signal'],
                            'direction': signal.get('direction'),
                            'score': signal['score'],
                            'probability': signal['probability'],
                            'price': signal['price'],
                            'duration': signal.get('trade_duration', {}).get('text', 'N/A')
                        })
                        continue
            
            signal = generator.generate_signal(asset, timeframe)
            signal['trade_duration'] = calculate_trade_duration(signal)
            
            with cache_lock:
                signal_cache[cache_key] = {
                    'signal': signal,
                    'cached_at': datetime.now()
                }
            
            results.append({
                'asset': asset,
                'signal': signal['signal'],
                'direction': signal.get('direction'),
                'score': signal['score'],
                'probability': signal['probability'],
                'price': signal['price'],
                'duration': signal['trade_duration']['text']
            })
            
        except Exception as e:
            print(f"Error getting signal for {asset}: {e}")
    
    return jsonify(results)


@app.route('/api/market_status')
def market_status():
    """Get current market status."""
    fetcher = get_fetcher()
    status = fetcher.get_market_status()
    return jsonify(status)


# Create templates directory and HTML file
TEMPLATE_DIR = os.path.join(os.path.dirname(__file__), 'templates')
os.makedirs(TEMPLATE_DIR, exist_ok=True)

HTML_TEMPLATE = '''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>MarketSense AI - Live Trading Signals</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css" rel="stylesheet">
    <script src="https://unpkg.com/lightweight-charts@4.1.0/dist/lightweight-charts.standalone.production.js"></script>
    <style>
        :root {
            --bg-dark: #0f0f1a;
            --bg-card: #1a1a2e;
            --bg-chart: #131722;
            --accent: #0f3460;
            --buy-color: #00d26a;
            --sell-color: #ff4757;
            --wait-color: #ffa502;
            --text-primary: #ffffff;
            --text-secondary: #a0a0a0;
        }
        
        * { box-sizing: border-box; }
        
        body {
            background: var(--bg-dark);
            color: var(--text-primary);
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            min-height: 100vh;
            margin: 0;
            overflow-x: hidden;
        }
        
        .header {
            background: linear-gradient(135deg, var(--bg-card), var(--accent));
            padding: 0.8rem 1.5rem;
            border-bottom: 1px solid rgba(255,255,255,0.1);
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        
        .logo {
            font-size: 1.3rem;
            font-weight: bold;
            background: linear-gradient(90deg, #00d26a, #0099ff);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }
        
        .live-indicator {
            display: inline-block;
            width: 8px;
            height: 8px;
            background: var(--buy-color);
            border-radius: 50%;
            margin-right: 5px;
            animation: pulse 1s infinite;
        }
        
        @keyframes pulse {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.5; }
        }
        
        .main-container {
            display: flex;
            height: calc(100vh - 60px);
        }
        
        .sidebar {
            width: 220px;
            background: var(--bg-card);
            border-right: 1px solid rgba(255,255,255,0.1);
            overflow-y: auto;
        }
        
        .asset-search {
            padding: 10px;
            position: sticky;
            top: 0;
            background: var(--bg-card);
            z-index: 10;
        }
        
        .asset-search input {
            width: 100%;
            padding: 8px 12px;
            background: var(--bg-dark);
            border: 1px solid rgba(255,255,255,0.1);
            border-radius: 5px;
            color: var(--text-primary);
            font-size: 0.85rem;
        }
        
        .category-header {
            padding: 8px 12px;
            background: var(--accent);
            font-weight: bold;
            font-size: 0.75rem;
            text-transform: uppercase;
            color: var(--text-secondary);
        }
        
        .asset-item {
            padding: 10px 12px;
            border-bottom: 1px solid rgba(255,255,255,0.05);
            cursor: pointer;
            transition: all 0.2s;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        
        .asset-item:hover { background: rgba(255,255,255,0.05); }
        .asset-item.active { background: var(--accent); border-left: 3px solid var(--buy-color); }
        
        .asset-name { font-weight: 600; font-size: 0.85rem; }
        .asset-price { font-size: 0.75rem; color: var(--text-secondary); }
        
        .signal-badge {
            padding: 2px 8px;
            border-radius: 10px;
            font-size: 0.65rem;
            font-weight: bold;
        }
        
        .signal-buy { background: var(--buy-color); color: #000; }
        .signal-sell { background: var(--sell-color); color: #fff; }
        .signal-wait { background: var(--wait-color); color: #000; }
        .signal-notrade { background: #6c757d; color: #fff; }
        
        .chart-container {
            flex: 1;
            display: flex;
            flex-direction: column;
            background: var(--bg-chart);
        }
        
        .chart-header {
            padding: 10px 15px;
            background: var(--bg-card);
            display: flex;
            justify-content: space-between;
            align-items: center;
            border-bottom: 1px solid rgba(255,255,255,0.1);
        }
        
        .chart-title {
            font-size: 1.1rem;
            font-weight: bold;
        }
        
        .timeframe-btns button {
            background: var(--bg-dark);
            border: 1px solid rgba(255,255,255,0.1);
            color: var(--text-primary);
            padding: 5px 12px;
            margin: 0 3px;
            border-radius: 4px;
            cursor: pointer;
            font-size: 0.8rem;
        }
        
        .timeframe-btns button:hover,
        .timeframe-btns button.active {
            background: var(--buy-color);
            color: #000;
            border-color: var(--buy-color);
        }
        
        #chart {
            flex: 1;
            width: 100%;
        }
        
        .signal-panel {
            width: 320px;
            background: var(--bg-card);
            border-left: 1px solid rgba(255,255,255,0.1);
            overflow-y: auto;
            padding: 15px;
        }
        
        .signal-box {
            padding: 20px;
            border-radius: 12px;
            text-align: center;
            margin-bottom: 15px;
        }
        
        .signal-box.buy { background: linear-gradient(135deg, rgba(0,210,106,0.3), rgba(0,210,106,0.1)); border: 2px solid var(--buy-color); }
        .signal-box.sell { background: linear-gradient(135deg, rgba(255,71,87,0.3), rgba(255,71,87,0.1)); border: 2px solid var(--sell-color); }
        .signal-box.wait { background: linear-gradient(135deg, rgba(255,165,2,0.3), rgba(255,165,2,0.1)); border: 2px solid var(--wait-color); }
        .signal-box.notrade { background: linear-gradient(135deg, rgba(108,117,125,0.3), rgba(108,117,125,0.1)); border: 2px solid #6c757d; }
        
        .signal-action {
            font-size: 2rem;
            font-weight: bold;
            margin: 5px 0;
        }
        
        .signal-action.buy { color: var(--buy-color); }
        .signal-action.sell { color: var(--sell-color); }
        .signal-action.wait { color: var(--wait-color); }
        .signal-action.notrade { color: #6c757d; }
        
        .duration-box {
            background: var(--bg-dark);
            border-radius: 10px;
            padding: 15px;
            margin: 15px 0;
            text-align: center;
        }
        
        .duration-value {
            font-size: 2rem;
            font-weight: bold;
            color: var(--buy-color);
        }
        
        .duration-label {
            font-size: 0.8rem;
            color: var(--text-secondary);
            text-transform: uppercase;
        }
        
        .metrics-grid {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 10px;
            margin: 15px 0;
        }
        
        .metric-card {
            background: var(--bg-dark);
            border-radius: 8px;
            padding: 12px;
            text-align: center;
        }
        
        .metric-value {
            font-size: 1.3rem;
            font-weight: bold;
        }
        
        .metric-label {
            font-size: 0.7rem;
            color: var(--text-secondary);
            text-transform: uppercase;
        }
        
        .reason-item {
            padding: 8px 10px;
            margin: 5px 0;
            border-radius: 5px;
            font-size: 0.8rem;
            background: rgba(255,255,255,0.05);
        }
        
        .reason-positive { border-left: 3px solid var(--buy-color); }
        .reason-negative { border-left: 3px solid var(--sell-color); }
        .reason-warning { border-left: 3px solid var(--wait-color); }
        
        .action-steps {
            background: var(--bg-dark);
            border-radius: 10px;
            padding: 15px;
            margin-top: 15px;
        }
        
        .action-step {
            display: flex;
            align-items: center;
            margin: 8px 0;
            font-size: 0.85rem;
        }
        
        .step-num {
            width: 24px;
            height: 24px;
            background: var(--buy-color);
            color: #000;
            border-radius: 50%;
            display: flex;
            justify-content: center;
            align-items: center;
            font-weight: bold;
            font-size: 0.75rem;
            margin-right: 10px;
            flex-shrink: 0;
        }
        
        .loading {
            display: flex;
            justify-content: center;
            align-items: center;
            height: 100%;
        }
        
        .spinner {
            width: 40px;
            height: 40px;
            border: 3px solid var(--accent);
            border-top-color: var(--buy-color);
            border-radius: 50%;
            animation: spin 1s linear infinite;
        }
        
        @keyframes spin { to { transform: rotate(360deg); } }
        
        .chart-signal-overlay {
            position: absolute;
            top: 60px;
            left: 50%;
            transform: translateX(-50%);
            z-index: 100;
            padding: 10px 25px;
            border-radius: 8px;
            font-weight: bold;
            font-size: 1.1rem;
            display: none;
            animation: fadeIn 0.3s;
        }
        
        .chart-signal-overlay.buy {
            background: var(--buy-color);
            color: #000;
        }
        
        .chart-signal-overlay.sell {
            background: var(--sell-color);
            color: #fff;
        }
        
        @keyframes fadeIn {
            from { opacity: 0; transform: translateX(-50%) translateY(-10px); }
            to { opacity: 1; transform: translateX(-50%) translateY(0); }
        }
        
        .refresh-btn {
            background: var(--buy-color);
            border: none;
            color: #000;
            padding: 8px 15px;
            border-radius: 5px;
            cursor: pointer;
            font-weight: bold;
            font-size: 0.85rem;
        }
        
        .refresh-btn:hover { opacity: 0.9; }
    </style>
</head>
<body>
    <div class="header">
        <div class="logo">
            <i class="fas fa-chart-line me-2"></i>MarketSense AI
        </div>
        <div style="display: flex; align-items: center; gap: 15px;">
            <div>
                <span class="live-indicator"></span>
                <span style="font-size: 0.85rem;">LIVE</span>
            </div>
            <span id="countdown" style="font-size: 0.8rem; color: var(--text-secondary);">Next update: 10s</span>
            <button class="refresh-btn" onclick="refreshAll()">
                <i class="fas fa-sync-alt me-1"></i>Refresh
            </button>
        </div>
    </div>
    
    <div class="main-container">
        <!-- Asset List Sidebar -->
        <div class="sidebar">
            <div class="asset-search">
                <input type="text" id="searchAsset" placeholder="Search asset...">
            </div>
            <div id="assetList">
                <div class="loading"><div class="spinner"></div></div>
            </div>
        </div>
        
        <!-- Chart Area -->
        <div class="chart-container">
            <div class="chart-header">
                <div class="chart-title" id="chartTitle">EUR/USD</div>
                <div class="timeframe-btns">
                    <button data-tf="1m">1M</button>
                    <button data-tf="5m" class="active">5M</button>
                    <button data-tf="15m">15M</button>
                </div>
            </div>
            <div id="chart"></div>
            <div class="chart-signal-overlay" id="chartSignalOverlay"></div>
        </div>
        
        <!-- Signal Panel -->
        <div class="signal-panel">
            <div id="signalContent">
                <div class="loading"><div class="spinner"></div></div>
            </div>
        </div>
    </div>
    
    <script>
        let selectedAsset = 'EUR/USD';
        let selectedTimeframe = '5m';
        let chart = null;
        let candleSeries = null;
        let countdownValue = 10;
        let refreshTimer = null;
        
        // Initialize
        document.addEventListener('DOMContentLoaded', function() {
            initChart();
            loadAssets();
            startAutoRefresh();
            
            // Timeframe buttons
            document.querySelectorAll('.timeframe-btns button').forEach(btn => {
                btn.addEventListener('click', function() {
                    document.querySelectorAll('.timeframe-btns button').forEach(b => b.classList.remove('active'));
                    this.classList.add('active');
                    selectedTimeframe = this.dataset.tf;
                    loadChartData();
                    loadSignal();
                });
            });
            
            // Search
            document.getElementById('searchAsset').addEventListener('input', function() {
                filterAssets(this.value);
            });
        });
        
        function initChart() {
            const chartContainer = document.getElementById('chart');
            
            chart = LightweightCharts.createChart(chartContainer, {
                layout: {
                    background: { type: 'solid', color: '#131722' },
                    textColor: '#d1d4dc',
                },
                grid: {
                    vertLines: { color: 'rgba(42, 46, 57, 0.5)' },
                    horzLines: { color: 'rgba(42, 46, 57, 0.5)' },
                },
                crosshair: {
                    mode: LightweightCharts.CrosshairMode.Normal,
                },
                rightPriceScale: {
                    borderColor: 'rgba(197, 203, 206, 0.4)',
                },
                timeScale: {
                    borderColor: 'rgba(197, 203, 206, 0.4)',
                    timeVisible: true,
                    secondsVisible: false,
                },
            });
            
            candleSeries = chart.addCandlestickSeries({
                upColor: '#00d26a',
                downColor: '#ff4757',
                borderDownColor: '#ff4757',
                borderUpColor: '#00d26a',
                wickDownColor: '#ff4757',
                wickUpColor: '#00d26a',
            });
            
            // Resize handler
            window.addEventListener('resize', () => {
                chart.applyOptions({
                    width: chartContainer.clientWidth,
                    height: chartContainer.clientHeight
                });
            });
            
            // Initial size
            chart.applyOptions({
                width: chartContainer.clientWidth,
                height: chartContainer.clientHeight
            });
        }
        
        function loadAssets() {
            fetch('/api/assets')
                .then(r => r.json())
                .then(data => {
                    renderAssetList(data);
                    loadChartData();
                    loadSignal();
                });
        }
        
        function renderAssetList(grouped) {
            const container = document.getElementById('assetList');
            let html = '';
            
            const categories = {
                'forex': { name: 'Forex', icon: 'fa-dollar-sign' },
                'crypto': { name: 'Crypto', icon: 'fa-bitcoin' },
                'commodities': { name: 'Commodities', icon: 'fa-gem' },
                'indices': { name: 'Indices', icon: 'fa-chart-line' }
            };
            
            for (const [key, assets] of Object.entries(grouped)) {
                if (assets.length === 0) continue;
                
                html += `<div class="category-header">
                    <i class="fas ${categories[key].icon} me-2"></i>${categories[key].name}
                </div>`;
                
                for (const asset of assets) {
                    const isActive = asset === selectedAsset ? 'active' : '';
                    html += `
                        <div class="asset-item ${isActive}" data-asset="${asset}" onclick="selectAsset('${asset}')">
                            <div>
                                <div class="asset-name">${asset}</div>
                                <div class="asset-price" id="price-${asset.replace(/\\//g, '-')}">--</div>
                            </div>
                            <div id="badge-${asset.replace(/\\//g, '-')}">
                                <span class="signal-badge signal-wait">...</span>
                            </div>
                        </div>
                    `;
                }
            }
            
            container.innerHTML = html;
            loadQuickSignals();
        }
        
        function loadQuickSignals() {
            fetch(`/api/quick_signals?timeframe=${selectedTimeframe}`)
                .then(r => r.json())
                .then(signals => {
                    signals.forEach(s => {
                        const safeId = s.asset.replace(/\\//g, '-');
                        const badgeEl = document.getElementById(`badge-${safeId}`);
                        const priceEl = document.getElementById(`price-${safeId}`);
                        
                        if (badgeEl) {
                            let badgeClass = 'signal-wait';
                            let badgeText = 'WAIT';
                            
                            if (s.signal === 'BUY') {
                                badgeClass = 'signal-buy';
                                badgeText = 'BUY';
                            } else if (s.signal === 'SELL') {
                                badgeClass = 'signal-sell';
                                badgeText = 'SELL';
                            } else if (s.signal === 'DO NOT TRADE') {
                                badgeClass = 'signal-notrade';
                                badgeText = 'AVOID';
                            }
                            
                            badgeEl.innerHTML = `<span class="signal-badge ${badgeClass}">${badgeText}</span>`;
                        }
                        
                        if (priceEl && s.price) {
                            priceEl.textContent = parseFloat(s.price).toFixed(5);
                        }
                    });
                });
        }
        
        function selectAsset(asset) {
            selectedAsset = asset;
            document.getElementById('chartTitle').textContent = asset;
            
            document.querySelectorAll('.asset-item').forEach(el => {
                el.classList.remove('active');
                if (el.dataset.asset === asset) {
                    el.classList.add('active');
                }
            });
            
            loadChartData();
            loadSignal();
        }
        
        function loadChartData() {
            fetch(`/api/candles/${encodeURIComponent(selectedAsset)}?timeframe=${selectedTimeframe}`)
                .then(r => r.json())
                .then(data => {
                    if (data.candles && data.candles.length > 0) {
                        candleSeries.setData(data.candles);
                        chart.timeScale().fitContent();
                        
                        // Load signal markers
                        loadSignalMarkers();
                    }
                });
        }
        
        function loadSignalMarkers() {
            fetch(`/api/signals_history/${encodeURIComponent(selectedAsset)}?timeframe=${selectedTimeframe}`)
                .then(r => r.json())
                .then(data => {
                    if (data.signals && data.signals.length > 0) {
                        const markers = data.signals.map(s => ({
                            time: s.time,
                            position: s.position,
                            color: s.color,
                            shape: s.shape,
                            text: s.text
                        }));
                        candleSeries.setMarkers(markers);
                        
                        // Show overlay
                        const overlay = document.getElementById('chartSignalOverlay');
                        const sig = data.signals[0];
                        if (sig.signal === 'BUY') {
                            overlay.className = 'chart-signal-overlay buy';
                            overlay.innerHTML = `<i class="fas fa-arrow-up me-2"></i>BUY (CALL) - ${sig.duration.text}`;
                            overlay.style.display = 'block';
                        } else if (sig.signal === 'SELL') {
                            overlay.className = 'chart-signal-overlay sell';
                            overlay.innerHTML = `<i class="fas fa-arrow-down me-2"></i>SELL (PUT) - ${sig.duration.text}`;
                            overlay.style.display = 'block';
                        } else {
                            overlay.style.display = 'none';
                        }
                    } else {
                        candleSeries.setMarkers([]);
                        document.getElementById('chartSignalOverlay').style.display = 'none';
                    }
                });
        }
        
        function loadSignal() {
            const container = document.getElementById('signalContent');
            container.innerHTML = '<div class="loading"><div class="spinner"></div></div>';
            
            fetch(`/api/signal/${encodeURIComponent(selectedAsset)}?timeframe=${selectedTimeframe}`)
                .then(r => r.json())
                .then(signal => {
                    renderSignalPanel(signal);
                });
        }
        
        function renderSignalPanel(signal) {
            const container = document.getElementById('signalContent');
            
            let signalClass = 'wait';
            let actionText = 'WAIT';
            let actionIcon = 'fa-clock';
            let directionText = '';
            
            if (signal.signal === 'BUY') {
                signalClass = 'buy';
                actionText = 'BUY';
                actionIcon = 'fa-arrow-up';
                directionText = 'CALL (UP)';
            } else if (signal.signal === 'SELL') {
                signalClass = 'sell';
                actionText = 'SELL';
                actionIcon = 'fa-arrow-down';
                directionText = 'PUT (DOWN)';
            } else if (signal.signal === 'DO NOT TRADE') {
                signalClass = 'notrade';
                actionText = 'AVOID';
                actionIcon = 'fa-ban';
                directionText = 'DO NOT TRADE';
            }
            
            const duration = signal.trade_duration || { text: 'N/A', seconds: 0 };
            
            let reasonsHtml = '';
            if (signal.reasons) {
                signal.reasons.slice(0, 5).forEach(r => {
                    let rClass = 'reason-warning';
                    if (r.includes('✅') || r.includes('📈')) rClass = 'reason-positive';
                    else if (r.includes('❌') || r.includes('📉')) rClass = 'reason-negative';
                    reasonsHtml += `<div class="reason-item ${rClass}">${r}</div>`;
                });
            }
            
            let stepsHtml = '';
            if (signal.signal === 'BUY' || signal.signal === 'SELL') {
                const dir = signal.signal === 'BUY' ? 'CALL (UP)' : 'PUT (DOWN)';
                stepsHtml = `
                    <div class="action-steps">
                        <div style="font-weight: bold; margin-bottom: 10px;"><i class="fas fa-list-ol me-2"></i>Trade Now</div>
                        <div class="action-step"><div class="step-num">1</div>Open Pocket Option</div>
                        <div class="action-step"><div class="step-num">2</div>Select ${signal.asset}</div>
                        <div class="action-step"><div class="step-num">3</div>Set time to <strong>${duration.text}</strong></div>
                        <div class="action-step"><div class="step-num">4</div>Click <strong style="color: ${signalClass === 'buy' ? 'var(--buy-color)' : 'var(--sell-color)'}">${dir}</strong></div>
                    </div>
                `;
            } else {
                stepsHtml = `
                    <div class="action-steps" style="text-align: center;">
                        <i class="fas fa-hand-paper fa-2x mb-2" style="color: var(--wait-color);"></i>
                        <div>Wait for a better setup</div>
                        <div style="font-size: 0.8rem; color: var(--text-secondary); margin-top: 5px;">Check other assets or wait</div>
                    </div>
                `;
            }
            
            container.innerHTML = `
                <div class="signal-box ${signalClass}">
                    <div style="font-size: 0.8rem; color: var(--text-secondary);">${signal.asset} • ${signal.timeframe}</div>
                    <div class="signal-action ${signalClass}">
                        <i class="fas ${actionIcon} me-2"></i>${actionText}
                    </div>
                    ${directionText ? `<div style="font-size: 1.1rem;">${directionText}</div>` : ''}
                </div>
                
                ${signal.signal === 'BUY' || signal.signal === 'SELL' ? `
                <div class="duration-box">
                    <div class="duration-label">Recommended Duration</div>
                    <div class="duration-value">${duration.text}</div>
                    <div style="font-size: 0.75rem; color: var(--text-secondary);">${duration.reason || ''}</div>
                </div>
                ` : ''}
                
                <div class="metrics-grid">
                    <div class="metric-card">
                        <div class="metric-value">${signal.price}</div>
                        <div class="metric-label">Price</div>
                    </div>
                    <div class="metric-card">
                        <div class="metric-value">${Math.round(signal.score)}</div>
                        <div class="metric-label">Score</div>
                    </div>
                    <div class="metric-card">
                        <div class="metric-value">${Math.round(signal.probability)}%</div>
                        <div class="metric-label">Probability</div>
                    </div>
                    <div class="metric-card">
                        <div class="metric-value">${signal.confidence}</div>
                        <div class="metric-label">Confidence</div>
                    </div>
                </div>
                
                <div style="margin-top: 15px;">
                    <div style="font-weight: bold; font-size: 0.85rem; margin-bottom: 8px;">
                        <i class="fas fa-list-check me-2"></i>Analysis
                    </div>
                    ${reasonsHtml || '<div class="text-secondary" style="font-size: 0.8rem;">No specific signals</div>'}
                </div>
                
                ${stepsHtml}
                
                <div style="margin-top: 15px; text-align: center; font-size: 0.75rem; color: var(--text-secondary);">
                    Updated: ${new Date(signal.timestamp).toLocaleTimeString()}
                </div>
            `;
        }
        
        function filterAssets(query) {
            query = query.toLowerCase();
            document.querySelectorAll('.asset-item').forEach(el => {
                const asset = el.dataset.asset.toLowerCase();
                el.style.display = asset.includes(query) ? 'flex' : 'none';
            });
        }
        
        function refreshAll() {
            loadChartData();
            loadSignal();
            loadQuickSignals();
            countdownValue = 10;
        }
        
        function startAutoRefresh() {
            setInterval(() => {
                countdownValue--;
                document.getElementById('countdown').textContent = `Next update: ${countdownValue}s`;
                
                if (countdownValue <= 0) {
                    refreshAll();
                }
            }, 1000);
        }
    </script>
</body>
</html>'''

# Write the template
with open(os.path.join(TEMPLATE_DIR, 'index.html'), 'w') as f:
    f.write(HTML_TEMPLATE)


if __name__ == '__main__':
    print("\n" + "="*60)
    print("  🎯 MarketSense AI - Live Trading Signals")
    print("="*60)
    print("\n  Starting web server...")
    print("  Open your browser and go to: http://localhost:5000")
    print("\n  Press Ctrl+C to stop the server")
    print("="*60 + "\n")
    
    app.run(host='0.0.0.0', port=5000, debug=False, threaded=True)
