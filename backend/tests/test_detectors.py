import json
from datetime import datetime, timedelta, timezone

import httpx

from backend.app import detectors
from backend.app.detectors import (
	batch_commits,
	detect_github_findings,
	detect_signals,
	groq_signal_detector,
	interpret_commit_themes,
	merge_backing_commits,
	merge_findings,
	parse_github_commits,
	rule_based_signal_detector,
	summarize_daily_activity,
)


def test_parse_github_commits_extracts_required_fields_within_45_days() -> None:
	now = datetime(2026, 10, 11, 12, tzinfo=timezone.utc)
	recent_date = (now - timedelta(days=5)).isoformat().replace("+00:00", "Z")
	old_date = (now - timedelta(days=50)).isoformat().replace("+00:00", "Z")

	repositories = [
		{
			"full_name": "acme/backend",
			"languages": {"Python": 10000},
			"recent_commits": [
				{
					"sha": "sha123",
					"message": "Add authentication middleware",
					"committed_at": recent_date,
				},
				{
					"sha": "shaold",
					"message": "Very old commit beyond 45 days",
					"committed_at": old_date,
				},
			],
		},
		{
			"full_name": "acme/frontend",
			"languages": {"TypeScript": 5000},
			"recent_commits": [
				{
					"sha": "sha456",
					"message": "Update client UI components",
					"committed_at": (now - timedelta(days=2)).isoformat().replace("+00:00", "Z"),
				}
			],
		},
		{
			"full_name": "acme/empty-repo",
			"recent_commits": [],
		},
	]

	parsed = parse_github_commits(repositories, now=now)

	# Exactly 2 commits qualify (within 45 days, non-empty)
	assert len(parsed) == 2
	for item in parsed:
		assert "commit_date" in item
		assert "commit_message" in item
		assert "committed_repo" in item
		assert "languages" not in item

	assert parsed[0] == {
		"commit_date": (now - timedelta(days=5)).strftime("%Y-%m-%d"),
		"commit_message": "Add authentication middleware",
		"committed_repo": "acme/backend",
	}
	assert parsed[1] == {
		"commit_date": (now - timedelta(days=2)).strftime("%Y-%m-%d"),
		"commit_message": "Update client UI components",
		"committed_repo": "acme/frontend",
	}


def test_rule_based_detector_groups_by_repo_sequentially() -> None:
	parsed_commits = [
		{"commit_date": "2026-10-01", "commit_message": "msg 1", "committed_repo": "acme/repo-a"},
		{"commit_date": "2026-10-02", "commit_message": "msg 2", "committed_repo": "acme/repo-a"},
		{"commit_date": "2026-10-03", "commit_message": "msg 3", "committed_repo": "acme/repo-b"},
		{"commit_date": "2026-10-04", "commit_message": "msg 4", "committed_repo": "acme/repo-a"},
	]

	results = rule_based_signal_detector(parsed_commits)

	# Output groups one repo completely first, then the next
	assert len(results) == 2
	repo_a = results[0]
	assert repo_a["committed_repo"] == "acme/repo-a"
	assert repo_a["number_of_commits"] == 3
	assert repo_a["commit_messages"] == ["msg 1", "msg 2", "msg 4"]

	repo_b = results[1]
	assert repo_b["committed_repo"] == "acme/repo-b"
	assert repo_b["number_of_commits"] == 1
	assert repo_b["commit_messages"] == ["msg 3"]


def test_groq_signal_detector_success(monkeypatch) -> None:
	monkeypatch.setattr(detectors, "load_dotenv", lambda path: None)
	monkeypatch.setenv("GROQ_API_KEY", "mock-groq-key")

	parsed_commits = [
		{"commit_date": "2026-10-01", "commit_message": "stealth deploy cluster", "committed_repo": "acme/infra"},
		{"commit_date": "2026-10-02", "commit_message": "add secret vault sync", "committed_repo": "acme/infra"},
	]

	mock_response_data = {
		"findings": [
			{
				"title": "Stealth infrastructure deployment",
				"committed_repo": "acme/infra",
				"description": "Suspicious cluster and secret sync changes observed",
			}
		],
		"backing_commits": ["stealth deploy cluster", "add secret vault sync"],
	}

	def handler(request: httpx.Request) -> httpx.Response:
		assert request.url == detectors.GROQ_API_URL
		assert request.headers["Authorization"] == "Bearer mock-groq-key"
		return httpx.Response(
			200,
			json={"choices": [{"message": {"content": json.dumps(mock_response_data)}}]},
			request=request,
		)

	findings, backing_commits, error = groq_signal_detector(parsed_commits, transport=httpx.MockTransport(handler))

	assert error is None
	assert len(findings) == 1
	assert findings[0] == {
		"title": "Stealth infrastructure deployment",
		"committed_repo": "acme/infra",
		"description": "Suspicious cluster and secret sync changes observed",
	}
	assert backing_commits == ["stealth deploy cluster", "add secret vault sync"]


