import numpy as np
import pandas as pd
from sklearn.preprocessing import MinMaxScaler
from sklearn.model_selection import train_test_split
import os
from datetime import datetime
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class StockPredictor:
    def __init__(self, config, lstm_model, ensemble_model, feature_engineer):
        self.config = config
        self.lstm_model = lstm_model
        self.ensemble_model = ensemble_model
        self.feature_engineer = feature_engineer
        self.scaler = MinMaxScaler()
        
    def prepare_data_for_training(self, df, news_sentiment=None):
        """Prepare data for model training"""
        # Add features
        df = self.feature_engineer.prepare_features(df, news_sentiment)
        
        # Select features for training
        feature_columns = [col for col in df.columns if col != 'close']
        target_column = 'close'
        
        X = df[feature_columns].values
        y = df[target_column].values
        
        # Scale features
        X_scaled = self.scaler.fit_transform(X)
        self.lstm_model.scaler = self.scaler
        
        # Split data
        X_train, X_test, y_train, y_test = train_test_split(
            X_scaled, y, test_size=self.config.TEST_SIZE, 
            shuffle=False, random_state=self.config.RANDOM_STATE
        )
        
        return X_train, X_test, y_train, y_test, feature_columns

    def _get_loaded_scaler(self):
        """Reuse the fitted scaler from training or a previously loaded model."""
        if hasattr(self.scaler, 'n_features_in_'):
            return self.scaler
        if hasattr(self.lstm_model.scaler, 'n_features_in_'):
            self.scaler = self.lstm_model.scaler
            return self.scaler
        raise ValueError("Scaler is not fitted. Train or load a saved model first.")

    def _baseline_prediction(self, df):
        """Fallback prediction used when trained models are unavailable."""
        closes = df['close'].dropna()
        if closes.empty:
            raise ValueError("No closing prices available for prediction.")

        current_price = float(closes.iloc[-1])
        recent_returns = closes.pct_change().dropna().tail(5)
        intraday_moves = pd.Series(dtype=float)
        if 'open' in df.columns:
            intraday_moves = ((df['close'] - df['open']) / df['open']).replace([np.inf, -np.inf], np.nan).dropna().tail(5)

        avg_return = float(recent_returns.mean()) if not recent_returns.empty else 0.0
        avg_intraday = float(intraday_moves.mean()) if not intraday_moves.empty else 0.0
        combined_move = np.clip((avg_return * 0.7) + (avg_intraday * 0.3), -0.05, 0.05)
        return current_price * (1 + float(combined_move))

    def _recent_move_limit(self, df):
        """Estimate a reasonable next-day move limit from recent history."""
        closes = df['close'].dropna()
        if closes.empty:
            return 0.08

        daily_moves = closes.pct_change().abs().dropna().tail(10)
        intraday_moves = pd.Series(dtype=float)
        if 'open' in df.columns:
            intraday_moves = (
                ((df['close'] - df['open']) / df['open'])
                .abs()
                .replace([np.inf, -np.inf], np.nan)
                .dropna()
                .tail(10)
            )

        observed_move = 0.0
        if not daily_moves.empty:
            observed_move = max(observed_move, float(daily_moves.median()))
        if not intraday_moves.empty:
            observed_move = max(observed_move, float(intraday_moves.median()))

        # Typical next-day moves should stay near recent behavior, but allow room.
        return float(np.clip((observed_move * 3.0) + 0.01, 0.04, 0.12))

    def _sanitize_prediction(self, raw_prediction, df):
        """Reject implausible model outputs and fall back to a recent-price baseline."""
        baseline_prediction = float(self._baseline_prediction(df))
        current_price = float(df['close'].dropna().iloc[-1])
        move_limit = self._recent_move_limit(df)

        if raw_prediction is None or not np.isfinite(raw_prediction) or raw_prediction <= 0:
            logger.warning("Invalid model output detected; using baseline prediction.")
            return baseline_prediction

        deviation = abs(float(raw_prediction) - current_price) / current_price if current_price else 0.0
        if deviation > move_limit:
            logger.warning(
                "Implausible model output %.2f rejected for current price %.2f; using baseline %.2f instead.",
                raw_prediction,
                current_price,
                baseline_prediction
            )
            return baseline_prediction

        return float(raw_prediction)
    
    def train_models(self, df, news_sentiment=None):
        """Train both LSTM and ensemble models"""
        # Prepare data
        X_train, X_test, y_train, y_test, feature_columns = self.prepare_data_for_training(df, news_sentiment)
        
        # Prepare sequences for LSTM
        X_train_lstm, y_train_lstm = self.lstm_model.create_sequences(
            np.column_stack([X_train, y_train]), 
            target_col_idx=X_train.shape[1]
        )
        
        X_test_lstm, y_test_lstm = self.lstm_model.create_sequences(
            np.column_stack([X_test, y_test]), 
            target_col_idx=X_test.shape[1]
        )
        
        # Train LSTM
        logger.info("Training LSTM model...")
        lstm_path = os.path.join(self.config.MODELS_PATH, 'lstm_model.h5')
        self.lstm_model.train(X_train_lstm, y_train_lstm, X_test_lstm, y_test_lstm, lstm_path)
        
        # Train ensemble model (using non-sequential data)
        logger.info("Training ensemble model...")
        self.ensemble_model.train_base_models(X_train, y_train)
        self.ensemble_model.train_meta_model(X_train, y_train)
        
        # Save scaler
        scaler_path = os.path.join(self.config.MODELS_PATH, 'scaler.pkl')
        self.lstm_model.save_scaler(scaler_path)
        
        # Save ensemble models
        ensemble_path = os.path.join(self.config.MODELS_PATH, 'ensemble')
        os.makedirs(ensemble_path, exist_ok=True)
        self.ensemble_model.save_models(ensemble_path)
        
        logger.info("All models trained and saved successfully")
        
        return {
            'lstm_model_path': lstm_path,
            'ensemble_model_path': ensemble_path,
            'scaler_path': scaler_path
        }
    
    def predict_next_day(self, df, news_sentiment=None, use_ensemble=True):
        """Predict next day's closing price"""
        try:
            # Prepare features for the latest data point
            df_features = self.feature_engineer.prepare_features(df, news_sentiment)
            if len(df_features) < self.config.SEQUENCE_LENGTH:
                return float(self._baseline_prediction(df))
            
            # Get the latest sequence for LSTM
            latest_features = df_features.iloc[-self.config.SEQUENCE_LENGTH:].values
            
            # Scale features
            latest_scaled = self._get_loaded_scaler().transform(latest_features)
            
            if use_ensemble and self.ensemble_model.meta_model is not None and self.ensemble_model.models:
                # Use ensemble model for prediction
                latest_features_flat = latest_scaled[-1].reshape(1, -1)
                prediction = self.ensemble_model.predict(latest_features_flat)
                raw_prediction = float(np.asarray(prediction).ravel()[0])
                return self._sanitize_prediction(raw_prediction, df)

            if self.lstm_model.model is not None:
                # Use LSTM model
                latest_sequence = latest_scaled.reshape(1, self.config.SEQUENCE_LENGTH, -1)
                prediction = self.lstm_model.predict(latest_sequence)
                raw_prediction = float(np.asarray(prediction).ravel()[0])
                return self._sanitize_prediction(raw_prediction, df)

            return float(self._baseline_prediction(df))
            
        except Exception as e:
            logger.warning(f"Falling back to baseline prediction: {e}")
            return float(self._baseline_prediction(df))
    
    def predict_future_days(self, df, days=5, news_sentiment=None):
        """Predict multiple days into the future"""
        predictions = []
        current_df = df.copy()
        
        for day in range(days):
            next_day_pred = self.predict_next_day(current_df, news_sentiment)
            predictions.append(next_day_pred)
            
            # Add prediction to dataframe for next iteration
            last_row = current_df.iloc[-1].copy()
            last_row['close'] = next_day_pred
            next_index = current_df.index[-1] + pd.Timedelta(days=1)
            next_frame = pd.DataFrame([last_row], index=[next_index])
            current_df = pd.concat([current_df, next_frame])
        
        return predictions
    
    def calculate_accuracy_metrics(self, df, news_sentiment=None):
        """Calculate model accuracy metrics"""
        # Prepare data
        X_train, X_test, y_train, y_test, _ = self.prepare_data_for_training(df, news_sentiment)
        
        # Make predictions on test set
        predictions = self.ensemble_model.predict(X_test)
        
        # Calculate metrics
        mae = np.mean(np.abs(predictions - y_test))
        mape = np.mean(np.abs((y_test - predictions) / y_test)) * 100
        rmse = np.sqrt(np.mean((predictions - y_test) ** 2))
        
        # Calculate direction accuracy
        actual_direction = np.sign(np.diff(y_test))
        pred_direction = np.sign(np.diff(predictions))
        direction_accuracy = np.mean(actual_direction == pred_direction) * 100
        
        return {
            'mae': mae,
            'mape': mape,
            'rmse': rmse,
            'direction_accuracy': direction_accuracy
        }

