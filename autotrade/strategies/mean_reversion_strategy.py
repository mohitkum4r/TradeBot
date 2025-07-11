import pandas as pd
import ta
from .base_strategy import BaseStrategy


class MeanReversionStrategy(BaseStrategy):
    """
    A strategy based on the principle of mean reversion using Bollinger Bands.
    It now incorporates sentiment as a potential filter.
    """

    def __init__(self, bb_window=20, bb_std_dev=2.0, sentiment_threshold=0.2):
        self.bb_window = bb_window
        self.bb_std_dev = bb_std_dev
        self.sentiment_threshold = sentiment_threshold

    def generate_signal(
        self, data: pd.DataFrame, sentiment_score: float = 0.0
    ) -> tuple[str, str]:
        if len(data) < self.bb_window:
            return "HOLD", "Insufficient historical data for Bollinger Bands."

        # Calculate Bollinger Bands
        bb = ta.volatility.BollingerBands(
            data["close"], window=self.bb_window, window_dev=self.bb_std_dev
        )
        data["bb_high"] = bb.bollinger_hband()
        data["bb_low"] = bb.bollinger_lband()
        data["bb_mid"] = bb.bollinger_mavg()

        last = data.iloc[-1]

        # --- Buy Logic ---
        # Price crosses below the lower Bollinger Band.
        # Optional: Add sentiment check to avoid buying into very negative news.
        if (
            last["close"] < last["bb_low"]
            and sentiment_score >= -self.sentiment_threshold
        ):
            return (
                "BUY",
                f"Price {last['close']:.2f} below lower BB {last['bb_low']:.2f}.",
            )

        # --- Sell Logic ---
        # Price crosses above the upper Bollinger Band.
        # Optional: Add sentiment check to confirm selling signal.
        if (
            last["close"] > last["bb_high"]
            and sentiment_score <= self.sentiment_threshold
        ):
            return (
                "SELL",
                f"Price {last['close']:.2f} above upper BB {last['bb_high']:.2f}.",
            )

        # Take profit logic: if price reverts to the mean (middle band)
        # This part should be handled by the TradeExecutor's take-profit mechanism
        # but can also be a signal here.
        # if last['close'] > last['bb_mid']:
        #     return 'SELL', f"Price reverted to mean at {last['bb_mid']:.2f}"

        return "HOLD", "Price is within Bollinger Bands."
