# domain/strategies/strategy_selector.py
import pandas as pd
import ta.trend
import ta.volatility
import logging
from typing import List, Tuple, Dict, Any
from app.config import Config
from .base_strategy import BaseStrategy
from .advanced_momentum_strategy import AdvancedMomentumStrategy
from .dual_ma_crossover_strategy import DualMaCrossoverStrategy
from .mean_reversion_strategy import MeanReversionStrategy
from .dynamic_pairs_strategy import DynamicPairsStrategy
from .volatility_breakout_strategy import VolatilityBreakoutStrategy
from .rsi_divergence_strategy import RSIDivergenceStrategy
from .statistical_arbitrage_strategy import StatisticalArbitrageStrategy
from .vwap_strategy import VWAPStrategy
from .enhanced_arbitrage_strategy import EnhancedArbitrageStrategy

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")


class StrategySelector(BaseStrategy):
    def __init__(
            self,
            adx_period=Config.ADX_PERIOD,
            trend_threshold=Config.TREND_THRESHOLD - 5,
            strong_trend_threshold=Config.STRONG_TREND_THRESHOLD - 5,
    ):
        self.adx_period = adx_period
        self.trend_threshold = trend_threshold
        self.strong_trend_threshold = strong_trend_threshold
        self.strong_trend_strategy = AdvancedMomentumStrategy(stock_universe=Config.STOCKS)
        self.moderate_trend_strategy = DualMaCrossoverStrategy()
        self.pairs_trading_strategy = DynamicPairsStrategy(pairs_list=Config.PAIRS_LIST)
        self.ranging_strategy = MeanReversionStrategy()
        self.vol_breakout_strategy = VolatilityBreakoutStrategy()
        self.rsi_divergence_strategy = RSIDivergenceStrategy()
        self.arbitrage_strategy = StatisticalArbitrageStrategy(pairs_list=Config.PAIRS_LIST)
        self.vwap_strategy = VWAPStrategy()
        self.enhanced_arbitrage = EnhancedArbitrageStrategy(Config.PAIRS_LIST)

    def generate_signal(
            self, data: pd.DataFrame | Dict[str, pd.DataFrame], **kwargs: Any
    ) -> List[Tuple[str, str, str, Dict[str, float]]]:
        full_stock_data = kwargs.get("full_stock_data", data)  # Fallback to data if not provided

        # New: Convert wide MultiIndex DataFrame to Dict[str, pd.DataFrame] if needed
        if isinstance(full_stock_data, pd.DataFrame) and isinstance(full_stock_data.columns, pd.MultiIndex):
            sliced_data = {}
            for stock in full_stock_data.columns.levels[0]:  # e.g., 'JPPOWER', 'share1'
                try:
                    stock_df = full_stock_data[stock].rename(columns={
                        'open': 'open', 'high': 'high', 'low': 'low', 'close': 'close', 'volume': 'volume'
                    }).dropna()  # Standardize and drop NaNs
                    if not all(col in stock_df.columns for col in ['high', 'low', 'close']):
                        logging.warning(f"Skipping {stock}: Missing required columns")
                        continue
                    sliced_data[stock] = stock_df
                except KeyError as e:
                    logging.error(f"Failed to slice data for {stock}: {e}")
                    continue
            full_stock_data = sliced_data if sliced_data else {}

        # If still not a dict, or empty, fallback
        if not isinstance(full_stock_data, dict) or not full_stock_data:
            logging.error("Invalid or empty full_stock_data; cannot generate signals")
            return [("", "HOLD", "Invalid data format", {})]

        # Filter valid stocks (sufficient length, required columns)
        min_required_length = 2 * self.adx_period
        valid_stock_data = {}
        for stock, df in full_stock_data.items():
            required_cols = ['high', 'low', 'close', 'volume']
            if len(df) < min_required_length or not all(col in df.columns for col in required_cols):
                logging.warning(f"Skipping {stock}: Insufficient data or missing columns")
                continue
            valid_stock_data[stock] = df

        if not valid_stock_data:
            return [("", "HOLD", "No valid stock data available", {})]

        # Select a representative DataFrame for regime analysis (e.g., first valid stock)
        rep_stock = next(iter(valid_stock_data))
        rep_data = valid_stock_data[rep_stock]

        try:
            adx_indicator = ta.trend.ADXIndicator(
                high=rep_data["high"], low=rep_data["low"], close=rep_data["close"], window=self.adx_period
            )
            adx_series = adx_indicator.adx().fillna(0)
            last_adx = adx_series.iloc[-1]

            atr_indicator = ta.volatility.AverageTrueRange(
                high=rep_data["high"], low=rep_data["low"], close=rep_data["close"]
            )
            atr_series = atr_indicator.average_true_range().fillna(0)
            atr = atr_series.iloc[-1]
            high_vol = atr > rep_data["close"].iloc[-1] * 0.015
        except KeyError as e:
            logging.error(f"Missing column in data: {e}")
            return [("", "HOLD", f"Missing column: {e}", {})]
        except Exception as e:
            logging.error(f"Regime analysis error: {e}")
            return [("", "HOLD", "Analysis failed", {})]

        current_portfolio = kwargs.get("current_portfolio", [])

        def confirm_signal(signals: List[Tuple[str, str, str, Dict[str, float]]], full_data: Dict[str, pd.DataFrame]) -> \
        List[Tuple[str, str, str, Dict[str, float]]]:
            confirmed = []
            for instrument, signal, reason, extras in signals:
                if instrument not in full_data:
                    continue
                stock_data = full_data[instrument]
                if len(stock_data) < 10 or "volume" not in stock_data.columns:
                    continue
                current_vol = stock_data["volume"].iloc[-1]
                avg_vol = stock_data["volume"].rolling(10).mean().iloc[-1] if len(stock_data) >= 10 else stock_data[
                    "volume"].mean()
                if pd.isna(current_vol) or pd.isna(
                        avg_vol) or current_vol < avg_vol * Config.VOLUME_CONFIRMATION_MULTIPLIER:
                    continue
                # Enhance profit: Adjust size based on ATR (risk 1% capital)
                capital = kwargs.get("capital", 10000.0)
                risk_per_trade = 0.01 * capital
                stop_distance = extras.get("stop_loss", 0) - stock_data["close"].iloc[-1] if signal == "BUY" else \
                stock_data["close"].iloc[-1] - extras.get("stop_loss", 0)
                extras["size"] = risk_per_trade / abs(stop_distance) if stop_distance != 0 else 100
                confirmed.append((instrument, signal, reason, extras))
            return confirmed if confirmed else [("", "HOLD", "All signals ignored: Low volume", {})]

        if last_adx > self.strong_trend_threshold:
            logging.info(f"STRONG TREND (ADX: {last_adx:.2f}) -> Advanced Momentum")
            try:
                signals = self.strong_trend_strategy.generate_signal(full_stock_data,
                                                                     current_portfolio=current_portfolio)
            except KeyError as e:
                logging.error(f"Signal generation failed: {e}")
                signals = []
            return confirm_signal(signals, full_stock_data)
        elif last_adx > self.trend_threshold:
            logging.info(f"MODERATE TREND (ADX: {last_adx:.2f}) -> Dual MA")
            signals = []
            for stock, stock_data in full_stock_data.items():
                if len(stock_data) < max(Config.MA_SHORT_WINDOW, Config.MA_LONG_WINDOW) + 1:
                    continue
                try:
                    stock_signals = self.moderate_trend_strategy.generate_signal(stock_data, stock=stock)
                    signals.extend([s for s in stock_signals if s[1] != "HOLD"])
                except KeyError as e:
                    logging.error(f"Error in DualMaCrossoverStrategy for {stock}: {e}")
                    continue
            return confirm_signal(signals, full_stock_data)
        elif high_vol:
            logging.info(f"HIGH VOLATILITY (ATR: {atr:.2f}) -> Volatility Breakout + RSI Divergence")
            vol_signals = self.vol_breakout_strategy.generate_signal(full_stock_data)
            rsi_signals = self.rsi_divergence_strategy.generate_signal(full_stock_data)
            combined_signals = vol_signals + rsi_signals
            return confirm_signal(combined_signals, full_stock_data)
        else:
            logging.info(f"RANGING MARKET (ADX: {last_adx:.2f}) -> Mean Reversion + Pairs Trading + VWAP")
            mean_signals = self.ranging_strategy.generate_signal(full_stock_data)
            pairs_signals = self.pairs_trading_strategy.generate_signal(full_stock_data)
            vwap_signals = self.vwap_strategy.generate_signal(full_stock_data)
            combined_signals = mean_signals + pairs_signals + vwap_signals
            return confirm_signal(combined_signals, full_stock_data)