def test_detect_signals_with_groq_success(monkeypatch) -> None:
	monkeypatch.setattr(detectors, "load_dotenv", lambda path: None)
	monkeypatch.setenv("GROQ_API_KEY", "mock-groq-key")

	parsed_commits = [
		{"commit_date": "2026-10-01", "commit_message": "add model weights loader", "committed_repo": "acme/models"},
	]

	mock_response_data = {
		"findings": [
			{
				"title": "Unannounced model loader",
				"committed_repo": "acme/models",
				"description": "Found model weights loader in public commits",
			}
		],
		"backing_commits": ["add model weights loader"],
	}

	def handler(request: httpx.Request) -> httpx.Response:
		return httpx.Response(
			200,
			json={"choices": [{"message": {"content": json.dumps(mock_response_data)}}]},
			request=request,
		)

	result = detect_signals(parsed_commits, transport=httpx.MockTransport(handler))

	assert result["detection_source"] == "groq"
	assert len(result["findings"]) == 1
	assert result["findings"][0]["title"] == "Unannounced model loader"
	assert result["backing_commits"] == ["add model weights loader"]
	assert "repositories" not in result
	assert "warnings" not in result



def test_detect_signals_fallback_on_groq_failure(monkeypatch) -> None:
	monkeypatch.setattr(detectors, "load_dotenv", lambda path: None)
	monkeypatch.setenv("GROQ_API_KEY", "mock-groq-key")

	parsed_commits = [
		{"commit_date": "2026-10-01", "commit_message": "commit 1", "committed_repo": "acme/engine"},
		{"commit_date": "2026-10-02", "commit_message": "commit 2", "committed_repo": "acme/engine"},
	]

	def handler(request: httpx.Request) -> httpx.Response:
		return httpx.Response(413, json={"error": {"message": "Rate limit exceeded"}}, request=request)

	result = detect_signals(parsed_commits, transport=httpx.MockTransport(handler))

	# Gracefully falls back to rule-based signal detector
	assert result["detection_source"] == "rule_based"
	assert len(result["repositories"]) == 1
	repo = result["repositories"][0]
	assert repo["committed_repo"] == "acme/engine"
	assert repo["number_of_commits"] == 2
	assert repo["commit_messages"] == ["commit 1", "commit 2"]
	assert len(result["warnings"]) == 1
	assert "rule-based signal detector" in result["warnings"][0]["message"]


def test_detect_signals_fallback_when_api_key_missing(monkeypatch) -> None:
	monkeypatch.setattr(detectors, "load_dotenv", lambda path: None)
	monkeypatch.delenv("GROQ_API_KEY", raising=False)

	parsed_commits = [
		{"commit_date": "2026-10-01", "commit_message": "commit 1", "committed_repo": "acme/core"},
	]

	result = detect_signals(parsed_commits)

	assert result["detection_source"] == "rule_based"
	assert len(result["repositories"]) == 1
	assert result["repositories"][0]["committed_repo"] == "acme/core"
	assert "GROQ_API_KEY is missing" in result["warnings"][0]["message"]


def test_empty_commits_returns_empty_result() -> None:
	result = detect_signals([])
	assert result["detection_source"] == "rule_based"
	assert result["findings"] == []
	assert result["repositories"] == []
	assert result["warnings"] == []


def test_summarize_daily_activity_detects_bursts() -> None:
	commits = [
		# 6 commits on 2026-10-05 in acme/repo-a (burst)
		{"commit_date": "2026-10-05", "commit_message": f"msg {i}", "committed_repo": "acme/repo-a"}
		for i in range(6)
	] + [
		# 2 commits on 2026-10-04 in acme/repo-a (not burst)
		{"commit_date": "2026-10-04", "commit_message": "msg x1", "committed_repo": "acme/repo-a"},
		{"commit_date": "2026-10-04", "commit_message": "msg x2", "committed_repo": "acme/repo-a"},
		# 1 commit on 2026-10-05 in acme/repo-b (not burst)
		{"commit_date": "2026-10-05", "commit_message": "msg y1", "committed_repo": "acme/repo-b"},
	]

	summary = summarize_daily_activity(commits, burst_threshold=5)

	assert summary["total_commits"] == 9
	assert len(summary["burst_days"]) == 1
	burst = summary["burst_days"][0]
	assert burst["commit_date"] == "2026-10-05"
	assert burst["committed_repo"] == "acme/repo-a"
	assert burst["commits_count"] == 6


