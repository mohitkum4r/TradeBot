# domain/strategies/dual_ma_crossover_strategy.py
import pandas as pd
import ta.trend
import ta.momentum
import logging
from typing import List, Tuple, Dict, Any
from .base_strategy import BaseStrategy
from app.config import Config

logging.basicConfig(level=logging.INFO)


class DualMaCrossoverStrategy(BaseStrategy):
    def __init__(
            self,
            short_window: int = 50,  # Optimized
            long_window: int = 200,  # Optimized
    ):
        self.short_window = short_window
        self.long_window = long_window
        self.cooldowns = {}  # {stock: remaining cooldown steps}

    def generate_signal(
            self, data: pd.DataFrame, **kwargs: Any
    ) -> List[Tuple[str, str, str, Dict[str, float]]]:
        sentiment_score = kwargs.get("sentiment_score", 0.0)
        stock = kwargs.get("stock", "")
        min_length = max(self.short_window, self.long_window) + 1

        if len(data) < min_length:
            return [(stock, "HOLD", f"Insufficient historical data (need {min_length} points).", {})]

        try:
            data = data.copy()
            data["short_ma"] = ta.trend.EMAIndicator(data["close"], window=self.short_window).ema_indicator().bfill()
            data["long_ma"] = ta.trend.EMAIndicator(data["close"], window=self.long_window).ema_indicator().bfill()
            data["rsi"] = ta.momentum.RSIIndicator(data["close"], window=14).rsi().fillna(50)
            data["adx"] = ta.trend.ADXIndicator(data["high"], data["low"], data["close"], window=14).adx().fillna(0)

            last = data.iloc[-1]
            prev = data.iloc[-2] if len(data) > 1 else last

            # Safe scalar access and float conversion to satisfy type checkers
            def get_float_value(s: pd.Series, key: str) -> float:
                value = s.get(key)  # Returns scalar or None
                if pd.isna(value):
                    return 0.0
                return float(value)  # Explicit cast for type safety

            close_price = get_float_value(last, "close")
            short_ma = get_float_value(last, "short_ma")
            long_ma = get_float_value(last, "long_ma")
            rsi_value = get_float_value(last, "rsi")
            adx_value = get_float_value(last, "adx")
            prev_short_ma = get_float_value(prev, "short_ma")
            prev_long_ma = get_float_value(prev, "long_ma")

            if stock in self.cooldowns and self.cooldowns[stock] > 0:
                self.cooldowns[stock] -= 1
                return [(stock, "HOLD", "In cooldown after recent loss.", {})]

            # Buy signal with enhancements
            if short_ma > long_ma and prev_short_ma <= prev_long_ma:
                if rsi_value > 30 and sentiment_score > 0.2 and adx_value > 25:  # Optimized thresholds
                    extras = {
                        "stop_loss": close_price * 0.98,
                        "take_profit": close_price * 1.05,
                        "size": 100.0
                    }
                    return [(stock, "BUY", f"Golden Cross: RSI {rsi_value:.2f}, ADX {adx_value:.2f}.", extras)]
                else:
                    return [(stock, "HOLD", "Golden Cross but failed filters.", {})]

            # Sell signal with enhancements
            if short_ma < long_ma and prev_short_ma >= prev_long_ma:
                if rsi_value < 70 and sentiment_score < -0.2 and adx_value > 25:
                    self.cooldowns[stock] = getattr(Config, 'COOLDOWN_AFTER_LOSS', 5)
                    extras = {
                        "stop_loss": close_price * 1.02,
                        "take_profit": close_price * 0.95,
                        "size": 100.0
                    }
                    return [(stock, "SELL", f"Death Cross: RSI {rsi_value:.2f}, ADX {adx_value:.2f}.", extras)]
                else:
                    return [(stock, "HOLD", "Death Cross but failed filters.", {})]

            return [(stock, "HOLD", "No crossover signal.", {})]

        except (KeyError, IndexError, TypeError) as e:
            logging.error(f"Error in DualMaCrossoverStrategy for {stock}: {e}")
            return [(stock, "HOLD", f"Error processing data: {str(e)}", {})]
