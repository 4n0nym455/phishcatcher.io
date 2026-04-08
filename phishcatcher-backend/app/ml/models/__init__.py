"""
Models Package

This package contains all ML models for phishing detection:
- classical.py: TF-IDF + Logistic Regression, SVM, XGBoost
- bert_model.py: DistilBERT embeddings extraction
"""

from .classical import ClassicalMLTrainer
from .bert_model import BERTTrainer

__all__ = [
    'ClassicalMLTrainer',
    'BERTTrainer'
]