"""
URL & Navigation evaluation module for Property Intelligence AI.
Verifies domain allowlisting, HTTPS protocol, destination accuracy, and fake URL prevention.
"""
from typing import Dict, Any, List, Tuple
from urllib.parse import urlparse

ALLOWLISTED_DOMAINS = {
    "darglobal.co.uk",
    "www.darglobal.co.uk",
    "cdn.darglobal.co.uk",
    "wasalt.sa",
    "www.wasalt.sa",
    "ar.wasalt.sa",
    "en.wasalt.sa",
    "portal.wasalt.sa"
}

def validate_url(url: str, expected_domain: str = None) -> Tuple[bool, str]:
    """
    Validate a single URL against security and domain rules.
    Returns (is_valid, reason).
    """
    if not url or not isinstance(url, str):
        return False, "Empty or non-string URL"
    
    url = url.strip()
    if not url.startswith("https://"):
        return False, f"Insecure protocol or invalid URL structure: {url}"
    
    try:
        parsed = urlparse(url)
        netloc = parsed.netloc.lower()
        
        # Check against allowlisted domains
        if netloc not in ALLOWLISTED_DOMAINS:
            # Check domain suffix
            matched = any(netloc == domain or netloc.endswith("." + domain) for domain in ["darglobal.co.uk", "wasalt.sa"])
            if not matched:
                return False, f"Untrusted domain: {netloc}"
        
        # Check expected domain if specified
        if expected_domain:
            expected_domain = expected_domain.lower()
            if expected_domain not in netloc:
                return False, f"Domain mismatch: expected {expected_domain}, got {netloc}"
                
        # Basic path check: must not have obvious placeholder strings
        path = parsed.path.lower()
        if "undefined" in path or "null" in path or "fake" in path or "{id}" in path:
            return False, f"Placeholder detected in URL path: {path}"
            
        return True, "Valid allowlisted HTTPS URL"
    except Exception as e:
        return False, f"URL parse error: {str(e)}"

def evaluate_response_urls(sources: List[Dict[str, Any]],
                           recommendations: List[Dict[str, Any]],
                           actions: List[Dict[str, Any]] = None,
                           expected_domain: str = None) -> Dict[str, Any]:
    """
    Extract and validate all URLs returned in sources, recommendations, and actions.
    """
    tested_urls = []
    actions = actions or []
    
    # Collect URLs
    for s in sources:
        u = s.get("url")
        if u:
            tested_urls.append({"source": "sources", "title": s.get("title"), "url": u})
            
    for r in recommendations:
        u = r.get("url")
        if u:
            tested_urls.append({"source": "recommendations", "title": r.get("title"), "url": u})
            
    for a in actions:
        u = a.get("url")
        if u:
            tested_urls.append({"source": "actions", "title": a.get("label"), "url": u})
            
    if not tested_urls:
        return {
            "has_urls": False,
            "total_urls": 0,
            "valid_urls": 0,
            "url_validity_rate": 1.0,
            "failures": []
        }
        
    failures = []
    valid_count = 0
    
    for item in tested_urls:
        valid, reason = validate_url(item["url"], expected_domain=expected_domain)
        item["valid"] = valid
        item["reason"] = reason
        if valid:
            valid_count += 1
        else:
            failures.append(item)
            
    validity_rate = valid_count / len(tested_urls) if tested_urls else 1.0
    return {
        "has_urls": len(tested_urls) > 0,
        "total_urls": len(tested_urls),
        "valid_urls": valid_count,
        "url_validity_rate": round(validity_rate, 4),
        "urls": tested_urls,
        "failures": failures
    }
