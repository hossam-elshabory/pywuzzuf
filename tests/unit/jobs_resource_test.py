import json
from pathlib import Path
from typing import cast

import pytest

from pywuzzuf.filters import SearchFilters
from pywuzzuf.models import (
    CompanyData,
    CompanyRelationship,
    JobAttributes,
    JobDetails,
    JobRelationships,
    Location,
    LocationCountry,
    Salary,
)
from pywuzzuf.resources.companies import CompaniesResource
from pywuzzuf.resources.jobs import JobsResource, _job_matches_filters


class TestJobsResource:
    @pytest.mark.asyncio
    async def test_search_jobs_returns_ids(self, mock_http):
        jobs = JobsResource(mock_http, cast(CompaniesResource, None))
        ids = await jobs._search_jobs("python", SearchFilters(), 0, 20)

        assert isinstance(ids, list)
        assert len(ids) > 0
        assert all(isinstance(i, str) for i in ids)

    @pytest.mark.asyncio
    async def test_fetch_job_details_returns_list(self, mock_http):
        jobs = JobsResource(mock_http, cast(CompaniesResource, None))

        fixture_path = Path(__file__).parent.parent / "fixtures" / "job_details" / "batch.json"
        with open(fixture_path) as f:
            fixture_data = json.load(f)

        if not fixture_data["data"]:
            pytest.skip("No job details in fixture")

        valid_ids = [j["id"] for j in fixture_data["data"]]

        details = await jobs._fetch_job_details(valid_ids)

        assert len(details) == len(valid_ids)
        assert all(isinstance(j, JobDetails) for j in details)

    def test_job_matches_filters(self):
        attrs = JobAttributes(
            title="Senior Python Developer",
            description="We need Python",
            salary=Salary(min=1, max=2),
            location=Location(country=LocationCountry(id=1, name="EG", code="EG")),
            posted_at=None,
            expire_at=None,
            keywords=[],
        )
        rels = JobRelationships(company=CompanyRelationship(data=CompanyData(type="company", id="c1")))
        job = JobDetails(type="job", id="123", attributes=attrs, relationships=rels)

        filters = SearchFilters(keywords=("python",))
        assert _job_matches_filters(job, filters) is True

        filters = SearchFilters(keywords=("java",))
        assert _job_matches_filters(job, filters) is False

        filters = SearchFilters(country_id=2)
        assert _job_matches_filters(job, filters) is False
