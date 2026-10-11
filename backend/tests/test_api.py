import json
import httpx
from fastapi.testclient import TestClient

from backend.app import main


def test_investigation_endpoint_returns_collection(monkeypatch) -> None:
	raw_mock = {
		"status": "success",
		"account": {"login": "octocat", "type": "user"},
		"website": {"url": "https://octo.cat", "title": "Octo", "text": "Lots of long text..."},
		"repositories": [
			{
				"name": "hello-world",
				"full_name": "octocat/hello-world",
				"url": "https://github.com/octocat/hello-world",
				"description": "My first repo",
				"topics": ["intro"],
				"language": "Python",
				"languages": {"Python": 1000},
				"created_at": "2020-01-01T00:00:00Z",
				"updated_at": "2026-10-01T00:00:00Z",
				"pushed_at": "2026-10-01T00:00:00Z",
				"evidence_id": "ev_001",
				"recent_commits": [{"sha": "123", "message": "hello"}],
				"weekly_commit_activity": [{"week": "2026-10-04T00:00:00Z", "total": 1}],
			}
		],
		"parsed_commits": [{"commit_date": "2026-10-01", "commit_message": "hello", "committed_repo": "octocat/hello-world"}],
		"detection_source": "rule_based",
		"findings": [],
		"backing_commits": [],
		"analysis": {"stated_focus": "None", "say_do_gaps": []},
		"summary": {"total_public_repositories": 1},
		"repositories_summary": [],
		"warnings": [],
	}
	monkeypatch.setattr(main, "investigate_company", lambda github_url, website_url=None, include_raw=False: raw_mock)

	client = TestClient(main.app)

	# 1. Default request returns COMPACT response (no raw commit arrays, no parsed_commits, no raw text)
	response = client.post(
		"/api/investigations",
		json={"target_url": "octocat"},
	)
	assert response.status_code == 200
	data = response.json()
	assert data["status"] == "success"
	assert "parsed_commits" not in data
	assert len(data["repositories"]) == 1
	repo = data["repositories"][0]
	assert repo["name"] == "hello-world"
	assert repo["recent_commits_count"] == 1
	assert "recent_commits" not in repo
	assert "weekly_commit_activity" not in repo
	assert "text" not in (data["website"] or {})

	# 2. Debug / include_raw request returns FULL RAW response
	raw_response = client.post(
		"/api/investigations",
		json={"target_url": "octocat", "include_raw": True},
	)
	assert raw_response.status_code == 200
	raw_data = raw_response.json()
	assert "parsed_commits" in raw_data
	assert "recent_commits" in raw_data["repositories"][0]
	assert "weekly_commit_activity" in raw_data["repositories"][0]
	assert "text" in (raw_data["website"] or {})


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


def test_investigation_endpoint_debug_flags(monkeypatch) -> None:
	raw_mock = {
		"status": "success",
		"account": {"login": "debug-org"},
		"website": {"url": "https://debug.com", "title": "Debug Org", "text": "Scraped body content"},
		"repositories": [
			{
				"name": "debug-repo",
				"full_name": "debug-org/debug-repo",
				"url": "https://github.com/debug-org/debug-repo",
				"description": "Debug repo",
				"topics": [],
				"language": "Go",
				"languages": {"Go": 500},
				"created_at": "2024-01-01T00:00:00Z",
				"updated_at": "2026-10-01T00:00:00Z",
				"pushed_at": "2026-10-01T00:00:00Z",
				"evidence_id": "ev_001",
				"recent_commits": [{"sha": "abc", "message": "commit abc"}],
				"weekly_commit_activity": [{"week": "2026-10-04T00:00:00Z", "total": 2}],
			}
		],
		"parsed_commits": [{"commit_date": "2026-10-01", "commit_message": "commit abc", "committed_repo": "debug-org/debug-repo"}],
		"detection_source": "groq",
		"findings": [{"title": "Finding", "committed_repo": "debug-org/debug-repo", "description": "Desc"}],
		"backing_commits": ["commit abc"],
		"analysis": {"stated_focus": "Focus", "say_do_gaps": []},
		"summary": {"total_public_repositories": 1},
		"repositories_summary": [],
		"warnings": [],
	}
	monkeypatch.setattr(main, "investigate_company", lambda github_url, website_url=None, include_raw=False: raw_mock)
	client = TestClient(main.app)

	# 1. Query param ?debug=true returns full raw response
	res_debug = client.post("/api/investigations?debug=true", json={"target_url": "debug-org"})
	assert res_debug.status_code == 200
	data_debug = res_debug.json()
	assert "parsed_commits" in data_debug
	assert "recent_commits" in data_debug["repositories"][0]
	assert "weekly_commit_activity" in data_debug["repositories"][0]
	assert "text" in data_debug["website"]

	# 2. Query param ?include_raw=true returns full raw response
	res_raw_param = client.post("/api/investigations?include_raw=true", json={"target_url": "debug-org"})
	assert res_raw_param.status_code == 200
	assert "parsed_commits" in res_raw_param.json()

	# 3. Body flag debug: True returns full raw response
	res_body_debug = client.post("/api/investigations", json={"target_url": "debug-org", "debug": True})
	assert res_body_debug.status_code == 200
	assert "parsed_commits" in res_body_debug.json()

	# 4. Default without flags returns compact response
	res_default = client.post("/api/investigations", json={"target_url": "debug-org"})
	assert res_default.status_code == 200
	data_default = res_default.json()
	assert "parsed_commits" not in data_default
	assert "recent_commits" not in data_default["repositories"][0]
	assert "weekly_commit_activity" not in data_default["repositories"][0]
	assert "text" not in data_default["website"]
	assert data_default["repositories"][0]["recent_commits_count"] == 1


