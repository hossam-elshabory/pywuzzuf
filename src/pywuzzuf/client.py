"""
Public client entry points.

This module provides the main entry points for the pywuzzuf library, offering
both asynchronous and synchronous clients.

The `WuzzufClient` is the recommended way to use the library in asynchronous
applications, while `SyncWuzzufClient` provides a familiar synchronous interface
for scripts and legacy environments.

Loop lifecycle
--------------
`SyncWuzzufClient` manages a private event loop to ensure thread safety and
compatibility with `curl_cffi`. Upon entering the context manager, a new loop
is created and registered as the thread's current loop. On exit, the loop is
properly closed and the previous loop state is restored. This prevents resource
leaks and ensures that internal `curl_cffi` calls use the correct loop.
"""

from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING, Any, Callable, Coroutine, Optional, TypeVar, cast

from curl_cffi.requests import AsyncSession

from ._http import HttpCore
from .filters import SearchFilters
from .models import EnrichedJob
from .pagination import PaginationResult, PaginationSignal
from .resources.companies import CompaniesResource
from .resources.jobs import JobQuery, JobsResource

if TYPE_CHECKING:
    from types import TracebackType

logger = logging.getLogger("pywuzzuf.client")

T = TypeVar("T")


class _NotInitialized:
    """
    Placeholder assigned to synchronous resources before they are initialized.

    Any attribute access on this object raises a ``RuntimeError`` with an
    explicit message instructing the user to use the client as a context manager.
    """

    def __getattr__(self, name: str) -> Any:
        raise RuntimeError(
            f"Attempted to access 'client.jobs.{name}' before entering the "
            "SyncWuzzufClient context manager.\n\n"
            "Use:\n"
            "    with SyncWuzzufClient() as client:\n"
            f"        client.jobs.{name}(...)\n"
        )


class WuzzufClient:
    """
    Asynchronous Wuzzuf API client.

    The primary entry point for interacting with the Wuzzuf API asynchronously.
    It manages an underlying HTTP session and provides access to various API
    resources.

    Examples
    --------
    Basic usage with an async context manager:

    >>> async with WuzzufClient() as client:
    ...     query = client.jobs.search("Python")
    ...     async for job in query.paginate():
    ...         print(job.attributes.title)

    Attributes
    ----------
    companies : CompaniesResource
        Access to company-related API endpoints.
    jobs : JobsResource
        Access to job-related API endpoints.
    """

    def __init__(
        self,
        base_url: str = "https://wuzzuf.net/api",
        impersonate: str = "chrome124",  # aligned with HttpCore default
        session: Optional[AsyncSession] = None,
    ) -> None:
        """
        Initialize the asynchronous Wuzzuf client.

        Parameters
        ----------
        base_url : str, optional
            The root URL of the Wuzzuf API. Defaults to "https://wuzzuf.net/api".
        impersonate : str, optional
            The browser fingerprint to impersonate for curl_cffi.
            Defaults to "chrome124". If the API returns unexpected 403 errors,
            try a different Chrome version string (e.g., "chrome124").
        session : curl_cffi.requests.AsyncSession, optional
            A pre-configured async session to use. If provided, the client
            will not close this session on exit. Defaults to None.
        """
        self._owns_session = session is None
        http = HttpCore(
            base_url=base_url,
            impersonate=impersonate,
            session=session,
        )
        self._http = http
        self.companies = CompaniesResource(http)
        self.jobs = JobsResource(http, self.companies)

    async def __aenter__(self) -> WuzzufClient:
        return self

    async def __aexit__(
        self,
        exc_type: Optional[type[BaseException]],
        exc_val: Optional[BaseException],
        exc_tb: Optional[TracebackType],
    ) -> None:
        await self.close()

    async def close(self) -> None:
        """
        Close the underlying HTTP session.

        Only closes the session if it was created and is owned by this client.
        """
        if self._owns_session:
            await self._http.close()


