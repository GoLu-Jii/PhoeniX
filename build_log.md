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
