---
icon: material/home
---

# PyWuzzuf

**Async Python client for the Wuzzuf job search API.**

PyWuzzuf is a type-safe library for programmatic job search and company data extraction. Built on `curl_cffi`, it provides browser impersonation and resilient pagination to facilitate data collection at scale.

!!! warning "Disclaimer and Usage"
    PyWuzzuf is an **unofficial**, **educational** project and is not affiliated with, endorsed by, or connected to [Wuzzuf](https://wuzzuf.net). Users are responsible for ensuring their use of this library complies with Wuzzuf's [Terms and Conditions](https://wuzzuf.net/policies) and `robots.txt` policies.

<div class="grid cards" markdown>

-   :material-download:{ .lg .middle } __Installation__

    ---

    Get up and running with `uv` or `pip`. Prerequisites for `curl_cffi` included.

    [:octicons-arrow-right-24: Installation Guide](installation.md)

-   :material-rocket-launch:{ .lg .middle } __Quickstart__

    ---

    Learn the basics of searching, filtering, and accessing job data safely.

    [:octicons-arrow-right-24: Start Searching](quickstart.md)

-   :material-shield-check:{ .lg .middle } __Resilience__

    ---

    Handle rate limits, bot detection (403s), and network errors gracefully.

    [:octicons-arrow-right-24: Resilience Guide](usage/resilience.md)

-   :material-database:{ .lg .middle } __Data Models__

    ---

    Explore the `EnrichedJob` object, nullable fields, and Data Quality Reports.

    [:octicons-arrow-right-24: Models Reference](reference/models.md)

</div>

## Quick Example

Get started immediately with the asynchronous client. This example demonstrates searching, safe data access, and basic quality checking.

```python
import asyncio
from pywuzzuf import WuzzufClient

async def main():
    async with WuzzufClient() as client:
        # 1. Search for recent Python jobs
        result = await client.jobs.search("Python Developer").limit(5).all()

        print(f"Found {len(result.items)} jobs.\n")

        for job in result.items:
            # 2. Safe attribute access
            title = job.attributes.title
            company = job.company.attributes.name if job.company else "Unknown"

            print(f"[{job.id}] {title}")
            print(f"  Company: {company}")

            # 3. Check data quality
            if job.quality.has_anomalies:
                print(f"  ⚠️  Quality Warning: {job.quality.missing_fields}")

if __name__ == "__main__":
    asyncio.run(main())
```

**Expected Output:**

```text
Found 5 jobs.

[12345] Senior Python Developer
  Company: TechCorp
[67890] Backend Engineer
  Company: StartupX
  ⚠️  Quality Warning: ['company']
...
```

## Key Features

*   **Browser Impersonation**: Uses `curl_cffi` to mimic real browser TLS fingerprints, bypassing basic bot detection.
*   **Resilient Pagination**: Automatic retries with exponential back-off and granular flow control signals.
*   **Data Quality Reports**: Built-in auditing of API responses to detect missing or malformed fields.
*   **Type Safety**: Fully typed with Pydantic models for excellent IDE support and validation.
