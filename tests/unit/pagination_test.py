import pytest

from pywuzzuf.pagination import (
    AsyncPaginator,
    FetchBatch,
    PaginationConfig,
    PaginationSignal,
)


@pytest.mark.asyncio
class TestAsyncPaginator:
    async def test_normal_iteration(self):
        async def fetch(start, size):
            if start >= 30:
                return FetchBatch(items=[], raw_count=0, has_more=False)
            items = list(range(start, min(start + size, 30)))
            return FetchBatch(items=items, raw_count=len(items), has_more=True)

        config = PaginationConfig(page_size=10)
        pag = AsyncPaginator(fetch, config)
        collected = [item async for item in pag]
        assert collected == list(range(30))

    async def test_max_results_stops_early(self):
        async def fetch(start, size):
            items = list(range(start, start + size))
            return FetchBatch(items=items, raw_count=len(items), has_more=True)

        config = PaginationConfig(page_size=10, max_results=25)
        pag = AsyncPaginator(fetch, config)
        result = await pag.collect()
        assert len(result.items) == 25
        assert result.terminated_early is True
        assert result.total_fetched == 25

    async def test_max_pages_stops_early(self):
        async def fetch(start, size):
            items = list(range(start, start + size))
            return FetchBatch(items=items, raw_count=len(items), has_more=True)

        config = PaginationConfig(page_size=10, max_pages=2)
        pag = AsyncPaginator(fetch, config)
        result = await pag.collect()
        assert len(result.items) == 20
        assert result.terminated_early is True

    async def test_progress_callback_receives_correct_values(self):
        called = []

        def progress(total, page):
            called.append((total, page))
            return None

        async def fetch(start, size):
            if start >= 20:
                return FetchBatch(items=[], raw_count=0, has_more=False)
            items = list(range(start, start + size))
            return FetchBatch(items=items, raw_count=len(items), has_more=True)

        config = PaginationConfig(page_size=10, on_progress=progress)
        pag = AsyncPaginator(fetch, config)
        await pag.collect()
        assert called == [(10, 1), (20, 2)]

    async def test_progress_callback_stop_signal(self):
        def progress(total, page):
            if page == 2:
                return PaginationSignal.STOP
            return None

        async def fetch(start, size):
            items = list(range(start, start + size))
            return FetchBatch(items=items, raw_count=len(items), has_more=True)

        config = PaginationConfig(page_size=10, on_progress=progress)
        pag = AsyncPaginator(fetch, config)
        result = await pag.collect()
        assert len(result.items) == 20
        assert result.terminated_early is True

    async def test_error_callback_continue(self):
        async def fetch(start, size):
            if start == 10:
                raise ValueError("Simulated error")
            if start >= 30:
                return FetchBatch(items=[], raw_count=0, has_more=False)
            items = list(range(start, start + size))
            return FetchBatch(items=items, raw_count=len(items), has_more=True)

        def on_error(exc, page, total):
            return PaginationSignal.CONTINUE

        config = PaginationConfig(page_size=10, on_error=on_error)
        pag = AsyncPaginator(fetch, config)
        result = await pag.collect()
        assert len(result.items) == 20
        assert result.terminated_early is False

    async def test_error_callback_stop(self):
        async def fetch(start, size):
            if start == 10:
                raise ValueError("Simulated error")
            items = list(range(start, start + size))
            return FetchBatch(items=items, raw_count=len(items), has_more=True)

        def on_error(exc, page, total):
            return PaginationSignal.STOP

        config = PaginationConfig(page_size=10, on_error=on_error)
        pag = AsyncPaginator(fetch, config)
        result = await pag.collect()
        assert len(result.items) == 10
        assert result.terminated_early is True

    async def test_empty_on_start_true(self):
        async def fetch(start, size):
            return FetchBatch(items=[], raw_count=0, has_more=False)

        config = PaginationConfig(page_size=10)
        pag = AsyncPaginator(fetch, config)
        result = await pag.collect()
        assert result.empty_on_start is True
        assert result.items == []
