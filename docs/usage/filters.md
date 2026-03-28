---
icon: material/filter
---

# Filtering & Precision

PyWuzzuf provides a type-safe filtering system via the `SearchFilters` container. It allows you to narrow down search results based on time, location, and metadata.

!!! warning "API Search Relevance & Trade-offs"
    The Wuzzuf API uses "soft matching". Results may drift into irrelevance after the first few pages (e.g., matching a keyword in the description rather than the title).

    PyWuzzuf enforces accuracy via **Client-Side Filtering**. It fetches full job details and applies your criteria locally before returning results.

    **Key Trade-offs:**

    | Benefit | Cost |
    | :--- | :--- |
    | **Guaranteed Accuracy** | **Network Overhead**: Fetches details for jobs that may be filtered out. |
    | **Strict Date Matching** | **Result Counts**: API totals may not match the number of items returned. |

## The SearchFilters Container

`SearchFilters` is an **immutable dataclass**. Once created, it cannot be modified. This design ensures that your filter criteria remain constant throughout a pagination run, preventing race conditions or "time drift" in long-running scripts.

```python
from pywuzzuf import SearchFilters

# Create a filter instance
filters = SearchFilters(country_id=1)

# filters.country_id = 2  <- Raises FrozenInstanceError
```

## Time Window Filters

You can filter jobs by when they were posted (`posted_within`) or when they expire (`expires_after`). PyWuzzuf offers two ways to define these windows.

### Relative Windows: DateRange

Use `DateRange` for sliding windows relative to the current time (UTC). This is the most common approach for "Freshness" filtering.

```python
from pywuzzuf import SearchFilters, DateRange

# Jobs posted in the last 24 hours
filters = SearchFilters(posted_within=DateRange.LAST_24_HOURS)

# Jobs posted in the last month
filters = SearchFilters(posted_within=DateRange.LAST_MONTH)
```

**Available Ranges:**

- `LAST_24_HOURS`
- `LAST_3_DAYS`
- `LAST_WEEK`
- `LAST_2_WEEKS`
- `LAST_MONTH`
- `ALL_TIME` (Default)

!!! tip "Time Snapshotting"
    The `DateRange` is resolved to a specific UTC timestamp the moment `SearchFilters` is instantiated. If you create a filter at 10:00 AM and use it for an hour-long pagination run, the "Start Time" remains 10:00 AM, ensuring consistent results.

### Absolute Windows: AbsoluteDateFilter

For precise boundaries (e.g., "Jobs posted in Q1 2024"), use `AbsoluteDateFilter`.

```python
from datetime import datetime, timezone
from pywuzzuf import SearchFilters, AbsoluteDateFilter

# Define a fixed window
q1_filter = AbsoluteDateFilter(
    since=datetime(2024, 1, 1, tzinfo=timezone.utc),
    until=datetime(2024, 3, 31, tzinfo=timezone.utc)
)

filters = SearchFilters(posted_within=q1_filter)
```

!!! warning "Timezone Awareness"
    `AbsoluteDateFilter` requires timezone-aware `datetime` objects. If you pass a naive datetime (without `tzinfo`), PyWuzzuf will assume UTC but emit a warning.

## Location & Metadata Filters

You can filter by Country, City, and Career Level using their internal Wuzzuf IDs.

```python
filters = SearchFilters(
    country_id=1,     # e.g., Egypt
    city_id=1545,     # e.g., Cairo
    career_level_id=3 # e.g., Experienced
)
```

### Discovering IDs

PyWuzzuf does not currently include a helper method to list all available IDs. To find the correct ID for a specific location or level:

1.  Perform a search on the Wuzzuf website with your desired filters.
2.  Inspect the Network tab in your browser's Developer Tools.
3.  Look for the request payload to the `/api/search/job` endpoint.
4.  Extract the `countryId`, `cityId`, or `careerLevelId` from the JSON payload.

!!! info "Future Improvement"
    This manual lookup process is temporary. Future versions of PyWuzzuf aim to provide streamlined access to location and metadata IDs directly within the library, similar to how `DateRange` works today.

## Keyword Constraints

While the `.search("query")` method performs a broad text match, you can also enforce strict keyword constraints via filters.

```python
# Only return jobs that explicitly contain "Django" AND "AWS"
filters = SearchFilters(keywords=("Django", "AWS"))

result = await client.jobs.search("Python").filter(filters).all()
```

**How it works:**

These keywords are applied to filter the search results. If the API supports these keywords directly, they are sent in the payload. Additionally, the client performs a secondary check to ensure returned jobs match the provided keywords, guaranteeing precision.

## Next Steps

Now that you can refine your search queries, learn how to manage the flow of large result sets efficiently.

**[Go to Pagination Docs :octicons-arrow-right-24:](usage/pagination.md)**