def test_investigate_company_end_to_end_two_stage_groq_mocked(monkeypatch) -> None:
	from backend.app import analysis, detectors, investigation

	monkeypatch.setattr(analysis, "load_dotenv", lambda path: None)
	monkeypatch.setattr(detectors, "load_dotenv", lambda path: None)
	monkeypatch.setenv("GROQ_API_KEY", "mock-groq-key")

	mock_github_data = {
		"status": "success",
		"account": {"login": "cloud-corp", "name": "Cloud Corp", "type": "organization"},
		"repositories": [
			{
				"name": "infra",
				"full_name": "cloud-corp/infra",
				"url": "https://github.com/cloud-corp/infra",
				"description": "Infra tooling",
				"topics": ["cloud", "k8s"],
				"language": "Go",
				"languages": {"Go": 2000},
				"created_at": "2024-01-01T00:00:00Z",
				"updated_at": "2026-10-01T00:00:00Z",
				"pushed_at": "2026-10-01T00:00:00Z",
				"recent_commits": [
					{"sha": "c1", "message": "feat: add k8s operator", "committed_at": "2026-10-01T12:00:00Z"},
					{"sha": "c2", "message": "fix: update helm chart", "committed_at": "2026-10-02T12:00:00Z"},
				],
				"weekly_commit_activity": [{"week": "2026-09-27T00:00:00Z", "total": 2}],
			}
		],
		"summary": {"total_public_repositories": 1},
		"warnings": [],
	}
	mock_website_data = {
		"status": "success",
		"url": "https://cloudcorp.io",
		"title": "Cloud Corp - Kubernetes Automation",
		"description": "Automating cloud native infrastructure.",
		"headings": ["Kubernetes Automation"],
		"text": "Cloud Corp automates Kubernetes clusters and infrastructure deployments.",
	}

	monkeypatch.setattr(investigation, "collect_github_account", lambda url, transport=None: mock_github_data)
	monkeypatch.setattr(investigation, "collect_website", lambda url, transport=None: mock_website_data)

	groq_calls = []

	def groq_handler(request: httpx.Request) -> httpx.Response:
		groq_calls.append(request)
		req_body = json.loads(request.content)
		# Distinguish between detector call and analysis call by input payload structure
		user_content = json.loads(req_body["messages"][1]["content"])
		if "daily_burst_summary" in user_content:
			# Stage 1: Detector response
			return httpx.Response(
				200,
				json={
					"choices": [
						{
							"message": {
								"content": json.dumps({
									"findings": [
										{
											"title": "Active Kubernetes tooling",
											"committed_repo": "cloud-corp/infra",
											"description": "Observed commits expanding k8s operators and helm charts.",
										}
									],
									"backing_commits": ["feat: add k8s operator"],
								})
							}
						}
					]
				},
				request=request,
			)
		# Stage 2: Analysis response
		return httpx.Response(
			200,
			json={
				"choices": [
					{
						"message": {
							"content": json.dumps({
								"stated_focus": "Automating cloud native infrastructure and Kubernetes.",
								"engineering_reality": "Public code directly demonstrates active development of Kubernetes operator tooling.",
								"say_do_gaps": [
									{
										"claim": "Kubernetes Automation",
										"reality": "Observed active engineering in cloud-corp/infra",
										"verdict": "supported",
									}
								],
								"strategic_verdict": "Public engineering directly validates stated product positioning without uncorroborated gaps.",
							})
						}
					}
				]
			},
			request=request,
		)

	transport = httpx.MockTransport(groq_handler)

	# 1. Test compact mode (default)
	res_compact = investigation.investigate_company(
		"https://github.com/cloud-corp",
		"https://cloudcorp.io",
		include_raw=False,
		transport=transport,
	)

	assert len(groq_calls) == 2
	assert res_compact["detection_source"] == "groq"
	assert res_compact["analysis"]["analysis_source"] == "groq"
	assert res_compact["analysis"]["say_do_gaps"][0]["verdict"] == "supported"
	assert "parsed_commits" not in res_compact
	repo_compact = res_compact["repositories"][0]
	assert "recent_commits" not in repo_compact
	assert "weekly_commit_activity" not in repo_compact
	assert repo_compact["recent_commits_count"] == 2
	assert "text" not in res_compact["website"]

	# 2. Test raw mode (include_raw=True)
	res_raw = investigation.investigate_company(
		"https://github.com/cloud-corp",
		"https://cloudcorp.io",
		include_raw=True,
		transport=transport,
	)
	assert "parsed_commits" in res_raw
	assert "recent_commits" in res_raw["repositories"][0]
	assert "weekly_commit_activity" in res_raw["repositories"][0]
	assert "text" in res_raw["website"]
