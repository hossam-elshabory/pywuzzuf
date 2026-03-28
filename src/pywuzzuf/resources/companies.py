"""
Companies resource — fetches company details by ID.

This module provides the `CompaniesResource` class for interacting with Wuzzuf
company endpoints.
"""

from __future__ import annotations

import logging
from typing import Iterable

from pydantic import ValidationError

from .._http import HttpCore
from ..exceptions import InvalidResponseError, WuzzufAPIError
from ..models import Company, CompanyDetailsResponse

logger = logging.getLogger("pywuzzuf.resources.companies")

# Maximum IDs per single GET request
_COMPANY_BATCH_SIZE = 20


def _chunked(ids: list[str], size: int) -> Iterable[list[str]]:
    """Yield successive fixed-size chunks from a list."""
    for i in range(0, len(ids), size):
        yield ids[i : i + size]


class CompaniesResource:
    """
    Provides company lookup functionality.

    This resource handles fetching and caching (at the request level) of
    company metadata to enrich job listings.
    """

    def __init__(self, http: HttpCore) -> None:
        """Initialize the companies resource."""
        self._http = http

    async def fetch_by_ids(self, company_ids: list[str]) -> dict[str, Company]:
        """
        Fetch company details for a list of IDs.

        Deduplicates the input, batches requests into chunks, and returns a
        mapping of company IDs to their full models.

        Parameters
        ----------
        company_ids : list[str]
            Raw company IDs (may contain duplicates).

        Returns
        -------
        dict[str, Company]
            Mapping from company ID to ``Company`` model. IDs not found in
            the API response are absent from the map.

        Raises
        ------
        InvalidResponseError
            If the API response fails validation.
        WuzzufAPIError
            If the API returns an error response.
        """
        if not company_ids:
            return {}

        unique_ids = list(dict.fromkeys(company_ids))
        company_map: dict[str, Company] = {}

        for chunk in _chunked(unique_ids, _COMPANY_BATCH_SIZE):
            params = {"filter[id]": ",".join(chunk)}
            try:
                raw = await self._http.get(self._http.company_url, params=params)
                response = CompanyDetailsResponse.model_validate(raw)
                for company in response.data:
                    company_map[company.id] = company
            except ValidationError as exc:
                logger.debug("Company details response validation failed", exc_info=True)
                raise InvalidResponseError(
                    "Failed to validate company details response.",
                    validation_error=exc,
                ) from exc
            except WuzzufAPIError:
                raise
            except Exception as exc:
                logger.error("Unexpected error fetching company details", exc_info=True)
                raise WuzzufAPIError(f"Unexpected error fetching company details: {exc}") from exc

        logger.debug("Fetched %d / %d requested companies.", len(company_map), len(unique_ids))
        return company_map
