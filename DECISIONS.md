# Decision Log: Phoenix

Solo build for Grevix AfterCode 2026. Live log of what the AI did, what I decided and what I rejected. Times are IST. The initial plan is in [docs/DESIGN.md](docs/DESIGN.md).

**Rules statement:** New repository created during the build window. [Keep this line only if it is true.]

## Why Phoenix (before the window, research only)
Rejected: a subscription-cancellation guide (similar extensions exist), a tender-collusion detector (couldn't confirm bidder-level data), a take-home assignment scoper (no way to verify accuracy).

## Naming real companies
Demos use a mock company I control plus 2–3 clearly open-source companies. Findings are observations with sources, never accusations.

---

## Log
<!-- One entry per real decision or change. Newest at the bottom. -->

### [HH:MM] Title
- **AI did:**
- **I decided:**
- **Rejected / changed from plan:**
- **Why (evidence):**

### [03:07] GitHub data collection
- **AI did:** Added bounded GitHub account/repository collection, an investigation API route, and mocked tests for success, validation, retry, and partial failure.
- **I decided:** Keep this increment data-only; signal detection remains a later task.
- **Rejected / changed from plan:** Did not add website, careers, release, or interpretation collection.
- **Why (evidence):** Backend tests passed (11 passed); `pip check` reported no broken requirements.

### [03:33] GitHub token loading and live smoke test
- **AI did:** Loaded `GITHUB_TOKEN` from the project-root `.env` using `python-dotenv`; started the API from `frontend/` with the shell token unset.
- **I decided:** Keep the token server-side and report only whether it is configured.
- **Rejected / changed from plan:** No architecture change and no credential values exposed.
- **Why (evidence):** Token presence was detected. The `openai` investigation returned HTTP 200, 10 repositories, and 453 recent commits with partial status; `openai/openai-ruby` commit activity was still computing. Backend tests passed (13 passed) and `pip check` passed.

### [04:12] Basic GitHub signal detection
- **AI did:** Added deterministic findings for repositories created within 30 days and per-repository completed-week commit spikes, then attached findings and repository evidence IDs in the investigation response.
- **I decided:** Applied the requested thresholds and kept findings observational, source-linked, and under `unannounced_move`.
- **Rejected / changed from plan:** No scores, ranking, LLM interpretation, or strategy claims were added.
- **Why (evidence):** Full backend suite passed (17 passed); `pip check` and `git diff --check` passed.

---

## Challenge Card #1 (08:00)
- **Card:**
- **Stayed / changed / removed:**
- **AI did / I decided / I rejected:**

## Challenge Card #2 (16:30)
- **Card:**
- **Stayed / changed / removed:**
- **AI did / I decided / I rejected:**

## Final notes
What worked, what didn't, and what the backtest showed (if done).