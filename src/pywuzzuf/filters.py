"""
Date filtering and search constraints for the Wuzzuf client.

Design decisions
----------------
* ``DateRange`` covers the common relative-offset cases via ``timedelta``.
* ``AbsoluteDateFilter`` handles arbitrary datetime windows for power users.
* ``SearchFilters`` is a **frozen dataclass** — immutable once constructed, safe
  to reuse across paginated requests without defensive copying.
* Datetimes are **snapshotted at construction time** so a filter reused across
  multiple pagination pages always refers to the same window.
* ``keywords`` is a ``tuple`` (not a list) to enforce true immutability on the
  frozen dataclass.
* Mixed tz-naive/tz-aware datetime comparison is handled by coercing both sides
  to UTC before comparing rather than letting Python raise ``TypeError``.
  ``AbsoluteDateFilter`` still emits a warning when tz-naive datetimes
  are provided so callers can fix their code.
* The logically-suspect warning that previously fired on common valid
  combinations (``posted_within=LAST_WEEK`` + ``expires_after=LAST_3_DAYS``)
  has been removed — the comparison semantics (lower bounds, not event
  timestamps) make any such "suspect" check incorrect.
"""

from __future__ import annotations

import warnings
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Union, cast


class DateRange(Enum):
    """
    Pre-defined relative date windows resolved against UTC now.

    These ranges provide a convenient way to filter jobs by their posting or
    expiry dates relative to the current time.

    Examples
    --------
    >>> DateRange.LAST_WEEK.since()
    datetime.datetime(2024, ..., tzinfo=datetime.timezone.utc)
    """

    LAST_24_HOURS = timedelta(hours=24)
    LAST_3_DAYS = timedelta(days=3)
    LAST_WEEK = timedelta(weeks=1)
    LAST_2_WEEKS = timedelta(weeks=2)
    LAST_MONTH = timedelta(days=30)
    ALL_TIME = None  # sentinel — no date filter

    def since(self) -> datetime | None:
        """Return the UTC datetime representing the start of this range."""
        if self.value is None:
            return None
        return datetime.now(tz=timezone.utc) - cast(timedelta, self.value)


@dataclass(frozen=True)
class AbsoluteDateFilter:
    """
    Fixed datetime boundaries for precise filtering.

    Unlike ``DateRange``, this filter uses specific start and end points
    that do not change relative to the current time.

    Parameters
    ----------
    since : datetime.datetime, optional
        Only return items after this date. Defaults to None.
    until : datetime.datetime, optional
        Only return items before this date. Defaults to None.

    Examples
    --------
    >>> from datetime import datetime, timezone
    >>> f = AbsoluteDateFilter(
    ...     since=datetime(2024, 1, 1, tzinfo=timezone.utc),
    ...     until=datetime(2024, 3, 31, tzinfo=timezone.utc),
    ... )
    """

    since: datetime | None = None
    until: datetime | None = None

    def __post_init__(self) -> None:
        if (
            self.since is not None
            and self.until is not None
            and _to_utc(self.since) > _to_utc(self.until)
        ):
            raise ValueError(
                f"AbsoluteDateFilter: `since` ({self.since!r}) must be before `until` ({self.until!r})."
            )
        for name, val in (("since", self.since), ("until", self.until)):
            if val is not None and val.tzinfo is None:
                warnings.warn(
                    f"AbsoluteDateFilter.{name} is tz-naive. "
                    "It will be treated as UTC by the client. "
                    "Pass a tz-aware datetime (e.g., use timezone.utc) to be explicit.",
                    stacklevel=3,
                )


DateFilterType = Union[DateRange, AbsoluteDateFilter]


def _resolve_since(f: DateFilterType) -> datetime | None:
    """Extract the effective 'not before' datetime from either filter type."""
    if isinstance(f, DateRange):
        return f.since()
    res = f.since
    return _to_utc(res) if res is not None else None


def _resolve_until(f: DateFilterType) -> datetime | None:
    """Extract the effective 'not after' datetime from either filter type."""
    if isinstance(f, DateRange):
        return None
    res = f.until
    return _to_utc(res) if res is not None else None


def _to_utc(dt: datetime) -> datetime:
    """Return ``dt`` as a tz-aware UTC datetime."""
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


@dataclass(frozen=True)
class SearchFilters:
    """
    Immutable container for search constraints.

    All date-based filters are snapshotted at construction time. This ensures
    that long-running pagination processes always refer to the same temporal
    window, preventing items from "shifting" across pages as time passes.

    Parameters
    ----------
    posted_within : DateRange or AbsoluteDateFilter, optional
        Only return jobs posted within this window.
        Defaults to ``DateRange.ALL_TIME``.
    expires_after : DateRange or AbsoluteDateFilter, optional
        Only return jobs whose expiry date is after this window's lower bound.
        Defaults to ``DateRange.ALL_TIME``.
    keywords : tuple[str, ...], optional
        A tuple of keyword strings to narrow the search. Defaults to ().
    country_id : int, optional
        Wuzzuf country ID. Defaults to None.
    city_id : int, optional
        Wuzzuf city ID. Defaults to None.
    career_level_id : int, optional
        Wuzzuf career level ID. Defaults to None.

    Attributes
    ----------
    posted_since : datetime.datetime, optional
        The snapshotted UTC lower bound for job posting date.
    posted_until : datetime.datetime, optional
        The snapshotted UTC upper bound for job posting date.
    expires_since : datetime.datetime, optional
        The snapshotted UTC lower bound for job expiry date.
    """

    posted_within: DateFilterType = DateRange.ALL_TIME
    expires_after: DateFilterType = DateRange.ALL_TIME
    keywords: tuple[str, ...] = ()
    country_id: int | None = None
    city_id: int | None = None
    career_level_id: int | None = None

    _posted_since: datetime | None = field(
        init=False, default=None, repr=False, compare=False, hash=False
    )
    _posted_until: datetime | None = field(
        init=False, default=None, repr=False, compare=False, hash=False
    )
    _expires_since: datetime | None = field(
        init=False, default=None, repr=False, compare=False, hash=False
    )

    def __post_init__(self) -> None:
        """Resolve all relative durations into absolute UTC timestamps."""
        object.__setattr__(self, "_posted_since", _resolve_since(self.posted_within))
        object.__setattr__(self, "_posted_until", _resolve_until(self.posted_within))
        object.__setattr__(self, "_expires_since", _resolve_since(self.expires_after))

    @property
    def posted_since(self) -> datetime | None:
        return self._posted_since

    @property
    def posted_until(self) -> datetime | None:
        return self._posted_until

    @property
    def expires_since(self) -> datetime | None:
        return self._expires_since

    def has_date_filters(self) -> bool:
        """Check if any date-based constraints are currently active."""
        return any(v is not None for v in (self._posted_since, self._posted_until, self._expires_since))
