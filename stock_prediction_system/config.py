import os

class Config:
    # Paths
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    DATA_RAW_PATH = os.path.join(BASE_DIR, 'data', 'raw')
    DATA_PROCESSED_PATH = os.path.join(BASE_DIR, 'data', 'processed')
    MODELS_PATH = os.path.join(BASE_DIR, 'data', 'models')

    # Redis Configuration (Upstash)
    REDIS_URL = os.environ.get('REDIS_URL', '')
    REDIS_TOKEN = os.environ.get('REDIS_TOKEN', '')
    REDIS_ENABLED = bool(REDIS_URL and REDIS_TOKEN)

    # Model parameters
    SEQUENCE_LENGTH = 60
    PREDICTION_DAYS = 1
    TEST_SIZE = 0.2
    RANDOM_STATE = 42

    # News API - Finnhub
    NEWS_API_KEY = os.environ.get('FINNHUB_API_KEY', 'd7vfunpr01qldb7frtg0d7vfunpr01qldb7frtgg')

    # Model hyperparameters
    LSTM_UNITS = [50, 50, 50]
    DROPOUT_RATE = 0.2
    EPOCHS = 50
    BATCH_SIZE = 32

    # Technical indicators
    TECHNICAL_INDICATORS = [
        'SMA_20', 'SMA_50', 'EMA_20', 'RSI', 'MACD',
        'BB_upper', 'BB_lower', 'Volume_SMA'
    ]

    def __init__(self):
        for path in (self.DATA_RAW_PATH, self.DATA_PROCESSED_PATH, self.MODELS_PATH):
            os.makedirs(path, exist_ok=True)

