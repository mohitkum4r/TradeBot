# domain/strategies/volatility_breakout_strategy.py
import pandas as pd
import ta.momentum
import logging
from typing import List, Tuple, Dict, Any
from .base_strategy import BaseStrategy
from app.config import Config

logging.basicConfig(level=logging.INFO)


class VolatilityBreakoutStrategy(BaseStrategy):
    def __init__(
            self, window: int = Config.VOL_BREAKOUT_WINDOW, volume_multiplier: float = 1.5
    ):
        self.window = window
        self.volume_multiplier = volume_multiplier

    def generate_signal(
            self, data: Dict[str, pd.DataFrame], **kwargs: Any
    ) -> List[Tuple[str, str, str, Dict[str, float]]]:
        """
        Updated to handle dict[str, DataFrame] input like other strategies
        """
        signals = []
        for stock, stock_data in data.items():
            sentiment_score = kwargs.get("sentiment_score", 0.0)
            if len(stock_data) < self.window:
                continue

            try:
                recent_high = stock_data["high"].rolling(self.window).max().iloc[-1]
                recent_low = stock_data["low"].rolling(self.window).min().iloc[-1]
                avg_volume = stock_data["volume"].rolling(self.window).mean().iloc[-1]

                # Add RSI for better signal quality
                rsi_series = ta.momentum.RSIIndicator(stock_data["close"], window=14).rsi()
                rsi = rsi_series.iloc[-1] if not pd.isna(rsi_series.iloc[-1]) else 50.0

                last = stock_data.iloc[-1]

                # Safe scalar access and float conversion to satisfy type checkers
                def get_float_value(s: pd.Series, key: str) -> float:
                    value = s.get(key)  # Returns scalar or None
                    if pd.isna(value):
                        return 0.0
                    return float(value)  # Explicit cast for type safety

                close_price = get_float_value(last, "close")
                volume = get_float_value(last, "volume")
                recent_high = float(recent_high) if not pd.isna(recent_high) else 0.0
                recent_low = float(recent_low) if not pd.isna(recent_low) else 0.0
                avg_volume = float(avg_volume) if not pd.isna(avg_volume) else 0.0
                rsi = float(rsi) if not pd.isna(rsi) else 50.0

                if (
                        close_price > recent_high
                        and volume > avg_volume * self.volume_multiplier
                        and sentiment_score > 0.2
                        and rsi > 50
                ):
                    extras = {
                        "stop_loss": recent_low,
                        "take_profit": close_price * 1.05,
                        "size": 100.0
                    }
                    signals.append((
                        stock,
                        "BUY",
                        f"Breakout above {recent_high:.2f} with high volume/RSI {rsi:.1f}.",
                        extras
                    ))
                elif close_price < recent_low and sentiment_score < -0.2 and rsi < 50:
                    extras = {
                        "stop_loss": recent_high,
                        "take_profit": close_price * 0.95,
                        "size": 100.0
                    }
                    signals.append((
                        stock,
                        "SELL",
                        f"Breakdown below {recent_low:.2f} with RSI {rsi:.1f}.",
                        extras
                    ))
            except (KeyError, IndexError) as e:
                logging.warning(f"Data issue for {stock}: {e}")
                continue

        return signals if signals else [("", "HOLD", "No breakout signal.", {})]
