import asyncio

import pytest

from pywuzzuf.client import SyncWuzzufClient, WuzzufClient


@pytest.mark.asyncio
class TestWuzzufClient:
    async def test_async_context_manager(self, mock_http):
        async with WuzzufClient() as client:
            client._http = mock_http  # inject mock
            # Perform a simple search
            result = await client.jobs.search("python").limit(5).all()
            assert len(result.items) > 0

    async def test_close_cleans_up(self):
        client = WuzzufClient()
        await client.close()  # should not raise


class TestSyncWuzzufClient:
    def test_sync_context_manager(self, mock_http):
        with SyncWuzzufClient() as client:
            # inject mock by replacing internal async client's _http
            assert client._async_client is not None
            client._async_client._http = mock_http
            result = client.jobs.search("python").limit(5).all()
            assert len(result.items) > 0

    def test_raises_if_used_outside_context(self):
        client = SyncWuzzufClient()
        with pytest.raises(RuntimeError, match="Attempted to access 'client.jobs.search'"):
            client.jobs.search("python")

    def test_detects_running_loop(self):
        # Simulate a running loop in the same thread
        async def run():
            with pytest.raises(RuntimeError, match="inside a running event loop"):
                SyncWuzzufClient().__enter__()

        asyncio.run(run())
