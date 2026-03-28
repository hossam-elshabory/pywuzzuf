"""
Pydantic v2 data models for Wuzzuf API responses.

This module defines the data structures used to represent and validate data
returned by the Wuzzuf API, including job listings and company details.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

logger = logging.getLogger("pywuzzuf.validation")


class NamedAttribute(BaseModel):
    """
    Structured enum-like object the API returns for some fields.

    Examples
    --------
    >>> NamedAttribute(id=1, name="EGP")
    >>> NamedAttribute(id=2, name="Monthly")

    Attributes
    ----------
    id : int
        The unique identifier for the attribute.
    name : str
        The human-readable name of the attribute.
    """

    model_config = ConfigDict(populate_by_name=True)

    id: int
    name: str


class DataQualityReport(BaseModel):
    """
    Non-raising anomaly record attached to every ``EnrichedJob``.

    Populated atomically by ``EnrichedJob._audit_quality`` after the model is
    fully constructed. Consumers can inspect ``has_anomalies`` to decide
    whether to skip, log, or surface the job for manual review.

    Attributes
    ----------
    missing_fields : list[str]
        Enrichment fields that are ``None`` due to a lookup failure or because
        the API relationship data was absent. Currently: ``company`` when
        company enrichment returned no data for this job's company ID.
    coerced_fields : list[str]
        Fields whose raw value was *present* but structurally transformed
        during parsing (e.g. the API returned a plain string ``"EGP"`` where a
        ``NamedAttribute`` object was expected).
    degraded_fields : list[str]
        Fields that resolved to ``None`` but whose absence is *ambiguous* —
        the API may have legitimately returned ``null``, or the raw value may
        have been unparseable.
    has_anomalies : bool
        Convenience flag — ``True`` when any of the three lists is non-empty.
    """

    model_config = ConfigDict(populate_by_name=True)

    missing_fields: list[str] = Field(default_factory=list)
    coerced_fields: list[str] = Field(default_factory=list)
    degraded_fields: list[str] = Field(default_factory=list)
    has_anomalies: bool = False


class CompanyAttributes(BaseModel):
    """
    Core attributes of a company.

    Attributes
    ----------
    name : str
        The legal name of the company.
    description : str, optional
        A brief description of the company's activities and history.
    website : str, optional
        The official website URL of the company.
    logo : str, optional
        The URL of the company's logo.
    established_year : str, optional
        The year the company was founded.
    """

    model_config = ConfigDict(populate_by_name=True)

    name: str
    description: str | None = None
    website: str | None = None
    logo: str | None = None
    established_year: str | None = Field(
        None, validation_alias="establishedYear", serialization_alias="establishedYear"
    )


class CompanyLinks(BaseModel):
    """
    Navigation links for a company resource.

    Attributes
    ----------
    self_url : str
        The internal API URL for this company.
    profile : str
        The public profile URL of the company on Wuzzuf.
    default_logo_url : str, optional
        A fallback URL for the company logo.
    """

    model_config = ConfigDict(populate_by_name=True)

    self_url: str = Field(validation_alias="self", serialization_alias="self")
    profile: str
    default_logo_url: str | None = Field(
        None, validation_alias="defaultLogoUrl", serialization_alias="defaultLogoUrl"
    )


class Company(BaseModel):
    """
    Full company record.

    Attributes
    ----------
    type : str
        The resource type (always "company").
    id : str
        The unique company identifier.
    attributes : CompanyAttributes
        The company's core metadata.
    links : CompanyLinks
        Associated links and resources for the company.
    """

    model_config = ConfigDict(populate_by_name=True)

    type: str
    id: str
    attributes: CompanyAttributes
    links: CompanyLinks


class Salary(BaseModel):
    """
    Job salary details.

    Attributes
    ----------
    min : int, optional
        The minimum salary offered.
    max : int, optional
        The maximum salary offered.
    currency : NamedAttribute | str | None
        The salary currency (e.g., EGP, USD). Normalised to NamedAttribute if
        possible.
    period : NamedAttribute | str | None
        The pay period (e.g., Monthly, Yearly). Normalised to NamedAttribute if
        possible.
    is_paid : bool
        Whether the position is a paid role. Defaults to False.
    """

    model_config = ConfigDict(populate_by_name=True)

    min: int | None = None
    max: int | None = None
    currency: NamedAttribute | str | None = None
    period: NamedAttribute | str | None = None
    is_paid: bool = Field(default=False, validation_alias="isPaid", serialization_alias="isPaid")

    @field_validator("currency", "period", mode="before")
    @classmethod
    def _coerce_named_or_str(cls, v: Any) -> NamedAttribute | str | None:
        """Coerce raw values to NamedAttribute or preserved string."""
        if v is None:
            return None
        if isinstance(v, dict):
            try:
                return NamedAttribute.model_validate(v)
            except Exception:
                return str(v)
        return v


class Keyword(BaseModel):
    """
    Search keyword or skill tag.

    Attributes
    ----------
    name : str
        The keyword text (e.g., "Python").
    browse_page : str
        The relative URL for browsing jobs with this keyword.
    """

    model_config = ConfigDict(populate_by_name=True)

    name: str
    browse_page: str = Field(validation_alias="browsePage", serialization_alias="browsePage")


class LocationCountry(BaseModel):
    """
    Country location details.

    Attributes
    ----------
    id : int
        The country's unique ID.
    name : str
        The full country name.
    code : str
        The ISO alpha-2 country code.
    """

    model_config = ConfigDict(populate_by_name=True)

    id: int
    name: str
    code: str


class LocationCity(BaseModel):
    """
    City location details.

    Attributes
    ----------
    id : int
        The city's unique ID.
    name : str
        The city name.
    latitude : str, optional
        Geographic latitude as a string.
    longitude : str, optional
        Geographic longitude as a string.
    """

    model_config = ConfigDict(populate_by_name=True)

    id: int
    name: str
    latitude: str | None = None
    longitude: str | None = None


class LocationArea(BaseModel):
    """
    Area or neighborhood details.

    Attributes
    ----------
    id : int
        The area's unique ID.
    name : str
        The area or district name.
    latitude : str, optional
        Geographic latitude as a string.
    longitude : str, optional
        Geographic longitude as a string.
    """

    model_config = ConfigDict(populate_by_name=True)

    id: int
    name: str
    latitude: str | None = None
    longitude: str | None = None


class Location(BaseModel):
    """
    Job location hierarchy.

    Attributes
    ----------
    country : LocationCountry
        The country where the job is based.
    city : LocationCity, optional
        The specific city.
    area : LocationArea, optional
        The specific area or district.
    """

    model_config = ConfigDict(populate_by_name=True)

    country: LocationCountry
    city: LocationCity | None = None
    area: LocationArea | None = None


class WorkExperience(BaseModel):
    """
    Required work experience range.

    Attributes
    ----------
    min : int, optional
        Minimum years of experience required.
    max : int, optional
        Maximum years of experience requested.
    """

    model_config = ConfigDict(populate_by_name=True)

    min: int | None = None
    max: int | None = None


class CareerLevel(BaseModel):
    """
    Required career seniority level.

    Attributes
    ----------
    id : int
        The career level ID.
    name : str
        The short name of the career level (e.g., "Experienced").
    hint : str, optional
        A longer human-readable description of the level.
    browse_page : str, optional
        The relative URL for browsing jobs at this career level.
    """

    model_config = ConfigDict(populate_by_name=True)

    id: int
    name: str
    hint: str | None = None
    browse_page: str | None = Field(
        None, validation_alias="browsePage", serialization_alias="browsePage"
    )


def _normalize_datetime(v: Any, field_name: str) -> datetime | None:
    """Coerce a raw value to a tz-aware UTC ``datetime``."""
    if v is None:
        return None
    if isinstance(v, datetime):
        if v.tzinfo is None:
            logger.debug("Coercing tz-naive datetime to UTC on field %r.", field_name)
            return v.replace(tzinfo=timezone.utc)
        return v

    raw = str(v)

    try:
        dt = datetime.fromisoformat(raw)
        if dt.tzinfo is None:
            logger.debug("Coercing tz-naive ISO string to UTC on field %r.", field_name)
            return dt.replace(tzinfo=timezone.utc)
        return dt
    except (ValueError, TypeError):
        pass

    try:
        dt = datetime.strptime(raw, "%m/%d/%Y %H:%M:%S")
        return dt.replace(tzinfo=timezone.utc)
    except (ValueError, TypeError):
        pass

    logger.warning("Unparseable datetime %r on field %r — defaulting to None.", v, field_name)
    return None


class JobAttributes(BaseModel):
    """
    Core metadata for a job listing.

    Attributes
    ----------
    title : str
        The job title.
    description : str
        The full job description and duties.
    requirements : str, optional
        The qualifications and requirements for the role.
    salary : Salary
        Salary information.
    keywords : list[Keyword]
        List of relevant keywords and skills.
    career_level : CareerLevel, optional
        The required career seniority level.
    location : Location
        The geographic location of the job.
    work_experience_years : WorkExperience
        The required range of work experience.
    vacancies : int
        The number of open positions. Defaults to 0.
    posted_at : datetime, optional
        The date and time the job was posted (UTC).
    expire_at : datetime, optional
        The date and time the listing expires (UTC).
    """

    model_config = ConfigDict(populate_by_name=True)

    title: str
    description: str
    requirements: str | None = None
    salary: Salary
    keywords: list[Keyword] = Field(default_factory=list)
    career_level: CareerLevel | None = Field(
        None, validation_alias="careerLevel", serialization_alias="careerLevel"
    )
    location: Location
    work_experience_years: WorkExperience = Field(
        default_factory=WorkExperience,
        validation_alias="workExperienceYears",
        serialization_alias="workExperienceYears",
    )
    vacancies: int = 0
    posted_at: datetime | None = Field(
        None, validation_alias="postedAt", serialization_alias="postedAt"
    )
    expire_at: datetime | None = Field(
        None, validation_alias="expireAt", serialization_alias="expireAt"
    )

    @field_validator("posted_at", mode="before")
    @classmethod
    def _parse_posted_at(cls, v: Any) -> datetime | None:
        return _normalize_datetime(v, "posted_at")

    @field_validator("expire_at", mode="before")
    @classmethod
    def _parse_expire_at(cls, v: Any) -> datetime | None:
        return _normalize_datetime(v, "expire_at")


class CompanyData(BaseModel):
    """
    Reference to a company in a relationship object.

    Attributes
    ----------
    type : str
        The resource type ("company").
    id : str
        The unique company identifier.
    """

    model_config = ConfigDict(populate_by_name=True)

    type: str
    id: str


class CompanyRelationship(BaseModel):
    """
    Wraps the company relationship data.

    Attributes
    ----------
    data : CompanyData, optional
        The reference to the company.
    """

    model_config = ConfigDict(populate_by_name=True)

    data: CompanyData | None = None


class JobRelationships(BaseModel):
    """
    Linkages between a job and other entities.

    Attributes
    ----------
    company : CompanyRelationship
        The company offering this job.
    """

    model_config = ConfigDict(populate_by_name=True)

    company: CompanyRelationship


class JobDetails(BaseModel):
    """
    The base model for a job as returned by the /api/job endpoint.

    Attributes
    ----------
    type : str
        The resource type (always "job").
    id : str
        The unique job identifier.
    attributes : JobAttributes
        The job's core metadata.
    relationships : JobRelationships
        Associations with other entities (like company).
    """

    model_config = ConfigDict(populate_by_name=True)

    type: str
    id: str
    attributes: JobAttributes
    relationships: JobRelationships


class EnrichedJob(JobDetails):
    """
    A ``JobDetails`` record augmented with full ``Company`` data.

    This is the primary model used by end-users. It combines the raw job
    details with enriched company information and a quality audit.

    Attributes
    ----------
    company : Company, optional
        Full details of the hiring company. None if enrichment failed.
    quality : DataQualityReport
        A report detailing any data anomalies or parsing issues.
    """

    model_config = ConfigDict(populate_by_name=True)

    company: Company | None = None
    quality: DataQualityReport = Field(default_factory=DataQualityReport)

    @model_validator(mode="after")
    def _audit_quality(self) -> "EnrichedJob":
        """Build a ``DataQualityReport`` atomically and assign it once."""
        missing: list[str] = []
        coerced: list[str] = []
        degraded: list[str] = []

        attrs = self.attributes

        if self.company is None:
            missing.append("company")

        if isinstance(attrs.salary.currency, str):
            coerced.append("attributes.salary.currency")
        if isinstance(attrs.salary.period, str):
            coerced.append("attributes.salary.period")

        if attrs.posted_at is None:
            degraded.append("attributes.posted_at")
        if attrs.expire_at is None:
            degraded.append("attributes.expire_at")

        has_anomalies = bool(missing or coerced or degraded)

        report = DataQualityReport(
            missing_fields=missing,
            coerced_fields=coerced,
            degraded_fields=degraded,
            has_anomalies=has_anomalies,
        )

        if has_anomalies:
            logger.debug(
                "Job %r anomalies — missing: %s, coerced: %s, degraded: %s",
                self.id,
                missing,
                coerced,
                degraded,
            )

        self.quality = report
        return self


class SearchResult(BaseModel):
    """
    Minimal job reference returned by the search endpoint.

    Attributes
    ----------
    id : str
        The unique job identifier.
    """

    model_config = ConfigDict(populate_by_name=True)

    id: str


class SearchResponse(BaseModel):
    """
    Top-level response from /api/search/job.

    Attributes
    ----------
    data : list[SearchResult]
        The list of job references matching the search.
    """

    model_config = ConfigDict(populate_by_name=True)

    data: list[SearchResult]


class JobDetailsResponse(BaseModel):
    """
    Top-level response from batch /api/job fetches.

    Attributes
    ----------
    data : list[JobDetails]
        The list of full job details.
    """

    model_config = ConfigDict(populate_by_name=True)

    data: list[JobDetails]


class CompanyDetailsResponse(BaseModel):
    """
    Top-level response from batch /api/company fetches.

    Attributes
    ----------
    data : list[Company]
        The list of full company details.
    """

    model_config = ConfigDict(populate_by_name=True)

    data: list[Company]


class SearchFilterPayload(BaseModel):
    """
    Internal serialization of ``SearchFilters`` for the API request body.

    Attributes
    ----------
    posted_at_from : str, optional
        Start date filter in MM/DD/YYYY HH:MM:SS format.
    posted_at_to : str, optional
        End date filter in MM/DD/YYYY HH:MM:SS format.
    expire_at_from : str, optional
        Expiration date filter in MM/DD/YYYY HH:MM:SS format.
    country_id : int, optional
        Country identifier filter.
    city_id : int, optional
        City identifier filter.
    career_level_id : int, optional
        Career level identifier filter.
    keywords : list[str], optional
        List of keywords to search for.
    """

    model_config = ConfigDict(populate_by_name=True)

    posted_at_from: str | None = Field(
        None, validation_alias="postedAtFrom", serialization_alias="postedAtFrom"
    )
    posted_at_to: str | None = Field(
        None, validation_alias="postedAtTo", serialization_alias="postedAtTo"
    )
    expire_at_from: str | None = Field(
        None, validation_alias="expireAtFrom", serialization_alias="expireAtFrom"
    )
    country_id: int | None = Field(None, validation_alias="countryId", serialization_alias="countryId")
    city_id: int | None = Field(None, validation_alias="cityId", serialization_alias="cityId")
    career_level_id: int | None = Field(
        None, validation_alias="careerLevelId", serialization_alias="careerLevelId"
    )
    keywords: list[str] | None = Field(
        None, validation_alias="keywords", serialization_alias="keywords"
    )


class SearchPayload(BaseModel):
    """
    Outgoing POST body for ``/api/search/job``.

    Attributes
    ----------
    start_index : int
        The offset for pagination. Defaults to 0.
    page_size : int
        The number of results to return. Defaults to 20.
    longitude : str
        Geographic longitude. Defaults to "0".
    latitude : str
        Geographic latitude. Defaults to "0".
    query : str
        The search query string.
    search_filters : SearchFilterPayload
        The filters to apply to the search.
    sort_by : str
        The sorting criteria. Defaults to "date".
    """

    model_config = ConfigDict(populate_by_name=True)

    start_index: int = Field(0, validation_alias="startIndex", serialization_alias="startIndex")
    page_size: int = Field(20, validation_alias="pageSize", serialization_alias="pageSize")
    longitude: str = "0"
    latitude: str = "0"
    query: str
    search_filters: SearchFilterPayload = Field(
        default_factory=SearchFilterPayload,
        validation_alias="searchFilters",
        serialization_alias="searchFilters",
    )
    sort_by: str = Field("date", validation_alias="sortBy", serialization_alias="sortBy")
