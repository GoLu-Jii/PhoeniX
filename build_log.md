# PHOENIX Build Log

Append-only: add a dated entry after each component finishes; do not rewrite earlier entries.

## 2026-10-11 — Project setup
- Root docs, Python requirements, `.venv`, and React/Vite/TypeScript frontend are present.
- Python 3.11.9; backend requirements installed. `pip check` passed.
- Frontend dependencies installed; production build and lint passed.

## 2026-10-11 — Backend health foundation
- FastAPI app exposes `GET /health` with `{"status":"ok"}`.
- Local `TestClient` health test passes.

## 2026-10-11 — GitHub collection and API
- `POST /api/investigations` accepts a GitHub username or account URL.
- Collector identifies user/organization; retrieves up to 10 public repositories, repository metadata, language bytes, up to 50 commits from the last 45 days, and weekly commit activity.
- Summaries aggregate language bytes and combine weekly activity by GitHub week-start timestamp.
- Uses bounded HTTP timeouts and commit-stat retry; endpoint failures retain available data and return warnings. HTTP 401 and rate-limit/access HTTP 403 warnings are distinguished.
- Optional `GITHUB_TOKEN` loads from the project-root `.env` via `python-dotenv`; token values are not returned or logged.
- Mocked backend suite: 13 passed. `pip check` and `git diff --check` passed.
- Live smoke: launched from `frontend/` with shell token unset; root token detected. `openai` returned HTTP 200, partial status, 10 repositories, and 453 recent commits. `openai/openai-ruby` commit activity was still computing; warning returned.

## 2026-10-11 — Build failures and recovery
- Initial Python check found pinned packages absent from `.venv`; pytest could not run. Installed the declared requirements; `pip check` passed.
- Frontend build/lint first ran from the repository root and failed because no root `package.json` exists. Reran from `frontend/`; build and lint passed.
- First health-test run failed with `ModuleNotFoundError: app` from the root test command. Corrected the package import; health test passed.
- An unauthenticated GitHub verification request hit HTTP 403 rate limiting. Added root `.env` loading with `python-dotenv`; token presence was confirmed without printing its value.
- The first live server attempt could not bind port 8000. Retried on 8001; the `openai` investigation returned HTTP 200.
- GitHub returned HTTP 202 while computing `openai/openai-ruby` commit activity; PHOENIX preserved available data and reported a partial result with a warning.

## 2026-10-11 — Basic GitHub signal detection
- Added deterministic findings for public repositories created within 30 days and for per-repository completed-week activity at least 5 commits and at least twice the prior four-week average.
- Excluded incomplete current weeks; missing or discontinuous history produces no spike finding.
- Investigation responses now include findings with rule IDs, observed dates/counts, repository source URLs, evidence IDs, interpretation, and limitations.
- Backend suite: 17 passed. `pip check` and `git diff --check` passed.

## 2026-10-11 — Commit-theme signals API
- Added `POST /api/signals`, reusing the existing investigation pipeline and collector.
- Case-insensitive keyword matching groups recent commit messages into five technical themes; a theme finding requires at least three distinct commits.
- Findings include commit messages, dates, repository/commit URLs, evidence references, interpretation, and limitations; collection status and warnings are preserved.
- Backend suite: 21 passed. `pip check` and `git diff --check` passed.

## 2026-10-11 — Groq commit interpretation
- Added one direct HTTPX Groq request to the existing `/api/signals` flow, with JSON mode, configured/default model selection, root `.env` key loading, SHA validation, and Python-built source evidence.
- Full bounded commits are sent once; unavailable/invalid model responses retain keyword findings with an explicit warning.
- Live `openai` request: HTTP 200, 10 repositories, 446 recent commits. Groq rejected interpretation with HTTP 413: 8,000 TPM allowed versus 23,633 requested; the endpoint returned keyword fallback and valid source links.
- Backend suite: 24 passed. `pip check` and `git diff --check` passed.

