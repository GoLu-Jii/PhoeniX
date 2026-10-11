import json
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import httpx
from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[2]
GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"
GROQ_DEFAULT_MODEL = "openai/gpt-oss-20b"
GROQ_TIMEOUT = 30.0
COMMIT_DAYS_LIMIT = 45
BATCH_SIZE = 25
MAX_BATCHES = 4
BURST_THRESHOLD = 5


def _as_utc_datetime(value: Any) -> datetime | None:
	if isinstance(value, datetime):
		parsed = value
	elif isinstance(value, str):
		try:
			parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
		except ValueError:
			return None
	else:
		return None

	if parsed.tzinfo is None:
		return parsed.replace(tzinfo=timezone.utc)
	return parsed.astimezone(timezone.utc)


def parse_github_commits(
	repositories: list[dict[str, Any]],
	*,
	now: datetime | None = None,
) -> list[dict[str, Any]]:
	"""
	Parses messy GitHub history JSON into a structured list of commits for the past 45 days.
	Each item contains: commit_date, commit_message, and committed_repo.
	Empty days, language data, and non-commit metadata are excluded.
	"""
	current_time = _as_utc_datetime(now or datetime.now(timezone.utc)) or datetime.now(timezone.utc)
	cutoff = current_time - timedelta(days=COMMIT_DAYS_LIMIT)
	parsed_commits: list[dict[str, Any]] = []

	for repo in repositories:
		if not isinstance(repo, dict):
			continue
		repo_name = repo.get("full_name") or repo.get("name")
		if not repo_name or not isinstance(repo_name, str):
			continue

		commits = repo.get("recent_commits") or repo.get("commits") or []
		if not isinstance(commits, list):
			continue

		for commit in commits:
			if not isinstance(commit, dict):
				continue

			# Extract commit message
			message = commit.get("message")
			if not message and isinstance(commit.get("commit"), dict):
				message = commit["commit"].get("message")
			if not isinstance(message, str) or not message.strip():
				continue

			# Extract date
			raw_date = (
				commit.get("committed_at")
				or commit.get("date")
				or (commit.get("commit", {}).get("author", {}).get("date") if isinstance(commit.get("commit"), dict) else None)
				or (commit.get("commit", {}).get("committer", {}).get("date") if isinstance(commit.get("commit"), dict) else None)
			)
			dt = _as_utc_datetime(raw_date)
			if dt is None:
				continue

			# Only keep commits within the past 45 days
			if not (cutoff <= dt <= current_time):
				continue

			commit_date_str = dt.strftime("%Y-%m-%d")
			parsed_commits.append(
				{
					"commit_date": commit_date_str,
					"commit_message": message.strip(),
					"committed_repo": repo_name,
				}
			)

	return parsed_commits


def rule_based_signal_detector(
	parsed_commits: list[dict[str, Any]],
) -> list[dict[str, Any]]:
	"""
	Groups commits by repository where commits were made.
	Returns: {committed_repo, number_of_commits, commit_messages} for each repo.
	Outputs one repo's total content completely first, then moves to the next repo.
	"""
	repo_map: dict[str, list[dict[str, Any]]] = {}
	for commit in parsed_commits:
		repo = commit.get("committed_repo") or commit.get("commited_repo") or "unknown"
		if repo not in repo_map:
			repo_map[repo] = []
		repo_map[repo].append(commit)

	results: list[dict[str, Any]] = []
	for repo_name, commits in repo_map.items():
		if not commits:
			continue
		messages = [c["commit_message"] for c in commits]
		results.append(
			{
				"committed_repo": repo_name,
				"commited_repo": repo_name,
				"number_of_commits": len(commits),
				"commit_messages": messages,
				"commit_message": messages,
				"commits": commits,
			}
		)

	return results


