# Phoenix

**See what a tech company is building before it announces it.**

Companies announce last. They ship first: new repos, quiet releases, new docs, hiring waves. Phoenix reads those public traces and tells you where a company is actually heading, and where that disagrees with what it says.


## What Phoenix finds
Enter a company. Phoenix scans it and reports two things:

1. **Unannounced moves.** What its public footprint shows that the company hasn't said: a new repo with deployment tooling, a hiring wave in one area, a burst of releases in one direction.
2. **Say-do gaps.** Website claims its footprint doesn't back up ("open source", "AI agents", "enterprise-ready").

## How it works
- Collects public traces: GitHub (repos, commits, releases), job boards, docs and changelogs.
- Rule-based detectors find the changes. Dates and counts never come from the LLM.
- The LLM only explains evidence in plain language. A verifier rejects any finding without a source.
- Every finding shows: what we observed, the source, what it may mean, and what it cannot prove.

## Example (illustrative, mock company)
    TARGET: AgentForge (mock)

    UNANNOUNCED MOVES
    ▲ Deployment tooling: 3 releases + new `deploy` repo in 21 days
    ▲ Infra hiring: 4 new platform roles vs 0 last quarter

    SAY-DO GAPS
    ✗ "Fully open source": 2 of 11 repos public, core engine not found

    Signals, not proof. A repo is not a product; a job post is not a strategy.

## Backtest (TODO)
Run Phoenix on a past launch and check whether public signals appeared before the announcement. Results will be added here.

## Status
- [ ] Public data collectors
- [ ] Change detectors
- [ ] Source verification step
- [ ] Interactive report

## Decision log
See [DECISIONS.md](DECISIONS.md): what the AI did, what I decided, what I rejected.