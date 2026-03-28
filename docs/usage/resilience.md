---
icon: material/shield-check
---

# Resilience & Troubleshooting

PyWuzzuf is designed for reliable data collection in the face of network instability and anti-bot measures. This guide covers how the client handles failures automatically and how you can customize error recovery.

## Layered Defense Strategy

PyWuzzuf uses a three-layer strategy to ensure reliability:

| Layer | Mechanism | Scope | Automatic? |
| :--- | :--- | :--- | :--- |
| **Transport** | Retries & Backoff | Single HTTP Requests | Yes |
| **Application** | Bot Detection Heuristic | Session State | Yes (Raises Error) |
| **Pagination** | Flow Control Signals | Data Collection Loop | Opt-in (Callbacks) |

## 1. Automatic HTTP Retries

The client automatically retries failed requests using exponential back-off.

- **Triggers**: Network errors (`RequestsError`) and Rate Limits (`HTTP 429`).
- **Strategy**: Exponential back-off with jitter (up to 5 attempts).
- **Configuration**: Currently hardcoded in `HttpCore`. If you need custom retry policies, you can inject a pre-configured `curl_cffi.AsyncSession` with custom adapters.

You generally do not need to handle these errors yourself unless they persist after 5 retries.

## 2. Bot Detection Mitigation

If the Wuzzuf API suspects automated access, it will return `HTTP 403 Forbidden`. PyWuzzuf tracks consecutive 403 responses.

### The Threshold
If **3 consecutive 403 responses** occur, the client raises a `BotDetectionError` instead of retrying indefinitely.

### Handling the Error

```python
import asyncio
from pywuzzuf import WuzzufClient, BotDetectionError

async def main():
    try:
        async with WuzzufClient() as client: # (1)!
            result = await client.jobs.search("Python").limit(10).all()
            print(f"Found {len(result.items)} jobs.")
    except BotDetectionError as e: # (2)!
        print(f"Bot detection triggered: {e}")

if __name__ == "__main__":
    asyncio.run(main())
```

1.  The client uses a default impersonation string (e.g., "chrome124"). If this fingerprint is flagged by Wuzzuf, requests will start failing.
2.  This exception is raised immediately after 3 consecutive 403s, preventing the script from hanging indefinitely on retries.

### Resolution Strategies

1.  **Update Impersonation**: The most common fix is to update the browser fingerprint.
    ```python
    # Try a newer Chrome version or a different browser
    async with WuzzufClient(impersonate="chrome124") as client: # (1)!
        # ...
        pass
    ```
    1.  Valid values include `"chrome110"`, `"chrome120"`, `"chrome124"`, `"safari15_5"`, etc. Updating this often bypasses outdated signature blocks.

2.  **Reduce Request Frequency**: Use `asyncio.sleep` between large pagination calls.
3.  **Use Proxies**: Pass a proxied `AsyncSession` to the client constructor.

## 3. Pagination Flow Control

For granular control over how errors are handled during large paginated fetches, use the `on_error` callback. This moves resilience from the "Request" level to the "Dataset" level.

### Skipping Failed Pages

If you are fetching 1000+ jobs and a single page times out, you might prefer to skip it rather than fail the entire operation.

```python
import asyncio
from pywuzzuf import WuzzufClient, PaginationSignal

async def main():
    def handle_error(error, page, total_fetched): # (1)!
        print(f"⚠️ Error on page {page}: {error}")

        # If we hit a 404 or Timeout, skip the page
        if "404" in str(error) or "Timeout" in str(error):
            return PaginationSignal.CONTINUE # (2)!

        # Stop on critical errors
        return PaginationSignal.STOP

    async with WuzzufClient() as client:
        result = await client.jobs.search("Backend") \
            .on_error(handle_error) \
            .limit(500) \
            .all()

        print(f"Fetched {len(result.items)} items.")

if __name__ == "__main__":
    asyncio.run(main())
```

1.  **Context**: The callback receives the exception, the page number where it occurred, and the total items fetched so far.
2.  **Signal**: Returning `CONTINUE` tells the paginator to swallow the error, discard that specific page, and proceed to the next one.

## 4. Data Quality Checks

Even successful API responses can have missing or malformed fields. The `EnrichedJob` object includes a `quality` attribute to help you audit data.

```python
import asyncio
from pywuzzuf import WuzzufClient

async def main():
    async with WuzzufClient() as client:
        result = await client.jobs.search("Data Scientist").limit(10).all()

        for job in result.items:
            if job.quality.has_anomalies: # (1)!
                print(f"Job {job.id} has issues:")
                print(f"  Missing: {job.quality.missing_fields}")
                print(f"  Degraded: {job.quality.degraded_fields}")

if __name__ == "__main__":
    asyncio.run(main())
```

1.  **Aggregated Check**: This property is `True` if any fields are missing (failed enrichment) or degraded (ambiguous values).

This ensures your pipeline doesn't break silently when the API returns incomplete records.

## Next Steps

You have now covered the full lifecycle of the client. Refer to the API Reference for detailed type information.

**[Go to Exceptions Reference :octicons-arrow-right-24:](../reference/exceptions.md)**
