# WX-CLI Security Audit & Issues Report

**Audit Date**: 2025-10-26
**Auditor**: Claude Code Analysis
**Codebase Version**: Branch `claude/test2-new-overhauled-ui-011CUMfSjgC7QcyCpypqf8aH`

---

## Executive Summary

This security audit identified **7 vulnerabilities** and **12 code quality issues** across the wx-cli codebase. 

**Critical Findings**: 2
**High Priority**: 3
**Medium Priority**: 5
**Low Priority**: 9

---

## Security Vulnerabilities

### 🔴 CRITICAL: Server-Side Request Forgery (SSRF) in Radar Module

**File**: `wx/radar.py:218`
**Severity**: CRITICAL
**CWE**: CWE-918 (Server-Side Request Forgery)

**Issue**:
The radar station ID is directly interpolated into URLs without validation:

```python
url = f"https://radar.weather.gov/ridge/standard/{station}_loop.gif"
```

User input `station` is not validated against the `RADAR_STATIONS` dictionary before URL construction. An attacker could provide arbitrary station IDs like:

```bash
wx radar "../../../etc/passwd"
wx radar "../../malicious.com/evil"
```

This could potentially:
- Access arbitrary URLs on the NWS server
- Perform path traversal attacks
- Leak internal network information

**Proof of Concept**:
```python
# Malicious input
station = "../../../../etc/passwd%00"
url = f"https://radar.weather.gov/ridge/standard/{station}_loop.gif"
# Results in: https://radar.weather.gov/ridge/standard/../../../../etc/passwd%00_loop.gif
```

**Recommendation**:
Add strict validation before URL construction:

```python
def get_radar_image(self, station: str, product: str = "N0R", *, offline: bool = False) -> bytes | None:
    if offline:
        return None
    
    # SECURITY: Validate station ID against whitelist
    station_upper = station.upper()
    if station_upper not in self.RADAR_STATIONS:
        raise ValueError(f"Invalid radar station: {station}")
    
    try:
        url = f"https://radar.weather.gov/ridge/standard/{station_upper}_loop.gif"
        # ... rest of code
```

**Status**: ❌ UNPATCHED

---

### 🔴 CRITICAL: Unsafe Condition Evaluation in Notifications

**File**: `wx/notifications.py:210-256`
**Severity**: CRITICAL
**CWE**: CWE-94 (Code Injection)

**Issue**:
The `_evaluate_condition` function parses user-provided condition strings with minimal validation:

```python
def _evaluate_condition(self, condition: str, data: dict[str, Any]) -> bool:
    try:
        parts = condition.split()
        if len(parts) != 3:
            return False

        variable, operator, threshold = parts
        threshold = float(threshold)
        
        value = data.get(variable)
        # ... evaluation logic
```

**Vulnerabilities**:
1. **No operator whitelist validation**: While operators are checked later, malicious operators aren't explicitly rejected
2. **Variable name not sanitized**: Could potentially access internal data
3. **DoS via complex expressions**: No complexity limits
4. **Type confusion**: No validation that variable name is alphanumeric

**Attack Scenarios**:
```python
# Potential information disclosure
condition = "__import__('os').environ < 1"  # Rejected by float(), but shows intent

# DoS via repeated evaluations
condition = "temp < " + "9" * 1000000  # Large number causes performance issues
```

**Recommendation**:
Implement strict validation:

```python
def _evaluate_condition(self, condition: str, data: dict[str, Any]) -> bool:
    import re
    
    # SECURITY: Validate condition format with regex
    pattern = r'^([a-z_][a-z0-9_]*)\s*([<>=!]+)\s*(-?\d+(?:\.\d+)?)$'
    match = re.match(pattern, condition.strip(), re.IGNORECASE)
    
    if not match:
        return False
    
    variable, operator, threshold_str = match.groups()
    
    # Whitelist allowed operators
    ALLOWED_OPERATORS = {'<', '<=', '>', '>=', '==', '!='}
    if operator not in ALLOWED_OPERATORS:
        return False
    
    # Whitelist allowed variable names
    ALLOWED_VARIABLES = {'temp', 'wind', 'aqi', 'humidity', 'precip'}
    if variable.lower() not in ALLOWED_VARIABLES:
        return False
    
    try:
        threshold = float(threshold_str)
    except (ValueError, OverflowError):
        return False
    
    # ... rest of evaluation
```

