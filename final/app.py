#!/usr/bin/env python3
"""
MarketSense AI - Real-Time Trading Signal Web App
Interactive dashboard with live asset list and instant BUY/SELL signals.
"""

import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from flask import Flask, render_template, jsonify, request
from datetime import datetime
import json
import threading
import time

from live_data import get_signal_generator, get_live_data_fetcher

app = Flask(__name__)

# Global cache for signals
signal_cache = {}
cache_lock = threading.Lock()

def get_generator():
    return get_signal_generator()

def get_fetcher():
    return get_live_data_fetcher()


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
    
    # Cache it
    with cache_lock:
        signal_cache[cache_key] = {
            'signal': signal,
            'cached_at': datetime.now()
        }
    
    return jsonify(signal)


@app.route('/api/scan')
def scan_markets():
    """Scan all markets for opportunities."""
    timeframe = request.args.get('timeframe', '5m')
    min_score = float(request.args.get('min_score', 50))
    
    generator = get_generator()
    opportunities = generator.get_best_opportunities(timeframe, min_score)
    
    return jsonify(opportunities)


@app.route('/api/quick_signals')
def quick_signals():
    """Get quick signals for all forex pairs (for the asset list)."""
    fetcher = get_fetcher()
    generator = get_generator()
    
    assets = fetcher.get_available_assets()
    timeframe = request.args.get('timeframe', '5m')
    
    results = []
    
    # Only get forex pairs for speed
    forex_assets = [a for a in assets if '/' in a and 'BTC' not in a][:10]
    
    for asset in forex_assets:
        try:
            # Check cache
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
                            'price': signal['price']
                        })
                        continue
            
            # Generate new signal
            signal = generator.generate_signal(asset, timeframe)
            
            # Cache it
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
                'price': signal['price']
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