class SyncJobQuery:
    """
    Synchronous mirror of the asynchronous JobQuery.

    Provides a synchronous builder interface for job searches. Every method
    delegates to an underlying async `JobQuery` and executes it using the
    client's persistent event loop.

    Parameters
    ----------
    async_query : JobQuery
        The underlying asynchronous job query object.
    run : Callable[[asyncio.Coroutine[Any, Any, Any]], Any]
        The internal runner function to execute coroutines synchronously.
    """

    def __init__(
        self,
        async_query: JobQuery,
        run: Callable[[Coroutine[Any, Any, Any]], Any],
    ) -> None:
        self._q = async_query
        self._run = run

    def filter(self, filters: SearchFilters) -> SyncJobQuery:
        """
        Apply search filters to the query.

        Parameters
        ----------
        filters : SearchFilters
            The filters to apply (e.g., career level, job type).

        Returns
        -------
        SyncJobQuery
            A new query instance with the applied filters.
        """
        return SyncJobQuery(self._q.filter(filters), self._run)

    def page_size(self, n: int) -> SyncJobQuery:
        """
        Set the number of results per page.

        Parameters
        ----------
        n : int
            Number of results per page (max 50).

        Returns
        -------
        SyncJobQuery
            A new query instance with the updated page size.
        """
        return SyncJobQuery(self._q.page_size(n), self._run)

    def limit(self, n: int) -> SyncJobQuery:
        """
        Set a cap on the total number of results to fetch.

        Parameters
        ----------
        n : int
            The maximum number of jobs to return.

        Returns
        -------
        SyncJobQuery
            A new query instance with the limit applied.
        """
        return SyncJobQuery(self._q.limit(n), self._run)

    def max_pages(self, n: int) -> SyncJobQuery:
        """
        Set a cap on the number of pages to fetch.

        Parameters
        ----------
        n : int
            The maximum number of pages to request.

        Returns
        -------
        SyncJobQuery
            A new query instance with the page limit applied.
        """
        return SyncJobQuery(self._q.max_pages(n), self._run)

    def on_progress(self, cb: Callable[[int, int], None]) -> SyncJobQuery:
        """
        Register a callback for pagination progress.

        Parameters
        ----------
        cb : Callable[[int, int], None]
            A function called with (current_count, total_available) after each page.

        Returns
        -------
        SyncJobQuery
            A new query instance with the progress callback.
        """
        return SyncJobQuery(self._q.on_progress(cb), self._run)

    def on_error(self, cb: Callable[[Exception, int, int], Optional[PaginationSignal]]) -> SyncJobQuery:
        """
        Register a callback for errors during pagination.

        Parameters
        ----------
        cb : Callable[[Exception, int, int], Optional[PaginationSignal]]

        Returns
        -------
        SyncJobQuery
            A new query instance with the error callback.
        """
        return SyncJobQuery(self._q.on_error(cb), self._run)

    def all(self) -> PaginationResult[EnrichedJob]:
        """
        Collect all results eagerly.

        Executes the search query and paginates through all available results.

        Returns
        -------
        PaginationResult[EnrichedJob]
            The paginated result containing all found jobs.

        Raises
        ------
        WuzzufAPIError
            If the API returns an error response.
        """
        return self._run(self._q.all())

    def first(self) -> Optional[EnrichedJob]:
        """
        Return the first result of the query.

        Returns
        -------
        EnrichedJob, optional
            The first job matching the query, or None if no results were found.
        """
        return self._run(self._q.first())

    def __repr__(self) -> str:
        return f"SyncJobQuery(query={self._q._query!r}, filters={self._q._filters!r})"


class SyncJobsResource:
    """
    Synchronous mirror of the JobsResource.

    Provides a synchronous entry point for job-related API operations.

    Parameters
    ----------
    async_resource : JobsResource
        The underlying asynchronous jobs resource object.
    run : Callable[[asyncio.Coroutine[Any, Any, Any]], Any]
        The internal runner function to execute coroutines synchronously.
    """

    def __init__(
        self,
        async_resource: JobsResource,
        run: Callable[[Coroutine[Any, Any, Any]], Any],
    ) -> None:
        self._resource = async_resource
        self._run = run

    def search(self, query: str) -> SyncJobQuery:
        """
        Begin building a synchronous job search query.

        Parameters
        ----------
        query : str
            The search keywords (e.g., "Python Developer").

        Returns
        -------
        SyncJobQuery
            A builder object to further refine and execute the search.
        """
        return SyncJobQuery(self._resource.search(query), self._run)


