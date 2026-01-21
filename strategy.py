"""
MarketSense AI - Strategy Scoring System
Evaluates trade setups and calculates weighted scores.
"""

import pandas as pd
import numpy as np
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
import json

import config
from database import get_database
from technical_analysis import get_ta_engine
from psychology import get_trap_detector


class StrategyScorer:
    """Calculates weighted scores for trade setups."""
    
    def __init__(self):
        self.weights = config.SCORING_WEIGHTS
        self.thresholds = config.SCORE_THRESHOLDS
        self.db = get_database()
        self.ta_engine = get_ta_engine()
        self.trap_detector = get_trap_detector()
    
    def calculate_score(self, signals: Dict[str, Any], 
                        volatility: Dict[str, Any] = None,
                        trend: Dict[str, Any] = None,
                        session: str = None) -> Dict[str, Any]:
        """Calculate comprehensive strategy score for a trade setup."""
        
        scores = {}
        
        # 1. Trend Alignment Score (25%)
        scores['trend_alignment'] = self._calculate_trend_score(signals, trend)
        
        # 2. Momentum Score (20%)
        scores['momentum'] = self._calculate_momentum_score(signals)
        
        # 3. Volatility Score (15%)
        scores['volatility'] = self._calculate_volatility_score(signals, volatility)
        
        # 4. Candle Pattern Score (15%)
        scores['candle_pattern'] = self._calculate_candle_score(signals)
        
        # 5. Session Quality Score (10%)
        scores['session_quality'] = self._calculate_session_score(session)
        
        # 6. Psychology Risk Penalty (-15%)
        scores['psychology_risk'] = self._calculate_psychology_penalty(signals)
        
        # Calculate weighted final score
        final_score = 0
        score_breakdown = {}
        
        for factor, score in scores.items():
            weight = self.weights.get(factor, 0)
            weighted_score = score * abs(weight) * 100  # Convert to 0-100 scale contribution
            
            if weight < 0:  # Penalty factor
                final_score -= weighted_score
            else:
                final_score += weighted_score
            
            score_breakdown[factor] = {
                'raw_score': round(score, 3),
                'weight': weight,
                'contribution': round(weighted_score if weight >= 0 else -weighted_score, 2)
            }
        
        # Ensure score is within 0-100
        final_score = max(0, min(100, final_score))
        
        # Determine grade
        grade = self._get_grade(final_score)
        
        return {
            'final_score': round(final_score, 1),
            'grade': grade['label'],
            'recommendation': grade['recommendation'],
            'breakdown': score_breakdown,
            'timestamp': datetime.now().isoformat()
        }
    
    def _calculate_trend_score(self, signals: Dict[str, Any], 
                                trend: Dict[str, Any] = None) -> float:
        """Calculate trend alignment score (0-1)."""
        score = 0.5  # Base score
        
        # EMA alignment
        ema_signal = signals.get('ema', {}).get('signal', 'NEUTRAL')
        if ema_signal in ['BULLISH', 'BEARISH']:
            score += 0.2
        
        # EMA crossover bonus
        ema_crossover = signals.get('ema', {}).get('crossover', 'NONE')
        if ema_crossover in ['BULLISH_CROSS', 'BEARISH_CROSS']:
            score += 0.15
        
        # Trend strength from analysis
        if trend:
            if trend.get('is_strong_trend', False):
                score += 0.15
            
            trend_direction = trend.get('trend', 'SIDEWAYS')
            bias_direction = signals.get('overall_bias', {}).get('direction', 'NEUTRAL')
            
            # Bonus for trend-bias alignment
            if (trend_direction == 'UPTREND' and bias_direction == 'BULLISH') or \
               (trend_direction == 'DOWNTREND' and bias_direction == 'BEARISH'):
                score += 0.1
        
        return min(1.0, score)
    
    def _calculate_momentum_score(self, signals: Dict[str, Any]) -> float:
        """Calculate momentum score (0-1)."""
        score = 0.5
        
        # RSI contribution
        rsi_data = signals.get('rsi', {})
        rsi_value = rsi_data.get('value', 50)
        rsi_signal = rsi_data.get('signal', 'NEUTRAL')
        
        # Good momentum: RSI between 40-60 for entry, or extreme for reversal plays
        if 40 <= rsi_value <= 60:
            score += 0.15  # Neutral zone, good for trend continuation
        elif rsi_signal in ['OVERSOLD', 'OVERBOUGHT']:
            score += 0.1  # Potential reversal setup
        
        # MACD contribution
        macd_data = signals.get('macd', {})
        macd_histogram = macd_data.get('histogram', 0)
        macd_strength = macd_data.get('strength', 0.5)
        
        # Strong MACD signal
        if macd_strength > 0.5:
            score += 0.15
        
        # Histogram direction matches trend
        macd_trend = macd_data.get('trend', 'NEUTRAL')
        if macd_trend in ['BULLISH', 'BEARISH']:
            score += 0.1
        
        # Overall bias confidence
        bias_confidence = signals.get('overall_bias', {}).get('confidence', 0.5)
        score += bias_confidence * 0.1
        
        return min(1.0, score)
    
    def _calculate_volatility_score(self, signals: Dict[str, Any],
                                     volatility: Dict[str, Any] = None) -> float:
        """Calculate volatility score (0-1). Moderate volatility is best."""
        score = 0.5
        
        bb_data = signals.get('bollinger', {})
        bb_width = bb_data.get('width', 0.02)
        bb_percent = bb_data.get('percent', 0.5)
        
        # Ideal: moderate volatility (not too tight, not too wide)
        if 0.01 <= bb_width <= 0.03:
            score += 0.25  # Good volatility range
        elif bb_width < 0.01:
            score += 0.1  # Low volatility, potential breakout
        else:
            score -= 0.1  # High volatility, risky
        
        # Price position within bands
        if 0.3 <= bb_percent <= 0.7:
            score += 0.15  # Good entry zone
        elif bb_percent < 0.2 or bb_percent > 0.8:
            score -= 0.1  # Extreme position
        
        # Use volatility analysis if available
        if volatility:
            if volatility.get('is_high_volatility', False):
                score -= 0.15
            
            vol_pct = volatility.get('volatility_pct', 0)
            if 0.5 <= vol_pct <= 2.0:
                score += 0.1
        
        return max(0, min(1.0, score))
    
    def _calculate_candle_score(self, signals: Dict[str, Any]) -> float:
        """Calculate candle pattern score (0-1)."""
        score = 0.5
        
        candle_data = signals.get('candle', {})
        candle_type = candle_data.get('type', 'NEUTRAL')
        candle_pattern = candle_data.get('pattern', 'NONE')
        
        # Pattern bonuses
        pattern_scores = {
            'HAMMER': 0.25,
            'INVERTED_HAMMER': 0.2,
            'MARUBOZU_BULLISH': 0.3,
            'MARUBOZU_BEARISH': 0.3,
            'DOJI': 0.1,  # Indecision, lower score
            'SPINNING_TOP': 0.05,
            'STANDARD': 0.15,
            'NONE': 0
        }
        
        score += pattern_scores.get(candle_pattern, 0)
        
        # Candle type alignment with bias
        bias_direction = signals.get('overall_bias', {}).get('direction', 'NEUTRAL')
        
        if (candle_type == 'BULLISH' and bias_direction == 'BULLISH') or \
           (candle_type == 'BEARISH' and bias_direction == 'BEARISH'):
            score += 0.15
        
        return min(1.0, score)
    
    def _calculate_session_score(self, session: str = None) -> float:
        """Calculate session quality score (0-1)."""
        if not session:
            # Determine current session
            current_hour = datetime.now().hour
            session = self._get_current_session(current_hour)
        
        # Session quality rankings (based on typical liquidity)
        session_scores = {
            'OVERLAP': 1.0,    # Best liquidity
            'LONDON': 0.85,
            'NEW_YORK': 0.8,
            'ASIAN': 0.6,
            'OFF_HOURS': 0.3
        }
        
        base_score = session_scores.get(session, 0.5)
        
        # Check historical performance for this session
        session_perf = self.db.get_session_performance()
        if not session_perf.empty and session in session_perf['session'].values:
            session_data = session_perf[session_perf['session'] == session].iloc[0]
            if session_data['trades'] >= 10:
                win_rate = session_data['wins'] / session_data['trades']
                # Adjust score based on personal performance
                base_score = base_score * 0.7 + win_rate * 0.3
        
        return base_score
    
    def _get_current_session(self, hour: int) -> str:
        """Determine current trading session based on hour (UTC)."""
        sessions = config.TRADING_SESSIONS
        
        for session_name, times in sessions.items():
            start = int(times['start'].split(':')[0])
            end = int(times['end'].split(':')[0])
            
            if start <= hour < end:
                return session_name
        
        return 'OFF_HOURS'
    
    def _calculate_psychology_penalty(self, signals: Dict[str, Any]) -> float:
        """Calculate psychology risk penalty (0-1, higher = more penalty)."""
        penalty = 0
        
        # Check for trap patterns
        trap_analysis = self.trap_detector.analyze_setup(signals)
        
        if trap_analysis['assessment'] == 'HIGH_RISK_TRAP':
            penalty += 0.5
        elif trap_analysis['assessment'] == 'MODERATE_RISK':
            penalty += 0.25
        
        # Check for "too perfect" setup
        for trap in trap_analysis.get('traps_detected', []):
            if trap['type'] == 'PERFECT_SETUP_TRAP':
                penalty += 0.2
            elif trap['type'] == 'LATE_ENTRY_TRAP':
                penalty += 0.15
            elif trap['type'] == 'VOLATILITY_SPIKE':
                penalty += 0.15
        
        return min(1.0, penalty)
    
    def _get_grade(self, score: float) -> Dict[str, str]:
        """Get grade and recommendation based on score."""
        for grade, (min_score, max_score) in self.thresholds.items():
            if min_score <= score <= max_score:
                recommendations = {
                    'NO_TRADE': {
                        'label': 'F - No Trade',
                        'recommendation': 'AVOID this setup. Score too low for any trade.'
                    },
                    'RISKY': {
                        'label': 'D - Risky',
                        'recommendation': 'HIGH RISK setup. Only consider with reduced position size.'
                    },
                    'ACCEPTABLE': {
                        'label': 'C - Acceptable',
                        'recommendation': 'MODERATE setup. Proceed with caution and standard risk.'
                    },
                    'HIGH_QUALITY': {
                        'label': 'A - High Quality',
                        'recommendation': 'STRONG setup. Good entry opportunity.'
                    }
                }
                return recommendations.get(grade, {'label': 'Unknown', 'recommendation': 'Review manually'})
        
        return {'label': 'Unknown', 'recommendation': 'Score out of range'}
    
    def get_score_history(self, limit: int = 50) -> pd.DataFrame:
        """Get historical scores and their outcomes."""
        trades = self.db.get_trades(limit=limit)
        
        if trades.empty:
            return pd.DataFrame()
        
        # Filter trades with scores
        scored_trades = trades[trades['strategy_score'].notna()]
        
        return scored_trades[['entry_time', 'asset', 'strategy_score', 'outcome', 'pnl']]
    
    def analyze_score_effectiveness(self) -> Dict[str, Any]:
        """Analyze how well scores predict outcomes."""
        trades = self.db.get_trades(limit=500)
        
        if trades.empty or len(trades) < 20:
            return {'data_available': False, 'message': 'Insufficient data for analysis'}
        
        scored_trades = trades[trades['strategy_score'].notna() & trades['outcome'].notna()]
        
        if len(scored_trades) < 20:
            return {'data_available': False, 'message': 'Insufficient scored trades'}
        
        # Analyze by score range
        results = {}
        for grade, (min_score, max_score) in self.thresholds.items():
            grade_trades = scored_trades[
                (scored_trades['strategy_score'] >= min_score) & 
                (scored_trades['strategy_score'] <= max_score)
            ]
            
            if len(grade_trades) > 0:
                wins = (grade_trades['outcome'] == 'WIN').sum()
                results[grade] = {
                    'trades': len(grade_trades),
                    'wins': wins,
                    'win_rate': round(wins / len(grade_trades) * 100, 1),
                    'avg_pnl': round(grade_trades['pnl'].mean(), 2)
                }
        
        # Calculate correlation
        scored_trades['outcome_numeric'] = (scored_trades['outcome'] == 'WIN').astype(int)
        correlation = scored_trades['strategy_score'].corr(scored_trades['outcome_numeric'])
        
        return {
            'data_available': True,
            'by_grade': results,
            'score_outcome_correlation': round(correlation, 3),
            'total_analyzed': len(scored_trades),
            'effectiveness': 'HIGH' if correlation > 0.3 else 'MODERATE' if correlation > 0.1 else 'LOW'
        }