@app.route('/api/price/<asset>')
def get_price(asset):
    """Get current price for an asset."""
    fetcher = get_fetcher()
    price_info = fetcher.fetch_current_price(asset)
    return jsonify(price_info)


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
    <style>
        :root {
            --bg-dark: #1a1a2e;
            --bg-card: #16213e;
            --accent: #0f3460;
            --buy-color: #00d26a;
            --sell-color: #ff4757;
            --wait-color: #ffa502;
            --text-primary: #ffffff;
            --text-secondary: #a0a0a0;
        }
        
        body {
            background: var(--bg-dark);
            color: var(--text-primary);
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            min-height: 100vh;
        }
        
        .header {
            background: linear-gradient(135deg, var(--bg-card), var(--accent));
            padding: 1rem 2rem;
            border-bottom: 1px solid rgba(255,255,255,0.1);
        }
        
        .logo {
            font-size: 1.5rem;
            font-weight: bold;
            background: linear-gradient(90deg, #00d26a, #0099ff);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }
        
        .live-indicator {
            display: inline-block;
            width: 10px;
            height: 10px;
            background: var(--buy-color);
            border-radius: 50%;
            margin-right: 5px;
            animation: pulse 1s infinite;
        }
        
        @keyframes pulse {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.5; }
        }
        
        .asset-list {
            background: var(--bg-card);
            border-radius: 10px;
            overflow: hidden;
        }
        
        .asset-item {
            padding: 12px 15px;
            border-bottom: 1px solid rgba(255,255,255,0.05);
            cursor: pointer;
            transition: all 0.2s;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        
        .asset-item:hover {
            background: var(--accent);
        }
        
        .asset-item.active {
            background: var(--accent);
            border-left: 3px solid var(--buy-color);
        }
        
        .asset-name {
            font-weight: 600;
            font-size: 0.95rem;
        }
        
        .asset-price {
            font-size: 0.85rem;
            color: var(--text-secondary);
        }
        
        .signal-badge {
            padding: 4px 10px;
            border-radius: 20px;
            font-size: 0.75rem;
            font-weight: bold;
            text-transform: uppercase;
        }
        
        .signal-buy { background: var(--buy-color); color: #000; }
        .signal-sell { background: var(--sell-color); color: #fff; }
        .signal-wait { background: var(--wait-color); color: #000; }
        .signal-notrade { background: #6c757d; color: #fff; }
        
        .main-signal {
            background: var(--bg-card);
            border-radius: 15px;
            padding: 2rem;
            text-align: center;
        }
        
        .signal-action {
            font-size: 3rem;
            font-weight: bold;
            margin: 1rem 0;
        }
        
        .signal-action.buy { color: var(--buy-color); }
        .signal-action.sell { color: var(--sell-color); }
        .signal-action.wait { color: var(--wait-color); }
        .signal-action.notrade { color: #6c757d; }
        
        .metric-card {
            background: var(--accent);
            border-radius: 10px;
            padding: 1rem;
            text-align: center;
        }
        
        .metric-value {
            font-size: 1.8rem;
            font-weight: bold;
        }
        
        .metric-label {
            font-size: 0.8rem;
            color: var(--text-secondary);
            text-transform: uppercase;
        }
        
        .reason-item {
            padding: 8px 12px;
            margin: 5px 0;
            border-radius: 5px;
            font-size: 0.9rem;
        }
        
        .reason-positive { background: rgba(0, 210, 106, 0.2); border-left: 3px solid var(--buy-color); }
        .reason-negative { background: rgba(255, 71, 87, 0.2); border-left: 3px solid var(--sell-color); }
        .reason-warning { background: rgba(255, 165, 2, 0.2); border-left: 3px solid var(--wait-color); }
        .reason-neutral { background: rgba(255, 255, 255, 0.1); border-left: 3px solid #6c757d; }
        
        .category-header {
            padding: 10px 15px;
            background: var(--accent);
            font-weight: bold;
            font-size: 0.85rem;
            text-transform: uppercase;
            color: var(--text-secondary);
        }
        
        .countdown {
            font-size: 0.9rem;
            color: var(--text-secondary);
        }
        
        .timeframe-btn {
            background: var(--accent);
            border: none;
            color: var(--text-primary);
            padding: 8px 16px;
            border-radius: 5px;
            margin: 0 5px;
            cursor: pointer;
            transition: all 0.2s;
        }
        
        .timeframe-btn:hover, .timeframe-btn.active {
            background: var(--buy-color);
            color: #000;
        }
        
        .loading {
            display: flex;
            justify-content: center;
            align-items: center;
            height: 200px;
        }
        
        .spinner {
            width: 50px;
            height: 50px;
            border: 3px solid var(--accent);
            border-top-color: var(--buy-color);
            border-radius: 50%;
            animation: spin 1s linear infinite;
        }
        
        @keyframes spin {
            to { transform: rotate(360deg); }
        }
        
        .action-guide {
            background: var(--accent);
            border-radius: 10px;
            padding: 1.5rem;
            margin-top: 1rem;
        }
        
        .action-step {
            display: flex;
            align-items: center;
            margin: 10px 0;
        }
        
        .step-number {
            width: 30px;
            height: 30px;
            background: var(--buy-color);
            color: #000;
            border-radius: 50%;
            display: flex;
            justify-content: center;
            align-items: center;
            font-weight: bold;
            margin-right: 10px;
        }
        
        .refresh-btn {
            background: var(--buy-color);
            border: none;
            color: #000;
            padding: 10px 20px;
            border-radius: 5px;
            font-weight: bold;
            cursor: pointer;
            transition: all 0.2s;
        }
        
        .refresh-btn:hover {
            transform: scale(1.05);
        }
    </style>
</head>
<body>
    <div class="header d-flex justify-content-between align-items-center">
        <div class="logo">
            <i class="fas fa-chart-line me-2"></i>MarketSense AI
        </div>
        <div>
            <span class="live-indicator"></span>
            <span>LIVE</span>
            <span class="ms-3 countdown" id="countdown">Updating in 10s</span>
        </div>
    </div>
    
    <div class="container-fluid py-4">
        <div class="row">
            <!-- Asset List -->
            <div class="col-md-3">
                <div class="mb-3">
                    <input type="text" class="form-control bg-dark text-white border-secondary" 
                           id="searchAsset" placeholder="Search asset...">
                </div>
                
                <div class="asset-list" id="assetList">
                    <div class="loading">
                        <div class="spinner"></div>
                    </div>
                </div>
            </div>
            
            <!-- Main Signal Display -->
            <div class="col-md-6">
                <div class="d-flex justify-content-center mb-3">
                    <button class="timeframe-btn active" data-tf="1m">1M</button>
                    <button class="timeframe-btn" data-tf="5m">5M</button>
                    <button class="timeframe-btn" data-tf="15m">15M</button>
                </div>
                
                <div class="main-signal" id="mainSignal">
                    <div class="text-secondary">Select an asset to see signal</div>
                </div>
                
                <div class="action-guide" id="actionGuide" style="display: none;">
                    <h5><i class="fas fa-clipboard-list me-2"></i>How to Trade This Signal</h5>
                    <div id="actionSteps"></div>
                </div>
            </div>
            
            <!-- Analysis Details -->
            <div class="col-md-3">
                <div class="mb-3">
                    <button class="refresh-btn w-100" onclick="refreshSignal()">
                        <i class="fas fa-sync-alt me-2"></i>Refresh Signal
                    </button>
                </div>
                
                <div id="analysisDetails">
                    <div class="text-center text-secondary py-5">
                        <i class="fas fa-chart-bar fa-3x mb-3"></i>
                        <p>Analysis details will appear here</p>
                    </div>
                </div>
            </div>
        </div>
    </div>
    
    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
    <script>
        let selectedAsset = 'EUR/USD';
        let selectedTimeframe = '5m';
        let refreshInterval = null;
        let countdownValue = 10;
        
        // Initialize
        document.addEventListener('DOMContentLoaded', function() {
            loadAssets();
            startAutoRefresh();
            
            // Timeframe buttons
            document.querySelectorAll('.timeframe-btn').forEach(btn => {
                btn.addEventListener('click', function() {
                    document.querySelectorAll('.timeframe-btn').forEach(b => b.classList.remove('active'));
                    this.classList.add('active');
                    selectedTimeframe = this.dataset.tf;
                    loadSignal(selectedAsset);
                });
            });
            
            // Search
            document.getElementById('searchAsset').addEventListener('input', function() {
                filterAssets(this.value);
            });
        });
        
        function loadAssets() {
            fetch('/api/assets')
                .then(r => r.json())
                .then(data => {
                    renderAssetList(data);
                    loadSignal(selectedAsset);
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
                                <div class="asset-price" id="price-${asset.replace('/', '-')}">Loading...</div>
                            </div>
                            <div id="badge-${asset.replace('/', '-')}">
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
                        const badgeEl = document.getElementById(`badge-${s.asset.replace('/', '-')}`);
                        const priceEl = document.getElementById(`price-${s.asset.replace('/', '-')}`);
                        
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
                        
                        if (priceEl) {
                            priceEl.textContent = s.price;
                        }
                    });
                });
        }
        
        function selectAsset(asset) {
            selectedAsset = asset;
            
            document.querySelectorAll('.asset-item').forEach(el => {
                el.classList.remove('active');
                if (el.dataset.asset === asset) {
                    el.classList.add('active');
                }
            });
            
            loadSignal(asset);
        }
        
        function loadSignal(asset) {
            const container = document.getElementById('mainSignal');
            container.innerHTML = '<div class="loading"><div class="spinner"></div></div>';
            
            fetch(`/api/signal/${encodeURIComponent(asset)}?timeframe=${selectedTimeframe}`)
                .then(r => r.json())
                .then(signal => {
                    renderMainSignal(signal);
                    renderAnalysisDetails(signal);
                    renderActionGuide(signal);
                });
        }
        
        function renderMainSignal(signal) {
            const container = document.getElementById('mainSignal');
            
            let actionClass = 'wait';
            let actionText = 'WAIT';
            let actionIcon = 'fa-clock';
            let directionText = '';
            
            if (signal.signal === 'BUY') {
                actionClass = 'buy';
                actionText = 'BUY';
                actionIcon = 'fa-arrow-up';
                directionText = 'CALL (UP)';
            } else if (signal.signal === 'SELL') {
                actionClass = 'sell';
                actionText = 'SELL';
                actionIcon = 'fa-arrow-down';
                directionText = 'PUT (DOWN)';
            } else if (signal.signal === 'DO NOT TRADE') {
                actionClass = 'notrade';
                actionText = 'DO NOT TRADE';
                actionIcon = 'fa-ban';
                directionText = 'AVOID';
            }
            
            container.innerHTML = `
                <div class="mb-2">
                    <span class="badge bg-secondary">${signal.asset}</span>
                    <span class="badge bg-secondary">${signal.timeframe}</span>
                    <span class="badge bg-secondary">${signal.session}</span>
                </div>
                
                <div class="signal-action ${actionClass}">
                    <i class="fas ${actionIcon} me-2"></i>${actionText}
                </div>
                
                ${directionText ? `<div class="h4 mb-4">${directionText}</div>` : ''}
                
                <div class="row g-3 mt-3">
                    <div class="col-4">
                        <div class="metric-card">
                            <div class="metric-value">${signal.price}</div>
                            <div class="metric-label">Price</div>
                        </div>
                    </div>
                    <div class="col-4">
                        <div class="metric-card">
                            <div class="metric-value">${Math.round(signal.score)}</div>
                            <div class="metric-label">Score</div>
                        </div>
                    </div>
                    <div class="col-4">
                        <div class="metric-card">
                            <div class="metric-value">${Math.round(signal.probability)}%</div>
                            <div class="metric-label">Probability</div>
                        </div>
                    </div>
                </div>
                
                <div class="row g-3 mt-2">
                    <div class="col-6">
                        <div class="metric-card">
                            <div class="metric-value">${signal.confidence}</div>
                            <div class="metric-label">Confidence</div>
                        </div>
                    </div>
                    <div class="col-6">
                        <div class="metric-card">
                            <div class="metric-value">${signal.risk_level}</div>
                            <div class="metric-label">Risk Level</div>
                        </div>
                    </div>
                </div>
                
                <div class="mt-3 text-secondary">
                    <small>Last updated: ${new Date(signal.timestamp).toLocaleTimeString()}</small>
                </div>
            `;
        }
        
        function renderAnalysisDetails(signal) {
            const container = document.getElementById('analysisDetails');
            
            let reasonsHtml = '';
            if (signal.reasons && signal.reasons.length > 0) {
                signal.reasons.forEach(reason => {
                    let reasonClass = 'reason-neutral';
                    if (reason.includes('✅') || reason.includes('📈')) {
                        reasonClass = 'reason-positive';
                    } else if (reason.includes('❌') || reason.includes('📉')) {
                        reasonClass = 'reason-negative';
                    } else if (reason.includes('⚠️')) {
                        reasonClass = 'reason-warning';
                    }
                    reasonsHtml += `<div class="reason-item ${reasonClass}">${reason}</div>`;
                });
            }
            
            let warningsHtml = '';
            if (signal.warnings && signal.warnings.length > 0) {
                signal.warnings.forEach(warning => {
                    warningsHtml += `<div class="reason-item reason-warning">${warning}</div>`;
                });
            }
            
            container.innerHTML = `
                <h6 class="mb-3"><i class="fas fa-list-check me-2"></i>Analysis Reasons</h6>
                ${reasonsHtml || '<div class="text-secondary">No specific reasons</div>'}
                
                ${warningsHtml ? `
                    <h6 class="mt-4 mb-3"><i class="fas fa-exclamation-triangle me-2"></i>Warnings</h6>
                    ${warningsHtml}
                ` : ''}
            `;
        }
        
        function renderActionGuide(signal) {
            const container = document.getElementById('actionGuide');
            const stepsContainer = document.getElementById('actionSteps');
            
            if (signal.signal === 'BUY' || signal.signal === 'SELL') {
                container.style.display = 'block';
                
                const direction = signal.signal === 'BUY' ? 'CALL (UP)' : 'PUT (DOWN)';
                const color = signal.signal === 'BUY' ? '#00d26a' : '#ff4757';
                
                stepsContainer.innerHTML = `
                    <div class="action-step">
                        <div class="step-number" style="background: ${color}">1</div>
                        <div>Open Pocket Option</div>
                    </div>
                    <div class="action-step">
                        <div class="step-number" style="background: ${color}">2</div>
                        <div>Select <strong>${signal.asset}</strong></div>
                    </div>
                    <div class="action-step">
                        <div class="step-number" style="background: ${color}">3</div>
                        <div>Choose <strong style="color: ${color}">${direction}</strong></div>
                    </div>
                    <div class="action-step">
                        <div class="step-number" style="background: ${color}">4</div>
                        <div>Set your trade amount (max 2% of balance)</div>
                    </div>
                    <div class="action-step">
                        <div class="step-number" style="background: ${color}">5</div>
                        <div>Execute the trade</div>
                    </div>
                `;
            } else {
                container.style.display = 'block';
                stepsContainer.innerHTML = `
                    <div class="alert alert-warning mb-0">
                        <i class="fas fa-hand-paper me-2"></i>
                        <strong>Do not trade right now.</strong><br>
                        Wait for a clearer signal or check other assets.
                    </div>
                `;
            }
        }
        
        function filterAssets(query) {
            query = query.toLowerCase();
            document.querySelectorAll('.asset-item').forEach(el => {
                const asset = el.dataset.asset.toLowerCase();
                el.style.display = asset.includes(query) ? 'flex' : 'none';
            });
        }
        
        function refreshSignal() {
            loadSignal(selectedAsset);
            loadQuickSignals();
            countdownValue = 10;
        }
        
        function startAutoRefresh() {
            // Update countdown every second
            setInterval(() => {
                countdownValue--;
                document.getElementById('countdown').textContent = `Updating in ${countdownValue}s`;
                
                if (countdownValue <= 0) {
                    refreshSignal();
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
