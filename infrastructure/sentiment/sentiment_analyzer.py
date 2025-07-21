# infrastructure/sentiment/sentiment_analyzer.py
import requests
from bs4 import BeautifulSoup
import praw
import ollama
from app.config import Config
from tenacity import retry, stop_after_attempt, wait_fixed
import logging
from datetime import datetime, timedelta


class SentimentAnalyzer:
    def __init__(self):
        self.enabled = Config.SENTIMENT_ANALYSIS_ENABLED
        self.reddit = None
        self._cache = {}
        self._cache_expiry = timedelta(minutes=30)
        if self.enabled:
            self._initialize_reddit()

    def _initialize_reddit(self):
        try:
            if Config.REDDIT_CLIENT_ID and Config.REDDIT_CLIENT_SECRET:
                self.reddit = praw.Reddit(
                    client_id=Config.REDDIT_CLIENT_ID,
                    client_secret=Config.REDDIT_CLIENT_SECRET,
                    user_agent=Config.REDDIT_USER_AGENT,
                )
                logging.info("Reddit initialized")
            else:
                logging.warning("Reddit credentials missing")
        except Exception as e:
            logging.error(f"Reddit init failed: {e}")

    @retry(stop=stop_after_attempt(2), wait=wait_fixed(2))
    def get_sentiment_score(self, stock: str) -> float:
        if not self.enabled:
            return 0.0
        cache_key = stock
        now = datetime.now()
        if (
            cache_key in self._cache
            and (now - self._cache[cache_key]["timestamp"]) < self._cache_expiry
        ):
            return self._cache[cache_key]["score"]
        logging.info(f"Analyzing sentiment for {stock}")
        headlines = self._scrape_news(stock)
        reddit_posts = self._scrape_reddit(stock)

        text_corpus = " ".join(headlines + reddit_posts)
        if not text_corpus.strip():
            logging.warning(f"No text for {stock}")
            return 0.0
        try:
            prompt = f"Analyze sentiment for '{stock}'. Return float -1.0 to 1.0. Text: '{text_corpus[:2000]}'"
            response = ollama.generate(model=Config.OLLAMA_MODEL, prompt=prompt)
            score = float(response["response"].strip())
            self._cache[cache_key] = {"timestamp": now, "score": score}
            logging.info(f"Score for {stock}: {score:.2f}")
            return score
        except Exception as e:
            logging.error(f"Sentiment error for {stock}: {e}")
            return 0.0

    def _scrape_news(self, stock: str) -> list[str]:
        headlines = []
        url = f"https://www.google.com/search?q={stock}+stock+news&tbm=nws"
        try:
            resp = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
            resp.raise_for_status()
            soup = BeautifulSoup(resp.text, "html.parser")
            for item in soup.find_all("h3", limit=5):
                headlines.append(item.get_text())
        except Exception as e:
            logging.error(f"News scrape failed for {stock}: {e}")
        return headlines

    def _scrape_reddit(self, stock: str) -> list[str]:
        if not self.reddit:
            return []
        posts = []
        try:
            subreddit = self.reddit.subreddit(
                "IndianStreetBets+IndiaInvestments+StockMarket"
            )
            for submission in subreddit.search(f'"{stock}"', limit=5, sort="new"):
                posts.append(submission.title)
        except Exception as e:
            logging.error(f"Reddit scrape failed for {stock}: {e}")
        return posts


logging.basicConfig(level=logging.INFO)
