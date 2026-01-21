"""
MarketSense AI - Configuration Module
Contains all configuration settings and constants for the trading bot.
"""

import os
from datetime import datetime

# ============================================
# DATABASE CONFIGURATION
# ============================================
DATABASE_PATH = os.path.join(os.path.dirname(__file__), 'data', 'marketsense.db')
CSV_DATA_PATH = os.path.join(os.path.dirname(__file__), 'data', 'candles')

# ============================================
# TRADING SESSIONS
# ============================================
TRADING_SESSIONS = {
    'ASIAN': {'start': '00:00', 'end': '08:00'},
    'LONDON': {'start': '08:00', 'end': '16:00'},
    'NEW_YORK': {'start': '13:00', 'end': '22:00'},
    'OVERLAP': {'start': '13:00', 'end': '16:00'}  # London/NY overlap
}

# ============================================
# SUPPORTED ASSETS
# ============================================
DEFAULT_ASSETS = [
    'EUR/USD', 'GBP/USD', 'USD/JPY', 'AUD/USD', 'USD/CAD',
    'EUR/GBP', 'EUR/JPY', 'GBP/JPY', 'GOLD', 'SILVER'
]

# ============================================
# TIMEFRAMES
# ============================================
SUPPORTED_TIMEFRAMES = ['1m', '5m', '15m']
DEFAULT_TIMEFRAME = '5m'

# ============================================
# TECHNICAL INDICATORS CONFIGURATION
# ============================================
INDICATOR_CONFIG = {
    'RSI': {'period': 14, 'overbought': 70, 'oversold': 30},
    'EMA_FAST': {'period': 9},
    'EMA_SLOW': {'period': 21},
    'MACD': {'fast': 12, 'slow': 26, 'signal': 9},
    'BOLLINGER': {'period': 20, 'std_dev': 2}
}

# ============================================
# STRATEGY SCORING WEIGHTS
# ============================================
SCORING_WEIGHTS = {
    'trend_alignment': 0.25,
    'momentum': 0.20,
    'volatility': 0.15,
    'candle_pattern': 0.15,
    'session_quality': 0.10,
    'psychology_risk': -0.15  # Negative weight (penalty)
}

# Score thresholds
SCORE_THRESHOLDS = {
    'NO_TRADE': (0, 40),
    'RISKY': (41, 60),
    'ACCEPTABLE': (61, 75),
    'HIGH_QUALITY': (76, 100)
}

# ============================================
# SIMULATION SETTINGS
# ============================================
SIMULATION_CONFIG = {
    'initial_balance': 10000.0,
    'risk_per_trade': 0.02,  # 2% risk per trade
    'min_trades_for_baseline': 50,
    'max_daily_trades': 10,
    'max_consecutive_losses': 3
}

# ============================================
# AI MODEL CONFIGURATION
# ============================================
AI_CONFIG = {
    'model_type': 'random_forest',  # 'logistic_regression' or 'random_forest'
    'min_training_samples': 100,
    'retrain_interval': 50,  # Retrain after every 50 new trades
    'confidence_threshold': 0.55
}

# ============================================
# PSYCHOLOGY DETECTION THRESHOLDS
# ============================================
PSYCHOLOGY_CONFIG = {
    'overtrading_threshold': 5,  # trades per hour
    'revenge_trade_window': 300,  # seconds after loss
    'emotional_cluster_size': 3,  # consecutive quick trades
    'performance_drop_threshold': 0.6  # 60% loss rate triggers warning
}

# ============================================
# MARKETING TRAP DETECTION
# ============================================
TRAP_DETECTION_CONFIG = {
    'perfect_setup_threshold': 0.9,  # Too many aligned indicators
    'volatility_spike_threshold': 2.0,  # 2x normal volatility
    'late_entry_threshold': 0.7  # 70% of move already done
}

# ============================================
# REPORTING CONFIGURATION
# ============================================
REPORT_CONFIG = {
    'reports_path': os.path.join(os.path.dirname(__file__), 'reports'),
    'daily_report_time': '23:00',
    'weekly_report_day': 'Sunday'
}

# ============================================
# EXECUTION RULES
# ============================================
EXECUTION_RULES = {
    'require_journal_entry': True,
    'pause_on_rule_violation': True,
    'cooldown_after_violation': 3600,  # 1 hour in seconds
    'max_drawdown_percent': 10.0
}

# ============================================
# LOGGING
# ============================================
LOG_CONFIG = {
    'log_path': os.path.join(os.path.dirname(__file__), 'logs'),
    'log_level': 'INFO',
    'max_log_files': 30
}

def ensure_directories():
    """Create necessary directories if they don't exist."""
    directories = [
        os.path.dirname(DATABASE_PATH),
        CSV_DATA_PATH,
        REPORT_CONFIG['reports_path'],
        LOG_CONFIG['log_path']
    ]
    for directory in directories:
        os.makedirs(directory, exist_ok=True)

# Create directories on import
ensure_directories()
