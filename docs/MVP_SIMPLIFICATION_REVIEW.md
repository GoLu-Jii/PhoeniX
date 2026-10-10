# PHOENIX — MVP Simplification Review

The initial documentation was careful but specified too much detail before the actual PHOENIX repository had been reconciled. These are the chosen cuts for a solo 24-hour build.

## Keep: core product value

- Real public source collection.
- Deterministic observations and dates.
- Two report tracks, with conservative claim assessment.
- Inspectable evidence URLs and source coverage.
- Basic safety limits for arbitrary website input.
- A single optional LLM interpretation call.
- Mocked tests plus one real-source smoke test.

These are not the overengineering: they protect PHOENIX's main promise.

## Defer or simplify

| Previous complexity | MVP choice |
|---|---|
| Separate SignalCandidate, ClaimAssessment, Finding, TimelineEvent and multiple nested models | Use one `Finding` shape for a detected item, with optional claim fields; derive any timeline later from evidence dates. |
| A schema file per model family | Start with `schemas.py`; split only if it becomes hard to navigate. |
| A generic collector base class / adapter framework | Use simple functions with the same return shape. Add an abstraction only when two real implementations need it. |
| Dedicated modules for logging, time helpers, URL utilities, prompts, route handlers and services before needed | Start with the small layout in `IMPLEMENTATION_GUIDE.md`. Move code when a module has a real distinct job. |
| A required timeline and detailed timing/request metrics in the public contract | Keep timestamps and basic source coverage; leave performance diagnostics in logs. Build a timeline only if it improves the report. |
| GitHub 52-week commit statistics, full commit history and per-repository deep fetches | Start with account/repository metadata and selected releases. Add activity comparisons only when data quality and rate limits support them. |
| ATS/careers and hiring-trend analysis in the first vertical slice | Defer until GitHub plus official pages works; current listings may be a snapshot, not a trend. |
| Broad claim-truth engine for any marketing statement | Compare a small number of explicit claims only; no broad verdict without relevant evidence and sufficient coverage. |
| Multi-agent loop, critique loop and LLM repair retry | One bounded call, or no LLM if unavailable. Deterministic report remains valid. |
| Database, auth, migrations, scheduler, queue, PDF and vector DB | Not required for a one-shot scan. Reconsider only when a tested need appears. |
| Exhaustive tests for all imagined platform failures before first scan | Test the core rules, evidence validation, timeouts/limits, partial failures and no-LLM fallback first. Expand with each new integration. |
| Eight files with overlapping responsibilities? | Keep docs modular, but avoid duplicating the same requirement in every document. `MVP_SIMPLIFICATION_REVIEW.md` records the deliberate cuts. |

## Recommended first milestone

A single real GitHub target goes through: input validation → bounded collection → normalized evidence → one or two deterministic findings → evidence validation → usable report. No LLM, website discovery, ATS, persistence or timeline is needed to prove this milestone.

Then add one official website source and the minimal Track B comparison. Add the optional LLM and polish the UI only after both can be tested end-to-end.

## A simple rule for new complexity

Before adding a module, class, dependency, source or status field, answer: **Which visible capability or concrete failure does this solve right now?** If there is no specific answer, defer it.
