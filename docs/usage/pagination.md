---
icon: material/file-document-multiple
---

# Advanced Pagination

PyWuzzuf abstracts away the complexities of cursor management, rate-limit recovery, and state tracking. You can choose between "all-at-once" collection for convenience or item-by-item streaming for memory efficiency.

## Two Modes of Operation

| Mode | Method | Use Case | Memory Usage |
| :--- | :--- | :--- | :--- |
| **Eager** | `.all()` | Small/medium datasets (<10k jobs). Data analysis. | **High** (Buffers all items in RAM). |
| **Streaming** | `async for` | Large datasets. Exporting to DB/CSV. | **Constant** (One page at a time). |

## Eager Collection: `.all()`

The simplest way to fetch results. Returns a `PaginationResult` object containing the items and exhaustive metadata.

```python
import asyncio
from pywuzzuf import WuzzufClient

async def main():
    async with WuzzufClient() as client:
        # Fetch up to 100 jobs
        result = await client.jobs.search("Data Science").limit(100).all()

        print(f"Fetched: {len(result.items)}")
        print(f"Pages: {result.pages_fetched}")
        print(f"Stopped Early: {result.terminated_early}")

if __name__ == "__main__":
    asyncio.run(main())
```

### Setting Hard Caps

To prevent runaway queries, always set a limit or page cap when using `.all()`.

```python
import asyncio
from pywuzzuf import WuzzufClient

async def main():
    async with WuzzufClient() as client:
        result = await client.jobs.search("Python") \
            .limit(500) \       # (1)!
            .max_pages(20) \    # (2)!
            .all()

        print(f"Total jobs fetched: {len(result.items)}")

if __name__ == "__main__":
    asyncio.run(main())
```

1.  **Item Cap**: Stop fetching after 500 items are collected.
2.  **Page Cap**: Stop after 20 pages, even if fewer than 500 items were found. Useful as a safety net.

!!! warning "Memory Safety"
    If you call `.all()` without a `limit`, PyWuzzuf will attempt to fetch *every* matching job. For popular searches, this could crash your memory. A warning is logged if `.all()` is called without limits.

## Streaming: `async for`

For large datasets, use the asynchronous iterator. This processes items as they arrive, keeping only one page in memory at a time.

```python
import asyncio
from pywuzzuf import WuzzufClient

async def main():
    async with WuzzufClient() as client:
        async for job in client.jobs.search("DevOps").paginate():
            # Process one job at a time
            print(f"Processing: {job.attributes.title}")

if __name__ == "__main__":
    asyncio.run(main())
```

This is ideal for:

- Exporting data to files or databases.
- Running in memory-constrained environments.
- Processing "infinite" streams until a condition is met.

## Flow Control & Signals

You can intercept the pagination process to handle errors or stop execution using callbacks.

### Error Handling: `on_error`

If a page fetch fails (e.g., network timeout), the default behavior is to raise an exception. You can change this by returning a `PaginationSignal`.

```python
import asyncio
from pywuzzuf import WuzzufClient, PaginationSignal

async def main():
    def handle_error(error, page, total_fetched):
        print(f"Error on page {page}: {error}")

        # If it's a 404, skip the page. Otherwise, stop.
        if "404" in str(error):
            return PaginationSignal.CONTINUE # (1)!

        return PaginationSignal.STOP        # (2)!

    async with WuzzufClient() as client:
        result = await client.jobs.search("Backend") \
            .on_error(handle_error) \
            .all()

        print(f"Finished with {len(result.items)} jobs.")

if __name__ == "__main__":
    asyncio.run(main())
```

1.  **CONTINUE**: Swallow the error, skip the failed page, and proceed to the next one.
2.  **STOP**: Gracefully stop pagination and return the items collected so far.

### Manual Stopping: `on_progress`

You can also use the progress callback to stop iteration based on custom logic (e.g., "Stop if I found a job from company X").

```python
import asyncio
from pywuzzuf import WuzzufClient, PaginationSignal

async def main():
    def monitor_progress(total, page): # (1)!
        print(f"Fetched {total} jobs (Page {page})...")

        # Custom stop condition
        if total > 1000:
            print("Limit reached, stopping.")
            return PaginationSignal.STOP # (2)!

    async with WuzzufClient() as client:
        async for job in client.jobs.search("Sales").on_progress(monitor_progress).paginate(): # (3)!
            print(f"Job: {job.attributes.title}")

if __name__ == "__main__":
    asyncio.run(main())
```

1.  **Arguments**: The callback receives `total` (items fetched so far) and `page` (current page number, 1-indexed).
2.  **Signal Return**: Returning `STOP` breaks the `async for` loop immediately. The generator will not yield any more items from that point.
3.  **Streaming Mode**: Unlike `.all()`, using `.paginate()` allows you to process items one by one in the loop body while the callback monitors the overall progress in the background.

## Next Steps

Learn how to handle the inevitable network hiccups and API blocks you might encounter during pagination.

**[Go to Resilience Docs :octicons-arrow-right-24:](resilience.md)**