def summarize_daily_activity(
	parsed_commits: list[dict[str, Any]],
	*,
	burst_threshold: int = BURST_THRESHOLD,
) -> dict[str, Any]:
	"""
	Summarizes daily commit activity per repository to detect commit pace and bursts.
	Returns daily counts and identified burst days across the 45-day window.
	"""
	counts: dict[tuple[str, str], int] = {}
	for commit in parsed_commits:
		date = commit.get("commit_date") or "unknown"
		repo = commit.get("committed_repo") or commit.get("commited_repo") or "unknown"
		counts[(date, repo)] = counts.get((date, repo), 0) + 1

	daily_counts: list[dict[str, Any]] = []
	burst_days: list[dict[str, Any]] = []

	sorted_keys = sorted(counts.keys(), key=lambda k: k[0], reverse=True)
	for date, repo in sorted_keys:
		c = counts[(date, repo)]
		is_burst = c >= burst_threshold
		record = {
			"commit_date": date,
			"committed_repo": repo,
			"commits_count": c,
			"is_burst": is_burst,
		}
		daily_counts.append(record)
		if is_burst:
			burst_days.append({
				"commit_date": date,
				"committed_repo": repo,
				"commits_count": c,
			})

	return {
		"daily_counts": daily_counts,
		"burst_days": burst_days,
		"total_commits": len(parsed_commits),
	}


def batch_commits(
	parsed_commits: list[dict[str, Any]],
	*,
	batch_size: int = BATCH_SIZE,
	max_batches: int = MAX_BATCHES,
) -> list[list[dict[str, Any]]]:
	"""
	Splits commits into smaller batches to keep each Groq request within token limits.
	"""
	if not parsed_commits:
		return []
	batches = [
		parsed_commits[i : i + batch_size]
		for i in range(0, len(parsed_commits), batch_size)
	]
	return batches[:max_batches]


def merge_findings(findings_lists: list[list[dict[str, Any]]]) -> list[dict[str, Any]]:
	"""
	Merges findings from multiple batches without duplicates.
	Deduplicates based on normalized title and committed_repo, or identical descriptions.
	"""
	merged: list[dict[str, Any]] = []
	seen_title_repo: set[str] = set()
	seen_repo_desc: set[str] = set()

	for findings in findings_lists:
		if not isinstance(findings, list):
			continue
		for f in findings:
			if not isinstance(f, dict):
				continue
			title = str(f.get("title") or "").strip()
			repo = str(f.get("committed_repo") or "").strip()
			desc = str(f.get("description") or "").strip()
			if not title:
				continue

			key1 = f"{title.lower()}::{repo.lower()}"
			key2 = f"{repo.lower()}::{desc.lower()}" if desc else ""

			if key1 in seen_title_repo or (key2 and key2 in seen_repo_desc):
				continue

			seen_title_repo.add(key1)
			if key2:
				seen_repo_desc.add(key2)

			merged.append({
				"title": title,
				"committed_repo": repo,
				"description": desc,
			})
	return merged


def merge_backing_commits(backing_lists: list[list[str]]) -> list[str]:
	"""
	Merges backing commit messages without duplicates, preserving order of appearance.
	"""
	merged: list[str] = []
	seen: set[str] = set()

	for commit_list in backing_lists:
		if not isinstance(commit_list, list):
			continue
		for msg in commit_list:
			if not isinstance(msg, str):
				continue
			cleaned = msg.strip()
			if not cleaned:
				continue
			if cleaned not in seen:
				seen.add(cleaned)
				merged.append(cleaned)
	return merged


