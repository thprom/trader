"""
MarketSense AI - Technical Analysis Engine
Computes technical indicators and generates trading signals.
"""

import pandas as pd
import numpy as np
from typing import Dict, Any, Tuple, Optional
from datetime import datetime
import ta
from ta.trend import EMAIndicator, MACD
from ta.momentum import RSIIndicator
from ta.volatility import BollingerBands
import config


class TechnicalAnalysisEngine:
    """Technical analysis engine for computing indicators and signals."""
    
    def __init__(self):
        self.config = config.INDICATOR_CONFIG
    
    def calculate_all_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calculate all technical indicators for the given candle data."""
        if df.empty or len(df) < 30:
            return df
        
        df = df.copy()
        
        # RSI
        df = self._calculate_rsi(df)
        
        # EMAs
        df = self._calculate_emas(df)
        
        # MACD
        df = self._calculate_macd(df)
        
        # Bollinger Bands
        df = self._calculate_bollinger(df)
        
        # Candle patterns
        df = self._detect_candle_patterns(df)
        
        return df
    
    def _calculate_rsi(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calculate RSI indicator."""
        period = self.config['RSI']['period']
        rsi = RSIIndicator(close=df['close'], window=period)
        df['rsi'] = rsi.rsi()
        
        # RSI signal
        df['rsi_signal'] = df['rsi'].apply(self._get_rsi_signal)
        
        return df
    
    def _get_rsi_signal(self, rsi_value: float) -> str:
        """Determine RSI signal."""
        if pd.isna(rsi_value):
            return 'NEUTRAL'
        
        overbought = self.config['RSI']['overbought']
        oversold = self.config['RSI']['oversold']
        
        if rsi_value >= overbought:
            return 'OVERBOUGHT'
        elif rsi_value <= oversold:
            return 'OVERSOLD'
        elif rsi_value > 50:
            return 'BULLISH'
        elif rsi_value < 50:
            return 'BEARISH'
        return 'NEUTRAL'
    
    def _calculate_emas(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calculate fast and slow EMAs."""
        fast_period = self.config['EMA_FAST']['period']
        slow_period = self.config['EMA_SLOW']['period']
        
        ema_fast = EMAIndicator(close=df['close'], window=fast_period)
        ema_slow = EMAIndicator(close=df['close'], window=slow_period)
        
        df['ema_fast'] = ema_fast.ema_indicator()
        df['ema_slow'] = ema_slow.ema_indicator()
        
        # EMA crossover signal
        df['ema_signal'] = np.where(
            df['ema_fast'] > df['ema_slow'], 'BULLISH',
            np.where(df['ema_fast'] < df['ema_slow'], 'BEARISH', 'NEUTRAL')
        )
        
        # Detect crossovers
        df['ema_crossover'] = 'NONE'
        for i in range(1, len(df)):
            if df['ema_fast'].iloc[i-1] <= df['ema_slow'].iloc[i-1] and \
               df['ema_fast'].iloc[i] > df['ema_slow'].iloc[i]:
                df.loc[df.index[i], 'ema_crossover'] = 'BULLISH_CROSS'
            elif df['ema_fast'].iloc[i-1] >= df['ema_slow'].iloc[i-1] and \
                 df['ema_fast'].iloc[i] < df['ema_slow'].iloc[i]:
                df.loc[df.index[i], 'ema_crossover'] = 'BEARISH_CROSS'
        
        return df
    
    def _calculate_macd(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calculate MACD indicator."""
        fast = self.config['MACD']['fast']
        slow = self.config['MACD']['slow']
        signal = self.config['MACD']['signal']
        
        macd = MACD(close=df['close'], window_fast=fast, window_slow=slow, window_sign=signal)
        
        df['macd'] = macd.macd()
        df['macd_signal'] = macd.macd_signal()
        df['macd_histogram'] = macd.macd_diff()
        
        # MACD trend signal
        df['macd_trend'] = np.where(
            df['macd'] > df['macd_signal'], 'BULLISH',
            np.where(df['macd'] < df['macd_signal'], 'BEARISH', 'NEUTRAL')
        )
        
        return df
    
    def _calculate_bollinger(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calculate Bollinger Bands."""
        period = self.config['BOLLINGER']['period']
        std_dev = self.config['BOLLINGER']['std_dev']
        
        bb = BollingerBands(close=df['close'], window=period, window_dev=std_dev)
        
        df['bb_upper'] = bb.bollinger_hband()
        df['bb_middle'] = bb.bollinger_mavg()
        df['bb_lower'] = bb.bollinger_lband()
        df['bb_width'] = bb.bollinger_wband()
        df['bb_percent'] = bb.bollinger_pband()
        
        # Bollinger signal
        df['bb_signal'] = df.apply(self._get_bb_signal, axis=1)
        
        return df
    
    def _get_bb_signal(self, row) -> str:
        """Determine Bollinger Band signal."""
        if pd.isna(row.get('bb_upper')) or pd.isna(row.get('close')):
            return 'NEUTRAL'
        
        close = row['close']
        upper = row['bb_upper']
        lower = row['bb_lower']
        middle = row['bb_middle']
        
        if close >= upper:
            return 'OVERBOUGHT'
        elif close <= lower:
            return 'OVERSOLD'
        elif close > middle:
            return 'BULLISH'
        elif close < middle:
            return 'BEARISH'
        return 'NEUTRAL'
    
    def _detect_candle_patterns(self, df: pd.DataFrame) -> pd.DataFrame:
        """Detect basic candle patterns."""
        df['candle_body'] = abs(df['close'] - df['open'])
        df['candle_range'] = df['high'] - df['low']
        df['upper_wick'] = df['high'] - df[['open', 'close']].max(axis=1)
        df['lower_wick'] = df[['open', 'close']].min(axis=1) - df['low']
        
        # Bullish/Bearish candle
        df['candle_type'] = np.where(df['close'] > df['open'], 'BULLISH', 
                                     np.where(df['close'] < df['open'], 'BEARISH', 'DOJI'))
        
        # Pattern detection
        df['candle_pattern'] = df.apply(self._identify_pattern, axis=1)
        
        return df
    
    def _identify_pattern(self, row) -> str:
        """Identify candle pattern for a single row."""
        if pd.isna(row.get('candle_body')) or row.get('candle_range', 0) == 0:
            return 'NONE'
        
        body = row['candle_body']
        range_val = row['candle_range']
        upper_wick = row['upper_wick']
        lower_wick = row['lower_wick']
        
        body_ratio = body / range_val if range_val > 0 else 0
        
        # Doji
        if body_ratio < 0.1:
            return 'DOJI'
        
        # Hammer / Inverted Hammer
        if lower_wick > body * 2 and upper_wick < body * 0.5:
            return 'HAMMER'
        if upper_wick > body * 2 and lower_wick < body * 0.5:
            return 'INVERTED_HAMMER'
        
        # Marubozu (strong momentum)
        if body_ratio > 0.8:
            return 'MARUBOZU_' + row['candle_type']
        
        # Spinning top
        if body_ratio < 0.3 and upper_wick > body and lower_wick > body:
            return 'SPINNING_TOP'
        
        return 'STANDARD'
    
    def get_current_signals(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Get current trading signals from the latest data."""
        if df.empty:
            return {}
        
        latest = df.iloc[-1]
        
        signals = {
            'timestamp': latest.get('timestamp', datetime.now()),
            'price': latest.get('close', 0),
            'rsi': {
                'value': round(latest.get('rsi', 50), 2),
                'signal': latest.get('rsi_signal', 'NEUTRAL'),
                'strength': self._calculate_signal_strength(latest.get('rsi', 50), 'rsi')
            },
            'ema': {
                'fast': round(latest.get('ema_fast', 0), 5),
                'slow': round(latest.get('ema_slow', 0), 5),
                'signal': latest.get('ema_signal', 'NEUTRAL'),
                'crossover': latest.get('ema_crossover', 'NONE'),
                'strength': self._calculate_ema_strength(latest)
            },
            'macd': {
                'value': round(latest.get('macd', 0), 5),
                'signal_line': round(latest.get('macd_signal', 0), 5),
                'histogram': round(latest.get('macd_histogram', 0), 5),
                'trend': latest.get('macd_trend', 'NEUTRAL'),
                'strength': self._calculate_macd_strength(latest)
            },
            'bollinger': {
                'upper': round(latest.get('bb_upper', 0), 5),
                'middle': round(latest.get('bb_middle', 0), 5),
                'lower': round(latest.get('bb_lower', 0), 5),
                'width': round(latest.get('bb_width', 0), 4),
                'percent': round(latest.get('bb_percent', 0.5), 4),
                'signal': latest.get('bb_signal', 'NEUTRAL')
            },
            'candle': {
                'type': latest.get('candle_type', 'NEUTRAL'),
                'pattern': latest.get('candle_pattern', 'NONE')
            },
            'overall_bias': self._calculate_overall_bias(latest)
        }
        
        return signals
    
    def _calculate_signal_strength(self, value: float, indicator: str) -> float:
        """Calculate signal strength (0-1) for an indicator."""
        if indicator == 'rsi':
            if pd.isna(value):
                return 0.5
            # Strength increases as RSI moves away from 50
            return abs(value - 50) / 50
        return 0.5
    
    def _calculate_ema_strength(self, row) -> float:
        """Calculate EMA signal strength."""
        ema_fast = row.get('ema_fast', 0)
        ema_slow = row.get('ema_slow', 0)
        
        if pd.isna(ema_fast) or pd.isna(ema_slow) or ema_slow == 0:
            return 0.5
        
        # Strength based on percentage difference
        diff_pct = abs(ema_fast - ema_slow) / ema_slow
        return min(diff_pct * 10, 1.0)  # Scale and cap at 1
    
    def _calculate_macd_strength(self, row) -> float:
        """Calculate MACD signal strength."""
        histogram = row.get('macd_histogram', 0)
        if pd.isna(histogram):
            return 0.5
        
        # Normalize histogram value
        return min(abs(histogram) * 100, 1.0)
    
    def _calculate_overall_bias(self, row) -> Dict[str, Any]:
        """Calculate overall market bias from all indicators."""
        bullish_count = 0
        bearish_count = 0
        total_signals = 0
        
        # Count signals
        signals_to_check = ['rsi_signal', 'ema_signal', 'macd_trend', 'bb_signal', 'candle_type']
        
        for signal_name in signals_to_check:
            signal = row.get(signal_name, 'NEUTRAL')
            if signal in ['BULLISH', 'OVERSOLD', 'BULLISH_CROSS']:
                bullish_count += 1
            elif signal in ['BEARISH', 'OVERBOUGHT', 'BEARISH_CROSS']:
                bearish_count += 1
            total_signals += 1
        
        if bullish_count > bearish_count:
            bias = 'BULLISH'
            confidence = bullish_count / total_signals
        elif bearish_count > bullish_count:
            bias = 'BEARISH'
            confidence = bearish_count / total_signals
        else:
            bias = 'NEUTRAL'
            confidence = 0.5
        
        return {
            'direction': bias,
            'confidence': round(confidence, 2),
            'bullish_signals': bullish_count,
            'bearish_signals': bearish_count,
            'total_signals': total_signals
        }
    
    def calculate_volatility(self, df: pd.DataFrame, period: int = 14) -> Dict[str, float]:
        """Calculate volatility metrics."""
        if df.empty or len(df) < period:
            return {'atr': 0, 'volatility_pct': 0, 'is_high_volatility': False}
        
        # Calculate ATR manually
        df = df.copy()
        df['tr1'] = df['high'] - df['low']
        df['tr2'] = abs(df['high'] - df['close'].shift(1))
        df['tr3'] = abs(df['low'] - df['close'].shift(1))
        df['tr'] = df[['tr1', 'tr2', 'tr3']].max(axis=1)
        atr = df['tr'].rolling(window=period).mean().iloc[-1]
        
        # Volatility as percentage of price
        current_price = df['close'].iloc[-1]
        volatility_pct = (atr / current_price) * 100 if current_price > 0 else 0
        
        # Historical average volatility
        avg_volatility = df['tr'].mean()
        is_high_volatility = atr > avg_volatility * config.TRAP_DETECTION_CONFIG['volatility_spike_threshold']
        
        return {
            'atr': round(atr, 5),
            'volatility_pct': round(volatility_pct, 4),
            'is_high_volatility': is_high_volatility,
            'avg_volatility': round(avg_volatility, 5)
        }
    
    def get_trend_strength(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Analyze trend strength using multiple methods."""
        if df.empty or len(df) < 20:
            return {'trend': 'UNKNOWN', 'strength': 0}
        
        closes = df['close'].values
        
        # Linear regression slope
        x = np.arange(len(closes))
        slope = np.polyfit(x, closes, 1)[0]
        
        # Normalize slope
        avg_price = np.mean(closes)
        normalized_slope = (slope / avg_price) * 100
        
        # Determine trend
        if normalized_slope > 0.1:
            trend = 'UPTREND'
        elif normalized_slope < -0.1:
            trend = 'DOWNTREND'
        else:
            trend = 'SIDEWAYS'
        
        # Calculate R-squared for trend strength
        y_pred = np.polyval(np.polyfit(x, closes, 1), x)
        ss_res = np.sum((closes - y_pred) ** 2)
        ss_tot = np.sum((closes - np.mean(closes)) ** 2)
        r_squared = 1 - (ss_res / ss_tot) if ss_tot > 0 else 0
        
        return {
            'trend': trend,
            'strength': round(r_squared, 3),
            'slope': round(normalized_slope, 4),
            'is_strong_trend': r_squared > 0.7
        }


# Singleton instance
_ta_engine = None

def get_ta_engine() -> TechnicalAnalysisEngine:
    """Get or create technical analysis engine singleton."""
    global _ta_engine
    if _ta_engine is None:
        _ta_engine = TechnicalAnalysisEngine()
    return _ta_engine
