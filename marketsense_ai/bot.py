"""
MarketSense AI - Main Bot Controller
Central controller for the trading intelligence bot.
"""

import pandas as pd
import numpy as np
from typing import Dict, Any, Optional, List
from datetime import datetime
import json
import os

import config
from database import get_database
from technical_analysis import get_ta_engine
from ai_engine import get_ai_engine
from psychology import get_psychology_analyzer, get_trap_detector
from strategy import get_strategy_manager, get_strategy_scorer
from simulation import get_simulation_engine
from reporting import get_report_generator


class MarketSenseBot:
    """Main controller for MarketSense AI trading bot."""
    
    def __init__(self):
        self.db = get_database()
        self.ta_engine = get_ta_engine()
        self.ai_engine = get_ai_engine()
        self.psychology = get_psychology_analyzer()
        self.trap_detector = get_trap_detector()
        self.strategy_manager = get_strategy_manager()
        self.strategy_scorer = get_strategy_scorer()
        self.simulation = get_simulation_engine()
        self.reporter = get_report_generator()
        
        self.mode = 'simulation'  # 'simulation' or 'manual_assist'
        self.preferred_assets = []
        self.preferred_timeframe = config.DEFAULT_TIMEFRAME
        self.is_initialized = False
    
    def initialize(self, assets: List[str] = None, 
                   timeframe: str = None) -> Dict[str, Any]:
        """Initialize the bot with user preferences."""
        # Set preferences
        self.preferred_assets = assets or config.DEFAULT_ASSETS[:3]
        self.preferred_timeframe = timeframe or config.DEFAULT_TIMEFRAME
        
        # Ensure directories exist
        config.ensure_directories()
        
        # Initialize database
        self.db._init_database()
        
        # Generate sample data if no data exists
        for asset in self.preferred_assets:
            candles = self.db.get_candles(asset, self.preferred_timeframe, limit=10)
            if candles.empty:
                print(f"Generating sample data for {asset}...")
                self.simulation.generate_sample_data(asset, self.preferred_timeframe, 500)
        
        self.is_initialized = True
        
        # Log initialization
        self.db.log_behavior('bot_initialized', json.dumps({
            'assets': self.preferred_assets,
            'timeframe': self.preferred_timeframe,
            'mode': self.mode
        }))
        
        return {
            'success': True,
            'message': 'MarketSense AI initialized successfully',
            'mode': self.mode,
            'assets': self.preferred_assets,
            'timeframe': self.preferred_timeframe,
            'balance': self.simulation.get_current_balance()
        }
    
    def set_mode(self, mode: str) -> Dict[str, Any]:
        """Set operating mode."""
        if mode not in ['simulation', 'manual_assist']:
            return {
                'success': False,
                'error': f"Invalid mode: {mode}. Use 'simulation' or 'manual_assist'"
            }
        
        self.mode = mode
        self.db.log_behavior('mode_changed', json.dumps({'new_mode': mode}))
        
        return {
            'success': True,
            'mode': mode,
            'message': f"Mode set to {mode}"
        }
    
    def analyze(self, asset: str = None, timeframe: str = None,
                direction: str = None) -> Dict[str, Any]:
        """Analyze a trading setup."""
        asset = asset or (self.preferred_assets[0] if self.preferred_assets else 'EUR/USD')
        timeframe = timeframe or self.preferred_timeframe
        
        return self.simulation.analyze_setup(asset, timeframe, direction)
    
    def suggest_trade(self, asset: str = None, timeframe: str = None) -> Dict[str, Any]:
        """Get AI trade suggestion."""
        analysis = self.analyze(asset, timeframe)
        
        if analysis.get('error'):
            return analysis
        
        # Determine suggested direction
        bias = analysis['signals'].get('overall_bias', {})
        direction = bias.get('direction', 'NEUTRAL')
        
        if direction == 'BULLISH':
            suggested_direction = 'CALL'
        elif direction == 'BEARISH':
            suggested_direction = 'PUT'
        else:
            suggested_direction = None
        
        # Get AI prediction for suggested direction
        if suggested_direction:
            ai_prediction = self.ai_engine.predict_trade(analysis['signals'], suggested_direction)
        else:
            ai_prediction = analysis['ai_prediction']
        
        return {
            'asset': analysis['asset'],
            'timeframe': analysis['timeframe'],
            'suggested_direction': suggested_direction,
            'score': analysis['score'],
            'ai_prediction': ai_prediction,
            'trap_analysis': analysis['trap_analysis'],
            'signals': analysis['signals'],
            'recommendation': self._generate_recommendation(analysis, suggested_direction)
        }
    
    def _generate_recommendation(self, analysis: Dict[str, Any], 
                                  direction: str) -> Dict[str, Any]:
        """Generate comprehensive trade recommendation."""
        score = analysis['score']['final_score']
        ai_rec = analysis['ai_prediction'].get('recommendation', 'WAIT')
        trap_risk = analysis['trap_analysis'].get('overall_risk_score', 0)
        
        # Determine action
        if score >= 70 and ai_rec == 'ENTER' and trap_risk < 25:
            action = 'ENTER'
            confidence = 'HIGH'
            message = "Strong setup with good probability. Consider entering."
        elif score >= 60 and ai_rec != 'AVOID' and trap_risk < 50:
            action = 'WAIT'
            confidence = 'MEDIUM'
            message = "Acceptable setup. Wait for confirmation or better entry."
        else:
            action = 'AVOID'
            confidence = 'LOW'
            message = "Setup does not meet criteria. Skip this trade."
        
        return {
            'action': action,
            'confidence': confidence,
            'message': message,
            'factors': {
                'score': score,
                'ai_recommendation': ai_rec,
                'trap_risk': trap_risk
            }
        }
    
    def execute(self, asset: str, direction: str, timeframe: str = None,
                journal: str = None) -> Dict[str, Any]:
        """Execute a trade (simulation mode)."""
        if self.mode != 'simulation':
            return {
                'success': False,
                'error': 'AUTO_TRADE_DISABLED',
                'message': 'Automatic execution only available in simulation mode. Use manual_assist mode for suggestions only.'
            }
        
        timeframe = timeframe or self.preferred_timeframe
        
        return self.simulation.execute_trade(asset, timeframe, direction, journal)
    
    def close(self, trade_id: int, exit_price: float = None) -> Dict[str, Any]:
        """Close an open trade."""
        return self.simulation.close_trade(trade_id, exit_price)
    
    def get_status(self) -> Dict[str, Any]:
        """Get comprehensive bot status."""
        sim_status = self.simulation.get_simulation_status()
        psychology = self.psychology.analyze_user_behavior()
        emotional_state = self.psychology.get_current_emotional_state()
        
        # Check if baseline report is due
        trade_count = self.db.get_trade_count()
        baseline_due = trade_count >= config.SIMULATION_CONFIG['min_trades_for_baseline']
        
        return {
            'initialized': self.is_initialized,
            'mode': self.mode,
            'preferred_assets': self.preferred_assets,
            'preferred_timeframe': self.preferred_timeframe,
            'simulation': sim_status,
            'psychology': {
                'discipline_score': psychology['discipline_score'],
                'emotional_state': emotional_state,
                'warnings': psychology['warnings'][:3]  # Top 3 warnings
            },
            'ai_model': self.ai_engine.get_model_status(),
            'baseline_report_due': baseline_due and trade_count < 60,
            'trade_count': trade_count
        }
    
    def get_daily_report(self) -> Dict[str, Any]:
        """Generate and return daily report."""
        return self.reporter.generate_daily_summary()
    
    def get_weekly_report(self) -> Dict[str, Any]:
        """Generate and return weekly report."""
        return self.reporter.generate_weekly_review()
    
    def get_report_text(self, report_type: str = 'daily') -> str:
        """Get formatted report text."""
        if report_type == 'daily':
            report = self.get_daily_report()
        else:
            report = self.get_weekly_report()
        
        return self.reporter.format_report_text(report, report_type)
    
    def train_ai(self) -> Dict[str, Any]:
        """Train or retrain the AI model."""
        return self.ai_engine.train_model()
    
    def get_psychology_analysis(self) -> Dict[str, Any]:
        """Get detailed psychology analysis."""
        return self.psychology.analyze_user_behavior()
    
    def get_strategy_rankings(self) -> List[Dict[str, Any]]:
        """Get strategy performance rankings."""
        return self.strategy_manager.get_strategy_rankings()
    
    def import_data(self, filepath: str, asset: str, 
                    timeframe: str) -> Dict[str, Any]:
        """Import candle data from CSV file."""
        try:
            df = pd.read_csv(filepath)
            return self.simulation.import_candle_data(df, asset, timeframe)
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    def resume(self) -> Dict[str, Any]:
        """Resume trading after pause."""
        return self.simulation.resume_trading()
    
    def get_open_trades(self) -> List[Dict[str, Any]]:
        """Get list of open trades."""
        trades = self.simulation.get_open_trades()
        if trades.empty:
            return []
        return trades.to_dict('records')
    
    def scan_markets(self) -> List[Dict[str, Any]]:
        """Scan all preferred assets for opportunities."""
        opportunities = []
        
        for asset in self.preferred_assets:
            analysis = self.analyze(asset, self.preferred_timeframe)
            
            if analysis.get('error'):
                continue
            
            score = analysis['score']['final_score']
            ai_rec = analysis['ai_prediction'].get('recommendation', 'WAIT')
            
            if score >= 60 or ai_rec == 'ENTER':
                opportunities.append({
                    'asset': asset,
                    'score': score,
                    'ai_recommendation': ai_rec,
                    'direction': analysis['signals'].get('overall_bias', {}).get('direction'),
                    'probability': analysis['ai_prediction'].get('probability')
                })
        
        # Sort by score
        opportunities.sort(key=lambda x: x['score'], reverse=True)
        
        return opportunities
    
    def journal_trade(self, trade_id: int, entry: str) -> Dict[str, Any]:
        """Add or update journal entry for a trade."""
        success = self.db.update_trade(trade_id, {'journal_entry': entry})
        
        return {
            'success': success,
            'trade_id': trade_id,
            'message': 'Journal entry updated' if success else 'Failed to update journal'
        }
    
    def get_help(self) -> str:
        """Get help text for using the bot."""
        return """
═══════════════════════════════════════════════════════════════
                    MarketSense AI - Help Guide
═══════════════════════════════════════════════════════════════

🎯 PURPOSE
MarketSense AI is a learning and trading intelligence bot designed
to help you develop discipline, analyze markets, and make data-driven
decisions. It does NOT promise profits and is for educational use.

📋 MAIN COMMANDS

  bot.initialize(assets, timeframe)
    - Initialize bot with preferred assets and timeframe
    - Example: bot.initialize(['EUR/USD', 'GBP/USD'], '5m')

  bot.analyze(asset, timeframe, direction)
    - Analyze a trading setup
    - Example: bot.analyze('EUR/USD', '5m', 'CALL')

  bot.suggest_trade(asset, timeframe)
    - Get AI trade suggestion
    - Example: bot.suggest_trade('EUR/USD')

  bot.execute(asset, direction, timeframe, journal)
    - Execute a simulated trade
    - Example: bot.execute('EUR/USD', 'CALL', '5m', 'Trend following setup')

  bot.close(trade_id, exit_price)
    - Close an open trade
    - Example: bot.close(1, 1.1050)

  bot.get_status()
    - Get comprehensive bot status

  bot.get_daily_report()
    - Generate daily trading summary

  bot.get_weekly_report()
    - Generate weekly performance review

  bot.scan_markets()
    - Scan all assets for opportunities

  bot.train_ai()
    - Train/retrain the AI model

  bot.get_psychology_analysis()
    - Get detailed psychology analysis

  bot.resume()
    - Resume trading after pause

🎮 OPERATING MODES

  Simulation Mode (Default):
    - No real money
    - Trades are simulated
    - Full AI assistance

  Manual-Assist Mode:
    - AI provides suggestions only
    - User makes all decisions
    - No automatic execution

📊 SCORING SYSTEM

  76-100: High Quality (A) - Strong setup
  61-75:  Acceptable (C)   - Proceed with caution
  41-60:  Risky (D)        - High risk
  0-40:   No Trade (F)     - Avoid

⚠️ SAFETY RULES

  - Maximum 10 trades per day
  - Pause after 3 consecutive losses
  - 2% risk per trade
  - Journal entries recommended
  - AI warnings should be respected

💡 TIPS FOR SUCCESS

  1. Start in Simulation Mode
  2. Focus on high-quality setups (score > 70)
  3. Always journal your trades
  4. Review daily and weekly reports
  5. Learn from mistakes
  6. Develop discipline before profits

═══════════════════════════════════════════════════════════════
        Remember: Learning and discipline come first!
═══════════════════════════════════════════════════════════════
"""


# Create global bot instance
bot = MarketSenseBot()


def main():
    """Main entry point for the bot."""
    print("\n" + "="*60)
    print("       MarketSense AI - Trading Intelligence Bot")
    print("="*60)
    print("\n🚀 Starting MarketSense AI...\n")
    
    # Initialize with default settings
    result = bot.initialize()
    
    if result['success']:
        print(f"✅ {result['message']}")
        print(f"   Mode: {result['mode']}")
        print(f"   Assets: {', '.join(result['assets'])}")
        print(f"   Timeframe: {result['timeframe']}")
        print(f"   Balance: ${result['balance']:,.2f}")
        print("\n" + "-"*60)
        print("📖 Type 'bot.get_help()' for usage instructions")
        print("-"*60 + "\n")
    else:
        print(f"❌ Initialization failed: {result.get('error')}")
    
    return bot


if __name__ == '__main__':
    main()
