"""
Ensemble Detector Module

This module combines ML-based predictions (text classifier + feature detector)
with Threat Intelligence results to produce a final phishing assessment.
"""

import logging
from typing import Dict, Any, Optional, List

from app.config import get_settings

logger = logging.getLogger(__name__)


class EnsembleDetector:
    """
    Ensemble detector combining ML models and Threat Intelligence.
    
    Final Score = ML_WEIGHT * ML_Score + TI_WEIGHT * TI_Score
    
    Default: ML_WEIGHT=0.4, TI_WEIGHT=0.6
    """
    
    def __init__(self):
        self.settings = get_settings()
        self.ml_weight = self.settings.ML_WEIGHT
        self.ti_weight = self.settings.TI_WEIGHT
        
        self.text_classifier = None
        self.feature_detector = None
        self.threat_intel = None
        
        self._load_components()
    
    def _load_components(self):
        """Load ML components."""
        try:
            from app.ml.text_classifier import get_text_classifier
            self.text_classifier = get_text_classifier()
            logger.info("Text classifier loaded")
        except Exception as e:
            logger.warning(f"Could not load text classifier: {e}")
        
        try:
            from app.ml.phishing_detector import get_phishing_detector
            self.feature_detector = get_phishing_detector()
            logger.info("Feature detector loaded")
        except Exception as e:
            logger.warning(f"Could not load feature detector: {e}")
        
        try:
            from app.services.threat_intel import get_threat_intel_service
            self.threat_intel = get_threat_intel_service()
            logger.info("Threat intel service loaded")
        except Exception as e:
            logger.warning(f"Could not load threat intel service: {e}")
    
    def analyze(
        self,
        parsed_email: Dict[str, Any],
        sender_email: str,
        urls: List[str],
        attachment_hashes: List[str]
    ) -> Dict[str, Any]:
        """
        Perform ensemble analysis combining ML and TI.
        
        Args:
            parsed_email: Parsed email data from EmailParser
            sender_email: Sender email address
            urls: List of URLs in the email
            attachment_hashes: List of attachment file hashes
            
        Returns:
            Comprehensive analysis result
        """
        warnings = []
        ml_components = {}
        ti_result = None
        
        ml_score = self._get_ml_score(parsed_email, ml_components)
        
        if not ml_components.get('text_classifier_trained', False):
            warnings.append("ML: Text classifier not trained, using feature detector only")
        if not ml_components.get('feature_detector_trained', False):
            warnings.append("ML: Feature detector not trained, using text classifier only")
        
        if self.threat_intel:
            import asyncio
            try:
                ti_result = asyncio.run(
                    self.threat_intel.analyze_email_threats(
                        sender_email=sender_email,
                        urls=urls,
                        attachment_hashes=attachment_hashes
                    )
                )
                ti_score = ti_result.get('overall_risk_score', 0.0)
                
                if ti_result.get('warnings'):
                    warnings.extend([f"TI: {w}" for w in ti_result['warnings']])
            except Exception as e:
                logger.error(f"TI analysis failed: {e}")
                ti_score = 0.0
                warnings.append(f"TI: Analysis failed - {str(e)}")
        else:
            ti_score = 0.0
            warnings.append("TI: Service not available")
        
        if ml_score is None:
            ml_score = 0.0
            warnings.append("ML: Both models unavailable, using TI only")
        
        final_score = self._calculate_ensemble_score(ml_score, ti_score)
        
        category = self._categorize_score(final_score)
        confidence = self._calculate_confidence(ml_components, ti_result, warnings)
        
        return {
            'is_phishing': final_score >= 0.5,
            'phishing_probability': final_score,
            'safe_probability': 1 - final_score,
            'risk_category': category,
            'confidence': confidence,
            'final_score': final_score,
            'ml_score': ml_score,
            'ti_score': ti_score,
            'ml_weight': self.ml_weight,
            'ti_weight': self.ti_weight,
            'ml_components': ml_components,
            'ti_result': ti_result,
            'warnings': warnings,
            'indicators': self._extract_indicators(ml_components, ti_result)
        }
    
    def _get_ml_score(self, parsed_email: Dict[str, Any], components: Dict) -> Optional[float]:
        """Get ML-based score from text classifier and feature detector."""
        text_score = None
        feature_score = None
        
        if self.text_classifier:
            text_classifier_info = self.text_classifier.get_model_info()
            components['text_classifier_trained'] = text_classifier_info.get('is_trained', False)
            components['text_classifier_info'] = text_classifier_info
            
            if text_classifier_info.get('is_trained'):
                subject = parsed_email.get('headers', {}).get('subject', '')
                body = parsed_email.get('body', {}).get('text', '')
                
                text_result = self.text_classifier.predict_proba(subject, body)
                text_score = text_result.get('phishing_probability', 0.0)
                components['text_classifier_result'] = text_result
        
        if self.feature_detector:
            feature_detector_info = self.feature_detector.get_model_info()
            components['feature_detector_trained'] = feature_detector_info.get('is_trained', False)
            components['feature_detector_info'] = feature_detector_info
            
            if feature_detector_info.get('is_trained'):
                feature_result = self.feature_detector.predict(parsed_email)
                feature_score = feature_result.get('phishing_probability', 0.0)
                components['feature_detector_result'] = feature_result
        
        if text_score is not None and feature_score is not None:
            return (text_score + feature_score) / 2.0
        elif text_score is not None:
            return text_score
        elif feature_score is not None:
            return feature_score
        
        return None
    
    def _calculate_ensemble_score(self, ml_score: float, ti_score: float) -> float:
        """Calculate final ensemble score."""
        if ml_score == 0.0 and ti_score == 0.0:
            return 0.0
        
        ml_available = ml_score > 0.0
        ti_available = ti_score > 0.0
        
        if not ml_available:
            return ti_score
        if not ti_available:
            return ml_score
        
        return (self.ml_weight * ml_score) + (self.ti_weight * ti_score)
    
    def _categorize_score(self, score: float) -> str:
        """Categorize score into risk levels."""
        if score >= 0.9:
            return 'phishing'
        elif score >= 0.7:
            return 'likely_phishing'
        elif score >= 0.5:
            return 'suspicious'
        elif score >= 0.3:
            return 'low_risk'
        return 'safe'
    
    def _calculate_confidence(
        self,
        ml_components: Dict,
        ti_result: Optional[Dict],
        warnings: List[str]
    ) -> float:
        """Calculate confidence in the assessment."""
        confidence = 0.5
        
        ml_trained = (
            ml_components.get('text_classifier_trained', False) or
            ml_components.get('feature_detector_trained', False)
        )
        
        if ml_trained:
            confidence += 0.2
        
        if ti_result:
            ti_confidence = ti_result.get('confidence', 0.0)
            confidence += ti_confidence * 0.3
        
        warning_penalty = min(len(warnings) * 0.05, 0.2)
        confidence -= warning_penalty
        
        return max(0.0, min(1.0, confidence))
    
    def _extract_indicators(
        self,
        ml_components: Dict,
        ti_result: Optional[Dict]
    ) -> List[str]:
        """Extract indicators from ML and TI results."""
        indicators = []
        
        if ml_components.get('text_classifier_result'):
            ml_result = ml_components['text_classifier_result']
            if ml_result.get('phishing_probability', 0) > 0.7:
                indicators.append("ML: High phishing probability from text")
        
        if ml_components.get('feature_detector_result'):
            ml_result = ml_components['feature_detector_result']
            if ml_result.get('phishing_probability', 0) > 0.7:
                indicators.append("ML: High phishing probability from features")
        
        if ti_result:
            ti_indicators = ti_result.get('indicators', [])
            indicators.extend([f"TI: {ind}" for ind in ti_indicators])
        
        return indicators


_ensemble_detector_instance: Optional[EnsembleDetector] = None


def get_ensemble_detector() -> EnsembleDetector:
    """Get singleton instance of ensemble detector."""
    global _ensemble_detector_instance
    if _ensemble_detector_instance is None:
        _ensemble_detector_instance = EnsembleDetector()
    return _ensemble_detector_instance