"""
Risk Scorer Module

This module calculates overall risk scores and generates findings
based on ML predictions and rule-based analysis.
"""

from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from enum import Enum
import logging

from app.ml.phishing_detector import get_phishing_detector

logger = logging.getLogger(__name__)


class SeverityLevel(Enum):
    """Severity levels for findings."""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


@dataclass
class Finding:
    """Represents a security finding."""
    id: str
    type: str
    severity: SeverityLevel
    title: str
    description: str
    recommendation: str
    evidence: Dict[str, Any]
    confidence: float


class RiskScorer:
    """
    Calculate risk scores and generate findings from email analysis.
    
    This class combines ML predictions with rule-based analysis to:
    - Calculate overall risk score (0-100)
    - Generate detailed findings
    - Provide recommendations
    """
    
    def __init__(self):
        """Initialize risk scorer."""
        self.detector = get_phishing_detector()
    
    def analyze(self, parsed_email: Dict[str, Any]) -> Dict[str, Any]:
        """
        Perform complete risk analysis on parsed email.
        
        Args:
            parsed_email: Parsed email data from EmailParser
            
        Returns:
            Dictionary with risk score, findings, and analysis details
        """
        # Get ML prediction
        ml_prediction = self.detector.predict(parsed_email)
        
        # Generate findings
        findings = self._generate_findings(parsed_email, ml_prediction)
        
        # Calculate risk factors breakdown
        risk_factors = self._calculate_risk_factors(parsed_email, findings)
        
        # Calculate final risk score
        risk_score = self._calculate_final_risk_score(
            ml_prediction, risk_factors, len(findings)
        )
        
        # Determine threat category
        threat_category = self._determine_threat_category(risk_score, findings)
        
        return {
            'risk_score': risk_score,
            'threat_category': threat_category,
            'confidence': ml_prediction['confidence'],
            'findings': [self._finding_to_dict(f) for f in findings],
            'findings_count': len(findings),
            'critical_findings': sum(1 for f in findings if f.severity == SeverityLevel.CRITICAL),
            'high_findings': sum(1 for f in findings if f.severity == SeverityLevel.HIGH),
            'medium_findings': sum(1 for f in findings if f.severity == SeverityLevel.MEDIUM),
            'low_findings': sum(1 for f in findings if f.severity == SeverityLevel.LOW),
            'risk_factors': risk_factors,
            'ml_prediction': ml_prediction
        }
    
    def _generate_findings(self, parsed_email: Dict[str, Any], 
                          ml_prediction: Dict[str, Any]) -> List[Finding]:
        """Generate findings from email analysis."""
        findings = []
        finding_id = 0
        
        headers = parsed_email.get('headers', {})
        links = parsed_email.get('links', [])
        attachments = parsed_email.get('attachments', [])
        body = parsed_email.get('body', {})
        
        # Authentication findings
        auth_results = headers.get('authentication_results', {})
        
        if auth_results.get('spf') == 'fail':
            finding_id += 1
            findings.append(Finding(
                id=f"F{finding_id:03d}",
                type="authentication",
                severity=SeverityLevel.HIGH,
                title="SPF Authentication Failed",
                description="The email failed SPF (Sender Policy Framework) authentication. This indicates the sender may be spoofing their identity.",
                recommendation="Verify the sender's legitimacy before taking any action. Contact the sender through a known legitimate channel.",
                evidence={"spf_result": headers.get('received_spf', 'fail')},
                confidence=0.9
            ))
        
        if auth_results.get('dkim') == 'fail':
            finding_id += 1
            findings.append(Finding(
                id=f"F{finding_id:03d}",
                type="authentication",
                severity=SeverityLevel.MEDIUM,
                title="DKIM Signature Invalid",
                description="The email's DKIM signature could not be verified. The message may have been tampered with in transit.",
                recommendation="Treat this email with caution. Verify any requests through alternative channels.",
                evidence={"dkim_result": "fail"},
                confidence=0.8
            ))
        
        if auth_results.get('dmarc') == 'fail':
            finding_id += 1
            findings.append(Finding(
                id=f"F{finding_id:03d}",
                type="authentication",
                severity=SeverityLevel.HIGH,
                title="DMARC Policy Failed",
                description="The email failed DMARC validation, indicating potential domain spoofing.",
                recommendation="This email is likely fraudulent. Do not click any links or download attachments.",
                evidence={"dmarc_result": "fail"},
                confidence=0.85
            ))
        
        # Reply-to mismatch
        if headers.get('reply_to_mismatch', False):
            finding_id += 1
            findings.append(Finding(
                id=f"F{finding_id:03d}",
                type="sender",
                severity=SeverityLevel.HIGH,
                title="Reply-To Address Mismatch",
                description=f"The Reply-To address ({headers.get('reply_to')}) differs from the sender address ({headers.get('from_address')}).",
                recommendation="This is a common phishing technique. Any replies will go to a different address than the apparent sender.",
                evidence={
                    "from": headers.get('from'),
                    "reply_to": headers.get('reply_to')
                },
                confidence=0.9
            ))
        
        # Suspicious links
        suspicious_links = [l for l in links if self._is_suspicious_link(l)]
        if suspicious_links:
            finding_id += 1
            severity = SeverityLevel.CRITICAL if len(suspicious_links) > 2 else SeverityLevel.HIGH
            findings.append(Finding(
                id=f"F{finding_id:03d}",
                type="links",
                severity=severity,
                title=f"{len(suspicious_links)} Suspicious Link(s) Detected",
                description=f"Found {len(suspicious_links)} links with suspicious characteristics such as IP addresses, URL shorteners, or suspicious domains.",
                recommendation="Do not click these links. If you need to access the service, type the URL directly in your browser.",
                evidence={"suspicious_urls": [l['url'] for l in suspicious_links[:5]]},
                confidence=0.85
            ))
        
        # URL shorteners
        shortened_links = [l for l in links if l.get('is_shortened', False)]
        if shortened_links:
            finding_id += 1
            findings.append(Finding(
                id=f"F{finding_id:03d}",
                type="links",
                severity=SeverityLevel.MEDIUM,
                title="URL Shorteners Detected",
                description=f"Found {len(shortened_links)} shortened URL(s) that hide the true destination.",
                recommendation="Be cautious with shortened URLs. Use a URL expander service to check the destination before clicking.",
                evidence={"shortened_urls": [l['url'] for l in shortened_links]},
                confidence=0.7
            ))
        
        # Executable attachments
        exe_attachments = [a for a in attachments if a.get('is_executable', False)]
        if exe_attachments:
            finding_id += 1
            findings.append(Finding(
                id=f"F{finding_id:03d}",
                type="attachments",
                severity=SeverityLevel.CRITICAL,
                title="Executable File Attachment",
                description=f"Found {len(exe_attachments)} executable file(s) which could contain malware.",
                recommendation="Never run executable files from email attachments. Delete this email immediately.",
                evidence={"files": [a['filename'] for a in exe_attachments]},
                confidence=0.95
            ))
        
        # Script attachments
        script_attachments = [a for a in attachments if a.get('is_script', False)]
        if script_attachments:
            finding_id += 1
            findings.append(Finding(
                id=f"F{finding_id:03d}",
                type="attachments",
                severity=SeverityLevel.HIGH,
                title="Script File Attachment",
                description=f"Found {len(script_attachments)} script file(s) which could contain malicious code.",
                recommendation="Do not open script files from emails. They can execute harmful commands on your system.",
                evidence={"files": [a['filename'] for a in script_attachments]},
                confidence=0.85
            ))
        
        # Content analysis
        content = f"{body.get('text', '')} {body.get('html', '')}".lower()
        
        # Urgency keywords
        urgency_keywords = ['urgent', 'immediate', 'action required', 'verify now', 'account suspended']
        found_urgency = [kw for kw in urgency_keywords if kw in content]
        if found_urgency:
            finding_id += 1
            findings.append(Finding(
                id=f"F{finding_id:03d}",
                type="content",
                severity=SeverityLevel.MEDIUM,
                title="Urgency Language Detected",
                description=f"The email uses urgency language ('{', '.join(found_urgency[:3])}') to pressure you into acting quickly.",
                recommendation="Phishing emails often create false urgency. Take time to verify the request independently.",
                evidence={"keywords_found": found_urgency},
                confidence=0.6
            ))
        
        # Password requests
        if 'password' in content and ('verify' in content or 'confirm' in content or 'enter' in content):
            finding_id += 1
            findings.append(Finding(
                id=f"F{finding_id:03d}",
                type="content",
                severity=SeverityLevel.HIGH,
                title="Password Request Detected",
                description="The email requests password verification or entry, which is a common phishing tactic.",
                recommendation="Legitimate services never ask for passwords via email. Never enter your password in response to an email.",
                evidence={},
                confidence=0.9
            ))
        
        # ML-based finding
        if ml_prediction['phishing_probability'] > 0.7:
            finding_id += 1
            severity = SeverityLevel.CRITICAL if ml_prediction['phishing_probability'] > 0.9 else SeverityLevel.HIGH
            findings.append(Finding(
                id=f"F{finding_id:03d}",
                type="ml_detection",
                severity=severity,
                title="Machine Learning Phishing Detection",
                description=f"Our machine learning model has identified this email as likely phishing with {ml_prediction['phishing_probability']*100:.1f}% confidence.",
                recommendation="Treat this email as potentially fraudulent. Do not interact with any links or attachments.",
                evidence={
                    "phishing_probability": ml_prediction['phishing_probability'],
                    "model_version": ml_prediction['model_version']
                },
                confidence=ml_prediction['confidence']
            ))
        
        return findings
    
    def _is_suspicious_link(self, link: Dict[str, Any]) -> bool:
        """Check if a link is suspicious."""
        return (
            link.get('is_ip_address', False) or
            link.get('has_suspicious_tld', False) or
            link.get('has_at_symbol', False) or
            link.get('has_hex_chars', False)
        )
    
    def _calculate_risk_factors(self, parsed_email: Dict[str, Any], 
                                findings: List[Finding]) -> Dict[str, int]:
        """Calculate risk factor scores (0-100)."""
        headers = parsed_email.get('headers', {})
        links = parsed_email.get('links', [])
        attachments = parsed_email.get('attachments', [])
        
        # Sender reputation risk
        sender_risk = 0
        auth_results = headers.get('authentication_results', {})
        if auth_results.get('spf') == 'fail':
            sender_risk += 30
        if auth_results.get('dkim') == 'fail':
            sender_risk += 20
        if auth_results.get('dmarc') == 'fail':
            sender_risk += 30
        if headers.get('reply_to_mismatch', False):
            sender_risk += 20
        sender_risk = min(sender_risk, 100)
        
        # Content risk
        content_risk = 0
        content_findings = [f for f in findings if f.type == 'content']
        content_risk += len(content_findings) * 15
        content_risk = min(content_risk, 100)
        
        # Link risk
        link_risk = 0
        if links:
            suspicious_ratio = sum(1 for l in links if self._is_suspicious_link(l)) / len(links)
            link_risk = int(suspicious_ratio * 100)
        link_findings = [f for f in findings if f.type == 'links']
        link_risk += len(link_findings) * 10
        link_risk = min(link_risk, 100)
        
        # Attachment risk
        attachment_risk = 0
        exe_count = sum(1 for a in attachments if a.get('is_executable', False))
        script_count = sum(1 for a in attachments if a.get('is_script', False))
        attachment_risk += exe_count * 50 + script_count * 30
        attachment_risk = min(attachment_risk, 100)
        
        # Authentication risk
        auth_risk = 0
        auth_findings = [f for f in findings if f.type == 'authentication']
        auth_risk += len(auth_findings) * 25
        auth_risk = min(auth_risk, 100)
        
        return {
            'sender_reputation': sender_risk,
            'content_risk': content_risk,
            'link_risk': link_risk,
            'attachment_risk': attachment_risk,
            'authentication_risk': auth_risk
        }
    
    def _calculate_final_risk_score(self, ml_prediction: Dict[str, Any],
                                    risk_factors: Dict[str, int],
                                    findings_count: int) -> int:
        """Calculate final risk score (0-100)."""
        # Start with ML prediction
        ml_score = ml_prediction['phishing_probability'] * 100
        
        # Calculate average of risk factors
        factor_score = sum(risk_factors.values()) / len(risk_factors)
        
        # Adjust based on number of findings
        findings_adjustment = min(findings_count * 5, 20)
        
        # Weighted combination
        final_score = (ml_score * 0.5) + (factor_score * 0.3) + findings_adjustment
        
        return min(int(final_score), 100)
    
    def _determine_threat_category(self, risk_score: int, 
                                   findings: List[Finding]) -> str:
        """Determine threat category based on risk score and findings."""
        if risk_score >= 80:
            return 'phishing'
        elif risk_score >= 60:
            return 'suspicious'
        elif risk_score >= 40:
            return 'caution'
        else:
            # Check for specific malware indicators
            exe_findings = [f for f in findings if f.type == 'attachments' and 'executable' in f.title.lower()]
            if exe_findings:
                return 'malware'
            return 'safe'
    
    def _finding_to_dict(self, finding: Finding) -> Dict[str, Any]:
        """Convert Finding to dictionary."""
        return {
            'id': finding.id,
            'type': finding.type,
            'severity': finding.severity.value,
            'title': finding.title,
            'description': finding.description,
            'recommendation': finding.recommendation,
            'evidence': finding.evidence,
            'confidence': finding.confidence
        }


# Singleton instance
_scorer_instance: Optional[RiskScorer] = None


def get_risk_scorer() -> RiskScorer:
    """Get singleton instance of risk scorer."""
    global _scorer_instance
    if _scorer_instance is None:
        _scorer_instance = RiskScorer()
    return _scorer_instance
