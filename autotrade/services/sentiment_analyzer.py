import requests
from bs4 import BeautifulSoup
import praw
import ollama
from ..config import Config
from tenacity import retry, stop_after_attempt, wait_fixed


class SentimentAnalyzer:
    def __init__(self):
        self.enabled = Config.SENTIMENT_ANALYSIS_ENABLED
        self.reddit = None
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
                print("Reddit client initialized successfully.")
            else:
                print(
                    "Warning: Reddit credentials not found. Sentiment analysis from Reddit will be skipped."
                )
        except Exception as e:
            print(f"Warning: Reddit initialization failed. {e}")

    @retry(stop=stop_after_attempt(2), wait=wait_fixed(2))
    def get_sentiment_score(self, stock: str) -> float:
        if not self.enabled:
            return 0.0

        print(f"Analyzing sentiment for {stock}...")
        headlines = self._scrape_news(stock)
        reddit_posts = self._scrape_reddit(stock)

        text_corpus = " ".join(headlines + reddit_posts)
        if not text_corpus.strip():
            print(f"No text found for sentiment analysis of {stock}.")
            return 0.0

        score_text = ""
        try:
            prompt = (
                f"Analyze the financial sentiment of the following text regarding the stock '{stock}'. "
                f"Provide only a single floating-point number from -1.0 (very bearish) to 1.0 (very bullish). "
                f"Consider the context of financial markets. Text: '{text_corpus[:2000]}'"
            )

            response = ollama.generate(model=Config.OLLAMA_MODEL, prompt=prompt)
            score_text = response["response"].strip()
            score = float(score_text)
            print(f"Sentiment score for {stock}: {score:.2f}")
            return score
        except (ValueError, TypeError) as e:
            print(
                f"Error converting sentiment analysis response to float for {stock}: {e}. Response was: '{score_text}'"
            )
            return 0.0
        except Exception as e:
            print(f"Error during sentiment analysis for {stock}: {e}")
            return 0.0

    def _scrape_news(self, stock: str) -> list[str]:
        # Note: Web scraping is fragile. Consider a news API for production.
        headlines = []
        # Using a more generic search to be more robust
        url = f"https://www.google.com/search?q={stock}+stock+news&tbm=nws"
        try:
            resp = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
            resp.raise_for_status()
            soup = BeautifulSoup(resp.text, "html.parser")
            for item in soup.find_all("h3", limit=5):
                headlines.append(item.get_text())
        except requests.RequestException as e:
            print(f"Could not scrape news for {stock}: {e}")
        return headlines

    def _scrape_reddit(self, stock: str) -> list[str]:
        if not self.reddit:
            return []
        posts = []
        try:
            # Searching multiple relevant subreddits
            subreddit_list = "IndianStreetBets+IndiaInvestments+StockMarket"
            subreddit = self.reddit.subreddit(subreddit_list)
            query = f'"{stock}"'  # Search for exact stock name
            for submission in subreddit.search(query, limit=5, sort="new"):
                posts.append(submission.title)
        except Exception as e:
            print(f"Could not scrape Reddit for {stock}: {e}")
        return posts
