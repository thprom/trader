"""
MarketSense AI - Psychology Analysis Module
Analyzes user behavior patterns and detects marketing manipulation traps.
"""

import pandas as pd
import numpy as np
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta
import json

import config
from database import get_database


class UserPsychologyAnalyzer:
    """Analyzes user trading behavior and psychology patterns."""
    
    def __init__(self):
        self.config = config.PSYCHOLOGY_CONFIG
        self.db = get_database()
    
    def analyze_user_behavior(self) -> Dict[str, Any]:
        """Comprehensive analysis of user trading behavior."""
        analysis = {
            'timestamp': datetime.now().isoformat(),
            'overtrading': self._detect_overtrading(),
            'revenge_trading': self._detect_revenge_trading(),
            'emotional_clusters': self._detect_emotional_clusters(),
            'time_performance': self._analyze_time_performance(),
            'loss_recovery': self._analyze_loss_recovery_behavior(),
            'discipline_score': self._calculate_discipline_score(),
            'warnings': [],
            'recommendations': []
        }
        
        # Generate warnings based on analysis
        analysis['warnings'] = self._generate_warnings(analysis)
        analysis['recommendations'] = self._generate_recommendations(analysis)
        
        return analysis
    
    def _detect_overtrading(self) -> Dict[str, Any]:
        """Detect if user is overtrading."""
        recent_trades = self.db.get_recent_trades(hours=1)
        trades_per_hour = len(recent_trades)
        
        is_overtrading = trades_per_hour >= self.config['overtrading_threshold']
        
        # Get daily trade count
        today_trades = self.db.get_trades(limit=1000)
        if not today_trades.empty:
            today_trades['entry_time'] = pd.to_datetime(today_trades['entry_time'])
            today = datetime.now().date()
            daily_count = len(today_trades[today_trades['entry_time'].dt.date == today])
        else:
            daily_count = 0
        
        max_daily = config.SIMULATION_CONFIG['max_daily_trades']
        
        return {
            'trades_last_hour': trades_per_hour,
            'threshold': self.config['overtrading_threshold'],
            'is_overtrading': is_overtrading,
            'daily_trades': daily_count,
            'max_daily_trades': max_daily,
            'daily_limit_reached': daily_count >= max_daily
        }
    
    def _detect_revenge_trading(self) -> Dict[str, Any]:
        """Detect revenge trading patterns after losses."""
        trades = self.db.get_trades(limit=50)
        
        if trades.empty or len(trades) < 2:
            return {'detected': False, 'instances': 0}
        
        trades = trades.sort_values('entry_time')
        trades['entry_time'] = pd.to_datetime(trades['entry_time'])
        
        revenge_instances = 0
        revenge_window = self.config['revenge_trade_window']
        
        for i in range(1, len(trades)):
            prev_trade = trades.iloc[i-1]
            curr_trade = trades.iloc[i]
            
            if prev_trade['outcome'] == 'LOSS':
                time_diff = (curr_trade['entry_time'] - prev_trade['entry_time']).total_seconds()
                
                if time_diff < revenge_window:
                    revenge_instances += 1
        
        return {
            'detected': revenge_instances > 0,
            'instances': revenge_instances,
            'window_seconds': revenge_window,
            'severity': 'HIGH' if revenge_instances >= 3 else 'MEDIUM' if revenge_instances >= 1 else 'LOW'
        }
    
    def _detect_emotional_clusters(self) -> Dict[str, Any]:
        """Detect clusters of rapid trades indicating emotional trading."""
        trades = self.db.get_trades(limit=100)
        
        if trades.empty or len(trades) < 3:
            return {'detected': False, 'clusters': 0}
        
        trades = trades.sort_values('entry_time')
        trades['entry_time'] = pd.to_datetime(trades['entry_time'])
        
        cluster_size = self.config['emotional_cluster_size']
        clusters_found = 0
        
        # Look for rapid consecutive trades (within 2 minutes each)
        rapid_trade_threshold = 120  # seconds
        
        i = 0
        while i < len(trades) - cluster_size + 1:
            cluster_trades = trades.iloc[i:i+cluster_size]
            
            time_diffs = cluster_trades['entry_time'].diff().dt.total_seconds().dropna()
            
            if all(time_diffs < rapid_trade_threshold):
                clusters_found += 1
                i += cluster_size  # Skip past this cluster
            else:
                i += 1
        
        return {
            'detected': clusters_found > 0,
            'clusters': clusters_found,
            'cluster_size': cluster_size,
            'rapid_threshold_seconds': rapid_trade_threshold
        }
    
    def _analyze_time_performance(self) -> Dict[str, Any]:
        """Analyze performance by time of day."""
        hourly_perf = self.db.get_hourly_performance()
        
        if hourly_perf.empty:
            return {'best_hours': [], 'worst_hours': [], 'data_available': False}
        
        hourly_perf['win_rate'] = hourly_perf['wins'] / hourly_perf['trades'] * 100
        hourly_perf = hourly_perf[hourly_perf['trades'] >= 5]  # Minimum sample size
        
        if hourly_perf.empty:
            return {'best_hours': [], 'worst_hours': [], 'data_available': False}
        
        # Sort by win rate
        sorted_perf = hourly_perf.sort_values('win_rate', ascending=False)
        
        best_hours = sorted_perf.head(3)[['hour', 'win_rate', 'trades']].to_dict('records')
        worst_hours = sorted_perf.tail(3)[['hour', 'win_rate', 'trades']].to_dict('records')
        
        return {
            'best_hours': best_hours,
            'worst_hours': worst_hours,
            'data_available': True,
            'total_hours_analyzed': len(hourly_perf)
        }
    
    def _analyze_loss_recovery_behavior(self) -> Dict[str, Any]:
        """Analyze how user performs after consecutive losses."""
        trades = self.db.get_trades(limit=200)
        
        if trades.empty or len(trades) < 10:
            return {'data_available': False}
        
        trades = trades.sort_values('entry_time')
        
        # Track performance after N consecutive losses
        max_consecutive = config.SIMULATION_CONFIG['max_consecutive_losses']
        
        consecutive_losses = 0
        performance_after_losses = {1: [], 2: [], 3: []}
        
        for i in range(len(trades)):
            outcome = trades.iloc[i]['outcome']
            
            if outcome == 'LOSS':
                consecutive_losses += 1
            else:
                # Record performance after consecutive losses
                if consecutive_losses > 0 and consecutive_losses <= 3:
                    performance_after_losses[consecutive_losses].append(
                        1 if outcome == 'WIN' else 0
                    )
                consecutive_losses = 0
        
        # Calculate win rates after N losses
        recovery_rates = {}
        for losses, outcomes in performance_after_losses.items():
            if outcomes:
                recovery_rates[f'after_{losses}_losses'] = {
                    'win_rate': round(sum(outcomes) / len(outcomes) * 100, 1),
                    'sample_size': len(outcomes)
                }
        
        return {
            'data_available': True,
            'recovery_rates': recovery_rates,
            'max_consecutive_before_pause': max_consecutive
        }
    
    def _calculate_discipline_score(self) -> Dict[str, Any]:
        """Calculate overall trading discipline score."""
        violations = self.db.get_violations(limit=100)
        trades = self.db.get_trades(limit=100)
        
        if trades.empty:
            return {'score': 100, 'grade': 'A', 'factors': {}}
        
        total_trades = len(trades)
        total_violations = len(violations)
        
        # Calculate factors
        factors = {}
        
        # Rule adherence (fewer violations = better)
        violation_rate = total_violations / total_trades if total_trades > 0 else 0
        factors['rule_adherence'] = max(0, 100 - violation_rate * 50)
        
        # Journal compliance
        journal_entries = trades['journal_entry'].notna().sum()
        factors['journal_compliance'] = (journal_entries / total_trades * 100) if total_trades > 0 else 0
        
        # Score consistency (trading within acceptable score range)
        if 'strategy_score' in trades.columns:
            good_score_trades = trades[trades['strategy_score'] >= 60]
            factors['score_discipline'] = (len(good_score_trades) / total_trades * 100) if total_trades > 0 else 50
        else:
            factors['score_discipline'] = 50
        
        # Calculate overall score
        weights = {'rule_adherence': 0.4, 'journal_compliance': 0.3, 'score_discipline': 0.3}
        overall_score = sum(factors[k] * weights[k] for k in factors)
        
        # Assign grade
        if overall_score >= 90:
            grade = 'A'
        elif overall_score >= 80:
            grade = 'B'
        elif overall_score >= 70:
            grade = 'C'
        elif overall_score >= 60:
            grade = 'D'
        else:
            grade = 'F'
        
        return {
            'score': round(overall_score, 1),
            'grade': grade,
            'factors': {k: round(v, 1) for k, v in factors.items()}
        }
    
    def _generate_warnings(self, analysis: Dict[str, Any]) -> List[str]:
        """Generate warnings based on behavior analysis."""
        warnings = []
        
        # Overtrading warning
        if analysis['overtrading']['is_overtrading']:
            warnings.append(
                f"⚠️ OVERTRADING DETECTED: {analysis['overtrading']['trades_last_hour']} trades in the last hour. "
                f"Recommended maximum is {analysis['overtrading']['threshold']}."
            )
        
        if analysis['overtrading']['daily_limit_reached']:
            warnings.append(
                f"🛑 DAILY LIMIT REACHED: You've made {analysis['overtrading']['daily_trades']} trades today. "
                "Consider stopping for the day."
            )
        
        # Revenge trading warning
        if analysis['revenge_trading']['detected']:
            warnings.append(
                f"⚠️ REVENGE TRADING PATTERN: {analysis['revenge_trading']['instances']} instances detected. "
                "Take a break after losses before entering new trades."
            )
        
        # Emotional cluster warning
        if analysis['emotional_clusters']['detected']:
            warnings.append(
                f"⚠️ EMOTIONAL TRADING: {analysis['emotional_clusters']['clusters']} rapid trade clusters detected. "
                "Slow down and analyze each setup carefully."
            )
        
        # Discipline warning
        if analysis['discipline_score']['score'] < 60:
            warnings.append(
                f"📉 LOW DISCIPLINE SCORE: {analysis['discipline_score']['score']}/100. "
                "Focus on following your trading rules and journaling trades."
            )
        
        return warnings
    
    def _generate_recommendations(self, analysis: Dict[str, Any]) -> List[str]:
        """Generate recommendations based on behavior analysis."""
        recommendations = []
        
        # Time-based recommendations
        time_perf = analysis['time_performance']
        if time_perf.get('data_available') and time_perf.get('best_hours'):
            best_hour = time_perf['best_hours'][0]
            recommendations.append(
                f"📊 Your best performance is at {best_hour['hour']}:00 "
                f"({best_hour['win_rate']:.1f}% win rate). Consider focusing on this time."
            )
        
        if time_perf.get('data_available') and time_perf.get('worst_hours'):
            worst_hour = time_perf['worst_hours'][0]
            if worst_hour['win_rate'] < 40:
                recommendations.append(
                    f"⏰ Avoid trading at {worst_hour['hour']}:00 "
                    f"({worst_hour['win_rate']:.1f}% win rate)."
                )
        
        # Loss recovery recommendations
        loss_recovery = analysis['loss_recovery']
        if loss_recovery.get('data_available'):
            for key, data in loss_recovery.get('recovery_rates', {}).items():
                if data['win_rate'] < 40 and data['sample_size'] >= 5:
                    losses = key.split('_')[1]
                    recommendations.append(
                        f"📉 Your win rate drops to {data['win_rate']}% after {losses} consecutive losses. "
                        "Consider taking a break after losing streaks."
                    )
        
        # Discipline recommendations
        discipline = analysis['discipline_score']
        if discipline['factors'].get('journal_compliance', 100) < 50:
            recommendations.append(
                "📝 Improve journaling: Only {:.0f}% of trades have journal entries. "
                "Document your reasoning for each trade.".format(discipline['factors']['journal_compliance'])
            )
        
        return recommendations
    
    def should_pause_trading(self) -> Tuple[bool, str]:
        """Determine if trading should be paused based on behavior."""
        analysis = self.analyze_user_behavior()
        
        # Check for critical conditions
        if analysis['overtrading']['daily_limit_reached']:
            return True, "Daily trade limit reached. Trading paused until tomorrow."
        
        if analysis['revenge_trading'].get('severity', 'LOW') == 'HIGH':
            return True, "Multiple revenge trading instances detected. Take a 1-hour break."
        
        # Check consecutive losses
        trades = self.db.get_trades(limit=10)
        if not trades.empty:
            recent_outcomes = trades.head(config.SIMULATION_CONFIG['max_consecutive_losses'])['outcome'].tolist()
            if all(o == 'LOSS' for o in recent_outcomes):
                return True, f"Maximum consecutive losses ({len(recent_outcomes)}) reached. Take a break."
        
        return False, ""
    
    def get_current_emotional_state(self) -> Dict[str, Any]:
        """Estimate current emotional state based on recent activity."""
        recent_trades = self.db.get_trades(limit=10)
        
        if recent_trades.empty:
            return {'state': 'CALM', 'confidence': 0.5, 'factors': []}
        
        factors = []
        risk_score = 0
        
        # Recent performance
        wins = (recent_trades['outcome'] == 'WIN').sum()
        losses = (recent_trades['outcome'] == 'LOSS').sum()
        
        if losses > wins:
            risk_score += 2
            factors.append('Recent losses outweigh wins')
        
        # Trade frequency
        if len(recent_trades) >= 5:
            recent_trades['entry_time'] = pd.to_datetime(recent_trades['entry_time'])
            time_span = (recent_trades['entry_time'].max() - recent_trades['entry_time'].min()).total_seconds()
            if time_span < 1800:  # 30 minutes
                risk_score += 2
                factors.append('High trade frequency')
        
        # Consecutive losses
        consecutive_losses = 0
        for outcome in recent_trades['outcome']:
            if outcome == 'LOSS':
                consecutive_losses += 1
            else:
                break
        
        if consecutive_losses >= 2:
            risk_score += consecutive_losses
            factors.append(f'{consecutive_losses} consecutive losses')
        
        # Determine state
        if risk_score >= 5:
            state = 'TILTED'
        elif risk_score >= 3:
            state = 'FRUSTRATED'
        elif risk_score >= 1:
            state = 'CAUTIOUS'
        else:
            state = 'CALM'
        
        return {
            'state': state,
            'risk_score': risk_score,
            'factors': factors,
            'recommendation': self._get_emotional_recommendation(state)
        }
    
    def _get_emotional_recommendation(self, state: str) -> str:
        """Get recommendation based on emotional state."""
        recommendations = {
            'TILTED': "🛑 STOP TRADING NOW. Take at least a 1-hour break. Review your journal.",
            'FRUSTRATED': "⚠️ Consider taking a 15-minute break. Only take A+ setups.",
            'CAUTIOUS': "⚡ Be selective. Stick to your highest-conviction setups only.",
            'CALM': "✅ Good emotional state. Continue following your trading plan."
        }
        return recommendations.get(state, "Continue trading carefully.")


