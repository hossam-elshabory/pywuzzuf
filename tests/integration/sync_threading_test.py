"""
Integration test for SyncWuzzufClient thread safety.

Verifies that multiple threads can each use their own SyncWuzzufClient
instance without interfering with each other. All HTTP calls are mocked
using the same static fixtures.
"""

import threading

from pywuzzuf.client import SyncWuzzufClient


def _worker(thread_index, results, mock_http):
    """
    Thread worker function: creates its own client, injects the mock HTTP,
    runs a search, and appends the number of returned jobs to results.
    """
    with SyncWuzzufClient() as client:
        # Inject the mock HTTP core into the internal async client
        assert client._async_client is not None
        client._async_client._http = mock_http

        # Perform a search – the query string is irrelevant because the mock
        # always returns the same set of job IDs.
        result = client.jobs.search("python").limit(5).all()

        # Append the count to results (list append is thread-safe in CPython)
        results.append(len(result.items))


def test_sync_client_thread_safety(mock_http):
    """Launch multiple threads, each using its own SyncWuzzufClient."""
    num_threads = 3
    threads = []
    results = []  # will be populated by worker threads

    for i in range(num_threads):
        t = threading.Thread(
            target=_worker,
            args=(i, results, mock_http),
            daemon=True,  # daemon ensures threads exit even if test fails
        )
        threads.append(t)
        t.start()

    # Wait for all threads to complete
    for t in threads:
        t.join(timeout=5)

    # All threads should have appended a result
    assert len(results) == num_threads

    # Each result should be > 0 (the mock fixture returns at least one job)
    for count in results:
        assert count > 0, f"Thread returned {count} jobs, expected at least 1"


def test_sync_client_thread_safety_no_warnings(mock_http, recwarn):
    """Same as test_sync_client_thread_safety but checks for warnings."""
    num_threads = 3
    threads = []
    results = []

    for i in range(num_threads):
        t = threading.Thread(target=_worker, args=(i, results, mock_http), daemon=True)
        threads.append(t)
        t.start()

    for t in threads:
        t.join(timeout=5)

    assert len(results) == num_threads
    for count in results:
        assert count > 0

    # No warnings should have been raised during the test
    assert len(recwarn) == 0, f"Warnings detected: {[str(w.message) for w in recwarn]}"
