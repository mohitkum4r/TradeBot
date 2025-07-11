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
        trend_threshold=Config.TREND_THRESHOLD - 5,  # Lowered for more sensitivity
        strong_trend_threshold=Config.STRONG_TREND_THRESHOLD - 5,  # Lowered for more sensitivity
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
        min_required_length = 2 * self.adx_period  # Ensure enough data for ADX internal calculations
        if len(data) < min_required_length:
            print(f"Insufficient data for ADX calculation (need at least {min_required_length} points, have {len(data)}). Returning HOLD.")
            return "HOLD", "", "Insufficient data for regime analysis."

        # --- Regime Analysis ---
        try:
            # Use ADX on a market index (like Nifty 50) to determine trend strength
            adx_indicator = ta.trend.ADXIndicator(
                high=data["high"],
                low=data["low"],
                close=data["close"],
                window=self.adx_period,
            )
            adx_series = adx_indicator.adx()
            if adx_series.isna().all() or len(adx_series.dropna()) == 0:
                raise ValueError("ADX computation resulted in all NaN values.")
            last_adx = adx_series.dropna().iloc[-1]

            # Calculate ATR for volatility regime
            atr_indicator = ta.volatility.AverageTrueRange(
                high=data["high"], low=data["low"], close=data["close"]
            )
            atr_series = atr_indicator.average_true_range()
            if atr_series.isna().all() or len(atr_series.dropna()) == 0:
                raise ValueError("ATR computation resulted in all NaN values.")
            atr = atr_series.dropna().iloc[-1]
            high_vol = atr > data["close"].iloc[-1] * 0.015  # Lowered threshold for more high-vol detection

        except (IndexError, ValueError, KeyError) as e:
            print(f"Error during regime analysis: {e}. Returning HOLD.")
            return "HOLD", "", f"Regime analysis failed: {str(e)}"

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
            signals = []
            target_stocks = Config.STOCKS if Config.MULTI_STOCK_TRADING_ENABLED else [Config.STOCKS[0]] if Config.STOCKS else ["RELIANCE"]
            for stock in target_stocks:
                # Extract data for the stock from full_data
                if isinstance(full_data.columns, pd.MultiIndex):
                    stock_data = full_data[stock]
                else:
                    stock_data = full_data  # Fallback if not multi-index
                if len(stock_data) < max(Config.MA_SHORT_WINDOW, Config.MA_LONG_WINDOW) + 1:
                    continue  # Skip if insufficient data for this stock
                signal, reason = self.moderate_trend_strategy.generate_signal(stock_data)
                if signal != "HOLD":
                    signals.append((stock, signal, reason))
                    print(f"Generated signal for {stock}: {signal} | Reason: {reason}")
            return signals if signals else ("HOLD", "", "No moderate trend signals across stocks.")

        elif high_vol:
            print(
                f"--- Market Regime: HIGH VOLATILITY (ATR: {atr:.2f}) -> Using Volatility Breakout or RSI Divergence ---"
            )
            # Choose between breakout and divergence based on sub-conditions
            if data["volume"].iloc[-1] > data["volume"].rolling(20).mean().iloc[-1] * 1.2:  # Added multiplier for more triggers
                signal = self.vol_breakout_strategy.generate_signal(full_data)
                print(f"Generated signal from Volatility Breakout: {signal}")
                return signal
            else:
                signal = self.rsi_divergence_strategy.generate_signal(full_data)
                print(f"Generated signal from RSI Divergence: {signal}")
                return signal

        elif last_adx < self.trend_threshold:
            print(
                f"--- Market Regime: RANGE-BOUND / LOW TREND (ADX: {last_adx:.2f}) -> Using Mean Reversion or Arbitrage ---"
            )
            if len(current_portfolio) > 0:  # If holding positions, prefer reversion
                signal, reason = self.ranging_strategy.generate_signal(data)
                print(f"Generated signal from Mean Reversion: {signal} | Reason: {reason}")
                return current_portfolio[0], signal, reason  # Apply to first held stock
            else:
                signal = self.arbitrage_strategy.generate_signal(full_data)
                print(f"Generated signal from Arbitrage: {signal}")
                return signal

        else:
            print(
                f"--- Market Regime: RANGE-BOUND / LOW TREND (ADX: {last_adx:.2f}) -> Using Dynamic Pairs Trading ---"
            )
            signal = self.pairs_trading_strategy.generate_signal(full_data)
            print(f"Generated signal from Pairs Trading: {signal}")
            return signal