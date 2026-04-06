"""
ML API Module

FastAPI endpoint for phishing detection predictions.
"""

import os
import pickle
import json
import logging
from typing import Optional
import numpy as np

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

logger = logging.getLogger(__name__)


class EmailInput(BaseModel):
    """Email input schema."""
    subject: str
    body: str


class PredictionOutput(BaseModel):
    """Prediction output schema."""
    is_phishing: bool
    phishing_probability: float
    safe_probability: float
    confidence: float
    category: str
    model_used: str


class PhishingDetectorAPI:
    """
    API for phishing detection.
    
    Loads best model and provides predictions.
    """
    
    def __init__(self, model_dir: str = "models"):
        self.model_dir = model_dir
        
        self.vectorizer = None
        self.classical_models = {}
        self.hybrid_model = None
        self.hybrid_scaler = None
        self.best_model_name = "hybrid"
        
        self._load_models()
    
    def _load_models(self):
        """Load all models from disk."""
        vectorizer_path = os.path.join(self.model_dir, "tfidf_vectorizer.pkl")
        if os.path.exists(vectorizer_path):
            with open(vectorizer_path, 'rb') as f:
                self.vectorizer = pickle.load(f)
            logger.info("Loaded TF-IDF vectorizer")
        
        classical_path = os.path.join(self.model_dir, "classical_ml_results.json")
        if os.path.exists(classical_path):
            with open(classical_path, 'r') as f:
                classical_results = json.load(f)
            
            for name in ['logistic_regression', 'svm', 'xgboost']:
                model_file = os.path.join(self.model_dir, f"{name.replace(' ', '_')}.pkl")
                if os.path.exists(model_file):
                    with open(model_file, 'rb') as f:
                        self.classical_models[name] = pickle.load(f)
            logger.info(f"Loaded {len(self.classical_models)} classical models")
        
        hybrid_model_path = os.path.join(self.model_dir, "hybrid_model.pkl")
        hybrid_scaler_path = os.path.join(self.model_dir, "hybrid_scaler.pkl")
        
        if os.path.exists(hybrid_model_path):
            with open(hybrid_model_path, 'rb') as f:
                self.hybrid_model = pickle.load(f)
            logger.info("Loaded hybrid model")
        
        if os.path.exists(hybrid_scaler_path):
            with open(hybrid_scaler_path, 'rb') as f:
                self.hybrid_scaler = pickle.load(f)
            logger.info("Loaded hybrid scaler")
    
    def predict_with_classical(
        self,
        subject: str,
        body: str,
        model_name: str = "xgboost"
    ) -> PredictionOutput:
        """Predict using classical ML model."""
        if self.vectorizer is None:
            raise ValueError("Vectorizer not loaded")
        
        if model_name not in self.classical_models:
            raise ValueError(f"Model {model_name} not loaded")
        
        text = f"{subject} {body}"
        X = self.vectorizer.transform([text])
        
        model = self.classical_models[model_name]
        y_prob = model.predict_proba(X)[0][1]
        
        return self._create_prediction_output(y_prob, f"classical_{model_name}")
    
    def predict_with_hybrid(
        self,
        bert_embeddings: np.ndarray,
        engineered_features: np.ndarray
    ) -> PredictionOutput:
        """Predict using hybrid model."""
        if self.hybrid_model is None or self.hybrid_scaler is None:
            raise ValueError("Hybrid model not loaded")
        
        scaled_features = self.hybrid_scaler.transform(engineered_features)
        hybrid_features = np.hstack([bert_embeddings, scaled_features])
        
        y_prob = self.hybrid_model.predict_proba(hybrid_features)[0][1]
        
        return self._create_prediction_output(y_prob, "hybrid")
    
    def _create_prediction_output(
        self,
        phishing_prob: float,
        model_name: str
    ) -> PredictionOutput:
        """Create prediction output object."""
        is_phishing = phishing_prob >= 0.5
        confidence = abs(phishing_prob - 0.5) * 2
        
        if phishing_prob >= 0.9:
            category = "phishing"
        elif phishing_prob >= 0.7:
            category = "suspicious"
        elif phishing_prob >= 0.5:
            category = "likely_phishing"
        elif phishing_prob >= 0.3:
            category = "low_risk"
        else:
            category = "safe"
        
        return PredictionOutput(
            is_phishing=is_phishing,
            phishing_probability=float(phishing_prob),
            safe_probability=float(1 - phishing_prob),
            confidence=float(confidence),
            category=category,
            model_used=model_name
        )
    
    def predict(
        self,
        subject: str,
        body: str,
        use_hybrid: bool = True
    ) -> PredictionOutput:
        """
        Predict phishing.
        
        Uses hybrid model if available, else falls back to classical.
        """
        if use_hybrid and self.hybrid_model is not None:
            try:
                from app.ml.models.bert_model import BERTTrainer
                from app.ml.feature_engineering import FeatureEngineer
                
                trainer = BERTTrainer()
                trainer.load_model()
                
                text = f"{subject} {body}"
                bert_emb = trainer.extract_embeddings([text], show_progress=False)
                
                engineer = FeatureEngineer()
                eng_features = engineer.get_feature_vector(subject, body)
                eng_features = np.array([eng_features])
                
                return self.predict_with_hybrid(bert_emb, eng_features)
            except Exception as e:
                logger.warning(f"Hybrid prediction failed: {e}, falling back to classical")
        
        if self.classical_models:
            return self.predict_with_classical(subject, body, "xgboost")
        
        raise ValueError("No models available")


_api_instance: Optional[PhishingDetectorAPI] = None


def get_phishing_api(model_dir: str = "models") -> PhishingDetectorAPI:
    """Get singleton instance of API."""
    global _api_instance
    if _api_instance is None:
        _api_instance = PhishingDetectorAPI(model_dir)
    return _api_instance


def create_prediction_endpoint(app: FastAPI, model_dir: str = "models"):
    """Add prediction endpoint to FastAPI app."""
    
    @app.post("/predict", response_model=PredictionOutput)
    async def predict_email(email: EmailInput):
        """
        Predict phishing for email.
        
        Returns prediction, confidence score.
        """
        api = get_phishing_api(model_dir)
        
        try:
            result = api.predict(email.subject, email.body)
            return result
        except Exception as e:
            logger.error(f"Prediction error: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    @app.get("/models")
    async def list_models():
        """List available models."""
        api = get_phishing_api(model_dir)
        
        return {
            "classical_models": list(api.classical_models.keys()),
            "hybrid_available": api.hybrid_model is not None,
            "best_model": api.best_model_name
        }
    
    return app


def predict_email(
    subject: str,
    body: str,
    model_dir: str = "models"
) -> PredictionOutput:
    """
    Quick prediction function.
    
    Usage:
        result = predict_email("Subject", "Email body")
    """
    api = get_phishing_api(model_dir)
    return api.predict(subject, body)