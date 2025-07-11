import pandas as pd
import ta
from ..config import Config
from .base_strategy import BaseStrategy
from .dual_ma_crossover_strategy import DualMaCrossoverStrategy
from .mean_reversion_strategy import MeanReversionStrategy
from .advanced_momentum_strategy import AdvancedMomentumStrategy
from .dynamic_pairs_strategy import DynamicPairsStrategy
from .volatility_breakout_strategy import VolatilityBreakoutStrategy
from .rsi_divergence_strategy import RsiDivergenceStrategy


class StrategySelector(BaseStrategy):
    """
    A fully autonomous, multi-layered regime filter that selects the optimal
    strategy from the entire toolkit based on market volatility and trend.
    """

    def __init__(
        self,
        adx_period=14,
        trend_threshold=25,
        strong_trend_threshold=40,
        bb_window=20,
        volatility_threshold=0.04, # Example: 4% BB Width
    ):
        self.adx_period = adx_period
        self.trend_threshold = trend_threshold
        self.strong_trend_threshold = strong_trend_threshold
        self.bb_window = bb_window
        self.volatility_threshold = volatility_threshold

        # Initialize all potential strategies
        self.strong_trend_strategy: BaseStrategy = AdvancedMomentumStrategy(
            stock_universe=Config.STOCKS
        )
        self.moderate_trend_strategy: BaseStrategy = DualMaCrossoverStrategy()
        self.ranging_strategy: BaseStrategy = MeanReversionStrategy()
        self.pairs_trading_strategy: BaseStrategy = DynamicPairsStrategy(
            pairs_list=Config.PAIRS_LIST
        )
        self.volatility_breakout_strategy: BaseStrategy = VolatilityBreakoutStrategy()
        self.reversal_strategy: BaseStrategy = RsiDivergenceStrategy()


    def generate_signal(
        self, data: pd.DataFrame, **kwargs
    ) -> tuple[str, str, str] | list[tuple[str, str, str]]:
        """
        Dynamically selects and executes the best strategy based on market regime.

        Args:
            data (pd.DataFrame): DataFrame for the primary instrument (e.g., Nifty 50)
                                 to determine the overall market regime.
            **kwargs: Can include 'full_stock_data' and 'current_portfolio'.
        """
        # --- Regime Analysis ---
        # 1. Trend Strength Analysis using ADX
        adx_indicator = ta.trend.ADXIndicator(
            high=data["high"],
            low=data["low"],
            close=data["close"],
            window=self.adx_period,
        )
        last_adx = adx_indicator.adx().iloc[-1]

        # 2. Volatility Analysis using Bollinger Band Width
        bb = ta.volatility.BollingerBands(close=data["close"], window=self.bb_window)
        bb_width = ((bb.bollinger_hband() - bb.bollinger_lband()) / bb.bollinger_mavg()).iloc[-1]


        # --- Dynamic Strategy Selection ---
        print(f"--- Market Regime Analysis: ADX={last_adx:.2f}, BB-Width={bb_width:.3f} ---")

        # High Volatility -> Volatility Breakout
        if bb_width > self.volatility_threshold:
            print("Regime: HIGH VOLATILITY -> Using Volatility Breakout Strategy")
            # This strategy generates a signal for the benchmark index ETF
            signal, reason = self.volatility_breakout_strategy.generate_signal(data)
            return "NIFTYBEES", signal, reason

        # Strong Trend -> Advanced Momentum
        elif last_adx > self.strong_trend_threshold:
            print(f"Regime: STRONG TREND -> Using Advanced Momentum Portfolio")
            full_data = kwargs.get("full_stock_data", data)
            current_portfolio = kwargs.get("current_portfolio", [])
            return self.strong_trend_strategy.generate_signal(
                full_data, current_portfolio=current_portfolio
            )

        # Moderate Trend -> Dual MA Crossover
        elif last_adx > self.trend_threshold:
            print(f"Regime: MODERATE TREND -> Using Dual MA Crossover Strategy")
            # This strategy generates a signal for the benchmark index ETF
            signal, reason = self.moderate_trend_strategy.generate_signal(data)
            return "NIFTYBEES", signal, reason

        # Low Trend / Ranging Market -> Mean Reversion & Pairs Trading
        else: # ADX < trend_threshold
            print(f"Regime: RANGE-BOUND / LOW TREND -> Evaluating Pairs & Reversal Strategies")
            # Attempt to find a pairs trade first, as it's market-neutral
            full_data = kwargs.get("full_stock_data", data)
            pairs_signal, instrument, reason = self.pairs_trading_strategy.generate_signal(full_data)
            if pairs_signal != "HOLD":
                print("-> Found valid Pairs Trade opportunity.")
                return instrument, pairs_signal, reason

            # If no pairs trade, look for a classic mean reversion or divergence signal on the index
            reversal_signal, reversal_reason = self.reversal_strategy.generate_signal(data)
            if reversal_signal != "HOLD":
                 print("-> Found RSI Divergence opportunity on Index.")
                 return "NIFTYBEES", reversal_signal, reversal_reason

            print("-> Defaulting to Mean Reversion on Index.")
            mean_rev_signal, mean_rev_reason = self.ranging_strategy.generate_signal(data)
            return "NIFTYBEES", mean_rev_signal, mean_rev_reason