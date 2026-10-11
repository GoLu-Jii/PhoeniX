from fastapi.testclient import TestClient

from backend.app import main


def test_investigation_endpoint_returns_collection(monkeypatch) -> None:
	expected = {
		"status": "success",
		"account": {"login": "octocat", "type": "user"},
		"website": None,
		"repositories": [],
		"parsed_commits": [],
		"detection_source": "rule_based",
		"findings": [],
		"backing_commits": [],
		"analysis": {"stated_focus": "None", "say_do_gaps": []},
		"warnings": [],
	}
	monkeypatch.setattr(main, "investigate_company", lambda github_url, website_url=None: expected)

	response = TestClient(main.app).post(
		"/api/investigations",
		json={"target_url": "octocat"},
	)

	assert response.status_code == 200
	assert response.json() == expected


def test_investigation_endpoint_accepts_github_and_website_urls(monkeypatch) -> None:
	captured_calls = []

	def mock_investigate(github_url, website_url=None):
		captured_calls.append((github_url, website_url))
		return {
			"status": "success",
			"account": {"login": "octocat"},
			"website": {"title": "Acme"},
			"findings": [],
			"analysis": {"stated_focus": "AI Tools"},
		}

	monkeypatch.setattr(main, "investigate_company", mock_investigate)

	response = TestClient(main.app).post(
		"/api/investigations",
		json={"github_url": "https://github.com/octocat", "website_url": "https://acme.ai"},
	)

	assert response.status_code == 200
	assert captured_calls == [("https://github.com/octocat", "https://acme.ai")]

	# Also test /api/analyze alias
	analyze_response = TestClient(main.app).post(
		"/api/analyze",
		json={"github_url": "https://github.com/octocat", "website_url": "https://acme.ai"},
	)
	assert analyze_response.status_code == 200
	assert len(captured_calls) == 2


def test_signals_endpoint_with_target_url(monkeypatch) -> None:
	parsed_commits = [
		{"commit_date": "2026-10-01", "commit_message": "deploy new infra", "committed_repo": "acme/work"},
	]
	monkeypatch.setattr(
		main,
		"investigate_github",
		lambda target_url: {
			"status": "success",
			"account": {"login": "acme", "type": "organization"},
			"repositories": [],
			"parsed_commits": parsed_commits,
			"warnings": [],
		},
	)
	monkeypatch.setattr(
		main,
		"detect_signals",
		lambda commits: {
			"detection_source": "groq",
			"findings": [{"title": "Infra change", "committed_repo": "acme/work", "description": "Infra update"}],
			"backing_commits": ["deploy new infra"],
		},
	)

	response = TestClient(main.app).post("/api/signals", json={"target_url": "https://github.com/acme"})

	assert response.status_code == 200
	data = response.json()
	assert data == {
		"findings": [{"title": "Infra change", "committed_repo": "acme/work", "description": "Infra update"}],
		"backing_commits": ["deploy new infra"],
	}


def test_signals_endpoint_with_direct_parsed_commits(monkeypatch) -> None:
	parsed_commits = [
		{"commit_date": "2026-10-05", "commit_message": "direct commit", "committed_repo": "acme/repo"},
	]
	monkeypatch.setattr(
		main,
		"detect_signals",
		lambda commits: {
			"detection_source": "rule_based",
			"findings": [],
			"backing_commits": ["direct commit"],
			"repositories": [{"committed_repo": "acme/repo", "number_of_commits": 1, "commit_messages": ["direct commit"]}],
			"warnings": [],
		},
	)

	response = TestClient(main.app).post(
		"/api/signals",
		json={"parsed_commits": parsed_commits},
	)

	assert response.status_code == 200
	data = response.json()
	assert data["status"] == "success"
	assert data["detection_source"] == "rule_based"
	assert data["parsed_commits"] == parsed_commits
	assert data["repositories"][0]["committed_repo"] == "acme/repo"


def test_signals_endpoint_automatically_uses_latest_investigation(monkeypatch) -> None:
	parsed_commits = [
		{"commit_date": "2026-10-08", "commit_message": "cached commit", "committed_repo": "acme/cached"},
	]
	monkeypatch.setattr(
		main,
		"investigate_company",
		lambda github_url, website_url=None: {
			"status": "success",
			"account": {"login": "acme", "type": "organization"},
			"repositories": [],
			"parsed_commits": parsed_commits,
			"warnings": [],
		},
	)
	monkeypatch.setattr(
		main,
		"detect_signals",
		lambda commits: {
			"detection_source": "groq",
			"findings": [{"title": "Cached finding", "committed_repo": "acme/cached", "description": "Cached desc"}],
			"backing_commits": ["cached commit"],
		},
	)

	client = TestClient(main.app)
	# 1. Run investigation
	inv_response = client.post("/api/investigations", json={"target_url": "https://github.com/acme"})
	assert inv_response.status_code == 200

	# 2. GET /api/signals with NO body
	get_response = client.get("/api/signals")
	assert get_response.status_code == 200
	assert get_response.json() == {
		"findings": [{"title": "Cached finding", "committed_repo": "acme/cached", "description": "Cached desc"}],
		"backing_commits": ["cached commit"],
	}

	# 3. POST /api/signals with empty body {}
	post_response = client.post("/api/signals", json={})
	assert post_response.status_code == 200
	assert post_response.json() == {
		"findings": [{"title": "Cached finding", "committed_repo": "acme/cached", "description": "Cached desc"}],
		"backing_commits": ["cached commit"],
	}


def test_investigation_endpoint_requires_target_url() -> None:
	response = TestClient(main.app).post(
		"/api/investigations",
		json={},
	)
	assert response.status_code == 422
