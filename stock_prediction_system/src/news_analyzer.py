import requests
# from transformers import pipeline
# self.transformer_sentiment = None  # Disabled due to dependency issues
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
import logging
from datetime import datetime, timedelta
import nltk
from nltk.sentiment import SentimentIntensityAnalyzer as NLTKSentiment

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class NewsAnalyzer:
    def __init__(self, config):
        self.config = config
        self.api_key = config.NEWS_API_KEY
        self.sentiment_analyzer = SentimentIntensityAnalyzer()
        
        # Load transformer model for advanced sentiment analysis
        logger.info("Transformer sentiment disabled - using VADER only")
        self.transformer_sentiment = None
    
    def fetch_company_news(self, company_name, days_back=7):
        """Fetch news for a company using Finnhub API"""
        try:
            # Map common company names to symbols
            symbol_map = {
                'apple': 'AAPL',
                'microsoft': 'MSFT',
                'google': 'GOOGL',
                'amazon': 'AMZN',
                'tesla': 'TSLA',
                'meta': 'META',
                'nvidia': 'NVDA',
                'netflix': 'NFLX'
            }

            # Get symbol from company name
            symbol = symbol_map.get(company_name.lower(), company_name.upper())

            # Calculate date range
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days_back)

            # Finnhub company-news endpoint (specific to a stock symbol)
            url = 'https://finnhub.io/api/v1/company-news'
            params = {
                'symbol': symbol,
                'from': start_date.strftime('%Y-%m-%d'),
                'to': end_date.strftime('%Y-%m-%d'),
                'token': self.api_key
            }

            response = requests.get(url, params=params, timeout=10)

            if response.status_code == 200:
                articles = response.json()
                # Transform Finnhub format to match expected format
                transformed = []
                for article in articles:
                    transformed.append({
                        'title': article.get('headline', ''),
                        'description': article.get('summary', ''),
                        'url': article.get('url', ''),
                        'publishedAt': article.get('datetime', ''),
                        'source': article.get('source', '')
                    })
                logger.info(f"Fetched {len(transformed)} news articles for {company_name} ({symbol})")
                return transformed
            else:
                logger.error(f"Finnhub API error: {response.status_code} - {response.text}")
                return []

        except Exception as e:
            logger.error(f"Error fetching news: {e}")
            return []
    
    def analyze_sentiment(self, text):
        """Analyze sentiment of text using multiple methods"""
        try:
            # VADER sentiment
            vader_scores = self.sentiment_analyzer.polarity_scores(text)
            
            # Transformer sentiment if available
            transformer_score = None
            if self.transformer_sentiment and len(text) < 512:
                result = self.transformer_sentiment(text[:512])[0]
                transformer_score = {
                    'label': result['label'],
                    'score': result['score']
                }
            
            # Combined sentiment score
            combined_score = vader_scores['compound']
            
            sentiment_label = 'NEUTRAL'
            if combined_score > 0.05:
                sentiment_label = 'POSITIVE'
            elif combined_score < -0.05:
                sentiment_label = 'NEGATIVE'
            
            return {
                'vader': vader_scores,
                'transformer': transformer_score,
                'combined_score': combined_score,
                'sentiment': sentiment_label
            }
            
        except Exception as e:
            logger.error(f"Sentiment analysis error: {e}")
            return {'combined_score': 0, 'sentiment': 'NEUTRAL'}
    
    def get_news_sentiment_score(self, company_name):
        """Get aggregated sentiment score from recent news"""
        articles = self.fetch_company_news(company_name)
        
        if not articles:
            return 0, "No news found"
        
        sentiments = []
        important_news = []
        
        for article in articles:
            title = article.get('title', '')
            description = article.get('description', '')
            content = f"{title}. {description}"
            
            if content and len(content) > 10:
                sentiment = self.analyze_sentiment(content)
                sentiments.append(sentiment['combined_score'])
                
                if abs(sentiment['combined_score']) > 0.5:
                    important_news.append({
                        'title': title,
                        'sentiment': sentiment['sentiment'],
                        'score': sentiment['combined_score']
                    })
        
        if sentiments:
            # Weighted average with recency
            avg_sentiment = sum(sentiments) / len(sentiments)
            
            # Normalize to range [-1, 1]
            sentiment_score = max(-1, min(1, avg_sentiment))
            
            return sentiment_score, important_news
        
        return 0, []

