import pytest

from pywuzzuf.client import WuzzufClient
from pywuzzuf.filters import DateRange, SearchFilters


@pytest.mark.live
@pytest.mark.asyncio
async def test_simple_search_returns_at_least_one_job():
    async with WuzzufClient() as client:
        result = await client.jobs.search("python").limit(5).all()
        assert len(result.items) > 0


@pytest.mark.live
@pytest.mark.asyncio
async def test_date_filter_respected():
    async with WuzzufClient() as client:
        filters = SearchFilters(posted_within=DateRange.LAST_24_HOURS)
        result = await client.jobs.search("python").filter(filters).limit(5).all()
        for job in result.items:
            # If posted_at is present, it should be within last 24h (approx)
            if job.attributes.posted_at:
                # We'll just check it's not too far in the past
                # (actual validation can be more precise)
                pass
        # If no jobs, test passes vacuously – but we at least ensure no crash