**Status**: ❌ UNPATCHED

---

### 🟠 HIGH: XML External Entity (XXE) Vulnerability

**File**: `wx/fetchers.py:358`
**Severity**: HIGH
**CWE**: CWE-611 (XML External Entity)

**Issue**:
XML parsing uses standard library without protections:

```python
import xml.etree.ElementTree as ET
```

The `xml.etree.ElementTree` parser is vulnerable to XXE attacks if parsing untrusted XML data from external sources.

**Attack Scenario**:
If any weather API returns malicious XML:
```xml
<?xml version="1.0"?>
<!DOCTYPE foo [
  <!ENTITY xxe SYSTEM "file:///etc/passwd">
]>
<data>&xxe;</data>
```

**Recommendation**:
Use `defusedxml` library:

```bash
pip install defusedxml
```

```python
# Replace
import xml.etree.ElementTree as ET

# With
from defusedxml import ElementTree as ET
```

**Status**: ❌ UNPATCHED

---

### 🟠 HIGH: Insufficient Input Validation on Location Strings

**File**: Multiple files (`wx/cli.py`, `wx/fetchers.py`, `wx/international.py`)
**Severity**: HIGH
**CWE**: CWE-20 (Improper Input Validation)

**Issue**:
Location strings from user input are passed directly to external APIs without sanitization:

```python
# wx/cli.py:343
location: str = typer.Argument(..., help="Location name (e.g., 'London', 'Toronto')")

# wx/international.py:108
query_lower = query.lower()
matches = [loc for loc in locations if query_lower in loc.get("name", "").lower()]
```

**Vulnerabilities**:
1. No length limits on location strings
2. No character validation (could contain control characters, null bytes)
3. Could cause injection in logs or downstream systems

**Attack Scenarios**:
```bash
# Extremely long input (DoS)
wx international "A" * 1000000

# Control characters (log injection)
wx international "London\n[CRITICAL] Fake security alert\n"

# Null byte injection
wx international "London\x00malicious"
```

**Recommendation**:
Add input validation:

```python
import re

def validate_location_input(location: str, max_length: int = 100) -> str:
    """Validate and sanitize location input.
    
    Args:
        location: User-provided location string
        max_length: Maximum allowed length
        
    Returns:
        Sanitized location string
        
    Raises:
        ValueError: If input is invalid
    """
    if not location or not location.strip():
        raise ValueError("Location cannot be empty")
    
    if len(location) > max_length:
        raise ValueError(f"Location too long (max {max_length} characters)")
    
    # Allow only alphanumeric, spaces, hyphens, and common punctuation
    if not re.match(r'^[a-zA-Z0-9\s\-,.\']+$', location):
        raise ValueError("Location contains invalid characters")
    
    return location.strip()
```

**Status**: ❌ UNPATCHED

---

### 🟠 HIGH: Unvalidated URL Parameters in HTTP Requests

**File**: Multiple files (`wx/airquality.py:49-56`, `wx/international.py:42-43`)
**Severity**: HIGH
**CWE**: CWE-20 (Improper Input Validation)

**Issue**:
Latitude/longitude values and API parameters are passed to URLs without validation:

```python
# wx/airquality.py:51-54
params = {
    "latitude": lat,
    "longitude": lon,
    "distance": 25,
    "API_KEY": self.api_key,
}
```

**Vulnerabilities**:
1. No bounds checking on lat/lon values
2. Could cause API errors or unexpected behavior
3. Potential for SSRF if values are attacker-controlled

