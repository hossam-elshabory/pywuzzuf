"""
Generic async pagination abstraction.

Design decisions
----------------
* ``PaginationConfig`` is ``@dataclass(frozen=True)`` — safe to nest inside
  the frozen ``JobQuery`` without mutation-through-reference escape hatch.

* ``_stream()`` and ``collect()`` delegate to a single shared ``_paginate()``
  async generator — single source of truth for the state machine.

* ``PaginationSignal`` gives callbacks a full three-branch contract:

    - Progress callback returns ``STOP``  → graceful cancel, ``terminated_early=True``
    - Error callback returns ``STOP``     → graceful cancel, ``terminated_early=True``
    - Error callback returns ``CONTINUE`` → skip the failing page, advance cursor,
                                            continue iteration
    - No error callback registered       → exception propagates as-is

* ``collect()`` sets ``terminated_early=True`` for ALL early-stop reasons, not
  just ``max_results`` / ``max_pages`` hits — including callback ``STOP`` signals.
  A ``_terminated_early`` instance flag is set inside ``_paginate``
  just before any non-natural return, and reset at the start of each ``collect()``
  call so repeated calls work correctly.

* Progress callback ``page_number`` argument is **1-indexed**.

* A ``max_pages`` hard ceiling prevents runaway loops from API cursor-wraparound
  bugs.

* ``collect()`` emits a memory warning when ``max_results`` is unset.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from enum import Enum, auto
from typing import (
    AsyncGenerator,
    Awaitable,
    Callable,
    Generic,
    NamedTuple,
    Optional,
    TypeVar,
)

logger = logging.getLogger("pywuzzuf.pagination")

T = TypeVar("T")


class PaginationSignal(Enum):
    """
    Control signal returned by pagination callbacks.

    This enum allows progress and error handlers to communicate back to the
    paginator's internal state machine.

    For **progress callbacks**:
        - ``STOP``: Gracefully terminate iteration after the current page.
        - ``CONTINUE`` (or ``None``): Proceed to the next page as normal.

    For **error callbacks**:
        - ``STOP`` (or ``None``): Swallow the current exception and terminate iteration.
        - ``CONTINUE``: Swallow the exception, skip the failing page, and attempt
          to fetch the next page.
        - ``RETRY``: Swallow the exception and immediately retry fetching the
          current page (use with caution to avoid infinite loops).
    """

    CONTINUE = auto()
    STOP = auto()
    RETRY = auto()


# Explicit type aliases — IDEs show the full signature in tooltips.
ProgressCallback = Callable[
    [int, int],  # (total_fetched: int, page_number: int)  ← 1-indexed
    Optional[PaginationSignal],
]
"""
Callback invoked after each successfully fetched page.

Parameters
----------
total_fetched : int
    The total number of items yielded so far across all pages.
page_number : int
    The current page number (1-indexed).

Returns
-------
PaginationSignal, optional
    Return ``PaginationSignal.STOP`` to cancel iteration gracefully.
    Returning ``None`` (the default for ``print``) is treated as ``CONTINUE``.
"""

ErrorCallback = Callable[
    [Exception, int, int],  # (error, page_number, total_fetched_before_error)
    Optional[PaginationSignal],
]
"""
Callback invoked when a page fetch raises an exception.

Parameters
----------
error : Exception
    The exception that was raised during the fetch.
page_number : int
    The 1-indexed page number where the error occurred.
total_fetched : int
    The number of items successfully retrieved before this error.

Returns
-------
PaginationSignal, optional
    - ``STOP`` (or ``None``): Swallow the error and stop iteration.
    - ``CONTINUE``: Swallow the error, skip this page, and keep iterating.
    - Raising an exception inside the callback will propagate it to the caller.
