import pytest

from pywuzzuf.models import Company
from pywuzzuf.resources.companies import CompaniesResource


@pytest.mark.asyncio
class TestCompaniesResource:
    async def test_fetch_by_ids_returns_map(self, mock_http):
        companies = CompaniesResource(mock_http)
        import json
        from pathlib import Path

        fixture_path = Path(__file__).parent.parent / "fixtures" / "company_details" / "batch.json"
        with open(fixture_path) as f:
            fixture_data = json.load(f)

        if not fixture_data["data"]:
            pytest.skip("No company data in fixture")

        valid_ids = [c["id"] for c in fixture_data["data"]]

        result = await companies.fetch_by_ids(valid_ids)

        assert len(result) == len(valid_ids)
        first_id = valid_ids[0]
        assert isinstance(result[first_id], Company)
        # Check that attributes are populated
        assert result[first_id].attributes.name is not None

    async def test_missing_ids_absent_from_map(self, mock_http):
        companies = CompaniesResource(mock_http)
        # This test is still valid and robust
        result = await companies.fetch_by_ids(["9999"])
        assert result == {}
