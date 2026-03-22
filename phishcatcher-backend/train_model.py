#!/usr/bin/env python3
"""
PhishCatcher ML Model Training Script

This script trains the phishing detection model using datasets from:
- Kaggle Phishing Dataset
- Enron Email Dataset (for legitimate emails)
- Synthetic phishing samples

Usage: python train_model.py [--data-dir DATA_DIR] [--model-dir MODEL_DIR]
"""

import os
import sys
import argparse
import pandas as pd
import numpy as np
from pathlib import Path
from typing import Dict, List, Tuple
import logging
from datetime import datetime

# Add the app directory to Python path
sys.path.append(str(Path(__file__).parent.parent / "app"))

from ml.feature_extractor import FeatureExtractor
from ml.phishing_detector import PhishingDetector
from ml.email_parser import EmailParser

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class ModelTrainer:
    """Handles training of the phishing detection model."""
    
    def __init__(self, data_dir: str = "data", model_dir: str = "models"):
        """Initialize the trainer."""
        self.data_dir = Path(data_dir)
        self.model_dir = Path(model_dir)
        self.feature_extractor = FeatureExtractor()
        self.email_parser = EmailParser()
        
        # Create directories if they don't exist
        self.data_dir.mkdir(exist_ok=True)
        self.model_dir.mkdir(exist_ok=True)
        
    def load_datasets(self) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """Load phishing and legitimate email datasets."""
        logger.info("Loading datasets...")
        
        # Load phishing emails
        phishing_data = []
        
        # Try to load Kaggle phishing dataset
        kaggle_file = self.data_dir / "phishing_emails.csv"
        if kaggle_file.exists():
            logger.info(f"Loading Kaggle dataset from {kaggle_file}")
            df_kaggle = pd.read_csv(kaggle_file)
            phishing_data.extend(df_kaggle.to_dict('records'))
        else:
            logger.warning(f"Kaggle dataset not found at {kaggle_file}")
            logger.info("Creating synthetic phishing samples...")
            phishing_data.extend(self._create_synthetic_phishing_samples())
        
        # Load legitimate emails
        legitimate_data = []
        
        # Try to load Enron dataset
        enron_file = self.data_dir / "enron_emails.csv"
        if enron_file.exists():
            logger.info(f"Loading Enron dataset from {enron_file}")
            df_enron = pd.read_csv(enron_file)
            legitimate_data.extend(df_enron.to_dict('records'))
        else:
            logger.warning(f"Enron dataset not found at {enron_file}")
            logger.info("Creating synthetic legitimate samples...")
            legitimate_data.extend(self._create_synthetic_legitimate_samples())
        
        # Convert to DataFrames
        phishing_df = pd.DataFrame(phishing_data)
        legitimate_df = pd.DataFrame(legitimate_data)
        
        logger.info(f"Loaded {len(phishing_df)} phishing emails")
        logger.info(f"Loaded {len(legitimate_df)} legitimate emails")
        
        return phishing_df, legitimate_df
    
    def _create_synthetic_phishing_samples(self) -> List[Dict]:
        """Create synthetic phishing email samples."""
        samples = [
            {
                "subject": "URGENT: Your Account Will Be Suspended",
                "body": """
                Dear valued customer,
                
                Your account will be suspended within 24 hours due to suspicious activity.
                Please click here immediately to verify your account:
                http://bit.ly/verify-now-urgent
                
                Failure to verify will result in permanent account closure.
                
                Best regards,
                Security Team
                """,
                "sender": "security@paypal-update.com",
                "is_phishing": 1
            },
            {
                "subject": "You've Won $1,000,000!!!",
                "body": """
                CONGRATULATIONS! You are our lucky winner!
                
                You have won $1,000,000 in our international lottery.
                To claim your prize, please send your bank details to:
                winner@lottery-scams.com
                
                Act now! This offer expires in 24 hours!
                
                Sincerely,
                Lottery Commission
                """,
                "sender": "winner@international-lottery.com",
                "is_phishing": 1
            },
            {
                "subject": "Invoice Overdue - Immediate Payment Required",
                "body": """
                Your invoice is overdue. Please pay immediately to avoid late fees.
                
                Click here to pay: http://fake-invoice.com/pay-now
                Amount due: $999.99
                
                Failure to pay will result in legal action.
                
                Accounting Department
                """,
                "sender": "billing@fake-company.com",
                "is_phishing": 1
            },
            {
                "subject": "Microsoft Security Alert - Password Reset Required",
                "body": """
                We detected unusual activity on your Microsoft account.
                Please reset your password immediately:
                http://microsoft-security-reset.com/reset
                
                If you don't reset your password, your account will be blocked.
                
                Microsoft Security Team
                """,
                "sender": "security@microsoft-alert.com",
                "is_phishing": 1
            },
            {
                "subject": "COVID-19 Relief Fund - Claim Your Money",
                "body": """
                You are eligible for COVID-19 relief funds.
                
                Click here to claim your $5,000 payment:
                http://covid-relief-scam.com/claim
                
                Limited time offer! Act now!
                
                Relief Fund Administration
                """,
                "sender": "relief@covid-gov.org",
                "is_phishing": 1
            }
        ]
        
        # Create more variations
        expanded_samples = []
        for sample in samples:
            for i in range(10):  # Create 10 variations each
                new_sample = sample.copy()
                # Add some variations
                new_sample["sender"] = sample["sender"].replace(".com", f".{i}.com")
                new_sample["body"] = sample["body"] + f"\n\nReference: {i:04d}"
                expanded_samples.append(new_sample)
        
        return expanded_samples
    
    def _create_synthetic_legitimate_samples(self) -> List[Dict]:
        """Create synthetic legitimate email samples."""
        samples = [
            {
                "subject": "Team Meeting - Project Update",
                "body": """
                Hi team,
                
                Just a reminder about our project meeting tomorrow at 2 PM.
                We'll be discussing the Q4 roadmap and deliverables.
                
                Please come prepared with your status updates.
                
                Best regards,
                John
                Project Manager
                """,
                "sender": "john.doe@company.com",
                "is_phishing": 0
            },
            {
                "subject": "Monthly Newsletter - Company Updates",
                "body": """
                Dear Team,
                
                Here are our monthly updates:
                
                1. New client onboarding completed
                2. Q3 revenue exceeded targets by 15%
                3. New product launch scheduled for next month
                
                Thank you for your continued hard work!
                
                Management
                """,
                "sender": "newsletter@company.com",
                "is_phishing": 0
            },
            {
                "subject": "Your Order Confirmation #12345",
                "body": """
                Thank you for your order!
                
                Order Details:
                - Item: Professional License
                - Quantity: 1
                - Total: $299.99
                - Expected Delivery: 3-5 business days
                
                Track your order: https://company.com/track/12345
                
                Customer Service
                """,
                "sender": "orders@legitimate-store.com",
                "is_phishing": 0
            },
            {
                "subject": "Welcome to Our Platform!",
                "body": """
                Welcome to our platform!
                
                Your account has been successfully created.
                Here's how to get started:
                
                1. Complete your profile
                2. Explore our features
                3. Connect with team members
                
                Need help? Check our FAQ or contact support.
                
                The Team
                """,
                "sender": "welcome@platform.com",
                "is_phishing": 0
            },
            {
                "subject": "System Maintenance Notification",
                "body": """
                Scheduled Maintenance Notice:
                
                Our system will undergo maintenance on Saturday, 
                November 15th from 2 AM to 6 AM EST.
                
                Services will be temporarily unavailable during this time.
                We apologize for any inconvenience.
                
                IT Department
                """,
                "sender": "it@company.com",
                "is_phishing": 0
            }
        ]
        
        # Create more variations
        expanded_samples = []
        for sample in samples:
            for i in range(10):  # Create 10 variations each
                new_sample = sample.copy()
                # Add some variations
                new_sample["body"] = sample["body"] + f"\n\nSent from: Office-{i}"
                expanded_samples.append(new_sample)
        
        return expanded_samples
    
    def extract_features(self, emails: List[Dict]) -> np.ndarray:
        """Extract features from email list."""
        logger.info("Extracting features from emails...")
        
        features_list = []
        for i, email in enumerate(emails):
            if i % 100 == 0:
                logger.info(f"Processing email {i}/{len(emails)}")
            
            try:
                # Create email content
                email_content = f"""
                From: {email['sender']}
                Subject: {email['subject']}
                
                {email['body']}
                """
                
                # Extract features
                features = self.feature_extractor.extract_features(email_content)
                features_list.append(features)
                
            except Exception as e:
                logger.error(f"Error processing email {i}: {e}")
                # Add empty features as fallback
                features_list.append(self.feature_extractor.extract_features(""))
        
        return np.array(features_list)
    
    def prepare_training_data(self) -> Tuple[np.ndarray, np.ndarray]:
        """Prepare training data with features and labels."""
        logger.info("Preparing training data...")
        
        # Load datasets
        phishing_df, legitimate_df = self.load_datasets()
        
        # Combine datasets
        all_emails = []
        
        # Add phishing emails
        for _, row in phishing_df.iterrows():
            all_emails.append({
                'subject': row.get('subject', ''),
                'body': row.get('body', ''),
                'sender': row.get('sender', ''),
                'is_phishing': 1
            })
        
        # Add legitimate emails
        for _, row in legitimate_df.iterrows():
            all_emails.append({
                'subject': row.get('subject', ''),
                'body': row.get('body', ''),
                'sender': row.get('sender', ''),
                'is_phishing': 0
            })
        
        # Shuffle the data
        np.random.shuffle(all_emails)
        
        # Extract features
        X = self.extract_features(all_emails)
        
        # Extract labels
        y = np.array([email['is_phishing'] for email in all_emails])
        
        logger.info(f"Training data shape: {X.shape}")
        logger.info(f"Labels distribution: {np.bincount(y)}")
        
        return X, y
    
    def train_model(self, X: np.ndarray, y: np.ndarray) -> Dict:
        """Train the phishing detection model."""
        logger.info("Training model...")
        
        # Initialize detector
        detector = PhishingDetector()
        
        # Train the model
        metrics = detector.train(X, y)
        
        logger.info("Model training completed!")
        logger.info(f"Training metrics: {metrics}")
        
        return metrics
    
    def save_model(self, detector: PhishingDetector, metrics: Dict):
        """Save the trained model and metrics."""
        logger.info("Saving model...")
        
        # Save model
        model_path = self.model_dir / "phishing_detector.pkl"
        detector.save_model(str(model_path))
        
        # Save feature scaler
        scaler_path = self.model_dir / "feature_scaler.pkl"
        detector.save_scaler(str(scaler_path))
        
        # Save metrics
        metrics_path = self.model_dir / "training_metrics.json"
        import json
        with open(metrics_path, 'w') as f:
            json.dump(metrics, f, indent=2)
        
        logger.info(f"Model saved to {model_path}")
        logger.info(f"Scaler saved to {scaler_path}")
        logger.info(f"Metrics saved to {metrics_path}")
    
    def evaluate_model(self, detector: PhishingDetector, X_test: np.ndarray, y_test: np.ndarray) -> Dict:
        """Evaluate the trained model."""
        logger.info("Evaluating model...")
        
        # Make predictions
        y_pred = detector.predict(X_test)
        
        # Calculate metrics
        from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, classification_report, confusion_matrix
        
        metrics = {
            'accuracy': accuracy_score(y_test, y_pred),
            'precision': precision_score(y_test, y_pred),
            'recall': recall_score(y_test, y_pred),
            'f1_score': f1_score(y_test, y_pred),
            'classification_report': classification_report(y_test, y_pred),
            'confusion_matrix': confusion_matrix(y_test, y_pred).tolist()
        }
        
        logger.info("Model evaluation completed!")
        logger.info(f"Test accuracy: {metrics['accuracy']:.4f}")
        logger.info(f"Test precision: {metrics['precision']:.4f}")
        logger.info(f"Test recall: {metrics['recall']:.4f}")
        logger.info(f"Test F1-score: {metrics['f1_score']:.4f}")
        
        return metrics
    
    def run_training(self):
        """Run the complete training pipeline."""
        logger.info("Starting PhishCatcher model training...")
        
        try:
            # Prepare training data
            X, y = self.prepare_training_data()
            
            # Split data
            from sklearn.model_selection import train_test_split
            X_train, X_test, y_train, y_test = train_test_split(
                X, y, test_size=0.2, random_state=42, stratify=y
            )
            
            logger.info(f"Training set size: {len(X_train)}")
            logger.info(f"Test set size: {len(X_test)}")
            
            # Train model
            detector = PhishingDetector()
            training_metrics = detector.train(X_train, y_train)
            
            # Evaluate model
            test_metrics = self.evaluate_model(detector, X_test, y_test)
            
            # Save model
            self.save_model(detector, {
                'training_metrics': training_metrics,
                'test_metrics': test_metrics,
                'training_date': datetime.now().isoformat(),
                'training_samples': len(X_train),
                'test_samples': len(X_test),
                'feature_count': X.shape[1]
            })
            
            logger.info("🎉 Model training completed successfully!")
            logger.info(f"📊 Model saved to {self.model_dir}")
            
            return detector, test_metrics
            
        except Exception as e:
            logger.error(f"❌ Training failed: {e}")
            raise


def main():
    """Main function."""
    parser = argparse.ArgumentParser(description="Train PhishCatcher ML model")
    parser.add_argument("--data-dir", default="data", help="Data directory")
    parser.add_argument("--model-dir", default="models", help="Model directory")
    
    args = parser.parse_args()
    
    # Initialize trainer
    trainer = ModelTrainer(args.data_dir, args.model_dir)
    
    # Run training
    try:
        detector, metrics = trainer.run_training()
        
        print("\n" + "="*50)
        print("🎉 TRAINING COMPLETED SUCCESSFULLY!")
        print("="*50)
        print(f"📊 Test Accuracy: {metrics['accuracy']:.4f}")
        print(f"🎯 Test Precision: {metrics['precision']:.4f}")
        print(f"🔄 Test Recall: {metrics['recall']:.4f}")
        print(f"💯 Test F1-Score: {metrics['f1_score']:.4f}")
        print(f"💾 Model saved to: {trainer.model_dir}")
        print("="*50)
        
    except Exception as e:
        print(f"\n❌ Training failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