def _call_groq_batch(
	batch_commits: list[dict[str, Any]],
	burst_summary: list[dict[str, Any]],
	api_key: str,
	model: str,
	*,
	transport: httpx.BaseTransport | None = None,
) -> tuple[list[dict[str, Any]], list[str], str | None]:
	request_body = {
		"model": model,
		"temperature": 0.1,
		"response_format": {"type": "json_object"},
		"messages": [
			{
				"role": "system",
				"content": (
					"You are an AI code intelligence analyst. Analyze the provided commit history for the past 45 days. "
					"Detect anything suspicious, unusual, or notable, including:\n"
					"1. Content and direction signals:\n"
					"   - Stealth or unannounced projects or features\n"
					"   - Major infrastructure, CI/CD, or deployment shifts\n"
					"   - Security, credential, auth, or permission changes\n"
					"   - New AI model, agent, or evaluation tooling\n"
					"2. Velocity and pace signals:\n"
					"   - Unusual commit pace, burst commits, or sudden activity spikes in a repository over a short timeframe.\n\n"
					"Return ONLY valid JSON with this exact format:\n"
					"{\n"
					'  "findings": [\n'
					"    {\n"
					'      "title": "Short descriptive title of the signal",\n'
					'      "committed_repo": "Repository name",\n'
					'      "description": "What was observed and why it is suspicious or unusual"\n'
					"    }\n"
					"  ],\n"
					'  "backing_commits": [\n'
					'    "Exact commit message that supports the findings"\n'
					"  ]\n"
					"}\n\n"
					"CRITICAL RULES:\n"
					"- Return ONLY findings and backing_commits.\n"
					"- In backing_commits, include ONLY specific commit messages that support content-based findings (clues about what is being built or changed).\n"
					"- For pacing or burst findings ('unusual commit pace', bursts, spikes), DO NOT paste commit messages into backing_commits. Describe the burst or pace in the finding description instead, because velocity is a timing signal rather than a message-content signal.\n"
					"- If nothing suspicious or unusual is detected, return {\"findings\": [], \"backing_commits\": []}."
				),
			},
			{
				"role": "user",
				"content": json.dumps(
					{
						"daily_burst_summary": burst_summary,
						"commits": batch_commits,
					},
					ensure_ascii=False,
				),
			},
		],
	}

	try:
		with httpx.Client(timeout=GROQ_TIMEOUT, transport=transport) as client:
			response = client.post(
				GROQ_API_URL,
				headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
				json=request_body,
			)
			response.raise_for_status()
			content = response.json()["choices"][0]["message"]["content"]
			parsed = json.loads(content)
			raw_findings = parsed.get("findings", [])
			raw_backing = parsed.get("backing_commits", [])
			if not isinstance(raw_findings, list):
				return [], [], "Groq response findings must be a list."

			clean_findings = []
			for f in raw_findings:
				if not isinstance(f, dict):
					continue
				title = f.get("title")
				if not title or not isinstance(title, str):
					continue
				clean_findings.append({
					"title": title.strip(),
					"committed_repo": str(f.get("committed_repo") or "").strip(),
					"description": str(f.get("description") or "").strip(),
				})

			clean_backing = [
				str(msg).strip() for msg in raw_backing if isinstance(msg, str) and msg.strip()
			] if isinstance(raw_backing, list) else []

			return clean_findings, clean_backing, None
	except httpx.HTTPStatusError as error:
		if error.response.status_code == 413:
			return [], [], "Groq token limit exceeded (HTTP 413)."
		return [], [], f"Groq returned HTTP {error.response.status_code}."
	except httpx.HTTPError:
		return [], [], "Groq request failed due to network error."
	except (ValueError, KeyError, IndexError, TypeError):
		return [], [], "Groq response format was invalid."


