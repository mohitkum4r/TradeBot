# 🤖 TradeBot - Automated Trading System for Groww

An advanced, production-ready automated trading system that integrates with the Groww API to execute systematic trading strategies on Indian stock markets (NSE/BSE).

[![Python Version](https://img.shields.io/badge/python-3.12-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

## ⚠️ Important Disclaimer

**This software is for educational and research purposes only. Trading in financial markets involves substantial risk of loss. The authors and contributors are not responsible for any financial losses incurred through the use of this software.**

- Always test thoroughly in PAPER mode before considering live trading
- Start with small amounts and low risk parameters
- Understand SEBI regulations for algorithmic trading in India
- Never invest more than you can afford to lose
- Past performance does not guarantee future results

## ✨ Features

### Trading Capabilities
- **14 Built-in Trading Strategies**: Momentum, Mean Reversion, Pairs Trading, Statistical Arbitrage, ML-based predictions, and more
- **Dual Execution Modes**: Paper trading (simulation) and Live trading with real money
- **Comprehensive Risk Management**: Position sizing, stop loss, take profit, exposure limits
- **Multi-Stock Trading**: Trade multiple stocks simultaneously with dynamic selection

### Analysis & Intelligence
- **Backtesting Framework**: Test strategies on historical data before deployment
- **Sentiment Analysis**: Reddit + Ollama LLM integration for market sentiment
- **Machine Learning**: Scikit-learn based predictions for enhanced decision making
- **Technical Indicators**: ADX, RSI, MACD, Bollinger Bands, VWAP, and more
- **Stock Screening**: Dynamic stock selection based on momentum and volume

### Infrastructure
- **Clean Architecture**: Separation of concerns with Domain, Infrastructure, and Use Cases layers
- **Dependency Injection**: Modular design for easy testing and maintenance
- **Database Persistence**: SQLAlchemy ORM with support for SQLite, PostgreSQL, MySQL
- **Tax Calculator**: Accurate calculation of Indian market taxes (STT, GST, SEBI charges)
- **Robust Error Handling**: Retry mechanisms and graceful failure handling

## 📋 Prerequisites

- Python 3.12 or higher
- Poetry (for dependency management)
- Groww account with API access
- (Optional) Reddit API credentials for sentiment analysis
- (Optional) Ollama installed for LLM-based sentiment analysis

## 🚀 Quick Start

### 1. Clone the Repository

```bash
git clone https://github.com/mohitkum4r/TradeBot.git
cd TradeBot
```

### 2. Install Dependencies

```bash
# Install Poetry if not already installed
pip install poetry

# Install project dependencies
poetry install --no-root
```

### 3. Configure Environment

```bash
# Copy the example environment file
cp .env.example .env

# Edit .env with your credentials
nano .env  # or use your preferred editor
```

**Minimum required configuration**:
```bash
GROWW_ACCESS_TOKEN=your_token_here
MODE=PAPER
INITIAL_CAPITAL=100000.0
```

### 4. Run the Bot

```bash
# Activate the poetry shell
poetry shell

# Run in paper trading mode (safe for testing)
python main.py
```

## 📖 Configuration

Key configuration parameters in `.env`:

| Parameter | Description | Default | Recommended Range |
|-----------|-------------|---------|-------------------|
| `MODE` | Trading mode (PAPER/LIVE) | PAPER | PAPER for testing |
| `INITIAL_CAPITAL` | Starting capital in INR | 100000 | 50000-500000 |
| `MAX_EXPOSURE_PER_TRADE` | Max % of capital per trade | 0.2 | 0.1-0.3 |
| `RISK_PER_TRADE` | Risk as % of capital | 0.01 | 0.005-0.02 |
| `STOP_LOSS_PCT` | Stop loss percentage | 0.05 | 0.03-0.10 |
| `TAKE_PROFIT_PCT` | Take profit percentage | 0.10 | 0.05-0.20 |

See [.env.example](.env.example) for all available options.

## 🧪 Testing

### Paper Trading (Recommended)
Always test in paper mode first:

```bash
# In .env
MODE=PAPER
python main.py
```

### Backtesting
Test strategies on historical data:

```bash
# In .env
BACKTEST=True
BACKTEST_START_DATE=01-01-2024
BACKTEST_END_DATE=31-03-2024
python main.py
```

## 📚 Documentation

- [**CODE_REVIEW_REPORT.md**](CODE_REVIEW_REPORT.md) - Comprehensive code quality analysis and recommendations
- [GEMINI.md](GEMINI.md) - AI assistant project context
- [.env.example](.env.example) - Complete configuration reference

## 🔒 Security

1. Never commit `.env` file (already in `.gitignore`)
2. Rotate API keys regularly
3. Test in PAPER mode extensively before live trading
4. Monitor logs for suspicious activity
5. Keep backups of your database

## 🐛 Troubleshooting

**Authentication Failed**: Check your `GROWW_ACCESS_TOKEN` in `.env`  
**No Data**: Verify market hours and internet connection  
**Import Errors**: Run `poetry install --no-root`

See [CODE_REVIEW_REPORT.md](CODE_REVIEW_REPORT.md) for detailed troubleshooting.

## 🤝 Contributing

Contributions welcome! Please:
1. Fork the repository
2. Create a feature branch
3. Follow code style guidelines (`bash run_checks.sh`)
4. Submit a pull request

## 📝 License

MIT License - See LICENSE file for details

## ⚖️ Legal

- Comply with SEBI regulations for algorithmic trading
- Review Groww's API terms of service
- Maintain proper tax records
- Understand and accept trading risks

## 📞 Support

- **Issues**: [GitHub Issues](https://github.com/mohitkum4r/TradeBot/issues)
- **Email**: mo.kum4r@gmail.com

---

**Version**: 0.3.0  
**Last Updated**: November 2025

**⚠️ IMPORTANT**: This is a complex trading system. Read [CODE_REVIEW_REPORT.md](CODE_REVIEW_REPORT.md) for complete understanding before use.
