import json
import httpx

from backend.app import analysis
from backend.app.analysis import analyze_company


def test_analyze_company_groq_success(monkeypatch) -> None:
	monkeypatch.setattr(analysis, "load_dotenv", lambda path: None)
	monkeypatch.setenv("GROQ_API_KEY", "mock-groq-key")

	github_data = {
		"account": {"login": "acme-corp", "name": "Acme Corp"},
		"findings": [
			{"title": "Stealth Kubernetes deployment", "committed_repo": "acme/deploy", "description": "New deploy repos and k8s cluster tooling"}
		],
		"backing_commits": ["Stealth k8s deploy"],
		"repositories": [{"committed_repo": "acme/deploy", "number_of_commits": 1}],
	}

	website_data = {
		"url": "https://acme.com",
		"title": "Acme - Consumer AI Chat",
		"description": "The friendliest AI chat interface for everyday users.",
		"headings": ["Chat with AI", "Simple and Beautiful"],
		"text": "Acme focuses on simple chat applications for consumers.",
	}

	mock_response = {
		"stated_focus": "Consumer AI chat application.",
		"engineering_reality": "Significant quiet engineering in enterprise Kubernetes deployment tooling.",
		"say_do_gaps": [
			{
				"claim": "Consumer AI chat positioning",
				"reality": "Unannounced deployment infrastructure in acme/deploy",
				"verdict": "unannounced_move",
			}
		],
		"strategic_verdict": "Pivoting toward platform infrastructure despite consumer front-end marketing.",
	}

	def handler(request: httpx.Request) -> httpx.Response:
		assert request.url == analysis.GROQ_API_URL
		req_body = json.loads(request.content)
		user_content = json.loads(req_body["messages"][1]["content"])
		assert "merged_findings" in user_content
		assert "website_content" in user_content
		assert "backing_commits" not in user_content
		assert "repositories" not in user_content
		return httpx.Response(
			200,
			json={"choices": [{"message": {"content": json.dumps(mock_response)}}]},
			request=request,
		)

	result = analyze_company(github_data, website_data, transport=httpx.MockTransport(handler))

	assert result["analysis_source"] == "groq"
	assert result["stated_focus"] == "Consumer AI chat application."
	assert "Kubernetes deployment" in result["engineering_reality"]
	assert len(result["say_do_gaps"]) == 1
	assert result["say_do_gaps"][0]["verdict"] == "unannounced_move"
	assert "Pivoting toward" in result["strategic_verdict"]
	assert result["warnings"] == []


def test_analyze_company_fallback_when_api_key_missing(monkeypatch) -> None:
	monkeypatch.setattr(analysis, "load_dotenv", lambda path: None)
	monkeypatch.delenv("GROQ_API_KEY", raising=False)

	github_data = {
		"account": {"login": "acme-corp", "name": "Acme"},
		"findings": [
			{"title": "Unannounced internal tools", "committed_repo": "acme/tools", "description": "Active internal tooling"}
		],
		"backing_commits": ["add tools"],
		"repositories": [{"committed_repo": "acme/tools"}],
	}

	website_data = {
		"title": "Acme AI",
		"description": "Next generation AI",
		"text": "Our mission is AI.",
	}

	result = analyze_company(github_data, website_data)

	assert result["analysis_source"] == "rule_based"
	assert result["stated_focus"] == "Next generation AI"
	assert "Acme" in result["engineering_reality"]
	assert len(result["say_do_gaps"]) == 1

	assert len(result["warnings"]) == 1
	assert "rule-based analysis used" in result["warnings"][0]["message"]


def test_analyze_company_retries_on_429_and_succeeds(monkeypatch) -> None:
	monkeypatch.setattr(analysis, "load_dotenv", lambda path: None)
	monkeypatch.setattr(analysis.time, "sleep", lambda s: None)
	monkeypatch.setenv("GROQ_API_KEY", "mock-groq-key")

	calls = []
	mock_response = {
		"stated_focus": "Fast cloud infrastructure.",
		"engineering_reality": "Heavy investment in developer tooling.",
		"say_do_gaps": [],
		"strategic_verdict": "On track.",
	}

	def handler(request: httpx.Request) -> httpx.Response:
		calls.append(request)
		if len(calls) == 1:
			return httpx.Response(429, headers={"retry-after": "1"}, request=request)
		return httpx.Response(
			200,
			json={"choices": [{"message": {"content": json.dumps(mock_response)}}]},
			request=request,
		)

	github_data = {"account": {"login": "test"}, "findings": [], "repositories": []}
	website_data = {"title": "Test Title"}

	result = analyze_company(github_data, website_data, transport=httpx.MockTransport(handler))

	assert len(calls) == 2
	assert result["analysis_source"] == "groq"
	assert result["stated_focus"] == "Fast cloud infrastructure."
	assert result["warnings"] == []
