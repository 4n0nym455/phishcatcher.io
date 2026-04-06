"""
Text Classifier Module

This module provides TF-IDF based text classification for phishing detection.
It uses TF-IDF vectorization combined with XGBoost or RandomForest classifier
to analyze email subject and body text.
"""

import os
import json
import pickle
import logging
from typing import List, Dict, Any, Optional, Tuple
import numpy as np

from app.config import get_settings

logger = logging.getLogger(__name__)

try:
    import xgboost as xgb
    XGBOOST_AVAILABLE = True
except ImportError:
    XGBOOST_AVAILABLE = False
    from sklearn.ensemble import RandomForestClassifier
    logger.warning("XGBoost not available, using RandomForest as fallback")

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.model_selection import train_test_split
from sklearn.metrics import (
    accuracy_score, precision_score, recall_score, 
    f1_score, roc_auc_score
)


class TextClassifier:
    """
    TF-IDF based text classifier for phishing detection.
    
    This classifier analyzes email subject and body text to detect phishing.
    Uses TF-IDF vectorization with n-grams for feature extraction.
    """
    
    DEFAULT_MAX_FEATURES = 10000
    DEFAULT_NGRAM_RANGE = (1, 2)
    DEFAULT_MIN_DF = 2
    DEFAULT_MAX_DF = 0.95
    
    def __init__(
        self,
        max_features: int = DEFAULT_MAX_FEATURES,
        ngram_range: Tuple[int, int] = DEFAULT_NGRAM_RANGE,
        min_df: int = DEFAULT_MIN_DF,
        max_df: float = DEFAULT_MAX_DF
    ):
        """
        Initialize text classifier.
        
        Args:
            max_features: Maximum number of TF-IDF features
            ngram_range: N-gram range for TF-IDF
            min_df: Minimum document frequency
            max_df: Maximum document frequency
        """
        self.settings = get_settings()
        
        self.max_features = max_features
        self.ngram_range = ngram_range
        self.min_df = min_df
        self.max_df = max_df
        
        self.vectorizer: Optional[TfidfVectorizer] = None
        self.model: Optional[Any] = None
        self.is_trained = False
        self.training_metadata: Dict[str, Any] = {}
        
        self._load_model()
    
    def _load_model(self):
        """Load saved model and vectorizer."""
        vectorizer_path = self.settings.TFIDF_VECTORIZER_PATH
        model_path = self.settings.TEXT_CLASSIFIER_PATH
        
        try:
            if os.path.exists(vectorizer_path):
                with open(vectorizer_path, 'rb') as f:
                    self.vectorizer = pickle.load(f)
                logger.info(f"Loaded vectorizer from {vectorizer_path}")
            else:
                self._init_new_model()
            
            if os.path.exists(model_path):
                with open(model_path, 'rb') as f:
                    saved_data = pickle.load(f)
                    self.model = saved_data.get('model')
                    self.training_metadata = saved_data.get('metadata', {})
                    self.is_trained = saved_data.get('is_trained', False)
                logger.info(f"Loaded text classifier from {model_path}")
            else:
                self._init_new_model()
        except Exception as e:
            logger.warning(f"Could not load text classifier: {e}")
            self._init_new_model()
    
    def _init_new_model(self):
        """Initialize new untrained model and vectorizer."""
        self.vectorizer = TfidfVectorizer(
            max_features=self.max_features,
            ngram_range=self.ngram_range,
            min_df=self.min_df,
            max_df=self.max_df,
            sublinear_tf=True,
            strip_accents='unicode',
            lowercase=True
        )
        
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
                use_label_encoder=False,
                verbosity=0
            )
        else:
            self.model = RandomForestClassifier(
                n_estimators=100,
                max_depth=10,
                random_state=42,
                n_jobs=-1
            )
        
        logger.info("Initialized new text classifier")
    
    def prepare_text(self, subject: str, body: str) -> str:
        """
        Combine subject and body for classification.
        
        Args:
            subject: Email subject
            body: Email body
            
        Returns:
            Combined text string
        """
        subject = subject or ""
        body = body or ""
        
        combined = f"{subject} {body}"
        
        combined = combined.replace('\n', ' ')
        combined = combined.replace('\r', ' ')
        
        while '  ' in combined:
            combined = combined.replace('  ', ' ')
        
        return combined.strip()
    
    def train(
        self,
        subjects: List[str],
        bodies: List[str],
        labels: List[int],
        validation_split: float = 0.2
    ) -> Dict[str, Any]:
        """
        Train the text classifier.
        
        Args:
            subjects: List of email subjects
            bodies: List of email bodies
            labels: List of labels (1=phishing, 0=legitimate)
            validation_split: Fraction for validation
            
        Returns:
            Training metrics
        """
        logger.info(f"Training text classifier on {len(labels)} samples")
        
        texts = [self.prepare_text(s, b) for s, b in zip(subjects, bodies)]
        
        X_text = self.vectorizer.fit_transform(texts)
        
        X_train, X_val, y_train, y_val = train_test_split(
            X_text, labels, 
            test_size=validation_split, 
            random_state=42, 
            stratify=labels
        )
        
        logger.info(f"Training on {X_train.shape[0]} samples, validating on {X_val.shape[0]}")
        
        if XGBOOST_AVAILABLE:
            self.model.fit(
                X_train, y_train,
                eval_set=[(X_val, y_val)],
                verbose=False
            )
        else:
            self.model.fit(X_train, y_train)
        
        y_pred = self.model.predict(X_val)
        y_prob = self.model.predict_proba(X_val)[:, 1] if hasattr(self.model, 'predict_proba') else y_pred
        
        unique_labels = np.unique(y_val)
        roc_auc = roc_auc_score(y_val, y_prob) if len(unique_labels) > 1 else 0.5
        
        metrics = {
            'accuracy': float(accuracy_score(y_val, y_pred)),
            'precision': float(precision_score(y_val, y_pred, zero_division=0)),
            'recall': float(recall_score(y_val, y_pred, zero_division=0)),
            'f1_score': float(f1_score(y_val, y_pred, zero_division=0)),
            'roc_auc': float(roc_auc),
            'training_samples': X_train.shape[0],
            'validation_samples': X_val.shape[0],
            'feature_count': X_text.shape[1]
        }
        
        self.is_trained = True
        self.training_metadata = {
            'trained_at': self._get_timestamp(),
            'metrics': metrics,
            'max_features': self.max_features,
            'ngram_range': self.ngram_range,
            'class_distribution': {
                'phishing': int(sum(labels)),
                'legitimate': int(len(labels) - sum(labels))
            }
        }
        
        logger.info(f"Training completed. Accuracy: {metrics['accuracy']:.4f}, F1: {metrics['f1_score']:.4f}")
        
        return metrics
    
    def predict_proba(self, subject: str, body: str) -> Dict[str, Any]:
        """
        Predict phishing probability for a single email.
        
        Args:
            subject: Email subject
            body: Email body
            
        Returns:
            Prediction result with probability
        """
        if not self.is_trained:
            logger.warning("Model not trained, returning default prediction")
            return self._fallback_prediction()
        
        try:
            text = self.prepare_text(subject, body)
            X = self.vectorizer.transform([text])
            
            if hasattr(self.model, 'predict_proba'):
                probabilities = self.model.predict_proba(X)[0]
                phishing_prob = float(probabilities[1])
            else:
                prediction = self.model.predict(X)[0]
                phishing_prob = float(prediction)
            
            category = self._categorize_prediction(phishing_prob)
            confidence = abs(phishing_prob - 0.5) * 2
            
            return {
                'is_phishing': phishing_prob > 0.5,
                'phishing_probability': phishing_prob,
                'safe_probability': 1 - phishing_prob,
                'category': category,
                'confidence': confidence
            }
        except Exception as e:
            logger.error(f"Prediction error: {e}")
            return self._fallback_prediction()
    
    def predict_proba_batch(
        self,
        subjects: List[str],
        bodies: List[str]
    ) -> List[Dict[str, Any]]:
        """
        Predict phishing probability for multiple emails.
        
        Args:
            subjects: List of email subjects
            bodies: List of email bodies
            
        Returns:
            List of prediction results
        """
        if not self.is_trained:
            return [self._fallback_prediction() for _ in subjects]
        
        try:
            texts = [self.prepare_text(s, b) for s, b in zip(subjects, bodies)]
            X = self.vectorizer.transform(texts)
            
            if hasattr(self.model, 'predict_proba'):
                probabilities = self.model.predict_proba(X)
                phishing_probs = probabilities[:, 1]
            else:
                predictions = self.model.predict(X)
                phishing_probs = predictions
            
            results = []
            for prob in phishing_probs:
                prob_float = float(prob)
                results.append({
                    'is_phishing': prob_float > 0.5,
                    'phishing_probability': prob_float,
                    'safe_probability': 1 - prob_float,
                    'category': self._categorize_prediction(prob_float),
                    'confidence': abs(prob_float - 0.5) * 2
                })
            
            return results
        except Exception as e:
            logger.error(f"Batch prediction error: {e}")
            return [self._fallback_prediction() for _ in subjects]
    
    def _categorize_prediction(self, probability: float) -> str:
        """Categorize prediction based on probability."""
        if probability >= 0.9:
            return 'phishing'
        elif probability >= 0.7:
            return 'suspicious'
        elif probability >= 0.5:
            return 'likely_phishing'
        elif probability >= 0.3:
            return 'low_risk'
        return 'safe'
    
    def _fallback_prediction(self) -> Dict[str, Any]:
        """Return fallback prediction when model unavailable."""
        return {
            'is_phishing': False,
            'phishing_probability': 0.0,
            'safe_probability': 1.0,
            'category': 'safe',
            'confidence': 0.0
        }
    
    @staticmethod
    def _get_timestamp() -> str:
        """Get current timestamp."""
        from datetime import datetime
        return datetime.utcnow().isoformat()
    
    def save_model(self, model_path: Optional[str] = None, vectorizer_path: Optional[str] = None):
        """
        Save the model and vectorizer.
        
        Args:
            model_path: Path to save model
            vectorizer_path: Path to save vectorizer
        """
        model_path = model_path or self.settings.TEXT_CLASSIFIER_PATH
        vectorizer_path = vectorizer_path or self.settings.TFIDF_VECTORIZER_PATH
        
        os.makedirs(os.path.dirname(model_path), exist_ok=True)
        os.makedirs(os.path.dirname(vectorizer_path), exist_ok=True)
        
        with open(model_path, 'wb') as f:
            pickle.dump({
                'model': self.model,
                'is_trained': self.is_trained,
                'metadata': self.training_metadata
            }, f)
        
        with open(vectorizer_path, 'wb') as f:
            pickle.dump(self.vectorizer, f)
        
        logger.info(f"Text classifier saved to {model_path}")
        logger.info(f"TF-IDF vectorizer saved to {vectorizer_path}")
    
    def get_top_features(self, n: int = 20) -> List[Dict[str, Any]]:
        """
        Get top TF-IDF features.
        
        Args:
            n: Number of top features to return
            
        Returns:
            List of feature importance dictionaries
        """
        if not self.is_trained or self.vectorizer is None:
            return []
        
        try:
            feature_names = self.vectorizer.get_feature_names_out()
            
            if hasattr(self.model, 'feature_importances_'):
                importances = self.model.feature_importances_
            elif hasattr(self.model, 'coef_'):
                importances = np.abs(self.model.coef_[0])
            else:
                return []
            
            indices = np.argsort(importances)[::-1][:n]
            
            return [
                {
                    'feature': feature_names[i],
                    'importance': float(importances[i])
                }
                for i in indices
            ]
        except Exception as e:
            logger.error(f"Error getting top features: {e}")
            return []
    
    def get_model_info(self) -> Dict[str, Any]:
        """Get model information."""
        return {
            'is_trained': self.is_trained,
            'model_type': 'xgboost' if XGBOOST_AVAILABLE else 'random_forest',
            'max_features': self.max_features,
            'ngram_range': self.ngram_range,
            'training_metadata': self.training_metadata
        }


_text_classifier_instance: Optional[TextClassifier] = None


def get_text_classifier() -> TextClassifier:
    """Get singleton instance of text classifier."""
    global _text_classifier_instance
    if _text_classifier_instance is None:
        _text_classifier_instance = TextClassifier()
    return _text_classifier_instance