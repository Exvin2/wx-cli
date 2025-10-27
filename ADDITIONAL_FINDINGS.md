# Additional Security Vulnerabilities & Issues - Deep Scan

**Deep Scan Date**: 2025-10-26
**Previous Audit**: SECURITY_AUDIT.md (7 vulnerabilities)
**Additional Findings**: 11 new vulnerabilities + 8 additional issues

---

## New Critical & High Priority Vulnerabilities

### 🔴 CRITICAL #3: Station ID Injection in Aviation Module

**File**: `wx/aviation.py:29, 82`
**Severity**: CRITICAL
**CWE**: CWE-918 (SSRF)

**Issue**:
Aviation station IDs are directly interpolated into URLs without validation:

```python
# Line 29
url = f"https://aviationweather.gov/cgi-bin/data/metar.php?ids={station_id}&format=json"

# Line 82  
url = f"https://aviationweather.gov/cgi-bin/data/taf.php?ids={station_id}&format=json"
```

**Attack Scenarios**:
```bash
wx aviation "../../../../../../../etc/passwd"
wx aviation "KDEN&malicious=param"
wx aviation "KDEN%00null_byte"
```

**Fix**:
```python
import re

def validate_icao_station(station_id: str) -> str:
    """Validate ICAO station ID format.
    
    Args:
        station_id: Station identifier
        
    Returns:
        Validated station ID
        
    Raises:
        ValueError: If station ID is invalid
    """
    # ICAO codes are 4 letters (e.g., KDEN, EGLL)
    if not re.match(r'^[A-Z]{4}$', station_id.upper()):
        raise ValueError(f"Invalid ICAO station ID: {station_id}")
    
    return station_id.upper()

# Use in functions:
def get_metar(station_id: str, **kwargs):
    station_id = validate_icao_station(station_id)
    url = f"https://aviationweather.gov/cgi-bin/data/metar.php?ids={station_id}&format=json"
    # ... rest of code
```

**Status**: ❌ UNPATCHED

---

### 🔴 CRITICAL #4: Station ID Injection in Marine Module

**File**: `wx/marine.py:61`
**Severity**: CRITICAL
**CWE**: CWE-918 (SSRF)

**Issue**:
NOAA buoy station IDs interpolated without validation:

```python
url = f"https://www.ndbc.noaa.gov/data/realtime2/{station_id}.txt"
```

**Attack**:
```bash
wx marine buoy "../../../etc/passwd"
wx marine buoy "../../../../config"
```

**Fix**:
```python
def validate_buoy_id(station_id: str) -> str:
    """Validate NOAA buoy station ID.
    
    Args:
        station_id: Buoy identifier
        
    Returns:
        Validated station ID
        
    Raises:
        ValueError: If station ID is invalid
    """
    # NOAA buoy IDs are typically 5 alphanumeric characters
    if not re.match(r'^[A-Z0-9]{5}$', station_id.upper()):
        raise ValueError(f"Invalid buoy station ID: {station_id}")
    
    return station_id.upper()
```

**Status**: ❌ UNPATCHED

---

### 🟠 HIGH #6: Insecure HTTP in UK Met Office API

**File**: `wx/international.py:13`
**Severity**: HIGH
**CWE**: CWE-319 (Cleartext Transmission of Sensitive Information)

**Issue**:
Met Office API uses HTTP instead of HTTPS:

```python
BASE_URL = "http://datapoint.metoffice.gov.uk/public/data"
```

**Risk**:
- API keys transmitted in cleartext
- Man-in-the-middle attacks
- Data integrity not guaranteed
- Credential theft

**Fix**:
```python
# Change to HTTPS
BASE_URL = "https://datapoint.metoffice.gov.uk/public/data"

# Verify SSL is enforced in requests
response = self.session.get(url, params=params, timeout=self.timeout, verify=True)
```

**Verification**:
```bash
# Test if HTTPS is available
curl -I https://datapoint.metoffice.gov.uk/public/data
```

