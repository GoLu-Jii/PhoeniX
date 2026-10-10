# PHOENIX — Dependency Policy

The goal is a small, reproducible environment. Add a package only when an implemented feature needs it. Preserve the actual PHOENIX repository's existing package manager and compatible versions; this document does not authorize replacing a working environment blindly.

## Initial backend dependencies

| Package | Why it is needed | When to add it |
|---|---|---|
| `fastapi` | HTTP API and request/response validation | Phase 0, only if not already present |
| `uvicorn` | Local ASGI server | Phase 0, only if not already present |
| `httpx` | Bounded HTTP requests to GitHub and official pages; built-in `MockTransport` for tests | Phase 0/collector work |
| `beautifulsoup4` | Parse links and readable HTML from official pages | When the website collector is introduced |
| `pytest` | Automated tests | Phase 0 if no test runner exists |

Pydantic is used directly for schemas, so declare it as a direct dependency even though FastAPI also depends on it. Keep versions compatible with the selected FastAPI/Starlette stack.

For tests, start with `pytest`, FastAPI's `TestClient`, and `httpx.MockTransport`. Do not add a separate HTTP mocking framework or async test plugin unless the actual code requires it. The first scan should use bounded, sequential HTTP calls; do not introduce concurrency as a default.

## Optional dependencies

- `python-dotenv`: add only if the application is designed to load a local `.env` file automatically. Otherwise use environment variables injected by the shell or deployment environment.
- An LLM provider SDK: not required for the first deterministic scan. Prefer the existing HTTPX client for an API-compatible provider; add an SDK only if a necessary feature cannot be implemented cleanly without it.
- Lint/format tooling: reuse anything the repository already has. Add one simple tool if it materially improves consistency, but do not block the first vertical slice on a large quality-toolchain setup.

## Do not add for the MVP

Unless a verified requirement changes, do not add SQLAlchemy, Alembic, APScheduler, Redis/Celery, JWT/auth packages, LangChain/LangGraph, vector databases, feed parsers, browser automation, PDF libraries, or a second HTTP client. The first scan is request-scoped and does not need accounts, persistence, background jobs, deep RSS support, browser rendering, or PDF export.

## Frontend dependencies

Do not select or add frontend packages from this document. First inspect the actual PHOENIX `package.json` (or other frontend manifest), framework, lockfile, existing UI kit, and build scripts. Reuse the current stack. Add a charting, state-management, routing, or component library only when a specific screen proves it is needed. Do not create a second frontend app.

## One manifest and one lock strategy

- If the repo already uses `pyproject.toml`, continue using it.
- If it already uses `requirements.txt`, continue using it.
- If there is no Python manifest, choose one simple option; do not maintain both without a demonstrated need.
- Preserve the existing JavaScript package manager and lockfile. Never regenerate or delete a lockfile merely to satisfy an agent's preference.
- Pin or constrain versions consistently with the chosen manifest and record reproducible install commands. Do not install latest versions blindly into an unknown environment.

## Environment and secrets

Keep `.env` and credentials out of Git. Add `.env.example` with names and placeholders only, and ensure `.gitignore` covers `.env`, `.venv/`, `__pycache__/`, `.pytest_cache/`, `node_modules/`, build output, logs, and local databases/reports where applicable. `GITHUB_TOKEN` and any LLM key are optional for the core deterministic path. Never put secrets in frontend variables, returned API JSON, screenshots, tests, or logs.

## Initial commands

Exact commands must be confirmed after inspecting the repo. Expected Python baseline if the existing project has no alternatives:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m pytest -q
```

Do not create the manifest until the repository baseline has been inspected. These commands are a fallback, not an instruction to overwrite an existing setup.
