import ipaddress
import re
from typing import Any
from urllib.parse import urlsplit, urlunsplit

import httpx
from bs4 import BeautifulSoup

REQUEST_TIMEOUT = 8.0
MAX_HTML_BYTES = 1_048_576  # 1 MB
MAX_TEXT_CHARS = 3000
MAX_HEADINGS = 15

DISALLOWED_HOSTS = {
	"localhost",
	"127.0.0.1",
	"0.0.0.0",
	"::1",
}


def normalize_website_url(value: str) -> str:
	candidate = value.strip()
	if not candidate:
		raise ValueError("Enter a company website URL.")

	if "://" in candidate:
		scheme = candidate.split("://", 1)[0].lower()
		if scheme not in {"http", "https"}:
			raise ValueError("Website URL must use HTTP or HTTPS.")
	else:
		candidate = f"https://{candidate}"

	parsed = urlsplit(candidate)
	if parsed.scheme not in {"http", "https"}:
		raise ValueError("Website URL must use HTTP or HTTPS.")

	hostname = (parsed.hostname or "").strip().lower()
	if not hostname:
		raise ValueError("Enter a valid website URL with a host name.")

	if hostname in DISALLOWED_HOSTS or hostname.endswith(".local") or hostname.endswith(".internal"):
		raise ValueError(f"Access to private/local host '{hostname}' is not allowed.")

	# Check if host is a private/reserved IP
	is_private_ip = False
	try:
		ip = ipaddress.ip_address(hostname)
		if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved:
			is_private_ip = True
	except ValueError:
		# Not a raw IP address; valid domain name
		pass

	if is_private_ip:
		raise ValueError(f"Access to private IP address '{hostname}' is not allowed.")

	# Clean query and fragment
	return urlunsplit((parsed.scheme, hostname, parsed.path or "/", "", ""))



def _extract_page_content(html: str) -> dict[str, Any]:
	soup = BeautifulSoup(html, "html.parser")

	# Remove non-content elements
	for element in soup(["script", "style", "noscript", "svg", "header", "footer", "nav", "iframe"]):
		element.decompose()

	# Title
	title = ""
	if soup.title and soup.title.string:
		title = soup.title.string.strip()

	# Meta description
	meta_desc = ""
	desc_tag = soup.find("meta", attrs={"name": re.compile(r"^description$", re.I)}) or soup.find(
		"meta", attrs={"property": re.compile(r"^og:description$", re.I)}
	)
	if desc_tag and desc_tag.get("content"):
		meta_desc = str(desc_tag["content"]).strip()

	# Headings (h1, h2, h3)
	headings: list[str] = []
	seen_headings = set()
	for h in soup.find_all(["h1", "h2", "h3"]):
		text = " ".join(h.get_text().split())
		if text and len(text) > 3 and text.casefold() not in seen_headings:
			seen_headings.add(text.casefold())
			headings.append(text)
			if len(headings) >= MAX_HEADINGS:
				break

	# Paragraph and text content
	text_blocks: list[str] = []
	seen_blocks = set()
	for tag in soup.find_all(["p", "li", "article", "section"]):
		block = " ".join(tag.get_text().split())
		if len(block) >= 20 and block.casefold() not in seen_blocks:
			seen_blocks.add(block.casefold())
			text_blocks.append(block)

	full_text = "\n".join(text_blocks)
	if len(full_text) > MAX_TEXT_CHARS:
		full_text = full_text[:MAX_TEXT_CHARS].rsplit(" ", 1)[0] + "..."

	return {
		"title": title,
		"description": meta_desc,
		"headings": headings,
		"text": full_text,
	}


def collect_website(
	value: str,
	*,
	transport: httpx.BaseTransport | None = None,
) -> dict[str, Any]:
	"""
	Safely fetches a company website homepage and extracts basic details:
	title, meta description, headings, and meaningful text content.
	"""
	warnings: list[dict[str, str]] = []
	result: dict[str, Any] = {
		"status": "unavailable",
		"url": value,
		"title": None,
		"description": None,
		"headings": [],
		"text": "",
		"warnings": warnings,
	}

	try:
		url = normalize_website_url(value)
		result["url"] = url
	except ValueError as error:
		warnings.append({"scope": "website", "message": str(error)})
		return result

	headers = {
		"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) PhoenixBot/1.0",
		"Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
		"Accept-Language": "en-US,en;q=0.5",
	}

	try:
		with httpx.Client(
			timeout=REQUEST_TIMEOUT,
			transport=transport,
			follow_redirects=True,
			max_redirects=3,
		) as client:
			response = client.get(url, headers=headers)

			# Re-validate destination if redirected
			final_host = (response.url.host or "").lower()
			if final_host in DISALLOWED_HOSTS:
				warnings.append(
					{"scope": "website", "message": f"Redirected to disallowed private host '{final_host}'."}
				)
				return result

			response.raise_for_status()

			# Check content length
			content_bytes = response.content
			if len(content_bytes) > MAX_HTML_BYTES:
				content_bytes = content_bytes[:MAX_HTML_BYTES]
				warnings.append(
					{"scope": "website", "message": "Website response exceeded 1 MB and was truncated."}
				)

			content_type = response.headers.get("content-type", "").lower()
			if "text/html" not in content_type and "application/xhtml" not in content_type:
				warnings.append(
					{"scope": "website", "message": f"Website returned non-HTML content type: {content_type}."}
				)

			extracted = _extract_page_content(response.text)
			result.update(
				{
					"status": "success",
					"title": extracted["title"] or None,
					"description": extracted["description"] or None,
					"headings": extracted["headings"],
					"text": extracted["text"],
				}
			)
			return result

	except httpx.HTTPStatusError as error:
		warnings.append(
			{
				"scope": "website",
				"message": f"Website returned HTTP {error.response.status_code}.",
			}
		)
		return result
	except httpx.TimeoutException:
		warnings.append(
			{
				"scope": "website",
				"message": f"Website request timed out after {REQUEST_TIMEOUT}s.",
			}
		)
		return result
	except Exception as error:
		warnings.append(
			{
				"scope": "website",
				"message": f"Website request failed: {error}",
			}
		)
		return result
