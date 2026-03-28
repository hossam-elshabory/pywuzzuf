import json
from pathlib import Path
from typing import Any

import pytest

from pywuzzuf._http import HttpCore
from pywuzzuf.client import WuzzufClient

FIXTURES_DIR = Path(__file__).parent / "fixtures"


def load_json(filename: str) -> dict[str, Any]:
    """Load a JSON fixture from the fixtures directory."""
    path = FIXTURES_DIR / filename
    with open(path, encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture
def mock_http(monkeypatch):
    """
    Replace HttpCore.request with a deterministic version that returns
    fixture data based on the requested URL/params.
    """

    async def mock_request(self, method, url, params=None, **kwargs):
        # Search endpoint
        if "/search/job" in url:
            # Respect the actual pageSize parameter (default 20)
            # params might be in the query string for GET or body for POST,
            # but search is a POST request usually.
            # However, _http.py passes params to request() which are query params.
            # Wait, the search endpoint in jobs.py uses POST with a JSON body.
            # The `mock_request` signature here receives `params`.
            # Let's check _http.py: request(method, url, params=..., **kwargs).
            # For POST, params are usually empty, data is in kwargs['data'].

            # Let's look at how JobsResource calls it:
            # raw = await self._http.post(self._http.search_url, data=payload...)
            # _http.post calls request("POST", url, data=data...)
            # So params is None for search.

            # This means the mock logic below for "start" and "page" is actually
            # incorrect for the search endpoint if it relies on 'params'.
            # The search payload is in the body.
            # We need to parse kwargs.get('data') which is a JSON string.

            import json

            body_data = kwargs.get("data")
            start = 0
            size = 20

            if body_data:
                try:
                    payload = json.loads(body_data)
                    start = payload.get("startIndex", 0)
                    size = payload.get("pageSize", 20)
                except json.JSONDecodeError:
                    pass

            # Fallback logic for GET params if needed (though search is POST)
            if params:
                start = params.get("startIndex", start)
                # pageSize is likely not in query params for this API structure

            page = (start // size) + 1

            # Return page1.json, page2.json, or empty.json
            if page == 1:
                return load_json("search/page1.json")
            elif page == 2:
                return load_json("search/page2.json")
            else:
                return load_json("search/empty.json")

        # Job details endpoint
        if "/job" in url and params and "filter[other][ids]" in str(params):
            # For simplicity, return the full batch
            # it contains only the IDs we use in tests.
            return load_json("job_details/batch.json")

        # Company details endpoint
        if "/company" in url and params and "filter[id]" in params:
            requested_ids = params["filter[id]"].split(",")
            full_data = load_json("company_details/batch.json")["data"]
            # Filter to only the requested IDs
            filtered_data = [c for c in full_data if c["id"] in requested_ids]
            return {"data": filtered_data}

        # Fallback – raise helpful error
        raise ValueError(f"No fixture mapping for {method} {url} with params={params}")

    monkeypatch.setattr(HttpCore, "request", mock_request)
    return HttpCore()  # return an instance for clients that need it


@pytest.fixture
def async_client(mock_http) -> WuzzufClient:
    """Return an async client pre-configured with the mock HTTP core."""
    client = WuzzufClient()
    client._http = mock_http
    return client


def pytest_addoption(parser):
    parser.addoption(
        "--run-live",
        action="store_true",
        help="run live API tests (against real Wuzzuf)",
    )


def pytest_configure(config):
    config.addinivalue_line("markers", "live: mark test as live API test")


def pytest_collection_modifyitems(config, items):
    if not config.getoption("--run-live"):
        skip_live = pytest.mark.skip(reason="need --run-live option to run")
        for item in items:
            if "live" in item.keywords:
                item.add_marker(skip_live)
