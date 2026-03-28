---
icon: material/database
---

# Data Models Reference

This page documents the data structures returned by the PyWuzzuf client. All models are implemented as Pydantic `BaseModel` classes, providing type safety and IDE autocompletion.

## The Root Object: `EnrichedJob`

This is the primary object returned by all search operations. It bundles the core job details with the hydrated company data and a data quality report.

### Handling Nullable Data

!!! warning "Data Completeness"
    Job listings depend entirely on the recruiter filling out the job post on Wuzzuf. **Many fields may be `None`**, including `company`, `requirements`, `salary`, and `city`.

    Always use defensive checks when accessing nested attributes.

**Safe Access Pattern:**

```python
# ❌ Unsafe: Will crash if company is None
print(job.company.attributes.name)

# ✅ Safe: Explicit check
if job.company:
    print(job.company.attributes.name)
else:
    print("Company not disclosed")
```

### Access Paths

| Field | Type | Access Path | Nullable? |
| :--- | :--- | :--- | :--- |
| **ID** | `str` | `job.id` | No |
| **Title** | `str` | `job.attributes.title` | No |
| **Description** | `str` | `job.attributes.description` | No |
| **Company Name** | `str` | `job.company.attributes.name` | **Yes** (via `job.company`) |
| **City** | `str` | `job.attributes.location.city.name` | **Yes** |
| **Posted At** | `datetime` | `job.attributes.posted_at` | **Yes** |

---

## Job Details

The `job.attributes` object contains the core metadata of the listing.

### Location

Location is a nested object containing Country, City, and Area.

```python
loc = job.attributes.location

# Country is always present
country = loc.country.name  # "Egypt"

# City and Area are optional
city_name = loc.city.name if loc.city else "Remote / Unspecified"
area_name = loc.area.name if loc.area else None
```

**Structure:**

| Field | Type | Nullable? | Description |
| :--- | :--- | :--- | :--- |
| `country` | `LocationCountry` | No | Contains `id`, `name`, `code`. |
| `city` | `LocationCity` | **Yes** | Contains `id`, `name`, `lat/long`. |
| `area` | `LocationArea` | **Yes** | Contains `id`, `name`, `lat/long`. |

### Salary

Salary information is often optional or partially filled by recruiters.

```python
salary = job.attributes.salary

if salary and salary.min:
    print(f"Range: {salary.min} - {salary.max}")
    # Currency can be a NamedAttribute or a raw str
    currency = salary.currency.name if hasattr(salary.currency, 'name') else str(salary.currency)
    print(f"Currency: {currency}")
else:
    print("Salary not disclosed.")
```

**Structure:**

| Field | Type | Nullable? | Description |
| :--- | :--- | :--- | :--- |
| `min` | `int` | **Yes** | Minimum salary value. |
| `max` | `int` | **Yes** | Maximum salary value. |
| `currency` | `NamedAttribute` | **Yes** | e.g., `{id: 1, name: "EGP"}`. |
| `period` | `NamedAttribute` | **Yes** | e.g., `{id: 1, name: "Monthly"}`. |
| `is_paid` | `bool` | No | False for unpaid internships. |

### Dates & Metadata

| Field | Type | Access Path | Nullable? | Description |
| :--- | :--- | :--- | :--- | :--- |
| `posted_at` | `datetime` | `job.attributes.posted_at` | **Yes** | UTC timestamp. |
| `expire_at` | `datetime` | `job.attributes.expire_at` | **Yes** | UTC timestamp. |
| `keywords` | `list[Keyword]` | `job.attributes.keywords` | No | List of skills/tags (can be empty). |
| `vacancies` | `int` | `job.attributes.vacancies` | No | Number of open positions. Default: 0. |

---

## Company Details

The `job.company` object provides full company metadata.

!!! warning "Enrichment Failure"
    This object is `None` if enrichment failed or the company data was not found in the API. **Always check for existence.**

```python
if job.company:
    attrs = job.company.attributes
    print(f"Company: {attrs.name}")
    print(f"Website: {attrs.website}")
else:
    print("Company data not available.")
```

**Structure (`CompanyAttributes`):**

| Field | Type | Nullable? | Description |
| :--- | :--- | :--- | :--- |
| `name` | `str` | No | Company name. |
| `description` | `str` | **Yes** | Profile text. |
| `website` | `str` | **Yes** | Official URL. |
| `logo` | `str` | **Yes** | Logo URL. |

---

## Data Quality Report

Every `EnrichedJob` comes with a `quality` attribute that reports on the integrity of the data. This is useful for filtering out incomplete records.

```python
if job.quality.has_anomalies:
    # Skip jobs with critical missing data
    if "company" in job.quality.missing_fields:
        continue
```

**Report Attributes:**

| Field | Type | Description |
| :--- | :--- | :--- |
| `missing_fields` | `list[str]` | Fields missing due to failed enrichment (e.g., `company`). |
| `degraded_fields` | `list[str]` | Fields that resolved to `None` ambiguously (e.g., `posted_at`). |
| `has_anomalies` | `bool` | `True` if any anomalies were detected. |

## Next Steps

Learn how to handle data inconsistencies and API errors at scale.

**[Go to Resilience Docs :octicons-arrow-right-24:](../usage/resilience.md)**
