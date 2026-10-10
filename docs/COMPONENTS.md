# PHOENIX — Component Responsibilities

This is a small-module design. Each component can be a normal Python module or function; do not turn it into a class hierarchy or separate service without a concrete reason.

## 1. API (`main.py`)

**Owns:** request validation, calling the investigation function, and returning the report schema.

**Does not own:** source fetching, detector logic, or LLM prompts.

**Failure behaviour:** invalid input returns a client error. A known source failure is represented in the report. Unexpected errors must not expose stack traces or secrets.

## 2. Investigation orchestrator (`investigation.py`)

**Owns:** running the applicable collectors in order, combining results, running detectors, optionally requesting interpretation, verifying findings, and assembling the response.

**Does not own:** detailed HTTP parsing or business logic for individual detector rules.

Keep it readable and sequential at first. Add concurrency only if measurements show it is needed.

## 3. GitHub collector (`collectors/github.py`)

**Owns:** normalizing an account URL, collecting account metadata, a bounded list of public repositories, useful repository metadata and selected releases.

**Rules:** explicit timeout, request/page caps, optional token, rate-limit handling, per-repository failure isolation. Do not fetch full commit history or every stats endpoint in the first pass. Do not turn `pushed_at` into a commit count or strategy claim.

## 4. Official-page collector (`collectors/website.py`)

**Owns:** safely fetching the supplied homepage and a small number of links found on that page; extracting title, readable text, source URL and reliable source dates where available.

**Rules:** page/byte/time caps, redirect validation, duplicate URL removal. This is not a general crawler or social-media scraper.

## 5. Evidence and schemas (`schemas.py`)

**Owns:** shared request, evidence, finding, source-status and report structures. All modules use the same names and semantics.

Keep the first set of models together in one file. Split schemas only if the file becomes genuinely hard to maintain.

## 6. Detectors (`detectors.py`)

**Owns:** pure Python rules for Track A and conservative Track B comparisons. Takes normalized evidence and returns findings with rule IDs and evidence IDs.

**Does not own:** HTTP calls, frontend rendering, or LLM requests. Rules must be reproducible and must not infer historical trends from one current snapshot.

## 7. Optional interpreter (`interpretation.py`)

**Owns:** one bounded LLM call that explains existing findings using supplied evidence excerpts.

**Does not own:** evidence collection, counts, dates, source URLs, evidence IDs, or final validation.

If the provider is not configured or fails, the scan still returns deterministic findings. No multi-agent loop and no repair/critic cycle in the MVP.

## 8. Verification (`verification.py`)

**Owns:** checking schema validity, ensuring every referenced evidence ID exists in this scan, and ensuring displayed URLs come from collected evidence. Reject or downgrade invalid output.

This is ordinary deterministic code, not another LLM call.

## 9. Frontend

**Owns:** target input, loading/error states, source coverage, findings in both tracks, evidence/source links, and limitations.

The frontend must not collect sources or compute facts. A timeline or charts are optional later; don't block the report cards on them.

## Shared failure rule

Collection status is separate from evidence sufficiency. A successfully fetched source can contain no relevant evidence; an unavailable source is not evidence of zero activity or a false claim.
