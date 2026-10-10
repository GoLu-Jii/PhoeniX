import os
import re
import time
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from urllib.parse import quote, urlsplit

import httpx
from dotenv import load_dotenv

GITHUB_API = "https://api.github.com"
PROJECT_ROOT = Path(__file__).resolve().parents[3]
REQUEST_TIMEOUT = 8.0
MAX_REPOSITORIES = 10
MAX_RECENT_COMMITS = 50
STATS_ATTEMPTS = 2
STATS_RETRY_DELAY = 0.2
_USERNAME = re.compile(r"^[A-Za-z0-9](?:[A-Za-z0-9-]{0,37}[A-Za-z0-9])?$")


def normalize_github_account(value: str) -> str:
	candidate = value.strip()
	if not candidate:
		raise ValueError("Enter a GitHub username or account URL.")

	if "://" in candidate:
		parsed = urlsplit(candidate)
		if (
			parsed.scheme != "https"
			or parsed.hostname not in {"github.com", "www.github.com"}
			or parsed.username is not None
			or parsed.password is not None
			or parsed.port is not None
			or parsed.query
			or parsed.fragment
		):
			raise ValueError("Enter a GitHub account URL such as https://github.com/octocat.")
		path = parsed.path.strip("/")
		if not path or "/" in path:
			raise ValueError("The GitHub URL must point directly to an account.")
		candidate = path

	if not _USERNAME.fullmatch(candidate):
		raise ValueError("Enter a valid GitHub username or account URL.")
	return candidate


def _warning(scope: str, message: str, repository: str | None = None) -> dict[str, str]:
	warning = {"scope": scope, "message": message}
	if repository is not None:
		warning["repository"] = repository
	return warning


def _request_failure(scope: str, error: Exception, repository: str | None = None) -> dict[str, str]:
	if isinstance(error, httpx.HTTPStatusError):
		status_code = error.response.status_code
		if status_code == 401:
			message = f"GitHub authentication failed for {scope}; check GITHUB_TOKEN."
		elif status_code == 403:
			try:
				response_message = error.response.json().get("message", "")
			except (ValueError, AttributeError):
				response_message = ""
			if (
				error.response.headers.get("X-RateLimit-Remaining") == "0"
				or "rate limit" in str(response_message).lower()
			):
				message = f"GitHub rate limit exceeded for {scope}."
			else:
				message = f"GitHub denied access to {scope} (HTTP 403); check token permissions."
		else:
			message = f"GitHub returned HTTP {status_code} for {scope}."
	else:
		message = f"GitHub request for {scope} failed due to a network or response error."
	return _warning(scope, message, repository)


def _timestamp(value: Any) -> datetime | None:
	if not isinstance(value, str):
		return None
	try:
		parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
	except ValueError:
		return None
	if parsed.tzinfo is None:
		return parsed.replace(tzinfo=timezone.utc)
	return parsed.astimezone(timezone.utc)


def _activity_rows(value: Any) -> list[dict[str, Any]]:
	if not isinstance(value, list):
		raise ValueError("Unexpected commit activity response.")

	rows = []
	for item in value:
		if not isinstance(item, dict):
			continue
		week = item.get("week")
		total = item.get("total")
		if not isinstance(week, (int, float)) or not isinstance(total, int):
			continue
		week_start = datetime.fromtimestamp(week, tz=timezone.utc)
		days = item.get("days")
		rows.append(
			{
				"week": week_start.isoformat().replace("+00:00", "Z"),
				"total": total,
				"days": days if isinstance(days, list) else [],
			}
		)
	return rows


def _recent_commit_rows(value: Any, since: datetime) -> list[dict[str, Any]]:
	if not isinstance(value, list):
		raise ValueError("Unexpected commits response.")

	rows = []
	for item in value[:MAX_RECENT_COMMITS]:
		if not isinstance(item, dict):
			continue
		commit = item.get("commit")
		if not isinstance(commit, dict):
			continue
		author = commit.get("author")
		committer = commit.get("committer")
		author = author if isinstance(author, dict) else {}
		committer = committer if isinstance(committer, dict) else {}
		committed_at = _timestamp(committer.get("date") or author.get("date"))
		if committed_at is None or committed_at < since:
			continue
		rows.append(
			{
				"sha": item.get("sha"),
				"url": item.get("html_url"),
				"message": str(commit.get("message") or "")[:240],
				"committed_at": committed_at.isoformat().replace("+00:00", "Z"),
			}
		)
	return rows


def _headers() -> dict[str, str]:
	load_dotenv(PROJECT_ROOT / ".env")
	headers = {
		"Accept": "application/vnd.github+json",
		"X-GitHub-Api-Version": "2022-11-28",
	}
	token = os.getenv("GITHUB_TOKEN")
	if token:
		headers["Authorization"] = f"Bearer {token}"
	return headers


