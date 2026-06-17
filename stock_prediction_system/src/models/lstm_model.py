import numpy as np
import tensorflow as tf
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import LSTM, Dense, Dropout, Bidirectional
from tensorflow.keras.callbacks import EarlyStopping, ModelCheckpoint
from sklearn.preprocessing import MinMaxScaler
import joblib
import os
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class LSTMPredictor:
    def __init__(self, config):
        self.config = config
        self.model = None
        self.scaler = MinMaxScaler()
        self.sequence_length = config.SEQUENCE_LENGTH
        
    def create_sequences(self, data, target_col_idx=0):
        """Create sequences for LSTM input"""
        X, y = [], []
        for i in range(self.sequence_length, len(data)):
            X.append(data[i-self.sequence_length:i])
            y.append(data[i, target_col_idx])
        return np.array(X), np.array(y)
    
    def build_model(self, input_shape):
        """Build LSTM model architecture"""
        model = Sequential()
        
        # First LSTM layer
        model.add(Bidirectional(
            LSTM(self.config.LSTM_UNITS[0], return_sequences=True),
            input_shape=input_shape
        ))
        model.add(Dropout(self.config.DROPOUT_RATE))
        
        # Second LSTM layer
        model.add(Bidirectional(
            LSTM(self.config.LSTM_UNITS[1], return_sequences=True)
        ))
        model.add(Dropout(self.config.DROPOUT_RATE))
        
        # Third LSTM layer
        model.add(LSTM(self.config.LSTM_UNITS[2]))
        model.add(Dropout(self.config.DROPOUT_RATE))
        
        # Dense layers
        model.add(Dense(32, activation='relu'))
        model.add(Dense(16, activation='relu'))
        model.add(Dense(1))
        
        # Compile model
        model.compile(
            optimizer='adam',
            loss='mse',
            metrics=['mae', 'mape']
        )
        
        return model
    
    def train(self, X_train, y_train, X_val, y_val, model_path):
        """Train the LSTM model"""
        try:
            # Build model
            input_shape = (X_train.shape[1], X_train.shape[2])
            self.model = self.build_model(input_shape)
            
            # Callbacks
            early_stopping = EarlyStopping(
                monitor='val_loss',
                patience=10,
                restore_best_weights=True
            )
            
            checkpoint = ModelCheckpoint(
                model_path,
                monitor='val_loss',
                save_best_only=True,
                mode='min'
            )
            
            # Train model
            history = self.model.fit(
                X_train, y_train,
                validation_data=(X_val, y_val),
                epochs=self.config.EPOCHS,
                batch_size=self.config.BATCH_SIZE,
                callbacks=[early_stopping, checkpoint],
                verbose=1
            )
            
            logger.info("Model training completed")
            return history
            
        except Exception as e:
            logger.error(f"Error training model: {e}")
            raise
    
    def predict(self, X):
        """Make predictions"""
        if self.model is None:
            raise ValueError("Model not loaded. Please load or train a model first.")
        
        predictions = self.model.predict(X)
        return predictions

    def load_model(self, path):
        """Load a saved Keras model from disk."""
        self.model = tf.keras.models.load_model(path)
        logger.info(f"Model loaded from {path}")
        return self.model
    
    def save_scaler(self, path):
        """Save the scaler"""
        joblib.dump(self.scaler, path)
        logger.info(f"Scaler saved to {path}")
    
    def load_scaler(self, path):
        """Load the scaler"""
        self.scaler = joblib.load(path)
        logger.info(f"Scaler loaded from {path}")

