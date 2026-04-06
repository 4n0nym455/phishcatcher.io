"""
BERT Model Module

This module provides DistilBERT embeddings extraction for phishing detection.
Uses frozen embeddings (no fine-tuning) for efficiency on CPU.
"""

import os
import pickle
import json
import logging
from typing import List, Dict, Any, Optional, Tuple
import numpy as np

logger = logging.getLogger(__name__)

try:
    from transformers import DistilBertTokenizer, DistilBertModel
    import torch
    TRANSFORMERS_AVAILABLE = True
except ImportError:
    TRANSFORMERS_AVAILABLE = False
    logger.warning("Transformers not available, BERT embeddings disabled")


class BERTTrainer:
    """
    Trainer for BERT embeddings extraction.
    
    Uses DistilBERT (frozen) for efficient CPU inference:
    - Extract embeddings (768 dimensions)
    - Train classifier on embeddings
    - Save embeddings to disk for reuse
    """
    
    DEFAULT_MAX_LENGTH = 256
    DEFAULT_BATCH_SIZE = 8
    EMBEDDING_DIM = 768
    
    def __init__(
        self,
        model_name: str = "distilbert-base-uncased",
        max_length: int = DEFAULT_MAX_LENGTH,
        batch_size: int = DEFAULT_BATCH_SIZE
    ):
        self.model_name = model_name
        self.max_length = max_length
        self.batch_size = batch_size
        
        self.tokenizer = None
        self.model = None
        self.device = None
        
        self.is_loaded = False
        
    def load_model(self):
        """Load DistilBERT model and tokenizer."""
        if not TRANSFORMERS_AVAILABLE:
            raise ImportError("Transformers library not available")
        
        logger.info(f"Loading {self.model_name}...")
        
        self.tokenizer = DistilBertTokenizer.from_pretrained(self.model_name)
        
        self.model = DistilBertModel.from_pretrained(self.model_name)
        
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.model.to(self.device)
        self.model.eval()
        
        logger.info(f"Model loaded on {self.device}")
        self.is_loaded = True
    
    def extract_embeddings(self, texts: List[str], show_progress: bool = True) -> np.ndarray:
        """
        Extract embeddings from texts using frozen DistilBERT.
        
        Args:
            texts: List of text strings
            show_progress: Show progress bar
            
        Returns:
            numpy array of embeddings (n_samples, 768)
        """
        if not self.is_loaded:
            self.load_model()
        
        embeddings = []
        
        for i in range(0, len(texts), self.batch_size):
            batch_texts = texts[i:i + self.batch_size]
            
            if show_progress and i % 100 == 0:
                logger.info(f"Processing batch {i//self.batch_size + 1}/{len(texts)//self.batch_size + 1}")
            
            encoded = self.tokenizer(
                batch_texts,
                padding=True,
                truncation=True,
                max_length=self.max_length,
                return_tensors='pt'
            )
            
            input_ids = encoded['input_ids'].to(self.device)
            attention_mask = encoded['attention_mask'].to(self.device)
            
            with torch.no_grad():
                outputs = self.model(input_ids=input_ids, attention_mask=attention_mask)
                
                attention_mask_expanded = attention_mask.unsqueeze(-1).expand(outputs.last_hidden_state.size()).float()
                sum_embeddings = torch.sum(outputs.last_hidden_state * attention_mask_expanded, 1)
                sum_mask = torch.clamp(attention_mask_expanded.sum(1), min=1e-9)
                batch_embeddings = (sum_embeddings / sum_mask).cpu().numpy()
            
            embeddings.append(batch_embeddings)
        
        return np.vstack(embeddings)
    
    def extract_single_embedding(self, text: str) -> np.ndarray:
        """Extract embedding from single text."""
        return self.extract_embeddings([text], show_progress=False)[0]
    
    def save_embeddings(self, embeddings: np.ndarray, file_path: str):
        """Save embeddings to disk."""
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        
        np.save(file_path, embeddings)
        logger.info(f"Saved embeddings to {file_path}")
    
    def load_embeddings(self, file_path: str) -> np.ndarray:
        """Load embeddings from disk."""
        embeddings = np.load(file_path)
        logger.info(f"Loaded embeddings from {file_path}, shape: {embeddings.shape}")
        return embeddings
    
    def save_model_info(self, model_dir: str):
        """Save model configuration info."""
        info = {
            'model_name': self.model_name,
            'max_length': self.max_length,
            'embedding_dim': self.EMBEDDING_DIM,
            'device': str(self.device),
            'batch_size': self.batch_size
        }
        
        info_path = os.path.join(model_dir, "bert_model_info.json")
        with open(info_path, 'w') as f:
            json.dump(info, f, indent=2)
        
        logger.info(f"Saved BERT model info to {info_path}")