def collect_github_account(
	value: str,
	*,
	transport: httpx.BaseTransport | None = None,
) -> dict[str, Any]:
	login = normalize_github_account(value)
	warnings: list[dict[str, str]] = []
	incomplete = False
	since = datetime.now(timezone.utc) - timedelta(days=45)
	since_param = since.isoformat(timespec="seconds").replace("+00:00", "Z")

	result: dict[str, Any] = {
		"status": "unavailable",
		"account": None,
		"repositories": [],
		"summary": {
			"repository_count": 0,
			"recent_commit_count": 0,
			"language_bytes": {},
			"weekly_commit_activity": [],
			"average_weekly_commits": None,
		},
		"warnings": warnings,
	}

	with httpx.Client(
		base_url=GITHUB_API,
		headers=_headers(),
		timeout=REQUEST_TIMEOUT,
		transport=transport,
	) as client:
		try:
			profile = client.get(f"/users/{quote(login)}")
			profile.raise_for_status()
			profile_data = profile.json()
			if not isinstance(profile_data, dict):
				raise ValueError("Unexpected account response.")
		except (httpx.HTTPError, ValueError) as error:
			warnings.append(_request_failure("account", error))
			return result

		account_type_name = profile_data.get("type")
		if account_type_name not in {"Organization", "User"}:
			warnings.append(_warning("account", "GitHub returned an unexpected account type."))
			return result
		account_type = "organization" if account_type_name == "Organization" else "user"
		result["account"] = {
			"login": profile_data.get("login", login),
			"name": profile_data.get("name"),
			"type": account_type,
			"url": profile_data.get("html_url", f"https://github.com/{login}"),
		}

		repositories_path = (
			f"/orgs/{quote(login)}" if account_type == "organization" else f"/users/{quote(login)}"
		)
		repository_params = {"sort": "pushed", "per_page": MAX_REPOSITORIES}
		if account_type == "organization":
			repository_params["type"] = "public"
		try:
			repositories_response = client.get(
				f"{repositories_path}/repos",
				params=repository_params,
			)
			repositories_response.raise_for_status()
			repositories_data = repositories_response.json()
			if not isinstance(repositories_data, list):
				raise ValueError("Unexpected repositories response.")
		except (httpx.HTTPError, ValueError) as error:
			warnings.append(_request_failure("repositories", error))
			result["status"] = "partial"
			return result

		repositories = []
		aggregate_languages: defaultdict[str, int] = defaultdict(int)
		aggregate_activity: defaultdict[str, int] = defaultdict(int)

		for source_repo in repositories_data[:MAX_REPOSITORIES]:
			if not isinstance(source_repo, dict) or source_repo.get("private") is True:
				continue

			owner_data = source_repo.get("owner")
			owner = owner_data.get("login") if isinstance(owner_data, dict) else login
			name = source_repo.get("name")
			if not isinstance(name, str) or not name:
				continue
			full_name = source_repo.get("full_name") or f"{owner}/{name}"
			repo_path = f"/repos/{quote(str(owner), safe='')}/{quote(name, safe='')}"
			repo = {
				"name": name,
				"full_name": full_name,
				"url": source_repo.get("html_url", f"https://github.com/{full_name}"),
				"description": source_repo.get("description"),
				"topics": source_repo.get("topics") if isinstance(source_repo.get("topics"), list) else [],
				"language": source_repo.get("language"),
				"created_at": source_repo.get("created_at"),
				"updated_at": source_repo.get("updated_at"),
				"pushed_at": source_repo.get("pushed_at"),
				"languages": {},
				"recent_commits": [],
				"weekly_commit_activity": [],
			}

			try:
				response = client.get(f"{repo_path}/languages")
				response.raise_for_status()
				language_data = response.json()
				if not isinstance(language_data, dict):
					raise ValueError("Unexpected languages response.")
				repo["languages"] = {
					language: count
					for language, count in language_data.items()
					if isinstance(language, str) and isinstance(count, int) and count >= 0
				}
				for language, count in repo["languages"].items():
					aggregate_languages[language] += count
			except (httpx.HTTPError, ValueError) as error:
				warnings.append(_request_failure("languages", error, full_name))
				incomplete = True

			try:
				response = client.get(
					f"{repo_path}/commits",
					params={"since": since_param, "per_page": MAX_RECENT_COMMITS},
				)
				response.raise_for_status()
				repo["recent_commits"] = _recent_commit_rows(response.json(), since)
			except (httpx.HTTPError, ValueError) as error:
				warnings.append(_request_failure("recent commits", error, full_name))
				incomplete = True

			try:
				response = None
				for attempt in range(STATS_ATTEMPTS):
					response = client.get(f"{repo_path}/stats/commit_activity")
					if response.status_code != 202 or attempt + 1 == STATS_ATTEMPTS:
						break
					time.sleep(STATS_RETRY_DELAY)
				if response is None or response.status_code == 202:
					warnings.append(
						_warning("commit activity", "GitHub is still computing commit activity.", full_name)
					)
					incomplete = True
				elif response.status_code == 204:
					repo["weekly_commit_activity"] = []
				else:
					response.raise_for_status()
					repo["weekly_commit_activity"] = _activity_rows(response.json())
					for row in repo["weekly_commit_activity"]:
						aggregate_activity[row["week"]] += row["total"]
			except (httpx.HTTPError, ValueError, OverflowError, OSError) as error:
				warnings.append(_request_failure("commit activity", error, full_name))
				incomplete = True

			repositories.append(repo)

	weekly_activity = [
		{"week": week, "total": total}
		for week, total in sorted(aggregate_activity.items())
	]
	result.update(
		{
			"status": "partial" if incomplete else "success",
			"repositories": repositories,
			"summary": {
				"repository_count": len(repositories),
				"recent_commit_count": sum(len(repo["recent_commits"]) for repo in repositories),
				"language_bytes": dict(sorted(aggregate_languages.items())),
				"weekly_commit_activity": weekly_activity,
				"average_weekly_commits": (
					round(sum(aggregate_activity.values()) / len(aggregate_activity), 2)
					if aggregate_activity
					else None
				),
			},
		}
	)
	return result
