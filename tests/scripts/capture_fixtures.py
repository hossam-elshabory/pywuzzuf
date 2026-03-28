#!/usr/bin/env python
"""
Capture live API responses and save them as JSON fixtures.

Run from project root:
    python scripts/capture_fixtures.py

Use --endpoint to capture only specific endpoints: search, job, company
"""

import argparse
import asyncio
import json
from pathlib import Path

from pywuzzuf.client import WuzzufClient
from pywuzzuf.models import SearchFilterPayload, SearchPayload

# Path(__file__).parent is 'scripts', parent.parent is 'tests'.
# We only need to append 'fixtures'.
FIXTURES_DIR = Path(__file__).parent.parent / "fixtures"
SEARCH_DIR = FIXTURES_DIR / "search"
JOB_DETAILS_DIR = FIXTURES_DIR / "job_details"
COMPANY_DETAILS_DIR = FIXTURES_DIR / "company_details"
ERRORS_DIR = FIXTURES_DIR / "errors"

# Known company IDs from captured jobs (adjust as needed)
COMPANY_IDS = ["1001", "1002"]


async def capture_search_pages():
    """Capture first two pages of search results for 'python' and an empty search."""
    async with WuzzufClient() as client:
        # Helper to perform a search with given parameters
        async def fetch_search(query, start, page_size=20):
            # Build payload using the same model as the client's internal method
            payload = SearchPayload(
                query=query,
                start_index=start,
                page_size=page_size,
                search_filters=SearchFilterPayload(),  # empty filters
            )
            # Serialize with by_alias=True to get camelCase field names
            data = payload.model_dump_json(by_alias=True)
            return await client._http.post(client._http.search_url, data=data)

        # Page 1
        resp = await fetch_search("python", 0)
        with open(SEARCH_DIR / "page1.json", "w") as f:
            json.dump(resp, f, indent=2)
        print("Saved search/page1.json")

        # Page 2 (startIndex=20)
        resp = await fetch_search("python", 20)
        with open(SEARCH_DIR / "page2.json", "w") as f:
            json.dump(resp, f, indent=2)
        print("Saved search/page2.json")

        # Empty search (unlikely term)
        resp = await fetch_search("thisjobprobablydoesnotexist", 0)
        with open(SEARCH_DIR / "empty.json", "w") as f:
            json.dump(resp, f, indent=2)
        print("Saved search/empty.json")


async def capture_job_details():
    """Capture job details for a set of job IDs obtained from search."""
    async with WuzzufClient() as client:
        # First get some real job IDs
        payload = SearchPayload(
            query="python",
            start_index=0,
            page_size=10,
            search_filters=SearchFilterPayload(),
        )
        data = payload.model_dump_json(by_alias=True)
        search_resp = await client._http.post(client._http.search_url, data=data)
        job_ids = [item["id"] for item in search_resp["data"]]

        if job_ids:
            params = {"filter[other][ids]": ",".join(job_ids)}
            details = await client._http.get(client._http.job_url, params=params)
            with open(JOB_DETAILS_DIR / "batch.json", "w") as f:
                json.dump(details, f, indent=2)
            print(f"Saved job_details/batch.json with {len(job_ids)} jobs")
        else:
            print("No job IDs found; skipping job details capture.")


async def capture_company_details():
    """Capture company details for known company IDs."""
    async with WuzzufClient() as client:
        if COMPANY_IDS:
            params = {"filter[id]": ",".join(COMPANY_IDS)}
            details = await client._http.get(client._http.company_url, params=params)
            with open(COMPANY_DETAILS_DIR / "batch.json", "w") as f:
                json.dump(details, f, indent=2)
            print(f"Saved company_details/batch.json for {len(COMPANY_IDS)} companies")
        else:
            print("No company IDs defined; skipping company details capture.")


async def capture_errors():
    """Placeholder for error responses (e.g., 403, 429)."""
    # These can be manually created if needed; the script doesn't generate them.
    pass


async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--endpoint",
        choices=["search", "job", "company", "all"],
        default="all",
        help="Which endpoint to capture",
    )
    args = parser.parse_args()

    # Create directories if they don't exist
    for d in [SEARCH_DIR, JOB_DETAILS_DIR, COMPANY_DETAILS_DIR, ERRORS_DIR]:
        d.mkdir(parents=True, exist_ok=True)

    if args.endpoint in ("search", "all"):
        print("Capturing search pages...")
        await capture_search_pages()

    if args.endpoint in ("job", "all"):
        print("Capturing job details...")
        await capture_job_details()

    if args.endpoint in ("company", "all"):
        print("Capturing company details...")
        await capture_company_details()

    print("Done.")


if __name__ == "__main__":
    asyncio.run(main())
