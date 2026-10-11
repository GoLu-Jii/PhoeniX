from typing import Any

import httpx

from .analysis import analyze_company
from .collectors.github import collect_github_account
from .collectors.website import collect_website
from .detectors import detect_signals, parse_github_commits


def investigate_github(
	target_url: str,
	*,
	transport: httpx.BaseTransport | None = None,
) -> dict[str, Any]:
	result = collect_github_account(target_url, transport=transport)
	for repository_index, repository in enumerate(result.get("repositories", []), start=1):
		repository["evidence_id"] = f"ev_{repository_index:03d}"

	parsed_commits = parse_github_commits(result.get("repositories", []))
	signals_data = detect_signals(parsed_commits, transport=transport)

	result["parsed_commits"] = parsed_commits
	result["detection_source"] = signals_data.get("detection_source")
	result["findings"] = signals_data.get("findings", [])
	result["backing_commits"] = signals_data.get("backing_commits", [])
	result["repositories_summary"] = signals_data.get("repositories", [])
	result["warnings"] = [*result.get("warnings", []), *signals_data.get("warnings", [])]
	return result


def investigate_company(
	github_url: str,
	website_url: str | None = None,
	*,
	transport: httpx.BaseTransport | None = None,
) -> dict[str, Any]:
	"""
	Complete end-to-end investigation:
	1. Collects and parses GitHub traces.
	2. Runs signal detection (Groq + rule fallback).
	3. Safely scrapes company website if provided.
	4. Runs final company analysis comparing website claims with code reality.
	"""
	result = investigate_github(github_url, transport=transport)

	website_data = None
	if website_url:
		website_data = collect_website(website_url, transport=transport)
		result["website"] = website_data
		if website_data.get("warnings"):
			result["warnings"].extend(website_data["warnings"])
	else:
		result["website"] = None

	final_analysis = analyze_company(result, website_data, transport=transport)
	result["analysis"] = final_analysis
	if final_analysis.get("warnings"):
		result["warnings"].extend(final_analysis["warnings"])

	return result