**Status**: ❌ UNPATCHED

---

### 🟠 HIGH #7: No SSL Certificate Verification Configuration

**File**: All HTTP client code
**Severity**: HIGH
**CWE**: CWE-295 (Improper Certificate Validation)

**Issue**:
While `httpx` and `requests` verify SSL by default, there's no explicit configuration or ability to pin certificates.

**Risk**:
- Vulnerable to man-in-the-middle if defaults change
- No protection against certificate pinning bypass
- No logging of certificate issues

**Recommendation**:
```python
# Add explicit SSL verification and logging
import ssl
import certifi

def create_secure_client(timeout: float) -> httpx.Client:
    """Create HTTP client with enforced SSL verification."""
    ssl_context = ssl.create_default_context(cafile=certifi.where())
    ssl_context.check_hostname = True
    ssl_context.verify_mode = ssl.CERT_REQUIRED
    
    return httpx.Client(
        timeout=timeout,
        headers={"User-Agent": USER_AGENT},
        verify=ssl_context,  # Explicit verification
        event_hooks={
            'request': [log_request],
            'response': [log_response, check_ssl_errors]
        }
    )

def check_ssl_errors(response):
    """Log SSL certificate issues."""
    if hasattr(response, 'ssl') and response.ssl:
        logger.debug(f"SSL verified: {response.url} - {response.ssl}")
```

**Status**: ⚠️ ACCEPTABLE (defaults are secure, but should be explicit)

---

### 🟠 HIGH #8: URL Parameter Injection in Multiple APIs

**File**: `wx/fetchers.py:482, 533, 570, 607`
**Severity**: HIGH
**CWE**: CWE-88 (Argument Injection)

**Issue**:
Latitude and longitude values directly embedded in f-strings:

```python
# Line 482
points_url = f"https://api.weather.gov/points/{lat:.4f},{lon:.4f}"

# Line 533
url = f"https://api.weather.gov/points/{lat:.4f},{lon:.4f}/stations"

# Line 570
url = f"https://api.weather.gov/stations/{station_id}/observations/latest"

# Line 607
points_url = f"https://api.weather.gov/points/{lat:.4f},{lon:.4f}"
```

**Vulnerability**:
While `.4f` formatting provides some protection, malicious float values could still cause issues:
- Extremely large numbers
- Special float values (inf, -inf, nan)
- Locale-specific formatting issues

**Fix**:
```python
def sanitize_coordinate(value: float, coord_type: str) -> float:
    """Sanitize coordinate value.
    
    Args:
        value: Coordinate value
        coord_type: 'lat' or 'lon'
        
    Returns:
        Sanitized float
        
    Raises:
        ValueError: If coordinate is invalid
    """
    if not isinstance(value, (int, float)):
        raise ValueError(f"Invalid {coord_type}: must be numeric")
    
    if math.isnan(value) or math.isinf(value):
        raise ValueError(f"Invalid {coord_type}: cannot be NaN or Inf")
    
    if coord_type == 'lat':
        if not (-90 <= value <= 90):
            raise ValueError(f"Invalid latitude: {value}")
    elif coord_type == 'lon':
        if not (-180 <= value <= 180):
            raise ValueError(f"Invalid longitude: {value}")
    
    return round(value, 4)  # Limit precision

# Use in code:
lat = sanitize_coordinate(lat, 'lat')
lon = sanitize_coordinate(lon, 'lon')
points_url = f"https://api.weather.gov/points/{lat},{lon}"
```

**Status**: ❌ UNPATCHED

---

### 🟡 MEDIUM #7: GitHub Repository URL in User-Agent

**File**: `wx/fetchers.py:14`, `wx/openrouter_client.py:73`
**Severity**: MEDIUM  
**CWE**: CWE-200 (Information Exposure)

**Issue**:
GitHub repository URL exposed in every HTTP request:

