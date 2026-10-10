# PHOENIX — Existing Backend Asset Audit

**Audience:** internal engineering/coding-agent reference. This document is an inventory of the uploaded backend code and a technical recommendation about what can be adapted. It is not a claim that any code has been integrated into PHOENIX.

## 1. Audit scope and limitations

The reviewed archive contains an `app/` Python package. It does **not** contain the project's dependency file, test suite, Alembic migration files, `.env.example`, root app configuration, or frontend. It includes Python bytecode cache files; these are generated artifacts and should not be copied into a project or treated as source of truth.

The source files were inspected. This audit is static review, not proof that the full application can be installed or run end-to-end: the archive does not contain enough of the project to recreate its environment or database migration history. The code below is therefore categorized by observed source content and integration suitability.

## 2. Summary matrix

| Existing file(s) | Contents observed | PHOENIX recommendation | Required changes before use |
|---|---|---|---|
| `app/kundali/builder.py` | GitHub account parsing, account type lookup, repo listing, language endpoint, commit activity, recent commits | **Adapt first** | Make HTTP client/config injectable; add timeouts and bounded retries; handle missing token cleanly; normalize errors and timestamps; cap pagination/request count; return typed collection results rather than print-only diagnostics. |
| `app/targets/onboarding.py` | HTTP fetch and BeautifulSoup anchor extraction; fallback paths; Groq JSON link classifier | **Reuse the link-extraction concept/function after hardening** | Validate URL/redirect destinations against SSRF; use a shared HTTP client; cap pages/link counts/text; deduplicate; deterministic domain/path classification first; validate LLM result against links that were actually collected; eliminate unsafe assumptions. |
| `app/daily/fetchers/ats.py` | Greenhouse, Lever, Ashby and Workable public job-board fetch functions | **Adapt later** | Validate actual payloads against live public board fixtures; separate platform adapters; normalize timestamps by source semantics; add caps and typed errors; Ashby path explicitly marked unverified in the source. Start with the most reliable adapter(s), not all four. |
| `app/daily/fetchers/blogs.py` | Fixed-path RSS/feed discovery, `feedparser`, article fetch and `trafilatura` extraction | **Selective reuse later** | Detect declared feeds from page metadata; current fixed suffix list misses many feeds; `feedparser.parse(url)` performs its own network request and bypasses the HTTPX timeout path; add URL safety, response bounds, safe errors, and stable timestamp parsing. |
| `app/daily/fetchers/socials.py` | Fetches one web/social URL and extracts text with `trafilatura` | **Defer** | It is a basic best-effort HTML extractor, not a real social-platform integration. Retain only as a generic official-page text extraction helper after URL safety and limits. Do not assume it works for JavaScript-rendered or blocked pages. |
| `app/kundali/synthesis.py` | Iterates repositories, aggregates languages and 52 weekly activity buckets, gathers ATS/blog/social info, writes a database row | **Reuse selected aggregation ideas, not the function unchanged** | Split pure collection/aggregation from persistence; emit normalized evidence, preserve actual timestamps, track source coverage and warnings, remove DB/model coupling, and avoid calling all sources in one serial function. `cadence_baseline` keyed only by array index loses explicit week-start timestamps. |
| `app/kundali/models.py` | SQLAlchemy `Kundali` table with JSON source summaries | **Do not use as PHOENIX's data contract** | PHOENIX's initial unit of work is a scan/report with evidence and finding references. If persistence is later required, design a schema around investigation runs, evidence and findings after the need is demonstrated. |
| `app/targets/models.py` | SQLAlchemy target record linked to a user, with website and source URLs | **Do not make it a required MVP model** | Target registry assumes authenticated, persistent monitoring. PHOENIX accepts a target for a single investigation; resolve/store it in the scan context first. |
| `app/auth/models.py`, `app/auth/routes.py`, `app/auth/utils.py` | Password hashing, JWT issuance/validation, signup/login/me endpoints | **Exclude from first version** | Not needed for the primary scan. If authentication later becomes required, review secret validation, password limits, account lock/rate limits, token expiry, error handling and test coverage independently. |
| `app/db/base.py`, `app/db/database.py` | SQLAlchemy declarative base and DB session dependency | **Exclude from the initial no-persistence path** | `DATABASE_URL` is used without a validated default; `check_same_thread=False` is SQLite-specific and may be inappropriate for other engines. No migration files were included in the archive. |
| `app/main.py` | FastAPI app mounts auth and target routes | **Use only as a reference for a FastAPI entry point** | The router imports the old application concerns; replace the route composition with the investigation/health API only if no PHOENIX app already exists. |
| `app/config.py`, `app/daily/collectors.py`, `app/daily/fetchers/github.py`, `app/events/*`, `app/llm/clients.py`, `app/export/pdf.py`, `app/scheduler/jobs.py`, `app/weekly/*` | Empty placeholder files | **Do not treat as implemented code** | Start from the component contracts in `COMPONENTS.md`; only create a module when needed in the current phase. |

