"""
Threat Intelligence Service

This module provides threat intelligence API integration with:
- AbuseIPDB (IP/Domain reputation)
- RDAP (Domain age - free)
- PhishTank/URLScan (URL phishing check)
- VirusTotal (URL/File hash analysis)

Includes Redis caching to reduce API calls.
"""

import re
import json
import hashlib
import logging
import asyncio
from typing import Optional, List, Dict, Any, Tuple
from datetime import datetime, timezone
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
    
    # URL Expansion Safety
    BLOCKED_IP_RANGES = [
        '127.0.0.0/8',
        '10.0.0.0/8',
        '172.16.0.0/12',
        '192.168.0.0/16',
        '169.254.0.0/16',
        '0.0.0.0/8',
        '100.64.0.0/10',
    ]
    
    BLOCKED_HOSTNAMES = {
        'localhost', 'localhost.localdomain', 'metadata.google.internal',
        '169.254.169.254',
    }
    
    MAX_REDIRECTS = 3
    EXPANSION_TIMEOUT = 5.0
    
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
        """Extract domain from URL including subdomain, excluding path.
        
        Handles:
        - URLs with or without http://https://
        - Subdomains (gift.bank.com)
        - Falls back to None if extraction fails (caller should use original URL)
        """
        try:
            # Add scheme if missing - important for proper parsing
            if not url.startswith(('http://', 'https://')):
                url = 'https://' + url
            
            parsed = urlparse(url)
            host = parsed.netloc.lower() if parsed.netloc else None
            
            if host:
                # Remove port if present (e.g., gift.bank.com:8080)
                host = host.split(':')[0]
                return host  # Includes subdomain like "gift.bank.com"
            return None
        except Exception:
            return None

    def _extract_domain_with_path(self, url: str) -> Optional[str]:
        """Extract domain + path from URL, excluding query params and fragment.
        
        Used for TI APIs to detect path-based phishing while protecting privacy.
        
        Example:
            https://example.com/login?utm_src=email&token=abc -> https://example.com/login
        """
        try:
            if not url.startswith(('http://', 'https://')):
                url = 'https://' + url
            
            parsed = urlparse(url)
            host = parsed.netloc.lower() if parsed.netloc else None
            
            if host:
                host = host.split(':')[0]
                path = parsed.path or '/'
                return f"https://{host}{path}"
            return None
        except Exception:
            return None
    
    @staticmethod
    def _hash_url(url: str) -> str:
        """Create hash for URL cache key."""
        return hashlib.sha256(url.encode()).hexdigest()[:16]
    
    @staticmethod
    def _get_risk_level_from_score(score: float) -> str:
        """Convert 0-100 score to risk level.
        
        Any positive detection is flagged as at least 'low' risk.
        """
        if score >= 80:
            return "critical"
        elif score >= 60:
            return "high"
        elif score >= 40:
            return "medium"
        elif score > 0:
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
                
                logger.debug(f"AbuseIPDB request for {ip_address}: status={response.status_code}")
                
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
    
    def _calculate_age_score(self, age_days: Optional[int]) -> Tuple[float, str]:
        """Calculate risk score based on domain age."""
        if age_days is None:
            return (0.5, 'medium')
        elif age_days < self.HIGH_RISK_AGE_DAYS:
            return (1.0, 'critical')
        elif age_days < self.MEDIUM_RISK_AGE_DAYS:
            return (0.7, 'high')
        elif age_days < 365:
            return (0.4, 'medium')
        else:
            return (0.0, 'none')
    
    async def check_domain_age(self, domain: str) -> Dict[str, Any]:
        """
        Check domain age using RDAP (free).
        
        Weight: 10% of TI score
        """
        # Clean domain - strip trailing '>' or other artifacts from email parsing
        domain = domain.rstrip('>').strip()
        
        cache_key = f"ti:domain_age:{domain}"
        cached = await self._get_from_cache(cache_key)
        if cached:
            cached['cached'] = True
            return cached
        
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(
                    f'https://rdap.org/domain/{domain}',
                    headers={'Accept': 'application/rdap+json'}
                )
                
                if response.status_code == 200:
                    data = response.json()
                    created = None
                    for event in data.get('events', []):
                        if event.get('eventAction') == 'registration':
                            created = event.get('eventDate')
                            break
                    
                    age_days = None
                    if created:
                        try:
                            created_dt = datetime.fromisoformat(created.replace('Z', '+00:00'))
                            age_days = (datetime.now(timezone.utc) - created_dt.replace(tzinfo=None)).days
                        except Exception:
                            pass
                    
                    score, risk = self._calculate_age_score(age_days)
                    
                    result = {
                        'api_name': 'rdap',
                        'success': True,
                        'score': score,
                        'risk_level': risk,
                        'data': {
                            'domain': domain,
                            'created': created,
                            'age_in_days': age_days
                        },
                        'cached': False
                    }
                    
                    await self._set_in_cache(cache_key, result, 86400 * 7)
                    return result
                else:
                    return {
                        'api_name': 'rdap',
                        'success': False,
                        'score': 0.0,
                        'risk_level': 'none',
                        'error': f'RDAP error: {response.status_code}',
                        'cached': False
                    }
        except Exception as e:
            logger.error(f"RDAP domain age check error: {e}")
            return {
                'api_name': 'rdap',
                'success': False,
                'score': 0.0,
                'risk_level': 'none',
                'error': str(e),
                'cached': False
            }
    
    async def check_domain_reputation(self, domain: str) -> Dict[str, Any]:
        """
        Check domain reputation by resolving to IPs and checking AbuseIPDB.
        
        Weight: 10% of TI score
        Note: AbuseIPDB does not have a direct domain check endpoint.
        This method resolves the domain and checks associated IPs.
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
            import socket
            ip_addresses = []
            
            try:
                result = socket.getaddrinfo(domain, None, socket.AF_INET)
                for res in result:
                    ip_addresses.append(res[4][0])
            except socket.gaierror:
                pass
            
            try:
                result = socket.getaddrinfo(domain, None, socket.AF_INET6)
                for res in result:
                    ip_addresses.append(res[4][0])
            except socket.gaierror:
                pass
            
            if not ip_addresses:
                return {
                    'api_name': 'abuseipdb_domain',
                    'success': True,
                    'score': 0.0,
                    'risk_level': 'none',
                    'data': {
                        'domain': domain,
                        'resolved_ips': [],
                        'skipped': 'No IPs resolved for domain'
                    },
                    'cached': False
                }
            
            unique_ips = list(set(ip_addresses))
            max_score = 0.0
            
            for ip in unique_ips[:3]:
                ip_result = await self.check_ip_reputation(ip)
                if ip_result.get('success'):
                    max_score = max(max_score, ip_result.get('score', 0.0) * 100)
            
            result = {
                'api_name': 'abuseipdb_domain',
                'success': True,
                'score': max_score / 100.0,
                'risk_level': self._get_risk_level_from_score(max_score),
                'data': {
                    'domain': domain,
                    'resolved_ips': unique_ips[:5],
                    'max_abuse_score': max_score
                },
                'cached': False
            }
            
            await self._set_in_cache(cache_key, result)
            return result
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
        Check URL using PhishTank (or URLScan as fallback).
        
        Weight: 15% of TI score
        
        Note: PhishTank registration is closed, so we use URLScan as primary
        phishing detection source when PhishTank is unavailable.
        """
        domain_with_path = self._extract_domain_with_path(url)
        check_target = domain_with_path if domain_with_path else url
        
        cache_key = f"ti:phishtank:{self._hash_url(check_target)}"
        cached = await self._get_from_cache(cache_key)
        if cached:
            cached['cached'] = True
            return cached
        
        if self.settings.PHISHTANK_API_KEY and self.settings.PHISHTANK_API_KEY != 'your-phishtank-api-key':
            try:
                async with httpx.AsyncClient(timeout=5.0) as client:
                    response = await client.post(
                        'https://checkurl.phishtank.com/checkurl/',
                        data={'url': check_target},
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
                                'url': check_target,
                                'original_url': url,
                                'in_database': in_db,
                                'verified': verified,
                                'phish_detail_url': data.get('phish_detail_url')
                            },
                            'cached': False
                        }
                        
                        await self._set_in_cache(cache_key, result, 43200)
                        return result
                    elif response.status_code == 403:
                        urlscan_result = await self.check_url_urlscan(url)
                        if urlscan_result.get('success'):
                            return {
                                'api_name': 'phishtank',
                                'success': True,
                                'score': urlscan_result.get('score', 0.0),
                                'risk_level': urlscan_result.get('risk_level', 'none'),
                                'data': {
                                    'url': check_target,
                                    'original_url': url,
                                    'fallback_to_urlscan': True,
                                    'urlscan_data': urlscan_result.get('data')
                                },
                                'cached': urlscan_result.get('cached', False)
                            }
                        return {
                            'api_name': 'phishtank',
                            'success': True,
                            'score': 0.0,
                            'risk_level': 'none',
                            'data': {'skipped': 'PhishTank blocked (403), URLScan unavailable'},
                            'cached': False
                        }
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
                logger.warning(f"PhishTank error, trying URLScan: {e}")
        
        urlscan_result = await self.check_url_urlscan(url)
        if urlscan_result.get('success'):
            return {
                'api_name': 'phishtank',
                'success': True,
                'score': urlscan_result.get('score', 0.0),
                'risk_level': urlscan_result.get('risk_level', 'none'),
                'data': {
                    'url': check_target,
                    'original_url': url,
                    'fallback_to_urlscan': True,
                    'urlscan_data': urlscan_result.get('data')
                },
                'cached': urlscan_result.get('cached', False)
            }
        
        return {
            'api_name': 'phishtank',
            'success': True,
            'score': 0.0,
            'risk_level': 'none',
            'data': {'skipped': 'PhishTank unavailable (registration closed), URLScan failed'},
            'cached': False
        }
    
    async def check_url_virustotal(self, url: str) -> Dict[str, Any]:
        """
        Check URL using VirusTotal.
        
        Weight: 15% of TI score
        
        Privacy: Extract domain + path to detect path-based phishing, exclude query params
        """
        import urllib.parse
        import base64
        
        # Extract domain for privacy - don't send full URLs with tokens
        domain_with_path = self._extract_domain_with_path(url)
        check_target = domain_with_path if domain_with_path else url
        
        cache_key = f"ti:vt_url:{self._hash_url(check_target)}"
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
            # Use base64 encoding (without padding) as required by VT v3 API
            encoded_url = base64.urlsafe_b64encode(check_target.encode()).decode().rstrip('=')
            async with httpx.AsyncClient(timeout=5.0) as client:
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
                            'url': check_target,  # Domain only for privacy
                            'original_url': url,  # Keep original for reference
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
                        'data': {'url': check_target, 'original_url': url, 'not_found': True},
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
        
        Privacy: Extract domain + path to detect path-based phishing, exclude query params
        """
        # Extract domain for privacy
        domain_with_path = self._extract_domain_with_path(url)
        check_target = domain_with_path if domain_with_path else url
        
        if not self.settings.ENABLE_URLSCAN_BACKUP:
            return {
                'api_name': 'urlscan',
                'success': True,
                'score': 0.0,
                'risk_level': 'none',
                'data': {'skipped': True},
                'cached': False
            }
        
        cache_key = f"ti:urlscan:{self._hash_url(check_target)}"
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
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(
                    'https://urlscan.io/api/v1/scan/',
                    data=json.dumps({'url': check_target, 'visibility': 'public'}),
                    headers={
                        'Content-Type': 'application/json',
                        'API-Key': self.settings.URLSCAN_API_KEY
                    }
                )
                
                if response.status_code == 200:
                    data = response.json()
                    result_uuid = data.get('uuid')
                    
                    max_retries = 3
                    retry_delay = 1.0
                    
                    for attempt in range(max_retries):
                        await asyncio.sleep(retry_delay)
                        
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
                                    'url': check_target,
                                    'original_url': url,
                                    'score': overall.get('score', 0),
                                    'categories': overall.get('categories', []),
                                    'permalink': f"https://urlscan.io/result/{result_uuid}/"
                                },
                                'cached': False
                            }
                            
                            await self._set_in_cache(cache_key, result, 43200)
                            return result
                        
                        if result_response.status_code == 404:
                            logger.debug(f"URLScan result not ready (attempt {attempt + 1}/{max_retries}): {result_uuid}")
                            retry_delay *= 1.5
                            continue
                        
                        break
                    
                    logger.debug(f"URLScan result unavailable after {max_retries} attempts: {result_uuid}")
                
                if response.status_code == 400:
                    logger.debug(f"URLScan rejected URL (400): {check_target}")
                
                return {
                    'api_name': 'urlscan',
                    'success': False,
                    'score': 0.0,
                    'risk_level': 'none',
                    'error': f'API error: {response.status_code}',
                    'cached': False
                }
                
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
            'rdap': 0.10,
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
        
        tasks = []  # Reserved for additional async tasks
        initial_tasks = []
        
        if sender_domain:
            domain_age_task = self.check_domain_age(sender_domain)
            initial_tasks.append(('rdap', domain_age_task))
            
            domain_rep_task = self.check_domain_reputation(sender_domain)
            initial_tasks.append(('domain_reputation', domain_rep_task))
        
        url_expansions = {}
        for url in urls[:5]:
            expansion = await self.expand_url(url)
            url_expansions[url] = {
                'expanded': expansion['expanded'],
                'final_domain': expansion['final_domain'],
                'blocked': expansion['blocked_reason'] is not None
            }
            
            ti_url = expansion['expanded'] if expansion['success'] else url
            initial_tasks.append(('phishtank', self.check_url_phishtank(ti_url)))
            initial_tasks.append(('virustotal_url', self.check_url_virustotal(ti_url)))
        
        for hash_val in attachment_hashes[:3]:
            initial_tasks.append(('virustotal_hash', self.check_hash_virustotal(hash_val)))
        
        task_results = {}
        if initial_tasks:
            results = await asyncio.gather(*[task for _, task in initial_tasks], return_exceptions=True)
            for (key, _), result in zip(initial_tasks, results):
                if isinstance(result, Exception):
                    logger.error(f"Task {key} failed: {result}")
                    task_results[key] = {'success': False, 'error': str(result)}
                else:
                    task_results[key] = result
        
        preliminary_score = 0.0
        preliminary_weight = 0.0
        for api_name, weight in [('rdap', 0.10), ('domain_reputation', 0.10), ('phishtank', 0.15), ('virustotal_url', 0.15), ('virustotal_hash', 0.10), ('urlscan', 0.10)]:
            result = task_results.get(api_name, {})
            if result.get('success'):
                score = result.get('score', 0.0)
                preliminary_score += score * weight
                preliminary_weight += weight
        
        if preliminary_weight > 0:
            preliminary_score = preliminary_score / preliminary_weight
        
        if sender_domain and preliminary_score > 0.3:
            logger.debug(f"Domain {sender_domain} preliminary TI score {preliminary_score:.2f} - checking AbuseIPDB")
            try:
                ip_result = await self._resolve_and_check_ip(sender_domain)
                task_results['abuseipdb'] = ip_result
            except Exception as e:
                logger.error(f"AbuseIPDB check failed: {e}")
                task_results['abuseipdb'] = {'success': False, 'error': str(e)}
        
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
            'url_expansions': url_expansions,
            'analysis_timestamp': datetime.now(timezone.utc).isoformat()
        }
    
    async def _resolve_and_check_ip(self, domain: str) -> Dict[str, Any]:
        """Resolve domain to IP and check reputation."""
        import socket
        try:
            logger.debug(f"Resolving domain: {domain}")
            ip_address = socket.gethostbyname(domain)
            logger.debug(f"Resolved {domain} -> {ip_address}, checking AbuseIPDB...")
            return await self.check_ip_reputation(ip_address)
        except socket.gaierror:
            return {
                'api_name': 'abuseipdb',
                'success': False,
                'score': 0.0,
                'risk_level': 'none',
                'error': f'Could not resolve domain: {domain}'
            }
    
    async def expand_url(self, url: str) -> Dict[str, Any]:
        """
        Expand shortened URLs by following redirects safely.
        
        Returns:
            {
                'original': str,
                'expanded': str or None,
                'success': bool,
                'blocked_reason': str or None,
                'final_domain': str or None
            }
        """
        import ipaddress
        
        cache_key = f"ti:url_expand:{self._hash_url(url)}"
        cached = await self._get_from_cache(cache_key)
        if cached:
            return cached
        
        result = {
            'original': url,
            'expanded': None,
            'success': False,
            'blocked_reason': None,
            'final_domain': None
        }
        
        try:
            parsed = urlparse(url if url.startswith(('http://', 'https://')) else f'https://{url}')
            initial_host = parsed.netloc.split(':')[0].lower()
            
            if initial_host in self.BLOCKED_HOSTNAMES or initial_host.endswith('.local'):
                result['blocked_reason'] = 'internal_hostname'
                await self._set_in_cache(cache_key, result, 86400)
                return result
            
            try:
                ip = ipaddress.ip_address(initial_host)
                for blocked in self.BLOCKED_IP_RANGES:
                    if ip in ipaddress.ip_network(blocked):
                        result['blocked_reason'] = 'blocked_ip_range'
                        await self._set_in_cache(cache_key, result, 86400)
                        return result
            except ValueError:
                pass
            
            async with httpx.AsyncClient(
                timeout=self.EXPANSION_TIMEOUT,
                follow_redirects=True,
                max_redirects=self.MAX_REDIRECTS,
                headers={'User-Agent': 'PhishCatcher/1.0'}
            ) as client:
                response = await client.head(url)
                
                final_url = str(response.url)
                result['expanded'] = final_url
                result['success'] = True
                
                final_parsed = urlparse(final_url)
                final_host = final_parsed.netloc.split(':')[0].lower()
                
                if final_host in self.BLOCKED_HOSTNAMES or final_host.endswith('.local'):
                    result['blocked_reason'] = 'final_destination_internal'
                    result['final_domain'] = None
                else:
                    result['final_domain'] = final_host
                
                await self._set_in_cache(cache_key, result, 3600)
                return result
                
        except httpx.TimeoutException:
            result['blocked_reason'] = 'timeout'
            await self._set_in_cache(cache_key, result, 300)
            return result
        except Exception as e:
            logger.warning(f"URL expansion failed for {url}: {e}")
            result['blocked_reason'] = f'error: {str(e)}'
            await self._set_in_cache(cache_key, result, 300)
            return result


def transform_ti_for_storage(ti_result: dict) -> dict:
    """
    Transform threat intel results into frontend-compatible format for storage.
    
    Converts raw API results with nested 'data' and 'api_results' into a flat
    structure with 'indicators' containing api_name, details, score, and risk_level.
    
    Preserves original URLs from url_expansions for proper domain matching.
    """
    indicators = []
    api_results = ti_result.get('api_results', {})
    url_expansions = ti_result.get('url_expansions', {})
    
    if api_results.get('abuseipdb', {}).get('success'):
        data = api_results['abuseipdb'].get('data', {})
        indicators.append({
            'api_name': 'abuseipdb',
            'indicator_type': 'ip_reputation',
            'indicator_value': data.get('ip_address', ''),
            'details': {
                'abuse_confidence_score': data.get('abuse_confidence_score', 0),
                'num_reports': data.get('num_reports', 0),
                'num_distinct_users': data.get('num_distinct_users', 0),
                'country_code': data.get('country_code'),
                'isp': data.get('isp'),
                'domain': data.get('domain'),
                'is_whitelisted': data.get('is_whitelisted', False),
            },
            'score': api_results['abuseipdb'].get('score', 0),
            'risk_level': api_results['abuseipdb'].get('risk_level', 'none')
        })
    
    if api_results.get('rdap', {}).get('success'):
        data = api_results['rdap'].get('data', {})
        indicators.append({
            'api_name': 'rdap',
            'indicator_type': 'domain_age',
            'indicator_value': data.get('domain', ''),
            'details': {
                'age_in_days': data.get('age_in_days'),
                'created': data.get('created'),
            },
            'score': api_results['rdap'].get('score', 0),
            'risk_level': api_results['rdap'].get('risk_level', 'none')
        })
    
    if api_results.get('abuseipdb_domain', {}).get('success'):
        data = api_results['abuseipdb_domain'].get('data', {})
        indicators.append({
            'api_name': 'abuseipdb_domain',
            'indicator_type': 'domain_reputation',
            'indicator_value': data.get('domain', ''),
            'details': {
                'resolved_ips': data.get('resolved_ips', []),
                'max_abuse_score': data.get('max_abuse_score', 0),
            },
            'score': api_results['abuseipdb_domain'].get('score', 0),
            'risk_level': api_results['abuseipdb_domain'].get('risk_level', 'none')
        })
    
    phishtank_result = api_results.get('phishtank', {})
    if phishtank_result.get('success'):
        data = phishtank_result.get('data', {})
        fallback = data.get('fallback_to_urlscan', False)
        indicator_url = data.get('url', '')
        original_url = data.get('original_url', '')
        
        # Find the ORIGINAL email URL that led to this indicator
        if not original_url or original_url == indicator_url:
            for orig, exp in url_expansions.items():
                if exp.get('final_domain') == indicator_url or indicator_url in (exp.get('expanded') or ''):
                    original_url = orig
                    break
        
        indicators.append({
            'api_name': 'phishtank',
            'indicator_type': 'phishing_check',
            'indicator_value': indicator_url,
            'original_url': original_url,
            'details': {
                'in_database': data.get('in_database', False),
                'verified': data.get('verified', False),
                'fallback_to_urlscan': fallback,
                'urlscan_data': data.get('urlscan_data') if fallback else None,
            },
            'score': phishtank_result.get('score', 0),
            'risk_level': phishtank_result.get('risk_level', 'none')
        })
    
    if api_results.get('virustotal_url', {}).get('success'):
        data = api_results['virustotal_url'].get('data', {})
        stats = data.get('last_analysis_stats', {})
        indicator_url = data.get('url', '')  # This is the domain that was checked
        original_url = data.get('original_url', '')  # This is the expanded URL
        
        # Find the ORIGINAL email URL that led to this indicator
        final_domain = data.get('url', '')  # Domain that was checked
        if final_domain:
            for orig, exp in url_expansions.items():
                # Match by final domain
                if exp.get('final_domain') == final_domain or final_domain in (exp.get('expanded') or ''):
                    original_url = orig
                    break
        
        indicators.append({
            'api_name': 'virustotal_url',
            'indicator_type': 'url_reputation',
            'indicator_value': indicator_url,
            'original_url': original_url,
            'details': {
                'malicious': stats.get('malicious', 0),
                'suspicious': stats.get('suspicious', 0),
                'harmless': stats.get('harmless', 0),
                'undetected': stats.get('undetected', 0),
                'threat_names': data.get('threat_names', []),
            },
            'score': api_results['virustotal_url'].get('score', 0),
            'risk_level': api_results['virustotal_url'].get('risk_level', 'none')
        })
    
    if api_results.get('virustotal_hash', {}).get('success'):
        data = api_results['virustotal_hash'].get('data', {})
        stats = data.get('last_analysis_stats', {})
        indicators.append({
            'api_name': 'virustotal_hash',
            'indicator_type': 'file_reputation',
            'indicator_value': data.get('hash', ''),
            'details': {
                'malicious': stats.get('malicious', 0),
                'suspicious': stats.get('suspicious', 0),
                'file_type': data.get('file_type'),
                'file_size': data.get('file_size'),
            },
            'score': api_results['virustotal_hash'].get('score', 0),
            'risk_level': api_results['virustotal_hash'].get('risk_level', 'none')
        })
    
    if api_results.get('urlscan', {}).get('success'):
        data = api_results['urlscan'].get('data', {})
        indicators.append({
            'api_name': 'urlscan',
            'indicator_type': 'url_analysis',
            'indicator_value': data.get('url', ''),
            'details': {
                'score': data.get('score', 0),
                'categories': data.get('categories', []),
                'permalink': data.get('permalink'),
            },
            'score': api_results['urlscan'].get('score', 0),
            'risk_level': api_results['urlscan'].get('risk_level', 'none')
        })
    
    return {
        'overall_risk_score': ti_result.get('overall_risk_score', 0),
        'risk_category': ti_result.get('risk_category', 'unknown'),
        'confidence': ti_result.get('confidence', 0),
        'indicators': indicators,
        'warnings': ti_result.get('warnings', []),
        'url_expansions': ti_result.get('url_expansions', {}),
        'analysis_timestamp': ti_result.get('analysis_timestamp')
    }


_threat_intel_instance: Optional[ThreatIntelService] = None


def get_threat_intel_service() -> ThreatIntelService:
    """Get singleton instance of threat intel service."""
    global _threat_intel_instance
    if _threat_intel_instance is None:
        _threat_intel_instance = ThreatIntelService()
    return _threat_intel_instance