class SyncWuzzufClient:
    """
    Synchronous Wuzzuf API client.

    A wrapper around `WuzzufClient` that provides a synchronous interface by
    managing its own persistent event loop. This allows using the library in
    synchronous scripts and environments without a running event loop.

    Examples
    --------
    >>> with SyncWuzzufClient() as client:
    ...     result = client.jobs.search("Python").limit(5).all()
    ...     for job in result.items:
    ...         print(job.attributes.title)

    Attributes
    ----------
    jobs : SyncJobsResource
        Access to job-related API endpoints.
    """

    def __init__(
        self,
        base_url: str = "https://wuzzuf.net/api",
        impersonate: str = "chrome124",  # aligned with WuzzufClient and HttpCore
    ) -> None:
        """
        Initialize the synchronous Wuzzuf client.

        Parameters
        ----------
        base_url : str, optional
            The root URL of the Wuzzuf API. Defaults to "https://wuzzuf.net/api".
        impersonate : str, optional
            The browser fingerprint to impersonate for curl_cffi.
            Defaults to "chrome124". If the API returns unexpected 403 errors,
            try a different Chrome version string (e.g., "chrome124").
        """
        self._base_url = base_url
        self._impersonate = impersonate
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._async_client: Optional[WuzzufClient] = None
        self._old_loop: Optional[asyncio.AbstractEventLoop] = None

        self.jobs: SyncJobsResource = cast(SyncJobsResource, _NotInitialized())

    def __enter__(self) -> SyncWuzzufClient:
        """
        Enter the synchronous context manager and initialize the event loop.

        Returns
        -------
        SyncWuzzufClient
            The initialized synchronous client.

        Raises
        ------
        RuntimeError
            If called inside a running event loop.
        """
        try:
            running = asyncio.get_running_loop()
        except RuntimeError:
            running = None

        if running is not None:
            raise RuntimeError(
                "SyncWuzzufClient cannot be used inside a running event loop "
                "(detected in Jupyter, FastAPI, or similar).\n\n"
                "Options:\n"
                "  1. Use the async client:\n"
                "         async with WuzzufClient() as client:\n"
                "             result = await client.jobs.search(...).all()\n"
                "  2. Install nest_asyncio and patch the loop before constructing:\n"
                "         import nest_asyncio; nest_asyncio.apply()\n"
                "         with SyncWuzzufClient() as client: ...\n"
            )

        try:
            self._old_loop = asyncio.get_event_loop_policy().get_event_loop()
        except (RuntimeError, AssertionError):
            self._old_loop = None

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        self._loop = loop
        logger.debug("SyncWuzzufClient created new event loop %r", loop)

        try:
            self._async_client = WuzzufClient(
                base_url=self._base_url,
                impersonate=self._impersonate,
            )
            self.jobs = SyncJobsResource(self._async_client.jobs, self._run)
        except Exception:
            self._loop.close()
            asyncio.set_event_loop(self._old_loop)
            self._loop = None
            self._old_loop = None
            raise

        return self

    def __exit__(
        self,
        exc_type: Optional[type[BaseException]],
        exc_val: Optional[BaseException],
        exc_tb: Optional[TracebackType],
    ) -> None:
        """
        Exit the synchronous context manager and close the event loop.

        Restores the previous event loop state and ensures all tasks are finished.
        """
        if self._async_client is not None and self._loop is not None:
            try:
                self._loop.run_until_complete(self._async_client.close())
                self._loop.run_until_complete(self._shutdown_loop())
            finally:
                logger.debug("SyncWuzzufClient closing loop %r", self._loop)
                self._loop.close()
                asyncio.set_event_loop(self._old_loop)
                logger.debug("SyncWuzzufClient restored previous loop %r", self._old_loop)
                self._loop = None
                self._old_loop = None
                self._async_client = None
                self.jobs = cast(SyncJobsResource, _NotInitialized())

    async def _shutdown_loop(self) -> None:
        """Cancel all remaining tasks on the loop and let them finish."""
        tasks = [t for t in asyncio.all_tasks(self._loop) if t is not asyncio.current_task()]
        for task in tasks:
            task.cancel()
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

    def _run(self, coro: Coroutine[Any, Any, T]) -> T:
        """Execute a coroutine on the client's private persistent event loop."""
        if self._loop is None:
            raise RuntimeError(
                "SyncWuzzufClient._run() called outside a 'with' block. "
                "Use 'with SyncWuzzufClient() as client: ...'."
            )
        return self._loop.run_until_complete(coro)
