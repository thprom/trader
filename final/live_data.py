"""
MarketSense AI - Live Data Module
Fetches real-time market data from Yahoo Finance API for forex, crypto, and stocks.
"""

import sys
sys.path.append('/opt/.manus/.sandbox-runtime')

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple
import time
import json

try:
    from data_api import ApiClient
    API_AVAILABLE = True
except ImportError:
    API_AVAILABLE = False
    print("Warning: data_api not available. Using offline mode.")

import config
from database import get_database


class LiveDataFetcher:
    """Fetches real-time market data from Yahoo Finance."""
    
    # Symbol mapping for Pocket Option assets
    SYMBOL_MAP = {
        # Forex pairs
        'EUR/USD': 'EURUSD=X',
        'GBP/USD': 'GBPUSD=X',
        'USD/JPY': 'USDJPY=X',
        'AUD/USD': 'AUDUSD=X',
        'USD/CAD': 'USDCAD=X',
        'EUR/GBP': 'EURGBP=X',
        'EUR/JPY': 'EURJPY=X',
        'GBP/JPY': 'GBPJPY=X',
        'USD/CHF': 'USDCHF=X',
        'NZD/USD': 'NZDUSD=X',
        
        # Crypto
        'BTC/USD': 'BTC-USD',
        'ETH/USD': 'ETH-USD',
        'XRP/USD': 'XRP-USD',
        'LTC/USD': 'LTC-USD',
        'DOGE/USD': 'DOGE-USD',
        
        # Commodities
        'GOLD': 'GC=F',
        'SILVER': 'SI=F',
        'OIL': 'CL=F',
        
        # Indices
        'US500': '^GSPC',
        'US100': '^NDX',
        'US30': '^DJI',
    }
    
    # Timeframe mapping
    TIMEFRAME_MAP = {
        '1m': '1m',
        '5m': '5m',
        '15m': '15m',
        '30m': '30m',
        '1h': '60m',
        '4h': '1d',  # Yahoo doesn't support 4h, use daily
        '1d': '1d',
    }
    
    # Range mapping for different timeframes
    RANGE_MAP = {
        '1m': '1d',
        '5m': '5d',
        '15m': '5d',
        '30m': '1mo',
        '1h': '1mo',
        '1d': '3mo',
    }
    
    def __init__(self):
        self.client = ApiClient() if API_AVAILABLE else None
        self.db = get_database()
        self.cache = {}
        self.cache_expiry = {}
        self.cache_duration = 60  # Cache for 60 seconds
    
    def get_symbol(self, asset: str) -> str:
        """Convert asset name to Yahoo Finance symbol."""
        return self.SYMBOL_MAP.get(asset, asset)
    
    def get_available_assets(self) -> List[str]:
        """Get list of available assets."""
        return list(self.SYMBOL_MAP.keys())
    
    def fetch_live_data(self, asset: str, timeframe: str = '5m', 
                        use_cache: bool = True) -> pd.DataFrame:
        """
        Fetch live candle data for an asset.
        
        Args:
            asset: Asset name (e.g., 'EUR/USD')
            timeframe: Candle timeframe (1m, 5m, 15m, etc.)
            use_cache: Whether to use cached data
            
        Returns:
            DataFrame with OHLCV data
        """
        cache_key = f"{asset}_{timeframe}"
        
        # Check cache
        if use_cache and cache_key in self.cache:
            if datetime.now().timestamp() < self.cache_expiry.get(cache_key, 0):
                return self.cache[cache_key].copy()
        
        if not API_AVAILABLE or self.client is None:
            print(f"API not available. Returning empty data for {asset}")
            return pd.DataFrame()
        
        symbol = self.get_symbol(asset)
        interval = self.TIMEFRAME_MAP.get(timeframe, '5m')
        range_val = self.RANGE_MAP.get(timeframe, '5d')
        
        try:
            response = self.client.call_api('YahooFinance/get_stock_chart', query={
                'symbol': symbol,
                'interval': interval,
                'range': range_val,
                'includeAdjustedClose': True
            })
            
            if response and 'chart' in response and 'result' in response['chart']:
                result = response['chart']['result'][0]
                timestamps = result['timestamp']
                quotes = result['indicators']['quote'][0]
                
                df = pd.DataFrame({
                    'timestamp': pd.to_datetime(timestamps, unit='s'),
                    'open': quotes['open'],
                    'high': quotes['high'],
                    'low': quotes['low'],
                    'close': quotes['close'],
                    'volume': quotes.get('volume', [0] * len(timestamps))
                })
                
                # Remove rows with NaN values
                df = df.dropna()
                
                # Add session information
                df['session'] = df['timestamp'].dt.hour.apply(self._get_session)
                
                # Cache the data
                self.cache[cache_key] = df
                self.cache_expiry[cache_key] = datetime.now().timestamp() + self.cache_duration
                
                # Also store in database for historical analysis
                self._store_to_database(df, asset, timeframe)
                
                return df
            else:
                print(f"No data returned for {asset}")
                return pd.DataFrame()
                
        except Exception as e:
            print(f"Error fetching data for {asset}: {e}")
            return pd.DataFrame()
    
    def fetch_current_price(self, asset: str) -> Dict[str, Any]:
        """Fetch current price and basic info for an asset."""
        if not API_AVAILABLE or self.client is None:
            return {'error': True, 'message': 'API not available'}
        
        symbol = self.get_symbol(asset)
        
        try:
            response = self.client.call_api('YahooFinance/get_stock_chart', query={
                'symbol': symbol,
                'interval': '1m',
                'range': '1d',
                'includeAdjustedClose': True
            })
            
            if response and 'chart' in response and 'result' in response['chart']:
                result = response['chart']['result'][0]
                meta = result['meta']
                
                return {
                    'error': False,
                    'asset': asset,
                    'symbol': symbol,
                    'price': meta.get('regularMarketPrice', 0),
                    'previous_close': meta.get('previousClose', 0),
                    'day_high': meta.get('regularMarketDayHigh', 0),
                    'day_low': meta.get('regularMarketDayLow', 0),
                    'change': meta.get('regularMarketPrice', 0) - meta.get('previousClose', 0),
                    'change_percent': ((meta.get('regularMarketPrice', 0) - meta.get('previousClose', 0)) / 
                                      meta.get('previousClose', 1)) * 100,
                    'timestamp': datetime.now().isoformat()
                }
            else:
                return {'error': True, 'message': f'No data for {asset}'}
                
        except Exception as e:
            return {'error': True, 'message': str(e)}
    
    def fetch_multiple_assets(self, assets: List[str], timeframe: str = '5m') -> Dict[str, pd.DataFrame]:
        """Fetch data for multiple assets."""
        results = {}
        for asset in assets:
            results[asset] = self.fetch_live_data(asset, timeframe)
            time.sleep(0.2)  # Small delay to avoid rate limiting
        return results
    
    def _get_session(self, hour: int) -> str:
        """Determine trading session based on hour (UTC)."""
        if 0 <= hour < 8:
            return 'ASIAN'
        elif 8 <= hour < 13:
            return 'LONDON'
        elif 13 <= hour < 16:
            return 'OVERLAP'
        elif 16 <= hour < 22:
            return 'NEW_YORK'
        else:
            return 'OFF_HOURS'
    
    def _store_to_database(self, df: pd.DataFrame, asset: str, timeframe: str):
        """Store fetched data to database for historical analysis."""
        try:
            for _, row in df.iterrows():
                self.db.insert_candle(
                    asset=asset,
                    timeframe=timeframe,
                    timestamp=row['timestamp'],
                    open_price=float(row['open']),
                    high=float(row['high']),
                    low=float(row['low']),
                    close=float(row['close']),
                    volume=float(row.get('volume', 0)),
                    session=row.get('session')
                )
        except Exception as e:
            pass  # Silently fail on duplicate entries
    
    def get_market_status(self) -> Dict[str, Any]:
        """Get current market status (open/closed for different sessions)."""
        now = datetime.utcnow()
        hour = now.hour
        weekday = now.weekday()
        
        # Forex market is closed on weekends
        is_weekend = weekday >= 5
        
        sessions = {
            'ASIAN': {'active': 0 <= hour < 8 and not is_weekend, 'hours': '00:00-08:00 UTC'},
            'LONDON': {'active': 8 <= hour < 16 and not is_weekend, 'hours': '08:00-16:00 UTC'},
            'NEW_YORK': {'active': 13 <= hour < 22 and not is_weekend, 'hours': '13:00-22:00 UTC'},
            'OVERLAP': {'active': 13 <= hour < 16 and not is_weekend, 'hours': '13:00-16:00 UTC'},
        }
        
        current_session = self._get_session(hour) if not is_weekend else 'CLOSED'
        
        return {
            'timestamp': now.isoformat(),
            'is_weekend': is_weekend,
            'current_session': current_session,
            'sessions': sessions,
            'forex_open': not is_weekend,
            'crypto_open': True,  # Crypto is 24/7
        }