def groq_signal_detector(
	parsed_commits: list[dict[str, Any]],
	*,
	transport: httpx.BaseTransport | None = None,
	batch_size: int = BATCH_SIZE,
	max_batches: int = MAX_BATCHES,
) -> tuple[list[dict[str, Any]], list[str], str | None]:
	"""
	Splits large commit histories into manageable batches that fit within Groq's token limits.
	Summarizes daily activity to detect bursts.
	Merges findings and backing commits across batches without duplicates.
	Returns (merged_findings, merged_backing_commits, error_message).
	"""
	if not parsed_commits:
		return [], [], None

	load_dotenv(PROJECT_ROOT / ".env")
	api_key = os.getenv("GROQ_API_KEY")
	if not api_key:
		return [], [], "GROQ_API_KEY is missing."

	model = os.getenv("GROQ_MODEL") or GROQ_DEFAULT_MODEL

	# Summarize daily activity to detect commit bursts
	daily_summary = summarize_daily_activity(parsed_commits)
	burst_summary = daily_summary.get("burst_days", [])

	# Split commits into smaller batches
	batches = batch_commits(parsed_commits, batch_size=batch_size, max_batches=max_batches)
	if not batches:
		return [], [], None

	all_findings_batches: list[list[dict[str, Any]]] = []
	all_backing_batches: list[list[str]] = []
	last_error: str | None = None
	successful_batches = 0

	for batch in batches:
		f_list, b_list, err = _call_groq_batch(
			batch,
			burst_summary,
			api_key,
			model,
			transport=transport,
		)
		if err is None:
			successful_batches += 1
			all_findings_batches.append(f_list)
			all_backing_batches.append(b_list)
		else:
			last_error = err

	# If all batches failed, Groq genuinely failed
	if successful_batches == 0:
		return [], [], last_error or "All Groq batches failed."

	# Merge findings and backing commits without duplicates
	merged_findings = merge_findings(all_findings_batches)
	merged_backing = merge_backing_commits(all_backing_batches)

	return merged_findings, merged_backing, None


def detect_signals(
	parsed_commits: list[dict[str, Any]],
	*,
	transport: httpx.BaseTransport | None = None,
) -> dict[str, Any]:
	"""
	Main signal detector module:
	1. Summarizes daily activity and batches commits for Groq AI to find suspicious/unusual signals.
	2. If Groq succeeds (at least one batch succeeded), returns merged findings and backing_commits.
	3. Only when Groq genuinely fails, falls back to the rule-based signal detector.
	"""
	if not parsed_commits:
		return {
			"detection_source": "rule_based",
			"findings": [],
			"backing_commits": [],
			"repositories": [],
			"warnings": [],
		}

	groq_findings, groq_backing, groq_error = groq_signal_detector(parsed_commits, transport=transport)

	if groq_error is None and groq_findings is not None:
		return {
			"detection_source": "groq",
			"findings": groq_findings,
			"backing_commits": groq_backing,
		}

	# Groq genuinely failed: fallback to rule-based signal detector
	rule_based_repos = rule_based_signal_detector(parsed_commits)
	fallback_findings = [
		{
			"title": f"Recent commit activity in {repo_item['committed_repo']}",
			"committed_repo": repo_item["committed_repo"],
			"description": f"Found {repo_item['number_of_commits']} commits in the past 45 days.",
		}
		for repo_item in rule_based_repos
	]
	fallback_backing = [
		msg
		for repo_item in rule_based_repos
		for msg in repo_item.get("commit_messages", [])
	]

	warning_msg = f"{groq_error} Falling back to rule-based signal detector."
	return {
		"detection_source": "rule_based",
		"findings": fallback_findings,
		"backing_commits": fallback_backing,
		"repositories": rule_based_repos,
		"warnings": [{"scope": "groq_interpretation", "message": warning_msg}],
	}



# Backward-compatible helper functions
def interpret_commit_themes(
	repositories: list[dict[str, Any]],
	*,
	transport: httpx.BaseTransport | None = None,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, str]]]:
	parsed = parse_github_commits(repositories)
	signals = detect_signals(parsed, transport=transport)
	return signals.get("findings", []), parsed, signals.get("warnings", [])


def detect_github_findings(
	repositories: list[dict[str, Any]],
	*,
	now: datetime | None = None,
) -> list[dict[str, Any]]:
	parsed = parse_github_commits(repositories, now=now)
	repo_summary = rule_based_signal_detector(parsed)
	return [
		{
			"id": f"finding_{i:03d}",
			"track": "unannounced_move",
			"category": "commit_activity",
			"title": f"Activity in {r['committed_repo']}",
			"observed_facts": [f"{r['number_of_commits']} commits in the past 45 days."],
			"committed_repo": r["committed_repo"],
			"number_of_commits": r["number_of_commits"],
			"commit_messages": r["commit_messages"],
		}
		for i, r in enumerate(repo_summary, start=1)
	]