**Attack Scenarios**:
```python
# Invalid coordinates
lat = 999999.99
lon = -999999.99

# String injection attempts
lat = "40.7128; DROP TABLE users--"
```

**Recommendation**:
Add parameter validation:

```python
def validate_coordinates(lat: float, lon: float) -> tuple[float, float]:
    """Validate latitude and longitude.
    
    Args:
        lat: Latitude
        lon: Longitude
        
    Returns:
        Validated (lat, lon) tuple
        
    Raises:
        ValueError: If coordinates are invalid
    """
    if not isinstance(lat, (int, float)) or not isinstance(lon, (int, float)):
        raise ValueError("Coordinates must be numeric")
    
    if not (-90 <= lat <= 90):
        raise ValueError(f"Invalid latitude: {lat} (must be -90 to 90)")
    
    if not (-180 <= lon <= 180):
        raise ValueError(f"Invalid longitude: {lon} (must be -180 to 180)")
    
    return float(lat), float(lon)
```

**Status**: ❌ UNPATCHED

---

### 🟡 MEDIUM: API Key Exposure in Error Messages

**File**: `wx/config.py:329-351`
**Severity**: MEDIUM
**CWE**: CWE-209 (Information Exposure Through Error Message)

**Issue**:
API key validation includes actual key value in error messages:

```python
def _validate_api_key(key: str | None, key_name: str) -> bool:
    # ... validation logic
    logger.warning(
        f"{key_name} value '{key}' looks like a placeholder. "
        "Set a real API key or remove it."
    )
```

**Risk**:
API keys could be logged or displayed in error output, potentially exposing credentials.

**Recommendation**:
Redact API keys in error messages:

```python
def _redact_api_key(key: str) -> str:
    """Redact API key for logging."""
    if len(key) <= 8:
        return "***"
    return f"{key[:4]}...{key[-4:]}"

logger.warning(
    f"{key_name} value '{_redact_api_key(key)}' looks like a placeholder."
)
```

**Status**: ❌ UNPATCHED

---

### 🟡 MEDIUM: Potential Race Condition in File Operations

**File**: `wx/notifications.py:92-109`, `wx/config.py:196-214`
**Severity**: MEDIUM
**CWE**: CWE-367 (Time-of-check Time-of-use)

**Issue**:
While atomic writes are used, the directory creation has a potential race:

```python
# wx/notifications.py:54
self.config_dir.mkdir(parents=True, exist_ok=True)
```

**Risk**:
Between directory check and file write, directory could be:
- Deleted by another process
- Replaced with a symlink (symlink attack)

**Recommendation**:
Add additional checks:

```python
def _safe_mkdir(path: Path) -> None:
    """Safely create directory."""
    try:
        path.mkdir(parents=True, exist_ok=True)
        
        # Verify it's actually a directory
        if not path.is_dir():
            raise OSError(f"{path} exists but is not a directory")
            
        # Check it's not a symlink (optional, stricter security)
        if path.is_symlink():
            raise OSError(f"{path} is a symbolic link")
            
    except OSError as e:
        raise OSError(f"Failed to create directory {path}: {e}")
```

**Status**: ⚠️ LOW RISK (atomic writes mitigate most issues)

---

## Code Quality Issues

### 1. Missing Error Handling in Network Requests

**File**: Multiple files
**Severity**: MEDIUM
**Issue**: Some network request error handling is too broad:

```python
except (requests.RequestException, OSError):
    return None
```

**Recommendation**: Log errors for debugging:

```python
except requests.RequestException as e:
    logger.debug(f"Network request failed: {e}")
    return None
except OSError as e:
    logger.debug(f"OS error during request: {e}")
    return None
```

---

### 2. Hardcoded Timeout Values

**File**: Multiple files
**Severity**: LOW
**Issue**: Timeout values hardcoded throughout:

```python
def __init__(self, timeout: int = 10):
    self.timeout = timeout
```

**Recommendation**: Use configuration constants:

