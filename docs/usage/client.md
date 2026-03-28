---
icon: material/api
---

# Client & Resources

The `WuzzufClient` is the primary interface for interacting with the Wuzzuf API. It manages HTTP sessions, browser impersonation, and resource access.

## Lifecycle Management

Always use the async context manager (`async with`) to ensure the underlying `curl_cffi` session is correctly closed. This prevents resource leaks and open socket warnings.

=== "Asynchronous"

    ```python
    from pywuzzuf import WuzzufClient

    async with WuzzufClient() as client:
        # Session is active and impersonation headers are set
        pass
    # Session is closed automatically
    ```

=== "Synchronous"

    ```python
    from pywuzzuf import SyncWuzzufClient

    with SyncWuzzufClient() as client:
        # Client manages a private event loop
        pass
    # Background loop and session are cleaned up
    ```

!!! warning "Blocking the Loop"
    The `SyncWuzzufClient` creates a private event loop. Do not attempt to instantiate it inside an already running asyncio loop (e.g., Jupyter Notebooks, FastAPI). Use `WuzzufClient` directly in those environments.

## Configuration

| Parameter | Type | Default | Description |
| :--- | :--- | :--- | :--- |
| `base_url` | `str` | `"https://wuzzuf.net/api"` | Root API endpoint. Change this for mocking tests. |
| `impersonate` | `str` | `"chrome124"` | Browser TLS fingerprint. |
| `session` | `AsyncSession` | `None` | Pre-configured `curl_cffi` session (Advanced). |

### Browser Impersonation

PyWuzzuf uses `curl_cffi` to mimic real browser TLS fingerprints, allowing it to bypass basic bot detection.

If you receive a `BotDetectionError`, the first step is to update the `impersonate` string to a newer Chrome version.

```python
# Example: Updating the browser fingerprint
async with WuzzufClient(impersonate="chrome124") as client:
    # ...
    pass
```

Common valid values include: `"chrome110"`, `"chrome120"`, `"chrome124"`, `"safari15_5"`.

### Base URL

Use `base_url` for testing against a mock server or recording fixtures.

```python
async with WuzzufClient(base_url="http://localhost:8080/api") as client:
    # Requests go to local mock server
    pass
```

## Advanced Usage: Proxies & Sessions

For large-scale data collection, you may need to route traffic through a proxy. To do this, inject a pre-configured `curl_cffi.AsyncSession`.

```python
from curl_cffi.requests import AsyncSession
from pywuzzuf import WuzzufClient

# 1. Configure a session with proxies
session = AsyncSession(
    impersonate="chrome124",
    proxy="http://user:pass@proxy.example.com:8080"
)

# 2. Inject the session into the client
async with WuzzufClient(session=session) as client: # (1)!
    # All requests now use the configured proxy
    results = await client.jobs.search("Python").limit(5).all()

await session.close() # (2)!
```

1.  The client detects the injected session and uses it for all transport. It will **not** override your proxy or impersonation settings.
2.  **Important**: When injecting a session, ownership remains with *you*. The client will not close it on exit. You must close it manually.

!!! warning "Resource Ownership"
    If you inject a custom `session` as shown in annotation **#2** above, the client assumes you are responsible for the lifecycle of that object. Failing to call `await session.close()` will lead to open socket warnings and resource leaks.

## Resource Accessors

### Accessing Jobs

The `jobs` resource returns a **Query Builder**. This allows you to chain methods to construct complex searches before executing them.

```python
# 1. Initialize the query (No network request yet)
query = client.jobs.search("Python Developer") # (1)!

# 2. Chain filters and limits
result = await query \
    .filter(SearchFilters(posted_within=DateRange.LAST_WEEK)) \
    .limit(20) \
    .all() # (2)!

# 3. Iterate results
for job in result.items:
    print(job.attributes.title)
```

1.  **Lazy Initialization**: Calling `.search()` simply prepares the query object. No HTTP request is sent yet.
2.  **Execution**: The `.all()` method is a "terminal operation". This is the exact moment the HTTP request is triggered, pagination begins, and data is collected.

## Next Steps

Now that you have a client configured and know how to trigger a search, the logical next step is refining your queries.

**[Go to Filtering Guide :octicons-arrow-right-24:](filters.md)**
