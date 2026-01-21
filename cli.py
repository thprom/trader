#!/usr/bin/env python3
"""
MarketSense AI - Command Line Interface
Interactive CLI for the trading intelligence bot.
"""

import cmd
import json
from datetime import datetime
from typing import Optional
import sys

from bot import MarketSenseBot
from config import DEFAULT_ASSETS, SUPPORTED_TIMEFRAMES


class MarketSenseCLI(cmd.Cmd):
    """Interactive command-line interface for MarketSense AI."""
    
    intro = """
╔═══════════════════════════════════════════════════════════════╗
║           MarketSense AI - Trading Intelligence Bot           ║
║                                                               ║
║  🎯 Purpose: Learning, discipline, and data-driven trading    ║
║  ⚠️  Mode: Simulation (No real money)                         ║
║                                                               ║
║  Type 'help' for available commands                           ║
╚═══════════════════════════════════════════════════════════════╝
"""
    prompt = '\n📊 MarketSense> '
    
    def __init__(self):
        super().__init__()
        self.bot = MarketSenseBot()
        self._initialize_bot()
    
    def _initialize_bot(self):
        """Initialize the bot on startup."""
        print("\n🚀 Initializing MarketSense AI...")
        result = self.bot.initialize()
        
        if result['success']:
            print(f"✅ Initialized successfully!")
            print(f"   Mode: {result['mode']}")
            print(f"   Assets: {', '.join(result['assets'])}")
            print(f"   Balance: ${result['balance']:,.2f}")
        else:
            print(f"❌ Initialization failed: {result.get('error')}")
    
    def _print_json(self, data: dict, indent: int = 2):
        """Pretty print JSON data."""
        print(json.dumps(data, indent=indent, default=str))
    
    def _print_analysis(self, analysis: dict):
        """Print analysis results in a formatted way."""
        if analysis.get('error'):
            print(f"❌ Error: {analysis.get('message')}")
            return
        
        print("\n" + "="*60)
        print(f"  ANALYSIS: {analysis['asset']} ({analysis['timeframe']})")
        print("="*60)
        
        # Score
        score = analysis['score']
        print(f"\n📊 SCORE: {score['final_score']:.1f}/100 - {score['grade']}")
        print(f"   {score['recommendation']}")
        
        # AI Prediction
        ai = analysis['ai_prediction']
        print(f"\n🤖 AI PREDICTION:")
        print(f"   Probability: {ai.get('probability', 0):.1f}%")
        print(f"   Risk Level: {ai.get('risk_level', 'N/A')}")
        print(f"   Recommendation: {ai.get('recommendation', 'N/A')}")
        
        # Signals
        signals = analysis['signals']
        bias = signals.get('overall_bias', {})
        print(f"\n📈 SIGNALS:")
        print(f"   Overall Bias: {bias.get('direction', 'N/A')} ({bias.get('confidence', 0)*100:.0f}% confidence)")
        print(f"   RSI: {signals.get('rsi', {}).get('value', 0):.1f} ({signals.get('rsi', {}).get('signal', 'N/A')})")
        print(f"   EMA: {signals.get('ema', {}).get('signal', 'N/A')}")
        print(f"   MACD: {signals.get('macd', {}).get('trend', 'N/A')}")
        
        # Trap Analysis
        trap = analysis['trap_analysis']
        if trap.get('traps_detected'):
            print(f"\n⚠️  TRAP WARNING: {trap['assessment']}")
            print(f"   {trap['recommendation']}")
        
        # Can trade
        can_trade, reason = analysis['can_trade']
        print(f"\n{'✅' if can_trade else '❌'} Can Trade: {reason}")
        
        print("="*60)
    
    # ==================== COMMANDS ====================
    
    def do_status(self, arg):
        """Show current bot status and account information."""
        status = self.bot.get_status()
        
        print("\n" + "="*60)
        print("                    BOT STATUS")
        print("="*60)
        
        sim = status['simulation']
        print(f"\n💰 ACCOUNT:")
        print(f"   Balance: ${sim['balance']:,.2f}")
        print(f"   P&L: ${sim['pnl']:,.2f} ({sim['pnl_percent']:+.1f}%)")
        print(f"   Open Trades: {sim['open_trades']}")
        print(f"   Total Trades: {sim['total_trades']}")
        
        print(f"\n⚙️  SETTINGS:")
        print(f"   Mode: {status['mode']}")
        print(f"   Assets: {', '.join(status['preferred_assets'])}")
        print(f"   Timeframe: {status['preferred_timeframe']}")
        print(f"   Session: {sim['current_session']}")
        
        psych = status['psychology']
        print(f"\n🧠 PSYCHOLOGY:")
        print(f"   Discipline: {psych['discipline_score']['score']:.0f}/100 ({psych['discipline_score']['grade']})")
        print(f"   Emotional State: {psych['emotional_state']['state']}")
        
        if psych['warnings']:
            print(f"\n⚠️  WARNINGS:")
            for w in psych['warnings']:
                print(f"   {w}")
        
        if sim['is_paused']:
            print(f"\n🛑 TRADING PAUSED: {sim['pause_reason']}")
        
        print("="*60)
    
    def do_analyze(self, arg):
        """
        Analyze a trading setup.
        Usage: analyze [asset] [direction]
        Example: analyze EUR/USD CALL
        """
        args = arg.split()
        
        asset = args[0] if args else self.bot.preferred_assets[0]
        direction = args[1].upper() if len(args) > 1 else None
        
        print(f"\n🔍 Analyzing {asset}...")
        analysis = self.bot.analyze(asset, self.bot.preferred_timeframe, direction)
        self._print_analysis(analysis)
    
    def do_suggest(self, arg):
        """
        Get AI trade suggestion.
        Usage: suggest [asset]
        Example: suggest EUR/USD
        """
        asset = arg.strip() if arg else self.bot.preferred_assets[0]
        
        print(f"\n🤖 Getting suggestion for {asset}...")
        suggestion = self.bot.suggest_trade(asset)
        
        if suggestion.get('error'):
            print(f"❌ Error: {suggestion.get('message')}")
            return
        
        print("\n" + "="*60)
        print(f"  AI SUGGESTION: {suggestion['asset']}")
        print("="*60)
        
        rec = suggestion['recommendation']
        print(f"\n📌 ACTION: {rec['action']}")
        print(f"   Confidence: {rec['confidence']}")
        print(f"   {rec['message']}")
        
        if suggestion['suggested_direction']:
            print(f"\n➡️  Suggested Direction: {suggestion['suggested_direction']}")
        
        print(f"\n📊 Score: {suggestion['score']['final_score']:.1f}")
        print(f"🎯 Probability: {suggestion['ai_prediction'].get('probability', 0):.1f}%")
        print("="*60)
    
    def do_trade(self, arg):
        """
        Execute a simulated trade.
        Usage: trade <asset> <CALL|PUT> [journal entry]
        Example: trade EUR/USD CALL "Trend following setup"
        """
        if not arg:
            print("❌ Usage: trade <asset> <CALL|PUT> [journal]")
            return
        
        parts = arg.split('"')
        main_args = parts[0].strip().split()
        journal = parts[1] if len(parts) > 1 else None
        
        if len(main_args) < 2:
            print("❌ Usage: trade <asset> <CALL|PUT> [journal]")
            return
        
        asset = main_args[0]
        direction = main_args[1].upper()
        
        if direction not in ['CALL', 'PUT']:
            print("❌ Direction must be CALL or PUT")
            return
        
        print(f"\n📝 Executing trade: {asset} {direction}...")
        result = self.bot.execute(asset, direction, journal=journal)
        
        if result['success']:
            print(f"\n✅ Trade Executed!")
            print(f"   Trade ID: {result['trade_id']}")
            print(f"   Entry: {result['entry_price']:.5f}")
            print(f"   Size: ${result['position_size']:.2f}")
            print(f"   Score: {result['score']:.1f}")
            
            if result.get('warnings'):
                print("\n⚠️  Warnings:")
                for w in result['warnings']:
                    print(f"   {w}")
        else:
            print(f"\n❌ Trade Failed: {result.get('message')}")
    
    def do_close(self, arg):
        """
        Close an open trade.
        Usage: close <trade_id> [exit_price]
        Example: close 1 1.1050
        """
        args = arg.split()
        
        if not args:
            print("❌ Usage: close <trade_id> [exit_price]")
            return
        
        try:
            trade_id = int(args[0])
            exit_price = float(args[1]) if len(args) > 1 else None
        except ValueError:
            print("❌ Invalid trade ID or price")
            return
        
        result = self.bot.close(trade_id, exit_price)
        
        if result['success']:
            outcome_emoji = "🟢" if result['outcome'] == 'WIN' else "🔴"
            print(f"\n{outcome_emoji} Trade #{trade_id} Closed!")
            print(f"   Exit: {result['exit_price']:.5f}")
            print(f"   P&L: ${result['pnl']:+.2f}")
            print(f"   Outcome: {result['outcome']}")
            print(f"   New Balance: ${result['new_balance']:,.2f}")
        else:
            print(f"\n❌ Failed: {result.get('message')}")
    
    def do_open(self, arg):
        """Show all open trades."""
        trades = self.bot.get_open_trades()
        
        if not trades:
            print("\n📭 No open trades")
            return
        
        print("\n" + "="*60)
        print("                    OPEN TRADES")
        print("="*60)
        
        for trade in trades:
            print(f"\n📌 Trade #{trade['id']}")
            print(f"   Asset: {trade['asset']} {trade['direction']}")
            print(f"   Entry: {trade['entry_price']:.5f}")
            print(f"   Amount: ${trade['amount']:.2f}")
            print(f"   Score: {trade.get('strategy_score', 'N/A')}")
        
        print("="*60)
    
    def do_scan(self, arg):
        """Scan all preferred assets for trading opportunities."""
        print("\n🔍 Scanning markets...")
        opportunities = self.bot.scan_markets()
        
        if not opportunities:
            print("\n📭 No opportunities found")
            return
        
        print("\n" + "="*60)
        print("                 MARKET OPPORTUNITIES")
        print("="*60)
        
        for opp in opportunities:
            score_emoji = "🟢" if opp['score'] >= 70 else "🟡" if opp['score'] >= 50 else "🔴"
            print(f"\n{score_emoji} {opp['asset']}")
            print(f"   Score: {opp['score']:.1f}")
            print(f"   Direction: {opp['direction']}")
            print(f"   Probability: {opp['probability']:.1f}%")
            print(f"   AI: {opp['ai_recommendation']}")
        
        print("="*60)
    
    def do_report(self, arg):
        """
        Generate performance report.
        Usage: report [daily|weekly]
        """
        report_type = arg.strip().lower() if arg else 'daily'
        
        if report_type not in ['daily', 'weekly']:
            print("❌ Usage: report [daily|weekly]")
            return
        
        print(f"\n📊 Generating {report_type} report...")
        
        report_text = self.bot.get_report_text(report_type)
        print(report_text)
    
    def do_psychology(self, arg):
        """Show detailed psychology analysis."""
        print("\n🧠 Analyzing psychology...")
        analysis = self.bot.get_psychology_analysis()
        
        print("\n" + "="*60)
        print("                 PSYCHOLOGY ANALYSIS")
        print("="*60)
        
        # Discipline
        discipline = analysis['discipline_score']
        print(f"\n📊 DISCIPLINE SCORE: {discipline['score']:.0f}/100 ({discipline['grade']})")
        for factor, value in discipline['factors'].items():
            print(f"   {factor}: {value:.0f}")
        
        # Overtrading
        ot = analysis['overtrading']
        print(f"\n⏱️  OVERTRADING:")
        print(f"   Trades last hour: {ot['trades_last_hour']}")
        print(f"   Daily trades: {ot['daily_trades']}/{ot['max_daily_trades']}")
        print(f"   Status: {'⚠️ OVERTRADING' if ot['is_overtrading'] else '✅ OK'}")
        
        # Revenge trading
        rt = analysis['revenge_trading']
        print(f"\n😤 REVENGE TRADING:")
        print(f"   Detected: {'⚠️ YES' if rt['detected'] else '✅ NO'}")
        if rt['detected']:
            print(f"   Instances: {rt['instances']}")
        
        # Emotional state
        es = analysis.get('emotional_clusters', {})
        print(f"\n💭 EMOTIONAL CLUSTERS:")
        print(f"   Detected: {'⚠️ YES' if es.get('detected') else '✅ NO'}")
        
        # Warnings
        if analysis['warnings']:
            print(f"\n⚠️  WARNINGS:")
            for w in analysis['warnings']:
                print(f"   {w}")
        
        # Recommendations
        if analysis['recommendations']:
            print(f"\n💡 RECOMMENDATIONS:")
            for r in analysis['recommendations']:
                print(f"   {r}")
        
        print("="*60)
    
    def do_train(self, arg):
        """Train or retrain the AI model."""
        print("\n🧠 Training AI model...")
        result = self.bot.train_ai()
        
        if result['success']:
            metrics = result['metrics']
            print(f"\n✅ Model trained successfully!")
            print(f"   Accuracy: {metrics['accuracy']*100:.1f}%")
            print(f"   Precision: {metrics['precision']*100:.1f}%")
            print(f"   Recall: {metrics['recall']*100:.1f}%")
            print(f"   F1 Score: {metrics['f1_score']*100:.1f}%")
            print(f"   Training samples: {metrics['training_samples']}")
        else:
            print(f"\n❌ Training failed: {result.get('message')}")
    
    def do_resume(self, arg):
        """Resume trading after pause."""
        result = self.bot.resume()
        
        if result['success']:
            print(f"\n✅ {result['message']}")
            if result.get('previous_pause_reason'):
                print(f"   Previous reason: {result['previous_pause_reason']}")
        else:
            print(f"\n❌ {result.get('message')}")
    
    def do_mode(self, arg):
        """
        Change operating mode.
        Usage: mode <simulation|manual_assist>
        """
        if not arg:
            print(f"\n📌 Current mode: {self.bot.mode}")
            print("   Use: mode <simulation|manual_assist>")
            return
        
        mode = arg.strip().lower()
        if mode == 'manual_assist':
            mode = 'manual_assist'
        
        result = self.bot.set_mode(mode)
        
        if result['success']:
            print(f"\n✅ Mode changed to: {result['mode']}")
        else:
            print(f"\n❌ {result.get('error')}")
    
    def do_assets(self, arg):
        """
        Set preferred assets.
        Usage: assets <asset1> <asset2> ...
        Example: assets EUR/USD GBP/USD
        """
        if not arg:
            print(f"\n📌 Current assets: {', '.join(self.bot.preferred_assets)}")
            print(f"\n   Available: {', '.join(DEFAULT_ASSETS)}")
            return
        
        assets = arg.upper().split()
        valid_assets = [a for a in assets if a in DEFAULT_ASSETS]
        
        if valid_assets:
            self.bot.preferred_assets = valid_assets
            print(f"\n✅ Assets set to: {', '.join(valid_assets)}")
        else:
            print(f"\n❌ No valid assets. Available: {', '.join(DEFAULT_ASSETS)}")
    
    def do_timeframe(self, arg):
        """
        Set preferred timeframe.
        Usage: timeframe <1m|5m|15m>
        """
        if not arg:
            print(f"\n📌 Current timeframe: {self.bot.preferred_timeframe}")
            return
        
        tf = arg.strip().lower()
        
        if tf in SUPPORTED_TIMEFRAMES:
            self.bot.preferred_timeframe = tf
            print(f"\n✅ Timeframe set to: {tf}")
        else:
            print(f"\n❌ Invalid timeframe. Use: {', '.join(SUPPORTED_TIMEFRAMES)}")
    
    def do_help(self, arg):
        """Show help for commands."""
        if arg:
            # Show help for specific command
            super().do_help(arg)
        else:
            print("""
╔═══════════════════════════════════════════════════════════════╗
║                    AVAILABLE COMMANDS                          ║
╠═══════════════════════════════════════════════════════════════╣
║  ANALYSIS                                                      ║
║    analyze [asset] [direction] - Analyze a trading setup       ║
║    suggest [asset]             - Get AI trade suggestion       ║
║    scan                        - Scan markets for opportunities║
║                                                                ║
║  TRADING                                                       ║
║    trade <asset> <CALL|PUT>    - Execute a simulated trade     ║
║    close <trade_id> [price]    - Close an open trade           ║
║    open                        - Show open trades              ║
║                                                                ║
║  REPORTS                                                       ║
║    status                      - Show bot status               ║
║    report [daily|weekly]       - Generate performance report   ║
║    psychology                  - Show psychology analysis      ║
║                                                                ║
║  AI                                                            ║
║    train                       - Train/retrain AI model        ║
║                                                                ║
║  SETTINGS                                                      ║
║    mode [simulation|manual]    - Change operating mode         ║
║    assets [asset1 asset2...]   - Set preferred assets          ║
║    timeframe [1m|5m|15m]       - Set preferred timeframe       ║
║    resume                      - Resume trading after pause    ║
║                                                                ║
║  OTHER                                                         ║
║    help [command]              - Show help                     ║
║    quit                        - Exit the program              ║
╚═══════════════════════════════════════════════════════════════╝
""")
    
    def do_quit(self, arg):
        """Exit the program."""
        print("\n👋 Goodbye! Remember: Learning and discipline come first!")
        return True
    
    def do_exit(self, arg):
        """Exit the program."""
        return self.do_quit(arg)
    
    def default(self, line):
        """Handle unknown commands."""
        print(f"❌ Unknown command: {line}")
        print("   Type 'help' for available commands")
    
    def emptyline(self):
        """Do nothing on empty line."""
        pass


def main():
    """Main entry point for CLI."""
    try:
        cli = MarketSenseCLI()
        cli.cmdloop()
    except KeyboardInterrupt:
        print("\n\n👋 Goodbye!")
        sys.exit(0)


if __name__ == '__main__':
    main()
