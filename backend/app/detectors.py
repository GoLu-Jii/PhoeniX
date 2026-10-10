from datetime import datetime, timedelta, timezone
from typing import Any

RECENT_REPOSITORY_DAYS = 30
COMMIT_SPIKE_MINIMUM = 5
BASELINE_WEEKS = 4


def _as_utc_datetime(value: Any) -> datetime | None:
	if isinstance(value, datetime):
		parsed = value
	elif isinstance(value, str):
		try:
			parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
		except ValueError:
			return None
	else:
		return None

	if parsed.tzinfo is None:
		return parsed.replace(tzinfo=timezone.utc)
	return parsed.astimezone(timezone.utc)


def _finding(
	*,
	index: int,
	evidence_id: str,
	category: str,
	rule_id: str,
	title: str,
	fact: str,
	interpretation: str,
	limitation: str,
	source_url: str,
) -> dict[str, Any]:
	return {
		"id": f"finding_{index:03d}",
		"track": "unannounced_move",
		"category": category,
		"rule_id": rule_id,
		"title": title,
		"observed_facts": [fact],
		"interpretation": interpretation,
		"limitations": [limitation],
		"evidence_ids": [evidence_id],
		"source_url": source_url,
		"claim_text": None,
		"claim_status": None,
	}


def detect_github_findings(
	repositories: list[dict[str, Any]],
	*,
	now: datetime | None = None,
) -> list[dict[str, Any]]:
	current_time = _as_utc_datetime(now or datetime.now(timezone.utc))
	if current_time is None:
		return []
	cutoff = current_time - timedelta(days=RECENT_REPOSITORY_DAYS)
	findings: list[dict[str, Any]] = []

	for repository_index, repository in enumerate(repositories, start=1):
		full_name = repository.get("full_name")
		source_url = repository.get("url")
		if not isinstance(full_name, str) or not isinstance(source_url, str) or not source_url:
			continue
		evidence_id = repository.get("evidence_id") or f"ev_{repository_index:03d}"

		created_at = _as_utc_datetime(repository.get("created_at"))
		if created_at is not None and cutoff <= created_at <= current_time:
			findings.append(
				_finding(
					index=len(findings) + 1,
					evidence_id=evidence_id,
					category="recently_created_repository",
					rule_id="github.recent_repository_creation.v1",
					title=f"Recently created public repository: {full_name}",
					fact=f"{full_name} was created at {created_at.isoformat().replace('+00:00', 'Z')}.",
					interpretation="This may indicate recently added engineering work in the account's public footprint.",
					limitation="Repository creation alone does not establish a product launch, purpose, or strategy.",
					source_url=source_url,
				)
			)

		activity = repository.get("weekly_commit_activity")
		if not isinstance(activity, list):
			continue
		week_totals: dict[datetime, int] = {}
		for row in activity:
			if not isinstance(row, dict):
				continue
			week = _as_utc_datetime(row.get("week"))
			total = row.get("total")
			if week is not None and isinstance(total, int) and not isinstance(total, bool) and total >= 0:
				week_totals[week] = total

		completed_weeks = sorted(
			(week for week in week_totals if week + timedelta(days=7) <= current_time),
			reverse=True,
		)
		if len(completed_weeks) <= BASELINE_WEEKS:
			continue

		latest_week = completed_weeks[0]
		previous_weeks = completed_weeks[1 : BASELINE_WEEKS + 1]
		if any(
			latest_week - week != timedelta(days=7 * offset)
			for offset, week in enumerate(previous_weeks, start=1)
		):
			continue

		latest_total = week_totals[latest_week]
		baseline_average = sum(week_totals[week] for week in previous_weeks) / BASELINE_WEEKS
		if latest_total < 5 or latest_total < 2 * baseline_average:
			continue

		week_end = latest_week + timedelta(days=7)
		findings.append(
			_finding(
				index=len(findings) + 1,
				evidence_id=evidence_id,
				category="weekly_activity_spike",
				rule_id="github.weekly_commit_activity_spike.v1",
				title=f"Elevated weekly commit activity: {full_name}",
				fact=(
					f"{full_name} recorded {latest_total} commits from "
					f"{latest_week.date().isoformat()} through "
					f"{(week_end - timedelta(days=1)).date().isoformat()}; "
					f"the previous four completed weeks averaged {baseline_average:g} commits."
				),
				interpretation="The latest completed week had more recorded commits than this repository's recent baseline.",
				limitation="Commit counts do not explain the work performed or establish a product or strategic change.",
				source_url=source_url,
			)
		)

	return findings