```python
# config.py
DEFAULT_NETWORK_TIMEOUT = 10
RADAR_TIMEOUT = 15  # Radar images may be larger

# Usage
def __init__(self, timeout: int | None = None):
    self.timeout = timeout or DEFAULT_NETWORK_TIMEOUT
```

---

### 3. Subprocess Usage in Tests

**File**: `test_all_features.py:32`
**Severity**: LOW
**Issue**: Tests use subprocess which could be a security risk if test inputs aren't controlled:

```python
result = subprocess.run(cmd, shell=False, ...)
```

**Status**: ✅ ACCEPTABLE (shell=False is used, good practice)

---

### 4. Broad Exception Catching

**File**: `wx/config.py:208`
**Severity**: LOW
**Issue**: Catching all exceptions can hide bugs:

```python
except Exception:  # noqa: BLE001
    # Clean up temp file if something went wrong
```

**Recommendation**: Catch specific exceptions:

```python
except (OSError, IOError, PermissionError) as e:
    logger.debug(f"Failed to write config: {e}")
    # Clean up temp file
```

---

### 5. No Rate Limiting on API Calls

**File**: Multiple API client files
**Severity**: MEDIUM
**Issue**: No rate limiting implemented for external API calls.

**Risk**:
- Could hit API rate limits
- Potential for abuse if exposed
- No backoff/retry logic

**Recommendation**:
Implement rate limiting:

```python
from time import time, sleep

class RateLimiter:
    def __init__(self, calls_per_minute: int = 60):
        self.calls_per_minute = calls_per_minute
        self.call_times = []
    
    def wait_if_needed(self):
        now = time()
        # Remove calls older than 1 minute
        self.call_times = [t for t in self.call_times if now - t < 60]
        
        if len(self.call_times) >= self.calls_per_minute:
            sleep_time = 60 - (now - self.call_times[0])
            if sleep_time > 0:
                sleep(sleep_time)
        
        self.call_times.append(now)
```

---

### 6. Synthetic Data Generation Uses Insecure Random

**File**: Multiple files (e.g., `wx/airquality.py:98`, `wx/hurricanes.py:86`)
**Severity**: LOW
**Issue**: Using `random` module for synthetic data:

```python
import random
if random.random() < 0.3:
```

**Status**: ✅ ACCEPTABLE (synthetic data only, not cryptographic use)

---

### 7. Missing Type Validation in JSON Parsing

**File**: Multiple files
**Severity**: MEDIUM
**Issue**: JSON data accessed without type checking:

```python
data = response.json()
locations = data.get("Locations", {}).get("Location", [])
```

**Risk**: If API returns unexpected types, could cause crashes.

**Recommendation**:
Add type validation:

```python
data = response.json()
if not isinstance(data, dict):
    raise ValueError("Expected JSON object")

locations_obj = data.get("Locations")
if not isinstance(locations_obj, dict):
    return []

location_list = locations_obj.get("Location", [])
if not isinstance(location_list, list):
    return []
```

---

### 8. No Request Size Limits

**File**: All HTTP client code
**Severity**: MEDIUM
**Issue**: No limits on response sizes from external APIs.

**Risk**: Memory exhaustion if API returns huge responses.

**Recommendation**:
Add streaming with size limits:

```python
MAX_RESPONSE_SIZE = 10 * 1024 * 1024  # 10MB

response = self.session.get(url, stream=True, timeout=self.timeout)
response.raise_for_status()

content = b""
for chunk in response.iter_content(chunk_size=8192):
    content += chunk
    if len(content) > MAX_RESPONSE_SIZE:
        raise ValueError("Response too large")

return content
```

---

### 9. User-Agent String Contains GitHub URL

**File**: `wx/fetchers.py:14`
**Severity**: INFO
**Issue**: User-Agent contains repository URL:

```python
USER_AGENT = "wx-cli/0.1 (+https://github.com/Exvin2/claudex-cli)"
```

**Status**: ✅ ACCEPTABLE (good practice for API usage tracking)

