# autotrade/strategies/strategy_selector.py
import pandas as pd
import ta
from ..config import Config
from .base_strategy import BaseStrategy
from .dual_ma_crossover_strategy import DualMaCrossoverStrategy
from .mean_reversion_strategy import MeanReversionStrategy
from .advanced_momentum_strategy import AdvancedMomentumStrategy
from .dynamic_pairs_strategy import DynamicPairsStrategy
from .volatility_breakout_strategy import VolatilityBreakoutStrategy  # New
from .rsi_divergence_strategy import RSIDivergenceStrategy  # New
from .statistical_arbitrage_strategy import StatisticalArbitrageStrategy  # New


class StrategySelector(BaseStrategy):
    """
    A fully autonomous, multi-layered regime filter that selects the optimal
    strategy from the entire toolkit based on market volatility and trend.
    """

    def __init__(
        self,
        adx_period=Config.ADX_PERIOD,
        trend_threshold=Config.TREND_THRESHOLD,
        strong_trend_threshold=Config.STRONG_TREND_THRESHOLD,
    ):
        self.adx_period = adx_period
        self.trend_threshold = trend_threshold
        self.strong_trend_threshold = strong_trend_threshold

        # Initialize all potential strategies
        self.strong_trend_strategy: BaseStrategy = AdvancedMomentumStrategy(
            stock_universe=Config.STOCKS
        )
        self.moderate_trend_strategy: BaseStrategy = DualMaCrossoverStrategy()
        self.pairs_trading_strategy: BaseStrategy = DynamicPairsStrategy(
            pairs_list=Config.PAIRS_LIST
        )
        self.ranging_strategy: BaseStrategy = MeanReversionStrategy()
        self.vol_breakout_strategy: BaseStrategy = VolatilityBreakoutStrategy()  # New
        self.rsi_divergence_strategy: BaseStrategy = RSIDivergenceStrategy()  # New
        self.arbitrage_strategy: BaseStrategy = StatisticalArbitrageStrategy(
            pairs_list=Config.PAIRS_LIST
        )  # New

    def generate_signal(
        self, data: pd.DataFrame, **kwargs
    ) -> tuple[str, str, str] | list[tuple[str, str, str]]:
        """
        Dynamically selects and executes the best strategy.

        Args:
            data (pd.DataFrame): DataFrame containing data for the primary instrument
                                 (e.g., Nifty 50) to determine the overall market regime.
            **kwargs: Can include 'full_stock_data' and 'current_portfolio'.
        """
        # --- Regime Analysis ---
        # Use ADX on a market index (like Nifty 50) to determine trend strength
        adx_indicator = ta.trend.ADXIndicator(
            high=data["high"],
            low=data["low"],
            close=data["close"],
            window=self.adx_period,
        )
        last_adx = adx_indicator.adx().iloc[-1]

        # Calculate ATR for volatility regime
        atr = (
            ta.volatility.AverageTrueRange(
                high=data["high"], low=data["low"], close=data["close"]
            )
            .average_true_range()
            .iloc[-1]
        )
        high_vol = (
            atr > data["close"].iloc[-1] * 0.02
        )  # Arbitrary threshold for high vol

        # --- Dynamic Strategy Selection ---
        full_data = kwargs.get("full_stock_data", data)
        current_portfolio = kwargs.get("current_portfolio", [])

        if last_adx > self.strong_trend_threshold:
            print(
                f"--- Market Regime: STRONG TREND (ADX: {last_adx:.2f}) -> Using Advanced Momentum Portfolio ---"
            )
            return self.strong_trend_strategy.generate_signal(
                full_data, current_portfolio=current_portfolio
            )

        elif last_adx > self.trend_threshold:
            print(
                f"--- Market Regime: MODERATE TREND (ADX: {last_adx:.2f}) -> Using Dual MA Crossover ---"
            )
            # This strategy generates a signal for the benchmark index itself
            signal, reason = self.moderate_trend_strategy.generate_signal(data)
            return "NIFTYBEES", signal, reason  # Example: trade Nifty ETF

        elif high_vol:
            print(
                f"--- Market Regime: HIGH VOLATILITY (ATR: {atr:.2f}) -> Using Volatility Breakout or RSI Divergence ---"
            )
            # Choose between breakout and divergence based on sub-conditions
            if data["volume"].iloc[-1] > data["volume"].rolling(20).mean().iloc[-1]:
                return self.vol_breakout_strategy.generate_signal(full_data)
            else:
                return self.rsi_divergence_strategy.generate_signal(full_data)

        elif last_adx < self.trend_threshold:
            print(
                f"--- Market Regime: RANGE-BOUND / LOW TREND (ADX: {last_adx:.2f}) -> Using Mean Reversion or Arbitrage ---"
            )
            if len(current_portfolio) > 0:  # If holding positions, prefer reversion
                signal, reason = self.ranging_strategy.generate_signal(data)
                return current_portfolio[0], signal, reason  # Apply to first held stock
            else:
                return self.arbitrage_strategy.generate_signal(full_data)

        else:
            print(
                f"--- Market Regime: RANGE-BOUND / LOW TREND (ADX: {last_adx:.2f}) -> Using Dynamic Pairs Trading ---"
            )
            return self.pairs_trading_strategy.generate_signal(full_data)
