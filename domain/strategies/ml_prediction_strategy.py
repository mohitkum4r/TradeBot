# domain/strategies/ml_prediction_strategy.py
import pandas as pd
import joblib
from sklearn.linear_model import SGDRegressor
import logging
from typing import Any
from .base_strategy import BaseStrategy

logging.basicConfig(level=logging.INFO)


class MLPredictionStrategy(BaseStrategy):
    def __init__(
        self,
        model_path: str = "model.pkl",
        optimal_model_path: str = "optimal_trade_model.joblib",
    ):
        self.model_path = model_path
        self.optimal_model_path = optimal_model_path
        self.model = None
        self.is_optimal = False
        try:
            self.model = joblib.load(self.optimal_model_path)
            self.is_optimal = True
            logging.info(f"Loaded optimal model from {self.optimal_model_path}")
        except FileNotFoundError:
            try:
                self.model = joblib.load(self.model_path)
                logging.info(f"Loaded default model from {self.model_path}")
            except FileNotFoundError:
                self.model = SGDRegressor()
                self._save_model()
                logging.info(f"Initialized new model and saved to {self.model_path}")

    def _save_model(self):
        joblib.dump(self.model, self.model_path)

    def _engineer_features(self, data: pd.DataFrame) -> pd.DataFrame:
        data["returns"] = data["close"].pct_change().fillna(0)
        data["volatility"] = data["returns"].rolling(window=20).std().fillna(0)
        data.dropna(inplace=True)
        return data

    def retrain_model(self, new_data: pd.DataFrame):
        if not hasattr(self.model, "partial_fit"):
            logging.warning("Model does not support online learning. Skipping retrain.")
            return
        features_df = self._engineer_features(new_data.copy())
        if len(features_df) < 1:
            logging.warning("Insufficient new data for retraining.")
            return
        X = features_df[["returns", "volatility"]]
        y = features_df["close"].shift(-1)[:-1]
        X = X[:-1]
        if len(X) > 0:
            self.model.partial_fit(X, y)
            self._save_model()
            logging.info(f"Model retrained on {len(X)} new data points.")

    def generate_signal(
        self, data: pd.DataFrame, **kwargs: Any
    ) -> list[tuple[str, str, str]]:
        stock = kwargs.get("stock", "")
        if self.model is None:
            return [(stock, "HOLD", "ML Model not loaded.")]
        if len(data) < 21:
            return [(stock, "HOLD", "Insufficient data for feature engineering.")]
        features_df = self._engineer_features(data.copy())
        latest_features = features_df.iloc[-1:][["returns", "volatility"]]
        try:
            prediction = self.model.predict(latest_features)[0]
        except Exception as e:
            logging.error(f"Prediction error: {e}")
            return [(stock, "HOLD", f"Error during model prediction: {e}")]
        if prediction > 0:
            return [(stock, "BUY", f"ML model predicted UP trend ({prediction:.2f}).")]
        elif prediction < 0:
            return [
                (stock, "SELL", f"ML model predicted DOWN trend ({prediction:.2f}).")
            ]
        else:
            return [(stock, "HOLD", "ML model predicted NEUTRAL trend.")]