```python
# fetchers.py:14
USER_AGENT = "wx-cli/0.1 (+https://github.com/Exvin2/claudex-cli)"

# openrouter_client.py:73
"HTTP-Referer": "https://github.com/Exvin2/claudex-cli",
```

**Risk**:
- Repository discovery by attackers
- Codebase analysis to find vulnerabilities
- Targeted attacks based on known code
- Privacy leak for internal deployments

**Fix**:
```python
# Make URL configurable
import os

REPO_URL = os.getenv("WX_REPO_URL", "https://example.com/weather-cli")
USER_AGENT = f"wx-cli/{__version__} (+{REPO_URL})"

# Or remove entirely for privacy:
USER_AGENT = f"wx-cli/{__version__}"
```

**Status**: ⚠️ LOW RISK (common practice, but configurable is better)

---

### 🟡 MEDIUM #8: Predictable Synthetic Data Generation

**File**: Multiple files using `random` module
**Severity**: MEDIUM
**CWE**: CWE-338 (Use of Cryptographically Weak PRNG)

**Issue**:
Using `random` module for synthetic data generation:

```python
# wx/dashboard.py:223-231
"temperature": random.randint(30, 90),
"humidity": random.randint(20, 90),

# wx/hurricanes.py:88
if random.random() < 0.3:
    num_storms = random.randint(1, 3)

# wx/lightning.py:75, 79-87
num_strikes = random.randint(5, 20)
offset_lat = random.uniform(-radius_km / 111, radius_km / 111)
```

**Risk**:
- Predictable random values if seed is known
- Not suitable for any security-related randomness
- Could affect test reproducibility

**Note**: This is LOW RISK for synthetic data generation (not cryptographic use), but should be documented.

**Status**: ✅ ACCEPTABLE (not cryptographic use, documented as synthetic)

---

### 🟡 MEDIUM #9: No Timeout on Retry Logic

**File**: `wx/openrouter_client.py:91-119`
**Severity**: MEDIUM
**CWE**: CWE-400 (Uncontrolled Resource Consumption)

**Issue**:
Retry logic with exponential backoff but no maximum total time limit:

```python
for attempt in range(1, config.retries + 1):
    attempts = attempt
    try:
        # ... request ...
    except httpx.HTTPStatusError as exc:
        # ... error handling ...
        time.sleep(backoff)
        backoff *= 2  # No maximum backoff limit!
        continue
```

**Risk**:
- Requests could hang indefinitely
- Exponential backoff could grow very large (2^n)
- No circuit breaker for persistent failures

**Fix**:
```python
MAX_BACKOFF = 60.0  # seconds
TOTAL_TIMEOUT = 300.0  # 5 minutes total

start_time = time.time()

for attempt in range(1, config.retries + 1):
    # Check total timeout
    if time.time() - start_time > TOTAL_TIMEOUT:
        raise OpenRouterError("Request timeout exceeded")
    
    try:
        # ... request ...
    except Exception as exc:
        # Cap backoff time
        sleep_time = min(backoff, MAX_BACKOFF)
        time.sleep(sleep_time)
        backoff = min(backoff * 2, MAX_BACKOFF)
        continue
```

**Status**: ❌ UNPATCHED

---

### 🟡 MEDIUM #10: JSON Parsing Without Size Limits

**File**: Multiple files
**Severity**: MEDIUM
**CWE**: CWE-400 (Resource Exhaustion)

**Issue**:
JSON responses parsed without size limits:

```python
# wx/openrouter_client.py:122-130
data = response.json()  # No size check
return OpenRouterResponse(text=_extract_text(data), ...)

# wx/fetchers.py:62
return response.json()  # No size limit
```

**Risk**:
- Memory exhaustion from large JSON responses
- DoS via "billion laughs" style attacks
- Slow parsing of deeply nested structures

