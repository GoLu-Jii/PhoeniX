from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import parse_qs

import httpx
import pytest

from backend.app.collectors import github as github_collector
from backend.app.collectors.github import collect_github_account, normalize_github_account


@pytest.mark.parametrize(
	("value", "expected"),
	[
		("octocat", "octocat"),
		("https://github.com/octocat/", "octocat"),
	],
)
def test_normalize_github_account(value: str, expected: str) -> None:
	assert normalize_github_account(value) == expected


@pytest.mark.parametrize(
	"value",
	["", "not a username", "https://example.com/octocat", "https://github.com/octocat/repo"],
)
def test_reject_invalid_github_account(value: str) -> None:
	with pytest.raises(ValueError):
		normalize_github_account(value)


def test_collect_github_account_summarizes_mocked_data(monkeypatch: pytest.MonkeyPatch) -> None:
	monkeypatch.delenv("GITHUB_TOKEN", raising=False)
	stats_requests = 0
	committed_at = (datetime.now(timezone.utc) - timedelta(days=3)).isoformat()
	week = int((datetime.now(timezone.utc) - timedelta(days=7)).timestamp())

	def handler(request: httpx.Request) -> httpx.Response:
		nonlocal stats_requests
		path = request.url.path
		if path == "/users/acme-labs":
			return httpx.Response(200, json={"login": "acme-labs", "name": "Acme", "type": "Organization"})
		if path == "/orgs/acme-labs/repos":
			assert request.url.params["type"] == "public"
			assert request.url.params["per_page"] == "10"
			assert request.url.params["sort"] == "pushed"
			return httpx.Response(
				200,
				json=[
					{
						"name": "engine",
						"full_name": "acme-labs/engine",
						"html_url": "https://github.com/acme-labs/engine",
						"description": "Core project",
						"topics": ["python"],
						"language": "Python",
						"created_at": "2025-01-01T00:00:00Z",
						"updated_at": "2026-10-01T00:00:00Z",
						"pushed_at": "2026-10-01T00:00:00Z",
						"private": False,
						"owner": {"login": "acme-labs"},
					}
				],
			)
		if path == "/repos/acme-labs/engine/languages":
			return httpx.Response(200, json={"Python": 1200, "Rust": 300})
		if path == "/repos/acme-labs/engine/commits":
			assert parse_qs(request.url.query.decode())["per_page"] == ["50"]
			return httpx.Response(
				200,
				json=[
					{
						"sha": "abc123",
						"html_url": "https://github.com/acme-labs/engine/commit/abc123",
						"commit": {
							"message": "Add feature",
							"author": {"date": committed_at},
						},
					}
				],
			)
		if path == "/repos/acme-labs/engine/stats/commit_activity":
			stats_requests += 1
			if stats_requests == 1:
				return httpx.Response(202)
			return httpx.Response(200, json=[{"week": week, "total": 4, "days": [0, 1, 0, 1, 0, 1, 1]}])
		return httpx.Response(404)

	result = collect_github_account("https://github.com/acme-labs", transport=httpx.MockTransport(handler))

	assert result["status"] == "success"
	assert result["account"]["type"] == "organization"
	assert result["repositories"][0]["topics"] == ["python"]
	assert result["repositories"][0]["recent_commits"][0]["sha"] == "abc123"
	assert result["summary"]["language_bytes"] == {"Python": 1200, "Rust": 300}
	assert result["summary"]["weekly_commit_activity"][0]["total"] == 4
	assert result["summary"]["average_weekly_commits"] == 4
	assert stats_requests == 2


def test_account_failure_returns_warning_without_raising() -> None:
	def handler(request: httpx.Request) -> httpx.Response:
		return httpx.Response(503)

	result = collect_github_account("octocat", transport=httpx.MockTransport(handler))

	assert result["status"] == "unavailable"
	assert result["repositories"] == []
	assert result["warnings"][0]["scope"] == "account"
	assert "503" in result["warnings"][0]["message"]


def test_headers_load_token_from_project_root_env(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
	monkeypatch.setattr(github_collector, "PROJECT_ROOT", tmp_path)
	monkeypatch.delenv("GITHUB_TOKEN", raising=False)
	(tmp_path / ".env").write_text("GITHUB_TOKEN=test-token\n", encoding="utf-8")

	assert github_collector._headers()["Authorization"] == "Bearer test-token"


def test_forbidden_rate_limit_warning_is_distinct() -> None:
	request = httpx.Request("GET", "https://api.github.com/users/octocat")
	response = httpx.Response(
		403,
		headers={"X-RateLimit-Remaining": "0"},
		json={"message": "API rate limit exceeded"},
		request=request,
	)
	error = httpx.HTTPStatusError("forbidden", request=request, response=response)

	warning = github_collector._request_failure("account", error)

	assert warning["message"] == "GitHub rate limit exceeded for account."


def test_repository_data_failure_preserves_account_and_repository() -> None:
	def handler(request: httpx.Request) -> httpx.Response:
		path = request.url.path
		if path == "/users/octocat":
			return httpx.Response(200, json={"login": "octocat", "type": "User"})
		if path == "/users/octocat/repos":
			return httpx.Response(
				200,
				json=[
					{
						"name": "hello-world",
						"full_name": "octocat/hello-world",
						"private": False,
					"owner": {"login": "octocat"},
					}
				],
			)
		if path == "/repos/octocat/hello-world/languages":
			return httpx.Response(503)
		if path == "/repos/octocat/hello-world/commits":
			return httpx.Response(200, json=[])
		if path == "/repos/octocat/hello-world/stats/commit_activity":
			return httpx.Response(200, json=[])
		return httpx.Response(404)

	result = collect_github_account("octocat", transport=httpx.MockTransport(handler))

	assert result["status"] == "partial"
	assert result["account"]["login"] == "octocat"
	assert result["repositories"][0]["full_name"] == "octocat/hello-world"
	assert result["repositories"][0]["languages"] == {}
	assert result["warnings"][0]["scope"] == "languages"
