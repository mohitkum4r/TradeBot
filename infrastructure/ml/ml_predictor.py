# infrastructure/ml/ml_predictor.py
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score
import joblib
import logging


class MLPredictor:
    def __init__(self, model_path="model.pkl"):
        self.model_path = model_path
        try:
            self.model = joblib.load(model_path)
            self.is_trained = True
        except FileNotFoundError:
            self.model = RandomForestClassifier(n_estimators=100, random_state=42)
            self.is_trained = False

    def _prepare_data(self, data: pd.DataFrame):
        features = data[["open", "high", "low", "close", "volume"]].copy()  # Lowercase
        features["returns"] = features["close"].pct_change()
        features["ma5"] = features["close"].rolling(window=5).mean()
        features["ma20"] = features["close"].rolling(window=20).mean()
        features.dropna(inplace=True)
        target = (features["close"].shift(-1) > features["close"]).astype(int)
        features = features.iloc[:-1]
        target = target.iloc[:-1]
        return features, target

    def train(self, data: pd.DataFrame):
        X, y = self._prepare_data(data)
        if len(X) < 20:
            logging.warning("Not enough data to train")
            return
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, random_state=42
        )
        self.model.fit(X_train, y_train)
        predictions = self.model.predict(X_test)
        accuracy = accuracy_score(y_test, predictions)
        logging.info(f"Model trained with accuracy: {accuracy:.2f}")
        self.is_trained = True
        joblib.dump(self.model, self.model_path)

    def predict(self, data: pd.DataFrame) -> int:
        if not self.is_trained:
            logging.warning("Model not trained; defaulting to 0")
            return 0
        features, _ = self._prepare_data(data)
        if features.empty:
            return 0
        latest_features = features.iloc[[-1]]
        prediction = self.model.predict(latest_features)
        return int(prediction[0])


logging.basicConfig(level=logging.INFO)
