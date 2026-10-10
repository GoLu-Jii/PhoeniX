# PHOENIX — Product Design

## Product goal

PHOENIX investigates public technical activity at technology and AI companies. It surfaces observable changes that may signal a shift in direction and compares explicit company claims with evidence that can actually be inspected.

**Promise:** evidence-backed investigation, not certainty about private strategy or future launches.

## Main workflow

1. Enter a company website or public GitHub account URL.
2. Validate the target and identify only sources that can be grounded in the supplied URL or official links.
3. Collect a bounded set of public records.
4. Convert source data into normalized evidence records.
5. Apply deterministic rules to produce candidate findings.
6. Where official claims are available, compare their wording with relevant evidence.
7. Optionally ask one LLM call to explain already-detected findings.
8. Validate evidence references and show the report, source coverage, and limitations.

The first complete scan must work in one session without requiring historical monitoring.

## The two report tracks

### Track A — Unannounced moves

Highlight observable changes that may deserve investigation, initially:

- recently created public repositories;
- recently published releases, where reliable timestamps exist;
- technical themes visible in repository descriptions/topics;
- recent activity indicators, but only when the data supports the specific comparison.

A recently created repository or a push timestamp is not proof of a product launch or strategic shift. Do not claim a trend from a snapshot alone.

### Track B — Say-do gaps

Show specific statements found on official pages and compare them with relevant collected evidence. Use conservative outcomes:

- `supported`
- `partly_supported`
- `no_public_corroboration`
- `contradictory_evidence`
- `insufficient_evidence`

Use `contradictory_evidence` only when there is explicit evidence that conflicts with the exact claim. Missing public evidence is not proof that a claim is false. Broad statements such as “fully open source” often cannot be settled by counting public repositories alone.

For the first version, prefer a small number of clear, inspectable claim comparisons over a general-purpose truth engine.

## Sources and build order

1. **GitHub:** public account/repository metadata and selected release data.
2. **Official website:** homepage and a small number of directly linked product, technical, documentation, or changelog pages.
3. **Careers/ATS:** later, after the complete scan works. Treat current job listings as a snapshot unless reliable publication dates and historical comparisons exist.

Do not build broad social scraping or integrations for every job platform.

## Core demo scope

- One company scan at a time.
- GitHub collection and deterministic Track A findings.
- Minimal official-page collection and Track B claim/evidence comparison.
- Clear source coverage, source links, observations, interpretation, and limitations.
- One optional, bounded LLM interpretation pass.
- A compact report UI with source inspection and honest empty/partial states.
- Automated tests for the critical path and one separately reported live smoke test.

## Explicitly defer

- User accounts and permissions.
- Database, migrations, and long-lived scan history.
- Scheduled monitoring, notifications, queues, and background workers.
- Vector databases, knowledge graphs, multi-agent workflows, and multiple LLM retry/critic loops.
- ATS/hiring trends until their date semantics are verified.
- PDF export, dashboards unrelated to the scan, and a timeline view until the finding cards work well.
- Claims that PHOENIX predicts launches accurately without a valid historical evaluation.

## Success criteria

A user can submit a real target, complete a scan, see which sources were checked, inspect useful findings and their source records, distinguish observation from interpretation, and understand the limits of the evidence. “Insufficient evidence” is an acceptable result; invented findings are not.
