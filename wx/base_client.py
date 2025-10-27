"""Base API client with common functionality.

This module provides a base class for all API clients with built-in
features like rate limiting, response size limits, error handling,
and logging.
"""

from __future__ import annotations

import requests
from typing import Any, Optional

from .constants import (
    DEFAULT_NETWORK_TIMEOUT,
    MAX_RESPONSE_SIZE,
    MAX_JSON_RESPONSE_SIZE,
    STREAM_CHUNK_SIZE,
    MAX_RETRIES,
    RETRY_BACKOFF_FACTOR,
    INITIAL_RETRY_DELAY,
    USER_AGENT,
)
from .logging_config import get_logger
from .rate_limiter import get_rate_limiter, RateLimiter
from .security import ValidationError, validate_json_dict


class APIError(Exception):
    """Base exception for API client errors."""
    pass


class ResponseTooLargeError(APIError):
    """Raised when API response exceeds size limit."""
    pass


class BaseAPIClient:
    """Base class for API clients.

    Provides common functionality:
    - HTTP session management with connection pooling
    - Rate limiting per endpoint
    - Response size limits for memory safety
    - Automatic retries with exponential backoff
    - Consistent error handling and logging
    - Offline mode support

    Subclasses should implement:
    - API-specific methods
    - Synthetic data generation for offline mode
    """

    def __init__(
        self,
        timeout: int = DEFAULT_NETWORK_TIMEOUT,
        user_agent: Optional[str] = None,
        rate_limiter_name: Optional[str] = None,
        max_response_size: int = MAX_RESPONSE_SIZE,
    ):
        """Initialize API client.

        Args:
            timeout: Request timeout in seconds
            user_agent: Custom User-Agent string (default: global USER_AGENT)
            rate_limiter_name: Name for rate limiter (default: class name)
            max_response_size: Maximum response size in bytes
        """
        self.timeout = timeout
        self.max_response_size = max_response_size
        self.session = requests.Session()

        # Set user agent
        self.session.headers.update({
            "User-Agent": user_agent or USER_AGENT
        })

        # Get rate limiter for this client
        limiter_name = rate_limiter_name or self.__class__.__name__
        self.rate_limiter: RateLimiter = get_rate_limiter(limiter_name)

        # Setup logging
        self.logger = get_logger(f"wx.{self.__class__.__name__}")

    def _get_with_size_limit(
        self,
        url: str,
        params: Optional[dict[str, Any]] = None,
        max_size: Optional[int] = None,
    ) -> bytes:
        """GET request with response size limit.

        Args:
            url: URL to fetch
            params: Query parameters
            max_size: Maximum response size (uses instance default if None)

        Returns:
            Response content as bytes

        Raises:
            ResponseTooLargeError: If response exceeds size limit
            requests.RequestException: On network errors
        """
        max_size = max_size or self.max_response_size

        # Apply rate limiting
        self.rate_limiter.wait_if_needed()

        # Stream response to check size
        response = self.session.get(
            url,
            params=params,
            timeout=self.timeout,
            stream=True,
            verify=True,  # Explicit SSL verification
        )
        response.raise_for_status()

        # Read response in chunks, checking size
        content = b""
        for chunk in response.iter_content(chunk_size=STREAM_CHUNK_SIZE):
            content += chunk
            if len(content) > max_size:
                response.close()
                raise ResponseTooLargeError(
                    f"Response exceeds size limit of {max_size} bytes"
                )

        return content

    def _get_json(
        self,
        url: str,
        params: Optional[dict[str, Any]] = None,
        *,
        offline: bool = False,
        validate_dict: bool = True,
    ) -> dict[str, Any] | list[Any] | None:
        """Safe JSON GET request with size limits and validation.

        Args:
            url: URL to fetch
            params: Query parameters
            offline: If True, return None immediately
            validate_dict: If True, validate response is a dict

        Returns:
            JSON response data or None on error

        Raises:
            ValidationError: If validate_dict=True and response is not a dict
        """
        if offline:
            self.logger.debug("Offline mode: skipping request")
            return None

        try:
            # Fetch with size limit
            content = self._get_with_size_limit(
                url,
                params=params,
                max_size=MAX_JSON_RESPONSE_SIZE
            )

            # Parse JSON
            import json
            data = json.loads(content)

            # Validate if requested
            if validate_dict and data is not None:
                if not isinstance(data, dict):
                    raise ValidationError(
                        f"Expected JSON object, got {type(data).__name__}"
                    )

            self.logger.debug(f"Successfully fetched JSON from {url}")
            return data

        except ResponseTooLargeError:
            self.logger.warning(f"Response too large from {url}")
            return None
        except requests.Timeout:
            self.logger.debug(f"Request timeout: {url}")
            return None
        except requests.RequestException as e:
            self.logger.debug(f"Request failed: {url} - {e}")
            return None
        except (ValueError, json.JSONDecodeError) as e:
            self.logger.warning(f"Invalid JSON from {url}: {e}")
            return None
        except ValidationError:
            self.logger.warning(f"JSON validation failed for {url}")
            raise

    def _get_bytes(
        self,
        url: str,
        params: Optional[dict[str, Any]] = None,
        *,
        offline: bool = False,
        max_size: Optional[int] = None,
    ) -> bytes | None:
        """GET request returning raw bytes.

        Args:
            url: URL to fetch
            params: Query parameters
            offline: If True, return None immediately
            max_size: Maximum response size (uses instance default if None)

        Returns:
            Response content as bytes or None on error
        """
        if offline:
            self.logger.debug("Offline mode: skipping request")
            return None

        try:
            content = self._get_with_size_limit(url, params, max_size)
            self.logger.debug(f"Successfully fetched {len(content)} bytes from {url}")
            return content

        except ResponseTooLargeError as e:
            self.logger.warning(f"Response too large from {url}: {e}")
            return None
        except requests.Timeout:
            self.logger.debug(f"Request timeout: {url}")
            return None
        except requests.RequestException as e:
            self.logger.debug(f"Request failed: {url} - {e}")
            return None

    def _post_json(
        self,
        url: str,
        data: Optional[dict[str, Any]] = None,
        json_data: Optional[dict[str, Any]] = None,
        *,
        offline: bool = False,
    ) -> dict[str, Any] | None:
        """Safe JSON POST request.

        Args:
            url: URL to post to
            data: Form data
            json_data: JSON data
            offline: If True, return None immediately

        Returns:
            JSON response data or None on error
        """
        if offline:
            self.logger.debug("Offline mode: skipping request")
            return None

        try:
            # Apply rate limiting
            self.rate_limiter.wait_if_needed()

            response = self.session.post(
                url,
                data=data,
                json=json_data,
                timeout=self.timeout,
                verify=True,
            )
            response.raise_for_status()

            # Check response size
            if len(response.content) > MAX_JSON_RESPONSE_SIZE:
                raise ResponseTooLargeError(
                    f"Response exceeds size limit of {MAX_JSON_RESPONSE_SIZE} bytes"
                )

            return response.json()

        except ResponseTooLargeError:
            self.logger.warning(f"Response too large from {url}")
            return None
        except requests.Timeout:
            self.logger.debug(f"Request timeout: {url}")
            return None
        except requests.RequestException as e:
            self.logger.debug(f"Request failed: {url} - {e}")
            return None
        except ValueError as e:
            self.logger.warning(f"Invalid JSON from {url}: {e}")
            return None

    def close(self) -> None:
        """Close the HTTP session."""
        self.session.close()
        self.logger.debug("HTTP session closed")

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()
