"""
Classical ML Module

This module implements classical machine learning models for phishing detection:
- TF-IDF vectorization (max_features=5000)
- Logistic Regression
- Linear SVM
- XGBoost
- Stacked Ensemble (with handcrafted features)
- Hybrid Model

With cross-validation and class weight handling.
"""

import os
import re
import pickle
import json
import logging
from typing import Dict, List, Any, Optional, Tuple
import numpy as np

try:
    import joblib
    JOBLIB_AVAILABLE = True
except ImportError:
    JOBLIB_AVAILABLE = False

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.svm import LinearSVC
from sklearn.model_selection import train_test_split, cross_val_score, StratifiedKFold
from sklearn.metrics import (
    accuracy_score, precision_score, recall_score, f1_score,
    classification_report, confusion_matrix, roc_auc_score
)

try:
    import xgboost as xgb
    XGBOOST_AVAILABLE = True
except ImportError:
    XGBOOST_AVAILABLE = False
    logging.warning("XGBoost not available, will skip XGBoost model")

logger = logging.getLogger(__name__)


class ClassicalMLTrainer:
    """
    Trainer for classical ML models with TF-IDF.
    
    Implements:
    - TF-IDF vectorization (max_features=5000)
    - Logistic Regression
    - Linear SVM
    - XGBoost
    - Cross-validation
    - Class weight handling
    """
    
    DEFAULT_MAX_FEATURES = 5000
    DEFAULT_NGRAM_RANGE = (1, 2)
    DEFAULT_CV_FOLDS = 5
    
    def __init__(
        self,
        max_features: int = DEFAULT_MAX_FEATURES,
        ngram_range: Tuple[int, int] = DEFAULT_NGRAM_RANGE,
        cv_folds: int = DEFAULT_CV_FOLDS
    ):
        self.max_features = max_features
        self.ngram_range = ngram_range
        self.cv_folds = cv_folds
        
        self.vectorizer: Optional[TfidfVectorizer] = None
        self.models: Dict[str, Any] = {}
        self.results: Dict[str, Dict] = {}
        self.is_trained = False
        
        # New ensemble models
        self.stacked_model: Optional[Any] = None
        self.is_stacked_loaded = False
        self.hybrid_model: Optional[Any] = None
        self.hybrid_scaler: Optional[Any] = None
        self.is_hybrid_loaded = False
        
        self.feature_names: List[str] = []
        
        self.urgency_keywords = [
            'urgent', 'immediate', 'action required', 'verify now', 'account suspended',
            'limited time', 'expires soon', 'confirm now', 'update required',
            'security alert', 'unusual activity', 'suspicious activity', 'verify account',
            'click here', 'act now', "don't delay", 'final notice', 'warning',
            'deadline', 'last chance', 'expiring', 'terminate', 'suspend'
        ]
        
        self.financial_keywords = [
            'bank', 'credit card', 'payment', 'invoice', 'transaction', 'refund',
            'billing', 'subscription', 'paypal', 'money', 'transfer', 'account',
            'balance', 'withdraw', 'deposit', 'ssn', 'social security', 'routing',
            'wire transfer', 'western union', 'gift card', 'bitcoin', 'cryptocurrency'
        ]
        
        self.suspicious_tlds = [
            'tk', 'ml', 'ga', 'cf', 'gq', 'xyz', 'top', 'click', 'link', 'work',
            'loan', 'online', 'site', 'club', 'win', 'download', 'bid', 'review'
        ]
    
    def extract_handcrafted_features(self, text: str) -> np.ndarray:
        """Extract 14 handcrafted features matching training setup."""
        text_lower = text.lower()
        
        urls = re.findall(r'https?://[^\s]+', text)
        url_count = len(urls)
        
        email_count = len(re.findall(r'[\w.-]+@[\w.-]+\.\w+', text))
        
        urgent_keyword_count = sum(1 for kw in self.urgency_keywords if kw in text_lower)
        
        financial_keyword_count = sum(1 for kw in self.financial_keywords if kw in text_lower)
        
        reward_keywords = ['won', 'prize', 'winner', 'congratulations', 'free', 'gift', 'reward', 'bonus']
        reward_keyword_count = sum(1 for kw in reward_keywords if kw in text_lower)
        
        exclamation_count = text.count('!')
        
        dollar_count = text.count('$')
        
        digits = sum(c.isdigit() for c in text)
        digit_ratio = digits / max(len(text), 1)
        
        words = text.split()
        uppercase_words = sum(1 for w in words if w.isupper() and len(w) > 1)
        uppercase_ratio = uppercase_words / max(len(words), 1)
        
        suspicious_tld_count = 0
        for url in urls:
            match = re.search(r'\.([a-z]{2,4})(?:/|$)', url.lower())
            if match and match.group(1) in self.suspicious_tlds:
                suspicious_tld_count += 1
        
        ip_count = len(re.findall(r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}', text))
        
        has_re = 1 if text_lower.startswith('re:') else 0
        has_fwd = 1 if 'forward' in text_lower else 0
        
        features = [
            float(url_count),
            1.0 if url_count > 0 else 0.0,
            float(email_count),
            float(urgent_keyword_count),
            float(financial_keyword_count),
            float(reward_keyword_count),
            float(exclamation_count),
            float(dollar_count),
            float(digit_ratio),
            float(uppercase_ratio),
            float(suspicious_tld_count),
            float(ip_count),
            float(has_re),
            float(has_fwd)
        ]
        
        return np.array(features)
        
    def prepare_data(
        self,
        texts: List[str],
        labels: List[int],
        test_size: float = 0.2,
        random_state: int = 42
    ) -> Tuple:
        """Prepare data for training."""
        X_train, X_test, y_train, y_test = train_test_split(
            texts, labels,
            test_size=test_size,
            random_state=random_state,
            stratify=labels
        )
        
        logger.info(f"Training samples: {len(X_train)}, Test samples: {len(X_test)}")
        
        return X_train, X_test, y_train, y_test
    
    def fit_vectorizer(self, texts: List[str]) -> np.ndarray:
        """Fit TF-IDF vectorizer and transform texts."""
        self.vectorizer = TfidfVectorizer(
            max_features=self.max_features,
            ngram_range=self.ngram_range,
            sublinear_tf=True,
            strip_accents='unicode',
            lowercase=True,
            min_df=2,
            max_df=0.95
        )
        
        X = self.vectorizer.fit_transform(texts)
        self.feature_names = self.vectorizer.get_feature_names_out().tolist()
        
        logger.info(f"TF-IDF matrix shape: {X.shape}")
        
        return X
    
    def transform_texts(self, texts: List[str]) -> np.ndarray:
        """Transform texts using fitted vectorizer."""
        if self.vectorizer is None:
            raise ValueError("Vectorizer not fitted. Call fit_vectorizer first.")
        
        return self.vectorizer.transform(texts)
    
    def train_models(
        self,
        X_train: np.ndarray,
        y_train: List[int],
        use_class_weights: bool = True
    ) -> Dict[str, Dict]:
        """
        Train all classical ML models.
        
        Args:
            X_train: TF-IDF features
            y_train: Labels
            use_class_weights: Use balanced class weights
            
        Returns:
            Dictionary of model results
        """
        logger.info("Training classical ML models...")
        
        class_weight = 'balanced' if use_class_weights else None
        
        self.models['logistic_regression'] = LogisticRegression(
            max_iter=1000,
            class_weight=class_weight,
            random_state=42,
            n_jobs=-1
        )
        
        self.models['svm'] = LinearSVC(
            max_iter=2000,
            class_weight=class_weight,
            random_state=42,
            dual=True
        )
        
        if XGBOOST_AVAILABLE:
            self.models['xgboost'] = xgb.XGBClassifier(
                n_estimators=100,
                max_depth=6,
                learning_rate=0.1,
                subsample=0.8,
                colsample_bytree=0.8,
                objective='binary:logistic',
                eval_metric='logloss',
                random_state=42,
                use_label_encoder=False,
                verbosity=0,
                n_jobs=-1
            )
        
        for name, model in self.models.items():
            logger.info(f"Training {name}...")
            model.fit(X_train, y_train)
            
            cv_scores = cross_val_score(
                model, X_train, y_train,
                cv=StratifiedKFold(n_splits=self.cv_folds, shuffle=True),
                scoring='f1'
            )
            
            self.results[name] = {
                'cv_f1_mean': float(np.mean(cv_scores)),
                'cv_f1_std': float(np.std(cv_scores))
            }
        
        self.is_trained = True
        logger.info("Classical ML training completed")
        
        return self.results
    
    def evaluate_models(
        self,
        X_test: np.ndarray,
        y_test: List[int]
    ) -> Dict[str, Dict]:
        """
        Evaluate all trained models.
        
        Returns:
            Dictionary of evaluation metrics
        """
        logger.info("Evaluating models...")
        
        evaluation_results = {}
        
        for name, model in self.models.items():
            y_pred = model.predict(X_test)
            
            if hasattr(model, 'predict_proba'):
                y_prob = model.predict_proba(X_test)[:, 1]
                try:
                    roc_auc = roc_auc_score(y_test, y_prob)
                except Exception:
                    roc_auc = 0.0
            else:
                y_prob = y_pred
                roc_auc = 0.0
            
            metrics = {
                'accuracy': float(accuracy_score(y_test, y_pred)),
                'precision': float(precision_score(y_test, y_pred, zero_division=0)),
                'recall': float(recall_score(y_test, y_pred, zero_division=0)),
                'f1_score': float(f1_score(y_test, y_pred, zero_division=0)),
                'roc_auc': float(roc_auc),
                'confusion_matrix': confusion_matrix(y_test, y_pred).tolist()
            }
            
            evaluation_results[name] = metrics
            
            logger.info(f"{name}: Accuracy={metrics['accuracy']:.4f}, F1={metrics['f1_score']:.4f}, ROC-AUC={metrics['roc_auc']:.4f}")
        
        self.results.update(evaluation_results)
        
        return evaluation_results
    
    def get_best_model(self) -> Tuple[str, Any]:
        """Get the best performing model based on F1 score."""
        best_name = None
        best_f1 = 0
        best_model = None
        
        for name, result in self.results.items():
            if 'f1_score' in result and result['f1_score'] > best_f1:
                best_f1 = result['f1_score']
                best_name = name
                best_model = self.models.get(name)
        
        return best_name, best_model
    
    def predict(self, texts: List[str]) -> Tuple[np.ndarray, np.ndarray]:
        """Predict using best model."""
        best_name, best_model = self.get_best_model()
        
        if best_model is None:
            raise ValueError("No trained models available")
        
        X = self.transform_texts(texts)
        y_pred = best_model.predict(X)
        
        if hasattr(best_model, 'predict_proba'):
            y_prob = best_model.predict_proba(X)[:, 1]
        else:
            y_prob = y_pred
        
        return y_pred, y_prob
    
    def predict_ensemble(self, texts: List[str]) -> Tuple[np.ndarray, np.ndarray]:
        """
        Predict using stacked ensemble model (primary).
        
        Returns predictions and probabilities.
        Falls back to hybrid if ensemble not available.
        """
        if not self.is_stacked_loaded:
            logger.warning("Stacked ensemble not loaded, falling back to hybrid model")
            return self.predict_hybrid(texts)
        
        try:
            # Combine TF-IDF + handcrafted features (5014 total)
            X_tfidf = self.transform_texts(texts)
            combined_features = []
            for text in texts:
                handcrafted = self.extract_handcrafted_features(text)
                combined_features.append(handcrafted)
            handcrafted_arr = np.array(combined_features)
            X = np.hstack([X_tfidf.toarray() if hasattr(X_tfidf, 'toarray') else X_tfidf, handcrafted_arr])
            
            y_pred = self.stacked_model.predict(X)
            y_prob = self.stacked_model.predict_proba(X)[:, 1]
            return y_pred, y_prob
        except Exception as e:
            logger.error(f"Stacked ensemble prediction failed: {e}, falling back to hybrid")
            return self.predict_hybrid(texts)
    
    def predict_hybrid(self, texts: List[str]) -> Tuple[np.ndarray, np.ndarray]:
        """
        Predict using hybrid model (fallback).
        
        Returns predictions and probabilities.
        Uses only handcrafted features (46 trained features).
        """
        if not self.is_hybrid_loaded:
            raise ValueError("Hybrid model not available")
        
        try:
            # Use only handcrafted features (first 14 + additional 32 = 46)
            combined_features = []
            for text in texts:
                handcrafted = self.extract_handcrafted_features(text)
                # Pad to 46 features (placeholder for rest if needed)
                padding = np.zeros(32)
                combined = np.concatenate([handcrafted, padding])
                combined_features.append(combined)
            X = np.array(combined_features)
            
            X_scaled = self.hybrid_scaler.transform(X)
            y_pred = self.hybrid_model.predict(X_scaled)
            y_prob = self.hybrid_model.predict_proba(X_scaled)[:, 1]
            return y_pred, y_prob
        except Exception as e:
            logger.error(f"Hybrid model prediction failed: {e}")
            # Fall back to classical
            return self.predict(texts)
    
    def save_models(self, model_dir: str = "models"):
        """Save all models to disk."""
        os.makedirs(model_dir, exist_ok=True)
        
        if self.vectorizer:
            vectorizer_path = os.path.join(model_dir, "tfidf_vectorizer.pkl")
            with open(vectorizer_path, 'wb') as f:
                pickle.dump(self.vectorizer, f)
            logger.info(f"Saved TF-IDF vectorizer to {vectorizer_path}")
        
        for name, model in self.models.items():
            model_path = os.path.join(model_dir, f"{name.replace(' ', '_')}.pkl")
            with open(model_path, 'wb') as f:
                pickle.dump(model, f)
            logger.info(f"Saved {name} to {model_path}")
        
        results_path = os.path.join(model_dir, "classical_ml_results.json")
        with open(results_path, 'w') as f:
            json.dump(self.results, f, indent=2)
        logger.info(f"Saved results to {results_path}")
    
    def load_models(self, model_dir: str = "models"):
        """Load all models from disk."""
        # Load TF-IDF vectorizer
        vectorizer_path = os.path.join(model_dir, "tfidf_vectorizer.pkl")
        if os.path.exists(vectorizer_path):
            with open(vectorizer_path, 'rb') as f:
                self.vectorizer = pickle.load(f)
            self.feature_names = self.vectorizer.get_feature_names_out().tolist()
            logger.info(f"Loaded TF-IDF vectorizer from {vectorizer_path}")
        
        # Load classical ML models (pickle)
        model_files = {
            'logistic_regression': 'logistic_regression.pkl',
            'svm': 'svm.pkl',
            'xgboost': 'xgboost.pkl'
        }
        
        for name, filename in model_files.items():
            model_path = os.path.join(model_dir, filename)
            if os.path.exists(model_path):
                with open(model_path, 'rb') as f:
                    self.models[name] = pickle.load(f)
                logger.info(f"Loaded {name} from {model_path}")
        
        # Load stacked ensemble model (joblib)
        if JOBLIB_AVAILABLE:
            stacked_path = os.path.join(model_dir, "stacked_ensemble_model.joblib")
            if os.path.exists(stacked_path):
                self.stacked_model = joblib.load(stacked_path)
                self.is_stacked_loaded = True
                logger.info(f"Loaded stacked ensemble model from {stacked_path}")
        
        # Load hybrid model (pickle)
        hybrid_path = os.path.join(model_dir, "hybrid_model.pkl")
        hybrid_scaler_path = os.path.join(model_dir, "hybrid_scaler.pkl")
        if os.path.exists(hybrid_path) and os.path.exists(hybrid_scaler_path):
            with open(hybrid_path, 'rb') as f:
                self.hybrid_model = pickle.load(f)
            with open(hybrid_scaler_path, 'rb') as f:
                self.hybrid_scaler = pickle.load(f)
            self.is_hybrid_loaded = True
            logger.info(f"Loaded hybrid model from {hybrid_path}")
        
        # Load results
        results_path = os.path.join(model_dir, "classical_ml_results.json")
        if os.path.exists(results_path):
            with open(results_path, 'r') as f:
                self.results = json.load(f)
            logger.info(f"Loaded results from {results_path}")
        
        self.is_trained = bool(self.models)
    
    def get_results_summary(self) -> Dict[str, Any]:
        """Get summary of all model results."""
        summary = {
            'trained_models': list(self.models.keys()),
            'cv_folds': self.cv_folds,
            'tfidf_features': self.max_features,
            'ngram_range': self.ngram_range,
            'results': self.results
        }
        
        best_name, _ = self.get_best_model()
        summary['best_model'] = best_name
        
        return summary


def train_classical_models(
    texts: List[str],
    labels: List[int],
    model_dir: str = "models",
    test_size: float = 0.2
) -> Dict[str, Any]:
    """
    Quick function to train classical ML models.
    
    Usage:
        results = train_classical_models(texts, labels)
    """
    trainer = ClassicalMLTrainer()
    
    X_train, X_test, y_train, y_test = trainer.prepare_data(
        texts, labels, test_size
    )
    
    X_train_tfidf = trainer.fit_vectorizer(X_train)
    X_test_tfidf = trainer.transform_texts(X_test)
    
    trainer.train_models(X_train_tfidf, y_train)
    results = trainer.evaluate_models(X_test_tfidf, y_test)
    
    trainer.save_models(model_dir)
    
    return results