class LiveSignalGenerator:
    """Generates live trading signals from real-time data."""
    
    def __init__(self):
        self.data_fetcher = LiveDataFetcher()
        self.db = get_database()
        
        # Import analysis modules
        from technical_analysis import get_ta_engine
        from ai_engine import get_ai_engine
        from psychology import get_trap_detector
        from strategy import get_strategy_scorer
        
        self.ta_engine = get_ta_engine()
        self.ai_engine = get_ai_engine()
        self.trap_detector = get_trap_detector()
        self.strategy_scorer = get_strategy_scorer()
    
    def generate_signal(self, asset: str, timeframe: str = '5m') -> Dict[str, Any]:
        """
        Generate a trading signal for an asset.
        
        Returns a clear BUY/SELL/WAIT recommendation with reasoning.
        """
        # Fetch live data
        df = self.data_fetcher.fetch_live_data(asset, timeframe)
        
        if df.empty or len(df) < 30:
            return {
                'signal': 'NO_DATA',
                'asset': asset,
                'timeframe': timeframe,
                'message': f'Insufficient data for {asset}. Need at least 30 candles.',
                'timestamp': datetime.now().isoformat()
            }
        
        # Calculate technical indicators
        df = self.ta_engine.calculate_all_indicators(df)
        
        # Get current signals
        signals = self.ta_engine.get_current_signals(df)
        
        # Get volatility and trend
        volatility = self.ta_engine.calculate_volatility(df)
        trend = self.ta_engine.get_trend_strength(df)
        
        # Get current session
        market_status = self.data_fetcher.get_market_status()
        session = market_status['current_session']
        
        # Calculate strategy score
        score_result = self.strategy_scorer.calculate_score(signals, volatility, trend, session)
        
        # Check for traps
        trap_analysis = self.trap_detector.analyze_setup(signals, df)
        
        # Determine direction based on overall bias
        bias = signals.get('overall_bias', {})
        bias_direction = bias.get('direction', 'NEUTRAL')
        bias_confidence = bias.get('confidence', 0.5)
        
        # Get AI prediction
        direction = 'CALL' if bias_direction == 'BULLISH' else 'PUT' if bias_direction == 'BEARISH' else None
        ai_prediction = self.ai_engine.predict_trade(signals, direction)
        
        # Generate final signal
        signal = self._determine_signal(
            score_result['final_score'],
            ai_prediction,
            trap_analysis,
            bias_direction,
            bias_confidence,
            volatility
        )
        
        # Build reasons list
        reasons = self._build_reasons(signals, trend, volatility, trap_analysis, session)
        
        # Get current price
        current_price = df['close'].iloc[-1]
        
        return {
            'signal': signal['action'],
            'direction': signal['direction'],
            'asset': asset,
            'timeframe': timeframe,
            'price': round(current_price, 5),
            'probability': ai_prediction.get('probability', 50),
            'confidence': signal['confidence'],
            'score': score_result['final_score'],
            'risk_level': ai_prediction.get('risk_level', 'MEDIUM'),
            'reasons': reasons,
            'warnings': signal.get('warnings', []),
            'session': session,
            'market_status': market_status,
            'timestamp': datetime.now().isoformat(),
            'details': {
                'signals': signals,
                'trend': trend,
                'volatility': volatility,
                'trap_analysis': trap_analysis,
                'score_breakdown': score_result['breakdown']
            }
        }
    
    def _determine_signal(self, score: float, ai_prediction: Dict, 
                          trap_analysis: Dict, bias_direction: str,
                          bias_confidence: float, volatility: Dict) -> Dict[str, Any]:
        """Determine the final trading signal."""
        warnings = []
        
        ai_rec = ai_prediction.get('recommendation', 'WAIT')
        ai_prob = ai_prediction.get('probability', 50)
        trap_risk = trap_analysis.get('overall_risk_score', 0)
        
        # Check for trap warnings
        if trap_risk >= 50:
            warnings.append("⚠️ HIGH TRAP RISK: Multiple manipulation patterns detected")
        elif trap_risk >= 25:
            warnings.append("⚠️ Moderate trap risk detected")
        
        # Check volatility
        if volatility.get('is_high_volatility', False):
            warnings.append("⚠️ High volatility - increased risk")
        
        # Determine signal
        if ai_rec == 'AVOID' or trap_risk >= 50:
            return {
                'action': 'DO NOT TRADE',
                'direction': None,
                'confidence': 'HIGH',
                'warnings': warnings + ["❌ Setup flagged as dangerous"]
            }
        
        if score >= 70 and ai_prob >= 60 and trap_risk < 25:
            # Strong signal
            if bias_direction == 'BULLISH':
                return {
                    'action': 'BUY',
                    'direction': 'CALL',
                    'confidence': 'HIGH' if score >= 80 else 'MEDIUM',
                    'warnings': warnings
                }
            elif bias_direction == 'BEARISH':
                return {
                    'action': 'SELL',
                    'direction': 'PUT',
                    'confidence': 'HIGH' if score >= 80 else 'MEDIUM',
                    'warnings': warnings
                }
        
        if score >= 55 and ai_prob >= 55 and trap_risk < 40:
            # Moderate signal
            if bias_direction == 'BULLISH':
                return {
                    'action': 'BUY',
                    'direction': 'CALL',
                    'confidence': 'LOW',
                    'warnings': warnings + ["⚡ Marginal setup - proceed with caution"]
                }
            elif bias_direction == 'BEARISH':
                return {
                    'action': 'SELL',
                    'direction': 'PUT',
                    'confidence': 'LOW',
                    'warnings': warnings + ["⚡ Marginal setup - proceed with caution"]
                }
        
        # Default: WAIT
        return {
            'action': 'WAIT',
            'direction': None,
            'confidence': 'MEDIUM',
            'warnings': warnings + ["⏳ No clear setup - wait for better opportunity"]
        }
    
    def _build_reasons(self, signals: Dict, trend: Dict, volatility: Dict,
                       trap_analysis: Dict, session: str) -> List[str]:
        """Build list of reasons for the signal."""
        reasons = []
        
        # RSI
        rsi = signals.get('rsi', {})
        rsi_value = rsi.get('value', 50)
        rsi_signal = rsi.get('signal', 'NEUTRAL')
        
        if rsi_signal == 'OVERSOLD':
            reasons.append(f"✅ RSI oversold ({rsi_value:.1f}) - potential bounce")
        elif rsi_signal == 'OVERBOUGHT':
            reasons.append(f"✅ RSI overbought ({rsi_value:.1f}) - potential reversal")
        elif rsi_signal == 'BULLISH':
            reasons.append(f"📈 RSI bullish ({rsi_value:.1f})")
        elif rsi_signal == 'BEARISH':
            reasons.append(f"📉 RSI bearish ({rsi_value:.1f})")
        
        # EMA
        ema = signals.get('ema', {})
        ema_signal = ema.get('signal', 'NEUTRAL')
        ema_cross = ema.get('crossover', 'NONE')
        
        if ema_cross == 'BULLISH_CROSS':
            reasons.append("✅ EMA bullish crossover detected")
        elif ema_cross == 'BEARISH_CROSS':
            reasons.append("✅ EMA bearish crossover detected")
        elif ema_signal == 'BULLISH':
            reasons.append("📈 Price above EMA (bullish)")
        elif ema_signal == 'BEARISH':
            reasons.append("📉 Price below EMA (bearish)")
        
        # MACD
        macd = signals.get('macd', {})
        macd_trend = macd.get('trend', 'NEUTRAL')
        
        if macd_trend == 'BULLISH':
            reasons.append("📈 MACD bullish momentum")
        elif macd_trend == 'BEARISH':
            reasons.append("📉 MACD bearish momentum")
        
        # Trend
        if trend.get('is_strong_trend', False):
            trend_dir = trend.get('trend', 'SIDEWAYS')
            reasons.append(f"✅ Strong {trend_dir.lower()} trend detected")
        
        # Session
        if session in ['LONDON', 'NEW_YORK', 'OVERLAP']:
            reasons.append(f"✅ Active {session} session (good liquidity)")
        elif session == 'ASIAN':
            reasons.append("⚠️ Asian session (lower volatility)")
        elif session == 'CLOSED':
            reasons.append("❌ Market closed (weekend)")
        
        # Traps
        for trap in trap_analysis.get('traps_detected', []):
            reasons.append(f"⚠️ {trap.get('type', 'Unknown trap')}: {trap.get('message', '')[:50]}...")
        
        return reasons
    
    def scan_all_assets(self, timeframe: str = '5m') -> List[Dict[str, Any]]:
        """Scan all available assets and return signals sorted by quality."""
        assets = self.data_fetcher.get_available_assets()
        signals = []
        
        for asset in assets:
            try:
                signal = self.generate_signal(asset, timeframe)
                if signal['signal'] != 'NO_DATA':
                    signals.append(signal)
                time.sleep(0.3)  # Rate limiting
            except Exception as e:
                print(f"Error scanning {asset}: {e}")
        
        # Sort by score (highest first)
        signals.sort(key=lambda x: x.get('score', 0), reverse=True)
        
        return signals
    
    def get_best_opportunities(self, timeframe: str = '5m', 
                               min_score: float = 60) -> List[Dict[str, Any]]:
        """Get the best trading opportunities right now."""
        all_signals = self.scan_all_assets(timeframe)
        
        # Filter for actionable signals
        opportunities = [
            s for s in all_signals 
            if s['signal'] in ['BUY', 'SELL'] and s['score'] >= min_score
        ]
        
        return opportunities


# Singleton instances
_data_fetcher = None
_signal_generator = None

def get_live_data_fetcher() -> LiveDataFetcher:
    """Get or create live data fetcher singleton."""
    global _data_fetcher
    if _data_fetcher is None:
        _data_fetcher = LiveDataFetcher()
    return _data_fetcher

def get_signal_generator() -> LiveSignalGenerator:
    """Get or create signal generator singleton."""
    global _signal_generator
    if _signal_generator is None:
        _signal_generator = LiveSignalGenerator()
    return _signal_generator