## 2026-10-11 — Compact commit input clarification
- Groq input uses a compact repository map, date index, actual commit message, and SHA for source validation; dates with no collected commits are omitted and explicitly described in the prompt.
- Complete collected messages/history remain available in Python evidence. No commits are silently dropped to work around quota.
- Groq live interpretation is currently limited by the configured 8,000 TPM quota; keyword fallback is returned with a warning.
- Backend suite: 24 passed. `pip check` and `git diff --check` passed.

## 2026-10-11 — Structured commit formatting and streamlined signal detector
- Added `parse_github_commits` to transform messy GitHub response data into a clean, structured JSON list containing `{commit_date, commit_message, committed_repo}` for the past 45 days.
- Excluded empty committed days, language distributions, and non-commit metadata to keep signal detection lean and quota-efficient.
- Integrated Groq AI signal detector on the parsed commit messages to identify suspicious or unusual engineering activity.
- Built `rule_based_signal_detector` fallback that groups commits by repository and outputs `{committed_repo, number_of_commits, commit_messages}` sequentially repo-by-repo.
- Connected the new parsing and signal detector flow through `POST /api/investigations` and `POST /api/signals`.
- Backend suite: 23 passed. `pip check` and `git diff --check` passed.

## 2026-10-11 — Separation of findings and backing commits
- Updated Groq prompt to return strictly clean findings `{title, committed_repo, description}` with no embedded commit messages.
- Added top-level `backing_commits` section collecting all commit messages that support the findings.
- Connected `backing_commits` through `investigate_github` and `_process_signals`.
- Backend suite: 24 passed. `pip check` and `git diff --check` passed.

## 2026-10-11 — Pacing signals and strict Groq response filter
- Added velocity and commit pacing / burst signal instructions to Groq prompt.
- Explicitly instructed model to describe bursts in finding descriptions and avoid copying generic commit messages to `backing_commits`.
- Filtered `/api/signals` output on Groq success to return strictly `findings` and `backing_commits` with no additional wrapper fields.
- Backend suite: 24 passed. `pip check` and `git diff --check` passed.

## 2026-10-11 — Website scraping and comparative company analysis
- Added `backend/app/collectors/website.py` using BeautifulSoup4 to extract title, description, headings, and clean text from company homepages with SSRF private-IP blocking, 8s timeouts, and 1MB size limit.
- Added `backend/app/analysis.py` calling Groq LLM to synthesize website claims vs GitHub engineering reality into structured findings: `stated_focus`, `engineering_reality`, `say_do_gaps` with verdicts, and `strategic_verdict`.
- Added deterministic `_build_rule_based_analysis` fallback when Groq is unavailable or fails.
- Integrated end-to-end orchestration in `investigate_company` and exposed via `POST /api/investigations` and `POST /api/analyze` accepting `{ "github_url": "...", "website_url": "..." }`.
- Backend suite: 38 passed. Live smoke test passed with HTTP 200.

## 2026-10-11 — Commit batching and daily burst summarization
- Added `summarize_daily_activity` in `backend/app/detectors.py` to aggregate commit counts by date and repo over the past 45 days and detect burst days (>= 5 commits).
- Added `batch_commits` to chunk large commit histories into manageable slices (default batch size 25) with configurable max batches to eliminate Groq HTTP 413 token-limit errors.
- Added `_call_groq_batch` sending `daily_burst_summary` alongside commit batches, keeping Groq responsible for interpreting both burst velocity and content signals.
- Added `merge_findings` and `merge_backing_commits` to deduplicate signals and supporting commit messages across batch executions without losing distinct findings.
- Updated `backend/app/analysis.py` to pass only `merged_findings` and compact `website_content` to the second LLM call, removing raw commit message and repository clutter.
- Confirmed fallback to rule-based signal detector activates only when Groq genuinely fails across all batches.
- Backend suite: 43 passed in 0.73s.
