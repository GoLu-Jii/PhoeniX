# PHOENIX — Implementation Guide

Use this guide to build in small vertical slices. Do not scaffold every possible feature first.

## 1. Preflight

1. Inspect the actual PHOENIX repository and its frontend/backend choices.
2. Read the root README, root `DECISIONS.md`, and relevant files in `docs/`.
3. Summarize existing code, scripts, and tests before modifying anything.
4. Preserve a reasonable existing structure; this layout is a fallback proposal, not a mandate to move files.
5. Work against the shared contracts in `DATA_CONTRACTS.md`. If a contract needs to change, explain why and update the docs/tests alongside it.

## 2. Small proposed backend layout

Treat this as a fallback proposal until the actual PHOENIX repository has been inspected. Do not create or move files just to match this diagram. For the first slice, prefer synchronous, sequential HTTPX requests with strict timeouts and limits; introduce async/concurrency only if measured scan time requires it. See `DEPENDENCIES.md` for the minimal package policy.

```text
backend/
├── requirements.txt            # or existing pyproject.toml
├── app/
│   ├── main.py                 # FastAPI app and two endpoints
│   ├── config.py               # only settings actually used
│   ├── schemas.py              # request, evidence, finding, report
│   ├── investigation.py        # orchestrates one scan
│   ├── collectors/
│   │   ├── github.py
│   │   └── website.py
│   ├── detectors.py            # deterministic Track A and Track B rules
│   ├── interpretation.py       # optional single LLM call
│   └── verification.py         # evidence-reference validation
└── tests/
    ├── test_collectors.py
    ├── test_detectors.py
    └── test_investigation.py
```

Keep the existing frontend and its framework. Do not create empty folders or placeholder modules for future features. The implementation may use fewer files if it stays readable; splitting modules is justified by real complexity, not naming symmetry.

## 3. Build phases

### Phase 0 — Inspect and run

- Inventory the existing repository and get the app/test command working.
- Confirm the chosen framework, dependencies, and environment variables.
- Add only a minimal health route if missing.

**Done when:** the project starts and the current baseline is known.

### Phase 1 — GitHub-only vertical slice

- Accept and normalize a GitHub account URL.
- Fetch account metadata, a bounded repository list, useful repository fields, and selected releases.
- Normalize records to `Evidence`.
- Implement 1–3 clear deterministic Track A rules.
- Return a report with source status, evidence links, and an honest empty state.
- Add mocked collector/detector tests and run one separately reported live smoke test.

**Done when:** a real public GitHub account returns evidence-linked findings without requiring an LLM.

### Phase 2 — Official website and Track B

- Safely fetch the homepage and only a small number of relevant official links.
- Preserve exact claim text and the URL where it appeared.
- Compare claims only with relevant collected evidence; prefer `insufficient_evidence` over an unsupported verdict.
- Add tests for unavailable pages and missing/ambiguous dates.

**Done when:** the report can show a real official claim and explain whether the collected evidence supports assessing it.

### Phase 3 — Optional interpretation and report UI

- If an LLM key is available, add one bounded call over detected findings and referenced excerpts.
- Validate returned IDs and discard invented URLs/facts. No retry/critic loop in the MVP.
- Complete the UI: target input, scan state, coverage, two finding tracks, evidence links and limitations.

**Done when:** the whole scan works even if the LLM fails, and the user can inspect every finding's evidence.

### Phase 4 — Stabilize, then consider extensions

- Test empty, partial, unavailable, timeout, rate-limit and invalid-input cases.
- Fix latency, loading/error states, and visual hierarchy.
- Only then consider careers, historical comparison, timeline, persistence, PDF export, or deeper source support.

## 4. Minimal engineering rules

- No external request without a timeout and bounded response handling.
- No unbounded crawl, repository list, pagination, retry, or commit-history request.
- No database, scheduler, queue, authentication, vector database or agent framework without a demonstrated need.
- No source failure turned into “zero activity.”
- No detector imports FastAPI or the LLM client.
- No LLM-created evidence IDs, URLs, counts, or dates.
- No frontend-derived source facts.
- Keep source data and its actual date semantics visible.
- Write tests for the critical rules and failure paths, but do not attempt to anticipate every possible internet failure before the first scan works.

## 5. Reusing available code

Refer to `REUSE_AUDIT.md` for the specific source inventory. Before adapting any function, inspect its imports, callers, and assumptions. Strip unrelated auth/database/scheduler dependencies, adapt its output to PHOENIX schemas, and test it with mocked responses. Do not claim live testing unless it occurred.

## 6. Coding-agent workflow

Follow `BUILD_WORKFLOW.md` exactly: define one outcome and acceptance checks, inspect existing callers/contracts, implement the smallest slice, run focused tests and the full suite, inspect `git diff`, update docs/log for real decisions, and commit only when relevant tests pass. Do not start the next task while the current one has a known failing check. Do not stage unrelated user changes.

Before each task, state which files/contracts it will touch. After each task, report modified files, exact tests run and outcomes, known limitations, commit hash, and any justified design change. Do not mark features complete because placeholder files exist.
