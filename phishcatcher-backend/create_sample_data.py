#!/usr/bin/env python3
"""
Create sample datasets for PhishCatcher model training.
This script creates sample CSV files for testing the training pipeline.
"""

import pandas as pd
import os
from pathlib import Path

def create_sample_datasets():
    """Create sample phishing and legitimate email datasets."""
    
    # Create data directory
    data_dir = Path("data")
    data_dir.mkdir(exist_ok=True)
    
    # Sample phishing emails
    phishing_data = [
        {
            "subject": "URGENT: Your Account Will Be Suspended",
            "body": "Dear valued customer, Your account will be suspended within 24 hours due to suspicious activity. Please click here immediately to verify your account: http://bit.ly/verify-now-urgent. Failure to verify will result in permanent account closure.",
            "sender": "security@paypal-update.com",
            "is_phishing": 1
        },
        {
            "subject": "You've Won $1,000,000!!!",
            "body": "CONGRATULATIONS! You are our lucky winner! You have won $1,000,000 in our international lottery. To claim your prize, please send your bank details to winner@lottery-scams.com. Act now! This offer expires in 24 hours!",
            "sender": "winner@international-lottery.com",
            "is_phishing": 1
        },
        {
            "subject": "Invoice Overdue - Immediate Payment Required",
            "body": "Your invoice is overdue. Please pay immediately to avoid late fees. Click here to pay: http://fake-invoice.com/pay-now. Amount due: $999.99. Failure to pay will result in legal action.",
            "sender": "billing@fake-company.com",
            "is_phishing": 1
        },
        {
            "subject": "Microsoft Security Alert - Password Reset Required",
            "body": "We detected unusual activity on your Microsoft account. Please reset your password immediately: http://microsoft-security-reset.com/reset. If you don't reset your password, your account will be blocked.",
            "sender": "security@microsoft-alert.com",
            "is_phishing": 1
        },
        {
            "subject": "COVID-19 Relief Fund - Claim Your Money",
            "body": "You are eligible for COVID-19 relief funds. Click here to claim your $5,000 payment: http://covid-relief-scam.com/claim. Limited time offer! Act now!",
            "sender": "relief@covid-gov.org",
            "is_phishing": 1
        }
    ]
    
    # Sample legitimate emails
    legitimate_data = [
        {
            "subject": "Team Meeting - Project Update",
            "body": "Hi team, Just a reminder about our project meeting tomorrow at 2 PM. We'll be discussing the Q4 roadmap and deliverables. Please come prepared with your status updates. Best regards, John",
            "sender": "john.doe@company.com",
            "is_phishing": 0
        },
        {
            "subject": "Monthly Newsletter - Company Updates",
            "body": "Dear Team, Here are our monthly updates: 1. New client onboarding completed 2. Q3 revenue exceeded targets by 15% 3. New product launch scheduled for next month. Thank you for your continued hard work!",
            "sender": "newsletter@company.com",
            "is_phishing": 0
        },
        {
            "subject": "Your Order Confirmation #12345",
            "body": "Thank you for your order! Order Details: - Item: Professional License - Quantity: 1 - Total: $299.99 - Expected Delivery: 3-5 business days. Track your order: https://company.com/track/12345",
            "sender": "orders@legitimate-store.com",
            "is_phishing": 0
        },
        {
            "subject": "Welcome to Our Platform!",
            "body": "Welcome to our platform! Your account has been successfully created. Here's how to get started: 1. Complete your profile 2. Explore our features 3. Connect with team members. Need help? Check our FAQ or contact support.",
            "sender": "welcome@platform.com",
            "is_phishing": 0
        },
        {
            "subject": "System Maintenance Notification",
            "body": "Scheduled Maintenance Notice: Our system will undergo maintenance on Saturday, November 15th from 2 AM to 6 AM EST. Services will be temporarily unavailable during this time. We apologize for any inconvenience.",
            "sender": "it@company.com",
            "is_phishing": 0
        }
    ]
    
    # Create DataFrames
    phishing_df = pd.DataFrame(phishing_data)
    legitimate_df = pd.DataFrame(legitimate_data)
    
    # Save to CSV files
    phishing_df.to_csv(data_dir / "phishing_emails.csv", index=False)
    legitimate_df.to_csv(data_dir / "enron_emails.csv", index=False)
    
    print(f"✅ Created sample datasets in {data_dir}")
    print(f"   - Phishing emails: {len(phishing_df)} samples")
    print(f"   - Legitimate emails: {len(legitimate_df)} samples")

if __name__ == "__main__":
    create_sample_datasets()
