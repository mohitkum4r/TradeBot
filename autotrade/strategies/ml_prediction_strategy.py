# autotrade/strategies/ml_prediction_strategy.py

import pandas as pd
import joblib
from sklearn.linear_model import SGDRegressor  # Example online-learning model
from .base_strategy import BaseStrategy


class MLPredictionStrategy(BaseStrategy):
    """
    A strategy that uses a pre-trained Machine Learning model
    to predict future price movements, with online learning.
    Source: Algorithmic Trading NSE Strategies_.docx [cite: 1628]
    """

    def __init__(self, model_path: str = "model.pkl"):
        self.model_path = model_path
        try:
            self.model = joblib.load(model_path)
            print(f"Successfully loaded model from {model_path}")
        except FileNotFoundError:
            print(f"Error: Model file not found at {model_path}. Initializing new model.")
            self.model = SGDRegressor()  # Online-learnable model (supports partial_fit)
            self._save_model()  # Save initial model

    def _save_model(self):
        joblib.dump(self.model, self.model_path)
        print(f"Model saved to {self.model_path}")

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

    def retrain_model(self, new_data: pd.DataFrame):
        """Incrementally train the model on new data (online learning)."""
        if not isinstance(self.model, SGDRegressor):
            print("Model does not support online learning. Skipping retrain.")
            return

        features_df = self._engineer_features(new_data.copy())
        if len(features_df) < 1:
            print("Insufficient new data for retraining.")
            return

        X = features_df[["returns", "volatility"]]
        y = features_df["close"].shift(-1)[:-1]  # Predict next close (example target)
        X = X[:-1]  # Align with y

        if len(X) > 0:
            self.model.partial_fit(X, y)
            self._save_model()
            print(f"Model retrained on {len(X)} new data points. Ready for more profits! 💰")

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
        # (Assuming model predicts price change: positive for BUY, negative for SELL)
        if prediction > 0:
            return "BUY", f"ML model predicted UP trend ({prediction:.2f})."
        elif prediction < 0:
            return "SELL", f"ML model predicted DOWN trend ({prediction:.2f})."
        else:
            return "HOLD", "ML model predicted NEUTRAL trend."

        # Retrain on this data for online learning (after signal)
        self.retrain_model(data)