class BERTClassifier:
    """
    Classifier that uses BERT embeddings.
    
    Trains on pre-computed embeddings.
    """
    
    def __init__(self):
        self.model = None
        self.is_trained = False
        
    def train(
        self,
        embeddings: np.ndarray,
        labels: List[int],
        use_xgboost: bool = True
    ) -> Dict[str, float]:
        """
        Train classifier on BERT embeddings.
        
        Args:
            embeddings: BERT embeddings (n_samples, 768)
            labels: Labels
            use_xgboost: Use XGBoost (else Logistic Regression)
            
        Returns:
            Training metrics
        """
        from sklearn.model_selection import train_test_split
        from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, roc_auc_score
        
        X_train, X_test, y_train, y_test = train_test_split(
            embeddings, labels, test_size=0.2, random_state=42, stratify=labels
        )
        
        if use_xgboost and XGBOOST_AVAILABLE:
            self.model = xgb.XGBClassifier(
                n_estimators=100,
                max_depth=6,
                learning_rate=0.1,
                random_state=42,
                use_label_encoder=False,
                verbosity=0
            )
        else:
            from sklearn.linear_model import LogisticRegression
            self.model = LogisticRegression(max_iter=1000, random_state=42)
        
        self.model.fit(X_train, y_train)
        
        y_pred = self.model.predict(X_test)
        y_prob = self.model.predict_proba(X_test)[:, 1] if hasattr(self.model, 'predict_proba') else y_pred
        
        metrics = {
            'accuracy': float(accuracy_score(y_test, y_pred)),
            'precision': float(precision_score(y_test, y_pred, zero_division=0)),
            'recall': float(recall_score(y_test, y_pred, zero_division=0)),
            'f1_score': float(f1_score(y_test, y_pred, zero_division=0)),
            'roc_auc': float(roc_auc_score(y_test, y_prob))
        }
        
        self.is_trained = True
        
        return metrics
    
    def predict(self, embeddings: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        """Predict on embeddings."""
        if not self.is_trained:
            raise ValueError("Model not trained")
        
        y_pred = self.model.predict(embeddings)
        y_prob = self.model.predict_proba(embeddings)[:, 1] if hasattr(self.model, 'predict_proba') else y_pred
        
        return y_pred, y_prob
    
    def save(self, model_path: str):
        """Save model to disk."""
        with open(model_path, 'wb') as f:
            pickle.dump(self.model, f)
        logger.info(f"Saved BERT classifier to {model_path}")
    
    def load(self, model_path: str):
        """Load model from disk."""
        with open(model_path, 'rb') as f:
            self.model = pickle.load(f)
        self.is_trained = True
        logger.info(f"Loaded BERT classifier from {model_path}")


def extract_bert_embeddings(
    texts: List[str],
    embeddings_path: Optional[str] = None,
    batch_size: int = 8,
    max_length: int = 256
) -> np.ndarray:
    """
    Quick function to extract BERT embeddings.
    
    Usage:
        embeddings = extract_bert_embeddings(texts, "models/bert_embeddings.npy")
    """
    trainer = BERTTrainer(batch_size=batch_size, max_length=max_length)
    embeddings = trainer.extract_embeddings(texts)
    
    if embeddings_path:
        trainer.save_embeddings(embeddings, embeddings_path)
    
    return embeddings


def train_bert_classifier(
    embeddings: np.ndarray,
    labels: List[int],
    model_path: str = "models/bert_classifier.pkl"
) -> Dict[str, float]:
    """
    Quick function to train BERT classifier.
    
    Usage:
        metrics = train_bert_classifier(embeddings, labels)
    """
    classifier = BERTClassifier()
    metrics = classifier.train(embeddings, labels)
    classifier.save(model_path)
    
    return metrics