def test_batch_commits_splits_and_caps() -> None:
	commits = [
		{"commit_date": "2026-10-01", "commit_message": f"msg {i}", "committed_repo": "acme/repo"}
		for i in range(60)
	]

	batches = batch_commits(commits, batch_size=25, max_batches=4)
	assert len(batches) == 3
	assert len(batches[0]) == 25
	assert len(batches[1]) == 25
	assert len(batches[2]) == 10

	# Max batches cap
	capped = batch_commits(commits, batch_size=10, max_batches=2)
	assert len(capped) == 2
	assert len(capped[0]) == 10
	assert len(capped[1]) == 10


def test_merge_findings_and_backing_commits_deduplication() -> None:
	batch1_findings = [
		{"title": "Stealth Repo", "committed_repo": "acme/stealth", "description": "New project"},
		{"title": "Pacing Burst", "committed_repo": "acme/core", "description": "High commit pace"},
	]
	batch2_findings = [
		{"title": "Stealth Repo", "committed_repo": "acme/stealth", "description": "New project duplicate"},
		{"title": "AI Agent Evaluation", "committed_repo": "acme/eval", "description": "Agent evals"},
	]

	merged_f = merge_findings([batch1_findings, batch2_findings])
	assert len(merged_f) == 3
	assert [f["title"] for f in merged_f] == ["Stealth Repo", "Pacing Burst", "AI Agent Evaluation"]

	batch1_backing = ["commit alpha", "commit beta"]
	batch2_backing = ["commit beta", "commit gamma", "  "]

	merged_b = merge_backing_commits([batch1_backing, batch2_backing])
	assert merged_b == ["commit alpha", "commit beta", "commit gamma"]


def test_groq_signal_detector_multibatch_merges_without_duplicates(monkeypatch) -> None:
	monkeypatch.setattr(detectors, "load_dotenv", lambda path: None)
	monkeypatch.setenv("GROQ_API_KEY", "mock-groq-key")

	# 50 commits with batch_size=25 -> 2 batches
	parsed_commits = [
		{"commit_date": "2026-10-01", "commit_message": f"commit {i}", "committed_repo": "acme/repo"}
		for i in range(50)
	]

	call_count = 0

	def handler(request: httpx.Request) -> httpx.Response:
		nonlocal call_count
		call_count += 1
		req_json = json.loads(request.content)
		# Verify each batch includes daily_burst_summary
		assert "daily_burst_summary" in req_json["messages"][1]["content"]

		if call_count == 1:
			batch_resp = {
				"findings": [
					{"title": "Shared Finding", "committed_repo": "acme/repo", "description": "Found in batch 1"}
				],
				"backing_commits": ["commit 0", "commit 1"],
			}
		else:
			batch_resp = {
				"findings": [
					{"title": "Shared Finding", "committed_repo": "acme/repo", "description": "Found in batch 2"},
					{"title": "Batch 2 Unique Finding", "committed_repo": "acme/repo", "description": "Unique desc"},
				],
				"backing_commits": ["commit 1", "commit 25"],
			}

		return httpx.Response(
			200,
			json={"choices": [{"message": {"content": json.dumps(batch_resp)}}]},
			request=request,
		)

	findings, backing_commits, error = groq_signal_detector(
		parsed_commits,
		transport=httpx.MockTransport(handler),
		batch_size=25,
	)

	assert error is None
	assert call_count == 2
	# Merged findings deduplicated "Shared Finding"
	assert len(findings) == 2
	assert findings[0]["title"] == "Shared Finding"
	assert findings[1]["title"] == "Batch 2 Unique Finding"
	# Merged backing commits deduplicated "commit 1"
	assert backing_commits == ["commit 0", "commit 1", "commit 25"]


def test_detect_signals_partial_batch_success_keeps_groq_findings(monkeypatch) -> None:
	monkeypatch.setattr(detectors, "load_dotenv", lambda path: None)
	monkeypatch.setenv("GROQ_API_KEY", "mock-groq-key")

	parsed_commits = [
		{"commit_date": "2026-10-01", "commit_message": f"commit {i}", "committed_repo": "acme/repo"}
		for i in range(50)
	]

	call_count = 0

	def handler(request: httpx.Request) -> httpx.Response:
		nonlocal call_count
		call_count += 1
		if call_count == 1:
			return httpx.Response(
				200,
				json={"choices": [{"message": {"content": json.dumps({
					"findings": [{"title": "Batch 1 Signal", "committed_repo": "acme/repo", "description": "Batch 1 OK"}],
					"backing_commits": ["commit 0"],
				})}}]},
				request=request,
			)
		return httpx.Response(500, request=request)

	result = detect_signals(parsed_commits, transport=httpx.MockTransport(handler))

	# Groq did not genuinely fail completely; 1 batch succeeded, so Groq findings are preserved
	assert result["detection_source"] == "groq"
	assert len(result["findings"]) == 1
	assert result["findings"][0]["title"] == "Batch 1 Signal"
	assert result["backing_commits"] == ["commit 0"]
