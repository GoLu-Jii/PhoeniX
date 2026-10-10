# PHOENIX — Minimal Data Contracts

These are the shared fields required for the first implementation. Prefer a small stable contract over many nested objects. Add fields when a real feature needs them; do not silently change a field's meaning.

## Conventions

- JSON uses `snake_case`.
- Known timestamps serialize as ISO 8601 UTC; unknown timestamps are `null`.
- Unknown is never replaced with a fabricated value or zero.
- Source URLs must originate in validated input or collected records, never from LLM output.
- Evidence IDs only need to be unique within the current investigation.

## Request

```json
{
  "target_url": "https://github.com/example-org"
}
```

The target can be a supported GitHub account URL or a company website URL. Do not add careers, time-window, pagination, or provider prompt controls to the request until needed.

## Evidence

```json
{
  "id": "ev_001",
  "source_type": "github_repository",
  "source_url": "https://github.com/example-org/deploy-tools",
  "title": "deploy-tools",
  "excerpt": "Deployment automation utilities ...",
  "event_at": "2026-09-19T12:30:00Z",
  "event_date_kind": "repository_created_at",
  "collected_at": "2026-10-11T01:05:00Z",
  "external_id": "example-org/deploy-tools",
  "metadata": {"topics": ["deployment"], "primary_language": "Python"}
}
```

Required semantics:

- `id`: unique within the scan.
- `source_type`: controlled label such as `github_repository`, `github_release`, or `official_page`.
- `source_url`: usable URL for the observed record.
- `title`: nullable short label.
- `excerpt`: short source-backed excerpt; nullable.
- `event_at`: time of the source event when available (creation, release, publication, etc.).
- `event_date_kind`: identifies what `event_at` means. Never mix update time, publication time, and collection time without saying so.
- `collected_at`: when PHOENIX retrieved the record.
- `external_id`: optional source-native identity used for deduplication.
- `metadata`: only bounded fields needed by rules and the report.

Use `event_at`, not the generic field name `published_at`, because not every record is a publication.

## Source status

```json
{
  "source_type": "github",
  "source_url": "https://github.com/example-org",
  "status": "partial",
  "record_count": 8,
  "warnings": ["release_endpoint_rate_limited"]
}
```

Statuses: `success`, `partial`, `unavailable`, `skipped`. A successful source may return zero records. `record_count` is the records actually collected by PHOENIX, not the source's global total. Keep detailed timing/request metrics in logs, not the public report contract unless the UI needs them.

## Finding

Use one finding shape for both tracks; do not maintain a separate signal object and then duplicate it into a second finding object unless implementation proves the separation necessary.

```json
{
  "id": "finding_001",
  "track": "unannounced_move",
  "rule_id": "github.recent_repository_creation.v1",
  "title": "Recently created repository in deployment tooling",
  "observed_facts": ["Repository created on 2026-09-19."],
  "interpretation": "This may indicate work on deployment automation.",
  "limitations": ["A repository alone does not establish a product launch."],
  "evidence_ids": ["ev_001"],
  "claim_text": null,
  "claim_status": null
}
```

Fields:

- `track`: `unannounced_move` or `say_do_gap`.
- `rule_id`: identifies deterministic rule or claim-comparison method.
- `observed_facts`: direct statements derived from source records/rules.
- `interpretation`: optional, may be absent when LLM is unavailable.
- `limitations`: short evidence caveats.
- `evidence_ids`: one or more IDs from this report, except explicitly-labelled insufficient-evidence messages.
- `claim_text`: the exact official claim for Track B; otherwise null.
- `claim_status`: one of the claim statuses below for Track B; otherwise null.

Claim statuses: `supported`, `partly_supported`, `no_public_corroboration`, `contradictory_evidence`, `insufficient_evidence`. A contradictory status requires affirmative conflicting evidence. Missing or inaccessible evidence normally means `insufficient_evidence`, not `no_public_corroboration`.

Do not add numerical confidence until its meaning can be calculated and tested.

## Report

```json
{
  "investigation_id": "uuid",
  "created_at": "2026-10-11T01:05:00Z",
  "completion_status": "partial",
  "target": {"name": "Example Company", "input_url": "https://example.com"},
  "source_coverage": [],
  "findings": {"unannounced_moves": [], "say_do_gaps": []},
  "evidence": [],
  "warnings": []
}
```

Completion statuses: `completed`, `partial`, `failed`. `completed` does not mean findings must exist. `partial` means useful data exists but meaningful coverage failed. `failed` means the scan could not gather enough to produce a useful result.

The frontend can derive a dated timeline from findings/evidence later. Do not require a separate timeline schema in the first pass.

## LLM output boundary

The LLM may return only finding IDs plus bounded interpretation/limitations. The backend attaches observed facts and source URLs from the collected evidence. Unknown IDs, malformed output, or unsupported source references are rejected. If the LLM fails, return the deterministic report without retrying in the MVP.
