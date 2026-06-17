import numpy as np
from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor
from sklearn.svm import SVR
from sklearn.linear_model import LinearRegression
from sklearn.model_selection import GridSearchCV
import joblib
import logging
import os

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class EnsemblePredictor:
    """
    Ensemble predictor with RandomForest, XGBoost, and LightGBM.

    Architecture:
    - Base models: RF, XGBoost, LightGBM (each trained independently)
    - Meta model: RandomForest stacking ensemble
    - Optional ensemble averaging for robustness

    This replaces older SVR/LR models with more powerful tree-based models.
    """

    def __init__(self, config):
        self.config = config
        self.models = {}
        self.meta_model = None
        self.ensemble_weights = None

    def _check_xgboost_available(self):
        """Check if XGBoost is available."""
        try:
            import xgboost
            return True
        except ImportError:
            return False

    def _check_lightgbm_available(self):
        """Check if LightGBM is available."""
        try:
            import lightgbm
            return True
        except ImportError:
            return False

    def initialize_models(self):
        """Initialize base models for ensemble - RF, XGBoost, LightGBM"""
        self.models = {}

        # RandomForest - robust baseline
        self.models['rf'] = RandomForestRegressor(
            n_estimators=200,
            max_depth=15,
            min_samples_split=5,
            min_samples_leaf=2,
            max_features='sqrt',
            bootstrap=True,
            oob_score=True,
            n_jobs=-1,
            random_state=self.config.RANDOM_STATE
        )
        logger.info("[ENSEMBLE] RandomForest initialized (n_estimators=200, max_depth=15)")

        # XGBoost - powerful gradient boosting (if available)
        if self._check_xgboost_available():
            import xgboost as xgb
            self.models['xgb'] = xgb.XGBRegressor(
                n_estimators=300,
                max_depth=6,
                learning_rate=0.05,
                subsample=0.8,
                colsample_bytree=0.8,
                min_child_weight=3,
                gamma=0.1,
                reg_alpha=0.1,
                reg_lambda=1.0,
                random_state=self.config.RANDOM_STATE,
                n_jobs=-1,
                verbosity=0,
                early_stopping_rounds=30
            )
            logger.info("[ENSEMBLE] XGBoost initialized (n_estimators=300, max_depth=6)")
        else:
            logger.warning("[ENSEMBLE] XGBoost not available - using GradientBoosting fallback")
            self.models['gbr'] = GradientBoostingRegressor(
                n_estimators=150,
                max_depth=6,
                learning_rate=0.05,
                random_state=self.config.RANDOM_STATE
            )

        # LightGBM - fast and efficient (if available)
        if self._check_lightgbm_available():
            import lightgbm as lgb
            self.models['lgb'] = lgb.LGBMRegressor(
                n_estimators=300,
                max_depth=8,
                learning_rate=0.05,
                num_leaves=31,
                subsample=0.8,
                colsample_bytree=0.8,
                min_child_samples=20,
                reg_alpha=0.1,
                reg_lambda=1.0,
                random_state=self.config.RANDOM_STATE,
                n_jobs=-1,
                verbosity=-1
            )
            logger.info("[ENSEMBLE] LightGBM initialized (n_estimators=300, max_depth=8)")
        else:
            logger.warning("[ENSEMBLE] LightGBM not available - skipping")

        # Legacy models for backward compatibility
        self.models['svr'] = SVR(kernel='rbf', C=100, gamma=0.1)
        self.models['lr'] = LinearRegression()

    def train_base_models(self, X_train, y_train, X_val=None, y_val=None):
        """Train base models with early stopping for XGB/LGB"""
        self.initialize_models()

        trained_models = []

        for name, model in self.models.items():
            if name in ['svr', 'lr']:
                # SVR and LR are fast, train directly
                logger.info(f"Training {name} model...")
                model.fit(X_train, y_train)
                trained_models.append(name)
            elif name in ['xgb', 'lgb'] and X_val is not None:
                # XGB and LGB with early stopping
                logger.info(f"Training {name} model with early stopping...")
                if name == 'xgb':
                    model.fit(X_train, y_train, eval_set=[(X_val, y_val)], verbose=False)
                elif name == 'lgb':
                    import lightgbm as lgb_module
                    model.fit(X_train, y_train, eval_set=[(X_val, y_val)],
                             callbacks=[lgb_module.early_stopping(30, verbose=False)])
                trained_models.append(name)
            else:
                # RF and GBR
                logger.info(f"Training {name} model...")
                model.fit(X_train, y_train)
                trained_models.append(name)

            self.models[name] = model

        logger.info(f"[ENSEMBLE] Trained base models: {trained_models}")

    def train_meta_model(self, X_train, y_train):
        """Train meta model using predictions from base models"""
        # Get predictions from base models
        base_predictions = self.get_base_predictions(X_train)

        # Train meta model (using Random Forest as meta-learner)
        self.meta_model = RandomForestRegressor(
            n_estimators=100,
            max_depth=10,
            random_state=self.config.RANDOM_STATE
        )
        self.meta_model.fit(base_predictions, y_train)

        logger.info("[ENSEMBLE] Meta model training completed")

    def get_base_predictions(self, X):
        """Get predictions from all base models"""
        predictions = []
        for name, model in self.models.items():
            if name not in ['meta']:
                pred = model.predict(X).reshape(-1, 1)
                predictions.append(pred)
        return np.hstack(predictions)

    def predict(self, X):
        """Make ensemble predictions using meta model or averaging"""
        # Get base predictions
        base_predictions = self.get_base_predictions(X)

        if self.meta_model is not None:
            # Use meta model (stacking)
            final_predictions = self.meta_model.predict(base_predictions)
        else:
            # Fallback to weighted average of available models
            rf_pred = self.models.get('rf', self.models.get('gbr'))
            xgb_pred = self.models.get('xgb')
            lgb_pred = self.models.get('lgb')

            preds = []
            weights = []

            if rf_pred is not None:
                preds.append(rf_pred.predict(X))
                weights.append(0.3)

            if xgb_pred is not None:
                preds.append(xgb_pred.predict(X))
                weights.append(0.4)

            if lgb_pred is not None:
                preds.append(lgb_pred.predict(X))
                weights.append(0.3)

            if preds:
                # Normalize weights
                weights = np.array(weights) / sum(weights)
                final_predictions = sum(w * p for w, p in zip(weights, preds))
            else:
                final_predictions = np.zeros(len(X))

        return final_predictions

    def predict_with_confidence(self, X):
        """Make predictions with confidence scores based on model agreement"""
        predictions = []
        for name, model in self.models.items():
            if name not in ['meta', 'svr', 'lr']:
                predictions.append(model.predict(X))

        if len(predictions) >= 2:
            predictions = np.array(predictions)
            mean_pred = predictions.mean(axis=0)
            std_pred = predictions.std(axis=0)

            # Confidence is inverse of std (lower std = higher confidence)
            max_std = predictions.std(axis=1).max() + 1e-10
            confidence = 100 * (1 - std_pred / max_std)

            return mean_pred, confidence
        elif predictions:
            return predictions[0], np.ones(len(predictions[0])) * 75
        else:
            return np.zeros(len(X)), np.zeros(len(X))

    def get_feature_importance(self):
        """Get aggregated feature importance from all models"""
        importance = {}

        for name, model in self.models.items():
            if name == 'xgb' and hasattr(model, 'feature_importances_'):
                for feat, imp in zip(['rf', 'xgb', 'lgb'], ['rf', 'xgb', 'lgb']):
                    pass
            elif hasattr(model, 'feature_importances_'):
                imp_dict = dict(zip(range(len(model.feature_importances_)),
                                   model.feature_importances_))
                for feat_idx, imp in imp_dict.items():
                    if feat_idx not in importance:
                        importance[feat_idx] = []
                    importance[feat_idx].append(imp)

        # Average importance across models
        avg_importance = {k: sum(v) / len(v) for k, v in importance.items()}
        return avg_importance

    def save_models(self, path):
        """Save all models"""
        for name, model in self.models.items():
            if model is not None:
                try:
                    joblib.dump(model, f"{path}/{name}_model.pkl")
                    logger.info(f"[ENSEMBLE] Saved {name} model to {path}")
                except Exception as e:
                    logger.warning(f"[ENSEMBLE] Failed to save {name}: {e}")

        if self.meta_model is not None:
            joblib.dump(self.meta_model, f"{path}/meta_model.pkl")
            logger.info(f"[ENSEMBLE] Saved meta model to {path}")

    def load_models(self, path):
        """Load all models"""
        self.models = {}

        # Load RF (primary model)
        rf_path = f"{path}/rf_model.pkl"
        if os.path.exists(rf_path):
            self.models['rf'] = joblib.load(rf_path)
            logger.info(f"[ENSEMBLE] Loaded RF model from {rf_path}")

        # Load XGBoost if available
        xgb_path = f"{path}/xgb_model.pkl"
        if os.path.exists(xgb_path):
            try:
                self.models['xgb'] = joblib.load(xgb_path)
                logger.info(f"[ENSEMBLE] Loaded XGBoost model from {xgb_path}")
            except Exception as e:
                logger.warning(f"[ENSEMBLE] Failed to load XGBoost: {e}")

        # Load LightGBM if available
        lgb_path = f"{path}/lgb_model.pkl"
        if os.path.exists(lgb_path):
            try:
                self.models['lgb'] = joblib.load(lgb_path)
                logger.info(f"[ENSEMBLE] Loaded LightGBM model from {lgb_path}")
            except Exception as e:
                logger.warning(f"[ENSEMBLE] Failed to load LightGBM: {e}")

        # Load legacy models for compatibility
        for name in ['gbr', 'svr', 'lr']:
            model_path = f"{path}/{name}_model.pkl"
            if os.path.exists(model_path):
                self.models[name] = joblib.load(model_path)

        # Load meta model
        meta_path = f"{path}/meta_model.pkl"
        if os.path.exists(meta_path):
            self.meta_model = joblib.load(meta_path)
            logger.info(f"[ENSEMBLE] Loaded meta model from {meta_path}")

