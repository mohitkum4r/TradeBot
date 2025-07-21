from abc import ABC, abstractmethod


class ISentimentAnalyzer(ABC):
    @abstractmethod
    def analyze_sentiment(self, stock: str) -> float:
        pass