"""


@dataclass(frozen=True)
class PaginationConfig:
    """
    Configuration for asynchronous pagination.

    This dataclass is frozen to ensure safe reuse when nested within other
    immutable objects like ``SearchFilters``.

    Parameters
    ----------
    page_size : int, optional
        Number of items to request per page from the API (max 50).
        Defaults to 50.
    max_results : int, optional
        Hard cap on the total number of items yielded. If None, the API
        will be exhausted naturally. Defaults to None.
    max_pages : int, optional
        Hard cap on the total number of pages fetched. Prevents infinite
        loops in case of API cursor issues. Defaults to 200.
    on_progress : ProgressCallback, optional
        A callable invoked after each successful page fetch.
    on_error : ErrorCallback, optional
        A callable invoked when a page fetch fails.
    """

    page_size: int = 50
    max_results: int | None = None
    max_pages: int = 200
    on_progress: ProgressCallback | None = None
    on_error: ErrorCallback | None = None


@dataclass(frozen=True)
class FetchBatch(Generic[T]):
    """
    Metadata for a single raw API page fetch.

    Decouples raw API counts from the actual number of yielded items, allowing
    for accurate cursor tracking even when items are filtered in-memory.

    Parameters
    ----------
    items : list[T]
        The items successfully retrieved from the page.
    raw_count : int
        The total number of raw results the API claimed were in this page.
    has_more : bool
        Whether the API indicates that more results are available.
    """

    items: list[T]
    raw_count: int
    has_more: bool


@dataclass
class PaginationResult(Generic[T]):
    """
    Aggregated result of an eager pagination operation.

    Attributes
    ----------
    items : list[T]
        All collected items across all fetched pages.
    total_fetched : int
        Running total of items yielded across all pages.
    pages_fetched : int
        The total number of successfully retrieved pages.
    terminated_early : bool
        True if the pagination stopped before the API was naturally exhausted
        (e.g., reached ``max_results`` or callback returned ``STOP``).
    empty_on_start : bool
        True if the first page fetch returned zero items.
    """

    items: list[T]
    total_fetched: int
    pages_fetched: int
    terminated_early: bool
    empty_on_start: bool


class _PageMeta(NamedTuple):
    """Per-item metadata emitted by the shared ``_paginate()`` generator."""

    page: int  # 1-indexed page number this item came from
    total_so_far: int  # running total *after* yielding this item
    is_last_in_batch: bool  # True for the last item in its page


class AsyncPaginator(Generic[T]):
    """
    Generic asynchronous paginator with built-in cursor management.

    This class wraps a raw page-fetching coroutine into an easy-to-use
    async iterable. It automatically handles cursor advancement, progress
    reporting, error recovery, and hard ceilings.

    Parameters
    ----------
    fetch_page : Callable[[int, int], Awaitable[FetchBatch[T]]]
        An async function that retrieves a single page given a start index
        and a page size. It must return a ``FetchBatch``.
    config : PaginationConfig
        The configuration for limits and callbacks.

    Examples
    --------
    Streaming results memory-efficiently:

    >>> async for item in paginator:
    ...     process(item)

    Eagerly collecting all results with metadata:

    >>> result = await paginator.collect()
    >>> print(f"Fetched {result.total_fetched} items.")
    """

    def __init__(
        self,
        fetch_page: Callable[[int, int], Awaitable[FetchBatch[T]]],
        config: PaginationConfig,
    ) -> None:
        self._fetch = fetch_page
        self._config = config
        # Tracks whether the most recent _paginate() call ended early
        self._terminated_early = False

    async def _paginate(self) -> AsyncGenerator[tuple[T, _PageMeta], None]:
        """
        Core pagination state machine.

        Yields ``(item, _PageMeta)`` pairs.
        """
        cfg = self._config
        start = 0
        page = 0  # 0-indexed internally
        total = 0

        while True:
            if cfg.max_results is not None and total >= cfg.max_results:
                logger.debug("max_results=%d reached — stopping.", cfg.max_results)
                self._terminated_early = True
                return

            if page >= cfg.max_pages:
                logger.warning(
                    "Pagination hard ceiling reached: %d pages fetched. "
                    "Stopping to prevent a runaway loop. "
                    "Raise PaginationConfig.max_pages if this is intentional.",
                    cfg.max_pages,
                )
                self._terminated_early = True
                return

            page_1indexed = page + 1
            try:
                batch = await self._fetch(start, cfg.page_size)
            except Exception as exc:
                signal = self._invoke_error_callback(exc, page_1indexed, total)

                if signal is PaginationSignal.STOP:
                    logger.info(
                        "Pagination stopped by error callback after %d items on page %d: %s",
                        total,
                        page_1indexed,
                        exc,
                    )
                    self._terminated_early = True
                    return

                elif signal is PaginationSignal.RETRY:
                    logger.info(
                        "Retrying page %d by error callback request: %s",
                        page_1indexed,
                        exc,
                    )
                    continue

                elif cfg.on_error is not None:
                    logger.warning(
                        "Page %d skipped by error callback (CONTINUE): %s",
                        page_1indexed,
                        exc,
                    )
                    page += 1
                    start += cfg.page_size
                    continue

                else:
                    raise

            if batch.raw_count == 0:
                logger.debug("Empty raw batch on page %d — iteration complete.", page_1indexed)
                return

            batch_len = len(batch.items)
            for i, item in enumerate(batch.items):
                if cfg.max_results is not None and total >= cfg.max_results:
                    self._terminated_early = True
                    return
                total += 1
                is_last = i == batch_len - 1
                yield (
                    item,
                    _PageMeta(
                        page=page_1indexed,
                        total_so_far=total,
                        is_last_in_batch=is_last,
                    ),
                )

            page += 1
            start += batch.raw_count

            signal = self._invoke_progress_callback(total, page)
            if signal is PaginationSignal.STOP:
                logger.info("Pagination stopped by progress callback after %d items.", total)
                self._terminated_early = True
                return

            if not batch.has_more:
                logger.debug("FetchBatch signalled no more items — assuming last page.")
                return

    def __aiter__(self):
        """Enable async iteration over paginated results."""
        return self._stream()

    async def _stream(self) -> AsyncGenerator[T, None]:
        """Yield items one at a time — lazy, memory-efficient."""
        async for item, _ in self._paginate():
            yield item

    async def collect(self) -> PaginationResult[T]:
        """
        Exhaust the API and collect all items eagerly.

        Warning: This buffers the entire result set in memory. For large
        queries, use async iteration instead.

        Returns
        -------
        PaginationResult
            The aggregated results including items and metadata.
        """
        if self._config.max_results is None:
            logger.warning(
                "collect() called without a max_results cap. "
                "The entire result set will be buffered in memory. "
                "For large queries, consider async iteration or set .limit(n)."
            )

        self._terminated_early = False

        items: list[T] = []
        last_page = 0
        last_total = 0
        empty_on_start = True

        async for item, meta in self._paginate():
            empty_on_start = False
            items.append(item)
            last_page = meta.page
            last_total = meta.total_so_far

        return PaginationResult(
            items=items,
            total_fetched=last_total,
            pages_fetched=last_page,
            terminated_early=self._terminated_early,
            empty_on_start=empty_on_start,
        )

    def _invoke_progress_callback(self, total: int, page: int) -> PaginationSignal:
        """Call the progress callback, swallowing any exception it raises."""
        cb = self._config.on_progress
        if cb is None:
            return PaginationSignal.CONTINUE
        try:
            result = cb(total, page)
            if isinstance(result, PaginationSignal):
                return result
            return PaginationSignal.CONTINUE
        except Exception as exc:
            logger.warning("Progress callback raised (ignored): %s", exc)
            return PaginationSignal.CONTINUE

    def _invoke_error_callback(self, error: Exception, page: int, total: int) -> PaginationSignal:
        """Call the error callback."""
        cb = self._config.on_error
        if cb is None:
            return PaginationSignal.CONTINUE
        try:
            result = cb(error, page, total)
            if isinstance(result, PaginationSignal):
                return result
            return PaginationSignal.STOP
        except Exception:
            raise