**Fix**:
```python
import sys

MAX_JSON_SIZE = 10 * 1024 * 1024  # 10MB
MAX_JSON_DEPTH = 50

def safe_json_parse(response: httpx.Response) -> dict:
    """Safely parse JSON with size and depth limits.
    
    Args:
        response: HTTP response
        
    Returns:
        Parsed JSON dict
        
    Raises:
        ValueError: If JSON is too large or too nested
    """
    content = response.content
    
    if len(content) > MAX_JSON_SIZE:
        raise ValueError(f"JSON response too large: {len(content)} bytes")
    
    # Set recursion limit for JSON parsing
    old_limit = sys.getrecursionlimit()
    try:
        sys.setrecursionlimit(MAX_JSON_DEPTH)
        data = response.json()
        return data
    finally:
        sys.setrecursionlimit(old_limit)
```

**Status**: ❌ UNPATCHED

---

### 🟡 MEDIUM #11: No API Response Validation

**File**: `wx/openrouter_client.py:155-168`
**Severity**: MEDIUM
**CWE**: CWE-20 (Improper Input Validation)

**Issue**:
OpenRouter API responses parsed without schema validation:

```python
def _extract_text(data: Mapping[str, Any]) -> str:
    """Extract text from an OpenRouter response dictionary."""
    choices = data.get("choices")
    if not isinstance(choices, list) or not choices:
        return ""
    message = choices[0].get("message") if isinstance(choices[0], Mapping) else None
    if not isinstance(message, Mapping):
        return ""
    content = message.get("content")
    if isinstance(content, str):
        return content.strip()
    # ... more parsing
```

**Risk**:
- Type confusion vulnerabilities
- Unexpected data structure crashes
- Missing error handling for malformed responses

**Fix**:
```python
from typing import TypedDict

class OpenRouterMessage(TypedDict):
    role: str
    content: str

class OpenRouterChoice(TypedDict):
    message: OpenRouterMessage
    finish_reason: str

class OpenRouterAPIResponse(TypedDict):
    choices: list[OpenRouterChoice]
    model: str
    usage: dict

def validate_openrouter_response(data: dict) -> OpenRouterAPIResponse:
    """Validate OpenRouter API response structure.
    
    Args:
        data: Raw API response
        
    Returns:
        Validated response
        
    Raises:
        ValueError: If response structure is invalid
    """
    if not isinstance(data, dict):
        raise ValueError("Response must be a dictionary")
    
    if "choices" not in data:
        raise ValueError("Missing 'choices' field")
    
    choices = data["choices"]
    if not isinstance(choices, list) or not choices:
        raise ValueError("'choices' must be a non-empty list")
    
    for choice in choices:
        if not isinstance(choice, dict):
            raise ValueError("Each choice must be a dictionary")
        if "message" not in choice:
            raise ValueError("Choice missing 'message' field")
        
        message = choice["message"]
        if not isinstance(message, dict):
            raise ValueError("Message must be a dictionary")
        if "content" not in message:
            raise ValueError("Message missing 'content' field")
    
    return data  # Type checked
```

**Status**: ❌ UNPATCHED

---

### 🟡 MEDIUM #12: User-Agent Version Inconsistency

**File**: `wx/fetchers.py:14` vs `wx/hurricanes.py:30`
**Severity**: LOW
**CWE**: CWE-1104 (Use of Unmaintained Third Party Components)

**Issue**:
Different version strings in User-Agent headers:

```python
# wx/fetchers.py:14
USER_AGENT = "wx-cli/0.1 (+https://github.com/Exvin2/claudex-cli)"

# wx/hurricanes.py:30
"User-Agent": "wx-cli/1.0 (Weather CLI Tool)"
```

**Risk**:
- Inconsistent version tracking
- Confusion in server logs
- Difficult to debug issues

