#!/usr/bin/env python3
"""
Test script to verify bot is working and fetching real market data
"""
import sys
import os
sys.path.insert(0, r'd:\Projects\Trader')

# Test 1: Check if yfinance is installed
print("=" * 60)
print("TEST 1: Checking yfinance installation...")
print("=" * 60)
try:
    import yfinance as yf
    print("✓ yfinance is installed and working")
except ImportError as e:
    print(f"✗ yfinance not installed: {e}")
    print("Installing yfinance...")
    os.system("pip install yfinance -q")
    import yfinance as yf
    print("✓ yfinance installed")

# Test 2: Fetch real market data for EUR/USD
print("\n" + "=" * 60)
print("TEST 2: Fetching live EUR/USD data from Yahoo Finance...")
print("=" * 60)
try:
    ticker = yf.Ticker('EURUSD=X')
    df = ticker.history(period='5d', interval='5m')
    
    if df.empty:
        print("✗ No data returned from Yahoo Finance")
    else:
        print(f"✓ Successfully fetched {len(df)} candles")
        print(f"  Latest close price: {df['Close'].iloc[-1]:.5f}")
        print(f"  High: {df['High'].max():.5f}")
        print(f"  Low: {df['Low'].min():.5f}")
except Exception as e:
    print(f"✗ Error fetching data: {e}")

# Test 3: Initialize bot components
print("\n" + "=" * 60)
print("TEST 3: Initializing bot components...")
print("=" * 60)
try:
    from live_data import LiveDataFetcher, LiveSignalGenerator
    print("✓ Imported data fetcher")
    
    fetcher = LiveDataFetcher()
    print("✓ Created data fetcher instance")
    
    generator = LiveSignalGenerator()
    print("✓ Created signal generator instance")
except Exception as e:
    print(f"✗ Error initializing components: {e}")
    sys.exit(1)

# Test 4: Generate actual trading signal
print("\n" + "=" * 60)
print("TEST 4: Generating trading signal for EUR/USD...")
print("=" * 60)
try:
    signal = generator.generate_signal('EUR/USD', '5m')
    
    print(f"\n{'Asset:':<20} {signal.get('asset', 'N/A')}")
    print(f"{'Signal:':<20} {signal.get('signal', 'N/A')}")
    print(f"{'Price:':<20} {signal.get('price', 'N/A')}")
    print(f"{'Score:':<20} {signal.get('score', 'N/A'):.0f}/100")
    print(f"{'Probability:':<20} {signal.get('probability', 'N/A'):.0f}%")
    print(f"{'Confidence:':<20} {signal.get('confidence', 'N/A')}")
    print(f"{'Risk Level:':<20} {signal.get('risk_level', 'N/A')}")
    print(f"{'Session:':<20} {signal.get('session', 'N/A')}")
    
    if signal['signal'] in ['BUY', 'SELL']:
        print(f"\n✓ BOT IS WORKING - Generated {signal['signal']} signal!")
        print(f"  Direction: {signal.get('direction', 'N/A')}")
    elif signal['signal'] == 'NO_DATA':
        print(f"\n✗ NO DATA returned - API not working")
        print(f"  Message: {signal.get('message', 'N/A')}")
    else:
        print(f"\n⚠ Signal is {signal['signal']} (awaiting better setup)")
    
    print("\nReasons:")
    for reason in signal.get('reasons', []):
        print(f"  • {reason}")
    
    if signal.get('warnings'):
        print("\nWarnings:")
        for warning in signal.get('warnings', []):
            print(f"  ⚠️ {warning}")
            
except Exception as e:
    print(f"✗ Error generating signal: {e}")
    import traceback
    traceback.print_exc()

# Test 5: Scan multiple assets
print("\n" + "=" * 60)
print("TEST 5: Scanning BTC/USD for signal...")
print("=" * 60)
try:
    signal_btc = generator.generate_signal('BTC/USD', '5m')
    print(f"BTC/USD: {signal_btc.get('signal')} @ {signal_btc.get('price')} (Score: {signal_btc.get('score', 0):.0f})")
except Exception as e:
    print(f"✗ Error: {e}")

print("\n" + "=" * 60)
print("SUMMARY")
print("=" * 60)
print("If you see BUY/SELL signals above, your bot is working correctly!")
print("If you see NO_DATA, check your internet connection.")
print("=" * 60)