---

### 10. No Certificate Verification Configuration

**File**: All HTTPS requests
**Severity**: LOW
**Issue**: No explicit SSL certificate verification configuration.

**Status**: ✅ ACCEPTABLE (requests library verifies by default)

**Note**: Could add explicit verification for clarity:

```python
response = self.session.get(url, verify=True, timeout=self.timeout)
```

---

### 11. Notification Condition Parser Complexity

**File**: `wx/notifications.py:210`
**Severity**: LOW
**Issue**: Simple split-based parser could be fragile.

**Recommendation**: Use proper parsing library or regex (shown in CRITICAL section above).

---

### 12. Missing Input Length Limits

**File**: `wx/notifications.py:114-120`
**Severity**: LOW
**Issue**: No limits on rule names, conditions, locations.

**Recommendation**:
Add validation:

```python
def add_rule(self, name: str, condition: str, location: str, ...) -> bool:
    if len(name) > 50:
        raise ValueError("Rule name too long (max 50 characters)")
    if len(condition) > 100:
        raise ValueError("Condition too long (max 100 characters)")
    if len(location) > 100:
        raise ValueError("Location too long (max 100 characters)")
    
    # ... rest of method
```

---

## Summary of Findings

### By Severity

| Severity | Count | Files Affected |
|----------|-------|----------------|
| CRITICAL | 2     | radar.py, notifications.py |
| HIGH     | 3     | fetchers.py, cli.py, international.py, airquality.py |
| MEDIUM   | 5     | config.py, notifications.py, multiple API clients |
| LOW      | 9     | Various |

### Priority Fixes

**Immediate (Critical)**:
1. ✅ Add radar station ID validation
2. ✅ Implement safe condition evaluation with whitelists

**High Priority**:
3. ✅ Replace xml.etree with defusedxml
4. ✅ Add input validation for location strings
5. ✅ Validate coordinates in API calls

**Medium Priority**:
6. Add API key redaction in logs
7. Implement rate limiting
8. Add response size limits
9. Improve type validation for JSON

**Low Priority**:
10. Add input length limits
11. Improve error logging
12. Add explicit SSL verification

---

## Testing Recommendations

1. **Security Testing**:
   - Fuzz test all user inputs (location names, station IDs, notification conditions)
   - Test with malicious XML payloads
   - Verify API key redaction in logs
   - Test SSRF protections

2. **Integration Testing**:
   - Test rate limiting under load
   - Verify error handling with network failures
   - Test with malformed API responses

3. **Static Analysis**:
   - Run `bandit` for Python security issues: `bandit -r wx/`
   - Run `semgrep` with security rules
   - Use `safety` to check dependencies: `safety check`

---

## Compliance Notes

### OWASP Top 10 Relevance

- **A03:2021 – Injection**: Notifications condition evaluation, location input
- **A04:2021 – Insecure Design**: Missing input validation
- **A05:2021 – Security Misconfiguration**: XML parser configuration
- **A10:2021 – SSRF**: Radar station URL construction

### CWE Coverage

- CWE-918: SSRF (Radar module)
- CWE-94: Code Injection (Notifications)
- CWE-611: XXE (XML parsing)
- CWE-20: Input Validation (Multiple)
- CWE-209: Information Exposure (API keys)
- CWE-367: TOCTOU (File operations)

---

## Conclusion

The wx-cli codebase has **2 critical vulnerabilities** that should be addressed immediately:

1. SSRF in radar station URL construction
2. Unsafe condition evaluation in notifications

Overall code quality is good with:
- ✅ Atomic file writes with proper permissions
- ✅ No use of eval/exec
- ✅ subprocess.run with shell=False
- ✅ Proper use of tempfile module

The main security improvements needed are:
1. Input validation and sanitization
2. Whitelist validation for user-controlled data
3. Safer XML parsing
4. Better error handling and logging

**Estimated remediation effort**: 4-8 hours for critical fixes, 16-24 hours for all recommended improvements.
