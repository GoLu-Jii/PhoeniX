# PHOENIX — Pre-Build Readiness Check

## Current assessment

The product scope and first-pass architecture are sufficiently defined to begin after one repository-specific check: **inspect the actual PHOENIX repository**. The uploaded previous-backend archive is useful as a source-code reuse reference, but it does not reveal the current PHOENIX frontend, package manifests, launch scripts, Git state, or working code. Therefore, the precise dependency set and exact file layout must not be finalized from the archive alone.

No new PHOENIX code should be written until this inspection and baseline run are complete.

## Settled enough for the MVP

- One on-demand investigation; no accounts, persistent database, scheduler, queue, vector store, or multi-agent workflow.
- First vertical slice: GitHub target → bounded public collection → normalized evidence → deterministic Track A findings → validated report.
- Official-page collection and a narrow Track B method come after the GitHub-only path works.
- One optional LLM explanation call, never required for deterministic functionality.
- Sequential, bounded HTTP calls before introducing concurrency.
- One shared finding schema and evidence IDs scoped to the investigation.
- Unknown dates remain unknown; failed collection is not zero activity; no finding is better than fabricated findings.
- Test each slice, inspect the diff, commit only a passing checkpoint, then move to the next task.

## Must inspect in the actual PHOENIX repository

- [ ] Current Git root, branch, latest commit, and working-tree status.
- [ ] Existing backend/frontend tree and entry points.
- [ ] Existing runtime and development dependencies, versions, manifest(s), and lockfiles.
- [ ] Existing test framework and the untouched baseline test result.
- [ ] Existing run/build/test commands and required environment variables.
- [ ] `.gitignore`, `.env.example`, and whether any secret/local artifacts are at risk of being committed.
- [ ] Existing API/frontend integration and CORS/proxy configuration.
- [ ] Current root `README.md`, root `DECISIONS.md`, and links to the docs directory.

## Small decisions to make during the relevant task, not in advance

- Exact limits for repositories, releases, page count, HTML size, redirects and timeouts: define named defaults in the collector/config and test them; adjust only from test/demo evidence.
- Exact first detector thresholds: choose a small, explicit initial rule during detector implementation and cover it with tests. Do not tune thresholds against a fabricated sample.
- Exact Track B extraction/comparison mechanism: decide before Phase 2 using real official text and collected evidence. Do not build a general-purpose truth engine.
- LLM provider/model: defer until deterministic findings work; use existing configuration if present and keep the call optional.
- Any persistent storage, caching, concurrency or rate-limiting package: add only when measured or required by the deployment target.

## Dependency baseline (conditional)

If the actual repository does not already establish a compatible stack, the expected minimal backend is FastAPI, Uvicorn, HTTPX, BeautifulSoup4 when the website collector is added, and pytest for tests. Pydantic is directly used for schemas and should be declared in accordance with the chosen manifest policy. Use HTTPX's built-in `MockTransport` for request tests. Avoid adding an LLM SDK before the optional LLM phase. See `DEPENDENCIES.md`.

## Security and demo readiness

- Fetch only HTTP(S) URLs. For user-supplied websites, reject local/private destinations, validate redirects, use timeouts and response/page caps, and never expose an arbitrary-URL fetcher.
- Treat retrieved webpage/repository text as untrusted data, including possible prompt-injection content. The LLM has no tools and must not be allowed to change collection scope, disclose secrets, or create source URLs.
- Keep secrets server-side; keep `.env` out of Git. The first deterministic path must work without credentials.
- If the API is exposed publicly for a demo, check platform-level request/rate limits and resource caps before sharing the URL. Do not introduce a whole rate-limiting subsystem before there is a deployment requirement.

## Ready-to-code gate

Proceed only when the current PHOENIX repository is available, existing code and dependencies have been inventoried, baseline commands/tests have been run, and the first task has one clearly stated behavior and acceptance criteria. The first task should not be “build the backend”; it should be a small baseline step that can be tested and committed on its own.