class MarketingTrapDetector:
    """Detects marketing manipulation patterns in trading setups."""
    
    def __init__(self):
        self.config = config.TRAP_DETECTION_CONFIG
    
    def analyze_setup(self, signals: Dict[str, Any], 
                      historical_df: pd.DataFrame = None) -> Dict[str, Any]:
        """Analyze a trading setup for potential manipulation traps."""
        traps_detected = []
        risk_factors = []
        overall_risk = 0
        
        # Check for "too perfect" setup
        perfect_check = self._check_perfect_setup(signals)
        if perfect_check['is_trap']:
            traps_detected.append(perfect_check)
            overall_risk += 30
        
        # Check for late entry
        late_entry_check = self._check_late_entry(signals, historical_df)
        if late_entry_check['is_trap']:
            traps_detected.append(late_entry_check)
            overall_risk += 25
        
        # Check for volatility spike
        volatility_check = self._check_volatility_spike(signals, historical_df)
        if volatility_check['is_trap']:
            traps_detected.append(volatility_check)
            overall_risk += 25
        
        # Check for indicator divergence
        divergence_check = self._check_indicator_divergence(signals)
        if divergence_check['is_concern']:
            risk_factors.append(divergence_check)
            overall_risk += 15
        
        # Determine overall assessment
        if overall_risk >= 50:
            assessment = 'HIGH_RISK_TRAP'
            recommendation = 'AVOID - Multiple trap signals detected'
        elif overall_risk >= 25:
            assessment = 'MODERATE_RISK'
            recommendation = 'CAUTION - Some concerning patterns present'
        else:
            assessment = 'LOW_RISK'
            recommendation = 'PROCEED - No significant trap patterns detected'
        
        return {
            'traps_detected': traps_detected,
            'risk_factors': risk_factors,
            'overall_risk_score': overall_risk,
            'assessment': assessment,
            'recommendation': recommendation,
            'analysis_time': datetime.now().isoformat()
        }
    
    def _check_perfect_setup(self, signals: Dict[str, Any]) -> Dict[str, Any]:
        """Check if setup is suspiciously perfect (all indicators aligned)."""
        bias = signals.get('overall_bias', {})
        total = bias.get('total_signals', 5)
        bullish = bias.get('bullish_signals', 0)
        bearish = bias.get('bearish_signals', 0)
        
        max_aligned = max(bullish, bearish)
        alignment_ratio = max_aligned / total if total > 0 else 0
        
        is_trap = alignment_ratio >= self.config['perfect_setup_threshold']
        
        return {
            'type': 'PERFECT_SETUP_TRAP',
            'is_trap': is_trap,
            'alignment_ratio': round(alignment_ratio, 2),
            'threshold': self.config['perfect_setup_threshold'],
            'message': (
                "This setup looks too perfect. Historically, setups with 90%+ indicator "
                "alignment often fail. The market may be setting up a trap."
            ) if is_trap else "Indicator alignment within normal range."
        }
    
    def _check_late_entry(self, signals: Dict[str, Any], 
                          historical_df: pd.DataFrame = None) -> Dict[str, Any]:
        """Check if this is a late entry into an existing move."""
        bb_percent = signals.get('bollinger', {}).get('percent', 0.5)
        threshold = self.config['late_entry_threshold']
        
        is_late = bb_percent > threshold or bb_percent < (1 - threshold)
        
        direction = 'overbought zone' if bb_percent > threshold else 'oversold zone'
        
        return {
            'type': 'LATE_ENTRY_TRAP',
            'is_trap': is_late,
            'bb_percent': round(bb_percent, 3),
            'threshold': threshold,
            'message': (
                f"Price is in the {direction} ({bb_percent:.1%} of Bollinger range). "
                "Most of the move may already be complete. High risk of reversal."
            ) if is_late else "Entry timing appears reasonable."
        }
    
    def _check_volatility_spike(self, signals: Dict[str, Any],
                                 historical_df: pd.DataFrame = None) -> Dict[str, Any]:
        """Check for sudden volatility spikes that may indicate manipulation."""
        bb_width = signals.get('bollinger', {}).get('width', 0)
        threshold = self.config['volatility_spike_threshold']
        
        # If we have historical data, compare to average
        if historical_df is not None and 'bb_width' in historical_df.columns:
            avg_width = historical_df['bb_width'].mean()
            is_spike = bb_width > avg_width * threshold
            ratio = bb_width / avg_width if avg_width > 0 else 1
        else:
            # Use absolute threshold
            is_spike = bb_width > 0.05  # 5% width is high
            ratio = bb_width / 0.025 if bb_width > 0 else 1
        
        return {
            'type': 'VOLATILITY_SPIKE',
            'is_trap': is_spike,
            'current_width': round(bb_width, 4),
            'ratio_to_average': round(ratio, 2),
            'message': (
                f"Volatility is {ratio:.1f}x higher than normal. "
                "Sudden spikes often precede reversals or stop hunts."
            ) if is_spike else "Volatility within normal range."
        }
    
    def _check_indicator_divergence(self, signals: Dict[str, Any]) -> Dict[str, Any]:
        """Check for divergence between price action and indicators."""
        rsi_signal = signals.get('rsi', {}).get('signal', 'NEUTRAL')
        macd_trend = signals.get('macd', {}).get('trend', 'NEUTRAL')
        ema_signal = signals.get('ema', {}).get('signal', 'NEUTRAL')
        candle_type = signals.get('candle', {}).get('type', 'NEUTRAL')
        
        # Check for conflicting signals
        bullish_count = sum(1 for s in [rsi_signal, macd_trend, ema_signal, candle_type] 
                          if s in ['BULLISH', 'OVERSOLD'])
        bearish_count = sum(1 for s in [rsi_signal, macd_trend, ema_signal, candle_type] 
                          if s in ['BEARISH', 'OVERBOUGHT'])
        
        # Divergence if signals are split
        is_divergent = bullish_count >= 2 and bearish_count >= 2
        
        return {
            'type': 'INDICATOR_DIVERGENCE',
            'is_concern': is_divergent,
            'bullish_signals': bullish_count,
            'bearish_signals': bearish_count,
            'message': (
                "Indicators are showing conflicting signals. "
                "This uncertainty often leads to choppy price action."
            ) if is_divergent else "Indicators showing reasonable alignment."
        }
    
    def get_trap_history_analysis(self, asset: str = None) -> Dict[str, Any]:
        """Analyze historical trap patterns and their outcomes."""
        db = get_database()
        trades = db.get_trades(limit=500, asset=asset)
        
        if trades.empty:
            return {'data_available': False}
        
        # Analyze trades where traps were detected
        trap_trades = trades[trades['ai_recommendation'] == 'AVOID']
        
        if trap_trades.empty:
            return {
                'data_available': True,
                'trap_trades_count': 0,
                'message': 'No trap-flagged trades in history'
            }
        
        # Calculate outcomes of ignored warnings
        ignored_traps = trap_trades[trap_trades['outcome'].notna()]
        
        if ignored_traps.empty:
            return {
                'data_available': True,
                'trap_trades_count': len(trap_trades),
                'ignored_count': 0
            }
        
        loss_rate = (ignored_traps['outcome'] == 'LOSS').sum() / len(ignored_traps) * 100
        
        return {
            'data_available': True,
            'trap_trades_count': len(trap_trades),
            'ignored_count': len(ignored_traps),
            'loss_rate_when_ignored': round(loss_rate, 1),
            'message': f"Trades taken despite trap warnings have a {loss_rate:.1f}% loss rate."
        }


# Singleton instances
_psychology_analyzer = None
_trap_detector = None

def get_psychology_analyzer() -> UserPsychologyAnalyzer:
    """Get or create psychology analyzer singleton."""
    global _psychology_analyzer
    if _psychology_analyzer is None:
        _psychology_analyzer = UserPsychologyAnalyzer()
    return _psychology_analyzer

def get_trap_detector() -> MarketingTrapDetector:
    """Get or create trap detector singleton."""
    global _trap_detector
    if _trap_detector is None:
        _trap_detector = MarketingTrapDetector()
    return _trap_detector
