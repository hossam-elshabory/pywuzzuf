"""
Low-level HTTP transport core.

Single responsibility: execute HTTP requests with retry/back-off.
Knows nothing about jobs, companies, pagination, or filters.

Design decisions
----------------
* ``base_url`` and ``impersonate`` are constructor parameters — the client is
  trivially pointable at a mock server for testing.
* The ``impersonate`` string defaults to ``"chrome120"``; document that updating
  it is the first troubleshooting step for unexplained 403 errors.
* Repeated 403 responses (tracked via ``_consecutive_403s``) raise a
  ``BotDetectionError`` with an actionable message rather than a generic
  ``WuzzufAPIError``.
* All URL properties are derived from ``_base`` — a single place to change if
  the API introduces a versioned path prefix.
"""

from __future__ import annotations

import logging
from typing import Any, Literal, cast

import backoff
from curl_cffi.requests import AsyncSession, RequestsError

from .exceptions import BotDetectionError, RateLimitError

logger = logging.getLogger("pywuzzuf.http")

# Threshold of consecutive 403s before raising BotDetectionError.
_BOT_DETECTION_THRESHOLD = 3

DEFAULT_HEADERS: dict[str, str] = {
    "content-type": "application/json;charset=UTF-8",
}

HttpMethod = Literal["GET", "POST", "PUT", "DELETE", "OPTIONS", "HEAD", "PATCH"]


class HttpCore:
    """
    Low-level HTTP transport core based on ``curl_cffi``.

    Provides a resilient async HTTP client with built-in retry logic,
    exponential back-off, and browser impersonation to bypass basic
    bot detection.

    Parameters
    ----------
    base_url : str, optional
        The root URL of the Wuzzuf API. Defaults to "https://wuzzuf.net/api".
    impersonate : str, optional
        The browser fingerprint to impersonate. If the API returns
        unexpected 403 errors, updating this to a more recent Chrome version
        (e.g., "chrome124") is the recommended first step.
        Defaults to "chrome124".
    session : curl_cffi.requests.AsyncSession, optional
        An existing async session to use. If None, a new session is created.

    Attributes
    ----------
    search_url : str
        The endpoint for job searches.
    job_url : str
        The endpoint for individual job details.
    company_url : str
        The endpoint for company details.
    """

    def __init__(
        self,
        base_url: str = "https://wuzzuf.net/api",
        impersonate: str = "chrome124",
        session: AsyncSession | None = None,
    ) -> None:
        self._base = base_url.rstrip("/")
        self._impersonate = impersonate
        self._session = session or AsyncSession(impersonate=impersonate)
        self._consecutive_403s = 0

    @property
    def search_url(self) -> str:
        return f"{self._base}/search/job"

    @property
    def job_url(self) -> str:
        return f"{self._base}/job"

    @property
    def company_url(self) -> str:
        return f"{self._base}/company"

    async def close(self) -> None:
        """
        Close the underlying HTTP session.

        Safely handles cases where the session might already be closed or
        partially initialized, preventing common C-level cleanup errors in
        curl_cffi.
        """
        try:
            if hasattr(self._session, "acurl") and self._session.acurl is not None:
                await self._session.close()
            else:
                logger.debug("Session already closed or not properly initialized.")
        except TypeError as e:
            # Catch the specific error: "initializer for ctype 'void *'
            # must be a cdata pointer, not NoneType"
            # This occurs when curl_multi_cleanup is called on a None object.
            logger.warning(f"Ignored TypeError during session close (likely already closed): {e}")
        except Exception:
            logger.error("Unexpected error during session close", exc_info=True)
            raise

    @backoff.on_exception(
        backoff.expo,
        (RequestsError, RateLimitError),
        max_tries=5,
        jitter=backoff.full_jitter,
        logger=logger,
    )
    async def request(
        self,
        method: str,
        url: str,
        params: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> dict:
        """
        Execute an HTTP request with automatic retries and bot detection.

        Parameters
        ----------
        method : str
            HTTP method (e.g., "GET", "POST").
        url : str
            Target URL for the request.
        params : dict[str, Any], optional
            Query parameters to attach to the URL.
        **kwargs : Any
            Additional arguments passed to ``curl_cffi.requests.AsyncSession.request``.

        Returns
        -------
        dict
            The parsed JSON response body.

        Raises
        ------
        RateLimitError
            If the API returns HTTP 429 after all retries are exhausted.
        BotDetectionError
            If the API returns 3 consecutive HTTP 403 responses, suggesting
            browser fingerprint rejection.
        WuzzufAPIError
            For any other non-2xx response.
        RequestsError
            If a network-level error occurs.
        """
        if method.upper() == "POST":
            kwargs.setdefault("headers", DEFAULT_HEADERS)

        logger.debug("%s %s params=%s", method.upper(), url, params)

        response = await self._session.request(
            cast(HttpMethod, method.upper()), url, params=params, **kwargs
        )

        if response.status_code == 429:
            logger.warning("Rate limit hit on %s — will retry.", url)
            self._consecutive_403s = 0
            raise RateLimitError("Rate limit exceeded.", status_code=429)

        if response.status_code == 403:
            self._consecutive_403s += 1
            logger.warning("403 Forbidden on %s (%d consecutive).", url, self._consecutive_403s)
            if self._consecutive_403s >= _BOT_DETECTION_THRESHOLD:
                raise BotDetectionError(
                    f"Received {self._consecutive_403s} consecutive 403 responses. "
                    "Bot detection is likely active. "
                    f"Try updating the `impersonate` parameter "
                    f"(currently '{self._impersonate}') to a more recent Chrome "
                    "version string (e.g., 'chrome124').",
                    status_code=403,
                )
        else:
            self._consecutive_403s = 0

        response.raise_for_status()
        return response.json()

    async def get(self, url: str, params: dict[str, Any] | None = None, **kwargs: Any) -> dict:
        """
        Execute an HTTP GET request.

        Parameters
        ----------
        url : str
            Target URL.
        params : dict[str, Any], optional
            Query parameters.
        **kwargs : Any
            Additional request arguments.

        Returns
        -------
        dict
            Parsed JSON response.
        """
        return await self.request("GET", url, params=params, **kwargs)

    async def post(self, url: str, data: str | None = None, **kwargs: Any) -> dict:
        """
        Execute an HTTP POST request.

        Parameters
        ----------
        url : str
            Target URL.
        data : str, optional
            Raw request body.
        **kwargs : Any
            Additional request arguments.

        Returns
        -------
        dict
            Parsed JSON response.
        """
        return await self.request("POST", url, data=data, **kwargs)
