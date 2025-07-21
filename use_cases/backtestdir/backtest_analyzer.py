# use_cases/backtest_analyzer.py
import pandas as pd
import logging
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score
from sklearn.preprocessing import LabelEncoder
from joblib import dump, load
from typing import List, Dict
from app.config import Config
import ollama

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

def train_ml_on_optimal(detailed_logs: List[Dict]) -> None:
    logging.info("Training ML Model on Optimal Signals")
    ml_data = []
    for log in detailed_logs:
        for stock, feats in log["features"].items():
            optimal = log.get("optimal_signals", {}).get(stock, "HOLD")
            row = {
                "adx": feats["adx"],
                "atr": feats["atr"],
                "rsi": feats["rsi"],
                "optimal_signal": optimal,
            }
            ml_data.append(row)
    if len(ml_data) < 50:
        logging.warning("Insufficient data for ML training")
        return
    df = pd.DataFrame(ml_data)
    X = df[["adx", "atr", "rsi"]]
    y = LabelEncoder().fit_transform(df["optimal_signal"])
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
    try:
        model = load("optimal_trade_model.joblib")
    except FileNotFoundError:
        model = RandomForestClassifier(n_estimators=100, random_state=42)
    model.fit(X_train, y_train)
    accuracy = accuracy_score(y_test, model.predict(X_test))
    logging.info(f"ML Accuracy: {accuracy * 100:.2f}%")
    dump(model, "optimal_trade_model.joblib")

def examine_backtest(performance_log: dict, historical_data: Dict[str, pd.DataFrame]):
    logging.info("Running Backtest Examiner")
    ideal_pnl = {}
    for stock, df in historical_data.items():
        if df.empty:
            continue
        min_price = df["low"].min()
        max_price = df["high"].max()
        min_price = min_price if not pd.isna(min_price) else 0.0
        max_price = max_price if not pd.isna(max_price) else 0.0
        if min_price >= max_price or min_price == 0:
            continue
        qty = int(performance_log["initial_capital"] * 0.2 / min_price)
        ideal_profit = (max_price - min_price) * qty
        ideal_pnl[stock] = ideal_profit
    total_ideal_pnl = sum(ideal_pnl.values())
    actual_pnl = performance_log["total_pnl"]
    pnl_gap = total_ideal_pnl - actual_pnl
    logging.info(f"Ideal PnL: ₹{total_ideal_pnl:,.2f} | Actual: ₹{actual_pnl:,.2f} | Gap: ₹{pnl_gap:,.2f}")

    try:
        prompt = f"Analyze backtest: {performance_log}. Ideal PnL: {total_ideal_pnl}. Gap: {pnl_gap}. Suggest improvements."
        response = ollama.generate(model=Config.OLLAMA_MODEL, prompt=prompt)
        analysis = response["response"].strip()
        logging.info(f"LLM Analysis: {analysis}")
    except Exception as e:
        logging.error(f"LLM failed: {e}")