## 3. Specific observations from the GitHub code

### Useful behaviour to preserve

- The account endpoint distinguishes organization/user account types before listing repositories.
- Repository lists are capped with a `limit` argument.
- The commit-activity function recognizes GitHub's `202` “statistics being computed” response and applies a bounded retry count.
- Recent commits are requested with a server-side `since` filter.
- Language response values are byte counts and can be aggregated, provided they are described as repository language metadata rather than company strategy.

### Issues to resolve before reuse

- Several HTTPX calls have no explicit timeout, including account lookup, repository listing, recent commits and language lookup.
- The token header is constructed as `Bearer None` when no token is configured instead of omitting authorization cleanly.
- Fixed `time.sleep` retry logic blocks the thread. Use an async/client-level bounded retry or keep the call small and isolated.
- Current error behaviour mixes raised exceptions and `None` plus `print` calls. PHOENIX requires consistent result statuses and structured warnings.
- The repository listing uses a capped `per_page` but does not implement pagination beyond that page. This is acceptable only if documented as a bounded sample, not a complete inventory.
- Account URL parsing uses the first URL path segment without fully validating host, scheme or path shape.
- Weekly activity is aggregated by list index in the existing synthesis function, losing explicit week timestamp semantics. Do not use it to make date-window claims without converting actual source week starts and validating coverage.

## 4. Specific observations from source discovery

The link extractor correctly uses `urljoin` to resolve relative anchors and independently attempts a small set of fallback pages. This is a useful start. However:

- It fetches user-supplied URLs without SSRF checks and does not revalidate redirects.
- It does not deduplicate links, bound total candidate count, or strip tracking/query noise.
- The Groq classifier sends the full unfiltered link list; a large page can produce unnecessary cost/latency or hit limits.
- JSON parsing fallback handles malformed JSON but does not fully validate field names, types, or confirm that selected URLs were among the discovered candidates.
- Classification cannot be relied on when the provider is unavailable. PHOENIX should use deterministic patterns first and treat the LLM as optional.

## 5. Specific observations from ATS, blog and social code

### ATS

The adapter functions normalize a few common job fields and deliberately mark the Ashby implementation as unverified. Preserve that caveat. Before a detector calculates hiring trends, validate each platform's public response shape and date field against a current real public board. In particular, do not assume an update timestamp is the original posting timestamp. If a source only returns the currently open postings, treat it as a snapshot rather than a longitudinal trend.

### Blog/RSS

The feed finder tests a fixed set of suffixes and checks whether the content-type header contains `xml`. Real sites may publish feeds at other paths or link them in HTML. The subsequent `feedparser.parse(feed_url)` network operation does not use the timeout passed to HTTPX elsewhere. Replace this with a shared, bounded retrieval path or set a clearly tested timeout strategy. Preserve article link and source-provided publication date when valid.

### Social/page extraction

The current generic function fetches one URL and runs text extraction. That can be a useful fallback for a simple official HTML page but is not a robust connector for a platform that requires authentication, client-side rendering, or blocks automated requests. PHOENIX should not make the initial scan depend on it.

## 6. Recommended adaptation sequence

1. Extract the useful GitHub REST interactions into a typed collector that returns `SourceCollectionResult`/`EvidenceRecord`.
2. Add fake-response tests for normal, empty, partial, rate-limit, malformed and timeout scenarios.
3. Build target URL normalization and safe website fetching independently of any legacy route/auth layer.
4. Reuse HTML link extraction after applying request/redirect safety, size/page limits, and deduplication.
5. Add official docs/changelog retrieval and deterministic signal rules.
6. Adapt Greenhouse/Lever career adapters only after the end-to-end scan works and date semantics are tested.
7. Only then decide whether any aggregation/storage pattern should be retained.

## 7. Files and artifacts not present

The archive does not include:

- dependency manifest (`requirements.txt` or `pyproject.toml`),
- test source files,
- Alembic configuration and migrations,
- `.env.example`,
- frontend code,
- root application documentation or deployment configuration.

Consequently, the archive alone does not prove reproducible installation, a successful full test run, or a complete database state. Request these items only if later work truly needs them; PHOENIX's first scan can be built without the old database/auth stack.
