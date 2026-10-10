# PHOENIX — One-Task, Test, Commit Workflow

This workflow is mandatory for implementation. Work in small, complete increments. Do not start the next task while the current task is untested or has a known failing acceptance check.

## Before the first code change

1. Inspect the actual PHOENIX repository and confirm its Git root, current branch, last commit, and working-tree status.
2. Read the root `README.md`, root `DECISIONS.md`, and the relevant docs.
3. Run existing install/start/test commands without modifying files. Record what passes and what already fails.
4. Inspect `.gitignore`, dependency manifests and lockfiles. Check that secrets, `.env`, virtual environments, databases, generated reports, and build output are excluded.
5. Do not reset, clean, checkout over, or overwrite uncommitted user work. If the working tree is dirty, identify those changes and preserve them.
6. Confirm the exact file scope and acceptance criteria for Task 1 before implementation.

## The task loop

Repeat these steps for every task:

1. **Define one outcome.** State the behavior being added or fixed, the files expected to change, and the tests that will prove it. Avoid combining unrelated features.
2. **Inspect relevant code.** Read callers, imports, tests, and contracts before editing. Do not create a parallel implementation if an appropriate module already exists.
3. **Implement the smallest complete slice.** No speculative scaffolding, empty modules, drive-by refactors, or dependency additions unrelated to the task.
4. **Test the slice.** Run the focused tests, then the full existing automated suite. Use mocked network responses for normal CI tests; they must not require Internet access, secrets, or live services.
5. **Fix before proceeding.** If a test fails, stay on the current task and diagnose it. Do not label a failure as passing, skip it silently, or move to the next feature. If blocked, explain the blocker and leave the repository in a recoverable state without committing a knowingly broken change.
6. **Inspect the diff.** Review `git diff` and `git status`. Look for unrelated edits, generated artifacts, secrets, broad formatting changes, hardcoded URLs/tokens, dependency churn, and mismatches with the docs.
7. **Update documentation when the contract changes.** Update the appropriate docs and tests in the same increment. Append a live-log entry to root `DECISIONS.md` for real decisions, deviations, rejected alternatives, and meaningful implementation results. Do not invent a decision on the user's behalf; record the user's decision only after the user makes or confirms it.
8. **Commit the passing checkpoint.** Stage explicit file paths (not `git add .` by default), check the staged diff, and make one clear commit. A commit must represent one coherent, tested increment.
9. **Verify the commit.** Run `git status --short` and confirm the working tree is clean except for intentionally preserved user changes. Record the commit hash and test result. Then start the next task.

## Commit rules

- One meaningful task per commit; avoid one giant “MVP complete” commit.
- Every commit should leave the application in a known, test-passing state.
- Use readable messages, for example `feat(github): collect bounded repository metadata`, `test(detectors): cover recent-repository rule`, or `fix(website): validate redirect targets`.
- Do not make a commit if relevant tests fail. Do not commit secrets, `.env`, virtual environments, caches, local databases, temporary report output, or unrelated user edits.
- Do not amend, rebase, force-push, or reset existing user commits unless explicitly asked.
- A failed external live smoke test must be distinguished from a failed unit test. If a non-deterministic external outage blocks the smoke test, record it and decide whether the local, mocked-tested increment is safe to commit; do not claim live verification occurred.
- Keep branches simple. Do not introduce a branch/PR workflow solely for ceremony in a solo 24-hour build, unless the repository or user already uses one.

## Suggested commit sequence

The sequence may be adjusted after repository inspection, but each item should remain independently testable:

1. Baseline: make the existing project setup and health check reproducible.
2. Target parsing: validate and normalize supported GitHub account URLs.
3. GitHub collection: collect a bounded account/repository sample with timeouts and structured failures.
4. Release collection: add bounded release records and corresponding mocked tests.
5. Evidence/report schemas: validate the minimal response contract.
6. Deterministic Track A rules: add rules and time-window tests.
7. Investigation API: connect collection, normalization, detection and reporting; test end-to-end with mocks.
8. Website collection safety: add bounded page retrieval, link parsing, redirect checks and SSRF tests.
9. Track B: implement one deliberately narrow, testable claim/evidence method.
10. Optional LLM explanation and UI integration; each can be split into its own task if needed.

Do not create all the modules in this list up front. Create a file when the current task needs it.

## Definition of a completed task

A task is done when the behavior works, tests prove the critical paths and failures, the full existing suite passes, the diff is scoped, the docs/log are accurate, the commit is created, and the next task has explicit acceptance criteria. A directory or placeholder function is not completion.
