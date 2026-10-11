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

### [11:42] Commit-theme signals API
- **AI did:** Added `POST /api/signals` using the existing investigation pipeline and a case-insensitive commit-message detector for five technical themes.
- **I decided:** Require three distinct commit SHAs per theme and return evidence only for qualifying findings.
- **Rejected / changed from plan:** No second collector, self-HTTP call, scoring, or LLM was added.
- **Why (evidence):** Full backend suite passed (21 passed); `pip check` and `git diff --check` passed.

### [12:24] Groq commit interpretation
- **AI did:** Added one HTTPX Groq chat-completions call to `/api/signals`, validated returned SHAs, rebuilt dates/URLs/counts/evidence from collected commits, and retained keyword fallback with warnings.
- **I decided:** Send the complete bounded commit history once and do not silently truncate or discard records to fit the provider quota.
- **Rejected / changed from plan:** No Groq SDK, repeated requests, or separate endpoint was added.
- **Why (evidence):** Live `openai` request returned HTTP 200 with 10 repositories and 446 commits. Groq returned HTTP 413 because the key's 8,000 TPM limit was below the 23,633-token request; keyword fallback was returned. Backend suite passed (24 passed); `pip check` passed.

### [12:34] Compact Groq input clarification
- **AI did:** Clarified that Groq receives compact repository/date/message rows plus SHAs for evidence validation, with dates lacking collected commits omitted.
- **I decided:** Omitted dates must not be interpreted as proof of inactivity; full commit messages remain available in local evidence.
- **Rejected / changed from plan:** Did not silently sample or drop commits to bypass the configured TPM quota.
- **Why (evidence):** Backend suite passed (24 passed); `pip check` and `git diff --check` passed. The live Groq request remains over the configured 8,000 TPM limit.

### [13:20] Structured Commit Formatting and Streamlined Signal Detector
- **AI did:** Replaced multi-theme keyword mappings and SHA requirements with `parse_github_commits`, producing a clean list of commits `{commit_date, commit_message, committed_repo}` for the past 45 days. Connected this structured JSON to Groq AI for finding suspicious/unusual activity, and built `rule_based_signal_detector` to output `{committed_repo, number_of_commits, commit_messages}` sequentially repo-by-repo as a guaranteed fallback.
- **I decided:** Strip languages and empty committed days completely from signal detection. Focus purely on structured 45-day commit history. Groq detects unusual activity first; on any failure/rate limit, fall back immediately to the deterministic repo-by-repo rule-based output.
- **Rejected / changed from plan:** Removed rigid 5-theme keyword matching, complex SHA verification arrays, and token-heavy dates mapping to fit within hackathon timeline and quota bounds.
- **Why (evidence):** Full backend test suite passed (23 passed in 0.72s); `pip check` and `git diff --check` passed.

### [13:52] Separation of Findings and Backing Commits
- **AI did:** Updated the Groq prompt and signal response schema so that `findings` contains exclusively `{title, committed_repo, description}` with no commit messages or dates embedded inside findings, followed by a dedicated `backing_commits` section listing all supporting commit messages.
- **I decided:** Keep findings clean and concise; group all supporting evidence commit messages under a unified `backing_commits` list at the end.
- **Rejected / changed from plan:** Rejected embedding repetitive commit messages inside every individual finding card.
- **Why (evidence):** Full backend test suite passed (24 passed); smoke test verified clean JSON with separate `backing_commits`.

### [14:28] Pacing Signals and Strict Groq Response Formatting
- **AI did:** Updated Groq system prompt to recognize velocity/pacing signals (unusual commit bursts/spikes) separately from content signals, instructing the model not to dump commit messages for velocity findings into `backing_commits`. Formatted `/api/signals` to output strictly `{findings, backing_commits}` with no extraneous metadata when Groq succeeds.
- **I decided:** Output only findings and backing_commits on Groq success. Velocity/burst signals describe the pace in the finding description rather than pasting commit messages.
- **Rejected / changed from plan:** Rejected printing status, repositories, account, or summary wrappers when Groq generates the signals.
- **Why (evidence):** Full backend suite passed (24 passed); live smoke test confirmed 15-commit single-day burst generated finding with zero commit clutter in `backing_commits`.

### [15:15] Website Scraping and Comparative Company Analysis Flow
- **AI did:** Created `backend/app/collectors/website.py` with BeautifulSoup for homepage extraction (SSRF protection, timeout, 1MB cap, metadata and cleaned text), `backend/app/analysis.py` for LLM-powered company analysis comparing website claims with GitHub signals/commits into structured say-do gaps and strategic verdicts with deterministic rule-based fallback, and unified `investigate_company` orchestrator. Updated `POST /api/investigations` and `POST /api/analyze` to execute both in a single API request.
- **I decided:** Keep scraper resilient (non-fatal on failure) and guarded against private IPs. Cap text passed to Groq to stay within token limits. Structure say-do gaps with explicit verdicts (`supported`, `partly_supported`, `no_public_corroboration`, `contradictory_evidence`, `unannounced_move`).
- **Rejected / changed from plan:** Rejected putting scraper or analysis directly in `main.py` or `detectors.py`. Maintained clean separation of concerns.
- **Why (evidence):** Full backend suite passed (38 passed); live smoke test against `example.com` and `octocat` returned HTTP 200 with Groq analysis and say-do gap comparison.

