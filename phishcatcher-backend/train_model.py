#!/usr/bin/env python3
"""
PhishCatcher ML Model Training Script

This script trains the phishing detection model using datasets from:
- Archive phishing email dataset (phishing_email.csv)
- Synthetic phishing samples (fallback)

Usage: 
    python train_model.py --data-source archive --sample-size 20000
    python train_model.py --data-source synthetic
"""

import os
import sys
import argparse
import pandas as pd
import numpy as np
from pathlib import Path
from typing import Dict, List, Tuple, Optional
import logging
from datetime import datetime
import re

from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, classification_report, confusion_matrix

sys.path.append(str(Path(__file__).parent / "app"))

from ml.feature_engineering import FeatureEngineer
from ml.phishing_detector import PhishingDetector
from ml.text_classifier import TextClassifier

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class ModelTrainer:
    """Handles training of the phishing detection models."""
    
    def __init__(self, data_dir: str = "data", model_dir: str = "models"):
        self.data_dir = Path(data_dir)
        self.model_dir = Path(model_dir)
        self.feature_engineer = FeatureEngineer()
        
        self.model_dir.mkdir(exist_ok=True)
    
    def load_archive_dataset(self, archive_path: Path, sample_size: Optional[int] = None) -> Tuple[List[Dict], List[Dict]]:
        """
        Load phishing email dataset from archive CSV.
        
        Args:
            archive_path: Path to phishing_email.csv
            sample_size: Optional stratified sample size
            
        Returns:
            Tuple of (phishing_emails, legitimate_emails)
        """
        logger.info(f"Loading archive dataset from {archive_path}")
        
        df = pd.read_csv(archive_path)
        logger.info(f"Total emails in dataset: {len(df)}")
        
        phishing_df = df[df['label'] == 1].copy()
        legitimate_df = df[df['label'] == 0].copy()
        
        logger.info(f"Phishing emails: {len(phishing_df)}")
        logger.info(f"Legitimate emails: {len(legitimate_df)}")
        
        if sample_size:
            sample_per_class = sample_size // 2
            phishing_sample = phishing_df.sample(n=min(sample_per_class, len(phishing_df)), random_state=42)
            legitimate_sample = legitimate_df.sample(n=min(sample_per_class, len(legitimate_df)), random_state=42)
            df = pd.concat([phishing_sample, legitimate_sample]).reset_index(drop=True)
            logger.info(f"Sampled {len(df)} emails (stratified)")
        
        phishing_emails = []
        legitimate_emails = []
        
        for _, row in df.iterrows():
            text_combined = str(row.get('text_combined', ''))
            subject, body, sender = self._parse_text_combined(text_combined)
            
            email_data = {
                'subject': subject,
                'body': body,
                'sender': sender,
                'label': int(row.get('label', 0))
            }
            
            if row.get('label') == 1:
                phishing_emails.append(email_data)
            else:
                legitimate_emails.append(email_data)
        
        return phishing_emails, legitimate_emails
    
    def _parse_text_combined(self, text: str) -> Tuple[str, str, str]:
        """
        Parse the combined text field into subject, body, sender.
        
        The text_combined field contains: sender, subject, date, body
        """
        lines = text.split('\n')
        
        sender = ""
        subject = ""
        body_parts = []
        
        for i, line in enumerate(lines[:10]):
            line = line.strip()
            if not line:
                continue
            
            if i == 0 and '@' in line:
                sender = line
            elif 'subject' in line.lower() and i < 3:
                subject = line
            elif i >= 3 and len(line) > 10:
                body_parts.append(line)
        
        body = ' '.join(body_parts)
        
        if not subject:
            subject = ' '.join(lines[:5]) if lines else ''
            subject = subject[:200]
        
        if not body:
            body = ' '.join(lines[5:15]) if len(lines) > 5 else ''
        
        return subject[:200], body[:5000], sender
    
    def load_synthetic_datasets(self) -> Tuple[List[Dict], List[Dict]]:
        """Load synthetic phishing and legitimate email samples."""
        phishing_emails = self._create_synthetic_phishing_samples()
        legitimate_emails = self._create_synthetic_legitimate_samples()
        
        logger.info(f"Loaded {len(phishing_emails)} synthetic phishing emails")
        logger.info(f"Loaded {len(legitimate_emails)} synthetic legitimate emails")
        
        return phishing_emails, legitimate_emails
    
    def _create_synthetic_phishing_samples(self) -> List[Dict]:
        """Create synthetic phishing email samples."""
        samples = [
            {
                "subject": "URGENT: Your Account Will Be Suspended",
                "body": "Dear valued customer, Your account will be suspended within 24 hours due to suspicious activity. Please click here immediately to verify your account. Failure to verify will result in permanent account closure. Best regards, Security Team",
                "sender": "security@paypal-update.com",
                "label": 1
            },
            {
                "subject": "You've Won $1,000,000!!!",
                "body": "CONGRATULATIONS! You are our lucky winner! You have won $1,000,000 in our international lottery. To claim your prize, please send your bank details. Act now! This offer expires in 24 hours!",
                "sender": "winner@international-lottery.com",
                "label": 1
            },
            {
                "subject": "Invoice Overdue - Immediate Payment Required",
                "body": "Your invoice is overdue. Please pay immediately to avoid late fees. Click here to pay. Amount due: $999.99. Failure to pay will result in legal action.",
                "sender": "billing@fake-company.com",
                "label": 1
            },
            {
                "subject": "Microsoft Security Alert - Password Reset Required",
                "body": "We detected unusual activity on your Microsoft account. Please reset your password immediately. If you don't reset your password, your account will be blocked.",
                "sender": "security@microsoft-alert.com",
                "label": 1
            },
            {
                "subject": "COVID-19 Relief Fund - Claim Your Money",
                "body": "You are eligible for COVID-19 relief funds. Click here to claim your $5,000 payment. Limited time offer! Act now!",
                "sender": "relief@covid-gov.org",
                "label": 1
            }
        ]
        
        expanded = []
        for sample in samples:
            for i in range(20):
                new_sample = sample.copy()
                new_sample['sender'] = sample['sender'].replace('.com', f'.{i}.com')
                new_sample['body'] = sample['body'] + f" Reference: {i:04d}"
                expanded.append(new_sample)
        
        return expanded
    
    def _create_synthetic_legitimate_samples(self) -> List[Dict]:
        """Create synthetic legitimate email samples."""
        samples = [
            {
                "subject": "Team Meeting - Project Update",
                "body": "Hi team, Just a reminder about our project meeting tomorrow at 2 PM. We'll be discussing the Q4 roadmap and deliverables. Please come prepared with your status updates. Best regards, John",
                "sender": "john.doe@company.com",
                "label": 0
            },
            {
                "subject": "Monthly Newsletter - Company Updates",
                "body": "Dear Team, Here are our monthly updates: 1. New client onboarding completed 2. Q3 revenue exceeded targets by 15% 3. New product launch scheduled for next month. Thank you for your continued hard work!",
                "sender": "newsletter@company.com",
                "label": 0
            },
            {
                "subject": "Your Order Confirmation #12345",
                "body": "Thank you for your order! Order Details: Item: Professional License, Quantity: 1, Total: $299.99, Expected Delivery: 3-5 business days. Track your order at company.com",
                "sender": "orders@legitimate-store.com",
                "label": 0
            },
            {
                "subject": "Welcome to Our Platform!",
                "body": "Welcome to our platform! Your account has been successfully created. Here's how to get started: 1. Complete your profile 2. Explore our features 3. Connect with team members. Need help? Check our FAQ.",
                "sender": "welcome@platform.com",
                "label": 0
            },
            {
                "subject": "System Maintenance Notification",
                "body": "Scheduled Maintenance Notice: Our system will undergo maintenance on Saturday from 2 AM to 6 AM EST. Services will be temporarily unavailable during this time. We apologize for any inconvenience.",
                "sender": "it@company.com",
                "label": 0
            }
        ]
        
        expanded = []
        for sample in samples:
            for i in range(20):
                new_sample = sample.copy()
                new_sample['body'] = sample['body'] + f" Sent from: Office-{i}"
                expanded.append(new_sample)
        
        return expanded
    
    def prepare_training_data(
        self,
        phishing_emails: List[Dict],
        legitimate_emails: List[Dict]
    ) -> Tuple[np.ndarray, np.ndarray, List[str], List[str]]:
        """
        Prepare training data for feature extraction.
        
        Returns:
            X: Feature matrix
            y: Labels
            subjects: List of subjects
            bodies: List of bodies
        """
        logger.info("Preparing training data...")
        
        all_emails = phishing_emails + legitimate_emails
        np.random.shuffle(all_emails)
        
        subjects = [e['subject'] for e in all_emails]
        bodies = [e['body'] for e in all_emails]
        labels = [e['label'] for e in all_emails]
        
        logger.info(f"Total training samples: {len(all_emails)}")
        logger.info(f"Phishing: {sum(labels)}, Legitimate: {len(labels) - sum(labels)}")
        
        return np.array(subjects), np.array(bodies), np.array(labels)
    
    def extract_features_for_training(self, subjects: List[str], bodies: List[str]) -> np.ndarray:
        """Extract ML features from email subject/body for training."""
        logger.info("Extracting features from emails...")
        
        features_list = []
        
        for i, (subject, body) in enumerate(zip(subjects, bodies)):
            if i % 500 == 0:
                logger.info(f"Processing email {i}/{len(subjects)}")
            
            parsed_email = {
                'headers': {
                    'subject': subject,
                    'from_address': '',
                    'sender_domain': '',
                    'return_path_domain': '',
                    'reply_to_mismatch': False,
                    'authentication_results': {'spf': None, 'dkim': None, 'dmarc': None}
                },
                'body': {
                    'text': body,
                    'text_length': len(body),
                    'has_text': bool(body),
                    'html': '',
                    'html_length': 0,
                    'has_html': False
                },
                'links': [],
                'attachments': [],
                'metadata': {
                    'is_multipart': False,
                    'received_count': 0
                }
            }
            
            features = self.feature_engineer.extract_all_features(subject, body)
            features_list.append(features)
        
        if not features_list:
            return np.array([])
        
        # Get feature names and ensure consistent feature dimension
        feature_names = self.feature_engineer.get_feature_importance_names()
        
        # Create feature matrix with consistent columns
        feature_matrix = np.zeros((len(features_list), len(feature_names)))
        for i, feats in enumerate(features_list):
            for j, fname in enumerate(feature_names):
                feature_matrix[i, j] = feats.get(fname, 0.0)
        
        return feature_matrix
    
    def train_text_classifier(
        self,
        subjects: List[str],
        bodies: List[str],
        labels: np.ndarray
    ) -> Dict:
        """Train the text classifier (TF-IDF + XGBoost)."""
        logger.info("Training text classifier...")
        
        classifier = TextClassifier()
        
        subjects_list = [str(s) for s in subjects]
        bodies_list = [str(b) for b in bodies]
        
        metrics = classifier.train(subjects_list, bodies_list, labels.tolist())
        
        classifier.save_model()
        
        logger.info(f"Text classifier training completed: {metrics}")
        
        return metrics
    
    def train_feature_detector(
        self,
        X_features: np.ndarray,
        labels: np.ndarray
    ) -> Dict:
        """Train the feature-based detector."""
        logger.info("Training feature detector...")
        
        detector = PhishingDetector()
        metrics = detector.train(X_features, labels)
        
        detector.save_model()
        
        logger.info(f"Feature detector training completed: {metrics}")
        
        return metrics
    
    def run_training(
        self,
        data_source: str = "synthetic",
        sample_size: Optional[int] = None
    ):
        """Run the complete training pipeline."""
        logger.info(f"Starting PhishCatcher model training (source: {data_source})...")
        
        try:
            if data_source == "archive":
                archive_path = Path(__file__).parent.parent / "archive" / "phishing_email.csv"
                if not archive_path.exists():
                    logger.error(f"Archive file not found: {archive_path}")
                    logger.info("Falling back to synthetic data...")
                    data_source = "synthetic"
                else:
                    phishing_emails, legitimate_emails = self.load_archive_dataset(archive_path, sample_size)
            else:
                phishing_emails, legitimate_emails = self.load_synthetic_datasets()
            
            subjects, bodies, labels = self.prepare_training_data(phishing_emails, legitimate_emails)
            
            X_train_sub, X_test_sub, y_train, y_test = train_test_split(
                subjects, labels, test_size=0.2, random_state=42, stratify=labels
            )
            
            _, X_test_bodies, _, _ = train_test_split(
                bodies, labels, test_size=0.2, random_state=42, stratify=labels
            )
            
            # Split bodies to match subjects split
            X_train_bodies, X_test_bodies, _, _ = train_test_split(
                bodies, labels, test_size=0.2, random_state=42, stratify=labels
            )
            
            logger.info(f"Training set: {len(X_train_sub)} samples")
            logger.info(f"Test set: {len(X_test_sub)} samples")
            
            logger.info("\n" + "="*50)
            logger.info("TRAINING TEXT CLASSIFIER")
            logger.info("="*50)
            text_metrics = self.train_text_classifier(
                X_train_sub.tolist(),
                X_train_bodies.tolist(),
                y_train
            )
            
            logger.info("\n" + "="*50)
            logger.info("TRAINING FEATURE DETECTOR")
            logger.info("="*50)
            X_train_features = self.extract_features_for_training(X_train_sub.tolist(), X_train_bodies.tolist())
            feature_metrics = self.train_feature_detector(X_train_features, y_train.tolist())
            
            final_metrics = {
                'text_classifier': text_metrics,
                'feature_detector': feature_metrics,
                'training_date': datetime.now().isoformat(),
                'training_samples': len(X_train_sub),
                'test_samples': len(X_test_sub)
            }
            
            import json
            metrics_path = self.model_dir / "training_metrics.json"
            with open(metrics_path, 'w') as f:
                json.dump(final_metrics, f, indent=2)
            
            logger.info("\n" + "="*50)
            logger.info("TRAINING COMPLETED SUCCESSFULLY!")
            logger.info("="*50)
            logger.info(f"Text Classifier - Accuracy: {text_metrics['accuracy']:.4f}, F1: {text_metrics['f1_score']:.4f}")
            logger.info(f"Feature Detector - Accuracy: {feature_metrics['accuracy']:.4f}, F1: {feature_metrics['f1_score']:.4f}")
            logger.info(f"Models saved to: {self.model_dir}")
            
            return final_metrics
            
        except Exception as e:
            logger.error(f"Training failed: {e}")
            raise


def main():
    parser = argparse.ArgumentParser(description="Train PhishCatcher ML models")
    parser.add_argument("--data-source", default="synthetic", 
                        choices=["synthetic", "archive"],
                        help="Data source: synthetic or archive")
    parser.add_argument("--sample-size", type=int, default=None,
                        help="Number of samples for stratified training (archive only)")
    parser.add_argument("--model-dir", default="models", help="Model directory")
    
    args = parser.parse_args()
    
    trainer = ModelTrainer(model_dir=args.model_dir)
    
    try:
        metrics = trainer.run_training(
            data_source=args.data_source,
            sample_size=args.sample_size
        )
        
        print("\n" + "="*50)
        print("TRAINING COMPLETED SUCCESSFULLY!")
        print("="*50)
        
    except Exception as e:
        print(f"\nTraining failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()