"""
MarketSense AI - Reporting & Feedback System
Generates daily summaries, weekly reviews, and improvement suggestions.
"""

import pandas as pd
import numpy as np
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import json
import os

import config
from database import get_database
from psychology import get_psychology_analyzer
from strategy import get_strategy_scorer


class ReportGenerator:
    """Generates comprehensive trading reports."""
    
    def __init__(self):
        self.db = get_database()
        self.psychology = get_psychology_analyzer()
        self.scorer = get_strategy_scorer()
        self.reports_path = config.REPORT_CONFIG['reports_path']
        os.makedirs(self.reports_path, exist_ok=True)
    
    def generate_daily_summary(self, date: datetime = None) -> Dict[str, Any]:
        """Generate daily trading summary."""
        if date is None:
            date = datetime.now()
        
        start_date = date.replace(hour=0, minute=0, second=0, microsecond=0)
        end_date = start_date + timedelta(days=1)
        
        trades = self.db.get_trades(limit=1000, start_date=start_date, end_date=end_date)
        
        summary = {
            'date': date.strftime('%Y-%m-%d'),
            'generated_at': datetime.now().isoformat(),
            'trading_activity': self._analyze_trading_activity(trades),
            'performance': self._analyze_performance(trades),
            'psychology': self._analyze_daily_psychology(trades),
            'best_worst_trades': self._get_best_worst_trades(trades),
            'score_analysis': self._analyze_scores(trades),
            'session_breakdown': self._analyze_sessions(trades),
            'mistakes': self._identify_mistakes(trades),
            'improvements': self._generate_improvements(trades)
        }
        
        # Save report
        self._save_report(summary, 'daily', date)
        
        return summary
    
    def generate_weekly_review(self, end_date: datetime = None) -> Dict[str, Any]:
        """Generate weekly performance review."""
        if end_date is None:
            end_date = datetime.now()
        
        start_date = end_date - timedelta(days=7)
        
        trades = self.db.get_trades(limit=5000, start_date=start_date, end_date=end_date)
        
        review = {
            'period': {
                'start': start_date.strftime('%Y-%m-%d'),
                'end': end_date.strftime('%Y-%m-%d')
            },
            'generated_at': datetime.now().isoformat(),
            'overview': self._generate_weekly_overview(trades),
            'daily_breakdown': self._generate_daily_breakdown(trades),
            'strategy_performance': self._analyze_strategy_performance(trades),
            'psychology_trends': self._analyze_psychology_trends(trades),
            'progress_metrics': self._calculate_progress_metrics(trades),
            'key_learnings': self._extract_key_learnings(trades),
            'next_week_focus': self._generate_focus_areas(trades)
        }
        
        # Save report
        self._save_report(review, 'weekly', end_date)
        
        return review
    
    def _analyze_trading_activity(self, trades: pd.DataFrame) -> Dict[str, Any]:
        """Analyze trading activity metrics."""
        if trades.empty:
            return {
                'total_trades': 0,
                'active_hours': 0,
                'avg_trades_per_hour': 0,
                'assets_traded': []
            }
        
        trades['entry_time'] = pd.to_datetime(trades['entry_time'])
        
        return {
            'total_trades': len(trades),
            'active_hours': trades['entry_time'].dt.hour.nunique(),
            'avg_trades_per_hour': round(len(trades) / max(1, trades['entry_time'].dt.hour.nunique()), 2),
            'assets_traded': trades['asset'].unique().tolist(),
            'most_traded_asset': trades['asset'].mode().iloc[0] if not trades['asset'].mode().empty else None,
            'timeframes_used': trades['timeframe'].unique().tolist()
        }
    
    def _analyze_performance(self, trades: pd.DataFrame) -> Dict[str, Any]:
        """Analyze trading performance."""
        if trades.empty:
            return {
                'wins': 0, 'losses': 0, 'win_rate': 0,
                'total_pnl': 0, 'avg_pnl': 0
            }
        
        wins = (trades['outcome'] == 'WIN').sum()
        losses = (trades['outcome'] == 'LOSS').sum()
        total = wins + losses
        
        return {
            'wins': int(wins),
            'losses': int(losses),
            'win_rate': round(wins / total * 100, 1) if total > 0 else 0,
            'total_pnl': round(trades['pnl'].sum(), 2),
            'avg_pnl': round(trades['pnl'].mean(), 2),
            'best_trade': round(trades['pnl'].max(), 2),
            'worst_trade': round(trades['pnl'].min(), 2),
            'profit_factor': self._calculate_profit_factor(trades),
            'expectancy': self._calculate_expectancy(trades)
        }
    
    def _calculate_profit_factor(self, trades: pd.DataFrame) -> float:
        """Calculate profit factor (gross profit / gross loss)."""
        if trades.empty:
            return 0
        
        gross_profit = trades[trades['pnl'] > 0]['pnl'].sum()
        gross_loss = abs(trades[trades['pnl'] < 0]['pnl'].sum())
        
        if gross_loss == 0:
            return float('inf') if gross_profit > 0 else 0
        
        return round(gross_profit / gross_loss, 2)
    
    def _calculate_expectancy(self, trades: pd.DataFrame) -> float:
        """Calculate trade expectancy."""
        if trades.empty:
            return 0
        
        win_trades = trades[trades['outcome'] == 'WIN']
        loss_trades = trades[trades['outcome'] == 'LOSS']
        
        if len(trades) == 0:
            return 0
        
        win_rate = len(win_trades) / len(trades)
        avg_win = win_trades['pnl'].mean() if not win_trades.empty else 0
        avg_loss = abs(loss_trades['pnl'].mean()) if not loss_trades.empty else 0
        
        expectancy = (win_rate * avg_win) - ((1 - win_rate) * avg_loss)
        return round(expectancy, 2)
    
    def _analyze_daily_psychology(self, trades: pd.DataFrame) -> Dict[str, Any]:
        """Analyze psychological aspects of daily trading."""
        analysis = self.psychology.analyze_user_behavior()
        
        return {
            'discipline_score': analysis['discipline_score'],
            'overtrading_detected': analysis['overtrading']['is_overtrading'],
            'revenge_trading_detected': analysis['revenge_trading']['detected'],
            'emotional_state': self.psychology.get_current_emotional_state(),
            'warnings_count': len(analysis['warnings'])
        }
    
    def _get_best_worst_trades(self, trades: pd.DataFrame) -> Dict[str, Any]:
        """Get best and worst trades of the period."""
        if trades.empty:
            return {'best': None, 'worst': None}
        
        best_idx = trades['pnl'].idxmax()
        worst_idx = trades['pnl'].idxmin()
        
        def trade_summary(trade):
            return {
                'asset': trade['asset'],
                'direction': trade['direction'],
                'pnl': round(trade['pnl'], 2),
                'score': trade.get('strategy_score'),
                'entry_time': str(trade['entry_time'])
            }
        
        return {
            'best': trade_summary(trades.loc[best_idx]) if pd.notna(best_idx) else None,
            'worst': trade_summary(trades.loc[worst_idx]) if pd.notna(worst_idx) else None
        }
    
    def _analyze_scores(self, trades: pd.DataFrame) -> Dict[str, Any]:
        """Analyze strategy scores."""
        if trades.empty or trades['strategy_score'].isna().all():
            return {'avg_score': 0, 'score_distribution': {}}
        
        scores = trades['strategy_score'].dropna()
        
        distribution = {
            'high_quality': len(scores[scores >= 76]),
            'acceptable': len(scores[(scores >= 61) & (scores < 76)]),
            'risky': len(scores[(scores >= 41) & (scores < 61)]),
            'no_trade': len(scores[scores < 41])
        }
        
        return {
            'avg_score': round(scores.mean(), 1),
            'median_score': round(scores.median(), 1),
            'score_distribution': distribution,
            'trades_below_threshold': distribution['no_trade'] + distribution['risky']
        }
    
    def _analyze_sessions(self, trades: pd.DataFrame) -> Dict[str, Any]:
        """Analyze performance by trading session."""
        if trades.empty:
            return {}
        
        session_perf = self.db.get_session_performance()
        
        if session_perf.empty:
            return {}
        
        results = {}
        for _, row in session_perf.iterrows():
            if row['trades'] > 0:
                results[row['session']] = {
                    'trades': int(row['trades']),
                    'wins': int(row['wins']),
                    'win_rate': round(row['wins'] / row['trades'] * 100, 1),
                    'total_pnl': round(row['total_pnl'], 2)
                }
        
        return results
    
    def _identify_mistakes(self, trades: pd.DataFrame) -> List[Dict[str, Any]]:
        """Identify trading mistakes."""
        mistakes = []
        
        if trades.empty:
            return mistakes
        
        # Low score trades that were taken
        low_score_losses = trades[
            (trades['strategy_score'] < 50) & 
            (trades['outcome'] == 'LOSS')
        ]
        
        if len(low_score_losses) > 0:
            mistakes.append({
                'type': 'LOW_SCORE_TRADES',
                'count': len(low_score_losses),
                'description': f"Took {len(low_score_losses)} trades with scores below 50 that resulted in losses",
                'suggestion': "Wait for higher quality setups (score > 60)"
            })
        
        # Ignored AI recommendations
        ignored_avoid = trades[
            (trades['ai_recommendation'] == 'AVOID') & 
            (trades['outcome'] == 'LOSS')
        ]
        
        if len(ignored_avoid) > 0:
            mistakes.append({
                'type': 'IGNORED_WARNINGS',
                'count': len(ignored_avoid),
                'description': f"Ignored {len(ignored_avoid)} AVOID recommendations that resulted in losses",
                'suggestion': "Trust the AI warnings and skip flagged setups"
            })
        
        # Trades without journal entries
        no_journal = trades[trades['journal_entry'].isna()]
        
        if len(no_journal) > len(trades) * 0.5:
            mistakes.append({
                'type': 'MISSING_JOURNALS',
                'count': len(no_journal),
                'description': f"{len(no_journal)} trades without journal entries",
                'suggestion': "Document your reasoning for every trade"
            })
        
        # Check violations
        violations = self.db.get_violations(limit=50)
        if not violations.empty:
            today = datetime.now().date()
            violations['timestamp'] = pd.to_datetime(violations['timestamp'])
            today_violations = violations[violations['timestamp'].dt.date == today]
            
            if len(today_violations) > 0:
                for _, v in today_violations.iterrows():
                    mistakes.append({
                        'type': v['violation_type'],
                        'count': 1,
                        'description': v['description'],
                        'suggestion': "Review and follow trading rules"
                    })
        
        return mistakes
    
    def _generate_improvements(self, trades: pd.DataFrame) -> List[str]:
        """Generate improvement suggestions."""
        improvements = []
        
        if trades.empty:
            improvements.append("Start trading to generate performance data")
            return improvements
        
        # Win rate based suggestions
        wins = (trades['outcome'] == 'WIN').sum()
        total = len(trades[trades['outcome'].notna()])
        win_rate = wins / total * 100 if total > 0 else 0
        
        if win_rate < 50:
            improvements.append("Focus on higher probability setups. Current win rate is below 50%.")
        
        # Score based suggestions
        avg_score = trades['strategy_score'].mean()
        if pd.notna(avg_score) and avg_score < 60:
            improvements.append(f"Average setup score is {avg_score:.1f}. Aim for scores above 60.")
        
        # Time-based suggestions
        hourly_perf = self.db.get_hourly_performance()
        if not hourly_perf.empty:
            hourly_perf['win_rate'] = hourly_perf['wins'] / hourly_perf['trades'] * 100
            best_hours = hourly_perf.nlargest(2, 'win_rate')
            if not best_hours.empty:
                hours = best_hours['hour'].tolist()
                improvements.append(f"Your best performance is at hours {hours}. Consider focusing on these times.")
        
        # Psychology based suggestions
        psychology_analysis = self.psychology.analyze_user_behavior()
        
        if psychology_analysis['overtrading']['is_overtrading']:
            improvements.append("Reduce trading frequency. Quality over quantity.")
        
        if psychology_analysis['revenge_trading']['detected']:
            improvements.append("Take breaks after losses to avoid revenge trading.")
        
        if psychology_analysis['discipline_score']['score'] < 70:
            improvements.append("Work on trading discipline. Follow your rules consistently.")
        
        return improvements
    
    def _generate_weekly_overview(self, trades: pd.DataFrame) -> Dict[str, Any]:
        """Generate weekly overview statistics."""
        return {
            'total_trades': len(trades),
            'performance': self._analyze_performance(trades),
            'avg_daily_trades': round(len(trades) / 7, 1),
            'trading_days': trades['entry_time'].dt.date.nunique() if not trades.empty else 0
        }
    
    def _generate_daily_breakdown(self, trades: pd.DataFrame) -> List[Dict[str, Any]]:
        """Generate day-by-day breakdown."""
        if trades.empty:
            return []
        
        trades['date'] = pd.to_datetime(trades['entry_time']).dt.date
        
        breakdown = []
        for date, day_trades in trades.groupby('date'):
            wins = (day_trades['outcome'] == 'WIN').sum()
            total = len(day_trades[day_trades['outcome'].notna()])
            
            breakdown.append({
                'date': str(date),
                'trades': len(day_trades),
                'wins': int(wins),
                'losses': int(total - wins),
                'win_rate': round(wins / total * 100, 1) if total > 0 else 0,
                'pnl': round(day_trades['pnl'].sum(), 2),
                'avg_score': round(day_trades['strategy_score'].mean(), 1) if day_trades['strategy_score'].notna().any() else 0
            })
        
        return sorted(breakdown, key=lambda x: x['date'])
    
    def _analyze_strategy_performance(self, trades: pd.DataFrame) -> Dict[str, Any]:
        """Analyze strategy performance over the week."""
        return self.scorer.analyze_score_effectiveness()
    
    def _analyze_psychology_trends(self, trades: pd.DataFrame) -> Dict[str, Any]:
        """Analyze psychological trends over the week."""
        behavior_history = self.db.get_behavior_history(limit=500)
        
        if behavior_history.empty:
            return {'data_available': False}
        
        # Count different event types
        event_counts = behavior_history['event_type'].value_counts().to_dict()
        
        return {
            'data_available': True,
            'event_summary': event_counts,
            'current_discipline': self.psychology.analyze_user_behavior()['discipline_score']
        }
    
    def _calculate_progress_metrics(self, trades: pd.DataFrame) -> Dict[str, Any]:
        """Calculate progress metrics compared to previous period."""
        if trades.empty:
            return {'data_available': False}
        
        # Get previous week's data
        end_date = pd.to_datetime(trades['entry_time']).min()
        start_date = end_date - timedelta(days=7)
        
        prev_trades = self.db.get_trades(limit=5000, start_date=start_date, end_date=end_date)
        
        if prev_trades.empty:
            return {
                'data_available': True,
                'comparison_available': False,
                'current_win_rate': self._analyze_performance(trades)['win_rate']
            }
        
        current_perf = self._analyze_performance(trades)
        prev_perf = self._analyze_performance(prev_trades)
        
        return {
            'data_available': True,
            'comparison_available': True,
            'win_rate_change': round(current_perf['win_rate'] - prev_perf['win_rate'], 1),
            'pnl_change': round(current_perf['total_pnl'] - prev_perf['total_pnl'], 2),
            'trade_count_change': current_perf['wins'] + current_perf['losses'] - prev_perf['wins'] - prev_perf['losses'],
            'improving': current_perf['win_rate'] > prev_perf['win_rate']
        }
    
    def _extract_key_learnings(self, trades: pd.DataFrame) -> List[str]:
        """Extract key learnings from the week."""
        learnings = []
        
        if trades.empty:
            return ["No trades to analyze. Start trading to generate insights."]
        
        # Analyze what worked
        winning_trades = trades[trades['outcome'] == 'WIN']
        if not winning_trades.empty:
            avg_winning_score = winning_trades['strategy_score'].mean()
            if pd.notna(avg_winning_score):
                learnings.append(f"Winning trades had an average score of {avg_winning_score:.1f}")
        
        # Analyze what didn't work
        losing_trades = trades[trades['outcome'] == 'LOSS']
        if not losing_trades.empty:
            avg_losing_score = losing_trades['strategy_score'].mean()
            if pd.notna(avg_losing_score):
                learnings.append(f"Losing trades had an average score of {avg_losing_score:.1f}")
        
        # Session insights
        session_perf = self._analyze_sessions(trades)
        if session_perf:
            best_session = max(session_perf.items(), key=lambda x: x[1].get('win_rate', 0))
            learnings.append(f"Best performing session: {best_session[0]} ({best_session[1]['win_rate']}% win rate)")
        
        return learnings
    
    def _generate_focus_areas(self, trades: pd.DataFrame) -> List[str]:
        """Generate focus areas for next week."""
        focus = []
        
        mistakes = self._identify_mistakes(trades)
        
        if any(m['type'] == 'LOW_SCORE_TRADES' for m in mistakes):
            focus.append("Only take trades with scores above 60")
        
        if any(m['type'] == 'IGNORED_WARNINGS' for m in mistakes):
            focus.append("Respect AI warnings and AVOID recommendations")
        
        if any(m['type'] == 'MISSING_JOURNALS' for m in mistakes):
            focus.append("Journal every trade with detailed reasoning")
        
        # Performance based focus
        perf = self._analyze_performance(trades)
        if perf['win_rate'] < 55:
            focus.append("Focus on quality over quantity - fewer, better trades")
        
        if not focus:
            focus.append("Maintain current discipline and continue learning")
        
        return focus
    
    def _save_report(self, report: Dict[str, Any], report_type: str, date: datetime) -> str:
        """Save report to file."""
        filename = f"{report_type}_{date.strftime('%Y%m%d')}.json"
        filepath = os.path.join(self.reports_path, filename)
        
        with open(filepath, 'w') as f:
            json.dump(report, f, indent=2, default=str)
        
        return filepath
    
    def get_report(self, report_type: str, date: datetime = None) -> Optional[Dict[str, Any]]:
        """Load a saved report."""
        if date is None:
            date = datetime.now()
        
        filename = f"{report_type}_{date.strftime('%Y%m%d')}.json"
        filepath = os.path.join(self.reports_path, filename)
        
        if os.path.exists(filepath):
            with open(filepath, 'r') as f:
                return json.load(f)
        
        return None
    
    def format_report_text(self, report: Dict[str, Any], report_type: str = 'daily') -> str:
        """Format report as human-readable text."""
        lines = []
        
        if report_type == 'daily':
            lines.append(f"═══════════════════════════════════════")
            lines.append(f"  DAILY TRADING SUMMARY - {report.get('date', 'N/A')}")
            lines.append(f"═══════════════════════════════════════\n")
            
            # Performance
            perf = report.get('performance', {})
            lines.append("📊 PERFORMANCE")
            lines.append(f"   Trades: {perf.get('wins', 0)}W / {perf.get('losses', 0)}L")
            lines.append(f"   Win Rate: {perf.get('win_rate', 0)}%")
            lines.append(f"   Total P&L: ${perf.get('total_pnl', 0):.2f}")
            lines.append(f"   Profit Factor: {perf.get('profit_factor', 0)}")
            lines.append("")
            
            # Psychology
            psych = report.get('psychology', {})
            discipline = psych.get('discipline_score', {})
            lines.append("🧠 PSYCHOLOGY")
            lines.append(f"   Discipline Score: {discipline.get('score', 0)}/100 ({discipline.get('grade', 'N/A')})")
            lines.append(f"   Overtrading: {'Yes ⚠️' if psych.get('overtrading_detected') else 'No ✓'}")
            lines.append(f"   Revenge Trading: {'Yes ⚠️' if psych.get('revenge_trading_detected') else 'No ✓'}")
            lines.append("")
            
            # Mistakes
            mistakes = report.get('mistakes', [])
            if mistakes:
                lines.append("❌ MISTAKES")
                for m in mistakes:
                    lines.append(f"   • {m.get('description', 'Unknown')}")
                lines.append("")
            
            # Improvements
            improvements = report.get('improvements', [])
            if improvements:
                lines.append("💡 IMPROVEMENTS")
                for imp in improvements:
                    lines.append(f"   • {imp}")
        
        return "\n".join(lines)


# Singleton instance
_report_generator = None

def get_report_generator() -> ReportGenerator:
    """Get or create report generator singleton."""
    global _report_generator
    if _report_generator is None:
        _report_generator = ReportGenerator()
    return _report_generator
