<div align="center">
  <h1>🔍 PyWuzzuf</h1>
  <p><em>An unofficial, async-first Python client for the Wuzzuf Jobs API</em></p>

  <p>
    <img src="https://img.shields.io/badge/python-3.12%2B-blue?logo=python&logoColor=yellow" alt="python - 3.12+">
    <img src="https://img.shields.io/badge/UV-blue?logo=uv" alt="UV">
    <a href="https://prek.j178.dev/">
      <img src="https://img.shields.io/badge/Prek-blue?logo=prek" alt="Prek - Ready">
    </a>
    <img src="https://img.shields.io/badge/Async-Ready-blue?logo=async" alt="Async - Ready">
    <img src="https://img.shields.io/badge/License-MIT-blue?logo=LICENSE" alt="License - MIT">
  </p>

  <p>
    <a href="https://hossam-elshabory.github.io/pywuzzuf/">📖 Read The Documentation</a>
  </p>
</div>

---

## 📑 Table of Contents <!-- omit in toc -->

- [🔧 Core Features](#-core-features)
- [🚀 Installation](#-installation)
- [🎯 Quick Start](#-quick-start)
- [🤝 Contributions](#-contributions)

---

## ⚠️ Important Considerations <!-- omit in toc -->

> [!WARNING]
> PyWuzzuf is an **unofficial**, **educational** project and is not affiliated with, endorsed by, or connected to [Wuzzuf](https://wuzzuf.net). Users are responsible for ensuring their use of this library complies with Wuzzuf's [Terms and Conditions](https://wuzzuf.net/policies) and `robots.txt` policies.

> [!IMPORTANT]
> **Search Accuracy Notice**: The Wuzzuf API uses "soft matching," meaning irrelevant results often appear after the first few pages. PyWuzzuf solves this with **Client-Side Filtering**, enforcing your criteria locally to guarantee data integrity. [Read more in the Filtering Guide](docs/usage/filters.md).

### Rate Limiting & Ethics <!-- omit in toc -->
- Client-side filtering means you may fetch more pages than requested to reach your target count
- Be respectful with request volumes — this tool is for educational and personal projects, not for scraping at scale
- Consider implementing delays between requests for larger operations

---

## 🔧 Core Features

| Feature                     | What It Does                                                                             |
| --------------------------- | ---------------------------------------------------------------------------------------- |
| **🎭 Browser Impersonation** | Uses `curl_cffi` to mimic real Chrome/Firefox TLS fingerprints. No more 403s.            |
| **🔄 Smart Pagination**      | Automatic retries with exponential backoff. Control flow with `STOP`/`CONTINUE`/`RETRY`. |
| **✅ Client-Side Filtering** | Enforces your criteria locally — no more irrelevant results slipping through.            |
| **📊 Data Quality Audits**   | Built-in detection for missing companies, salaries, and malformed entries.               |
| **🔒 Type Safety**           | Full Pydantic v2 models with IDE autocomplete and validation.                            |

---

## 🚀 Installation

**One-liner with uv (recommended):**
```bash
uv add pywuzzuf
```

**Classic pip:**
```bash
pip install pywuzzuf
```

**Poetry:**
```bash
poetry add pywuzzuf
```

> Requires **Python 3.12+**

---

## 🎯 Quick Start

Get the first 10 "Python Developer" jobs posted in the last 24 hours:

```python
import asyncio
from pywuzzuf import WuzzufClient, SearchFilters, DateRange

async def main():
    async with WuzzufClient() as client:
        results = await client.jobs.search("Python Developer") \
            .filter(SearchFilters(posted_within=DateRange.LAST_24_HOURS)) \
            .limit(10) \
            .all()

        for job in results.items:
            company = job.company.attributes.name if job.company else "Unknown"
            print(f"📌 {job.attributes.title} @ {company}")
            
            if job.quality.has_anomalies:
                print(f"   ⚠️  Missing: {', '.join(job.quality.missing_fields)}")

asyncio.run(main())
```

**Output:**
```bash
📌 Senior Python Engineer @ Instabug
📌 Backend Python Developer @ Paymob
   ⚠️  Missing: salary_range
📌 Python Team Lead @ Vezeeta
...
```
---

## 🤝 Contributions

> [!IMPORTANT]
> **Not accepting contributions at this time.** Contributions will reopen once the project the more stable.