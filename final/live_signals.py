#!/usr/bin/env python3
"""
MarketSense AI - Live Trading Signals
Real-time trading signal generator for Pocket Option and other platforms.
"""

import os
import sys
import time
from datetime import datetime
from typing import Optional, List

# Add project path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from live_data import get_signal_generator, get_live_data_fetcher


def clear_screen():
    """Clear terminal screen."""
    os.system('cls' if os.name == 'nt' else 'clear')


def print_header():
    """Print the header."""
    print("\n" + "="*70)
    print("            🎯 MARKETSENSE AI - LIVE TRADING SIGNALS 🎯")
    print("="*70)
    print(f"  Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("  Platform: Pocket Option / Any Binary Options Platform")
    print("  Mode: REAL-TIME ANALYSIS")
    print("="*70)


def print_signal(signal: dict, detailed: bool = True):
    """Print a trading signal in a clear format."""
    action = signal['signal']
    direction = signal.get('direction', '')
    asset = signal['asset']
    price = signal['price']
    score = signal['score']
    probability = signal['probability']
    confidence = signal['confidence']
    
    # Color codes for terminal
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    RESET = '\033[0m'
    BOLD = '\033[1m'
    
    # Determine action color
    if action == 'BUY':
        action_color = GREEN
        action_emoji = "🟢"
        action_text = f"BUY (CALL)"
    elif action == 'SELL':
        action_color = RED
        action_emoji = "🔴"
        action_text = f"SELL (PUT)"
    elif action == 'WAIT':
        action_color = YELLOW
        action_emoji = "🟡"
        action_text = "WAIT"
    else:
        action_color = RED
        action_emoji = "⛔"
        action_text = "DO NOT TRADE"
    
    print(f"\n{BOLD}{'─'*60}{RESET}")
    print(f"{BOLD}  ASSET: {BLUE}{asset}{RESET}")
    print(f"{'─'*60}")
    
    # Main signal
    print(f"\n  {action_emoji} {BOLD}{action_color}SIGNAL: {action_text}{RESET}")
    print(f"  📊 Current Price: {price}")
    print(f"  🎯 Score: {score:.0f}/100")
    print(f"  📈 Probability: {probability:.0f}%")
    print(f"  💪 Confidence: {confidence}")
    print(f"  ⏰ Session: {signal.get('session', 'N/A')}")
    
    # Reasons
    if detailed and signal.get('reasons'):
        print(f"\n  {BOLD}📋 REASONS:{RESET}")
        for reason in signal['reasons'][:6]:
            print(f"     {reason}")
    
    # Warnings
    if signal.get('warnings'):
        print(f"\n  {BOLD}{YELLOW}⚠️ WARNINGS:{RESET}")
        for warning in signal['warnings']:
            print(f"     {warning}")
    
    print(f"\n{'─'*60}")


def print_opportunity_summary(opportunities: List[dict]):
    """Print a summary of best opportunities."""
    if not opportunities:
        print("\n  📭 No strong trading opportunities found right now.")
        print("     Wait for better setups or try different assets.")
        return
    
    print(f"\n  🏆 TOP {len(opportunities)} OPPORTUNITIES:")
    print(f"  {'─'*50}")
    
    for i, opp in enumerate(opportunities[:5], 1):
        action = opp['signal']
        direction = opp.get('direction', '')
        
        if action == 'BUY':
            emoji = "🟢"
            dir_text = "CALL"
        else:
            emoji = "🔴"
            dir_text = "PUT"
        
        print(f"  {i}. {emoji} {opp['asset']:12} | {dir_text:4} | Score: {opp['score']:.0f} | Prob: {opp['probability']:.0f}%")


def get_single_signal(asset: str = 'EUR/USD', timeframe: str = '5m'):
    """Get and display a single signal."""
    print(f"\n  🔍 Analyzing {asset} on {timeframe} timeframe...")
    
    generator = get_signal_generator()
    signal = generator.generate_signal(asset, timeframe)
    
    print_signal(signal)
    
    return signal


def scan_markets(timeframe: str = '5m'):
    """Scan all markets for opportunities."""
    print(f"\n  🔍 Scanning all markets on {timeframe} timeframe...")
    print("     This may take a moment...")
    
    generator = get_signal_generator()
    opportunities = generator.get_best_opportunities(timeframe, min_score=55)
    
    print_opportunity_summary(opportunities)
    
    return opportunities


def live_monitor(assets: List[str], timeframe: str = '5m', interval: int = 60):
    """
    Continuously monitor assets and display signals.
    
    Args:
        assets: List of assets to monitor
        timeframe: Candle timeframe
        interval: Refresh interval in seconds
    """
    generator = get_signal_generator()
    
    print(f"\n  📡 Starting live monitor...")
    print(f"     Assets: {', '.join(assets)}")
    print(f"     Timeframe: {timeframe}")
    print(f"     Refresh: Every {interval} seconds")
    print(f"\n     Press Ctrl+C to stop\n")
    
    try:
        while True:
            clear_screen()
            print_header()
            
            print(f"\n  📡 LIVE MONITORING ({len(assets)} assets)")
            print(f"  Last update: {datetime.now().strftime('%H:%M:%S')}")
            
            for asset in assets:
                try:
                    signal = generator.generate_signal(asset, timeframe)
                    print_signal(signal, detailed=False)
                except Exception as e:
                    print(f"\n  ❌ Error analyzing {asset}: {e}")
            
            print(f"\n  ⏳ Next update in {interval} seconds...")
            print("     Press Ctrl+C to stop")
            
            time.sleep(interval)
            
    except KeyboardInterrupt:
        print("\n\n  👋 Monitor stopped. Goodbye!")


def interactive_mode():
    """Interactive CLI mode."""
    generator = get_signal_generator()
    data_fetcher = get_live_data_fetcher()
    
    available_assets = data_fetcher.get_available_assets()
    
    while True:
        clear_screen()
        print_header()
        
        print(f"\n  📌 AVAILABLE COMMANDS:")
        print(f"  {'─'*50}")
        print(f"  1. Analyze single asset")
        print(f"  2. Scan all markets")
        print(f"  3. Start live monitor")
        print(f"  4. Show market status")
        print(f"  5. List available assets")
        print(f"  6. Exit")
        print(f"  {'─'*50}")
        
        choice = input("\n  Enter choice (1-6): ").strip()
        
        if choice == '1':
            print(f"\n  Available assets: {', '.join(available_assets[:10])}...")
            asset = input("  Enter asset (e.g., EUR/USD): ").strip().upper()
            if '/' not in asset and asset in ['GOLD', 'SILVER', 'OIL']:
                pass  # Keep as is
            elif '/' not in asset:
                asset = asset[:3] + '/' + asset[3:] if len(asset) == 6 else asset
            
            timeframe = input("  Enter timeframe (1m/5m/15m) [5m]: ").strip() or '5m'
            
            get_single_signal(asset, timeframe)
            input("\n  Press Enter to continue...")
            
        elif choice == '2':
            timeframe = input("  Enter timeframe (1m/5m/15m) [5m]: ").strip() or '5m'
            scan_markets(timeframe)
            input("\n  Press Enter to continue...")
            
        elif choice == '3':
            print(f"\n  Enter assets to monitor (comma-separated)")
            print(f"  Example: EUR/USD, GBP/USD, BTC/USD")
            assets_input = input("  Assets [EUR/USD, GBP/USD]: ").strip()
            
            if assets_input:
                assets = [a.strip().upper() for a in assets_input.split(',')]
            else:
                assets = ['EUR/USD', 'GBP/USD']
            
            timeframe = input("  Timeframe (1m/5m/15m) [5m]: ").strip() or '5m'
            interval = input("  Refresh interval in seconds [60]: ").strip()
            interval = int(interval) if interval else 60
            
            live_monitor(assets, timeframe, interval)
            
        elif choice == '4':
            status = data_fetcher.get_market_status()
            print(f"\n  📊 MARKET STATUS")
            print(f"  {'─'*50}")
            print(f"  Current Session: {status['current_session']}")
            print(f"  Forex Open: {'✅ Yes' if status['forex_open'] else '❌ No (Weekend)'}")
            print(f"  Crypto Open: {'✅ Yes' if status['crypto_open'] else '❌ No'}")
            print(f"\n  Sessions:")
            for session, info in status['sessions'].items():
                active = "🟢 ACTIVE" if info['active'] else "⚪ Inactive"
                print(f"    {session}: {active} ({info['hours']})")
            input("\n  Press Enter to continue...")
            
        elif choice == '5':
            print(f"\n  📋 AVAILABLE ASSETS:")
            print(f"  {'─'*50}")
            
            # Group by type
            forex = [a for a in available_assets if '/' in a and 'USD' in a and 'BTC' not in a]
            crypto = [a for a in available_assets if 'BTC' in a or 'ETH' in a or 'XRP' in a or 'LTC' in a or 'DOGE' in a]
            commodities = [a for a in available_assets if a in ['GOLD', 'SILVER', 'OIL']]
            indices = [a for a in available_assets if 'US' in a and '/' not in a]
            
            print(f"\n  Forex: {', '.join(forex)}")
            print(f"\n  Crypto: {', '.join(crypto)}")
            print(f"\n  Commodities: {', '.join(commodities)}")
            print(f"\n  Indices: {', '.join(indices)}")
            
            input("\n  Press Enter to continue...")
            
        elif choice == '6':
            print("\n  👋 Goodbye! Trade wisely!")
            break
        
        else:
            print("\n  ❌ Invalid choice. Please try again.")
            time.sleep(1)


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description='MarketSense AI - Live Trading Signals')
    parser.add_argument('--asset', '-a', type=str, default='EUR/USD',
                        help='Asset to analyze (e.g., EUR/USD)')
    parser.add_argument('--timeframe', '-t', type=str, default='5m',
                        help='Timeframe (1m, 5m, 15m)')
    parser.add_argument('--scan', '-s', action='store_true',
                        help='Scan all markets')
    parser.add_argument('--monitor', '-m', action='store_true',
                        help='Start live monitor')
    parser.add_argument('--interval', '-i', type=int, default=60,
                        help='Monitor refresh interval (seconds)')
    parser.add_argument('--interactive', action='store_true',
                        help='Start interactive mode')
    
    args = parser.parse_args()
    
    print_header()
    
    if args.interactive or len(sys.argv) == 1:
        interactive_mode()
    elif args.scan:
        scan_markets(args.timeframe)
    elif args.monitor:
        assets = [args.asset]
        live_monitor(assets, args.timeframe, args.interval)
    else:
        get_single_signal(args.asset, args.timeframe)


if __name__ == '__main__':
    main()
