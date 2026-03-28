---
icon: material/rocket-launch
---

# Quickstart

## 1. The Basic Search

The simplest way to search is to initialize the client and call the search endpoint. PyWuzzuf handles pagination and session management automatically.

=== "Asynchronous"

    ```python
    import asyncio
    from pywuzzuf import WuzzufClient

    async def main():
        async with WuzzufClient() as client:
            print("🔍 Searching for 'Python Developer'...")

            # Fetch the first 5 results
            result = await client.jobs.search("Python Developer").limit(5).all()

            for job in result.items:
                print(f"- {job.attributes.title}")

    if __name__ == "__main__":
        asyncio.run(main())
    ```

=== "Synchronous"

    ```python
    from pywuzzuf import SyncWuzzufClient

    with SyncWuzzufClient() as client:
        print("🔍 Searching for 'Python Developer'...")

        # Fetch the first 5 results
        result = client.jobs.search("Python Developer").limit(5).all()

        for job in result.items:
            print(f"- {job.attributes.title}")
    ```

**Expected Output:**

```text
🔍 Searching for 'Python Developer'...
- Senior Python Developer
- Python Backend Engineer (Django)
- Data Scientist (Python)
- ...
```

## 2. Accessing Job Data

Each result is an `EnrichedJob` object. This means the standard job attributes are available, and the associated `Company` data is pre-fetched for you.

### Job Attributes

Core metadata lives under `.attributes`:

```python
job.attributes.title        # "Senior Python Developer"
job.attributes.description  # Full HTML description
job.attributes.posted_at    # datetime object (UTC)
job.attributes.location     # Location object (City, Country)
```

### Company Enrichment

Unlike raw API responses, PyWuzzuf attaches the full company profile directly to the job object:

```python
if job.company:
    print(f"Company: {job.company.attributes.name}")
    print(f"Website: {job.company.attributes.website}")
```

!!! warning "Data Completeness & Null Values"
    Job listings depend entirely on the recruiter or company filling out the job post application on Wuzzuf.

    **Common missing fields include:**

    - `job.company` (if enrichment fails or data is absent)
    - `job.attributes.requirements`
    - `job.attributes.salary` details

    Always use defensive checks when accessing these attributes:

    ```python
    # Safe access pattern
    salary = job.attributes.salary
    if salary and salary.min:
        print(f"Salary: {salary.min} - {salary.max}")

    if job.company:
        print(f"Company: {job.company.attributes.name}")
    ```

    For advanced auditing, refer to the **Data Quality Report** in the Data Models documentation.

## 3. Filtering Results

Use `SearchFilters` to narrow down your search. For example, finding jobs posted in the last 24 hours.

=== "Asynchronous"

    ```python
    from pywuzzuf import SearchFilters, DateRange

    filters = SearchFilters(posted_within=DateRange.LAST_24_HOURS)

    result = await client.jobs.search("DevOps").filter(filters).all()
    print(f"Found {len(result.items)} recent DevOps jobs.")
    ```

=== "Synchronous"

    ```python
    from pywuzzuf import SearchFilters, DateRange

    filters = SearchFilters(posted_within=DateRange.LAST_24_HOURS)

    result = client.jobs.search("DevOps").filter(filters).all()
    print(f"Found {len(result.items)} recent DevOps jobs.")
    ```

## 4. Running Your Script

Save your code to a file (e.g., `main.py`) and run it.

=== "uv"

    ```bash
    uv run main.py
    ```

=== "python"

    ```bash
    python main.py
    ```

## Next Steps

- **[Filtering Guide](usage/filters.md)**: Dive deep into location, career level, and date filters.
- **[Pagination](usage/pagination.md)**: Learn how to handle large datasets and progress tracking.
- **[Resilience](usage/resilience.md)**: Handle rate limits and bot detection gracefully.
