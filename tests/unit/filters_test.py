"""
Unit tests for the filters module.
"""

from datetime import datetime, timedelta, timezone

import pytest

from pywuzzuf.filters import AbsoluteDateFilter, DateRange, SearchFilters
from pywuzzuf.resources.jobs import _build_filter_payload


class TestDateRange:
    def test_since_returns_utc_datetime(self):
        dt = DateRange.LAST_24_HOURS.since()
        assert dt is not None
        assert dt.tzinfo == timezone.utc
        assert (datetime.now(timezone.utc) - dt) < timedelta(hours=24, seconds=1)

    def test_all_time_returns_none(self):
        assert DateRange.ALL_TIME.since() is None


class TestAbsoluteDateFilter:
    def test_valid_dates(self):
        since = datetime(2024, 1, 1, tzinfo=timezone.utc)
        until = datetime(2024, 1, 31, tzinfo=timezone.utc)
        f = AbsoluteDateFilter(since=since, until=until)
        assert f.since == since
        assert f.until == until

    def test_invalid_order_raises(self):
        since = datetime(2024, 2, 1, tzinfo=timezone.utc)
        until = datetime(2024, 1, 31, tzinfo=timezone.utc)
        with pytest.raises(ValueError):
            AbsoluteDateFilter(since=since, until=until)

    def test_warning_on_naive_datetime(self):
        with pytest.warns(UserWarning, match="tz-naive"):
            AbsoluteDateFilter(since=datetime(2024, 1, 1))


class TestSearchFilters:
    def test_posted_since_approximately_now_minus_24h(self):
        before = datetime.now(timezone.utc)
        f = SearchFilters(posted_within=DateRange.LAST_24_HOURS)
        after = datetime.now(timezone.utc)

        tolerance = timedelta(seconds=2)
        assert f.posted_since is not None
        assert (
            (before - timedelta(hours=24) - tolerance)
            <= f.posted_since
            <= (after - timedelta(hours=24) + tolerance)
        )

    def test_mixed_tz_does_not_raise(self):
        aware = AbsoluteDateFilter(since=datetime(2024, 1, 1, tzinfo=timezone.utc))
        aware_range = DateRange.LAST_24_HOURS
        SearchFilters(posted_within=aware, expires_after=aware_range)

    def test_has_date_filters(self):
        f1 = SearchFilters()
        assert not f1.has_date_filters()

        f2 = SearchFilters(posted_within=DateRange.LAST_WEEK)
        assert f2.has_date_filters()

    def test_keywords_tuple(self):
        f = SearchFilters(keywords=("python", "django"))
        assert f.keywords == ("python", "django")
        with pytest.raises(AttributeError):
            setattr(f, "keywords", ("new",))


@pytest.mark.parametrize(
    "filters,expected",
    [
        (
            SearchFilters(),
            {
                "posted_at_from": None,
                "posted_at_to": None,
                "expire_at_from": None,
                "country_id": None,
                "city_id": None,
                "career_level_id": None,
                "keywords": None,
            },
        ),
        (
            SearchFilters(posted_within=DateRange.LAST_24_HOURS),
            {
                "posted_at_from": (datetime.now(timezone.utc) - timedelta(hours=24)).strftime(
                    "%m/%d/%Y %H:%M:%S"
                ),
                "posted_at_to": None,
                "expire_at_from": None,
                "country_id": None,
                "city_id": None,
                "career_level_id": None,
                "keywords": None,
            },
        ),
        (
            SearchFilters(
                posted_within=AbsoluteDateFilter(
                    since=datetime(2025, 1, 1, tzinfo=timezone.utc),
                    until=datetime(2025, 1, 31, tzinfo=timezone.utc),
                )
            ),
            {
                "posted_at_from": "01/01/2025 00:00:00",
                "posted_at_to": "01/31/2025 00:00:00",
                "expire_at_from": None,
                "country_id": None,
                "city_id": None,
                "career_level_id": None,
                "keywords": None,
            },
        ),
        (
            SearchFilters(keywords=("python", "django")),
            {
                "posted_at_from": None,
                "posted_at_to": None,
                "expire_at_from": None,
                "country_id": None,
                "city_id": None,
                "career_level_id": None,
                "keywords": ["python", "django"],
            },
        ),
        (
            SearchFilters(country_id=1, city_id=2, career_level_id=3),
            {
                "posted_at_from": None,
                "posted_at_to": None,
                "expire_at_from": None,
                "country_id": 1,
                "city_id": 2,
                "career_level_id": 3,
                "keywords": None,
            },
        ),
        (
            SearchFilters(
                posted_within=AbsoluteDateFilter(
                    since=datetime(2025, 1, 1, tzinfo=timezone.utc),
                ),
                keywords=("python",),
                country_id=1,
            ),
            {
                "posted_at_from": "01/01/2025 00:00:00",
                "posted_at_to": None,
                "expire_at_from": None,
                "country_id": 1,
                "city_id": None,
                "career_level_id": None,
                "keywords": ["python"],
            },
        ),
    ],
)
def test_build_filter_payload(filters, expected):
    """
    Verify that _build_filter_payload correctly serializes SearchFilters
    into the API-expected payload structure.
    """
    payload = _build_filter_payload(filters)

    assert payload.posted_at_from == expected["posted_at_from"] or (
        expected["posted_at_from"] is not None
        and payload.posted_at_from is not None
        and abs(
            datetime.strptime(payload.posted_at_from, "%m/%d/%Y %H:%M:%S")
            - datetime.strptime(expected["posted_at_from"], "%m/%d/%Y %H:%M:%S")
        )
        < timedelta(seconds=2)
    )
    assert payload.posted_at_to == expected["posted_at_to"]
    assert payload.expire_at_from == expected["expire_at_from"]
    assert payload.country_id == expected["country_id"]
    assert payload.city_id == expected["city_id"]
    assert payload.career_level_id == expected["career_level_id"]
    assert payload.keywords == expected["keywords"]