**Fix**:
Create central version management (see CODE_ISSUES.md #10).

**Status**: ❌ UNPATCHED

---

## Additional Code Quality Issues

### 1. Missing Input Sanitization in Chat Module

**File**: `wx/chat.py`
**Severity**: LOW

**Issue**:
User input from chat not sanitized before processing:

```python
user_input = Prompt.ask("\n[bright_blue]▶[/bright_blue]")
```

No validation on:
- Input length
- Special characters
- Control characters

**Recommendation**: Add input validation similar to location validation.

---

### 2. No Rate Limiting Across Modules

**Severity**: MEDIUM

**Issue**:
Each API client (radar, aviation, marine, international, etc.) makes requests independently with no global rate limiting.

**Risk**:
- Could exceed API rate limits across all features combined
- No backoff coordination between modules
- Potential for ban from external services

**Recommendation**: Implement global rate limiter (see CODE_ISSUES.md #5).

---

### 3. Dependency Versions Not Pinned

**File**: `pyproject.toml`
**Severity**: MEDIUM

**Issue**:
Dependencies use minimum version constraints without maximum:

```toml
dependencies = [
    "typer>=0.9",        # Could use any future version
    "rich>=13",          # Breaking changes possible
    "httpx>=0.24",       # Security updates needed
]
```

**Risk**:
- Breaking changes in dependencies
- Security vulnerabilities in new versions
- Inconsistent behavior across installations

**Fix**:
```toml
dependencies = [
    "typer>=0.9,<1.0",
    "rich>=13,<14",
    "httpx>=0.24,<1.0",
    "python-dateutil>=2.8,<3.0",
]

# Or use requirements.txt with pinned versions:
# typer==0.20.0
# rich==14.2.0
# httpx==0.28.1
```

**Status**: ❌ UNPATCHED

---

### 4. No Content-Type Validation

**File**: All API clients
**Severity**: LOW

**Issue**:
HTTP responses parsed without checking Content-Type header:

```python
response = self.session.get(url, timeout=self.timeout)
response.raise_for_status()
return response.json()  # Assumes JSON, doesn't check Content-Type
```

**Risk**:
- Parsing HTML error pages as JSON
- Missing server-side errors
- Type confusion vulnerabilities

**Fix**:
```python
response = self.session.get(url, timeout=self.timeout)
response.raise_for_status()

content_type = response.headers.get('Content-Type', '')
if 'application/json' not in content_type:
    raise ValueError(f"Expected JSON, got {content_type}")

return response.json()
```

**Status**: ❌ UNPATCHED

---

### 5. Missing Request/Response Logging

**Severity**: LOW

**Issue**:
No centralized logging of API requests for debugging or security auditing.

**Recommendation**:
```python
import logging

logger = logging.getLogger(__name__)

def log_api_request(url: str, params: dict = None):
    """Log API request for audit trail."""
    logger.info(f"API Request: {url}", extra={
        "url": url,
        "params": params,
        "timestamp": datetime.now(UTC).isoformat()
    })

def log_api_response(url: str, status: int, size: int):
    """Log API response for monitoring."""
    logger.info(f"API Response: {url} - {status} ({size} bytes)")
```

---

### 6. No Circuit Breaker Pattern

**Severity**: MEDIUM

**Issue**:
No circuit breaker for repeatedly failing APIs. Will keep retrying even if service is down.

**Recommendation**:
Implement circuit breaker pattern with states: CLOSED → OPEN → HALF_OPEN

---

### 7. Missing Security Headers

**File**: All HTTP clients
**Severity**: LOW

**Issue**:
No security-related headers sent with requests:

```python
# Missing headers:
# - X-Request-ID (for request tracking)
# - X-Client-Version (for version tracking)
# - Accept-Encoding (for compression)
```

**Recommendation**:
```python
headers = {
    "User-Agent": USER_AGENT,
    "Accept": "application/json",
    "Accept-Encoding": "gzip, deflate",
    "X-Request-ID": generate_request_id(),
    "X-Client-Version": __version__,
}
```

---

### 8. Timezone Issues in Synthetic Data

**File**: `wx/lightning.py:85`
**Severity**: LOW

**Issue**:
Synthetic lightning data uses `datetime.now(UTC)` but doesn't validate timezone consistency:

```python
"time": datetime.now(UTC) - timedelta(minutes=random.randint(1, 30)),
```

**Recommendation**: Ensure all timestamps are UTC-aware throughout codebase.

---

## Dependency Security Check

Current installed versions:
- httpx 0.28.1 ✅
- requests 2.32.5 ✅  
- urllib3 2.5.0 ✅
- pillow 12.0.0 ✅ (but check for known CVEs)
- rich 14.2.0 ✅
- typer 0.20.0 ✅

**Action Required**:
```bash
# Check for known vulnerabilities
pip install safety
safety check

# Or use pip-audit
pip install pip-audit
pip-audit
```

---

## Summary Statistics

### New Findings

| Severity | Previous | New | Total |
|----------|----------|-----|-------|
| CRITICAL | 2 | 2 | 4 |
| HIGH | 3 | 3 | 6 |
| MEDIUM | 2 | 6 | 8 |
| LOW | 0 | 8 | 8 |
| **TOTAL** | **7** | **19** | **26** |

### By Category

| Category | Count |
|----------|-------|
| SSRF/Injection | 6 |
| Input Validation | 4 |
| Information Exposure | 3 |
| Resource Exhaustion | 3 |
| Configuration Issues | 3 |
| Missing Security Controls | 4 |
| Code Quality | 3 |

---

## Immediate Actions Required

### Phase 1A: Additional Critical Fixes (2-3 hours)

1. ✅ Add ICAO station validation in aviation.py
2. ✅ Add buoy station validation in marine.py
3. ✅ Change Met Office to HTTPS
4. ✅ Add coordinate sanitization to all API calls

### Updated Remediation Timeline

| Phase | Original | Additional | New Total |
|-------|----------|------------|-----------|
| Phase 1 | 4-6h | 2-3h | 6-9h |
| Phase 2 | 4-6h | 2-3h | 6-9h |
| Phase 3 | 8-12h | 3-4h | 11-16h |
| Phase 4 | 6-8h | 2-3h | 8-11h |
| **TOTAL** | **22-32h** | **9-13h** | **31-45h** |

---

## Testing Checklist

Additional tests needed:

```python
# Test aviation station validation
def test_aviation_invalid_station():
    with pytest.raises(ValueError):
        get_metar("../../../etc/passwd")
    with pytest.raises(ValueError):
        get_metar("INVALID_STATION")

# Test marine station validation  
def test_marine_invalid_buoy():
    with pytest.raises(ValueError):
        get_buoy_observations("../../../../../config")

# Test coordinate sanitization
def test_coordinate_nan_inf():
    with pytest.raises(ValueError):
        sanitize_coordinate(float('nan'), 'lat')
    with pytest.raises(ValueError):
        sanitize_coordinate(float('inf'), 'lon')

# Test JSON size limits
def test_json_size_limit():
    huge_json = '{"a":' + '"x"*' * 1000000 + '}'
    with pytest.raises(ValueError):
        safe_json_parse(huge_json)
```

---

## Tools to Run

```bash
# Static analysis
bandit -r wx/ -ll -f html -o bandit-full-report.html
semgrep --config=p/security-audit wx/

# Dependency checking
safety check --full-report
pip-audit --desc

# SAST scanning
snyk test
horusec start -p .

# Fuzzing key inputs
python -m atheris wx.radar.get_radar_image
```

---

## Conclusion

This deep scan identified **19 additional vulnerabilities** beyond the initial 7, bringing the total to **26 findings**. Key new issues:

**Most Critical**:
1. ✅ Station ID injection in aviation module (SSRF)
2. ✅ Station ID injection in marine module (SSRF)
3. ✅ Insecure HTTP in Met Office API (credential leak)

**Total Effort**: Original 22-32 hours + 9-13 hours = **31-45 hours** for complete remediation.

The codebase security posture is **CRITICAL** with 4 critical vulnerabilities requiring immediate attention before any production deployment.

---

**End of Additional Findings Report**
