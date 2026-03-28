"""
PyWuzzuf — Production-grade Python client for the Wuzzuf Jobs API.

This package provides a robust, async-first interface to the Wuzzuf API,
featuring built-in browser impersonation, resilient pagination, and
comprehensive data quality reporting.

Quick start
-----------

Async (recommended)::

    import asyncio
    from pywuzzuf import WuzzufClient, SearchFilters, DateRange

    async def main():
        async with WuzzufClient() as client:
            # Build and execute a filtered search
            result = await (
                client.jobs
                    .search("Python Developer")
                    .filter(SearchFilters(posted_within=DateRange.LAST_WEEK))
                    .limit(50)
                    .all()
            )

            for job in result.items:
                print(f"{job.attributes.title} at {job.company.attributes.name}")

    asyncio.run(main())

Synchronous (notebooks/scripts)::

    from pywuzzuf import SyncWuzzufClient

    with SyncWuzzufClient() as client:
        result = client.jobs.search("Data Scientist").limit(10).all()
        for job in result.items:
            print(job.attributes.title)

Key Improvements in v3
----------------------
* **Resilient Pagination**: Error callbacks can now return ``CONTINUE`` to skip
  failing pages instead of stopping iteration.
* **Accurate Status Tracking**: ``terminated_early`` now correctly captures all
  stop reasons, including manual signals from callbacks.
* **Type Safety**: Fixed a critical ``TypeError`` when comparing mixed
  tz-aware/tz-naive datetimes in filters.
* **Enhanced Diagnostics**: Improved ``DataQualityReport`` to reduce false
  positives on optional fields like ``requirements``.
* **API Compatibility**: Standardized outbound date formats to match Wuzzuf's
  native ``MM/DD/YYYY HH:MM:SS`` requirement.

Public Surface
--------------

Clients
~~~~~~~
* ``WuzzufClient``: Asynchronous context manager (primary entry point).
* ``SyncWuzzufClient``: Synchronous wrapper with persistent event loop.

Filtering
~~~~~~~~~
* ``SearchFilters``: Immutable container for keywords and metadata.
* ``DateRange``: Enum for relative time windows (e.g., ``LAST_WEEK``).
* ``AbsoluteDateFilter``: Precise datetime boundaries.

Pagination
~~~~~~~~~~
* ``PaginationConfig``: Controls caps, page size, and callbacks.
* ``PaginationResult``: Aggregated items with exhaustive metadata.
* ``PaginationSignal``: Flow control (STOP/CONTINUE/RETRY) for callbacks.

Models
~~~~~~
* ``EnrichedJob``: The core job object with company data and quality reports.
* ``DataQualityReport``: Detailed anomaly analysis for API responses.

Exceptions
~~~~~~~~~~
* ``WuzzufAPIError``: Base exception for all client errors.
* ``BotDetectionError``: Raised when fingerprint-based rejection is suspected.
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# Package version
# ---------------------------------------------------------------------------
# Dynamically retrieve the version from installed package metadata.
# This ensures pyproject.toml is the single source of truth.
# Falls back to "0.0.0" if the package is not installed (e.g., running from source).
# ---------------------------------------------------------------------------
try:
    from importlib.metadata import PackageNotFoundError, version

    __version__ = version("pywuzzuf")
except PackageNotFoundError:
    # Fallback for local development or if running from source without installation
    __version__ = "0.0.0+local"

from .client import SyncWuzzufClient, WuzzufClient
from .exceptions import (
    BotDetectionError,
    InvalidResponseError,
    RateLimitError,
    WuzzufAPIError,
)
from .filters import AbsoluteDateFilter, DateRange, SearchFilters
from .models import (
    Company,
    CompanyAttributes,
    DataQualityReport,
    EnrichedJob,
    JobAttributes,
    JobDetails,
    Location,
    NamedAttribute,
    Salary,
)
from .pagination import (
    AsyncPaginator,
    PaginationConfig,
    PaginationResult,
    PaginationSignal,
)

__all__ = [
    # Package metadata
    "__version__",
    # Clients
    "WuzzufClient",
    "SyncWuzzufClient",
    # Filtering
    "SearchFilters",
    "DateRange",
    "AbsoluteDateFilter",
    # Pagination
    "PaginationConfig",
    "PaginationResult",
    "PaginationSignal",
    "AsyncPaginator",
    # Models
    "EnrichedJob",
    "JobDetails",
    "JobAttributes",
    "Company",
    "CompanyAttributes",
    "Salary",
    "Location",
    "NamedAttribute",
    "DataQualityReport",
    # Exceptions
    "WuzzufAPIError",
    "RateLimitError",
    "InvalidResponseError",
    "BotDetectionError",
]
