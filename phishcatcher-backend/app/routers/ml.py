"""
ML Router

FastAPI endpoints for ML-based phishing detection.
"""

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from app.config import get_settings
from app.models.user import User
from app.routers.auth import get_current_active_user
from app.ml.api import predict_email as ml_predict_email, get_phishing_api

logger = logging.getLogger(__name__)
router = APIRouter(tags=["ML"])


class EmailPredictionRequest(BaseModel):
    """Request schema for email phishing prediction."""
    subject: str
    body: str


class EmailPredictionResponse(BaseModel):
    """Response schema for email phishing prediction."""
    is_phishing: bool
    phishing_probability: float
    safe_probability: float
    confidence: float
    category: str
    model_used: str


class ModelInfo(BaseModel):
    """Model information schema."""
    name: str
    accuracy: Optional[float] = None
    f1_score: Optional[float] = None


class ModelsStatusResponse(BaseModel):
    """Response schema for models status."""
    available_models: list[ModelInfo]
    best_model: str


@router.post(
    "/predict",
    response_model=EmailPredictionResponse,
    summary="Predict phishing email",
    description="Uses the trained ML model (SVM, 96.8% accuracy) to classify an email as phishing or safe based on subject and body text.",
    responses={
        503: {"description": "ML model not available"},
    },
)
async def predict_phishing(
    request: EmailPredictionRequest,
    current_user: User = Depends(get_current_active_user)
):
    """
    Predict if an email is phishing based on subject and body.
    
    Uses the best performing model (SVM with 96.8% accuracy).
    """
    settings = get_settings()
    
    try:
        api = get_phishing_api(settings.ML_MODELS_DIR)
        result = api.predict(
            request.subject,
            request.body
        )
        
        return EmailPredictionResponse(
            is_phishing=result.is_phishing,
            phishing_probability=result.phishing_probability,
            safe_probability=result.safe_probability,
            confidence=result.confidence,
            category=result.category,
            model_used=result.model_used
        )
    except ValueError as e:
        logger.error(f"Prediction error: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Unexpected prediction error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Prediction failed"
        )


@router.get(
    "/models",
    response_model=ModelsStatusResponse,
    summary="Get ML models status",
    description="Returns information about available ML models including accuracy and F1 scores.",
)
async def get_models_status(
    current_user: User = Depends(get_current_active_user)
):
    """Get status of available ML models."""
    settings = get_settings()
    
    api = get_phishing_api(settings.ML_MODELS_DIR)
    
    models_info = []
    import json
    results_path = f"{settings.ML_MODELS_DIR}/classical_ml_results.json"
    try:
        with open(results_path, 'r') as f:
            results = json.load(f)
        for name in ['logistic_regression', 'svm', 'xgboost']:
            if name in api.classical_models:
                model_info = {"name": name}
                if name in results:
                    model_info["accuracy"] = results[name].get("accuracy")
                    model_info["f1_score"] = results[name].get("f1_score")
                models_info.append(ModelInfo(**model_info))
    except Exception as e:
        logger.warning(f"Could not load model metrics: {e}")
        for name in api.classical_models.keys():
            models_info.append(ModelInfo(name=name))
    
    return ModelsStatusResponse(
        available_models=models_info,
        best_model=settings.ML_BEST_MODEL
    )