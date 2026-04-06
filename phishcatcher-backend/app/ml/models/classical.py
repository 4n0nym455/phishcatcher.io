"""
Classical ML Module

This module implements classical machine learning models for phishing detection:
- TF-IDF vectorization (max_features=5000)
- Logistic Regression
- Linear SVM
- XGBoost

With cross-validation and class weight handling.
"""

import os
import pickle
import json
import logging
from typing import Dict, List, Any, Optional, Tuple
import numpy as np

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
        
        self.feature_names: List[str] = []
        
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
        vectorizer_path = os.path.join(model_dir, "tfidf_vectorizer.pkl")
        if os.path.exists(vectorizer_path):
            with open(vectorizer_path, 'rb') as f:
                self.vectorizer = pickle.load(f)
            self.feature_names = self.vectorizer.get_feature_names_out().tolist()
            logger.info(f"Loaded TF-IDF vectorizer from {vectorizer_path}")
        
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