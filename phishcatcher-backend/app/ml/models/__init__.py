"""
Models Package

This package contains all ML models for phishing detection:
- classical.py: TF-IDF + Logistic Regression, SVM, XGBoost
- bert_model.py: DistilBERT embeddings extraction
- hybrid.py: Combined BERT embeddings + engineered features
"""

from .classical import ClassicalMLTrainer
from .bert_model import BERTTrainer
from .hybrid import HybridModel

__all__ = [
    'ClassicalMLTrainer',
    'BERTTrainer', 
    'HybridModel'
]