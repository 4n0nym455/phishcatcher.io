"""
Threat Intelligence Service

This module provides threat intelligence API integration with:
- AbuseIPDB (IP/Domain reputation)
- WhoisJSON (Domain age)
- PhishTank (URL phishing check)
- VirusTotal (URL/File hash analysis)
- URLScan (Backup URL analysis)

Includes Redis caching to reduce API calls.
"""

import re
import json
import hashlib
import logging
import asyncio
from typing import Optional, List, Dict, Any, Tuple
from datetime import datetime
from urllib.parse import urlparse
import httpx

from app.config import get_settings

logger = logging.getLogger(__name__)


class ThreatIntelService:
    """Service for threat intelligence API calls with caching."""
    
    # Risk thresholds
    HIGH_RISK_AGE_DAYS = 30
    MEDIUM_RISK_AGE_DAYS = 90
    HIGH_CONFIDENCE_SCORE = 70
    
    def __init__(self):
        self.settings = get_settings()
        self._redis_client = None
        self._cache_ttl = self.settings.TI_CACHE_TTL_HOURS * 3600
    
    async def get_redis_client(self):
        """Get Redis client (lazy initialization)."""
        if self._redis_client is None:
            try:
                import redis.asyncio as redis
                self._redis_client = redis.from_url(
                    self.settings.REDIS_URL,
                    encoding="utf-8",
                    decode_responses=True
                )
            except Exception as e:
                logger.warning(f"Redis not available, caching disabled: {e}")
        return self._redis_client
    
    async def _get_from_cache(self, key: str) -> Optional[Dict]:
        """Get value from Redis cache."""
        try:
            redis_client = await self.get_redis_client()
            if redis_client:
                cached = await redis_client.get(key)
                if cached:
                    logger.debug(f"Cache hit: {key}")
                    return json.loads(cached)
        except Exception as e:
            logger.warning(f"Cache read error: {e}")
        return None
    
    async def _set_in_cache(self, key: str, value: Dict, ttl: Optional[int] = None):
        """Set value in Redis cache."""
        try:
            redis_client = await self.get_redis_client()
            if redis_client:
                ttl = ttl or self._cache_ttl
                await redis_client.setex(key, ttl, json.dumps(value))
        except Exception as e:
            logger.warning(f"Cache write error: {e}")
    
    @staticmethod
    def _extract_domain_from_email(email: str) -> Optional[str]:
        """Extract domain from email address."""
        if '@' in email:
            return email.split('@')[1].lower()
        return None
    
    @staticmethod
    def _extract_domain_from_url(url: str) -> Optional[str]:
        """Extract domain from URL."""
        try:
            parsed = urlparse(url)
            return parsed.netloc.lower() if parsed.netloc else None
        except Exception:
            return None
    
    @staticmethod
    def _hash_url(url: str) -> str:
        """Create hash for URL cache key."""
        return hashlib.sha256(url.encode()).hexdigest()[:16]
    
    @staticmethod
    def _get_risk_level_from_score(score: float) -> str:
        """Convert 0-100 score to risk level."""
        if score >= 80:
            return "critical"
        elif score >= 60:
            return "high"
        elif score >= 40:
            return "medium"
        elif score >= 20:
            return "low"
        return "none"
    
    async def check_ip_reputation(self, ip_address: str) -> Dict[str, Any]:
        """
        Check IP reputation using AbuseIPDB.
        
        Weight: 20% of TI score
        """
        cache_key = f"ti:ip:{ip_address}"
        cached = await self._get_from_cache(cache_key)
        if cached:
            cached['cached'] = True
            return cached
        
        if not self.settings.ABUSEIPDB_API_KEY:
            return {
                'api_name': 'abuseipdb',
                'success': False,
                'score': 0.0,
                'risk_level': 'none',
                'error': 'API key not configured',
                'cached': False
            }
        
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(
                    'https://api.abuseipdb.com/api/v2/check',
                    headers={
                        'Accept': 'application/json',
                        'Key': self.settings.ABUSEIPDB_API_KEY
                    },
                    params={
                        'ipAddress': ip_address,
                        'maxAgeInDays': 90,
                        'verbose': ''
                    }
                )
                
                if response.status_code == 200:
                    data = response.json().get('data', {})
                    confidence = data.get('abuseConfidenceScore', 0)
                    
                    result = {
                        'api_name': 'abuseipdb',
                        'success': True,
                        'score': confidence / 100.0,
                        'risk_level': self._get_risk_level_from_score(confidence),
                        'data': {
                            'ip_address': ip_address,
                            'abuse_confidence_score': confidence,
                            'num_reports': data.get('totalReports', 0),
                            'num_distinct_users': data.get('numDistinctUsers', 0),
                            'country_code': data.get('countryCode'),
                            'isp': data.get('isp'),
                            'domain': data.get('domain'),
                            'is_whitelisted': data.get('isWhitelisted', False),
                            'categories': data.get('categoryDescriptions', [])
                        },
                        'cached': False
                    }
                    
                    await self._set_in_cache(cache_key, result)
                    return result
                else:
                    return {
                        'api_name': 'abuseipdb',
                        'success': False,
                        'score': 0.0,
                        'risk_level': 'none',
                        'error': f'API error: {response.status_code}',
                        'cached': False
                    }
        except Exception as e:
            logger.error(f"AbuseIPDB error: {e}")
            return {
                'api_name': 'abuseipdb',
                'success': False,
                'score': 0.0,
                'risk_level': 'none',
                'error': str(e),
                'cached': False
            }
    
    async def check_domain_age(self, domain: str) -> Dict[str, Any]:
        """
        Check domain age using WhoisJSON.
        
        Weight: 10% of TI score
        """
        cache_key = f"ti:domain_age:{domain}"
        cached = await self._get_from_cache(cache_key)
        if cached:
            cached['cached'] = True
            return cached
        
        if not self.settings.WHOISJSON_API_KEY:
            return {
                'api_name': 'whoisjson',
                'success': False,
                'score': 0.0,
                'risk_level': 'none',
                'error': 'API key not configured',
                'cached': False
            }
        
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                response = await client.get(
                    'https://www.whoisjsonapi.com/v1/whois',
                    params={
                        'domain': domain,
                        'apikey': self.settings.WHOISJSON_API_KEY
                    }
                )
                
                if response.status_code == 200:
                    data = response.json()
                    age_days = data.get('age_in_days')
                    
                    # Calculate risk score based on age
                    if age_days is None:
                        score = 0.5
                        risk = 'medium'
                    elif age_days < self.HIGH_RISK_AGE_DAYS:
                        score = 1.0
                        risk = 'critical'
                    elif age_days < self.MEDIUM_RISK_AGE_DAYS:
                        score = 0.7
                        risk = 'high'
                    elif age_days < 365:
                        score = 0.4
                        risk = 'medium'
                    else:
                        score = 0.0
                        risk = 'none'
                    
                    result = {
                        'api_name': 'whoisjson',
                        'success': True,
                        'score': score,
                        'risk_level': risk,
                        'data': {
                            'domain': domain,
                            'created_date': data.get('created_date_normalized'),
                            'age_in_days': age_days,
                            'age_in_years': data.get('age_in_years'),
                            'registrar': data.get('registrar'),
                            'name_servers': data.get('nameServers', [])
                        },
                        'cached': False
                    }
                    
                    await self._set_in_cache(cache_key, result, 86400 * 7)
                    return result
                else:
                    return {
                        'api_name': 'whoisjson',
                        'success': False,
                        'score': 0.0,
                        'risk_level': 'none',
                        'error': f'API error: {response.status_code}',
                        'cached': False
                    }
        except Exception as e:
            logger.error(f"WhoisJSON error: {e}")
            return {
                'api_name': 'whoisjson',
                'success': False,
                'score': 0.0,
                'risk_level': 'none',
                'error': str(e),
                'cached': False
            }
    
    async def check_domain_reputation(self, domain: str) -> Dict[str, Any]:
        """
        Check domain reputation using AbuseIPDB.
        
        Weight: 10% of TI score
        """
        cache_key = f"ti:domain_rep:{domain}"
        cached = await self._get_from_cache(cache_key)
        if cached:
            cached['cached'] = True
            return cached
        
        if not self.settings.ABUSEIPDB_API_KEY:
            return {
                'api_name': 'abuseipdb_domain',
                'success': False,
                'score': 0.0,
                'risk_level': 'none',
                'error': 'API key not configured',
                'cached': False
            }
        
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(
                    'https://api.abuseipdb.com/api/v2/check-domain',
                    headers={
                        'Accept': 'application/json',
                        'Key': self.settings.ABUSEIPDB_API_KEY
                    },
                    params={'domain': domain}
                )
                
                if response.status_code == 200:
                    data = response.json().get('data', {})
                    score = data.get('abuseConfidenceScore', 0) / 100.0
                    
                    result = {
                        'api_name': 'abuseipdb_domain',
                        'success': True,
                        'score': score,
                        'risk_level': self._get_risk_level_from_score(score * 100),
                        'data': {
                            'domain': domain,
                            'abuse_confidence_score': data.get('abuseConfidenceScore', 0),
                            'num_reported_ips': data.get('numReportedIp', 0),
                            'num_distinct_ips': data.get('numDistinctIp', 0)
                        },
                        'cached': False
                    }
                    
                    await self._set_in_cache(cache_key, result)
                    return result
                else:
                    return {
                        'api_name': 'abuseipdb_domain',
                        'success': False,
                        'score': 0.0,
                        'risk_level': 'none',
                        'error': f'API error: {response.status_code}',
                        'cached': False
                    }
        except Exception as e:
            logger.error(f"AbuseIPDB domain check error: {e}")
            return {
                'api_name': 'abuseipdb_domain',
                'success': False,
                'score': 0.0,
                'risk_level': 'none',
                'error': str(e),
                'cached': False
            }
    
    async def check_url_phishtank(self, url: str) -> Dict[str, Any]:
        """
        Check URL using PhishTank.
        
        Weight: 15% of TI score
        """
        cache_key = f"ti:phishtank:{self._hash_url(url)}"
        cached = await self._get_from_cache(cache_key)
        if cached:
            cached['cached'] = True
            return cached
        
        if not self.settings.PHISHTANK_API_KEY:
            return {
                'api_name': 'phishtank',
                'success': False,
                'score': 0.0,
                'risk_level': 'none',
                'error': 'API key not configured',
                'cached': False
            }
        
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(
                    'https://checkurl.phishtank.com/checkurl/',
                    data={'url': url},
                    headers={
                        'App-Key': self.settings.PHISHTANK_API_KEY,
                        'Content-Type': 'application/x-www-form-urlencoded'
                    }
                )
                
                if response.status_code == 200:
                    data = response.json().get('results', {})
                    in_db = data.get('in_database', False)
                    verified = data.get('verified', False)
                    
                    if in_db and verified:
                        score = 1.0
                        risk = 'critical'
                    elif in_db:
                        score = 0.6
                        risk = 'high'
                    else:
                        score = 0.0
                        risk = 'none'
                    
                    result = {
                        'api_name': 'phishtank',
                        'success': True,
                        'score': score,
                        'risk_level': risk,
                        'data': {
                            'url': url,
                            'in_database': in_db,
                            'verified': verified,
                            'phish_detail_url': data.get('phish_detail_url')
                        },
                        'cached': False
                    }
                    
                    await self._set_in_cache(cache_key, result, 43200)
                    return result
                else:
                    return {
                        'api_name': 'phishtank',
                        'success': False,
                        'score': 0.0,
                        'risk_level': 'none',
                        'error': f'API error: {response.status_code}',
                        'cached': False
                    }
        except Exception as e:
            logger.error(f"PhishTank error: {e}")
            return {
                'api_name': 'phishtank',
                'success': False,
                'score': 0.0,
                'risk_level': 'none',
                'error': str(e),
                'cached': False
            }
    
    async def check_url_virustotal(self, url: str) -> Dict[str, Any]:
        """
        Check URL using VirusTotal.
        
        Weight: 15% of TI score
        """
        import urllib.parse
        cache_key = f"ti:vt_url:{self._hash_url(url)}"
        cached = await self._get_from_cache(cache_key)
        if cached:
            cached['cached'] = True
            return cached
        
        if not self.settings.VIRUSTOTAL_API_KEY:
            return {
                'api_name': 'virustotal_url',
                'success': False,
                'score': 0.0,
                'risk_level': 'none',
                'error': 'API key not configured',
                'cached': False
            }
        
        try:
            encoded_url = urllib.parse.quote(url, safe='')
            async with httpx.AsyncClient(timeout=15.0) as client:
                response = await client.get(
                    f'https://www.virustotal.com/api/v3/urls/{encoded_url}',
                    headers={'x-apikey': self.settings.VIRUSTOTAL_API_KEY}
                )
                
                if response.status_code == 200:
                    data = response.json().get('data', {}).get('attributes', {})
                    stats = data.get('last_analysis_stats', {})
                    
                    malicious = stats.get('malicious', 0)
                    suspicious = stats.get('suspicious', 0)
                    total = sum(stats.values())
                    
                    if total > 0:
                        score = (malicious + suspicious) / total
                    else:
                        score = 0.0
                    
                    result = {
                        'api_name': 'virustotal_url',
                        'success': True,
                        'score': score,
                        'risk_level': self._get_risk_level_from_score(score * 100),
                        'data': {
                            'url': url,
                            'last_analysis_stats': stats,
                            'threat_names': data.get('threat_labels', []),
                            'permalink': f"https://www.virustotal.com/gui/url/{encoded_url}"
                        },
                        'cached': False
                    }
                    
                    await self._set_in_cache(cache_key, result, 43200)
                    return result
                elif response.status_code == 404:
                    result = {
                        'api_name': 'virustotal_url',
                        'success': True,
                        'score': 0.0,
                        'risk_level': 'none',
                        'data': {'url': url, 'not_found': True},
                        'cached': False
                    }
                    await self._set_in_cache(cache_key, result, 3600)
                    return result
                else:
                    return {
                        'api_name': 'virustotal_url',
                        'success': False,
                        'score': 0.0,
                        'risk_level': 'none',
                        'error': f'API error: {response.status_code}',
                        'cached': False
                    }
        except Exception as e:
            logger.error(f"VirusTotal URL error: {e}")
            return {
                'api_name': 'virustotal_url',
                'success': False,
                'score': 0.0,
                'risk_level': 'none',
                'error': str(e),
                'cached': False
            }
    
    async def check_hash_virustotal(self, file_hash: str) -> Dict[str, Any]:
        """
        Check file hash using VirusTotal.
        
        Weight: 10% of TI score
        """
        cache_key = f"ti:vt_hash:{file_hash}"
        cached = await self._get_from_cache(cache_key)
        if cached:
            cached['cached'] = True
            return cached
        
        if not self.settings.VIRUSTOTAL_API_KEY:
            return {
                'api_name': 'virustotal_hash',
                'success': False,
                'score': 0.0,
                'risk_level': 'none',
                'error': 'API key not configured',
                'cached': False
            }
        
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                response = await client.get(
                    f'https://www.virustotal.com/api/v3/files/{file_hash}',
                    headers={'x-apikey': self.settings.VIRUSTOTAL_API_KEY}
                )
                
                if response.status_code == 200:
                    data = response.json().get('data', {}).get('attributes', {})
                    stats = data.get('last_analysis_stats', {})
                    
                    malicious = stats.get('malicious', 0)
                    suspicious = stats.get('suspicious', 0)
                    total = sum(stats.values())
                    
                    if total > 0:
                        score = (malicious + suspicious) / total
                    else:
                        score = 0.0
                    
                    result = {
                        'api_name': 'virustotal_hash',
                        'success': True,
                        'score': score,
                        'risk_level': self._get_risk_level_from_score(score * 100),
                        'data': {
                            'hash': file_hash,
                            'meaningful_name': data.get('meaningful_name'),
                            'file_type': data.get('file_type'),
                            'file_size': data.get('size'),
                            'last_analysis_stats': stats,
                            'names': data.get('names', [])[:5]
                        },
                        'cached': False
                    }
                    
                    await self._set_in_cache(cache_key, result, 172800)
                    return result
                else:
                    return {
                        'api_name': 'virustotal_hash',
                        'success': False,
                        'score': 0.0,
                        'risk_level': 'none',
                        'error': f'API error: {response.status_code}',
                        'cached': False
                    }
        except Exception as e:
            logger.error(f"VirusTotal hash error: {e}")
            return {
                'api_name': 'virustotal_hash',
                'success': False,
                'score': 0.0,
                'risk_level': 'none',
                'error': str(e),
                'cached': False
            }
    
    async def check_url_urlscan(self, url: str) -> Dict[str, Any]:
        """
        Check URL using URLScan as backup.
        
        Weight: 10% of TI score (backup)
        """
        if not self.settings.ENABLE_URLSCAN_BACKUP:
            return {
                'api_name': 'urlscan',
                'success': True,
                'score': 0.0,
                'risk_level': 'none',
                'data': {'skipped': True},
                'cached': False
            }
        
        cache_key = f"ti:urlscan:{self._hash_url(url)}"
        cached = await self._get_from_cache(cache_key)
        if cached:
            cached['cached'] = True
            return cached
        
        if not self.settings.URLSCAN_API_KEY:
            return {
                'api_name': 'urlscan',
                'success': False,
                'score': 0.0,
                'risk_level': 'none',
                'error': 'API key not configured',
                'cached': False
            }
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    'https://urlscan.io/api/v1/scan/',
                    data=json.dumps({'url': url, 'visibility': 'public'}),
                    headers={
                        'Content-Type': 'application/json',
                        'API-Key': self.settings.URLSCAN_API_KEY
                    }
                )
                
                if response.status_code == 200:
                    data = response.json()
                    result_uuid = data.get('uuid')
                    
                    await asyncio.sleep(2)
                    
                    result_response = await client.get(
                        f'https://urlscan.io/api/v1/result/{result_uuid}/',
                        headers={'API-Key': self.settings.URLSCAN_API_KEY}
                    )
                    
                    if result_response.status_code == 200:
                        result_data = result_response.json()
                        verdicts = result_data.get('verdicts', {})
                        overall = verdicts.get('overall', {})
                        
                        score = overall.get('score', 0) / 100.0
                        
                        result = {
                            'api_name': 'urlscan',
                            'success': True,
                            'score': score,
                            'risk_level': self._get_risk_level_from_score(score * 100),
                            'data': {
                                'url': url,
                                'score': overall.get('score', 0),
                                'categories': overall.get('categories', []),
                                'permalink': f"https://urlscan.io/result/{result_uuid}/"
                            },
                            'cached': False
                        }
                        
                        await self._set_in_cache(cache_key, result, 43200)
                        return result
                
                return {
                    'api_name': 'urlscan',
                    'success': False,
                    'score': 0.0,
                    'risk_level': 'none',
                    'error': f'API error: {response.status_code}',
                    'cached': False
                }
        except Exception as e:
            logger.error(f"URLScan error: {e}")
            return {
                'api_name': 'urlscan',
                'success': False,
                'score': 0.0,
                'risk_level': 'none',
                'error': str(e),
                'cached': False
            }
    
    async def analyze_email_threats(
        self,
        sender_email: str,
        urls: List[str],
        attachment_hashes: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Perform comprehensive threat analysis on an email.
        
        Combines all TI API checks and calculates weighted score.
        
        Weights:
        - IP reputation (AbuseIPDB): 20%
        - Domain age (WhoisJSON): 10%
        - Domain reputation (AbuseIPDB): 10%
        - URL PhishTank: 15%
        - URL VirusTotal: 15%
        - File hash VirusTotal: 10%
        - URLScan (backup): 10%
        """
        if attachment_hashes is None:
            attachment_hashes = []
        
        weights = {
            'abuseipdb': 0.20,
            'whoisjson': 0.10,
            'abuseipdb_domain': 0.10,
            'phishtank': 0.15,
            'virustotal_url': 0.15,
            'virustotal_hash': 0.10,
            'urlscan': 0.10
        }
        
        results = []
        warnings = []
        indicators = []
        
        sender_domain = self._extract_domain_from_email(sender_email)
        
        tasks = []
        
        if sender_domain:
            ip_task = self._resolve_and_check_ip(sender_domain)
            tasks.append(('ip_reputation', ip_task))
            
            domain_age_task = self.check_domain_age(sender_domain)
            tasks.append(('domain_age', domain_age_task))
            
            domain_rep_task = self.check_domain_reputation(sender_domain)
            tasks.append(('domain_reputation', domain_rep_task))
        
        for url in urls[:5]:
            tasks.append(('phishtank', self.check_url_phishtank(url)))
            tasks.append(('virustotal_url', self.check_url_virustotal(url)))
        
        for hash_val in attachment_hashes[:3]:
            tasks.append(('virustotal_hash', self.check_hash_virustotal(hash_val)))
        
        task_results = {}
        for key, task in tasks:
            try:
                result = await task
                task_results[key] = result
            except Exception as e:
                logger.error(f"Task {key} failed: {e}")
                task_results[key] = {'success': False, 'error': str(e)}
        
        weighted_score = 0.0
        total_weight = 0.0
        
        for api_name, weight in weights.items():
            result = task_results.get(api_name, {})
            
            if result.get('success'):
                score = result.get('score', 0.0)
                weighted_score += score * weight
                total_weight += weight
                
                if score > 0.5:
                    indicators.append(f"{api_name}: high risk detected")
            else:
                warnings.append(f"{api_name}: {result.get('error', 'failed')}")
        
        if total_weight > 0:
            final_score = weighted_score / total_weight
        else:
            final_score = 0.0
        
        if final_score >= 0.8:
            category = 'phishing'
        elif final_score >= 0.6:
            category = 'likely_phishing'
        elif final_score >= 0.4:
            category = 'suspicious'
        elif final_score >= 0.2:
            category = 'low_risk'
        else:
            category = 'safe'
        
        confidence = min(total_weight / 0.6, 1.0) if total_weight > 0 else 0.0
        
        return {
            'overall_risk_score': final_score,
            'risk_category': category,
            'confidence': confidence,
            'api_results': task_results,
            'indicators': indicators,
            'warnings': warnings,
            'analysis_timestamp': datetime.utcnow().isoformat()
        }
    
    async def _resolve_and_check_ip(self, domain: str) -> Dict[str, Any]:
        """Resolve domain to IP and check reputation."""
        import socket
        try:
            ip_address = socket.gethostbyname(domain)
            return await self.check_ip_reputation(ip_address)
        except socket.gaierror:
            return {
                'api_name': 'abuseipdb',
                'success': False,
                'score': 0.0,
                'risk_level': 'none',
                'error': f'Could not resolve domain: {domain}'
            }


_threat_intel_instance: Optional[ThreatIntelService] = None


def get_threat_intel_service() -> ThreatIntelService:
    """Get singleton instance of threat intel service."""
    global _threat_intel_instance
    if _threat_intel_instance is None:
        _threat_intel_instance = ThreatIntelService()
    return _threat_intel_instance