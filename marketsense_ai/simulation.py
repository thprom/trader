"""
MarketSense AI - Trading Simulation Engine
Handles simulated trading, position management, and trade execution.
"""

import pandas as pd
import numpy as np
from typing import Dict, Any, Optional, Tuple, List
from datetime import datetime, timedelta
import json
import random

import config
from database import get_database
from technical_analysis import get_ta_engine
from ai_engine import get_ai_engine
from psychology import get_psychology_analyzer, get_trap_detector
from strategy import get_strategy_manager


class SimulationEngine:
    """Handles simulated trading operations."""
    
    def __init__(self):
        self.db = get_database()
        self.ta_engine = get_ta_engine()
        self.ai_engine = get_ai_engine()
        self.psychology = get_psychology_analyzer()
        self.trap_detector = get_trap_detector()
        self.strategy_manager = get_strategy_manager()
        
        self.config = config.SIMULATION_CONFIG
        self.is_paused = False
        self.pause_reason = ""
        self.current_session = None
        
        # Initialize balance if needed
        self._initialize_balance()
    
    def _initialize_balance(self):
        """Initialize simulation balance if not exists."""
        current_balance = self.db.get_current_balance()
        if current_balance == self.config['initial_balance']:
            # Check if this is first time
            balance_history = self.db.get_balance_history(limit=1)
            if balance_history.empty:
                self.db.update_balance(
                    self.config['initial_balance'],
                    0,
                    "Initial simulation balance"
                )
    
    def get_current_balance(self) -> float:
        """Get current simulation balance."""
        return self.db.get_current_balance()
    
    def calculate_position_size(self, balance: float = None) -> float:
        """Calculate position size based on risk management."""
        if balance is None:
            balance = self.get_current_balance()
        
        risk_per_trade = self.config['risk_per_trade']
        return round(balance * risk_per_trade, 2)
    
    def can_trade(self) -> Tuple[bool, str]:
        """Check if trading is allowed based on rules."""
        # Check if paused
        if self.is_paused:
            return False, self.pause_reason
        
        # Check psychology
        should_pause, reason = self.psychology.should_pause_trading()
        if should_pause:
            self.is_paused = True
            self.pause_reason = reason
            self.db.log_violation('TRADING_PAUSED', reason)
            return False, reason
        
        # Check daily trade limit
        today_trades = self.db.get_trades(limit=100)
        if not today_trades.empty:
            today_trades['entry_time'] = pd.to_datetime(today_trades['entry_time'])
            today = datetime.now().date()
            daily_count = len(today_trades[today_trades['entry_time'].dt.date == today])
            
            if daily_count >= self.config['max_daily_trades']:
                return False, f"Daily trade limit ({self.config['max_daily_trades']}) reached"
        
        # Check drawdown
        balance = self.get_current_balance()
        initial = self.config['initial_balance']
        drawdown = (initial - balance) / initial * 100
        
        if drawdown >= self.config.get('max_drawdown_percent', 10):
            return False, f"Maximum drawdown ({drawdown:.1f}%) reached"
        
        return True, "Trading allowed"
    
    def analyze_setup(self, asset: str, timeframe: str, 
                      direction: str = None) -> Dict[str, Any]:
        """Analyze a potential trade setup."""
        # Get candle data
        df = self.db.get_candles(asset, timeframe, limit=200)
        
        if df.empty or len(df) < 50:
            return {
                'error': True,
                'message': f"Insufficient data for {asset} {timeframe}. Need at least 50 candles."
            }
        
        # Calculate indicators
        df = self.ta_engine.calculate_all_indicators(df)
        
        # Get current signals
        signals = self.ta_engine.get_current_signals(df)
        
        # Get volatility and trend
        volatility = self.ta_engine.calculate_volatility(df)
        trend = self.ta_engine.get_trend_strength(df)
        
        # Determine session
        session = self._get_current_session()
        
        # Get strategy evaluation
        evaluation = self.strategy_manager.evaluate_setup(signals, df, session, direction)
        
        # Get AI prediction
        ai_prediction = self.ai_engine.predict_trade(signals, direction)
        
        # Check for traps
        trap_analysis = self.trap_detector.analyze_setup(signals, df)
        
        return {
            'error': False,
            'asset': asset,
            'timeframe': timeframe,
            'direction': direction,
            'timestamp': datetime.now().isoformat(),
            'price': signals.get('price', 0),
            'signals': signals,
            'volatility': volatility,
            'trend': trend,
            'session': session,
            'score': evaluation['score'],
            'ai_prediction': ai_prediction,
            'trap_analysis': trap_analysis,
            'can_trade': self.can_trade()
        }
    
    def execute_trade(self, asset: str, timeframe: str, direction: str,
                      journal_entry: str = None, force: bool = False) -> Dict[str, Any]:
        """Execute a simulated trade."""
        # Check if trading is allowed
        can_trade, reason = self.can_trade()
        if not can_trade and not force:
            return {
                'success': False,
                'error': 'TRADING_BLOCKED',
                'message': reason
            }
        
        # Analyze setup
        analysis = self.analyze_setup(asset, timeframe, direction)
        
        if analysis.get('error'):
            return {
                'success': False,
                'error': 'ANALYSIS_FAILED',
                'message': analysis.get('message')
            }
        
        # Check score threshold
        score = analysis['score']['final_score']
        ai_rec = analysis['ai_prediction'].get('recommendation', 'WAIT')
        
        # Warn but allow if score is low
        warnings = []
        if score < 40:
            warnings.append(f"Low score ({score}). Consider skipping this trade.")
            self.db.log_violation('LOW_SCORE_TRADE', f"Took trade with score {score}")
        
        if ai_rec == 'AVOID':
            warnings.append("AI recommends AVOID. Potential trap detected.")
            self.db.log_violation('IGNORED_AI_WARNING', f"Took trade despite AVOID recommendation")
        
        # Check journal requirement
        if config.EXECUTION_RULES['require_journal_entry'] and not journal_entry:
            warnings.append("Journal entry recommended for trade tracking.")
        
        # Calculate position size
        balance = self.get_current_balance()
        position_size = self.calculate_position_size(balance)
        
        # Get entry price
        entry_price = analysis['price']
        
        # Create trade record
        trade_data = {
            'asset': asset,
            'timeframe': timeframe,
            'direction': direction,
            'entry_price': entry_price,
            'entry_time': datetime.now(),
            'amount': position_size,
            'mode': 'simulation',
            'strategy_score': score,
            'ai_probability': analysis['ai_prediction'].get('probability'),
            'ai_recommendation': ai_rec,
            'indicators_snapshot': json.dumps(analysis['signals'], default=str),
            'journal_entry': journal_entry,
            'session': analysis['session']
        }
        
        trade_id = self.db.insert_trade(trade_data)
        
        # Log behavior
        self.db.log_behavior('trade_opened', json.dumps({
            'trade_id': trade_id,
            'asset': asset,
            'direction': direction,
            'score': score
        }))
        
        return {
            'success': True,
            'trade_id': trade_id,
            'entry_price': entry_price,
            'position_size': position_size,
            'score': score,
            'ai_recommendation': ai_rec,
            'warnings': warnings,
            'analysis': analysis
        }
    
    def close_trade(self, trade_id: int, exit_price: float = None,
                    outcome: str = None) -> Dict[str, Any]:
        """Close an open trade."""
        trades = self.db.get_trades(limit=1000)
        trade = trades[trades['id'] == trade_id]
        
        if trade.empty:
            return {
                'success': False,
                'error': 'TRADE_NOT_FOUND',
                'message': f"Trade {trade_id} not found"
            }
        
        trade = trade.iloc[0]
        
        if trade['exit_time'] is not None:
            return {
                'success': False,
                'error': 'TRADE_ALREADY_CLOSED',
                'message': f"Trade {trade_id} is already closed"
            }
        
        # If no exit price provided, simulate one
        if exit_price is None:
            exit_price = self._simulate_exit_price(trade)
        
        # Calculate P&L
        entry_price = trade['entry_price']
        direction = trade['direction']
        amount = trade['amount']
        
        if direction == 'CALL':
            pnl = (exit_price - entry_price) / entry_price * amount
        else:  # PUT
            pnl = (entry_price - exit_price) / entry_price * amount
        
        # Determine outcome if not provided
        if outcome is None:
            outcome = 'WIN' if pnl > 0 else 'LOSS'
        
        # Update trade
        update_data = {
            'exit_price': exit_price,
            'exit_time': datetime.now(),
            'pnl': round(pnl, 2),
            'outcome': outcome
        }
        
        self.db.update_trade(trade_id, update_data)
        
        # Update balance
        new_balance = self.get_current_balance() + pnl
        self.db.update_balance(new_balance, pnl, f"Trade {trade_id} closed: {outcome}")
        
        # Log behavior
        self.db.log_behavior('trade_closed', json.dumps({
            'trade_id': trade_id,
            'outcome': outcome,
            'pnl': round(pnl, 2)
        }))
        
        # Check for consecutive losses
        self._check_consecutive_losses()
        
        return {
            'success': True,
            'trade_id': trade_id,
            'exit_price': exit_price,
            'pnl': round(pnl, 2),
            'outcome': outcome,
            'new_balance': round(new_balance, 2)
        }
    
    def _simulate_exit_price(self, trade: pd.Series) -> float:
        """Simulate an exit price based on market conditions."""
        entry_price = trade['entry_price']
        score = trade['strategy_score'] or 50
        
        # Higher score = higher probability of favorable exit
        win_probability = min(0.8, max(0.3, score / 100))
        
        # Add some randomness
        is_win = random.random() < win_probability
        
        # Calculate price movement (0.1% to 1% typical for short-term)
        movement_pct = random.uniform(0.001, 0.01)
        
        if trade['direction'] == 'CALL':
            if is_win:
                exit_price = entry_price * (1 + movement_pct)
            else:
                exit_price = entry_price * (1 - movement_pct)
        else:  # PUT
            if is_win:
                exit_price = entry_price * (1 - movement_pct)
            else:
                exit_price = entry_price * (1 + movement_pct)
        
        return round(exit_price, 5)
    
    def _check_consecutive_losses(self):
        """Check for consecutive losses and pause if needed."""
        recent_trades = self.db.get_trades(limit=self.config['max_consecutive_losses'])
        
        if recent_trades.empty:
            return
        
        outcomes = recent_trades['outcome'].tolist()
        
        if all(o == 'LOSS' for o in outcomes[:self.config['max_consecutive_losses']]):
            self.is_paused = True
            self.pause_reason = f"Maximum consecutive losses ({self.config['max_consecutive_losses']}) reached. Take a break."
            self.db.log_violation('CONSECUTIVE_LOSSES', self.pause_reason)
    
    def _get_current_session(self) -> str:
        """Get current trading session."""
        hour = datetime.now().hour
        
        for session_name, times in config.TRADING_SESSIONS.items():
            start = int(times['start'].split(':')[0])
            end = int(times['end'].split(':')[0])
            
            if start <= hour < end:
                return session_name
        
        return 'OFF_HOURS'
    
    def resume_trading(self) -> Dict[str, Any]:
        """Resume trading after pause."""
        if not self.is_paused:
            return {
                'success': True,
                'message': "Trading was not paused"
            }
        
        self.is_paused = False
        previous_reason = self.pause_reason
        self.pause_reason = ""
        
        self.db.log_behavior('trading_resumed', json.dumps({
            'previous_pause_reason': previous_reason
        }))
        
        return {
            'success': True,
            'message': "Trading resumed",
            'previous_pause_reason': previous_reason
        }
    
    def get_open_trades(self) -> pd.DataFrame:
        """Get all open trades."""
        trades = self.db.get_trades(limit=100)
        
        if trades.empty:
            return pd.DataFrame()
        
        return trades[trades['exit_time'].isna()]
    
    def get_simulation_status(self) -> Dict[str, Any]:
        """Get current simulation status."""
        balance = self.get_current_balance()
        initial = self.config['initial_balance']
        
        # Calculate stats
        stats = self.db.get_performance_stats(days=30)
        
        return {
            'balance': round(balance, 2),
            'initial_balance': initial,
            'pnl': round(balance - initial, 2),
            'pnl_percent': round((balance - initial) / initial * 100, 2),
            'is_paused': self.is_paused,
            'pause_reason': self.pause_reason,
            'current_session': self._get_current_session(),
            'can_trade': self.can_trade(),
            'stats': stats,
            'open_trades': len(self.get_open_trades()),
            'total_trades': self.db.get_trade_count()
        }
    
    def import_candle_data(self, df: pd.DataFrame, asset: str, 
                           timeframe: str) -> Dict[str, Any]:
        """Import candle data from DataFrame."""
        required_columns = ['timestamp', 'open', 'high', 'low', 'close']
        
        for col in required_columns:
            if col not in df.columns:
                return {
                    'success': False,
                    'error': f"Missing required column: {col}"
                }
        
        # Add session information
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df['session'] = df['timestamp'].dt.hour.apply(
            lambda h: self._get_session_for_hour(h)
        )
        
        # Insert into database
        count = self.db.insert_candles_bulk(df, asset, timeframe)
        
        return {
            'success': True,
            'imported': count,
            'asset': asset,
            'timeframe': timeframe
        }
    
    def _get_session_for_hour(self, hour: int) -> str:
        """Get session name for a given hour."""
        for session_name, times in config.TRADING_SESSIONS.items():
            start = int(times['start'].split(':')[0])
            end = int(times['end'].split(':')[0])
            
            if start <= hour < end:
                return session_name
        
        return 'OFF_HOURS'
    
    def generate_sample_data(self, asset: str, timeframe: str, 
                             num_candles: int = 500) -> Dict[str, Any]:
        """Generate sample candle data for testing."""
        base_price = 1.1000 if 'EUR' in asset else 100.0
        
        timestamps = pd.date_range(
            end=datetime.now(),
            periods=num_candles,
            freq='5min' if timeframe == '5m' else '1min' if timeframe == '1m' else '15min'
        )
        
        prices = [base_price]
        for _ in range(num_candles - 1):
            change = random.gauss(0, 0.0005)  # Small random changes
            prices.append(prices[-1] * (1 + change))
        
        data = []
        for i, ts in enumerate(timestamps):
            price = prices[i]
            volatility = random.uniform(0.0001, 0.0005)
            
            open_price = price
            close_price = price * (1 + random.gauss(0, volatility))
            high_price = max(open_price, close_price) * (1 + random.uniform(0, volatility))
            low_price = min(open_price, close_price) * (1 - random.uniform(0, volatility))
            
            data.append({
                'timestamp': ts,
                'open': round(open_price, 5),
                'high': round(high_price, 5),
                'low': round(low_price, 5),
                'close': round(close_price, 5),
                'volume': random.randint(100, 10000)
            })
        
        df = pd.DataFrame(data)
        result = self.import_candle_data(df, asset, timeframe)
        
        return {
            'success': result['success'],
            'generated': num_candles,
            'asset': asset,
            'timeframe': timeframe,
            'imported': result.get('imported', 0)
        }


# Singleton instance
_simulation_engine = None

def get_simulation_engine() -> SimulationEngine:
    """Get or create simulation engine singleton."""
    global _simulation_engine
    if _simulation_engine is None:
        _simulation_engine = SimulationEngine()
    return _simulation_engine
