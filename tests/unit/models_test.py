from datetime import datetime, timezone

import pytest

from pywuzzuf.models import (
    EnrichedJob,
    NamedAttribute,
    Salary,
    _normalize_datetime,
)


class TestSalaryCoercion:
    def test_currency_as_dict_becomes_namedattribute(self):
        raw = {"min": 1000, "max": 2000, "currency": {"id": 1, "name": "EGP"}}
        s = Salary.model_validate(raw)
        assert isinstance(s.currency, NamedAttribute)
        assert s.currency.id == 1
        assert s.currency.name == "EGP"

    def test_currency_as_string_becomes_str(self):
        raw = {"min": 1000, "max": 2000, "currency": "EGP"}
        s = Salary.model_validate(raw)
        assert isinstance(s.currency, str)
        assert s.currency == "EGP"


class TestDatetimeNormalization:
    def test_iso_string_utc(self):
        dt = _normalize_datetime("2025-03-16T10:00:00+00:00", "test")
        assert dt == datetime(2025, 3, 16, 10, 0, tzinfo=timezone.utc)

    def test_naive_iso_becomes_utc(self):
        dt = _normalize_datetime("2025-03-16T10:00:00", "test")
        assert dt == datetime(2025, 3, 16, 10, 0, tzinfo=timezone.utc)

    def test_wuzzuf_format(self):
        dt = _normalize_datetime("03/16/2025 10:00:00", "test")
        assert dt == datetime(2025, 3, 16, 10, 0, tzinfo=timezone.utc)

    def test_unparseable_returns_none(self):
        dt = _normalize_datetime("garbage", "test")
        assert dt is None


class TestEnrichedJobQualityReport:
    @pytest.fixture
    def base_job_dict(self):
        return {
            "type": "job",
            "id": "123",
            "attributes": {
                "title": "Test",
                "description": "desc",
                "salary": {"min": 1, "max": 2},
                "location": {"country": {"id": 1, "name": "EG", "code": "EG"}},
                "posted_at": "03/16/2025 10:00:00",
                "expire_at": "04/16/2025 10:00:00",
            },
            "relationships": {"company": {"data": {"type": "company", "id": "c1"}}},
        }

    def test_no_anomalies(self, base_job_dict):
        job = EnrichedJob.model_validate(
            {
                **base_job_dict,
                "company": {
                    "type": "company",
                    "id": "c1",
                    "attributes": {"name": "C"},
                    "links": {
                        "self": "/company/c1",
                        "profile": "/company/c",
                        "default_logo_url": None,
                    },
                },
            }
        )
        assert not job.quality.has_anomalies
        assert job.quality.missing_fields == []
        assert job.quality.coerced_fields == []
        assert job.quality.degraded_fields == []

    def test_missing_company(self, base_job_dict):
        job = EnrichedJob.model_validate({**base_job_dict, "company": None})
        assert job.quality.has_anomalies
        assert "company" in job.quality.missing_fields

    def test_coerced_salary_currency(self, base_job_dict):
        d = base_job_dict.copy()
        d["attributes"]["salary"]["currency"] = "EGP"  # string, not dict
        job = EnrichedJob.model_validate(
            {
                **d,
                "company": {
                    "type": "company",
                    "id": "c1",
                    "attributes": {"name": "C"},
                    "links": {
                        "self": "/company/c1",
                        "profile": "/company/c",
                        "default_logo_url": None,
                    },
                },
            }
        )
        assert job.quality.has_anomalies
        assert "attributes.salary.currency" in job.quality.coerced_fields

    def test_degraded_posted_at(self, base_job_dict):
        d = base_job_dict.copy()
        d["attributes"]["posted_at"] = None
        job = EnrichedJob.model_validate(
            {
                **d,
                "company": {
                    "type": "company",
                    "id": "c1",
                    "attributes": {"name": "C"},
                    "links": {
                        "self": "/company/c1",
                        "profile": "/company/c",
                        "default_logo_url": None,
                    },
                },
            }
        )
        assert job.quality.has_anomalies
        assert "attributes.posted_at" in job.quality.degraded_fields

    def test_requirements_and_career_level_not_tracked(self, base_job_dict):
        # Even if missing, they should not appear in any anomaly list
        d = base_job_dict.copy()
        d["attributes"]["requirements"] = None
        d["attributes"]["career_level"] = None
        job = EnrichedJob.model_validate(
            {
                **d,
                "company": {
                    "type": "company",
                    "id": "c1",
                    "attributes": {"name": "C"},
                    "links": {
                        "self": "/company/c1",
                        "profile": "/company/c",
                        "default_logo_url": None,
                    },
                },
            }
        )
        assert not job.quality.has_anomalies
        assert "requirements" not in job.quality.missing_fields
        assert "career_level" not in job.quality.missing_fields