### [15:50] Groq Token-Limit Resolution: Commit Batching and Daily Burst Summarization
- **AI did:** Added `summarize_daily_activity` in `backend/app/detectors.py` to aggregate commit counts per day per repo and identify burst dates (>=5 commits). Split large commit histories into manageable batches (size 25) with `batch_commits`. Called Groq on each batch with `daily_burst_summary` to keep Groq responsible for interpreting both velocity bursts and content signals. Merged findings and backing commits across batches with `merge_findings` and `merge_backing_commits` without duplicates. Updated `backend/app/analysis.py` to pass only merged findings + compact website content to the final LLM call. Ensured rule-based detector is invoked only when Groq genuinely fails.
- **I decided:** Keep batching size at 25 commits to comfortably fit within 8,000 TPM limits. Summarize daily activity so burst pace is visible without raw commit message bloat. Strip backing commits and raw repo dumps from the final LLM call.
- **Rejected / changed from plan:** Rejected passing raw commit messages to the final LLM call; rejected falling back to rule-based detector when partial batches succeed.
- **Why (evidence):** Full backend suite passed (43 passed in 0.73s); `git diff --check` passed with 0 errors.

### [17:00] Response Payload Ordering and Groq HTTP 429 Retry Backoff
- **AI did:** Reordered `investigate_company` return dictionary so high-priority intelligence fields (`status`, `account`, `detection_source`, `analysis`, `findings`, `backing_commits`, `website`) appear at the top of the JSON payload before the 1.7 MB raw `repositories` and `parsed_commits` arrays. Added automated retry loops with backoff on HTTP 429 in both `_call_groq_batch` and `analyze_company`.
- **I decided:** Keep all raw repositories and parsed commits in the response for backward compatibility, but place intelligence at the top so Swagger UI and frontend clients do not have to scroll past 50,000 lines of raw commits. Handle Groq rate limits with a short backoff (1.5-2.0s) so sequential LLM calls succeed with Groq instead of prematurely degrading to rule-based fallback.
- **Rejected / changed from plan:** Rejected stripping repositories completely from the payload to avoid breaking existing downstream clients.
- **Why (evidence):** Full backend suite passed (45 passed in 0.81s); live Vercel investigation confirmed Groq detection and comparative analysis.

### [17:35] Compact Default Response Payload and Non-Speculative Intelligence Grounding
- **AI did:** Reduced the default `/api/investigations` response payload from ~1.8 MB to ~7–10 KB (>99% reduction) by providing `compact_investigation_result`. Omitted root `parsed_commits` and raw `recent_commits` / `weekly_commit_activity` arrays from monitored repositories, while keeping `recent_commits_count` and complete metadata. Retained full histories internally in `latest_investigation_store` and exposed full raw data via `include_raw: true` / `debug: true` (body flags or query parameters). Updated Groq prompts in `detectors.py` and `analysis.py` with strict grounding rules prohibiting speculative conclusions or unverified corporate intent from being stated as facts.
- **I decided:** Make the frontend-optimized compact payload the default while preserving debug access for internal tracing and power users. Require all verdicts and reality statements to describe observable public code evidence rather than conjecture.
- **Rejected / changed from plan:** Rejected removing repository metadata entirely from the compact response; kept clean repository summaries with commit counts.
- **Why (evidence):** Full backend suite passed (47 passed in 0.83s); live end-to-end investigation with `encode` and `octocat` confirmed both Groq stages (`detection_source: groq`, `analysis_source: groq`), verified compact payload size reduction to 7–10 KB, and verified internal store retains parsed commits for `/api/signals`.

### [18:15] Hacktoberfest 2026 Styled Frontend Implementation & Verification
- **AI did:** Built a complete, production-grade React 19 + TypeScript frontend modeled after the Hacktoberfest 2026 visual theme (`AI belongs to everyone`). Styled with deep forest slate (`#28453a`), coral-red (`#ff6f59`), warm cream (`#f6f4ee`), 2px solid retro borders, and 4px–6px offset hard drop shadows. Integrated a dual-field search bar (GitHub URL + Website URL), quick presets (`Encode`, `Vercel`, `Octocat`), real-time radar scanner loading state with progress steps, Company Profile header, Strategic Verdict card (`Stated Focus vs. Engineering Reality`), Claim vs. Evidence Matrix cards with color-coded verdict badges, Observed Signals cards with split right-side evidence/date badges and expandable supporting commits, Monitored Repositories cards, and Technical Notices drawer. Connected directly to the live backend `/api/investigations` with Vite proxy and verified the complete flow and mobile responsiveness using the browser subagent.
- **I decided:** Strictly preserve Phoenix branding, terminology, and real backend connectivity while faithfully capturing the retro-editorial aesthetic of Hacktoberfest 2026. Use real data from the backend rather than mock payloads. Ensure mobile responsiveness by stacking input fields and hiding navigation clutter below 860px.
- **Rejected / changed from plan:** Rejected using mock datasets; rejected using TailwindCSS to ensure maximum precision and control with Vanilla CSS; rejected speculative claims in UI labels.
- **Why (evidence):** End-to-end browser subagent run verified the full flow against live Groq APIs (`encode` investigation completed in ~14s, returning 10 repositories, 3 detected signals, 6 say-do gaps, and strategic verdict). Production build (`tsc -b && vite build`) and `oxlint` passed with 0 errors. All 47 backend tests pass.


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