class StrategyManager:
    """Manages and tracks different trading strategies."""
    
    def __init__(self):
        self.db = get_database()
        self.scorer = StrategyScorer()
    
    def evaluate_setup(self, signals: Dict[str, Any],
                       df: pd.DataFrame = None,
                       session: str = None,
                       direction: str = None) -> Dict[str, Any]:
        """Complete evaluation of a trade setup."""
        from technical_analysis import get_ta_engine
        
        ta_engine = get_ta_engine()
        
        # Get additional analysis
        volatility = ta_engine.calculate_volatility(df) if df is not None else None
        trend = ta_engine.get_trend_strength(df) if df is not None else None
        
        # Calculate score
        score_result = self.scorer.calculate_score(signals, volatility, trend, session)
        
        # Get trap analysis
        trap_detector = get_trap_detector()
        trap_analysis = trap_detector.analyze_setup(signals, df)
        
        return {
            'score': score_result,
            'signals': signals,
            'volatility': volatility,
            'trend': trend,
            'trap_analysis': trap_analysis,
            'direction': direction,
            'session': session,
            'timestamp': datetime.now().isoformat()
        }
    
    def get_strategy_rankings(self) -> List[Dict[str, Any]]:
        """Get ranking of strategies by performance."""
        trades = self.db.get_trades(limit=1000)
        
        if trades.empty:
            return []
        
        # Group by score ranges
        trades['score_range'] = pd.cut(
            trades['strategy_score'],
            bins=[0, 40, 60, 75, 100],
            labels=['0-40', '41-60', '61-75', '76-100']
        )
        
        rankings = []
        for score_range in ['76-100', '61-75', '41-60', '0-40']:
            range_trades = trades[trades['score_range'] == score_range]
            
            if len(range_trades) > 0:
                wins = (range_trades['outcome'] == 'WIN').sum()
                rankings.append({
                    'score_range': score_range,
                    'total_trades': len(range_trades),
                    'wins': wins,
                    'losses': len(range_trades) - wins,
                    'win_rate': round(wins / len(range_trades) * 100, 1),
                    'total_pnl': round(range_trades['pnl'].sum(), 2),
                    'avg_pnl': round(range_trades['pnl'].mean(), 2)
                })
        
        return rankings


# Singleton instances
_strategy_scorer = None
_strategy_manager = None

def get_strategy_scorer() -> StrategyScorer:
    """Get or create strategy scorer singleton."""
    global _strategy_scorer
    if _strategy_scorer is None:
        _strategy_scorer = StrategyScorer()
    return _strategy_scorer

def get_strategy_manager() -> StrategyManager:
    """Get or create strategy manager singleton."""
    global _strategy_manager
    if _strategy_manager is None:
        _strategy_manager = StrategyManager()
    return _strategy_manager
