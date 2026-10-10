from fastapi.testclient import TestClient

from backend.app import main
from backend.app import investigation


def test_investigation_endpoint_returns_collection(monkeypatch) -> None:
	expected = {
		"status": "success",
		"account": {"login": "octocat", "type": "user"},
		"repositories": [],
		"summary": {},
		"warnings": [],
	}
	monkeypatch.setattr(main, "investigate_github", lambda target_url: expected)

	response = TestClient(main.app).post(
		"/api/investigations",
		json={"target_url": "octocat"},
	)

	assert response.status_code == 200
	assert response.json() == expected


def test_investigation_endpoint_returns_repository_findings(monkeypatch) -> None:
	from datetime import datetime, timezone

	repository = {
		"full_name": "acme/new-project",
		"url": "https://github.com/acme/new-project",
		"created_at": datetime.now(timezone.utc).isoformat(),
		"weekly_commit_activity": [],
	}
	monkeypatch.setattr(
		investigation,
		"collect_github_account",
		lambda target_url, *, transport=None: {"status": "success", "repositories": [repository]},
	)

	response = TestClient(main.app).post(
		"/api/investigations",
		json={"target_url": "acme"},
	)

	assert response.status_code == 200
	data = response.json()
	assert data["repositories"][0]["evidence_id"] == "ev_001"
	assert data["findings"][0]["source_url"] == repository["url"]
