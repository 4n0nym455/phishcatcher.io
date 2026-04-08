"""
Phishing Detector Module

This module provides the main ML-based phishing detection functionality.
It uses XGBoost as the primary classifier with support for model training,
prediction, and persistence.
"""

import os
import json
import pickle
import logging
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
import numpy as np

from app.config import get_settings
from app.ml.feature_extractor import FeatureExtractor
from app.ml.models.bert_model import BERTClassifier
from app.ml.models.classical import ClassicalMLTrainer


def convert_numpy_types(obj):
    """Convert numpy types to native Python types for MongoDB serialization."""
    if isinstance(obj, np.floating):
        return float(obj)
    elif isinstance(obj, np.integer):
        return int(obj)
    elif isinstance(obj, np.bool_):
        return bool(obj)
    elif isinstance(obj, dict):
        return {k: convert_numpy_types(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [convert_numpy_types(i) for i in obj]
    elif isinstance(obj, np.ndarray):
        return obj.tolist()
    return obj

logger = logging.getLogger(__name__)

# Try to import XGBoost, fallback to sklearn if not available
try:
    import xgboost as xgb
    XGBOOST_AVAILABLE = True
except ImportError:
    XGBOOST_AVAILABLE = False
    from sklearn.ensemble import RandomForestClassifier
    logger.warning("XGBoost not available, using RandomForest as fallback")


class PhishingDetector:
    """
    ML-based phishing detector using XGBoost or RandomForest.
    
    This class handles:
    - Model loading and initialization
    - Prediction on email features
    - Model training and evaluation
    - Model persistence
    """
    
    def __init__(self, model_path: Optional[str] = None):
        """
        Initialize the phishing detector.
        
        Args:
            model_path: Path to saved model file (optional)
        """
        self.settings = get_settings()
        self.model_path = model_path or self.settings.ML_MODEL_PATH
        self.feature_extractor = FeatureExtractor()
        self.model = None
        self.model_version = self.settings.ML_MODEL_VERSION
        self.training_metadata = {}
        
        # Load model if exists
        self._load_model()
    
    def _load_model(self):
        """Load model from disk or initialize new model."""
        if os.path.exists(self.model_path):
            try:
                with open(self.model_path, 'rb') as f:
                    saved_data = pickle.load(f)
                    
                # Handle different model formats
                if isinstance(saved_data, dict):
                    self.model = saved_data.get('model')
                    self.training_metadata = saved_data.get('metadata', {})
                    self.model_version = saved_data.get('version', self.model_version)
                else:
                    # Legacy format - just the model
                    self.model = saved_data
                    self.training_metadata = {}
                    self.model_version = "legacy"
                    
                if self.model is not None:
                    logger.info(f"Loaded model version {self.model_version} from {self.model_path}")
                else:
                    logger.warning("Model file exists but contains no model data")
                    self._init_new_model()
                    
            except Exception as e:
                logger.error(f"Error loading model: {e}")
                self._init_new_model()
        else:
            logger.warning(f"Model file not found at {self.model_path}, initializing new model")
            self._init_new_model()
    
    def _init_new_model(self):
        """Initialize a new untrained model."""
        if XGBOOST_AVAILABLE:
            self.model = xgb.XGBClassifier(
                n_estimators=100,
                max_depth=6,
                learning_rate=0.1,
                subsample=0.8,
                colsample_bytree=0.8,
                objective='binary:logistic',
                eval_metric='logloss',
                random_state=42,
                use_label_encoder=False
            )
        else:
            self.model = RandomForestClassifier(
                n_estimators=100,
                max_depth=10,
                random_state=42,
                n_jobs=-1
            )
        logger.info("Initialized new model")
    
    def is_trained(self) -> bool:
        """Check if model has been trained."""
        if self.model is None:
            return False
        
        # Check if model has been fitted
        if hasattr(self.model, 'booster'):
            return True
        if hasattr(self.model, 'n_features_in_'):
            return True
        return False
    
    def predict(self, parsed_email: Dict[str, Any]) -> Dict[str, Any]:
        """
        Predict phishing probability for an email.
        
        Args:
            parsed_email: Parsed email data from EmailParser
            
        Returns:
            Dictionary with prediction results
        """
        if not self.is_trained():
            logger.warning("Model not trained, returning fallback prediction")
            return self._fallback_prediction(parsed_email)
        
        # Extract features
        features = self.feature_extractor.get_feature_vector(parsed_email)
        X = np.array([features])
        
        try:
            # Get prediction probability
            if hasattr(self.model, 'predict_proba'):
                probabilities = self.model.predict_proba(X)[0]
                phishing_prob = probabilities[1]  # Probability of phishing class
                logger.info(f"ML prediction - phishing probability: {phishing_prob:.4f}")
            else:
                # Fallback for models without predict_proba
                prediction = self.model.predict(X)[0]
                phishing_prob = float(prediction)
                logger.info(f"ML prediction - binary result: {prediction}")
            
            # Determine category based on probability
            category = self._categorize_prediction(phishing_prob)
            
            prediction_result = {
                'is_phishing': phishing_prob > 0.5,
                'phishing_probability': float(phishing_prob),
                'safe_probability': float(1 - phishing_prob),
                'category': category,
                'confidence': abs(phishing_prob - 0.5) * 2,  # Scale to 0-1
                'model_version': self.model_version,
                'features_used': len(features)
            }
            
            logger.info(f"ML prediction complete - category: {category}, confidence: {prediction_result['confidence']:.4f}")
            
            # Convert numpy types to native Python types
            return convert_numpy_types(prediction_result)
        except Exception as e:
            logger.error(f"Prediction error: {e}")
            return self._fallback_prediction(parsed_email)
    
    def predict_batch(self, parsed_emails: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Predict phishing probability for multiple emails.
        
        Args:
            parsed_emails: List of parsed email data
            
        Returns:
            List of prediction results
        """
        return [self.predict(email) for email in parsed_emails]
    
    def _fallback_prediction(self, parsed_email: Dict[str, Any]) -> Dict[str, Any]:
        """
        Fallback prediction when model is not available.
        Uses rule-based heuristics.
        """
        features = self.feature_extractor.extract_features(parsed_email)
        
        # Simple heuristic scoring
        score = 0.0
        indicators = 0
        
        # Authentication failures
        if features.get('spf_fail', 0) > 0:
            score += 0.2
            indicators += 1
        if features.get('dkim_fail', 0) > 0:
            score += 0.15
            indicators += 1
        if features.get('dmarc_fail', 0) > 0:
            score += 0.15
            indicators += 1
        
        # Reply-to mismatch
        if features.get('reply_to_mismatch', 0) > 0:
            score += 0.1
            indicators += 1
        
        # Suspicious links
        if features.get('suspicious_links_ratio', 0) > 0.3:
            score += 0.2
            indicators += 1
        
        # Urgency keywords
        if features.get('urgency_keywords_count', 0) > 2:
            score += 0.1
            indicators += 1
        
        # Executable attachments
        if features.get('executable_attachments', 0) > 0:
            score += 0.3
            indicators += 1
        
        # Normalize score
        score = min(score, 1.0)
        
        return {
            'is_phishing': score > 0.5,
            'phishing_probability': score,
            'safe_probability': 1 - score,
            'category': self._categorize_prediction(score),
            'confidence': 0.5,  # Low confidence for fallback
            'model_version': 'fallback',
            'features_used': len(features),
            'heuristic_indicators': indicators
        }
    
    def _categorize_prediction(self, probability: float) -> str:
        """
        Categorize prediction based on probability.
        
        Args:
            probability: Phishing probability (0-1)
            
        Returns:
            Category string
        """
        if probability >= 0.9:
            return 'phishing'
        elif probability >= 0.7:
            return 'suspicious'
        elif probability >= 0.5:
            return 'likely_phishing'
        elif probability >= 0.3:
            return 'low_risk'
        else:
            return 'safe'
    
    def train(self, X: np.ndarray, y: np.ndarray, 
              validation_split: float = 0.2) -> Dict[str, Any]:
        """
        Train the model on labeled data.
        
        Args:
            X: Feature matrix
            y: Labels (0 for safe, 1 for phishing)
            validation_split: Fraction of data for validation
            
        Returns:
            Training metrics
        """
        from sklearn.model_selection import train_test_split
        from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, roc_auc_score
        
        # Split data
        X_train, X_val, y_train, y_val = train_test_split(
            X, y, test_size=validation_split, random_state=42, stratify=y
        )
        
        logger.info(f"Training on {len(X_train)} samples, validating on {len(X_val)} samples")
        
        # Train model
        if XGBOOST_AVAILABLE:
            self.model.fit(
                X_train, y_train,
                eval_set=[(X_val, y_val)],
                verbose=False
            )
        else:
            self.model.fit(X_train, y_train)
        
        # Evaluate
        y_pred = self.model.predict(X_val)
        y_prob = self.model.predict_proba(X_val)[:, 1] if hasattr(self.model, 'predict_proba') else y_pred
        
        metrics = {
            'accuracy': accuracy_score(y_val, y_pred),
            'precision': precision_score(y_val, y_pred, zero_division=0),
            'recall': recall_score(y_val, y_pred, zero_division=0),
            'f1_score': f1_score(y_val, y_pred, zero_division=0),
            'roc_auc': roc_auc_score(y_val, y_prob) if len(np.unique(y_val)) > 1 else 0.5,
            'training_samples': len(X_train),
            'validation_samples': len(X_val)
        }
        
        # Convert numpy types to native Python types
        metrics = convert_numpy_types(metrics)
        
        # Store training metadata
        self.training_metadata = {
            'trained_at': datetime.utcnow().isoformat(),
            'metrics': metrics,
            'feature_names': self.feature_extractor.feature_names,
            'validation_split': validation_split
        }
        
        logger.info(f"Training completed. Accuracy: {metrics['accuracy']:.4f}, F1: {metrics['f1_score']:.4f}")
        
        return metrics
    
    def save_model(self, path: Optional[str] = None):
        """
        Save model to disk.
        
        Args:
            path: Save path (optional, uses default if not provided)
        """
        save_path = path or self.model_path
        
        # Ensure directory exists
        os.makedirs(os.path.dirname(save_path), exist_ok=True)
        
        # Save model and metadata
        save_data = {
            'model': self.model,
            'version': self.model_version,
            'metadata': self.training_metadata
        }
        
        with open(save_path, 'wb') as f:
            pickle.dump(save_data, f)
        
        logger.info(f"Model saved to {save_path}")
    
    def get_feature_importance(self) -> Dict[str, float]:
        """
        Get feature importance from the model.
        
        Returns:
            Dictionary mapping feature names to importance scores
        """
        if not self.is_trained():
            return {}
        
        try:
            if hasattr(self.model, 'feature_importances_'):
                importances = self.model.feature_importances_
            elif hasattr(self.model, 'get_booster'):
                importances = self.model.get_booster().get_score(importance_type='gain')
                # Convert to array format
                importances = [importances.get(f'f{i}', 0) for i in range(len(self.feature_extractor.feature_names))]
            else:
                return {}
            
            return dict(zip(self.feature_extractor.feature_names, importances))
        except Exception as e:
            logger.error(f"Error getting feature importance: {e}")
            return {}
    
    def get_model_info(self) -> Dict[str, Any]:
        """
        Get model information.
        
        Returns:
            Dictionary with model information
        """
        return {
            'version': self.model_version,
            'is_trained': self.is_trained(),
            'model_type': 'xgboost' if XGBOOST_AVAILABLE else 'random_forest',
            'feature_count': len(self.feature_extractor.feature_names),
            'training_metadata': self.training_metadata
        }


# Singleton instance
_detector_instance: Optional[PhishingDetector] = None


def get_phishing_detector() -> PhishingDetector:
    """Get singleton instance of phishing detector."""
    global _detector_instance
    if _detector_instance is None:
        _detector_instance = PhishingDetector()
    return _detector_instance
