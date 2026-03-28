"""
Jobs resource and fluent query builder.

This module provides the `JobsResource` class for interacting with Wuzzuf job
endpoints and the `JobQuery` builder for constructing and executing searches.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field, replace
from typing import Awaitable, Callable, Iterable, Optional

from pydantic import ValidationError

from .._http import HttpCore
from ..exceptions import InvalidResponseError, WuzzufAPIError
from ..filters import SearchFilters
from ..models import (
    EnrichedJob,
    JobDetails,
    JobDetailsResponse,
    SearchFilterPayload,
    SearchPayload,
    SearchResponse,
)
from ..pagination import (
    AsyncPaginator,
    FetchBatch,
    PaginationConfig,
    PaginationResult,
    PaginationSignal,
    ProgressCallback,
)
from .companies import CompaniesResource

logger = logging.getLogger("pywuzzuf.resources.jobs")

# Maximum job IDs per single details request
_JOB_BATCH_SIZE = 20


def _chunked(ids: list[str], size: int) -> Iterable[list[str]]:
    """Yield successive fixed-size chunks from a list."""
    for i in range(0, len(ids), size):
        yield ids[i : i + size]


def _job_matches_filters(job: JobDetails, filters: SearchFilters) -> bool:
    """Evaluate job metadata against search filters in-memory."""
    attrs = job.attributes

    if filters.posted_since:
        if not attrs.posted_at or attrs.posted_at < filters.posted_since:
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug(
                    "Job %s rejected: posted_at %s < posted_since %s",
                    job.id,
                    attrs.posted_at,
                    filters.posted_since,
                )
            return False
    if filters.posted_until:
        if not attrs.posted_at or attrs.posted_at > filters.posted_until:
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug(
                    "Job %s rejected: posted_at %s > posted_until %s",
                    job.id,
                    attrs.posted_at,
                    filters.posted_until,
                )
            return False
    if filters.expires_since:
        if not attrs.expire_at or attrs.expire_at < filters.expires_since:
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug(
                    "Job %s rejected: expire_at %s < expires_since %s",
                    job.id,
                    attrs.expire_at,
                    filters.expires_since,
                )
            return False

    if filters.country_id is not None:
        if attrs.location.country.id != filters.country_id:
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug(
                    "Job %s rejected: country_id %s != %s",
                    job.id,
                    attrs.location.country.id,
                    filters.country_id,
                )
            return False
    if filters.city_id is not None:
        if not attrs.location.city or attrs.location.city.id != filters.city_id:
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug("Job %s rejected: city_id mismatch", job.id)
            return False
    if filters.career_level_id is not None:
        if not attrs.career_level or attrs.career_level.id != filters.career_level_id:
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug("Job %s rejected: career_level_id mismatch", job.id)
            return False

    if filters.keywords:
        job_kw_names = [k.name.lower() for k in attrs.keywords]
        search_corpus = " ".join([attrs.title, attrs.description] + job_kw_names).lower()
        for kw in filters.keywords:
            if not re.search(rf"\b{re.escape(kw.lower())}\b", search_corpus):
                if logger.isEnabledFor(logging.DEBUG):
                    logger.debug("Job %s rejected: keyword %r not found", job.id, kw)
                return False

    return True


@dataclass(frozen=True)
class JobQuery:
    """
    Immutable query builder for job searches.

    Provides a fluent interface for configuring search parameters and
    executing the search. Every modifier method returns a new instance.

    Attributes
    ----------
    _resource : JobsResource
        The parent resource used to execute requests.
    _query : str
        The search keywords.
    _filters : SearchFilters
        The filters applied to the search.
    _config : PaginationConfig
        Configuration for pagination and result limits.
    """

    _resource: "JobsResource" = field(repr=False)
    _query: str = field(repr=False)
    _filters: SearchFilters = field(default_factory=SearchFilters, repr=False)
    _config: PaginationConfig = field(default_factory=PaginationConfig, repr=False)

    def __repr__(self) -> str:
        return f"JobQuery(query={self._query!r}, filters={self._filters!r}, config={self._config!r})"

    def filter(self, filters: SearchFilters) -> "JobQuery":
        """
        Apply search filters.

        Parameters
        ----------
        filters : SearchFilters
            The filters to apply (date ranges, location, career level, keywords).

        Returns
        -------
        JobQuery
            A new query instance with the applied filters.
        """
        return replace(self, _filters=filters)

    def page_size(self, n: int) -> "JobQuery":
        """
        Set the number of results to fetch per page.

        Parameters
        ----------
        n : int
            Number of results per page (max 50).

        Returns
        -------
        JobQuery
            A new query instance with the updated page size.
        """
        return replace(self, _config=replace(self._config, page_size=n))

    def limit(self, n: int) -> "JobQuery":
        """
        Set a maximum number of total results to return.

        Parameters
        ----------
        n : int
            Maximum number of jobs to fetch.

        Returns
        -------
        JobQuery
            A new query instance with the limit applied.
        """
        return replace(self, _config=replace(self._config, max_results=n))

    def max_pages(self, n: int) -> "JobQuery":
        """
        Set a maximum number of pages to fetch.

        Parameters
        ----------
        n : int
            Maximum number of pages to request.

        Returns
        -------
        JobQuery
            A new query instance with the page limit applied.
        """
        return replace(self, _config=replace(self._config, max_pages=n))

    def on_progress(self, cb: ProgressCallback) -> "JobQuery":
        """
        Register a callback for pagination progress.

        Parameters
        ----------
        cb : ProgressCallback
            A function called with ``(total_fetched, page_number)`` after each page.

        Returns
        -------
        JobQuery
            A new query instance with the progress callback.
        """
        return replace(self, _config=replace(self._config, on_progress=cb))

    def on_error(self, cb: Callable[[Exception, int, int], Optional[PaginationSignal]]) -> "JobQuery":
        """
        Register a callback for errors during pagination.

        Parameters
        ----------
        cb : Callable
            A function called if an error occurs while fetching a page.

        Returns
        -------
        JobQuery
            A new query instance with the error callback.
        """
        return replace(self, _config=replace(self._config, on_error=cb))

    def paginate(self) -> AsyncPaginator[EnrichedJob]:
        """
        Return an async iterator for lazy result streaming.

        Returns
        -------
        AsyncPaginator[EnrichedJob]
            An object that can be iterated using ``async for``.
        """
        return AsyncPaginator(
            fetch_page=self._resource._make_fetch_page(self._query, self._filters),
            config=self._config,
        )

    async def all(self) -> PaginationResult[EnrichedJob]:
        """
        Collect all matching results eagerly.

        Returns
        -------
        PaginationResult[EnrichedJob]
            The paginated result containing all found jobs.

        Raises
        ------
        WuzzufAPIError
            If the API returns an error response.
        """
        return await self.paginate().collect()

    async def first(self) -> EnrichedJob | None:
        """
        Return the first matching result.

        Returns
        -------
        EnrichedJob, optional
            The first job matching the query, or None if no results were found.
        """
        async for job in self.paginate():
            return job
        return None


class JobsResource:
    """
    High-level interface for job-related API operations.

    Handles searching for jobs and enriching them with company metadata.
    """

    def __init__(self, http: HttpCore, companies: CompaniesResource) -> None:
        """Initialize the jobs resource."""
        self._http = http
        self._companies = companies

    def search(self, query: str) -> JobQuery:
        """
        Begin building a job search query.

        Parameters
        ----------
        query : str
            The search keywords (e.g., "Python Developer").

        Returns
        -------
        JobQuery
            A builder object to further refine and execute the search.
        """
        return JobQuery(_resource=self, _query=query)

    def _make_fetch_page(
        self, query: str, filters: SearchFilters
    ) -> Callable[[int, int], Awaitable[FetchBatch[EnrichedJob]]]:
        """Create a closure for fetching a single page of results."""

        async def _fetcher(start: int, page_size: int) -> FetchBatch[EnrichedJob]:
            job_ids = await self._search_jobs(query, filters, start, page_size)
            if not job_ids:
                return FetchBatch(items=[], raw_count=0, has_more=False)

            job_details_list = await self._fetch_job_details(job_ids) or []

            passing_details = []

            for job in job_details_list:
                if _job_matches_filters(job, filters):
                    passing_details.append(job)

            company_ids = [
                job.relationships.company.data.id
                for job in passing_details
                if job.relationships.company.data is not None
            ]

            company_map = await self._companies.fetch_by_ids(company_ids)

            enriched: list[EnrichedJob] = []
            for job in passing_details:
                company = None
                if job.relationships.company.data is not None:
                    company = company_map.get(job.relationships.company.data.id)

                enriched.append(
                    EnrichedJob.model_validate(
                        {
                            **job.model_dump(mode="python"),
                            "company": company,
                        }
                    )
                )

            return FetchBatch(
                items=enriched,
                raw_count=len(job_ids),
                has_more=len(job_ids) == page_size,
            )

        return _fetcher

    async def _search_jobs(
        self,
        query: str,
        filters: SearchFilters,
        start: int,
        page_size: int,
    ) -> list[str]:
        """POST to the search endpoint and return a list of job IDs."""
        filter_payload = _build_filter_payload(filters)

        payload = SearchPayload(
            query=query,
            start_index=start,
            page_size=page_size,
            search_filters=filter_payload,
        )

        try:
            raw = await self._http.post(
                self._http.search_url,
                data=payload.model_dump_json(by_alias=True),
            )
            response = SearchResponse.model_validate(raw)
            ids = [item.id for item in response.data]
            logger.debug(
                "Search %r start=%d page_size=%d → %d IDs",
                query,
                start,
                page_size,
                len(ids),
            )
            return ids
        except ValidationError as exc:
            logger.debug("Search response validation failed", exc_info=True)
            raise InvalidResponseError(
                "Failed to validate search response.", validation_error=exc
            ) from exc
        except WuzzufAPIError:
            raise
        except Exception as exc:
            logger.error("Unexpected error during job search", exc_info=True)
            raise WuzzufAPIError(f"Unexpected error during job search: {exc}") from exc

    async def _fetch_job_details(self, job_ids: list[str]) -> list[JobDetails]:
        """Fetch JobDetails for a list of IDs."""
        if not job_ids:
            return []

        all_details: list[JobDetails] = []

        for chunk in _chunked(job_ids, _JOB_BATCH_SIZE):
            params = {"filter[other][ids]": ",".join(chunk)}
            try:
                raw = await self._http.get(self._http.job_url, params=params)
                response = JobDetailsResponse.model_validate(raw)
                all_details.extend(response.data)
            except ValidationError as exc:
                logger.debug("Job details response validation failed", exc_info=True)
                raise InvalidResponseError(
                    "Failed to validate job details response.", validation_error=exc
                ) from exc
            except WuzzufAPIError:
                raise
            except Exception as exc:
                logger.error("Unexpected error fetching job details", exc_info=True)
                raise WuzzufAPIError(f"Unexpected error fetching job details: {exc}") from exc

        logger.debug("Fetched details for %d jobs.", len(all_details))
        return all_details


def _build_filter_payload(filters: SearchFilters) -> SearchFilterPayload:
    """Serialize a SearchFilters instance for the API."""

    def _fmt(dt) -> str | None:
        """Format datetime to MM/DD/YYYY HH:MM:SS."""
        if dt is None:
            return None
        if dt.tzinfo is None:
            from datetime import timezone

            dt = dt.replace(tzinfo=timezone.utc)
        return dt.strftime("%m/%d/%Y %H:%M:%S")

    return SearchFilterPayload(
        posted_at_from=_fmt(filters.posted_since),
        posted_at_to=_fmt(filters.posted_until),
        expire_at_from=_fmt(filters.expires_since),
        country_id=filters.country_id,
        city_id=filters.city_id,
        career_level_id=filters.career_level_id,
        keywords=list(filters.keywords) if filters.keywords else None,
    )
