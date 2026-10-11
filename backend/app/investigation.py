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


def compact_investigation_result(result: dict[str, Any]) -> dict[str, Any]:
	"""
	Produces a clean, frontend-ready investigation payload:
	- Retains actionable intelligence: analysis, findings, backing_commits, account, summary, website metadata.
	- Omits raw parsed_commits list.
	- Trims repository objects by omitting the heavy 50-commit recent_commits arrays and 52-week activity matrices.
	- Trims raw scraped webpage body text from website, retaining structured titles, descriptions, and headings.
	"""
	compact_repos = []
	for r in result.get("repositories", []):
		if not isinstance(r, dict):
			continue
		commits = r.get("recent_commits")
		if isinstance(commits, list):
			commits_count = len(commits)
		else:
			commits_count = r.get("recent_commits_count", 0)

		compact_repos.append(
			{
				"name": r.get("name"),
				"full_name": r.get("full_name"),
				"url": r.get("url"),
				"description": r.get("description"),
				"topics": r.get("topics", []),
				"language": r.get("language"),
				"languages": r.get("languages", {}),
				"created_at": r.get("created_at"),
				"updated_at": r.get("updated_at"),
				"pushed_at": r.get("pushed_at"),
				"evidence_id": r.get("evidence_id"),
				"recent_commits_count": commits_count,
			}
		)

	website_data = result.get("website")
	compact_website = None
	if isinstance(website_data, dict):
		compact_website = {
			"url": website_data.get("url"),
			"title": website_data.get("title"),
			"description": website_data.get("description"),
			"headings": website_data.get("headings", []),
			"status": website_data.get("status"),
		}

	return {
		"status": result.get("status", "success"),
		"account": result.get("account"),
		"detection_source": result.get("detection_source"),
		"analysis": result.get("analysis"),
		"findings": result.get("findings", []),
		"backing_commits": result.get("backing_commits", []),
		"website": compact_website,
		"summary": result.get("summary"),
		"repositories_summary": result.get("repositories_summary", []),
		"warnings": result.get("warnings", []),
		"repositories": compact_repos,
	}


def investigate_company(
	github_url: str,
	website_url: str | None = None,
	*,
	include_raw: bool = False,
	transport: httpx.BaseTransport | None = None,
) -> dict[str, Any]:
	"""
	Complete end-to-end investigation:
	1. Collects and parses GitHub traces.
	2. Runs signal detection (Groq + rule fallback).
	3. Safely scrapes company website if provided.
	4. Runs final company analysis comparing website claims with code reality.
	Returns compact payload by default; pass include_raw=True for full commit histories.
	"""
	result = investigate_github(github_url, transport=transport)

	website_data = None
	if website_url:
		website_data = collect_website(website_url, transport=transport)
		if website_data.get("warnings"):
			result["warnings"].extend(website_data["warnings"])

	final_analysis = analyze_company(result, website_data, transport=transport)
	if final_analysis.get("warnings"):
		result["warnings"].extend(final_analysis["warnings"])

	full_result = {
		"status": result.get("status", "success"),
		"account": result.get("account"),
		"detection_source": result.get("detection_source"),
		"analysis": final_analysis,
		"findings": result.get("findings", []),
		"backing_commits": result.get("backing_commits", []),
		"website": website_data,
		"summary": result.get("summary"),
		"repositories_summary": result.get("repositories_summary", []),
		"warnings": result.get("warnings", []),
		"repositories": result.get("repositories", []),
		"parsed_commits": result.get("parsed_commits", []),
	}

	if include_raw:
		return full_result

	return compact_investigation_result(full_result)
