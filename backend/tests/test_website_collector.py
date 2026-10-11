import httpx
import pytest

from backend.app.collectors.website import collect_website, normalize_website_url


def test_normalize_website_url_adds_scheme_and_cleans() -> None:
	assert normalize_website_url("example.com") == "https://example.com/"
	assert normalize_website_url("http://acme.org/about?ref=123#team") == "http://acme.org/about"


@pytest.mark.parametrize(
	"invalid_url",
	[
		"",
		"   ",
		"ftp://example.com",
		"http://localhost",
		"https://127.0.0.1/admin",
		"http://192.168.1.1",
		"http://10.0.0.5",
		"http://test.local",
	],
)
def test_normalize_website_url_rejects_ssrf_and_invalid(invalid_url: str) -> None:
	with pytest.raises(ValueError):
		normalize_website_url(invalid_url)


def test_collect_website_extracts_clean_content() -> None:
	html_content = """
	<!DOCTYPE html>
	<html>
	<head>
		<title>Acme AI - Next-Gen Intelligence</title>
		<meta name="description" content="Acme builds state-of-the-art AI infrastructure." />
		<style>body { color: red; }</style>
		<script>console.log("secret");</script>
	</head>
	<body>
		<header><nav><a href="/">Home</a></nav></header>
		<h1>Transform Your Infrastructure</h1>
		<h2>Enterprise AI Agents</h2>
		<p>We empower companies to ship autonomous agents with complete transparency.</p>
		<p>Our open source core powers thousands of developers worldwide.</p>
		<footer>Copyright 2026 Acme Inc</footer>
	</body>
	</html>
	"""

	def handler(request: httpx.Request) -> httpx.Response:
		return httpx.Response(
			200,
			text=html_content,
			headers={"Content-Type": "text/html; charset=utf-8"},
			request=request,
		)

	result = collect_website("https://acme.ai", transport=httpx.MockTransport(handler))

	assert result["status"] == "success"
	assert result["title"] == "Acme AI - Next-Gen Intelligence"
	assert result["description"] == "Acme builds state-of-the-art AI infrastructure."
	assert "Transform Your Infrastructure" in result["headings"]
	assert "Enterprise AI Agents" in result["headings"]
	assert "autonomous agents" in result["text"]
	assert "open source core" in result["text"]
	assert "console.log" not in result["text"]
	assert "Copyright" not in result["text"]
	assert result["warnings"] == []


def test_collect_website_handles_http_failure_gracefully() -> None:
	def handler(request: httpx.Request) -> httpx.Response:
		return httpx.Response(500, request=request)

	result = collect_website("https://failing-site.com", transport=httpx.MockTransport(handler))

	assert result["status"] == "unavailable"
	assert result["title"] is None
	assert len(result["warnings"]) == 1
	assert "500" in result["warnings"][0]["message"]
