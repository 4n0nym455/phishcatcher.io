"""
Hybrid Model Module

This module combines BERT embeddings with engineered features for phishing detection.
Concatenates [BERT embeddings (768 dim)] + [Engineered features (~40 dim)] -> XGBoost
"""

import os
import pickle
import json
import logging
from typing import Dict, List, Any, Optional, Tuple
import numpy as np

from sklearn.model_selection import train_test_split
from sklearn.metrics import (
    accuracy_score, precision_score, recall_score, 
    f1_score, roc_auc_score, confusion_matrix
)
from sklearn.preprocessing import StandardScaler

try:
    import xgboost as xgb
    XGBOOST_AVAILABLE = True
except ImportError:
    XGBOOST_AVAILABLE = False
    logging.warning("XGBoost not available for hybrid model")


logger = logging.getLogger(__name__)


class HybridModel:
    """
    Hybrid model combining:
    - BERT embeddings (semantic features, 768 dimensions)
    - Engineered features (URL, text, structural, ~40 dimensions)
    
    Trained with XGBoost classifier.
    """
    
    def __init__(self):
        self.bert_embeddings: Optional[np.ndarray] = None
        self.engineered_features: Optional[np.ndarray] = None
        self.scaler: Optional[StandardScaler] = None
        self.model: Optional[Any] = None
        self.is_trained = False
        self.results: Dict = {}
    
    def prepare_hybrid_features(
        self,
        bert_embeddings: np.ndarray,
        engineered_features: np.ndarray
    ) -> np.ndarray:
        """
        Concatenate BERT embeddings with engineered features.
        
        Args:
            bert_embeddings: BERT embeddings (n_samples, 768)
            engineered_features: Engineered features (n_samples, n_features)
            
        Returns:
            Combined features (n_samples, 768 + n_features)
        """
        if bert_embeddings.shape[0] != engineered_features.shape[0]:
            raise ValueError(
                f"Embedding count mismatch: {bert_embeddings.shape[0]} vs {engineered_features.shape[0]}"
            )
        
        self.scaler = StandardScaler()
        scaled_engineered = self.scaler.fit_transform(engineered_features)
        
        hybrid_features = np.hstack([bert_embeddings, scaled_engineered])
        
        logger.info(f"Hybrid features shape: {hybrid_features.shape}")
        
        return hybrid_features
    
    def prepare_hybrid_features_inference(
        self,
        bert_embeddings: np.ndarray,
        engineered_features: np.ndarray
    ) -> np.ndarray:
        """Prepare hybrid features for inference (uses fitted scaler)."""
        if self.scaler is None:
            raise ValueError("Scaler not fitted. Train model first.")
        
        scaled_engineered = self.scaler.transform(engineered_features)
        return np.hstack([bert_embeddings, scaled_engineered])
    
    def train(
        self,
        bert_embeddings: np.ndarray,
        engineered_features: np.ndarray,
        labels: List[int],
        test_size: float = 0.2,
        random_state: int = 42
    ) -> Dict[str, Any]:
        """
        Train hybrid model.
        
        Args:
            bert_embeddings: BERT embeddings
            engineered_features: Engineered features from FeatureEngineer
            labels: Labels
            test_size: Test split ratio
            random_state: Random seed
            
        Returns:
            Training metrics and results
        """
        if not XGBOOST_AVAILABLE:
            raise ImportError("XGBoost not available")
        
        logger.info("Preparing hybrid features...")
        
        hybrid_features = self.prepare_hybrid_features(bert_embeddings, engineered_features)
        
        X_train, X_test, y_train, y_test = train_test_split(
            hybrid_features, labels,
            test_size=test_size,
            random_state=random_state,
            stratify=labels
        )
        
        logger.info(f"Training hybrid model on {X_train.shape[0]} samples...")
        
        self.model = xgb.XGBClassifier(
            n_estimators=150,
            max_depth=8,
            learning_rate=0.1,
            subsample=0.8,
            colsample_bytree=0.8,
            objective='binary:logistic',
            eval_metric='logloss',
            random_state=random_state,
            use_label_encoder=False,
            verbosity=0,
            n_jobs=-1
        )
        
        self.model.fit(
            X_train, y_train,
            eval_set=[(X_test, y_test)],
            verbose=False
        )
        
        y_pred = self.model.predict(X_test)
        y_prob = self.model.predict_proba(X_test)[:, 1]
        
        metrics = {
            'accuracy': float(accuracy_score(y_test, y_pred)),
            'precision': float(precision_score(y_test, y_pred, zero_division=0)),
            'recall': float(recall_score(y_test, y_pred, zero_division=0)),
            'f1_score': float(f1_score(y_test, y_pred, zero_division=0)),
            'roc_auc': float(roc_auc_score(y_test, y_prob)),
            'confusion_matrix': confusion_matrix(y_test, y_pred).tolist()
        }
        
        self.results = metrics
        self.is_trained = True
        
        logger.info(f"Hybrid model trained. Accuracy: {metrics['accuracy']:.4f}, F1: {metrics['f1_score']:.4f}")
        
        return metrics
    
    def predict(
        self,
        bert_embeddings: np.ndarray,
        engineered_features: np.ndarray
    ) -> Tuple[np.ndarray, np.ndarray]:
        """
        Predict using hybrid model.
        
        Returns:
            predictions, probabilities
        """
        if not self.is_trained:
            raise ValueError("Model not trained")
        
        hybrid_features = self.prepare_hybrid_features_inference(
            bert_embeddings, engineered_features
        )
        
        y_pred = self.model.predict(hybrid_features)
        y_prob = self.model.predict_proba(hybrid_features)[:, 1]
        
        return y_pred, y_prob
    
    def get_feature_importance(self, feature_names: List[str]) -> List[Dict]:
        """
        Get feature importance from XGBoost.
        
        Returns top contributing features.
        """
        if not self.is_trained or self.model is None:
            return []
        
        importances = self.model.feature_importances_
        
        feature_importance = [
            {'feature': name, 'importance': float(imp)}
            for name, imp in zip(feature_names, importances)
        ]
        
        feature_importance.sort(key=lambda x: x['importance'], reverse=True)
        
        return feature_importance[:20]
    
    def save(self, model_dir: str = "models"):
        """Save hybrid model and scaler."""
        os.makedirs(model_dir, exist_ok=True)
        
        model_path = os.path.join(model_dir, "hybrid_model.pkl")
        with open(model_path, 'wb') as f:
            pickle.dump(self.model, f)
        logger.info(f"Saved hybrid model to {model_path}")
        
        scaler_path = os.path.join(model_dir, "hybrid_scaler.pkl")
        with open(scaler_path, 'wb') as f:
            pickle.dump(self.scaler, f)
        logger.info(f"Saved scaler to {scaler_path}")
        
        results_path = os.path.join(model_dir, "hybrid_results.json")
        with open(results_path, 'w') as f:
            json.dump(self.results, f, indent=2)
        logger.info(f"Saved results to {results_path}")
    
    def load(self, model_dir: str = "models"):
        """Load hybrid model and scaler."""
        model_path = os.path.join(model_dir, "hybrid_model.pkl")
        with open(model_path, 'rb') as f:
            self.model = pickle.load(f)
        logger.info(f"Loaded hybrid model from {model_path}")
        
        scaler_path = os.path.join(model_dir, "hybrid_scaler.pkl")
        with open(scaler_path, 'rb') as f:
            self.scaler = pickle.load(f)
        logger.info(f"Loaded scaler from {scaler_path}")
        
        results_path = os.path.join(model_dir, "hybrid_results.json")
        if os.path.exists(results_path):
            with open(results_path, 'r') as f:
                self.results = json.load(f)
        
        self.is_trained = True


def train_hybrid_model(
    bert_embeddings: np.ndarray,
    engineered_features: np.ndarray,
    labels: List[int],
    model_dir: str = "models"
) -> Dict[str, Any]:
    """
    Quick function to train hybrid model.
    
    Usage:
        metrics = train_hybrid_model(bert_emb, eng_features, labels)
    """
    model = HybridModel()
    metrics = model.train(bert_embeddings, engineered_features, labels)
    model.save(model_dir)
    
    return metrics