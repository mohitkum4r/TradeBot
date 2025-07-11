import pandas as pd
import ta
from ..config import Config
from .base_strategy import BaseStrategy
from .dual_ma_crossover_strategy import DualMaCrossoverStrategy
from .mean_reversion_strategy import MeanReversionStrategy
from .advanced_momentum_strategy import AdvancedMomentumStrategy
from .dynamic_pairs_strategy import DynamicPairsStrategy
from .volatility_breakout_strategy import VolatilityBreakoutStrategy  # Assuming this exists from original
from .rsi_divergence_strategy import RSIDivergenceStrategy  # Assuming this exists from original
from .statistical_arbitrage_strategy import StatisticalArbitrageStrategy  # Assuming this exists from original
# NEW: Imports for new strategies
from .vwap_strategy import VWAPStrategy
from .enhanced_arbitrage_strategy import EnhancedArbitrageStrategy


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

        # NEW: Additional strategies for profit maximization
        self.vwap_strategy = VWAPStrategy()
        self.enhanced_arbitrage = EnhancedArbitrageStrategy(Config.PAIRS_LIST)

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

        # MODIFIED: Volume confirmation function with NaN/None handling and stock-specific data
        def confirm_signal(signal_tuple, full_data, stock=None):
            if isinstance(signal_tuple, list):
                confirmed = []
                for s in signal_tuple:
                    stock, signal, reason = s  # Unpack for lists
                    stock_data = full_data.get(stock) if isinstance(full_data, dict) else full_data[stock] if isinstance(full_data.columns, pd.MultiIndex) and stock in full_data.columns.levels[0] else None
                    if stock_data is None or len(stock_data) < 10:  # Require min data for rolling (lowered from 20 for more signals)
                        print(f"Skipping confirmation for {stock}: Insufficient or missing data.")
                        continue  # Skip instead of HOLD to avoid blocking
                    conf_s, conf_i, conf_r = confirm_signal((signal, '', reason), stock_data, stock)  # Recursive with stock_data
                    if conf_s != "HOLD":
                        confirmed.append((stock, conf_s, conf_r))
                return confirmed if confirmed else [("HOLD", "", "All signals ignored: Low volume or data issues")]
            elif isinstance(signal_tuple, tuple):
                signal, instrument, reason = signal_tuple if len(signal_tuple) == 3 else (signal_tuple[0], "", signal_tuple[1])
                confirm_data = full_data  # Use provided full_data (stock-specific if passed)
                if "volume" not in confirm_data.columns:
                    print(f"No volume data for {stock or instrument}. Allowing signal without volume check.")
                    return signal, instrument, reason  # Allow if no volume data

                current_vol = confirm_data["volume"].iloc[-1]
                if pd.isna(current_vol):
                    print(f"Current volume is NaN for {stock or instrument}. Allowing signal.")
                    return signal, instrument, reason

                # Compute avg_vol with handling for short data
                if len(confirm_data) < 10:  # Lowered window for backtests with short data
                    avg_vol = confirm_data["volume"].mean()  # Fallback to simple mean
                else:
                    avg_vol = confirm_data["volume"].rolling(10).mean().iloc[-1]  # Lowered to 10 for more valid computations

                if pd.isna(avg_vol):
                    print(f"Avg volume is NaN for {stock or instrument}. Allowing signal to avoid data blockage.")
                    return signal, instrument, reason  # Allow signal if NaN

                if current_vol < avg_vol * Config.VOLUME_CONFIRMATION_MULTIPLIER:
                    return "HOLD", instrument, "Signal ignored: Low volume confirmation"
                return signal, instrument, reason
            return signal_tuple

        # --- Dynamic Strategy Selection ---
        full_stock_data = kwargs.get("full_stock_data", data)  # MODIFIED: Renamed for clarity, use dict or multi-index
        current_portfolio = kwargs.get("current_portfolio", [])

        if last_adx > self.strong_trend_threshold:
            print(
                f"--- Market Regime: STRONG TREND (ADX: {last_adx:.2f}) -> Using Advanced Momentum Portfolio ---"
            )
            signals = self.strong_trend_strategy.generate_signal(
                full_stock_data, current_portfolio=current_portfolio
            )
            return confirm_signal(signals, full_stock_data)

        elif last_adx > self.trend_threshold:
            print(
                f"--- Market Regime: MODERATE TREND (ADX: {last_adx:.2f}) -> Using Dual MA Crossover ---"
            )
            signals = []
            target_stocks = Config.STOCKS if Config.MULTI_STOCK_TRADING_ENABLED else [Config.STOCKS[0]] if Config.STOCKS else ["RELIANCE"]
            for stock in target_stocks:
                # Check if stock data exists in full_stock_data
                if isinstance(full_stock_data.columns, pd.MultiIndex):
                    if stock not in full_stock_data.columns.levels[0]:
                        print(f"Skipping {stock}: Data not available in full_data.")
                        continue
                    stock_data = full_stock_data[stock]
                elif isinstance(full_stock_data, dict) and stock in full_stock_data:  # NEW: Handle dict case from DataHandler
                    stock_data = full_stock_data[stock]
                else:
                    stock_data = full_stock_data  # Fallback
                if len(stock_data) < max(Config.MA_SHORT_WINDOW, Config.MA_LONG_WINDOW) + 1:
                    print(f"Skipping {stock}: Insufficient data (need at least {max(Config.MA_SHORT_WINDOW, Config.MA_LONG_WINDOW) + 1} points).")
                    continue
                signal, reason = self.moderate_trend_strategy.generate_signal(stock_data)
                if signal != "HOLD":
                    signals.append((stock, signal, reason))
                    print(f"Generated signal for {stock}: {signal} | Reason: {reason}")
            confirmed_signals = confirm_signal(signals, full_stock_data)  # Pass full_stock_data for lookup
            return confirmed_signals if confirmed_signals else ("HOLD", "", "No moderate trend signals across stocks.")

        elif high_vol:
            print(
                f"--- Market Regime: HIGH VOLATILITY (ATR: {atr:.2f}) -> Using VWAP or Volatility Breakout ---"  # MODIFIED: Prioritize new VWAP
            )
            # NEW: Choose VWAP for high-vol to maximize profits
            if data["volume"].iloc[-1] > data["volume"].rolling(20).mean().iloc[-1] * 1.2:  # Added multiplier for more triggers
                signal = self.vwap_strategy.generate_signal(full_stock_data)
            else:
                signal = self.vol_breakout_strategy.generate_signal(full_stock_data)
            return confirm_signal(signal, full_stock_data)

        elif last_adx < self.trend_threshold:
            print(
                f"--- Market Regime: RANGE-BOUND / LOW TREND (ADX: {last_adx:.2f}) -> Using Enhanced Arbitrage or Mean Reversion ---"
            )
            if len(current_portfolio) > 0:  # If holding positions, prefer reversion
                # Use first portfolio stock's data for confirmation
                first_stock = current_portfolio[0]
                stock_data = full_stock_data.get(first_stock) if isinstance(full_stock_data, dict) else full_stock_data[first_stock] if isinstance(full_stock_data.columns, pd.MultiIndex) else data
                signal, reason = self.ranging_strategy.generate_signal(stock_data)
                print(f"Generated signal from Mean Reversion: {signal} | Reason: {reason}")
                return confirm_signal((first_stock, signal, reason), stock_data)
            else:
                signal = self.enhanced_arbitrage.generate_signal(full_stock_data)
                print(f"Generated signal from Enhanced Arbitrage: {signal}")
                return confirm_signal(signal, full_stock_data)

        else:
            print(
                f"--- Market Regime: RANGE-BOUND / LOW TREND (ADX: {last_adx:.2f}) -> Using Dynamic Pairs Trading ---"
            )
            signal = self.pairs_trading_strategy.generate_signal(full_stock_data)
            print(f"Generated signal from Pairs Trading: {signal}")
            return confirm_signal(signal, full_stock_data)