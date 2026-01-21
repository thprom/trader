# MarketSense AI - Trading Intelligence Bot

<p align="center">
  <strong>🎯 A Learning & Trading Intelligence Bot for Educational Purposes</strong>
</p>

---

## 📌 Overview

MarketSense AI is a personal-use educational trading intelligence bot designed to help users learn digital marketing psychology, market behavior, and trading decision-making. 

**Important:** This bot does NOT promise profits, does NOT auto-trade with real money, and is designed purely for learning and simulation purposes.

### Core Objectives

- ✅ Analyze market data with technical indicators
- ✅ Simulate and evaluate trading strategies
- ✅ Learn behavioral patterns through AI
- ✅ Assist decision-making with probability-based insights
- ✅ Generate structured reports and feedback
- ✅ Develop trading discipline and emotional control

---

## 🚀 Quick Start

### Installation

```bash
# Clone or download the project
cd marketsense_ai

# Install dependencies
pip install -r requirements.txt

# Run the CLI
python cli.py

# Or run the web dashboard
streamlit run dashboard.py
```

### Basic Usage (CLI)

```bash
# Start the CLI
python cli.py

# Analyze a setup
MarketSense> analyze EUR/USD CALL

# Get AI suggestion
MarketSense> suggest EUR/USD

# Execute a simulated trade
MarketSense> trade EUR/USD CALL "Trend following setup"

# View status
MarketSense> status

# Generate report
MarketSense> report daily
```

### Basic Usage (Python)

```python
from bot import MarketSenseBot

# Initialize bot
bot = MarketSenseBot()
bot.initialize(assets=['EUR/USD', 'GBP/USD'], timeframe='5m')

# Analyze a setup
analysis = bot.analyze('EUR/USD', '5m', 'CALL')
print(f"Score: {analysis['score']['final_score']}")

# Get AI suggestion
suggestion = bot.suggest_trade('EUR/USD')
print(f"Recommendation: {suggestion['recommendation']['action']}")

# Execute trade (simulation only)
result = bot.execute('EUR/USD', 'CALL', journal="Trend following")

# Get status
status = bot.get_status()
print(f"Balance: ${status['simulation']['balance']}")
```

---

## 📊 Features

### 1. Technical Analysis Engine

Computes multiple indicators:
- **RSI** (Relative Strength Index)
- **EMA** (Fast & Slow Exponential Moving Averages)
- **MACD** (Moving Average Convergence Divergence)
- **Bollinger Bands**
- **Candle Patterns** (Hammer, Doji, Marubozu, etc.)

### 2. AI Decision Engine

- Machine learning-based probability prediction
- Random Forest / Logistic Regression models
- Feature engineering from indicators
- Continuous learning from trade outcomes

**Output Example:**
```
Trade Probability: 61%
Risk Level: Medium
Historical Sample Size: 480 trades
Recommendation: WAIT / ENTER / AVOID
```

### 3. Marketing Psychology Layer

Detects manipulation patterns:
- "Too perfect" setups (indicator over-alignment)
- Late-entry traps
- Sudden volatility spikes
- Emotional trade clustering

**Example Warning:**
> "This setup visually looks strong, but historically fails 64% of the time. Possible marketing trap."

### 4. User Psychology Model

Tracks and learns user behavior:
- Win rate by time of day
- Overtrading detection
- Performance after losses
- Strategy discipline adherence

**Example Warning:**
> "Your performance drops after 3 consecutive losses. Recommend stopping."

### 5. Strategy Scoring System

Each setup is scored (0-100):

| Factor | Weight |
|--------|--------|
| Trend Alignment | 25% |
| Momentum | 20% |
| Volatility | 15% |
| Candle Pattern | 15% |
| Session Quality | 10% |
| Psychology Risk | -15% |

**Score Interpretation:**
- 76-100: High Quality (A) - Strong setup
- 61-75: Acceptable (C) - Proceed with caution
- 41-60: Risky (D) - High risk
- 0-40: No Trade (F) - Avoid

### 6. Reporting System

- Daily summaries
- Weekly performance reviews
- Strategy rankings
- Mistake analysis
- Improvement suggestions

---

## 🎮 Operating Modes

### Mode 1: Learning & Simulation (Default)

- No real-money execution
- Simulated balance ($10,000 default)
- Trade outcomes recorded
- Strategy performance evaluated

### Mode 2: Manual-Assist

- AI suggests trades
- User confirms manually
- No automatic execution
- Full analysis available

⚠️ **Auto-trading is intentionally excluded** to avoid platform violations and encourage learning.

---

## 📁 Project Structure

```
marketsense_ai/
├── bot.py              # Main bot controller
├── cli.py              # Command-line interface
├── dashboard.py        # Streamlit web dashboard
├── config.py           # Configuration settings
├── database.py         # SQLite database handler
├── technical_analysis.py   # Technical indicators
├── ai_engine.py        # Machine learning engine
├── psychology.py       # User behavior analysis
├── strategy.py         # Strategy scoring system
├── simulation.py       # Trade simulation engine
├── reporting.py        # Report generation
├── requirements.txt    # Dependencies
├── README.md           # This file
├── data/               # Database and candle data
├── models/             # Trained AI models
├── reports/            # Generated reports
└── logs/               # Application logs
```

---

## ⚙️ Configuration

Edit `config.py` to customize:

```python
# Simulation settings
SIMULATION_CONFIG = {
    'initial_balance': 10000.0,
    'risk_per_trade': 0.02,  # 2%
    'max_daily_trades': 10,
    'max_consecutive_losses': 3
}

# Scoring weights
SCORING_WEIGHTS = {
    'trend_alignment': 0.25,
    'momentum': 0.20,
    'volatility': 0.15,
    'candle_pattern': 0.15,
    'session_quality': 0.10,
    'psychology_risk': -0.15
}
```

---

## 🛡️ Safety Rules

The bot enforces:
- ❌ No emotional overrides
- ❌ No revenge trading
- ✅ Fixed risk per trade (2%)
- ✅ Mandatory journaling (recommended)
- ✅ Pause after rule violations

---

## 📈 Success Metrics

This bot is successful if:
1. User develops discipline
2. Strategies improve statistically
3. Emotional mistakes decrease
4. Decision-making becomes data-driven

💡 **Profit is a side-effect, not the goal.**

---

## 🔧 API Reference

### MarketSenseBot

```python
# Initialize
bot.initialize(assets=['EUR/USD'], timeframe='5m')

# Analysis
bot.analyze(asset, timeframe, direction)
bot.suggest_trade(asset, timeframe)
bot.scan_markets()

# Trading
bot.execute(asset, direction, timeframe, journal)
bot.close(trade_id, exit_price)
bot.get_open_trades()

# Reports
bot.get_status()
bot.get_daily_report()
bot.get_weekly_report()
bot.get_psychology_analysis()

# AI
bot.train_ai()

# Control
bot.set_mode('simulation' | 'manual_assist')
bot.resume()
```

---

## ⚠️ Disclaimer

This software is for **educational purposes only**. It does not constitute financial advice and should not be used for real trading decisions. The developers are not responsible for any financial losses incurred from using this software.

- No signal selling
- No "guaranteed profit" claims
- No exploitation of platform weaknesses
- Educational & analytical use only

---

## 📝 License

MIT License - Feel free to use and modify for personal learning.

---

<p align="center">
  <strong>Remember: Learning and discipline come first! 📚</strong>
</p>
