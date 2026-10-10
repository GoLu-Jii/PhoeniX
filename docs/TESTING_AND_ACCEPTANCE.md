# PHOENIX — Testing and Acceptance

Test the behaviours that protect the core product. Expand test breadth after the first end-to-end scan works.

## Essential automated tests

### Input and collectors

- Accept supported GitHub account URLs and reject malformed/unsupported targets.
- Website URLs use HTTP(S), reject local/private destinations, and revalidate redirects.
- GitHub success, empty data, timeout, rate limit, and one-repository partial failure.
- Website success, unavailable page, oversized response, timeout, unsafe redirect, and duplicate links.
- Missing or ambiguous timestamps remain unknown rather than being invented.

### Detector and evidence integrity

- A recent repository triggers the expected rule only when its source date is inside the configured window.
- Evidence outside the window does not trigger the rule.
- No historical trend is claimed from a current snapshot or incomparable data.
- Empty data does not create a finding.
- Every finding references evidence in the same report.
- Unknown evidence IDs and LLM-supplied URLs are rejected.
- Missing/inaccessible sources produce insufficient evidence, not false/contradictory verdicts.

### End-to-end

- GitHub target → collection → normalization → Track A finding → report.
- Website target with a linked GitHub source → available source results survive a partial failure.
- LLM disabled/failing → valid deterministic report still returns.
- Successful collection with no findings is distinguishable from failed collection.

Mock external HTTP calls in automated tests. Unit tests must not need Internet access, API tokens, or LLM credentials.

## Live smoke test

Run one manual/opt-in test against a known public GitHub account. Record the target, time, status of endpoints, record counts and any rate-limit issue. Never print or record the token. Mark this as a live smoke test—not as a unit test.

## Demo acceptance checklist

- [ ] A real target can be submitted and scanned.
- [ ] At least one real source is collected, with warnings shown for unavailable sources.
- [ ] Findings derive from rules over actual source fields.
- [ ] Both report tracks are represented, even when one is empty or insufficient.
- [ ] Every finding exposes source evidence.
- [ ] Observed facts, interpretation and limitations are distinct.
- [ ] No finding is invented to make the UI look populated.
- [ ] The complete frontend-to-backend path has been tested.
- [ ] Tests actually run and the results are recorded in the live decision log.

Defer exhaustive hardening and secondary-source test suites until the corresponding feature is implemented. Do not write tests for placeholder components as if those components already exist.


## Commit gate

Use `BUILD_WORKFLOW.md` for the exact loop. Do not commit a task while its relevant automated tests fail. Run the focused tests first, then the full suite; inspect the staged diff and stage explicit paths. Commit one coherent increment and record the commit hash/test result before beginning another task. If a live external smoke test is blocked by a service outage, record that separately from automated test status and do not claim the live test passed.
