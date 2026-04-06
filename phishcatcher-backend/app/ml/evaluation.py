"""
Evaluation Module

This module provides model evaluation, comparison, and explainability:
- Model comparison (all models)
- SHAP for tree-based models
- LIME for text models
"""

import os
import json
import logging
from typing import Dict, List, Any, Optional, Tuple
import numpy as np

from sklearn.metrics import (
    accuracy_score, precision_score, recall_score, f1_score,
    classification_report, confusion_matrix, roc_auc_score,
    roc_curve, precision_recall_curve
)

logger = logging.getLogger(__name__)

try:
    import shap
    SHAP_AVAILABLE = True
except ImportError:
    SHAP_AVAILABLE = False
    logger.warning("SHAP not available")

try:
    from lime.lime_text import LimeTextExplainer
    LIME_AVAILABLE = True
except ImportError:
    LIME_AVAILABLE = False
    logger.warning("LIME not available")


class ModelEvaluator:
    """
    Evaluator for comparing models and generating explanations.
    
    Features:
    - Compare all models (LR, SVM, XGBoost, BERT, Hybrid)
    - SHAP explanations for tree-based
    - LIME explanations for text
    """
    
    def __init__(self):
        self.results: Dict[str, Dict] = {}
        self.best_model_name: Optional[str] = None
        self.best_model_score: float = 0.0
    
    def compare_models(
        self,
        model_results: Dict[str, Dict],
        save_path: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Compare multiple model results.
        
        Args:
            model_results: Dictionary of {model_name: metrics}
            save_path: Optional path to save comparison
            
        Returns:
            Comparison summary
        """
        self.results = model_results
        
        comparison = {
            'models': [],
            'best_model': None,
            'rankings': {}
        }
        
        metrics = ['accuracy', 'precision', 'recall', 'f1_score', 'roc_auc']
        
        for model_name, metrics_dict in model_results.items():
            if 'f1_score' not in metrics_dict:
                continue
            
            model_comparison = {
                'name': model_name,
                'metrics': {m: metrics_dict.get(m, 0.0) for m in metrics}
            }
            comparison['models'].append(model_comparison)
            
            if metrics_dict['f1_score'] > self.best_model_score:
                self.best_model_score = metrics_dict['f1_score']
                self.best_model_name = model_name
        
        comparison['best_model'] = self.best_model_name
        
        for metric in metrics:
            ranked = sorted(
                comparison['models'],
                key=lambda x: x['metrics'].get(metric, 0.0),
                reverse=True
            )
            comparison['rankings'][metric] = [m['name'] for m in ranked]
        
        if save_path:
            with open(save_path, 'w') as f:
                json.dump(comparison, f, indent=2)
            logger.info(f"Saved model comparison to {save_path}")
        
        return comparison
    
    def print_comparison(self, comparison: Dict):
        """Print formatted comparison results."""
        print("\n" + "="*80)
        print("MODEL COMPARISON RESULTS")
        print("="*80)
        
        print(f"\nBest Model: {comparison['best_model']}")
        print("\nRankings by Metric:")
        
        for metric, ranking in comparison['rankings'].items():
            print(f"\n  {metric.upper()}:")
            for i, model in enumerate(ranking, 1):
                score = next((m['metrics'].get(metric, 0.0) for m in comparison['models'] if m['name'] == model), 0.0)
                print(f"    {i}. {model}: {score:.4f}")
        
        print("\n" + "-"*80)
        print("Detailed Metrics:")
        print("-"*80)
        
        for model in comparison['models']:
            print(f"\n{model['name']}:")
            for metric, value in model['metrics'].items():
                print(f"  {metric}: {value:.4f}")
        
        print("\n" + "="*80)
    
    def generate_classification_report(
        self,
        y_true: List[int],
        y_pred: List[int],
        model_name: str = "model"
    ) -> str:
        """Generate sklearn classification report."""
        return classification_report(y_true, y_pred, target_names=['legitimate', 'phishing'])
    
    def generate_confusion_matrix(
        self,
        y_true: List[int],
        y_pred: List[int]
    ) -> Dict:
        """Generate confusion matrix visualization data."""
        cm = confusion_matrix(y_true, y_pred)
        
        return {
            'matrix': cm.tolist(),
            'labels': ['legitimate', 'phishing'],
            'tn': int(cm[0][0]),
            'fp': int(cm[0][1]),
            'fn': int(cm[1][0]),
            'tp': int(cm[1][1])
        }
    
    def compute_roc_curve(
        self,
        y_true: List[int],
        y_prob: List[float]
    ) -> Dict:
        """Compute ROC curve data."""
        fpr, tpr, thresholds = roc_curve(y_true, y_prob)
        auc = roc_auc_score(y_true, y_prob)
        
        return {
            'fpr': fpr.tolist(),
            'tpr': tpr.tolist(),
            'thresholds': thresholds.tolist(),
            'auc': float(auc)
        }
    
    def compute_precision_recall_curve(
        self,
        y_true: List[int],
        y_prob: List[float]
    ) -> Dict:
        """Compute precision-recall curve data."""
        precision, recall, thresholds = precision_recall_curve(y_true, y_prob)
        
        return {
            'precision': precision.tolist(),
            'recall': recall.tolist(),
            'thresholds': thresholds.tolist()
        }


class SHAPExplainer:
    """SHAP explainer for tree-based models."""
    
    def __init__(self, model, feature_names: Optional[List[str]] = None):
        if not SHAP_AVAILABLE:
            raise ImportError("SHAP not available")
        
        self.model = model
        self.feature_names = feature_names
        self.explainer = None
    
    def create_explainer(self, X: np.ndarray):
        """Create SHAP explainer."""
        if hasattr(self.model, 'predict_proba'):
            self.explainer = shap.TreeExplainer(self.model)
        else:
            logger.warning("Model doesn't support SHAP explainer")
    
    def explain_instance(self, X: np.ndarray) -> Dict:
        """Explain a single instance."""
        if self.explainer is None:
            raise ValueError("Create explainer first with create_explainer()")
        
        shap_values = self.explainer.shap_values(X)
        
        if isinstance(shap_values, list):
            shap_values = shap_values[1]
        
        feature_importance = []
        if self.feature_names and len(shap_values[0]) == len(self.feature_names):
            feature_importance = [
                {'feature': self.feature_names[i], 'value': float(shap_values[0][i])}
                for i in range(len(shap_values[0]))
            ]
            feature_importance.sort(key=lambda x: abs(x['value']), reverse=True)
        
        return {
            'shap_values': shap_values[0].tolist(),
            'base_value': float(self.explainer.expected_value[0]) if isinstance(self.explainer.expected_value, list) else float(self.explainer.expected_value),
            'feature_importance': feature_importance[:20]
        }
    
    def explain_batch(self, X: np.ndarray, max_samples: int = 100) -> Dict:
        """Explain multiple instances."""
        X_sample = X[:max_samples] if len(X) > max_samples else X
        
        shap_values = self.explainer.shap_values(X_sample)
        
        if isinstance(shap_values, list):
            shap_values = shap_values[1]
        
        mean_importance = np.abs(shap_values).mean(axis=0).tolist()
        
        feature_importance = []
        if self.feature_names and len(mean_importance) == len(self.feature_names):
            feature_importance = [
                {'feature': self.feature_names[i], 'importance': float(mean_importance[i])}
                for i in range(len(mean_importance))
            ]
            feature_importance.sort(key=lambda x: x['importance'], reverse=True)
        
        return {
            'mean_abs_shap': mean_importance,
            'feature_importance': feature_importance[:20],
            'num_samples': len(X_sample)
        }


class LIMEExplainer:
    """LIME explainer for text models."""
    
    def __init__(self, classifier_fn):
        if not LIME_AVAILABLE:
            raise ImportError("LIME not available")
        
        self.classifier_fn = classifier_fn
        self.explainer = LimeTextExplainer()
    
    def explain_instance(self, text: str, num_features: int = 10) -> Dict:
        """Explain a single text instance."""
        explanation = self.explainer.explain_instance(
            text,
            self.classifier_fn,
            num_features=num_features,
            num_samples=500
        )
        
        features = []
        for feature, weight in explanation.as_list():
            features.append({
                'feature': feature,
                'weight': float(weight)
            })
        
        return {
            'text': text,
            'features': features,
            'prediction': explanation.predict_proba[1],
            'label': 'phishing' if explanation.predict_proba[1] > 0.5 else 'legitimate'
        }


def explain_with_shap(model, X: np.ndarray, feature_names: Optional[List[str]] = None) -> Dict:
    """
    Quick SHAP explanation function.
    
    Usage:
        explanation = explain_with_shap(model, X_test, feature_names)
    """
    explainer = SHAPExplainer(model, feature_names)
    explainer.create_explainer(X)
    return explainer.explain_instance(X)


def explain_with_lime(text: str, classifier_fn, num_features: int = 10) -> Dict:
    """
    Quick LIME explanation function.
    
    Usage:
        explanation = explain_with_lime(email_text, classifier.predict_proba)
    """
    explainer = LIMEExplainer(classifier_fn)
    return explainer.explain_instance(text, num_features)