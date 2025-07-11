# autotrade/strategies/ml_prediction_strategy.py

import pandas as pd
import joblib  # Example for loading a scikit-learn model
from .base_strategy import BaseStrategy


class MLPredictionStrategy(BaseStrategy):
    """
    A template for a strategy that uses a pre-trained Machine Learning model
    to predict future price movements.
    Source: Algorithmic Trading NSE Strategies_.docx [cite: 1628]
    """

    def __init__(self, model_path: str = "model.pkl"):
        try:
            self.model = joblib.load(model_path)
            print(f"Successfully loaded model from {model_path}")
        except FileNotFoundError:
            print(f"Error: Model file not found at {model_path}.")
            self.model = None

    def _engineer_features(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        This is a critical step. The features created here must match
        the features the model was trained on.
        Source: Algorithmic Trading NSE Strategies_.docx [cite: 1641, 1682]
        """
        # Example features:
        data["returns"] = data["close"].pct_change()
        data["volatility"] = data["returns"].rolling(window=20).std()
        data.dropna(inplace=True)
        return data

    def generate_signal(
        self, data: pd.DataFrame, sentiment_score: float = 0.0
    ) -> tuple[str, str]:
        if self.model is None:
            return "HOLD", "ML Model not loaded."

        if len(data) < 21:  # Need enough data for feature engineering
            return "HOLD", "Insufficient data for feature engineering."

        # 1. Engineer features from the latest data
        features_df = self._engineer_features(data.copy())
        latest_features = features_df.iloc[-1:][
            ["returns", "volatility"]
        ]  # Match training columns

        # 2. Make a prediction
        try:
            prediction = self.model.predict(latest_features)[0]
        except Exception as e:
            return "HOLD", f"Error during model prediction: {e}"

        # 3. Convert prediction to a trading signal [cite: 1633]
        # (Assuming model outputs 1 for BUY, -1 for SELL, 0 for HOLD)
        if prediction == 1:
            return "BUY", f"ML model predicted UP trend."
        elif prediction == -1:
            return "SELL", f"ML model predicted DOWN trend."
        else:
            return "HOLD", "ML model predicted NEUTRAL trend."
