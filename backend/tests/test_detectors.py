from datetime import datetime, timedelta, timezone

from backend.app.detectors import detect_github_findings


def _week(date: datetime, total: int) -> dict[str, int | str]:
	return {"week": date.isoformat().replace("+00:00", "Z"), "total": total}


def test_recent_repository_finding_uses_actual_date_and_url() -> None:
	now = datetime(2026, 10, 11, 12, tzinfo=timezone.utc)
	repository = {
		"full_name": "acme/new-project",
		"url": "https://github.com/acme/new-project",
		"created_at": "2026-10-01T08:30:00Z",
	}

	findings = detect_github_findings([repository], now=now)

	assert len(findings) == 1
	assert findings[0]["track"] == "unannounced_move"
	assert findings[0]["category"] == "recently_created_repository"
	assert findings[0]["rule_id"] == "github.recent_repository_creation.v1"
	assert findings[0]["source_url"] == repository["url"]
	assert "2026-10-01T08:30:00Z" in findings[0]["observed_facts"][0]
	assert "does not establish" in findings[0]["limitations"][0]


def test_weekly_spike_uses_four_previous_completed_weeks() -> None:
	now = datetime(2026, 10, 11, 12, tzinfo=timezone.utc)
	latest_completed_week = datetime(2026, 10, 4, tzinfo=timezone.utc)
	activity = [_week(latest_completed_week - timedelta(weeks=offset), 2) for offset in range(1, 5)]
	activity.extend(
		[
			_week(latest_completed_week, 5),
			_week(datetime(2026, 10, 11, tzinfo=timezone.utc), 100),
		]
	)
	repository = {
		"full_name": "acme/active-project",
		"url": "https://github.com/acme/active-project",
		"weekly_commit_activity": activity,
	}
	other_repository = {
		"full_name": "acme/steady-project",
		"url": "https://github.com/acme/steady-project",
		"weekly_commit_activity": [
			*[_week(latest_completed_week - timedelta(weeks=offset), 10) for offset in range(1, 5)],
			_week(latest_completed_week, 12),
			_week(datetime(2026, 10, 11, tzinfo=timezone.utc), 1000),
		],
	}

	findings = detect_github_findings([repository, other_repository], now=now)

	assert len(findings) == 1
	assert findings[0]["category"] == "weekly_activity_spike"
	assert findings[0]["rule_id"] == "github.weekly_commit_activity_spike.v1"
	assert findings[0]["source_url"] == repository["url"]
	assert "recorded 5 commits" in findings[0]["observed_facts"][0]
	assert "averaged 2 commits" in findings[0]["observed_facts"][0]
	assert "2026-10-04" in findings[0]["observed_facts"][0]


def test_missing_or_insufficient_weekly_history_does_not_spike() -> None:
	now = datetime(2026, 10, 11, 12, tzinfo=timezone.utc)
	latest_completed_week = datetime(2026, 10, 4, tzinfo=timezone.utc)
	repositories = [
		{
			"full_name": "acme/no-stats",
			"url": "https://github.com/acme/no-stats",
			"weekly_commit_activity": None,
		},
		{
			"full_name": "acme/sparse-project",
			"url": "https://github.com/acme/sparse-project",
			"weekly_commit_activity": [
				_week(latest_completed_week, 20),
				_week(latest_completed_week - timedelta(weeks=1), 1),
				_week(latest_completed_week - timedelta(weeks=3), 1),
				_week(latest_completed_week - timedelta(weeks=4), 1),
			],
		},
	]

	assert detect_github_findings(repositories, now=now) == []
