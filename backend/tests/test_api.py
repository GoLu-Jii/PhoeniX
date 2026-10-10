from fastapi.testclient import TestClient

from backend.app import main


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
